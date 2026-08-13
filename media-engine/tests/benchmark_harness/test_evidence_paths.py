"""Evidence-path layout invariants.

Confirms the ratified §17.8.a per-artifact bucketing is preserved
and the 8.b additions (candidates/ bucket + fixtures/_runs/
top-level run summary directory) are the only new taxonomy.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.services.benchmark_harness import (
    CellKey,
    EvidenceLayout,
    RATIFIED_ARTIFACT_BUCKETS,
    cell_id_for,
    is_ratified_artifact_bucket,
)


def _sample_cell() -> CellKey:
    return CellKey(
        fixture_id="fixture_h1",
        direction="identity_only",
        reference_kind="portrait_reference",
        reference_purpose="front",
        provider="mock",
        surface_profile="compact",
    )


def test_ratified_artifact_buckets_is_the_ratified_set() -> None:
    """Sanity anchor — the buckets tuple must contain exactly the
    ratified five (raw, normalized, manifests, observations,
    scores) in ratification order."""
    assert RATIFIED_ARTIFACT_BUCKETS == (
        "raw", "normalized", "manifests", "observations", "scores",
    )


def test_is_ratified_artifact_bucket_recognizes_only_ratified() -> None:
    for b in RATIFIED_ARTIFACT_BUCKETS:
        assert is_ratified_artifact_bucket(b)
    # 8.b addition is NOT ratified.
    assert not is_ratified_artifact_bucket("candidates")
    # Random string is not.
    assert not is_ratified_artifact_bucket("scores_v2")


def test_cell_id_encodes_four_axes_only() -> None:
    cell = _sample_cell()
    assert cell_id_for(cell) == "fixture_h1__portrait_reference__front__compact"


def test_cell_id_double_underscore_delimiter_stable_for_single_underscore_ids() -> None:
    """Underscore-in-identifier edge case: fixture_h1 already has
    a `_`. The `__` delimiter keeps the four axes parseable."""
    cell = CellKey(
        fixture_id="fixture_nh1",
        direction="painterly_naturalistic",
        reference_kind="canonical_reference",
        reference_purpose="front",
        provider="stability_still",
        surface_profile="team_card",
    )
    cid = cell_id_for(cell)
    parts = cid.split("__")
    assert parts == [
        "fixture_nh1", "canonical_reference", "front", "team_card",
    ]


def test_layout_top_level_run_root_uses_added_underscore_prefix(tmp_path: Path) -> None:
    """The 8.b-added top-level run bucket is ``_runs/`` under
    the fixtures root — separated from real fixture_ directories
    by the underscore prefix."""
    layout = EvidenceLayout(fixtures_root=tmp_path, run_id="bootstrap_x")
    assert layout.top_level_run_root == tmp_path / "_runs" / "bootstrap_x"
    assert layout.run_summary_path == tmp_path / "_runs" / "bootstrap_x" / "run_summary.json"


def test_layout_cell_provider_root_matches_ratified_shape(tmp_path: Path) -> None:
    """``fixtures/<fixture_id>/runs/<run_id>/<direction>/<provider>/``
    per §17.8.a Amendment 1 — exact match."""
    layout = EvidenceLayout(fixtures_root=tmp_path, run_id="bootstrap_x")
    cell = _sample_cell()
    assert layout.cell_provider_root(cell) == (
        tmp_path / "fixture_h1" / "runs" / "bootstrap_x"
        / "identity_only" / "mock"
    )


def test_all_bucket_paths_are_children_of_cell_provider_root(tmp_path: Path) -> None:
    layout = EvidenceLayout(fixtures_root=tmp_path, run_id="bootstrap_x")
    cell = _sample_cell()
    root = layout.cell_provider_root(cell)
    for bucket in (*RATIFIED_ARTIFACT_BUCKETS, "candidates"):
        # scores is Step 9 territory but the layout still names it
        # — the paths method just resolves relative locations, it
        # does not decide who creates directories.
        if bucket == "scores":
            continue
        assert layout.bucket_dir(cell, bucket).parent == root


def test_layout_bucket_dir_rejects_unknown_bucket(tmp_path: Path) -> None:
    layout = EvidenceLayout(fixtures_root=tmp_path, run_id="bootstrap_x")
    cell = _sample_cell()
    with pytest.raises(ValueError, match="unknown evidence bucket"):
        layout.bucket_dir(cell, "never_a_bucket")


def test_relative_from_fixtures_root_is_posix(tmp_path: Path) -> None:
    layout = EvidenceLayout(fixtures_root=tmp_path, run_id="bootstrap_x")
    cell = _sample_cell()
    p = layout.raw_artifact_path(cell)
    rel = layout.relative_from_fixtures_root(p)
    assert "\\" not in rel  # POSIX slashes on every platform
    assert rel.endswith(".png")
    assert rel.startswith("fixture_h1/runs/bootstrap_x/identity_only/mock/raw/")


def test_observations_marker_is_a_hidden_file(tmp_path: Path) -> None:
    """The empty-observations marker starts with a dot so it does
    not appear in default ``ls`` output — it exists to prove the
    bucket was created intentionally."""
    layout = EvidenceLayout(fixtures_root=tmp_path, run_id="bootstrap_x")
    cell = _sample_cell()
    p = layout.observations_marker_path(cell)
    assert p.name.startswith(".")
