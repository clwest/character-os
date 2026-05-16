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

from celery import shared_task
from django.db import transaction
from django.utils import timezone

from .cost import refresh_composition_cost_actual
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
    composition.save(
        update_fields=["final_asset", "status", "updated_at"],
    )
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
    """
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
        # W11.6.5.3 (SESSION 174) — auto-title from the parent
        # composition's name so the SPA asset_picker dropdowns
        # render readable labels instead of CDN URL tails
        # (e.g. "Talking-head — Marcus" vs
        # "5cf5ab4e-0398-480c-b33b-f994f567ccc1.mp4?_jwt=eyJh…").
        # Multi-step compositions get the same title across
        # step outputs in v1; per-step disambiguation can land
        # later if operators ask for it.
        title=(composition.name or "")[:120],
    )


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
