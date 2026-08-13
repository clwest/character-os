"""End-to-end runner behavior — mock-mode matrix + normalization
failure taxonomy + evidence-tree shape.

Uses the ratified Mock adapter (small 256×256 output) — every
mock cell will factually fail normalization with
``input_smaller_than_output``. This is the correct evidence per
operator discipline F-8.4. The tests below prove:

* Every cell records raw evidence (bytes preserved).
* Every cell records the stable failure code.
* Normalized + manifest artifacts are absent (never faked).
* Run continues across per-cell failures.
* Run summary counts match.
* No qualification decision is emitted.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.benchmark_harness import (
    IdentityBranch,
    MatrixAxes,
    load_fixture,
    run_matrix,
)

from ._test_helpers import seed_tmp_fixtures


# ---- End-to-end small matrix (mock only) --------------------


def _small_axes() -> MatrixAxes:
    """Two fixtures × 1 direction × 2 purposes × 1 provider × 2
    profiles = 4 human cells + 2 nh cells = actually filter by branch
    scoping (nh only has 1 purpose 'front')."""
    return MatrixAxes(
        fixture_ids=("fixture_h1", "fixture_nh1"),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front", "neutral_rest"),
            IdentityBranch.NON_HUMAN: ("front",),
        },
        providers=("mock",),
        surface_profiles=("compact", "team_card"),
    )


def test_mock_matrix_completes_and_all_cells_normalization_fail(tmp_path: Path) -> None:
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1", "fixture_nh1"])
    fixtures = [
        load_fixture("fixture_h1", fixtures_root=fixtures_root),
        load_fixture("fixture_nh1", fixtures_root=fixtures_root),
    ]
    axes = _small_axes()
    result = run_matrix(
        fixtures=fixtures,
        axes=axes,
        execution_mode="forced_mock",
        fixtures_root=fixtures_root,
    )
    # Human fixture: 2 purposes × 2 profiles = 4
    # Non-human fixture: 1 purpose × 2 profiles = 2
    assert len(result.cell_results) == 6
    for r in result.cell_results:
        # Every cell factually fails normalization on mock output.
        assert r.outcome == "normalization_failed", r.cell
        assert r.stable_failure_code == "input_smaller_than_output"


def test_run_summary_written_at_top_level_bucket(tmp_path: Path) -> None:
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
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    summary_path = result.layout.run_summary_path
    assert summary_path.exists()
    payload = json.loads(summary_path.read_text())
    assert payload["run"]["run_id"] == result.run_identity.run_id
    assert payload["run"]["run_fingerprint"] == result.run_identity.run_fingerprint
    assert payload["execution_mode"]["requested"] == "forced_mock"
    assert payload["execution_mode"]["contains_real_execution"] is False
    assert payload["qualification_status"] == "not_evaluated"
    # Counts.
    assert payload["counts"]["planned"] == 1
    assert payload["counts"]["by_outcome"] == {"normalization_failed": 1}


def test_every_cell_writes_raw_evidence_even_on_normalization_failure(
    tmp_path: Path,
) -> None:
    """Operator discipline F-8.4 + Step 8 architectural rule:
    provider bytes are preserved even when normalization fails.
    The Runway 1280×720 → portrait-profile case is exactly this
    behavior in production; here we prove it works on the mock
    adapter's tiny outputs too."""
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
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    r = result.cell_results[0]
    # Raw is present with a real byte count + hash.
    assert r.raw_artifact is not None
    assert r.raw_artifact.byte_count > 0
    assert len(r.raw_artifact.sha256_hex) == 64
    # No normalized / manifest artifacts.
    assert r.normalized_artifact is None
    assert r.manifest_artifact is None
    # File actually on disk.
    assert (fixtures_root / r.raw_artifact.relative_from_fixtures_root).exists()


def test_candidate_json_carries_every_step9_promotion_field(
    tmp_path: Path,
) -> None:
    """Operator's field-completeness list from the 8.b briefing:
    every candidate.json must include enough for Step 9 mechanical
    ingestion."""
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
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    r = result.cell_results[0]
    candidate_path = fixtures_root / r.candidate_artifact.relative_from_fixtures_root
    payload = json.loads(candidate_path.read_text())

    # Top-level.
    assert payload["harness_schema_version"] == 1
    assert payload["prompt_builder_version"] == "1"
    assert payload["outcome"] == "normalization_failed"
    assert payload["not_applicable_unscored"] is False

    # Run.
    assert payload["run"]["run_id"] == result.run_identity.run_id
    assert payload["run"]["run_fingerprint"] == result.run_identity.run_fingerprint

    # Cell.
    assert payload["cell"]["fixture_id"] == "fixture_h1"
    assert payload["cell"]["direction"] == "identity_only"
    assert payload["cell"]["reference_kind"] == "portrait_reference"
    assert payload["cell"]["reference_purpose"] == "front"
    assert payload["cell"]["provider"] == "mock"
    assert payload["cell"]["surface_profile"] == "compact"

    # Identity.
    assert payload["identity"]["branch"] == "human"
    assert payload["identity"]["spec_schema_version"] == 1
    assert len(payload["identity"]["fixture_content_hash"]) == 64

    # Provider stage.
    ps = payload["provider_stage"]
    assert ps["outcome"] == "success"  # provider itself succeeded
    assert ps["provider"] == "mock"
    assert ps["provider_model"] == "deterministic-solid"
    assert ps["requested_execution_mode"] == "forced_mock"
    assert ps["actual_execution_mode"] == "mock"
    assert ps["prompt"].startswith("[character-os benchmark prompt builder v1]")
    assert ps["prompt_snapshot"] is not None
    assert ps["elapsed_ms"] is not None
    assert ps["capabilities"] is not None
    assert ps["capabilities"]["provider_name"] == "mock"
    assert ps["error"] is None

    # Raw evidence present.
    assert payload["raw_artifact"] is not None
    assert len(payload["raw_artifact"]["sha256_hex"]) == 64

    # Normalization stage.
    ns = payload["normalization_stage"]
    assert ns["attempted"] is True
    assert ns["outcome"] == "failed"
    assert ns["failure"]["stable_code"] == "input_smaller_than_output"
    assert ns["failure"]["stage_name"] == "framing"
    assert ns["normalized_artifact"] is None
    assert ns["manifest_artifact"] is None
    # pipeline_version was recorded even on failure.
    assert "pipeline_v1" in ns["pipeline_version"]
    assert ns["surface_profile_id"] == "compact"
    assert ns["surface_profile_version"] == 1


def test_non_human_fixture_carries_not_applicable_unscored_marker(
    tmp_path: Path,
) -> None:
    """Per operator discipline #11 + §17.2.b: fixture_nh1 evidence
    must carry the ratified non-human marker distinguishing it
    from human-scored evidence downstream."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_nh1"])
    fixtures = [load_fixture("fixture_nh1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_nh1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: (),
            IdentityBranch.NON_HUMAN: ("front",),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    candidate_path = fixtures_root / result.cell_results[0].candidate_artifact.relative_from_fixtures_root
    payload = json.loads(candidate_path.read_text())
    assert payload["not_applicable_unscored"] is True
    assert payload["identity"]["branch"] == "non_human"
    assert payload["cell"]["reference_kind"] == "canonical_reference"


def test_observations_bucket_is_created_empty_with_marker(tmp_path: Path) -> None:
    """The observations/ directory is created intentionally and
    empty at Step 8, marked by ``.step8_empty_observations``."""
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
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    obs_dir = result.layout.cell_provider_root(result.cell_results[0].cell) / "observations"
    assert obs_dir.is_dir()
    marker = obs_dir / ".step8_empty_observations"
    assert marker.exists()
    assert marker.stat().st_size == 0


def test_scores_bucket_not_created_at_step_8(tmp_path: Path) -> None:
    """The scores/ bucket is Step 9 territory. Step 8 must NOT
    create it — otherwise a downstream Step 9 write path could
    silently write into it before the ratified promotion
    workflow lands."""
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
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    scores_dir = result.layout.cell_provider_root(result.cell_results[0].cell) / "scores"
    assert not scores_dir.exists()


def test_bootstrap_references_not_populated_at_step_8(tmp_path: Path) -> None:
    """Step 9 territory. Step 8 must NOT populate
    ``fixtures/<fixture>/bootstrap/references/``."""
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
    run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    bootstrap_dir = fixtures_root / "fixture_h1" / "bootstrap" / "references"
    # It may not exist at all; if it does, it must be empty.
    if bootstrap_dir.exists():
        assert list(bootstrap_dir.iterdir()) == []


def test_run_id_conflict_refuses_to_overwrite(tmp_path: Path) -> None:
    """Operator discipline #4: no --force. A second run with the
    same run_id refuses BEFORE executing providers."""
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
    from datetime import datetime, timezone

    now = datetime(2026, 8, 8, 4, 0, 0, tzinfo=timezone.utc)
    run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root, now=now,
    )
    from app.services.benchmark_harness import RunIdConflictError
    import pytest as _pytest

    with _pytest.raises(RunIdConflictError, match="already has evidence"):
        # Passing the same ``now`` reproduces the same run_id →
        # append-only refusal fires.
        run_matrix(
            fixtures=fixtures, axes=axes,
            execution_mode="forced_mock", fixtures_root=fixtures_root, now=now,
        )
