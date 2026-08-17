"""Celery runtime for the composition layer.

SESSION 142 / V2 — the runtime that walks a Composition's
ordered steps, dispatches to step primitives, and persists
outputs as ``Asset`` rows.

Two tasks ship in V2:

* ``execute_composition(composition_id)`` — walks every step
  in position order, dispatches to the matching primitive,
  persists the output Asset, advances the per-step state
  machine. Stops on first failure (composition status
  becomes ``PARTIAL`` if any prior step succeeded;
  ``FAILED`` otherwise). Idempotent: re-running on a
  ``COMPLETED`` composition is a no-op; re-running on a
  ``PARTIAL`` composition resumes from the first non-
  ``SUCCEEDED`` step (prior outputs are preserved).
* ``retry_step(step_id)`` — resets a ``FAILED`` step to
  ``PENDING`` + clears its error + re-enqueues
  ``execute_composition``. The same composition runs
  forward from the now-PENDING step.

State machines (locked in VIDEO_COMPOSITION_V1.md §"Composition
execution"):

  Composition: DRAFT → PLANNING → RUNNING ──┬──► COMPLETED
                                             ├──► PARTIAL
                                             └──► FAILED

  Step:        PENDING → RUNNING ──┬──► SUCCEEDED
                                    └──► FAILED

This module is one of the sanctioned writers of the
composition tables (see
``apps/compositions/tests/test_isolation.py``); it creates
``Asset`` rows for step outputs + updates ``Composition`` +
``CompositionStep`` status. All cross-workspace validation
runs at save time via the V1 signal + ``clean()`` — the
runtime treats those guarantees as load-bearing and does
not re-check them on the read side, except for a defense-
in-depth assertion in input resolution.
"""
from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from celery import chord, group, shared_task
from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .assets import StorageHealth, compute_storage_health
from .cost import refresh_composition_cost_actual
from .execution_layers import DagValidationError, compute_execution_layers
from .models import (
    Asset,
    Composition,
    CompositionStatus,
    CompositionStep,
    StepStatus,
)
from .primitives import (
    PrimitiveError,
    PrimitiveResult,
    UnknownPrimitiveError,
    get_primitive,
)

logger = logging.getLogger(__name__)


# ---- error types ------------------------------------------


class WorkspaceMismatchError(Exception):
    """Raised by ``_resolve_inputs`` when a step's
    ``asset_id`` input references an asset in a different
    workspace than the composition. The V1 signal already
    rejects this at save time; this is defense-in-depth for
    the read path."""


class InputResolutionError(Exception):
    """Raised when a step's ``from_step_position`` input
    refers to a step that has no output yet (the upstream
    step is PENDING/RUNNING/FAILED). The runtime treats this
    as a step failure rather than crashing — the operator
    sees a clear message."""


# ---- the main task ----------------------------------------


@shared_task(
    bind=True,
    name="apps.compositions.tasks.execute_composition",
    max_retries=0,  # primitives handle their own retries
)
def execute_composition(self, composition_id: str) -> dict[str, Any]:
    """Walk steps in position order, fire each primitive,
    persist outputs as Assets. Idempotent and resume-safe.

    Returns a small status dict for Celery's result backend.
    The real state lives on the Composition + Step rows.
    """
    composition = Composition.objects.filter(pk=composition_id).first()
    if composition is None:
        logger.error("execute_composition: composition=%s not found", composition_id)
        return {"composition_id": composition_id, "status": "not_found"}

    # Idempotency guard: COMPLETED compositions are terminal.
    if composition.status == CompositionStatus.COMPLETED:
        logger.info(
            "execute_composition: composition=%s already completed — no-op",
            composition_id,
        )
        return {
            "composition_id": composition_id,
            "status": "already_completed",
        }

    # FAILED at step-0 is also terminal unless the operator
    # explicitly retried (which flips the step back to
    # PENDING via retry_step).
    if composition.status == CompositionStatus.FAILED:
        any_pending = composition.steps.filter(
            status__in=[StepStatus.PENDING, StepStatus.RUNNING]
        ).exists()
        if not any_pending:
            logger.info(
                "execute_composition: composition=%s in FAILED with no PENDING steps — no-op",
                composition_id,
            )
            return {
                "composition_id": composition_id,
                "status": "already_failed_no_retry",
            }

    # P2.G — parallel dispatch branch. When the master switch is
    # on AND this composition's ``template_kind`` is in the
    # allow-list, hand off to the parallel entry point + return.
    # Sequential path continues as the default for everything else.
    if _should_use_parallel_execution(composition):
        return _dispatch_composition_parallel(composition)

    # Flip to RUNNING. clear error_message so a previously
    # PARTIAL composition's stale error doesn't haunt the
    # resumed run.
    composition.status = CompositionStatus.RUNNING
    composition.error_message = ""
    composition.save(
        update_fields=["status", "error_message", "updated_at"],
    )

    # Build a map of already-succeeded step outputs so
    # later steps can resolve ``from_step_position`` inputs.
    steps = list(composition.steps.all().order_by("position"))
    prior_outputs: dict[int, Asset] = {}
    for step in steps:
        if step.status == StepStatus.SUCCEEDED and step.output_asset_id:
            prior_outputs[step.position] = step.output_asset

    for step in steps:
        if step.status == StepStatus.SUCCEEDED:
            # Resumed run — skip; output_asset already captured above.
            logger.info(
                "execute_composition: step=%s already SUCCEEDED — skipping",
                step.id,
            )
            continue

        # Move step to RUNNING, clear any stale error.
        started_at = timezone.now()
        started_perf = time.perf_counter()
        step.status = StepStatus.RUNNING
        step.error_message = ""
        step.started_at = started_at
        step.save(
            update_fields=["status", "error_message", "started_at"],
        )

        try:
            resolved_inputs = _resolve_inputs(step, prior_outputs)
            primitive = get_primitive(step.primitive)
            result = primitive.execute(
                step=step,
                resolved_inputs=resolved_inputs,
                mock_mode=composition.mock_mode,
            )

            with transaction.atomic():
                asset = _persist_output_asset(composition, step, result)
                step.output_asset = asset
                step.status = StepStatus.SUCCEEDED
                step.cost_actual_micros = result.cost_micros
                step.completed_at = timezone.now()
                step.elapsed_ms = int(
                    (time.perf_counter() - started_perf) * 1000
                )
                step.save(
                    update_fields=[
                        "output_asset",
                        "status",
                        "cost_actual_micros",
                        "completed_at",
                        "elapsed_ms",
                    ]
                )

            prior_outputs[step.position] = asset
            # Keep the composition's cost_actual in sync as
            # the run progresses — useful for live dashboards
            # in V8+ and for partial-failure cost accounting.
            refresh_composition_cost_actual(composition)

        except Exception as exc:
            return _mark_step_failed(composition, step, exc, started_perf, steps)

    # Every step succeeded.
    final_asset = (
        steps[-1].output_asset if (steps and steps[-1].output_asset_id) else None
    )
    composition.final_asset = final_asset
    composition.status = CompositionStatus.COMPLETED

    # SESSION 210 — aggregate knowledge_chunk_ids from produced
    # assets' source_spec into Composition.knowledge_chunk_ids.
    # Closes the SESSION 209 calibration finding: every
    # use_knowledge=True render not anchored in a Script-row
    # lineage was writing chunks to the final Asset's
    # source_spec.knowledge_chunk_ids but never aggregating to
    # the Composition level — breaking SPA citation surfaces
    # (F-arc brief-mode panel, BC4 lineage, verifier panel) for
    # single-step renders. Generic — applies to talking_head,
    # talking_head_polished, long_form_ad, storyboard_voiced,
    # and any future knowledge-grounded recipe.
    chunks_changed = _aggregate_knowledge_chunk_ids(composition)

    update_fields = ["final_asset", "status", "updated_at"]
    if chunks_changed:
        update_fields.append("knowledge_chunk_ids")
    composition.save(update_fields=update_fields)
    refresh_composition_cost_actual(composition)

    logger.info(
        "execute_composition: composition=%s COMPLETED steps=%d cost_actual=%d",
        composition.id,
        len(steps),
        composition.cost_actual_micros,
    )

    return {
        "composition_id": str(composition.id),
        "status": "completed",
        "steps_succeeded": len(steps),
        "cost_actual_micros": composition.cost_actual_micros,
    }


@shared_task(
    name="apps.compositions.tasks.retry_step",
    max_retries=0,
)
def retry_step(step_id: str) -> dict[str, Any]:
    """Reset a FAILED step to PENDING + clear error +
    re-enqueue the composition. The composition runs forward
    from this step; prior SUCCEEDED steps are skipped (their
    outputs are preserved on the step rows).

    Idempotency: retrying a non-FAILED step is a no-op.
    """
    step = CompositionStep.objects.filter(pk=step_id).first()
    if step is None:
        return {"step_id": step_id, "status": "not_found"}

    if step.status != StepStatus.FAILED:
        return {"step_id": step_id, "status": "not_failed"}

    step.status = StepStatus.PENDING
    step.error_message = ""
    step.output_asset = None
    step.completed_at = None
    step.elapsed_ms = None
    step.cost_actual_micros = 0
    step.save(
        update_fields=[
            "status",
            "error_message",
            "output_asset",
            "completed_at",
            "elapsed_ms",
            "cost_actual_micros",
        ]
    )

    execute_composition.delay(str(step.composition_id))
    return {
        "step_id": step_id,
        "composition_id": str(step.composition_id),
        "status": "retried",
    }


# ---- helpers ----------------------------------------------


def _resolve_inputs(
    step: CompositionStep,
    prior_outputs: dict[int, Asset],
) -> list[dict[str, Any]]:
    """Resolve every entry in ``step.inputs`` to a concrete
    Asset. Two shapes are supported:

    * ``{"slot": "...", "asset_id": "<uuid>"}`` — workspace
      asset by id. The V1 signal already rejected
      cross-workspace asset ids at save time; the read here
      is defensive and raises ``WorkspaceMismatchError`` if
      somehow one slipped past.
    * ``{"slot": "...", "from_step_position": <int>}`` —
      output of an earlier step in the same composition.
      Raises ``InputResolutionError`` if the upstream step
      hasn't succeeded yet.

    Returns a list of ``{"slot": str, "asset": Asset}`` dicts
    in input-list order so primitives can rely on positional
    semantics when slot names collide (which they shouldn't
    in practice).
    """
    composition_workspace_id = step.composition.workspace_id
    resolved: list[dict[str, Any]] = []

    if not isinstance(step.inputs, list):
        return resolved

    for entry in step.inputs:
        if not isinstance(entry, dict):
            continue
        slot = entry.get("slot", "")

        asset_id = entry.get("asset_id")
        from_pos = entry.get("from_step_position")

        if asset_id:
            try:
                asset_uuid = UUID(str(asset_id))
            except (ValueError, TypeError) as exc:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"asset_id {asset_id!r} is not a valid UUID"
                ) from exc
            asset = Asset.objects.filter(pk=asset_uuid).first()
            if asset is None:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"asset {asset_id} not found"
                )
            if asset.workspace_id != composition_workspace_id:
                raise WorkspaceMismatchError(
                    f"step {step.position} slot {slot!r}: "
                    f"asset {asset.pk} workspace {asset.workspace_id} "
                    f"!= composition workspace {composition_workspace_id}"
                )
            resolved.append({"slot": slot, "asset": asset})
            continue

        if from_pos is not None:
            try:
                upstream_pos = int(from_pos)
            except (ValueError, TypeError) as exc:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"from_step_position {from_pos!r} is not an integer"
                ) from exc
            upstream_asset = prior_outputs.get(upstream_pos)
            if upstream_asset is None:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"from_step_position {upstream_pos} has no output yet"
                )
            resolved.append({"slot": slot, "asset": upstream_asset})
            continue

        # Neither asset_id nor from_step_position — treat as
        # a no-op input (e.g., a slot the primitive optionally
        # accepts but the operator didn't fill).
        continue

    return resolved


def _persist_output_asset(
    composition: Composition,
    step: CompositionStep,
    result: PrimitiveResult,
) -> Asset:
    """Create an Asset row capturing the primitive's output.
    Records provenance in ``source_spec`` so re-runs +
    audits can reconstruct what fed the asset.

    Asset Library v1 contract rule 20 (SESSION 186 / A2): the
    primitive must have stamped ``result.role``. Defense-in-depth
    raise here catches any future primitive that forgets, since
    a role-less row would defeat A4's role-filtered list and A7's
    asset_picker. The coverage test in
    ``tests/test_primitive_role_coverage.py`` is the static
    enforcement; this raise is the runtime backstop.
    """
    if not result.role:
        raise PrimitiveError(
            f"primitive {step.primitive!r} (step {step.id}) returned a "
            "PrimitiveResult with no role stamped. Contract rule 20: every "
            "primitive must set role=AssetRole.X.value on its output. See "
            "apps.compositions.asset_roles.PRIMITIVE_TO_ROLE for the "
            "registered mapping."
        )

    source_spec: dict[str, Any] = {
        "primitive": step.primitive,
        "step_position": step.position,
        "step_id": str(step.id),
        "composition_id": str(composition.id),
        "params": step.params or {},
        "mock_mode": composition.mock_mode,
    }
    if result.extra_source_spec:
        source_spec.update(result.extra_source_spec)

    return Asset.objects.create(
        workspace=composition.workspace,
        asset_type=result.asset_type,
        file_path=result.file_path,
        inline_content=result.inline_content,
        source_spec=source_spec,
        duration_ms=result.duration_ms,
        width=result.width,
        height=result.height,
        mime_type=result.mime_type,
        size_bytes=result.size_bytes,
        cost_micros=result.cost_micros,
        composition=composition,
        role=result.role,
        # W11.6.5.3 (SESSION 174) — auto-title from the parent
        # composition's name so the SPA asset_picker dropdowns
        # render readable labels instead of CDN URL tails. SESSION
        # 177 — for multi-step compositions (long_form_ad chunks,
        # storyboard beats, etc.), append a per-step suffix so
        # the dropdown distinguishes step outputs that would
        # otherwise share the same title verbatim.
        title=_step_asset_title(composition, step),
    )


def _step_asset_title(composition: Composition, step: CompositionStep) -> str:
    """Compose the auto-title for a step's output Asset.

    Single-step compositions: just the composition name (no suffix
    — operator UX stays unchanged from W11.6.5.3 for the common
    case). Multi-step compositions: append `— step N/M
    (<primitive>)` so the SPA asset_picker can distinguish the
    intermediate + final outputs of a long_form_ad / storyboard /
    chunked render. Total cap 120 chars to stay within the
    `Asset.title` column ceiling.
    """
    base = (composition.name or "").strip()
    total = composition.steps.count()
    if total <= 1:
        return base[:120]
    human_pos = (step.position or 0) + 1
    suffix = f" — step {human_pos}/{total} ({step.primitive})"
    # Reserve the suffix length first so the base gets truncated
    # rather than the suffix.
    base_budget = 120 - len(suffix)
    if base_budget < 1:
        # Implausibly long primitive names — fall back to base only.
        return base[:120]
    return (base[:base_budget] + suffix)[:120]


def _aggregate_knowledge_chunk_ids(composition: Composition) -> bool:
    """Aggregate knowledge_chunk_ids from produced assets' source_spec
    into ``Composition.knowledge_chunk_ids``.

    Walks every Asset produced by this composition's steps and pulls
    ``source_spec["knowledge_chunk_ids"]`` (set by primitives like
    ``generate_avatar_speech`` when ``use_knowledge=True``). The
    union is written to ``Composition.knowledge_chunk_ids``,
    preserving any entries already present (e.g. the BC2 Script-row
    lineage carry-up in ``starters.py``).

    Generic — applies to talking_head, talking_head_polished,
    long_form_ad, storyboard_voiced, and any future
    knowledge-grounded recipe.

    Returns ``True`` if the field changed (caller should include it
    in the next ``save(update_fields=...)`` call), ``False`` if
    nothing to aggregate or no change.

    Mutates ``composition.knowledge_chunk_ids`` in place; the caller
    is responsible for persisting.
    """
    # Preserve any existing chunks (e.g. BC2 Script lineage path
    # at ``starters.py:252`` writes them at composition-create time).
    existing: list[str] = [str(cid) for cid in (composition.knowledge_chunk_ids or [])]
    seen: set[str] = set(existing)
    aggregated: set[str] = set(existing)

    # Walk every Asset this composition produced.
    for asset in composition.produced_assets.all():
        source_spec = asset.source_spec or {}
        for cid in (source_spec.get("knowledge_chunk_ids") or []):
            aggregated.add(str(cid))

    if not aggregated:
        return False

    # Stable output: preserve original ordering of any existing
    # entries, append newly-discovered chunk_ids sorted for
    # determinism. Keeps BC2 ordering intact for the lineage
    # case while still aggregating asset-level chunks.
    final = list(existing)
    for cid in sorted(aggregated - seen):
        final.append(cid)

    if final != existing:
        composition.knowledge_chunk_ids = final
        return True
    return False


def _mark_step_failed(
    composition: Composition,
    step: CompositionStep,
    exc: Exception,
    started_perf: float,
    all_steps: list[CompositionStep],
) -> dict[str, Any]:
    """Persist a step failure and set the composition to the
    right terminal state (PARTIAL if any earlier step
    succeeded; FAILED otherwise). Returns a Celery-friendly
    status dict.
    """
    error_kind = (
        "unknown_primitive" if isinstance(exc, UnknownPrimitiveError)
        else "workspace_mismatch" if isinstance(exc, WorkspaceMismatchError)
        else "input_resolution" if isinstance(exc, InputResolutionError)
        else "primitive_failure" if isinstance(exc, PrimitiveError)
        else "unexpected"
    )

    elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
    step.status = StepStatus.FAILED
    step.error_message = f"{type(exc).__name__}: {exc}"[:1000]
    step.completed_at = timezone.now()
    step.elapsed_ms = elapsed_ms
    step.save(
        update_fields=[
            "status",
            "error_message",
            "completed_at",
            "elapsed_ms",
        ]
    )

    # Decide composition terminal state. If *any* step
    # succeeded before this one, partial; else fully failed.
    any_succeeded = any(
        s.status == StepStatus.SUCCEEDED for s in all_steps
    )
    composition.status = (
        CompositionStatus.PARTIAL if any_succeeded
        else CompositionStatus.FAILED
    )
    composition.error_message = (
        f"step {step.position} ({step.primitive}): "
        f"{type(exc).__name__}: {exc}"
    )[:1000]
    composition.save(
        update_fields=["status", "error_message", "updated_at"],
    )
    refresh_composition_cost_actual(composition)

    logger.warning(
        "execute_composition: composition=%s step=%s position=%d %s — %s",
        composition.id, step.id, step.position, error_kind, exc,
    )

    return {
        "composition_id": str(composition.id),
        "status": composition.status,
        "failed_step_id": str(step.id),
        "failed_step_position": step.position,
        "error_kind": error_kind,
    }


# ---- P2: parallel execution primitives --------------------
#
# SESSION 258 / P2.B — helpers and a per-step Celery task that,
# together with the layer coordinator (P2.D) and the entry-point
# branch (P2.G), let a composition execute layers of siblings in
# parallel instead of one step at a time. The pieces here are
# deliberately independent of ``execute_composition`` — they can
# be tested and imported without touching the sequential runner.
#
# Contract deltas vs the sequential runner (see scope-lock):
#
# * Input resolution reads UPSTREAM STEP OUTPUTS FROM THE DATABASE
#   (``CompositionStep.output_asset``). The sequential runner's
#   ``prior_outputs: dict[int, Asset]`` can't be shared across
#   workers — the parallel path cannot rely on it. Preserving the
#   asset_id branch verbatim keeps workspace-mismatch defense-in-
#   depth on both paths.
# * ``execute_step`` NEVER re-raises. A parallel dispatch attaches a
#   chord callback (the layer coordinator) that must always fire so
#   it can decide the next layer's disposition from aggregated
#   results. Raising inside a chord member cancels the callback and
#   strands the composition in RUNNING forever.
# * Step failure is persisted step-locally. The composition-level
#   FAILED / PARTIAL / COMPLETED transition is made ONLY by the
#   layer coordinator after fan-in, from the DB state — not from
#   any single step's runtime knowledge.


def _resolve_inputs_from_db(
    step: CompositionStep,
) -> list[dict[str, Any]]:
    """P2 twin of ``_resolve_inputs`` that resolves
    ``from_step_position`` entries by reading the upstream
    ``CompositionStep.output_asset`` from the database, rather than
    a caller-supplied ``prior_outputs`` dict.

    Contract:

    * ``asset_id`` entries are handled identically to the sequential
      resolver (defense-in-depth workspace check retained).
    * ``from_step_position`` entries require the referenced upstream
      step to be ``SUCCEEDED`` **and** to have a non-null
      ``output_asset``; anything else raises
      ``InputResolutionError`` so the step fails cleanly instead of
      the primitive receiving an incomplete input list.
    * Starter-authored input-list order is preserved so slot-order-
      sensitive primitives (e.g. ``concat_clips``) still see clips
      in the intended sequence.
    """
    composition_workspace_id = step.composition.workspace_id
    resolved: list[dict[str, Any]] = []

    if not isinstance(step.inputs, list):
        return resolved

    for entry in step.inputs:
        if not isinstance(entry, dict):
            continue
        slot = entry.get("slot", "")

        asset_id = entry.get("asset_id")
        from_pos = entry.get("from_step_position")

        if asset_id:
            try:
                asset_uuid = UUID(str(asset_id))
            except (ValueError, TypeError) as exc:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"asset_id {asset_id!r} is not a valid UUID"
                ) from exc
            asset = Asset.objects.filter(pk=asset_uuid).first()
            if asset is None:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"asset {asset_id} not found"
                )
            if asset.workspace_id != composition_workspace_id:
                raise WorkspaceMismatchError(
                    f"step {step.position} slot {slot!r}: "
                    f"asset {asset.pk} workspace {asset.workspace_id} "
                    f"!= composition workspace {composition_workspace_id}"
                )
            resolved.append({"slot": slot, "asset": asset})
            continue

        if from_pos is not None:
            try:
                upstream_pos = int(from_pos)
            except (ValueError, TypeError) as exc:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"from_step_position {from_pos!r} is not an integer"
                ) from exc
            upstream = (
                CompositionStep.objects
                .filter(
                    composition_id=step.composition_id,
                    position=upstream_pos,
                )
                .select_related("output_asset")
                .first()
            )
            if upstream is None:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"from_step_position {upstream_pos} has no matching "
                    f"step in this composition"
                )
            if upstream.status != StepStatus.SUCCEEDED:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"upstream step {upstream_pos} status "
                    f"{upstream.status!r} (expected SUCCEEDED)"
                )
            if upstream.output_asset_id is None:
                raise InputResolutionError(
                    f"step {step.position} slot {slot!r}: "
                    f"upstream step {upstream_pos} SUCCEEDED but has "
                    f"no output_asset"
                )
            resolved.append({"slot": slot, "asset": upstream.output_asset})
            continue

        # Neither asset_id nor from_step_position — optional slot
        # the operator didn't fill; mirror the sequential runner.
        continue

    return resolved


def _classify_step_error(exc: Exception) -> str:
    """Same taxonomy as ``_mark_step_failed`` — shared by the
    parallel-only step-failure helper so both paths surface the
    same ``error_kind`` values in logs/metrics."""
    if isinstance(exc, UnknownPrimitiveError):
        return "unknown_primitive"
    if isinstance(exc, WorkspaceMismatchError):
        return "workspace_mismatch"
    if isinstance(exc, InputResolutionError):
        return "input_resolution"
    if isinstance(exc, PrimitiveError):
        return "primitive_failure"
    return "unexpected"


def _mark_step_only_failed(
    step: CompositionStep,
    exc: Exception,
    started_perf: float,
) -> str:
    """Persist a step-level failure WITHOUT touching the parent
    ``Composition`` status or error_message.

    In the parallel path, the composition-level FAILED / PARTIAL /
    COMPLETED transition is a data-driven decision made by the
    layer coordinator (P2.D) after fan-in — one failing step in a
    layer of siblings is not enough information on its own. Siblings
    may still be running; earlier layers may have succeeded. The
    coordinator reads the DB and decides.

    Returns the ``error_kind`` string so the caller can log/tag.
    """
    elapsed_ms = int((time.perf_counter() - started_perf) * 1000)
    step.status = StepStatus.FAILED
    step.error_message = f"{type(exc).__name__}: {exc}"[:1000]
    step.completed_at = timezone.now()
    step.elapsed_ms = elapsed_ms
    step.save(
        update_fields=[
            "status",
            "error_message",
            "completed_at",
            "elapsed_ms",
        ]
    )
    return _classify_step_error(exc)


@shared_task(
    bind=True,
    name="apps.compositions.tasks.execute_step",
    max_retries=0,  # primitives handle their own retries
)
def execute_step(self, step_id: str) -> dict[str, Any]:
    """Run one ``CompositionStep`` to terminal state and return a
    status dict.

    This task is the parallel-path unit of dispatch — the layer
    coordinator (P2.D) launches a Celery ``group`` of these, with
    itself as the chord callback. It MUST NOT re-raise on failure:
    raising cancels the chord and strands the composition, so every
    failure path funnels through ``_mark_step_only_failed`` and
    returns a status dict.

    Idempotency:

    * ``SUCCEEDED`` — returns ``{"status": "already_succeeded"}``
      without touching the row. Lets a resume dispatch cover a layer
      where some siblings already ran.
    * ``FAILED`` — returns ``{"status": "already_failed"}`` without
      re-executing. Operator retry (``retry_step``) is the only way
      to re-run a failed step; a coordinator resume must not
      silently retry.
    * ``PENDING`` / ``RUNNING`` — executes normally.

    Cost + provenance semantics match the sequential runner: the
    Asset row + step transition are committed inside one
    ``transaction.atomic()``; the composition's ``cost_actual_micros``
    is refreshed via the P1 SQL-subquery aggregator so concurrent
    siblings can't clobber each other's writes.
    """
    step = (
        CompositionStep.objects
        .select_related("composition")
        .filter(pk=step_id)
        .first()
    )
    if step is None:
        logger.error("execute_step: step=%s not found", step_id)
        return {"step_id": step_id, "status": "not_found"}

    if step.status == StepStatus.SUCCEEDED:
        return {
            "step_id": step_id,
            "position": step.position,
            "status": "already_succeeded",
        }

    if step.status == StepStatus.FAILED:
        return {
            "step_id": step_id,
            "position": step.position,
            "status": "already_failed",
        }

    composition = step.composition
    started_at = timezone.now()
    started_perf = time.perf_counter()

    step.status = StepStatus.RUNNING
    step.error_message = ""
    step.started_at = started_at
    step.save(update_fields=["status", "error_message", "started_at"])

    try:
        resolved_inputs = _resolve_inputs_from_db(step)
        primitive = get_primitive(step.primitive)
        result = primitive.execute(
            step=step,
            resolved_inputs=resolved_inputs,
            mock_mode=composition.mock_mode,
        )

        with transaction.atomic():
            asset = _persist_output_asset(composition, step, result)
            step.output_asset = asset
            step.status = StepStatus.SUCCEEDED
            step.cost_actual_micros = result.cost_micros
            step.completed_at = timezone.now()
            step.elapsed_ms = int(
                (time.perf_counter() - started_perf) * 1000
            )
            step.save(
                update_fields=[
                    "output_asset",
                    "status",
                    "cost_actual_micros",
                    "completed_at",
                    "elapsed_ms",
                ]
            )

        # P1-safe: SQL subquery UPDATE avoids read-modify-write
        # races when sibling steps finish nearly-simultaneously.
        refresh_composition_cost_actual(composition)

        return {
            "step_id": str(step.id),
            "position": step.position,
            "status": "succeeded",
            "cost_actual_micros": result.cost_micros,
        }

    except Exception as exc:  # noqa: BLE001 — funnel-all is required
        error_kind = _mark_step_only_failed(step, exc, started_perf)
        # Refresh cost even on failure: partial siblings may have
        # already committed cost_actual_micros to their step rows.
        refresh_composition_cost_actual(composition)
        logger.warning(
            "execute_step: composition=%s step=%s position=%d %s — %s",
            composition.id, step.id, step.position, error_kind, exc,
        )
        return {
            "step_id": str(step.id),
            "position": step.position,
            "status": "failed",
            "error_kind": error_kind,
        }


# ---- P2: layer coordinator (chord callback) --------------
#
# SESSION 258 / P2.D + P2.F — the coordinator is the ONLY
# writer of the composition's terminal
# (COMPLETED / PARTIAL / FAILED) state on the parallel path.
# It runs as a Celery chord callback after every step in a
# dispatched layer has returned a status dict, then decides
# from the DB state (never from the results list) whether to
# dispatch the next layer or finalize.
#
# Failure economics (scope-lock): successful siblings survive.
# On a failure anywhere in the composition, subsequent layers
# are NOT dispatched — dependent steps would fail input
# resolution against the missing upstream. The finalize path
# preserves the PARTIAL vs FAILED split by walking step
# statuses: any-succeeded + any-failed => PARTIAL; all-failed
# with no successes => FAILED; all-succeeded => COMPLETED.
#
# Non-blocking chord dispatch: the coordinator schedules the
# next layer via ``chord(group, coordinator).apply_async()`` —
# no ``.get()`` / ``.join()`` calls anywhere. Celery workers
# stay free to execute other steps.


def _finalize_parallel_composition(
    composition: Composition,
    steps: list[CompositionStep],
    *,
    forced_status: str | None = None,
    error_message: str | None = None,
) -> dict[str, Any]:
    """Terminal-state writer for a parallel-run composition.

    Decides COMPLETED / PARTIAL / FAILED from the DB step
    statuses (or from ``forced_status`` when we detected a
    malformed DAG). Wires ``final_asset`` on clean completion,
    aggregates knowledge_chunk_ids (SESSION 210 semantics),
    refreshes ``cost_actual_micros`` via the P1 SQL aggregator.

    Sequential + parallel paths share ``_aggregate_knowledge_chunk_ids``
    + ``refresh_composition_cost_actual`` so downstream SPA
    surfaces (F-arc brief-mode, verifier panel, lineage) see the
    same shape regardless of dispatch mode.
    """
    if forced_status is not None:
        final_status = forced_status
    else:
        any_failed = any(s.status == StepStatus.FAILED for s in steps)
        any_succeeded = any(
            s.status == StepStatus.SUCCEEDED for s in steps
        )
        if any_failed and any_succeeded:
            final_status = CompositionStatus.PARTIAL
        elif any_failed:
            final_status = CompositionStatus.FAILED
        else:
            final_status = CompositionStatus.COMPLETED

    # Wire final_asset only on clean completion; PARTIAL/FAILED
    # deliberately leaves it unset so SPA "watch the render"
    # doesn't wire an incomplete deliverable.
    if final_status == CompositionStatus.COMPLETED and steps:
        last = steps[-1]
        if last.output_asset_id:
            composition.final_asset = last.output_asset

    if final_status == CompositionStatus.COMPLETED:
        composition.error_message = ""
    elif error_message is not None:
        composition.error_message = error_message[:1000]
    else:
        first_failed = next(
            (s for s in steps if s.status == StepStatus.FAILED),
            None,
        )
        if first_failed is not None:
            composition.error_message = (
                f"step {first_failed.position} "
                f"({first_failed.primitive}): "
                f"{first_failed.error_message}"
            )[:1000]

    composition.status = final_status

    chunks_changed = _aggregate_knowledge_chunk_ids(composition)

    update_fields = [
        "final_asset",
        "status",
        "error_message",
        "updated_at",
    ]
    if chunks_changed:
        update_fields.append("knowledge_chunk_ids")
    composition.save(update_fields=update_fields)
    refresh_composition_cost_actual(composition)

    steps_succeeded = sum(
        1 for s in steps if s.status == StepStatus.SUCCEEDED
    )
    steps_failed = sum(
        1 for s in steps if s.status == StepStatus.FAILED
    )

    logger.info(
        "coordinator: composition=%s finalized status=%s "
        "steps=%d succeeded=%d failed=%d cost_actual=%d",
        composition.id, final_status, len(steps),
        steps_succeeded, steps_failed,
        composition.cost_actual_micros,
    )

    return {
        "composition_id": str(composition.id),
        "status": final_status,
        "steps_total": len(steps),
        "steps_succeeded": steps_succeeded,
        "steps_failed": steps_failed,
        "cost_actual_micros": composition.cost_actual_micros,
    }


def _dispatch_layer(
    composition_id: str,
    step_ids: list[str],
    next_layer_index: int,
) -> None:
    """Fire a Celery chord: parallel ``execute_step`` group +
    coordinator callback. Non-blocking — returns immediately;
    the coordinator resumes when the group's members are all
    done.

    ``.si(sid)`` (immutable signature) means the chord passes
    only the results list to the callback and doesn't try to
    forward any prior chain result.
    """
    chord(
        group(execute_step.si(sid) for sid in step_ids),
        execute_composition_layer_coordinator.s(
            composition_id, next_layer_index,
        ),
    ).apply_async()


@shared_task(
    bind=True,
    name="apps.compositions.tasks.execute_composition_layer_coordinator",
    max_retries=0,
)
def execute_composition_layer_coordinator(
    self,
    results: list[dict[str, Any]],
    composition_id: str,
    layer_index: int,
) -> dict[str, Any]:
    """Chord callback fired after every step in the layer at
    ``layer_index`` reaches terminal state (SUCCEEDED or FAILED).

    Decides, from a fresh DB read of the composition + steps:

    * Composition already terminal → no-op ``already_finalized``.
      Handles duplicate coordinators + double-dispatch races.
    * Malformed DAG → finalize FAILED with an operator-readable
      error. Defense-in-depth: P2.A's builder already validated
      shape at dispatch time.
    * Any step FAILED anywhere → finalize (PARTIAL/FAILED). Do
      NOT dispatch subsequent layers; dependents would only
      fail input resolution against the missing upstream.
    * All steps SUCCEEDED → finalize COMPLETED (wire
      final_asset, aggregate chunks, refresh cost).
    * Otherwise → dispatch the next layer whose steps still
      have PENDING work via ``chord(group, coordinator)``.

    The ``results`` arg is not consulted for the decision — a
    fresh DB read is authoritative (avoids races with any
    in-flight resume/retry that changed step status between
    dispatch and callback).
    """
    composition = Composition.objects.filter(pk=composition_id).first()
    if composition is None:
        logger.error(
            "coordinator: composition=%s not found", composition_id,
        )
        return {
            "composition_id": composition_id,
            "status": "not_found",
        }

    if composition.status in (
        CompositionStatus.COMPLETED,
        CompositionStatus.PARTIAL,
        CompositionStatus.FAILED,
    ):
        logger.info(
            "coordinator: composition=%s already finalized status=%s "
            "— no-op",
            composition_id, composition.status,
        )
        return {
            "composition_id": composition_id,
            "status": "already_finalized",
            "final_status": composition.status,
            "layer_index": layer_index,
        }

    steps = list(composition.steps.all().order_by("position"))

    try:
        layers = compute_execution_layers(steps)
    except DagValidationError as exc:
        logger.error(
            "coordinator: composition=%s DAG validation failed: %s",
            composition_id, exc,
        )
        return _finalize_parallel_composition(
            composition, steps,
            forced_status=CompositionStatus.FAILED,
            error_message=f"DAG validation: {exc}",
        )

    any_failed = any(s.status == StepStatus.FAILED for s in steps)
    all_succeeded = steps and all(
        s.status == StepStatus.SUCCEEDED for s in steps
    )

    if any_failed or all_succeeded:
        return _finalize_parallel_composition(composition, steps)

    # More work to do. Find the first layer with at least one
    # non-SUCCEEDED step and dispatch its unsatisfied members.
    satisfied_positions = {
        s.position for s in steps if s.status == StepStatus.SUCCEEDED
    }
    step_ids_by_position = {s.position: str(s.id) for s in steps}

    next_layer_positions: list[int] = []
    next_layer_index_actual = layer_index + 1
    for i, layer in enumerate(layers):
        pending_in_layer = [
            pos for pos in layer if pos not in satisfied_positions
        ]
        if pending_in_layer:
            next_layer_positions = pending_in_layer
            next_layer_index_actual = i
            break

    if not next_layer_positions:
        # Every layer is fully satisfied but the composition
        # isn't COMPLETED yet — treat as done. Shouldn't happen
        # given the all_succeeded branch above; keep as
        # defense-in-depth.
        return _finalize_parallel_composition(composition, steps)

    next_step_ids = [
        step_ids_by_position[pos] for pos in next_layer_positions
    ]
    _dispatch_layer(
        composition_id, next_step_ids, next_layer_index_actual,
    )

    logger.info(
        "coordinator: composition=%s dispatched layer=%d positions=%s",
        composition_id, next_layer_index_actual, next_layer_positions,
    )

    return {
        "composition_id": composition_id,
        "status": "dispatched_next_layer",
        "layer_index": next_layer_index_actual,
        "positions": next_layer_positions,
    }


# ---- P2.G: parallel dispatch entry point ------------------
#
# The sequential path stays the default. ``execute_composition``
# consults ``_should_use_parallel_execution`` immediately after
# the terminal-state idempotency checks; if it returns True we
# hand off to ``_dispatch_composition_parallel`` and return. That
# helper flips the composition to RUNNING (same semantics as the
# sequential path), computes execution layers via P2.A, and fires
# the FIRST layer as a ``chord(group, coordinator)`` — the
# coordinator recurses on itself for every subsequent layer, so
# this helper never touches Celery again for a single composition.
#
# Rollback: ``settings.COMPOSITION_PARALLEL_EXECUTION_ENABLED``
# defaults False. Setting it False mid-run does not affect
# already-dispatched compositions — the coordinator chain
# terminates naturally on fan-in.


def _should_use_parallel_execution(composition: Composition) -> bool:
    """Return True iff the parallel dispatch path should own this
    composition's run.

    Two gates in AND:

    * ``settings.COMPOSITION_PARALLEL_EXECUTION_ENABLED`` — master
      kill switch. False by default; flipping to True does not
      enable parallelism for any recipe unless the second gate
      also permits it.
    * ``composition.template_kind`` in
      ``settings.COMPOSITION_PARALLEL_EXECUTION_KINDS`` — per-
      recipe allow-list, initially ``{"dialogue_scene"}``.
    """
    if not getattr(
        settings, "COMPOSITION_PARALLEL_EXECUTION_ENABLED", False,
    ):
        return False
    allowed = getattr(
        settings, "COMPOSITION_PARALLEL_EXECUTION_KINDS", set(),
    )
    return composition.template_kind in allowed


def _dispatch_composition_parallel(
    composition: Composition,
) -> dict[str, Any]:
    """Parallel-path entry — flip composition to RUNNING, compute
    layers, dispatch the first layer's PENDING steps as a chord.

    Only called by ``execute_composition`` after the sequential-
    path terminal-state idempotency checks have already run. The
    ``COMPLETED`` / ``FAILED-no-retry`` no-ops therefore fire in
    the parent regardless of dispatch mode.

    * Empty composition (no steps) → finalize COMPLETED
      immediately. Consistent with the sequential path returning
      ``steps_succeeded=0`` on an empty step list.
    * Malformed DAG → finalize FAILED via
      ``_finalize_parallel_composition`` (data-driven error).
    * All steps already SUCCEEDED (resumed after crash where
      steps ran but composition wasn't finalized) → finalize
      COMPLETED without re-dispatch.
    * Otherwise → flip to RUNNING, dispatch first pending
      layer, return ``dispatched``.
    """
    composition_id = str(composition.id)

    composition.status = CompositionStatus.RUNNING
    composition.error_message = ""
    composition.save(
        update_fields=["status", "error_message", "updated_at"],
    )

    steps = list(composition.steps.all().order_by("position"))
    if not steps:
        composition.status = CompositionStatus.COMPLETED
        composition.save(update_fields=["status", "updated_at"])
        logger.info(
            "execute_composition[parallel]: composition=%s COMPLETED (empty)",
            composition_id,
        )
        return {
            "composition_id": composition_id,
            "status": "completed",
            "steps_succeeded": 0,
            "cost_actual_micros": composition.cost_actual_micros,
        }

    try:
        layers = compute_execution_layers(steps)
    except DagValidationError as exc:
        logger.error(
            "execute_composition[parallel]: composition=%s DAG "
            "validation failed: %s",
            composition_id, exc,
        )
        return _finalize_parallel_composition(
            composition, steps,
            forced_status=CompositionStatus.FAILED,
            error_message=f"DAG validation: {exc}",
        )

    satisfied_positions = {
        s.position for s in steps if s.status == StepStatus.SUCCEEDED
    }
    step_ids_by_position = {s.position: str(s.id) for s in steps}

    first_layer_positions: list[int] = []
    first_layer_index = 0
    for i, layer in enumerate(layers):
        pending = [
            pos for pos in layer if pos not in satisfied_positions
        ]
        if pending:
            first_layer_positions = pending
            first_layer_index = i
            break

    if not first_layer_positions:
        # Every step already SUCCEEDED — finalize without dispatch.
        return _finalize_parallel_composition(composition, steps)

    first_step_ids = [
        step_ids_by_position[pos] for pos in first_layer_positions
    ]
    _dispatch_layer(composition_id, first_step_ids, first_layer_index)

    logger.info(
        "execute_composition[parallel]: composition=%s dispatched "
        "layer=%d positions=%s",
        composition_id, first_layer_index, first_layer_positions,
    )

    return {
        "composition_id": composition_id,
        "status": "dispatched",
        "first_layer_index": first_layer_index,
        "first_layer_positions": first_layer_positions,
    }


# ---- expired-asset sweep ----------------------------------
#
# SESSION 210 — closes the last queued SESSION 209 calibration
# finding (expired-asset accumulation). Runway's Cloudfront URLs
# carry a JWT ``exp`` claim in their query string; once it's
# past the SPA still shows the Composition row as having a
# deliverable, but clicking it 404s. This periodic sweep walks
# the Asset table, classifies each row via
# ``compute_storage_health``, and on ``HTTPS_EXPIRED`` it
# detaches the Composition's ``final_asset`` link. The Asset row
# itself is left intact — its cost_micros + asset_type are
# still useful provenance, and the Asset Library v1 UI surfaces
# the expired badge so the operator sees the history.
#
# Cadence is configured in ``character_os/settings.py`` via
# ``CELERY_BEAT_SCHEDULE``. Hourly is the default — the JWT
# window is 24h so checking once per hour is plenty of
# headroom without thrashing the table.


def run_expired_asset_sweep(*, commit: bool = True) -> dict[str, Any]:
    """Core sweep logic — shared by the Celery task + the
    operator-facing ``sweep_expired_assets`` management command.

    Walks every HTTPS Asset, classifies via
    ``compute_storage_health``, and on ``HTTPS_EXPIRED`` detaches
    the Composition's ``final_asset`` FK. With ``commit=False`` it
    performs the scan but skips the write — useful for the
    management command's default dry-run.

    Returns:
        {
            "scanned": int,          # HTTPS assets considered
            "expired": int,          # rows with HTTPS_EXPIRED
            "detached": int,         # Composition.final_asset SET_NULL'd
            "expired_asset_ids": list[str],  # for the command's report
            "committed": bool,
        }
    """
    scanned = 0
    expired_asset_ids: list[str] = []

    # Only HTTPS assets can carry a JWT exp; everything else
    # (local files, data URIs, transcripts) can't expire by
    # this mechanism. Filter at the DB level so we don't fetch
    # the whole Asset table.
    qs = Asset.objects.filter(
        file_path__startswith="https://",
    ).only("id", "file_path")

    for asset in qs.iterator(chunk_size=200):
        scanned += 1
        if compute_storage_health(asset) == StorageHealth.HTTPS_EXPIRED:
            expired_asset_ids.append(str(asset.id))

    detached = 0
    if commit and expired_asset_ids:
        # SET_NULL each Composition.final_asset that points at an
        # expired row. Done in a single update for atomicity +
        # to avoid loading the Composition objects into memory.
        detached = Composition.objects.filter(
            final_asset_id__in=expired_asset_ids,
        ).update(final_asset=None, updated_at=timezone.now())

    return {
        "scanned": scanned,
        "expired": len(expired_asset_ids),
        "detached": detached,
        "expired_asset_ids": expired_asset_ids,
        "committed": commit,
    }


@shared_task(
    name="apps.compositions.tasks.sweep_expired_assets",
    ignore_result=False,
)
def sweep_expired_assets() -> dict[str, Any]:
    """Detach ``Composition.final_asset`` for every Composition
    whose final asset's storage health classifies as
    ``HTTPS_EXPIRED``.

    Returns a small status dict (Celery result + handy for the
    Beat log line):

        {
            "scanned": int,     # HTTPS assets considered
            "expired": int,     # rows with HTTPS_EXPIRED
            "detached": int,    # Composition.final_asset SET_NULL'd
        }

    Idempotent — a second run on the same set is a no-op
    because the FKs already point at NULL.
    """
    result = run_expired_asset_sweep(commit=True)

    if result["expired"]:
        logger.info(
            "sweep_expired_assets: scanned=%d expired=%d detached=%d",
            result["scanned"], result["expired"], result["detached"],
        )
    else:
        logger.debug(
            "sweep_expired_assets: scanned=%d expired=0 detached=0",
            result["scanned"],
        )

    # Trim the asset-id list from the Celery result (Beat log line
    # is cleaner without it; the command surface keeps the full
    # dict for the operator report).
    return {
        "scanned": result["scanned"],
        "expired": result["expired"],
        "detached": result["detached"],
    }
