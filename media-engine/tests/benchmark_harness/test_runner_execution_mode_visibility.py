"""Execution-mode visibility invariants.

Operator discipline #6 lock: mock runs are NEVER qualification
evidence. Run-summary + per-cell evidence must make execution
mode impossible to overlook.
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


def _small_matrix_setup(tmp_path: Path) -> tuple[Path, list, MatrixAxes]:
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
    return fixtures_root, fixtures, axes


def test_run_summary_records_execution_mode_and_non_qualification_notice(
    tmp_path: Path,
) -> None:
    fixtures_root, fixtures, axes = _small_matrix_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    summary = json.loads(result.layout.run_summary_path.read_text())
    em = summary["execution_mode"]
    assert em["requested"] == "forced_mock"
    assert em["contains_real_execution"] is False
    assert "non-qualification" in em["notice"].lower() or "not present as" in em["notice"].lower()


def test_per_cell_candidate_records_execution_mode_actual_visibly(
    tmp_path: Path,
) -> None:
    """Every candidate.json includes ``actual_execution_mode`` on
    the provider stage — cannot be overlooked when reading
    evidence.
    """
    fixtures_root, fixtures, axes = _small_matrix_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    r = result.cell_results[0]
    payload = json.loads(
        (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
    )
    assert payload["provider_stage"]["actual_execution_mode"] == "mock"
    assert payload["provider_stage"]["requested_execution_mode"] == "forced_mock"


def test_run_summary_qualification_status_is_neutral_not_evaluated(
    tmp_path: Path,
) -> None:
    """Operator discipline #8: neutral factual guard against
    invented scoring vocabulary. ``qualification_status`` is a
    stable marker that Step 8 has not evaluated — NOT a scoring
    verdict."""
    fixtures_root, fixtures, axes = _small_matrix_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    summary = json.loads(result.layout.run_summary_path.read_text())
    assert summary["qualification_status"] == "not_evaluated"


def test_run_summary_reports_containsRealExecution_true_for_real_required(
    tmp_path: Path,
) -> None:
    """``real_required`` on the mock adapter raises
    ProviderUnavailableError — cell records provider_unavailable
    outcome. But the run summary still labels the run
    ``contains_real_execution=True`` because that's a caller-
    intent flag, not an outcome flag."""
    fixtures_root, fixtures, axes = _small_matrix_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="real_required", fixtures_root=fixtures_root,
    )
    summary = json.loads(result.layout.run_summary_path.read_text())
    assert summary["execution_mode"]["requested"] == "real_required"
    assert summary["execution_mode"]["contains_real_execution"] is True
    # Mock cannot satisfy real_required → provider_unavailable.
    assert result.cell_results[0].outcome == "provider_unavailable"
