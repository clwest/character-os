"""Replay contract — ``replay_same_raw_input`` (§19 Step 8.c).

Two concepts operator-locked in the SESSION 247 8.c briefing:

* **A. ``replay_same_raw_input``** (this module) — reads raw
  provider bytes from a prior immutable evidence run, verifies
  their SHA-256 against the source candidate record, and
  re-runs the current normalization pipeline against those same
  raw bytes. Writes results into a NEW run_id under
  ``fixtures/_runs/<target_run_id>/`` + per-cell replay
  candidates under the same §17.8.a-shaped subtree. **Never
  touches ``PortraitProvider``.** Never modifies the source
  run's files.

* **B. ``regenerate_provider_output``** (NOT built here) —
  would call ``PortraitProvider`` again. Real providers may be
  nondeterministic; regeneration consistency is a Step 10
  qualification question, not a Step 8 harness determinism
  requirement.

Compatibility contract (per operator #2):

* If the source's ``pipeline_version`` matches the current
  pipeline_version:
  - normalized bytes MUST be byte-identical (fail loudly if not
    — that means the pipeline is nondeterministic).
  - deterministic manifest content MUST match (excluding
    observational timing fields).

* If the source's ``pipeline_version`` differs:
  - factually record a version-mismatch result;
  - do NOT call that a failure;
  - preserve both source + replay evidence;
  - never mutate the old run.

Source integrity (per operator #3):

* Every replay first recomputes the source raw bytes' SHA-256
  and compares against the source candidate.json's recorded
  hash. On mismatch → raise ``SourceRawHashMismatch`` (stable
  code ``source_raw_hash_mismatch``). Do not normalize altered
  bytes while presenting the result as a replay.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from ..normalization import (
    NormalizationPipeline,
    NormalizationSpec,
    PipelineError,
    PipelineInputError,
    PipelineStageError,
    load_background_family,
    load_surface_profile,
)
from ..normalization.stages.background_replacement import BackgroundReplacementStage
from ..normalization.stages.crop import CropStage
from ..normalization.stages.framing import FramingStage

from .evidence_paths import EvidenceLayout, cell_id_for
from .evidence_writer import EvidenceWriter, WrittenArtifact
from .fixture_loader import default_fixtures_root
from .matrix import CellKey
from .version import HARNESS_SCHEMA_VERSION


# ---- Errors ---------------------------------------------------


class ReplayError(Exception):
    """Base for replay-contract errors."""


class SourceRunNotFound(ReplayError):
    """The source run's ``run_summary.json`` is not present."""


class SourceEvidenceMalformed(ReplayError):
    """A source candidate.json or run_summary.json is missing
    fields the replay contract requires. Distinct from a raw-
    hash mismatch — this fires when the file itself is
    structurally broken."""


class SourceRawHashMismatch(ReplayError):
    """The raw bytes on disk hash differently than the source
    candidate recorded. Stable code: ``source_raw_hash_mismatch``.
    Refuses to normalize altered bytes while presenting the
    result as a replay of the original run."""


# ---- Result dataclasses --------------------------------------


@dataclass(frozen=True, slots=True)
class ReplayCellResult:
    """Per-cell outcome of a replay pass.

    * ``pipeline_version_match`` — True iff the source
      candidate's ``pipeline_version`` equals the current pipeline
      version for the same surface profile.
    * ``normalized_bytes_byte_identical`` — populated only when
      both source AND replay produced normalized bytes. None on
      any other path (source failed norm; replay failed norm;
      pipeline versions differ so contract does not require
      equality).
    * ``comparison_notes`` — factual short strings describing
      what was compared. NOT scoring vocabulary.
    """

    cell: CellKey
    source_pipeline_version: str | None
    current_pipeline_version: str | None
    pipeline_version_match: bool
    replay_outcome: str  # 'success' | 'normalization_failed' | 'source_raw_absent' | 'source_raw_hash_mismatch'
    source_raw_sha256: str | None
    source_normalized_sha256: str | None
    replay_normalized_sha256: str | None
    normalized_bytes_byte_identical: bool | None
    stable_failure_code: str | None
    error_message: str | None
    candidate_artifact: WrittenArtifact
    replay_normalized_artifact: WrittenArtifact | None
    replay_manifest_artifact: WrittenArtifact | None
    comparison_notes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ReplayRunResult:
    source_run_id: str
    target_run_id: str
    target_layout: EvidenceLayout
    cell_results: tuple[ReplayCellResult, ...]
    counts_by_outcome: Mapping[str, int]
    started_at_utc: datetime
    ended_at_utc: datetime


# ---- Helpers -------------------------------------------------


def _sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


_REQUIRED_CANDIDATE_FIELDS = frozenset(
    {
        "harness_schema_version",
        "prompt_builder_version",
        "run",
        "cell",
        "identity",
        "outcome",
        "provider_stage",
        "raw_artifact",
        "normalization_stage",
    }
)


def _load_source_candidate(candidate_path: Path) -> dict[str, Any]:
    if not candidate_path.is_file():
        raise SourceEvidenceMalformed(
            f"source candidate not found: {candidate_path}"
        )
    try:
        payload = json.loads(candidate_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise SourceEvidenceMalformed(
            f"source candidate not valid JSON: {candidate_path}: {exc!s}"
        ) from exc
    missing = _REQUIRED_CANDIDATE_FIELDS - set(payload.keys())
    if missing:
        raise SourceEvidenceMalformed(
            f"source candidate {candidate_path} missing required fields: "
            f"{sorted(missing)}"
        )
    return payload


def _find_source_candidates(
    fixtures_root: Path, source_run_id: str,
) -> list[Path]:
    """Enumerate every ``candidate.json`` under the source run_id
    across all fixture directories. Returns paths sorted so the
    order is deterministic."""
    matches: list[Path] = []
    for fixture_dir in sorted(fixtures_root.iterdir()):
        if not fixture_dir.is_dir():
            continue
        if fixture_dir.name == "_runs":
            continue
        run_root = fixture_dir / "runs" / source_run_id
        if not run_root.is_dir():
            continue
        # Walk direction / provider / candidates
        for direction_dir in sorted(run_root.iterdir()):
            if not direction_dir.is_dir():
                continue
            for provider_dir in sorted(direction_dir.iterdir()):
                if not provider_dir.is_dir():
                    continue
                candidates_dir = provider_dir / "candidates"
                if not candidates_dir.is_dir():
                    continue
                for f in sorted(candidates_dir.glob("*.json")):
                    matches.append(f)
    return matches


def _default_v1_pipeline() -> NormalizationPipeline:
    return NormalizationPipeline(
        stages=[CropStage(), FramingStage(), BackgroundReplacementStage()],
    )


_STABLE_FAILURE_CODES: tuple[str, ...] = (
    "input_smaller_than_output",
    "aspect_ratio_mismatch",
    "background_replacement_failed",
    "surface_profile",
    "background_id",
)


def _extract_stable_failure_code(message: str) -> str | None:
    for code in _STABLE_FAILURE_CODES:
        if code in message:
            return code
    return None


# ---- Public API ----------------------------------------------


def replay_same_raw_input(
    *,
    source_run_id: str,
    fixtures_root: Path | None = None,
    target_run_id: str | None = None,
    now: datetime | None = None,
) -> ReplayRunResult:
    """Read every candidate from the source run, verify raw
    integrity, and re-run each raw byte payload through the
    current normalization pipeline. Writes into a new run_id
    without touching any source file.

    * ``source_run_id`` — an existing run_id whose evidence
      lives under ``fixtures/<fixture>/runs/<source_run_id>/…``.
    * ``target_run_id`` — where the replay writes. If None,
      mints ``replay_<utc_iso>_of_<source_run_id_prefix>``.
    * ``fixtures_root`` — defaults to the ratified fixtures
      root; tests override with tmp_path.

    Refuses (raises ``SourceRawHashMismatch``) when a source raw
    file's on-disk SHA-256 disagrees with the recorded hash.

    Returns a ``ReplayRunResult`` describing every cell's replay
    outcome + comparison metadata.
    """
    if fixtures_root is None:
        fixtures_root = default_fixtures_root()
    assert fixtures_root is not None  # narrow for typechecker after default

    top_source = fixtures_root / "_runs" / source_run_id / "run_summary.json"
    if not top_source.is_file():
        raise SourceRunNotFound(
            f"source run summary not found: {top_source}"
        )

    if target_run_id is None:
        stamp = (now or datetime.now(timezone.utc)).astimezone(timezone.utc).strftime(
            "%Y%m%dT%H%M%SZ"
        )
        target_run_id = f"replay_{stamp}_of_{source_run_id[:16]}"

    layout = EvidenceLayout(fixtures_root=fixtures_root, run_id=target_run_id)
    writer = EvidenceWriter(fixtures_root=fixtures_root, run_id=target_run_id)

    pipeline = _default_v1_pipeline()
    family = load_background_family()

    started_at_utc = datetime.now(timezone.utc)
    cell_results: list[ReplayCellResult] = []

    for source_candidate_path in _find_source_candidates(
        fixtures_root, source_run_id,
    ):
        source_payload = _load_source_candidate(source_candidate_path)
        source_cell_dict = source_payload["cell"]
        cell = CellKey(
            fixture_id=source_cell_dict["fixture_id"],
            direction=source_cell_dict["direction"],
            reference_kind=source_cell_dict["reference_kind"],
            reference_purpose=source_cell_dict["reference_purpose"],
            provider=source_cell_dict["provider"],
            surface_profile=source_cell_dict["surface_profile"],
        )
        result = _replay_one_cell(
            source_candidate_path=source_candidate_path,
            source_payload=source_payload,
            cell=cell,
            fixtures_root=fixtures_root,
            pipeline=pipeline,
            family=family,
            writer=writer,
            layout=layout,
            source_run_id=source_run_id,
            target_run_id=target_run_id,
        )
        cell_results.append(result)

    ended_at_utc = datetime.now(timezone.utc)

    counts_by_outcome: dict[str, int] = {}
    for r in cell_results:
        counts_by_outcome[r.replay_outcome] = (
            counts_by_outcome.get(r.replay_outcome, 0) + 1
        )

    replay_summary_payload = {
        "harness_schema_version": HARNESS_SCHEMA_VERSION,
        "kind": "replay_same_raw_input",
        "source_run_id": source_run_id,
        "target_run_id": target_run_id,
        "started_at_utc": started_at_utc.isoformat(),
        "ended_at_utc": ended_at_utc.isoformat(),
        "counts_by_outcome": counts_by_outcome,
        "planned_cells": [
            {
                "cell": r.cell.to_stable_dict(),
                "replay_outcome": r.replay_outcome,
                "pipeline_version_match": r.pipeline_version_match,
                "normalized_bytes_byte_identical": r.normalized_bytes_byte_identical,
                "stable_failure_code": r.stable_failure_code,
                "source_pipeline_version": r.source_pipeline_version,
                "current_pipeline_version": r.current_pipeline_version,
                "comparison_notes": list(r.comparison_notes),
            }
            for r in cell_results
        ],
        "qualification_status": "not_evaluated",
    }
    writer.write_json(layout.run_summary_path, replay_summary_payload)

    return ReplayRunResult(
        source_run_id=source_run_id,
        target_run_id=target_run_id,
        target_layout=layout,
        cell_results=tuple(cell_results),
        counts_by_outcome=counts_by_outcome,
        started_at_utc=started_at_utc,
        ended_at_utc=ended_at_utc,
    )


# ---- Per-cell replay ----------------------------------------


def _replay_one_cell(
    *,
    source_candidate_path: Path,
    source_payload: Mapping[str, Any],
    cell: CellKey,
    fixtures_root: Path,
    pipeline: NormalizationPipeline,
    family,
    writer: EvidenceWriter,
    layout: EvidenceLayout,
    source_run_id: str,
    target_run_id: str,
) -> ReplayCellResult:
    """Verify source raw integrity + re-normalize + write per-cell
    replay candidate. Also writes normalized bytes + manifest when
    replay normalization succeeds."""
    source_raw_desc = source_payload.get("raw_artifact")
    source_normalization = source_payload.get("normalization_stage") or {}
    source_pipeline_version = source_normalization.get("pipeline_version")

    # Current pipeline version for this profile.
    try:
        profile = load_surface_profile(cell.surface_profile)
    except Exception as exc:
        # Profile disappeared / renamed — surface as malformed
        # source evidence with a factual outcome.
        comparison_notes = (f"current profile load failed: {exc!s}",)
        candidate_out = _write_replay_candidate(
            writer=writer,
            layout=layout,
            cell=cell,
            source_run_id=source_run_id,
            target_run_id=target_run_id,
            source_pipeline_version=source_pipeline_version,
            current_pipeline_version=None,
            replay_outcome="source_evidence_malformed",
            source_raw_sha256=(source_raw_desc.get("sha256_hex") if source_raw_desc else None),
            source_normalized_sha256=_source_normalized_hash(source_normalization),
            replay_normalized_sha256=None,
            normalized_bytes_byte_identical=None,
            stable_failure_code=None,
            error_message=str(exc),
            replay_normalized_artifact=None,
            replay_manifest_artifact=None,
            comparison_notes=comparison_notes,
        )
        return ReplayCellResult(
            cell=cell,
            source_pipeline_version=source_pipeline_version,
            current_pipeline_version=None,
            pipeline_version_match=False,
            replay_outcome="source_evidence_malformed",
            source_raw_sha256=(source_raw_desc.get("sha256_hex") if source_raw_desc else None),
            source_normalized_sha256=_source_normalized_hash(source_normalization),
            replay_normalized_sha256=None,
            normalized_bytes_byte_identical=None,
            stable_failure_code=None,
            error_message=str(exc),
            candidate_artifact=candidate_out,
            replay_normalized_artifact=None,
            replay_manifest_artifact=None,
            comparison_notes=comparison_notes,
        )

    current_pipeline_version = pipeline.pipeline_version(profile, family)
    pipeline_version_match = source_pipeline_version == current_pipeline_version

    # Source raw absent — provider stage failed in source, so
    # there's nothing to replay. Record factually.
    if source_raw_desc is None:
        comparison_notes = ("source raw absent; nothing to replay",)
        candidate_out = _write_replay_candidate(
            writer=writer,
            layout=layout,
            cell=cell,
            source_run_id=source_run_id,
            target_run_id=target_run_id,
            source_pipeline_version=source_pipeline_version,
            current_pipeline_version=current_pipeline_version,
            replay_outcome="source_raw_absent",
            source_raw_sha256=None,
            source_normalized_sha256=_source_normalized_hash(source_normalization),
            replay_normalized_sha256=None,
            normalized_bytes_byte_identical=None,
            stable_failure_code=None,
            error_message=None,
            replay_normalized_artifact=None,
            replay_manifest_artifact=None,
            comparison_notes=comparison_notes,
        )
        return ReplayCellResult(
            cell=cell,
            source_pipeline_version=source_pipeline_version,
            current_pipeline_version=current_pipeline_version,
            pipeline_version_match=pipeline_version_match,
            replay_outcome="source_raw_absent",
            source_raw_sha256=None,
            source_normalized_sha256=_source_normalized_hash(source_normalization),
            replay_normalized_sha256=None,
            normalized_bytes_byte_identical=None,
            stable_failure_code=None,
            error_message=None,
            candidate_artifact=candidate_out,
            replay_normalized_artifact=None,
            replay_manifest_artifact=None,
            comparison_notes=comparison_notes,
        )

    source_raw_relpath = source_raw_desc["relative_path"]
    source_raw_hash = source_raw_desc["sha256_hex"]
    source_raw_abs = fixtures_root / source_raw_relpath

    if not source_raw_abs.is_file():
        # Source raw file missing on disk but the candidate said
        # it should be present — corruption of the immutable
        # evidence tree.
        raise SourceEvidenceMalformed(
            f"source candidate {source_candidate_path} claims raw at "
            f"{source_raw_abs} but the file is missing"
        )

    raw_bytes = source_raw_abs.read_bytes()
    recomputed_hash = _sha256_hex(raw_bytes)
    if recomputed_hash != source_raw_hash:
        raise SourceRawHashMismatch(
            f"source_raw_hash_mismatch at {source_raw_abs}: recorded "
            f"{source_raw_hash!r}, recomputed {recomputed_hash!r}"
        )

    # Re-normalize.
    replay_outcome: str
    replay_normalized_sha256: str | None = None
    normalized_bytes_byte_identical: bool | None = None
    stable_failure_code: str | None = None
    error_message: str | None = None
    replay_normalized_artifact: WrittenArtifact | None = None
    replay_manifest_artifact: WrittenArtifact | None = None
    comparison_notes_list: list[str] = []

    if not pipeline_version_match:
        comparison_notes_list.append(
            "pipeline_version_differs — byte-equality NOT required by contract"
        )

    norm_spec = NormalizationSpec(
        raw_bytes=raw_bytes, surface_profile_id=cell.surface_profile,
    )
    try:
        norm_result = pipeline.run(norm_spec)
    except PipelineStageError as exc:
        replay_outcome = "normalization_failed"
        stable_failure_code = _extract_stable_failure_code(str(exc))
        error_message = str(exc)
    except (PipelineInputError, PipelineError) as exc:
        replay_outcome = "normalization_failed"
        stable_failure_code = _extract_stable_failure_code(str(exc))
        error_message = str(exc)
    else:
        replay_outcome = "success"
        replay_normalized_sha256 = _sha256_hex(norm_result.normalized_bytes)
        replay_normalized_artifact = writer.write_binary(
            layout.normalized_artifact_path(cell),
            norm_result.normalized_bytes,
        )
        replay_manifest_artifact = writer.write_json(
            layout.normalization_manifest_path(cell),
            norm_result.manifest,
        )

    source_normalized_hash = _source_normalized_hash(source_normalization)

    if (
        replay_outcome == "success"
        and source_normalized_hash is not None
    ):
        if pipeline_version_match:
            if replay_normalized_sha256 != source_normalized_hash:
                # Pipeline claimed determinism; disagreement means
                # a Step 7 invariant broke.
                raise ReplayError(
                    f"pipeline_version matched but normalized bytes "
                    f"differ: source={source_normalized_hash!r}, "
                    f"replay={replay_normalized_sha256!r} for cell "
                    f"{cell}. This is a Step 7 determinism regression."
                )
            normalized_bytes_byte_identical = True
            comparison_notes_list.append(
                "pipeline_version match; normalized bytes byte-identical"
            )
        else:
            normalized_bytes_byte_identical = (
                replay_normalized_sha256 == source_normalized_hash
            )
            comparison_notes_list.append(
                f"pipeline_version differs; observed byte-equality="
                f"{normalized_bytes_byte_identical}"
            )
    elif replay_outcome == "success" and source_normalized_hash is None:
        comparison_notes_list.append(
            "source had no normalized artifact; nothing to compare"
        )
    elif replay_outcome == "normalization_failed":
        comparison_notes_list.append(
            f"replay normalization failed with stable_code="
            f"{stable_failure_code!r}"
        )

    candidate_out = _write_replay_candidate(
        writer=writer,
        layout=layout,
        cell=cell,
        source_run_id=source_run_id,
        target_run_id=target_run_id,
        source_pipeline_version=source_pipeline_version,
        current_pipeline_version=current_pipeline_version,
        replay_outcome=replay_outcome,
        source_raw_sha256=source_raw_hash,
        source_normalized_sha256=source_normalized_hash,
        replay_normalized_sha256=replay_normalized_sha256,
        normalized_bytes_byte_identical=normalized_bytes_byte_identical,
        stable_failure_code=stable_failure_code,
        error_message=error_message,
        replay_normalized_artifact=replay_normalized_artifact,
        replay_manifest_artifact=replay_manifest_artifact,
        comparison_notes=tuple(comparison_notes_list),
    )

    return ReplayCellResult(
        cell=cell,
        source_pipeline_version=source_pipeline_version,
        current_pipeline_version=current_pipeline_version,
        pipeline_version_match=pipeline_version_match,
        replay_outcome=replay_outcome,
        source_raw_sha256=source_raw_hash,
        source_normalized_sha256=source_normalized_hash,
        replay_normalized_sha256=replay_normalized_sha256,
        normalized_bytes_byte_identical=normalized_bytes_byte_identical,
        stable_failure_code=stable_failure_code,
        error_message=error_message,
        candidate_artifact=candidate_out,
        replay_normalized_artifact=replay_normalized_artifact,
        replay_manifest_artifact=replay_manifest_artifact,
        comparison_notes=tuple(comparison_notes_list),
    )


def _source_normalized_hash(source_normalization: Mapping[str, Any]) -> str | None:
    """Extract the source's normalized_artifact SHA-256, or None
    if the source did not produce one."""
    art = source_normalization.get("normalized_artifact")
    if art is None:
        return None
    return art.get("sha256_hex")


def _write_replay_candidate(
    *,
    writer: EvidenceWriter,
    layout: EvidenceLayout,
    cell: CellKey,
    source_run_id: str,
    target_run_id: str,
    source_pipeline_version: str | None,
    current_pipeline_version: str | None,
    replay_outcome: str,
    source_raw_sha256: str | None,
    source_normalized_sha256: str | None,
    replay_normalized_sha256: str | None,
    normalized_bytes_byte_identical: bool | None,
    stable_failure_code: str | None,
    error_message: str | None,
    replay_normalized_artifact: WrittenArtifact | None,
    replay_manifest_artifact: WrittenArtifact | None,
    comparison_notes: tuple[str, ...],
) -> WrittenArtifact:
    """Write a per-cell replay candidate.json into the target
    run's tree. Distinct schema from the provider-generation
    candidate.json: this one is a replay comparison record.
    """
    payload = {
        "harness_schema_version": HARNESS_SCHEMA_VERSION,
        "kind": "replay_same_raw_input_candidate",
        "source_run_id": source_run_id,
        "target_run_id": target_run_id,
        "cell": {
            "fixture_id": cell.fixture_id,
            "direction": cell.direction,
            "reference_kind": cell.reference_kind,
            "reference_purpose": cell.reference_purpose,
            "provider": cell.provider,
            "surface_profile": cell.surface_profile,
            "cell_id": cell_id_for(cell),
        },
        "replay_outcome": replay_outcome,
        "pipeline_version_match": (
            source_pipeline_version is not None
            and current_pipeline_version is not None
            and source_pipeline_version == current_pipeline_version
        ),
        "source_pipeline_version": source_pipeline_version,
        "current_pipeline_version": current_pipeline_version,
        "source_raw_sha256": source_raw_sha256,
        "source_normalized_sha256": source_normalized_sha256,
        "replay_normalized_sha256": replay_normalized_sha256,
        "normalized_bytes_byte_identical": normalized_bytes_byte_identical,
        "stable_failure_code": stable_failure_code,
        "error_message": error_message,
        "replay_normalized_artifact": (
            {
                "relative_path": replay_normalized_artifact.relative_from_fixtures_root,
                "sha256_hex": replay_normalized_artifact.sha256_hex,
                "byte_count": replay_normalized_artifact.byte_count,
            }
            if replay_normalized_artifact is not None
            else None
        ),
        "replay_manifest_artifact": (
            {
                "relative_path": replay_manifest_artifact.relative_from_fixtures_root,
                "sha256_hex": replay_manifest_artifact.sha256_hex,
                "byte_count": replay_manifest_artifact.byte_count,
            }
            if replay_manifest_artifact is not None
            else None
        ),
        "comparison_notes": list(comparison_notes),
        "written_at_utc": datetime.now(timezone.utc).isoformat(),
    }
    return writer.write_json(layout.candidate_json_path(cell), payload)


__all__ = [
    "ReplayCellResult",
    "ReplayError",
    "ReplayRunResult",
    "SourceEvidenceMalformed",
    "SourceRawHashMismatch",
    "SourceRunNotFound",
    "replay_same_raw_input",
]
