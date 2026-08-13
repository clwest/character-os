"""Replay contract — ``replay_same_raw_input`` executable proof.

Load-bearing invariants (operator disciplines #1–#3):

* Reads raw evidence from a prior immutable run.
* Never calls ``PortraitProvider``.
* Never modifies the source run.
* Verifies source raw SHA-256 vs candidate record; refuses on
  mismatch with stable code ``source_raw_hash_mismatch``.
* Matching pipeline_version → normalized bytes byte-identical
  (else Step 7 determinism regression, raised loudly).
* Differing pipeline_version → factual version-mismatch record,
  not a failure.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.benchmark_harness import (
    IdentityBranch,
    MatrixAxes,
    ReplayError,
    SourceEvidenceMalformed,
    SourceRawHashMismatch,
    SourceRunNotFound,
    canonical_json_bytes,
    load_fixture,
    replay_same_raw_input,
    run_matrix,
)

from ._test_helpers import large_mock_provider_factory, seed_tmp_fixtures


# ---- Setup: a small source run to replay from ----------------


def _seed_source_run(tmp_path: Path):
    """Produce a small source run using the large-mock stub so
    the source has BOTH raw + normalized bytes on disk."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    source = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
        provider_factory=large_mock_provider_factory,
    )
    return fixtures_root, source


# ---- Happy path: matching pipeline_version ------------------


def test_replay_matching_pipeline_version_produces_byte_identical_normalized(
    tmp_path: Path,
) -> None:
    fixtures_root, source = _seed_source_run(tmp_path)
    assert source.cell_results[0].outcome == "success"
    replay = replay_same_raw_input(
        source_run_id=source.run_identity.run_id,
        fixtures_root=fixtures_root,
    )
    assert len(replay.cell_results) == 1
    r = replay.cell_results[0]
    assert r.replay_outcome == "success"
    assert r.pipeline_version_match is True
    assert r.source_normalized_sha256 == r.replay_normalized_sha256
    assert r.normalized_bytes_byte_identical is True
    # Replay writer landed the normalized + manifest.
    assert r.replay_normalized_artifact is not None
    assert r.replay_manifest_artifact is not None


def test_replay_preserves_source_run_files_untouched(tmp_path: Path) -> None:
    fixtures_root, source = _seed_source_run(tmp_path)
    # Snapshot the source raw bytes + sha256.
    source_cell = source.cell_results[0]
    source_raw_path = fixtures_root / source_cell.raw_artifact.relative_from_fixtures_root
    src_bytes_before = source_raw_path.read_bytes()
    # Run the replay.
    replay_same_raw_input(
        source_run_id=source.run_identity.run_id,
        fixtures_root=fixtures_root,
    )
    # Source raw unchanged after replay.
    assert source_raw_path.read_bytes() == src_bytes_before


def test_replay_writes_into_a_new_run_id_directory(tmp_path: Path) -> None:
    fixtures_root, source = _seed_source_run(tmp_path)
    replay = replay_same_raw_input(
        source_run_id=source.run_identity.run_id,
        fixtures_root=fixtures_root,
    )
    assert replay.target_run_id != source.run_identity.run_id
    # New run summary at the new location.
    assert (fixtures_root / "_runs" / replay.target_run_id / "run_summary.json").is_file()


# ---- Source integrity ---------------------------------------


def test_replay_refuses_when_source_raw_bytes_tampered(tmp_path: Path) -> None:
    """Modify the raw evidence file after the source run wrote
    it. Replay must refuse with a stable ``source_raw_hash_mismatch``
    error rather than normalizing the altered bytes."""
    fixtures_root, source = _seed_source_run(tmp_path)
    source_cell = source.cell_results[0]
    source_raw_path = fixtures_root / source_cell.raw_artifact.relative_from_fixtures_root
    # Append one byte to alter the SHA-256.
    with open(source_raw_path, "ab") as fh:
        fh.write(b"\x00")
    with pytest.raises(SourceRawHashMismatch, match="source_raw_hash_mismatch"):
        replay_same_raw_input(
            source_run_id=source.run_identity.run_id,
            fixtures_root=fixtures_root,
        )


def test_replay_refuses_when_source_raw_file_missing(tmp_path: Path) -> None:
    """Delete the raw file after the source run wrote it — the
    candidate.json still claims a raw artifact. Replay must
    surface a malformed-source error, not silently continue."""
    fixtures_root, source = _seed_source_run(tmp_path)
    source_cell = source.cell_results[0]
    (fixtures_root / source_cell.raw_artifact.relative_from_fixtures_root).unlink()
    with pytest.raises(SourceEvidenceMalformed, match="claims raw at"):
        replay_same_raw_input(
            source_run_id=source.run_identity.run_id,
            fixtures_root=fixtures_root,
        )


def test_replay_refuses_when_source_run_summary_missing(tmp_path: Path) -> None:
    """The source run_id has no run_summary.json anywhere —
    refuse before touching any fixture."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    with pytest.raises(SourceRunNotFound, match="source run summary not found"):
        replay_same_raw_input(
            source_run_id="bootstrap_never_ran",
            fixtures_root=fixtures_root,
        )


def test_replay_refuses_on_malformed_source_candidate(tmp_path: Path) -> None:
    """A candidate.json missing required fields is refused
    rather than silently interpreted."""
    fixtures_root, source = _seed_source_run(tmp_path)
    source_cell = source.cell_results[0]
    candidate_path = fixtures_root / source_cell.candidate_artifact.relative_from_fixtures_root
    candidate_path.write_bytes(b'{"harness_schema_version": 1}\n')  # missing required fields
    with pytest.raises(SourceEvidenceMalformed, match="missing required fields"):
        replay_same_raw_input(
            source_run_id=source.run_identity.run_id,
            fixtures_root=fixtures_root,
        )


# ---- Pipeline-version mismatch ------------------------------


def test_replay_records_factual_version_mismatch_without_raising(
    tmp_path: Path,
) -> None:
    """Simulate a pipeline_version differing between source and
    current by overwriting the source candidate's recorded
    pipeline_version to a fake value. Replay must NOT raise;
    it must record the mismatch factually and preserve both
    evidence sets."""
    fixtures_root, source = _seed_source_run(tmp_path)
    source_cell = source.cell_results[0]
    candidate_path = fixtures_root / source_cell.candidate_artifact.relative_from_fixtures_root
    payload = json.loads(candidate_path.read_text())
    payload["normalization_stage"]["pipeline_version"] = "pipeline_v_hypothetical_future"
    # Overwrite the source candidate (test-only tampering — the
    # replay does NOT modify source; we're forcing a mismatch to
    # test the mismatch branch).
    candidate_path.write_bytes(canonical_json_bytes(payload))

    replay = replay_same_raw_input(
        source_run_id=source.run_identity.run_id,
        fixtures_root=fixtures_root,
    )
    r = replay.cell_results[0]
    assert r.pipeline_version_match is False
    assert r.replay_outcome == "success"
    assert any("pipeline_version_differs" in n or "pipeline_version differs" in n for n in r.comparison_notes)
    # Source normalized bytes still on disk unchanged.
    assert (fixtures_root / source_cell.normalized_artifact.relative_from_fixtures_root).exists()


# ---- Provider-failure source: nothing to replay -------------


def test_replay_records_source_raw_absent_for_provider_failure_cells(
    tmp_path: Path,
) -> None:
    """A source cell that failed at the provider stage has no
    raw evidence. Replay records ``source_raw_absent`` factually
    and does not raise."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    # real_required → mock adapter raises ProviderUnavailableError → cell outcome = provider_unavailable.
    source = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="real_required", fixtures_root=fixtures_root,
    )
    assert source.cell_results[0].outcome == "provider_unavailable"
    replay = replay_same_raw_input(
        source_run_id=source.run_identity.run_id,
        fixtures_root=fixtures_root,
    )
    r = replay.cell_results[0]
    assert r.replay_outcome == "source_raw_absent"
    assert r.source_raw_sha256 is None


# ---- Normalization-failure source: raw present, no compare -


def test_replay_of_normalization_failed_source_re_runs_normalization(
    tmp_path: Path,
) -> None:
    """Source cell had raw evidence + normalization_failed
    (input_smaller_than_output on the ratified Mock). Replay
    re-attempts normalization on the same raw bytes — should
    factually reproduce the same failure with the same stable
    code, since the pipeline is deterministic."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    # Ratified Mock adapter → normalization_failed on every cell.
    source = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    assert source.cell_results[0].outcome == "normalization_failed"

    replay = replay_same_raw_input(
        source_run_id=source.run_identity.run_id,
        fixtures_root=fixtures_root,
    )
    r = replay.cell_results[0]
    assert r.pipeline_version_match is True
    assert r.replay_outcome == "normalization_failed"
    assert r.stable_failure_code == "input_smaller_than_output"


# ---- Replay summary shape ------------------------------------


def test_replay_summary_records_source_and_target_run_ids(tmp_path: Path) -> None:
    fixtures_root, source = _seed_source_run(tmp_path)
    replay = replay_same_raw_input(
        source_run_id=source.run_identity.run_id,
        fixtures_root=fixtures_root,
    )
    summary_path = replay.target_layout.run_summary_path
    payload = json.loads(summary_path.read_text())
    assert payload["kind"] == "replay_same_raw_input"
    assert payload["source_run_id"] == source.run_identity.run_id
    assert payload["target_run_id"] == replay.target_run_id
    assert payload["qualification_status"] == "not_evaluated"
    assert payload["harness_schema_version"] == 1


def test_replay_run_id_conflict_refuses_second_replay_to_same_target(
    tmp_path: Path,
) -> None:
    """Explicit target_run_id already exists → append-only writer
    refuses. Same discipline as the primary runner."""
    fixtures_root, source = _seed_source_run(tmp_path)
    replay_same_raw_input(
        source_run_id=source.run_identity.run_id,
        fixtures_root=fixtures_root,
        target_run_id="replay_target_x",
    )
    from app.services.benchmark_harness import RunIdConflictError

    with pytest.raises(RunIdConflictError, match="already has evidence"):
        replay_same_raw_input(
            source_run_id=source.run_identity.run_id,
            fixtures_root=fixtures_root,
            target_run_id="replay_target_x",
        )
