"""Full mock/config reproducibility — operator discipline #4.

Two harness executions with:
* different run_ids
* same run_fingerprint
* same fixtures / matrix / provider stub behavior / prompt-
  builder version / pipeline_version

MUST produce identical deterministic components:
* cell set
* prompts
* cell IDs
* raw hashes (where provider is deterministic)
* normalized hashes (where normalization succeeds)
* stable failure codes
* deterministic manifest payload
* provider capabilities snapshot
* fixture hashes

Excluded from equality (observational, not reproducibility):
* run_id
* started/ended timestamps
* elapsed_ms
* filesystem root
"""
from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

from app.services.benchmark_harness import (
    IdentityBranch,
    MatrixAxes,
    load_fixture,
    run_matrix,
)

from ._test_helpers import large_mock_provider_factory, seed_tmp_fixtures


def _small_matrix(tmp_path: Path):
    """3-cell matrix using the large stub so every cell reaches
    normalization success — proves reproducibility across the
    interesting deterministic surfaces."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1", "fixture_nh1"])
    fixtures = [
        load_fixture("fixture_h1", fixtures_root=fixtures_root),
        load_fixture("fixture_nh1", fixtures_root=fixtures_root),
    ]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1", "fixture_nh1"),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: ("front",),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    return fixtures_root, fixtures, axes


def _load_candidate(fixtures_root: Path, cell_result) -> dict:
    return json.loads(
        (fixtures_root / cell_result.candidate_artifact.relative_from_fixtures_root).read_text()
    )


def test_same_config_different_time_produces_same_fingerprint_different_run_id(
    tmp_path: Path,
) -> None:
    """Split the tmp path into two separate fixture roots so the
    two runs write independent evidence trees but share the same
    reproducibility configuration."""
    root_a = tmp_path / "run_a"
    root_b = tmp_path / "run_b"
    fx_a_root = seed_tmp_fixtures(root_a, ["fixture_h1"])
    fx_b_root = seed_tmp_fixtures(root_b, ["fixture_h1"])
    fixtures_a = [load_fixture("fixture_h1", fixtures_root=fx_a_root)]
    fixtures_b = [load_fixture("fixture_h1", fixtures_root=fx_b_root)]
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
    now_a = datetime(2026, 8, 8, 10, 0, 0, tzinfo=timezone.utc)
    now_b = now_a + timedelta(days=1)
    result_a = run_matrix(
        fixtures=fixtures_a, axes=axes,
        execution_mode="forced_mock", fixtures_root=fx_a_root,
        provider_factory=large_mock_provider_factory, now=now_a,
    )
    result_b = run_matrix(
        fixtures=fixtures_b, axes=axes,
        execution_mode="forced_mock", fixtures_root=fx_b_root,
        provider_factory=large_mock_provider_factory, now=now_b,
    )
    assert result_a.run_identity.run_fingerprint == result_b.run_identity.run_fingerprint
    assert result_a.run_identity.run_id != result_b.run_identity.run_id


def test_deterministic_components_match_across_two_runs(tmp_path: Path) -> None:
    """The load-bearing reproducibility proof. Runs two full mock
    matrices under identical configuration and asserts every
    deterministic component matches. Observational fields (run_id,
    timestamps, elapsed_ms, filesystem path) are excluded."""
    root_a = tmp_path / "run_a"
    root_b = tmp_path / "run_b"
    fx_a_root = seed_tmp_fixtures(root_a, ["fixture_h1", "fixture_nh1"])
    fx_b_root = seed_tmp_fixtures(root_b, ["fixture_h1", "fixture_nh1"])
    fixtures_a = [
        load_fixture("fixture_h1", fixtures_root=fx_a_root),
        load_fixture("fixture_nh1", fixtures_root=fx_a_root),
    ]
    fixtures_b = [
        load_fixture("fixture_h1", fixtures_root=fx_b_root),
        load_fixture("fixture_nh1", fixtures_root=fx_b_root),
    ]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1", "fixture_nh1"),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: ("front",),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    now_a = datetime(2026, 8, 8, 10, 0, 0, tzinfo=timezone.utc)
    now_b = now_a + timedelta(seconds=1)
    result_a = run_matrix(
        fixtures=fixtures_a, axes=axes,
        execution_mode="forced_mock", fixtures_root=fx_a_root,
        provider_factory=large_mock_provider_factory, now=now_a,
    )
    result_b = run_matrix(
        fixtures=fixtures_b, axes=axes,
        execution_mode="forced_mock", fixtures_root=fx_b_root,
        provider_factory=large_mock_provider_factory, now=now_b,
    )

    # Same cell set.
    cells_a = tuple(sorted(r.cell for r in result_a.cell_results))
    cells_b = tuple(sorted(r.cell for r in result_b.cell_results))
    assert cells_a == cells_b

    # Index by cell for pairwise comparison.
    by_cell_a = {r.cell: (r, _load_candidate(fx_a_root, r)) for r in result_a.cell_results}
    by_cell_b = {r.cell: (r, _load_candidate(fx_b_root, r)) for r in result_b.cell_results}

    for cell in cells_a:
        r_a, p_a = by_cell_a[cell]
        r_b, p_b = by_cell_b[cell]

        # Prompt byte-identical.
        assert p_a["provider_stage"]["prompt"] == p_b["provider_stage"]["prompt"]

        # Cell ID identical.
        assert p_a["cell"]["cell_id"] == p_b["cell"]["cell_id"]

        # Raw hash identical (deterministic stub).
        assert r_a.raw_artifact.sha256_hex == r_b.raw_artifact.sha256_hex

        # Normalized hash identical (deterministic pipeline on
        # identical input).
        if r_a.normalized_artifact is not None:
            assert r_b.normalized_artifact is not None
            assert (
                r_a.normalized_artifact.sha256_hex
                == r_b.normalized_artifact.sha256_hex
            )

        # Stable failure code (None on success).
        assert r_a.stable_failure_code == r_b.stable_failure_code

        # Outcome.
        assert r_a.outcome == r_b.outcome

        # Provider capabilities snapshot identical.
        assert p_a["provider_stage"]["capabilities"] == p_b["provider_stage"]["capabilities"]

        # Fixture content hash identical.
        assert p_a["identity"]["fixture_content_hash"] == p_b["identity"]["fixture_content_hash"]

        # not_applicable_unscored marker identical.
        assert p_a["not_applicable_unscored"] == p_b["not_applicable_unscored"]

        # Normalization manifest deterministic components — every
        # field except ``execution_duration_ms`` and per-stage
        # ``duration_ms``.
        if r_a.manifest_artifact is not None:
            assert r_b.manifest_artifact is not None
            m_a = p_a["normalization_stage"]["manifest_payload"]
            m_b = p_b["normalization_stage"]["manifest_payload"]
            _assert_manifest_deterministic_equal(m_a, m_b)


def _assert_manifest_deterministic_equal(m_a: dict, m_b: dict) -> None:
    """Assert normalization manifests are equal ignoring
    observational timing fields (§10.6 manifest determinism
    contract)."""
    m_a2 = _strip_timing(m_a)
    m_b2 = _strip_timing(m_b)
    assert m_a2 == m_b2


def _strip_timing(manifest: dict) -> dict:
    """Return a deep copy of ``manifest`` with observational
    timing fields removed. Mirrors the Step 7 closure test's
    stripping."""
    out = dict(manifest)
    out.pop("execution_duration_ms", None)
    if "stages_executed" in out:
        out["stages_executed"] = [_strip_stage_timing(s) for s in out["stages_executed"]]
    if "stages_skipped" in out:
        out["stages_skipped"] = [_strip_stage_timing(s) for s in out["stages_skipped"]]
    return out


def _strip_stage_timing(stage: dict) -> dict:
    out = dict(stage)
    out.pop("duration_ms", None)
    return out


def test_run_summary_deterministic_components_match(tmp_path: Path) -> None:
    """Run summary counts + planned cell records + reproducibility
    fields match across two runs. Observational fields differ."""
    root_a = tmp_path / "run_a"
    root_b = tmp_path / "run_b"
    fx_a_root = seed_tmp_fixtures(root_a, ["fixture_h1"])
    fx_b_root = seed_tmp_fixtures(root_b, ["fixture_h1"])
    fixtures_a = [load_fixture("fixture_h1", fixtures_root=fx_a_root)]
    fixtures_b = [load_fixture("fixture_h1", fixtures_root=fx_b_root)]
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
    now_a = datetime(2026, 8, 8, 10, 0, 0, tzinfo=timezone.utc)
    now_b = now_a + timedelta(seconds=1)
    result_a = run_matrix(
        fixtures=fixtures_a, axes=axes,
        execution_mode="forced_mock", fixtures_root=fx_a_root,
        provider_factory=large_mock_provider_factory, now=now_a,
    )
    result_b = run_matrix(
        fixtures=fixtures_b, axes=axes,
        execution_mode="forced_mock", fixtures_root=fx_b_root,
        provider_factory=large_mock_provider_factory, now=now_b,
    )
    s_a = json.loads(result_a.layout.run_summary_path.read_text())
    s_b = json.loads(result_b.layout.run_summary_path.read_text())
    # Counts equal.
    assert s_a["counts"] == s_b["counts"]
    # Reproducibility block equal.
    assert s_a["reproducibility"] == s_b["reproducibility"]
    # Fixture records equal.
    assert s_a["fixtures"] == s_b["fixtures"]
    # Run fingerprint equal.
    assert s_a["run"]["run_fingerprint"] == s_b["run"]["run_fingerprint"]
    # run_id + timestamps differ.
    assert s_a["run"]["run_id"] != s_b["run"]["run_id"]
    assert s_a["started_at_utc"] != s_b["started_at_utc"]
