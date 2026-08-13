"""Runner SUCCESS-path proof-of-life using a stub provider.

The ratified Mock adapter emits 256×256 PNGs — too small to
survive any ratified surface_profile's declared output
dimensions. To prove the runner's SUCCESS shape (raw + normalized
+ manifest all written, cell outcome = success), we inject a
stub provider that returns a large-enough PNG via the runner's
``provider_factory`` hook.

Every operator-mandated Step-9 promotion field must be present
on the SUCCESS-path candidate.json.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.benchmark_harness import (
    CELL_OUTCOME_SUCCESS,
    IdentityBranch,
    MatrixAxes,
    load_fixture,
    run_matrix,
)

from ._test_helpers import large_mock_provider_factory, seed_tmp_fixtures


def test_stub_provider_success_writes_all_four_artifact_types(tmp_path: Path) -> None:
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
        fixtures=fixtures,
        axes=axes,
        execution_mode="forced_mock",
        fixtures_root=fixtures_root,
        provider_factory=large_mock_provider_factory,
    )
    r = result.cell_results[0]
    assert r.outcome == CELL_OUTCOME_SUCCESS
    # All four artifact classes present.
    assert r.candidate_artifact is not None
    assert r.raw_artifact is not None
    assert r.normalized_artifact is not None
    assert r.manifest_artifact is not None
    for artifact in (r.candidate_artifact, r.raw_artifact, r.normalized_artifact, r.manifest_artifact):
        p = fixtures_root / artifact.relative_from_fixtures_root
        assert p.exists()
        assert len(artifact.sha256_hex) == 64
        assert artifact.byte_count > 0


def test_success_candidate_carries_manifest_payload_and_normalization_metadata(
    tmp_path: Path,
) -> None:
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
        provider_factory=large_mock_provider_factory,
    )
    r = result.cell_results[0]
    payload = json.loads(
        (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
    )
    ns = payload["normalization_stage"]
    assert ns["attempted"] is True
    assert ns["outcome"] == "success"
    assert ns["failure"] is None
    # manifest_payload embedded so Step 9 does not need to open
    # the manifest file to promote the candidate.
    assert ns["manifest_payload"] is not None
    for field in (
        "pipeline_version", "surface_profile_id", "surface_profile_version",
        "background_id", "stages_executed", "stages_skipped",
        "eye_line_adjustments", "crop_metadata", "execution_duration_ms",
    ):
        assert field in ns["manifest_payload"]
    # Normalized artifact reference matches actual file size.
    normalized_path = fixtures_root / ns["normalized_artifact"]["relative_path"]
    assert normalized_path.stat().st_size == ns["normalized_artifact"]["byte_count"]


def test_success_run_summary_counts_reflect_all_success(tmp_path: Path) -> None:
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front", "neutral_rest"),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact", "team_card"),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
        provider_factory=large_mock_provider_factory,
    )
    summary = json.loads(result.layout.run_summary_path.read_text())
    assert summary["counts"]["planned"] == 4
    assert summary["counts"]["by_outcome"] == {"success": 4}
    # No failure evidence anywhere in the summary.
    for record in summary["planned_cells"]:
        assert record["status"] == "success"
        assert record["stable_failure_code"] is None
