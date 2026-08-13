"""Benchmark matrix runner — 8.b orchestration.

Takes the deterministic configuration produced by 8.a, executes the
requested matrix through ``PortraitProvider`` + ``NormalizationPipeline``,
writes immutable two-tier evidence under the ratified §17.8.a
fixture-runs layout, and produces a top-level ``run_summary.json``.

Load-bearing rules (operator disciplines #1–#15):

* Every cell executes independently. A factual per-cell failure
  (unavailable / request-failed / unsupported / normalization-failed)
  is recorded and the run continues. Only genuine
  harness/programming/infrastructure failures may abort the run,
  and even then the summary must record which cells were
  ``not_attempted_due_to_fatal_run_error``.

* Raw provider bytes are written FIRST, byte-for-byte, before
  normalization is invoked. A normalization failure never destroys
  raw evidence.

* Prompt is provider-neutral — the same cell handed to two
  providers gets the same final prompt (enforced by construction:
  runner calls ``build_prompt(fixture, direction, purpose)`` with
  no provider input).

* No qualification vocabulary. Every emitted field is factual
  (outcome names describe what happened operationally — never
  "good," "preferred," "selected," etc.).

* No substrate persistence — evidence is file-only, shaped so
  Step 9 can promote candidates without reinterpretation.

* No writes to ``bootstrap/references/`` or ``scores/``.

* Run identity is append-only: the writer refuses if the run_id
  directory already exists.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from ...config import Settings
from ..normalization import (
    BackgroundFamily,
    NormalizationPipeline,
    NormalizationSpec,
    PipelineError,
    PipelineInputError,
    PipelineStageError,
    SurfaceProfile,
    load_background_family,
    load_surface_profile,
)
from ..normalization.stages.background_replacement import BackgroundReplacementStage
from ..normalization.stages.crop import CropStage
from ..normalization.stages.framing import FramingStage

from .evidence_paths import EvidenceLayout, cell_id_for
from .evidence_writer import (
    EvidenceWriter,
    WrittenArtifact,
)
from .fixture_loader import LoadedFixture, default_fixtures_root
from .matrix import CellKey, MatrixAxes, expand_matrix
from .prompt_builder import PROMPT_BUILDER_VERSION
from .provider_dispatcher import (
    CELL_OUTCOME_NORMALIZATION_FAILED,
    CELL_OUTCOME_SUCCESS,
    CellProviderResult,
    ProviderFactory,
    capabilities_to_dict,
    default_provider_factory,
    dispatch_cell,
    execution_mode_actual_str,
    provider_name_str,
)
from .run_identity import RunIdentity, mint_run_identity
from .version import HARNESS_SCHEMA_VERSION
from .vocabulary import IdentityBranch


# ---- Cell / run result dataclasses ---------------------------


@dataclass(frozen=True, slots=True)
class CellRunResult:
    """Return shape of one cell's full execution (provider + normalization).

    ``outcome`` is the final cell-level status — one of the ratified
    taxonomy strings. ``provider_stage`` and ``normalization_stage``
    dicts are the same shape that lands in candidate.json.
    """

    cell: CellKey
    outcome: str
    candidate_artifact: WrittenArtifact
    raw_artifact: WrittenArtifact | None
    normalized_artifact: WrittenArtifact | None
    manifest_artifact: WrittenArtifact | None
    stable_failure_code: str | None
    error_message: str | None


@dataclass(frozen=True, slots=True)
class RunResult:
    """Return shape of a full harness run."""

    run_identity: RunIdentity
    layout: EvidenceLayout
    cell_results: tuple[CellRunResult, ...]
    fatal_run_error: str | None
    counts_by_outcome: Mapping[str, int]
    started_at_utc: datetime
    ended_at_utc: datetime


# ---- Failure-code extraction (stable domain codes) -----------

# Pipeline stage exception messages carry stable domain codes as
# substrings. Extract them into a dedicated field on evidence so
# Step 9 consumers do not need to parse messages.

_STABLE_FAILURE_CODES: tuple[str, ...] = (
    # From FramingStage upscale refusal.
    "input_smaller_than_output",
    # From FramingStage aspect mismatch.
    "aspect_ratio_mismatch",
    # From BackgroundReplacementStage.
    "background_replacement_failed",
    # Pipeline-level input errors.
    "surface_profile",
    "background_id",
)


def _extract_stable_failure_code(message: str) -> str | None:
    """Return the first matching stable failure code substring
    found in ``message``, or None if none matches. Deterministic:
    order matches ``_STABLE_FAILURE_CODES``."""
    for code in _STABLE_FAILURE_CODES:
        if code in message:
            return code
    return None


# ---- Precomputed run-scope helpers ---------------------------


def _load_profiles(
    profile_ids: Sequence[str],
) -> dict[str, SurfaceProfile]:
    return {pid: load_surface_profile(pid) for pid in profile_ids}


def _default_v1_pipeline() -> NormalizationPipeline:
    """The ratified default v1 chain from SESSION 246 7.c close.
    Kept as one function so if the chain ever changes, the runner
    picks up the new composition."""
    return NormalizationPipeline(
        stages=[CropStage(), FramingStage(), BackgroundReplacementStage()],
    )


def _pipeline_versions_by_profile(
    profiles: Mapping[str, SurfaceProfile],
    family: BackgroundFamily,
) -> dict[str, str]:
    """Compute the pipeline_version string per profile — reused
    by the fingerprint AND recorded verbatim on every cell's
    evidence."""
    pipeline = _default_v1_pipeline()
    return {
        pid: pipeline.pipeline_version(profile, family)
        for pid, profile in profiles.items()
    }


# ---- Candidate JSON assembly (single canonical shape) -------


def _build_candidate_payload(
    *,
    run_identity: RunIdentity,
    cell: CellKey,
    cell_id_str: str,
    fixture: LoadedFixture,
    provider_result: CellProviderResult,
    raw_artifact: WrittenArtifact | None,
    normalization_stage: dict[str, Any],
    cell_outcome: str,
    written_at_utc: datetime,
) -> dict[str, Any]:
    """Assemble the canonical candidate.json payload.

    Fields cover every operator-mandated Step-9 promotion input:
    fixture identity + provider provenance + execution-mode
    visibility + prompt + raw hash/path + normalization outcome +
    stable failure code + non-human marker.
    """
    provider_response = provider_result.provider_response
    is_non_human = fixture.branch == IdentityBranch.NON_HUMAN

    provider_stage: dict[str, Any] = {
        "outcome": provider_result.outcome,
        "requested_execution_mode": provider_result.requested_execution_mode,
        "provider_model_override": provider_result.provider_model_override,
        "prompt": provider_result.final_prompt,
        "deterministic_seed": provider_result.deterministic_seed,
        "capabilities": (
            capabilities_to_dict(provider_result.capabilities_snapshot)
            if provider_result.capabilities_snapshot is not None
            else None
        ),
        "error": (
            {
                "class": provider_result.error_class,
                "message": provider_result.error_message,
            }
            if provider_result.error_class is not None
            else None
        ),
    }
    if provider_response is not None:
        provider_stage.update(
            {
                "provider": provider_name_str(provider_response.provider),
                "provider_model": provider_response.provider_model,
                "actual_execution_mode": execution_mode_actual_str(
                    provider_response.execution_mode_actual
                ),
                "prompt_snapshot": dict(provider_response.prompt_snapshot),
                "elapsed_ms": provider_response.elapsed_ms,
            }
        )
    else:
        provider_stage.update(
            {
                "provider": cell.provider,  # requested name; adapter did not run to completion
                "provider_model": None,
                "actual_execution_mode": None,
                "prompt_snapshot": None,
                "elapsed_ms": None,
            }
        )

    raw_evidence: dict[str, Any] | None
    if raw_artifact is not None:
        raw_evidence = {
            "relative_path": raw_artifact.relative_from_fixtures_root,
            "sha256_hex": raw_artifact.sha256_hex,
            "byte_count": raw_artifact.byte_count,
        }
    else:
        raw_evidence = None

    payload = {
        "harness_schema_version": HARNESS_SCHEMA_VERSION,
        "prompt_builder_version": PROMPT_BUILDER_VERSION,
        "run": {
            "run_id": run_identity.run_id,
            "run_fingerprint": run_identity.run_fingerprint,
            "run_kind": run_identity.run_kind,
        },
        "cell": {
            "fixture_id": cell.fixture_id,
            "direction": cell.direction,
            "reference_kind": cell.reference_kind,
            "reference_purpose": cell.reference_purpose,
            "provider": cell.provider,
            "surface_profile": cell.surface_profile,
            "cell_id": cell_id_str,
        },
        "identity": {
            "branch": fixture.branch.value,
            "spec_schema_version": fixture.fixture_version,
            "fixture_content_hash": fixture.content_hash,
        },
        "not_applicable_unscored": is_non_human,
        "outcome": cell_outcome,
        "provider_stage": provider_stage,
        "raw_artifact": raw_evidence,
        "normalization_stage": normalization_stage,
        "written_at_utc": written_at_utc.isoformat(),
    }
    return payload


# ---- Per-cell orchestration ----------------------------------


def _run_one_cell(
    *,
    cell: CellKey,
    fixture: LoadedFixture,
    surface_profile: SurfaceProfile,
    pipeline_version: str,
    family: BackgroundFamily,
    run_identity: RunIdentity,
    execution_mode: str,
    provider_models: Mapping[str, str] | None,
    settings: Settings,
    provider_factory: ProviderFactory,
    writer: EvidenceWriter,
    layout: EvidenceLayout,
) -> CellRunResult:
    """Execute one cell + write all four artifact types.

    Every path — success, provider failure, normalization failure
    — writes:
      * candidate.json (always)
      * raw/<cell_id>.png (when provider produced bytes)
      * normalized/<cell_id>.png (only on norm success)
      * manifests/<cell_id>.json (only when norm ran; success or
        failure is captured in the normalization_stage record,
        not by manifest presence)

    Observations bucket is created as an empty marker file so a
    future consumer sees intentional emptiness.
    """
    cell_id_str = cell_id_for(cell)
    provider_model_override = None
    if provider_models is not None:
        provider_model_override = provider_models.get(cell.provider)

    # 1. Provider stage.
    provider_result = dispatch_cell(
        cell=cell,
        fixture=fixture,
        surface_profile=surface_profile,
        run_fingerprint=run_identity.run_fingerprint,
        cell_id=cell_id_str,
        execution_mode=execution_mode,
        provider_model_override=provider_model_override,
        settings=settings,
        provider_factory=provider_factory,
    )

    # 2. Raw evidence FIRST — never mutated / transcoded.
    raw_artifact: WrittenArtifact | None = None
    if provider_result.raw_image_bytes is not None:
        raw_artifact = writer.write_binary(
            layout.raw_artifact_path(cell),
            provider_result.raw_image_bytes,
        )

    # 3. Observations marker (always).
    writer.create_empty_marker(layout.observations_marker_path(cell))

    # 4. Normalization stage.
    normalized_artifact: WrittenArtifact | None = None
    manifest_artifact: WrittenArtifact | None = None
    cell_outcome: str
    stable_failure_code: str | None = None
    error_message: str | None = provider_result.error_message
    normalization_stage: dict[str, Any]

    if provider_result.raw_image_bytes is None:
        # Provider stage failed — nothing to normalize.
        cell_outcome = provider_result.outcome
        normalization_stage = {
            "attempted": False,
            "outcome": "not_attempted",
            "pipeline_version": None,
            "surface_profile_id": cell.surface_profile,
            "surface_profile_version": surface_profile.version,
            "background_id": None,
            "failure": None,
            "manifest_payload": None,
        }
    else:
        # Attempt normalization on the raw bytes.
        pipeline = _default_v1_pipeline()
        norm_spec = NormalizationSpec(
            raw_bytes=provider_result.raw_image_bytes,
            surface_profile_id=cell.surface_profile,
        )
        try:
            norm_result = pipeline.run(norm_spec)
        except PipelineStageError as exc:
            cell_outcome = CELL_OUTCOME_NORMALIZATION_FAILED
            stable_failure_code = _extract_stable_failure_code(str(exc))
            error_message = str(exc)
            normalization_stage = {
                "attempted": True,
                "outcome": "failed",
                "pipeline_version": pipeline_version,
                "surface_profile_id": cell.surface_profile,
                "surface_profile_version": surface_profile.version,
                "background_id": None,
                "failure": {
                    "stage_name": exc.stage_name,
                    "stable_code": stable_failure_code,
                    "message": str(exc),
                },
                "manifest_payload": None,
            }
        except PipelineInputError as exc:
            cell_outcome = CELL_OUTCOME_NORMALIZATION_FAILED
            stable_failure_code = _extract_stable_failure_code(str(exc))
            error_message = str(exc)
            normalization_stage = {
                "attempted": True,
                "outcome": "failed",
                "pipeline_version": pipeline_version,
                "surface_profile_id": cell.surface_profile,
                "surface_profile_version": surface_profile.version,
                "background_id": None,
                "failure": {
                    "stage_name": None,
                    "stable_code": stable_failure_code,
                    "message": str(exc),
                },
                "manifest_payload": None,
            }
        except PipelineError as exc:
            cell_outcome = CELL_OUTCOME_NORMALIZATION_FAILED
            error_message = str(exc)
            normalization_stage = {
                "attempted": True,
                "outcome": "failed",
                "pipeline_version": pipeline_version,
                "surface_profile_id": cell.surface_profile,
                "surface_profile_version": surface_profile.version,
                "background_id": None,
                "failure": {
                    "stage_name": None,
                    "stable_code": None,
                    "message": str(exc),
                },
                "manifest_payload": None,
            }
        else:
            # SUCCESS — normalization completed. Write normalized
            # + manifest artifacts.
            normalized_artifact = writer.write_binary(
                layout.normalized_artifact_path(cell),
                norm_result.normalized_bytes,
            )
            manifest_artifact = writer.write_json(
                layout.normalization_manifest_path(cell),
                norm_result.manifest,
            )
            cell_outcome = CELL_OUTCOME_SUCCESS
            normalization_stage = {
                "attempted": True,
                "outcome": "success",
                "pipeline_version": norm_result.manifest["pipeline_version"],
                "surface_profile_id": norm_result.manifest["surface_profile_id"],
                "surface_profile_version": norm_result.manifest["surface_profile_version"],
                "background_id": norm_result.manifest["background_id"],
                "failure": None,
                "manifest_payload": norm_result.manifest,
            }

    # 5. Attach normalized/manifest paths to normalization_stage if written.
    if normalized_artifact is not None:
        normalization_stage["normalized_artifact"] = {
            "relative_path": normalized_artifact.relative_from_fixtures_root,
            "sha256_hex": normalized_artifact.sha256_hex,
            "byte_count": normalized_artifact.byte_count,
        }
    else:
        normalization_stage["normalized_artifact"] = None
    if manifest_artifact is not None:
        normalization_stage["manifest_artifact"] = {
            "relative_path": manifest_artifact.relative_from_fixtures_root,
            "sha256_hex": manifest_artifact.sha256_hex,
            "byte_count": manifest_artifact.byte_count,
        }
    else:
        normalization_stage["manifest_artifact"] = None

    # 6. Candidate JSON — the single canonical evidence locator.
    candidate_payload = _build_candidate_payload(
        run_identity=run_identity,
        cell=cell,
        cell_id_str=cell_id_str,
        fixture=fixture,
        provider_result=provider_result,
        raw_artifact=raw_artifact,
        normalization_stage=normalization_stage,
        cell_outcome=cell_outcome,
        written_at_utc=datetime.now(timezone.utc),
    )
    candidate_artifact = writer.write_json(
        layout.candidate_json_path(cell),
        candidate_payload,
    )

    return CellRunResult(
        cell=cell,
        outcome=cell_outcome,
        candidate_artifact=candidate_artifact,
        raw_artifact=raw_artifact,
        normalized_artifact=normalized_artifact,
        manifest_artifact=manifest_artifact,
        stable_failure_code=stable_failure_code,
        error_message=error_message,
    )


# ---- Run summary assembly ----------------------------------


_CONTAINS_REAL_EXECUTION_MODES: frozenset[str] = frozenset({"real_required", "auto"})


def _build_run_summary(
    *,
    run_identity: RunIdentity,
    execution_mode: str,
    axes: MatrixAxes,
    fixtures: Sequence[LoadedFixture],
    provider_models: Mapping[str, str] | None,
    surface_profile_versions: Mapping[str, int],
    background_family_schema_hash: str,
    pipeline_versions: Mapping[str, str],
    planned_cells: Sequence[CellKey],
    cell_results: Sequence[CellRunResult],
    fatal_run_error: str | None,
    started_at_utc: datetime,
    ended_at_utc: datetime,
) -> dict[str, Any]:
    """Assemble ``run_summary.json``. Records every fact needed for
    Step 9 to make sense of the run without opening individual
    candidate files (though the candidate.json files remain the
    authoritative per-cell records)."""
    completed_cells = {cr.cell: cr for cr in cell_results}
    counts_by_outcome: dict[str, int] = {}
    counts_by_provider: dict[str, dict[str, int]] = {}
    counts_by_profile: dict[str, dict[str, int]] = {}
    counts_by_direction: dict[str, dict[str, int]] = {}

    planned_cell_records: list[dict[str, Any]] = []
    for cell in planned_cells:
        result = completed_cells.get(cell)
        if result is not None:
            status = result.outcome
        else:
            status = "not_attempted_due_to_fatal_run_error"
        counts_by_outcome[status] = counts_by_outcome.get(status, 0) + 1
        counts_by_provider.setdefault(cell.provider, {})
        counts_by_provider[cell.provider][status] = (
            counts_by_provider[cell.provider].get(status, 0) + 1
        )
        counts_by_profile.setdefault(cell.surface_profile, {})
        counts_by_profile[cell.surface_profile][status] = (
            counts_by_profile[cell.surface_profile].get(status, 0) + 1
        )
        counts_by_direction.setdefault(cell.direction, {})
        counts_by_direction[cell.direction][status] = (
            counts_by_direction[cell.direction].get(status, 0) + 1
        )
        planned_cell_records.append(
            {
                "cell": {
                    "fixture_id": cell.fixture_id,
                    "direction": cell.direction,
                    "reference_kind": cell.reference_kind,
                    "reference_purpose": cell.reference_purpose,
                    "provider": cell.provider,
                    "surface_profile": cell.surface_profile,
                    "cell_id": cell_id_for(cell),
                },
                "status": status,
                "stable_failure_code": (
                    result.stable_failure_code if result is not None else None
                ),
                "error_message": (
                    result.error_message if result is not None else None
                ),
            }
        )

    contains_real_execution = execution_mode in _CONTAINS_REAL_EXECUTION_MODES

    fixture_records = [
        {
            "fixture_id": fx.fixture_id,
            "branch": fx.branch.value,
            "spec_schema_version": fx.fixture_version,
            "content_hash": fx.content_hash,
        }
        for fx in sorted(fixtures, key=lambda f: f.fixture_id)
    ]

    return {
        "harness_schema_version": HARNESS_SCHEMA_VERSION,
        "prompt_builder_version": PROMPT_BUILDER_VERSION,
        "run": {
            "run_id": run_identity.run_id,
            "run_fingerprint": run_identity.run_fingerprint,
            "run_kind": run_identity.run_kind,
            "created_at_utc": run_identity.created_at_utc.isoformat(),
        },
        "started_at_utc": started_at_utc.isoformat(),
        "ended_at_utc": ended_at_utc.isoformat(),
        "execution_mode": {
            "requested": execution_mode,
            "contains_real_execution": contains_real_execution,
            "notice": (
                "Mock-only harness-mechanics evidence. Do not present as "
                "qualification evidence per SESSION 244 constraint 7 and "
                "SESSION 247 operator discipline #6."
                if not contains_real_execution
                else "Contains real-provider execution. Individual candidates "
                     "record execution_mode_actual per adapter; only records "
                     "with actual=real are candidate qualification evidence."
            ),
        },
        "qualification_status": "not_evaluated",
        "reproducibility": {
            "axes": {
                "fixture_ids": list(axes.fixture_ids),
                "directions": list(axes.directions),
                "purposes_by_branch": {
                    branch.value: list(purposes)
                    for branch, purposes in sorted(
                        axes.purposes_by_branch.items(),
                        key=lambda kv: kv[0].value,
                    )
                },
                "providers": list(axes.providers),
                "surface_profiles": list(axes.surface_profiles),
            },
            "provider_models": (
                dict(provider_models) if provider_models is not None else None
            ),
            "surface_profile_versions": dict(surface_profile_versions),
            "background_family_schema_hash": background_family_schema_hash,
            "pipeline_versions": dict(pipeline_versions),
        },
        "fixtures": fixture_records,
        "counts": {
            "planned": len(planned_cells),
            "by_outcome": counts_by_outcome,
            "by_provider": counts_by_provider,
            "by_profile": counts_by_profile,
            "by_direction": counts_by_direction,
        },
        "planned_cells": planned_cell_records,
        "fatal_run_error": fatal_run_error,
    }


# ---- Public entry point -------------------------------------


def run_matrix(
    *,
    fixtures: Iterable[LoadedFixture],
    axes: MatrixAxes,
    execution_mode: str = "forced_mock",
    provider_models: Mapping[str, str] | None = None,
    fixtures_root: Path | None = None,
    settings: Settings | None = None,
    provider_factory: ProviderFactory | None = None,
    now: datetime | None = None,
) -> RunResult:
    """Execute one benchmark harness run.

    Returns a ``RunResult`` and writes:
      * ``fixtures/_runs/<run_id>/run_summary.json``
      * per-cell candidate + raw + (normalized + manifest on success)
        under ``fixtures/<fixture_id>/runs/<run_id>/<direction>/<provider>/``

    Never mutates a prior run — refuses immediately if the run_id
    is already on disk (per operator discipline #4).

    ``fixtures_root`` — where evidence writes (also the ratified
    read root for fixture identity). Defaults to the ratified
    ``docs/design/visual/portrait_qualification/fixtures/``.

    ``settings`` — media-engine Settings; default constructs a
    fresh instance. Provider adapters may consult it for API
    keys / force-mock env vars.

    ``provider_factory`` — override for tests. Production callers
    leave None and receive ``portrait_provider.get_provider``.
    """
    if fixtures_root is None:
        fixtures_root = default_fixtures_root()
    if settings is None:
        settings = Settings()
    if provider_factory is None:
        provider_factory = default_provider_factory

    fixtures_seq = tuple(fixtures)

    # 1. Load pipeline-scope data + compute per-profile
    #    pipeline_version strings.
    surface_profiles = _load_profiles(axes.surface_profiles)
    family = load_background_family()
    pipeline_versions = _pipeline_versions_by_profile(surface_profiles, family)
    profile_versions = {
        pid: profile.version for pid, profile in surface_profiles.items()
    }

    # 2. Mint the run_identity. Same-config-different-time
    #    produces the same fingerprint per 8.a.
    run_identity = mint_run_identity(
        kind="bootstrap",
        fixtures=fixtures_seq,
        axes=axes,
        provider_models=provider_models,
        surface_profile_versions=profile_versions,
        background_family_schema_hash=family.schema_hash,
        pipeline_versions=pipeline_versions,
        prompt_builder_version=PROMPT_BUILDER_VERSION,
        execution_mode=execution_mode,
        harness_schema_version=HARNESS_SCHEMA_VERSION,
        now=now,
    )

    layout = EvidenceLayout(fixtures_root=fixtures_root, run_id=run_identity.run_id)

    # 3. Instantiate writer — this refuses if run_id already exists
    #    (operator discipline #4). Refusal propagates as a
    #    RunIdConflictError to the caller BEFORE any providers run.
    writer = EvidenceWriter(fixtures_root=fixtures_root, run_id=run_identity.run_id)

    # 4. Expand matrix.
    planned_cells = expand_matrix(axes, fixtures_seq)
    fixture_by_id = {fx.fixture_id: fx for fx in fixtures_seq}

    # 5. Execute each cell, capturing per-cell results. On
    #    per-cell exception (would be a harness bug), record as
    #    HARNESS_ERROR and continue. On a truly fatal condition
    #    (e.g., writer failure), record the remaining cells as
    #    not_attempted and re-raise.
    started_at_utc = datetime.now(timezone.utc)
    cell_results: list[CellRunResult] = []
    fatal_run_error: str | None = None
    fatal_exception: Exception | None = None

    for cell in planned_cells:
        try:
            fixture = fixture_by_id[cell.fixture_id]
            profile = surface_profiles[cell.surface_profile]
            pipeline_version = pipeline_versions[cell.surface_profile]
            result = _run_one_cell(
                cell=cell,
                fixture=fixture,
                surface_profile=profile,
                pipeline_version=pipeline_version,
                family=family,
                run_identity=run_identity,
                execution_mode=execution_mode,
                provider_models=provider_models,
                settings=settings,
                provider_factory=provider_factory,
                writer=writer,
                layout=layout,
            )
            cell_results.append(result)
        except (OSError, IOError) as exc:
            # Filesystem-level failure is the canonical "abort the
            # run loudly" path (operator discipline #1). Remaining
            # cells are recorded as not_attempted in the summary.
            fatal_run_error = f"{type(exc).__name__}: {exc!s}"
            fatal_exception = exc
            break

    ended_at_utc = datetime.now(timezone.utc)

    # 6. Write run_summary.json.
    summary_payload = _build_run_summary(
        run_identity=run_identity,
        execution_mode=execution_mode,
        axes=axes,
        fixtures=fixtures_seq,
        provider_models=provider_models,
        surface_profile_versions=profile_versions,
        background_family_schema_hash=family.schema_hash,
        pipeline_versions=pipeline_versions,
        planned_cells=planned_cells,
        cell_results=cell_results,
        fatal_run_error=fatal_run_error,
        started_at_utc=started_at_utc,
        ended_at_utc=ended_at_utc,
    )
    writer.write_json(layout.run_summary_path, summary_payload)

    counts_by_outcome = dict(summary_payload["counts"]["by_outcome"])

    result_bundle = RunResult(
        run_identity=run_identity,
        layout=layout,
        cell_results=tuple(cell_results),
        fatal_run_error=fatal_run_error,
        counts_by_outcome=counts_by_outcome,
        started_at_utc=started_at_utc,
        ended_at_utc=ended_at_utc,
    )
    if fatal_exception is not None:
        # Preserve the fatal exception's context so callers can
        # investigate. The RunResult + partial evidence are already
        # on disk.
        raise RuntimeError(
            f"benchmark run aborted due to fatal error; partial evidence "
            f"written to {layout.top_level_run_root} + fixture subtrees. "
            f"See run_summary.json for planned-vs-attempted status."
        ) from fatal_exception
    return result_bundle


__all__ = [
    "CellRunResult",
    "RunResult",
    "run_matrix",
]
