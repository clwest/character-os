"""Matrix-completeness invariant + fatal-mid-matrix behavior.

Operator discipline #5 lock:

    Given N requested cells:
      success + failed + not_attempted_due_to_fatal_run_error == planned

    There must never be an unaccounted cell.

For ordinary expected per-cell failures the run continues. For
a fatal harness-level failure (filesystem exhaustion / permission
denied / etc.), completed cells are preserved and remaining cells
are marked ``not_attempted_due_to_fatal_run_error`` — never left
implicit.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.services.benchmark_harness import (
    IdentityBranch,
    MatrixAxes,
    load_fixture,
    run_matrix,
)

from ._test_helpers import large_mock_provider_factory, seed_tmp_fixtures


def _wide_matrix(tmp_path: Path):
    """4-cell matrix so mid-run interruption leaves cells in
    both completed and not-attempted states."""
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
    return fixtures_root, fixtures, axes


def test_full_matrix_accounting_on_ordinary_failures(tmp_path: Path) -> None:
    """No fatal error → every planned cell has a per-cell status
    entry in run_summary; success + failed sum to planned."""
    fixtures_root, fixtures, axes = _wide_matrix(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    summary = json.loads(result.layout.run_summary_path.read_text())
    counts = summary["counts"]["by_outcome"]
    planned = summary["counts"]["planned"]
    # Sum of all outcome counts equals planned.
    assert sum(counts.values()) == planned
    # Every planned_cell record has a non-null status.
    for record in summary["planned_cells"]:
        assert record["status"] is not None
        assert record["status"] != ""


def test_fatal_run_records_completed_and_not_attempted_cells(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Inject a filesystem-level failure mid-matrix. Cells written
    before the failure keep their per-cell records; remaining
    cells appear in run_summary as ``not_attempted_due_to_fatal_run_error``.
    The fatal error itself surfaces via ``RuntimeError`` from
    ``run_matrix`` after the partial summary is written."""
    fixtures_root, fixtures, axes = _wide_matrix(tmp_path)

    # Monkeypatch os.replace to fail ONCE mid-matrix, then let
    # subsequent renames succeed. This simulates a transient
    # filesystem failure that trips the runner's fatal-run
    # bailout without breaking the run_summary write that must
    # follow it.
    import os
    call_state = {"count": 0, "already_failed": False}
    orig_replace = os.replace
    trigger_after = 8  # enough for ~1 cell (candidate + raw + observation marker)

    def failing_replace(src, dst, *a, **kw):
        call_state["count"] += 1
        if (
            call_state["count"] > trigger_after
            and not call_state["already_failed"]
        ):
            call_state["already_failed"] = True
            raise OSError("simulated filesystem exhaustion")
        return orig_replace(src, dst, *a, **kw)

    monkeypatch.setattr(os, "replace", failing_replace)

    with pytest.raises(RuntimeError, match="fatal error"):
        run_matrix(
            fixtures=fixtures, axes=axes,
            execution_mode="forced_mock", fixtures_root=fixtures_root,
        )

    # Restore os.replace before reading the (partial) summary.
    monkeypatch.setattr(os, "replace", orig_replace)

    # Partial summary landed at the top-level run tree.
    summary_files = list((fixtures_root / "_runs").glob("*/run_summary.json"))
    assert len(summary_files) == 1
    summary = json.loads(summary_files[0].read_text())

    counts = summary["counts"]
    planned = counts["planned"]
    # Every planned cell has a status; at least one is
    # not_attempted_due_to_fatal_run_error.
    statuses = [rec["status"] for rec in summary["planned_cells"]]
    assert len(statuses) == planned
    assert "not_attempted_due_to_fatal_run_error" in statuses
    assert summary["fatal_run_error"] is not None
    # The invariant: success + failure + not_attempted == planned.
    assert sum(counts["by_outcome"].values()) == planned


def test_no_hidden_cells_across_ordinary_matrix(tmp_path: Path) -> None:
    """Regression guard: the ordering discipline shouldn't
    accidentally drop cells from the summary. Full 6-cell matrix
    across two fixtures, four purposes, two profiles."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1", "fixture_nh1"])
    fixtures = [
        load_fixture("fixture_h1", fixtures_root=fixtures_root),
        load_fixture("fixture_nh1", fixtures_root=fixtures_root),
    ]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1", "fixture_nh1"),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front", "neutral_rest"),
            IdentityBranch.NON_HUMAN: ("front",),
        },
        providers=("mock",),
        surface_profiles=("compact", "team_card"),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    summary = json.loads(result.layout.run_summary_path.read_text())
    # Human: 2 purposes × 2 profiles = 4.
    # Non-human: 1 purpose × 2 profiles = 2.
    # Total: 6.
    assert summary["counts"]["planned"] == 6
    assert len(summary["planned_cells"]) == 6
    assert sum(summary["counts"]["by_outcome"].values()) == 6
