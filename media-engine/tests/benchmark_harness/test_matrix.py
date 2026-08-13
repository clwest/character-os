"""Benchmark harness matrix — cell expansion + axis discipline.

Confirms:

* Background is NOT a matrix axis (derived from surface profile).
* Cell keys are hashable + comparable and produce a stable order.
* Branch-scoped purposes: cross-branch purpose combinations
  never appear in the expansion.
* Ratified round-one matrix produces the expected cardinality.
* Fingerprint input is stable across axis-tuple reorderings.
"""
from __future__ import annotations

import pytest

from app.services.benchmark_harness import (
    BACKGROUND_IS_DERIVED_FROM_PROFILE,
    CellKey,
    HumanPortraitReferencePurpose,
    IdentityBranch,
    MatrixAxes,
    NonHumanCanonicalReferencePurpose,
    RATIFIED_PROVIDERS,
    RATIFIED_SURFACE_PROFILES,
    RenderingDirectionHypothesis,
    axes_fingerprint_input,
    expand_matrix,
    load_ratified_fixtures,
)


# ---- The load-bearing derived-not-swept constant ----------------


def test_background_is_derived_from_profile_constant_is_true() -> None:
    """If a future change makes background an independent matrix
    axis, this test fails first — before the change leaks into
    evidence."""
    assert BACKGROUND_IS_DERIVED_FROM_PROFILE is True


def test_cell_key_has_no_background_field() -> None:
    """CellKey MUST NOT carry a background axis. Backgrounds are
    derived from the surface profile via
    ``resolve_background_for_profile`` — swept only via
    reviewer_override, not as a matrix axis."""
    ck = CellKey(
        fixture_id="fixture_h1",
        direction="identity_only",
        reference_kind="portrait_reference",
        reference_purpose="front",
        provider="mock",
        surface_profile="compact",
    )
    assert not hasattr(ck, "background_id")
    assert "background" not in ck.to_stable_dict()


# ---- Ratified round-one cardinality -----------------------------


def test_ratified_round_one_matrix_cardinality() -> None:
    """5 fixtures × 6 directions × (7 human purposes | 1 nh purpose)
    × 3 providers × 5 profiles.

    * humans:     4 × 6 × 7 × 3 × 5 = 2520 cells
    * non-human:  1 × 6 × 1 × 3 × 5 =   90 cells
    * total:                          2610 cells
    """
    axes = MatrixAxes.ratified_round_one()
    fixtures = load_ratified_fixtures()
    cells = expand_matrix(axes, fixtures)
    assert len(cells) == 2610


def test_matrix_expansion_is_deterministically_ordered() -> None:
    """Two identical inputs produce the same tuple in the same
    order."""
    axes = MatrixAxes.ratified_round_one()
    fixtures = load_ratified_fixtures()
    a = expand_matrix(axes, fixtures)
    b = expand_matrix(axes, fixtures)
    assert a == b


# ---- Branch scoping --------------------------------------------


def test_non_human_fixture_only_gets_non_human_purposes() -> None:
    axes = MatrixAxes.ratified_round_one()
    fixtures = load_ratified_fixtures()
    cells = expand_matrix(axes, fixtures)
    non_human_cells = [c for c in cells if c.fixture_id == "fixture_nh1"]
    nh_purposes = {c.reference_purpose for c in non_human_cells}
    assert nh_purposes == {p.value for p in NonHumanCanonicalReferencePurpose}
    nh_kinds = {c.reference_kind for c in non_human_cells}
    assert nh_kinds == {"canonical_reference"}


def test_human_fixture_only_gets_human_purposes() -> None:
    axes = MatrixAxes.ratified_round_one()
    fixtures = load_ratified_fixtures()
    cells = expand_matrix(axes, fixtures)
    human_cells = [c for c in cells if c.fixture_id == "fixture_h1"]
    human_purposes = {c.reference_purpose for c in human_cells}
    assert human_purposes == {p.value for p in HumanPortraitReferencePurpose}
    human_kinds = {c.reference_kind for c in human_cells}
    assert human_kinds == {"portrait_reference"}


def test_expand_rejects_unknown_fixture_id() -> None:
    """A matrix that names a fixture_id absent from the loaded
    fixture set raises. Cannot silently produce zero cells for
    that fixture."""
    axes = MatrixAxes(
        fixture_ids=("fixture_never_authored",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    with pytest.raises(ValueError, match="not present in the loaded fixture set"):
        expand_matrix(axes, load_ratified_fixtures())


# ---- Bounded matrix by caller --------------------------------


def test_narrow_axes_produce_expected_cardinality() -> None:
    """Bounded matrix (1 fixture × 1 direction × 2 purposes × 1
    provider × 2 profiles) produces exactly 4 cells."""
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
    fixtures = load_ratified_fixtures()
    cells = expand_matrix(axes, fixtures)
    assert len(cells) == 4
    purposes_seen = {c.reference_purpose for c in cells}
    assert purposes_seen == {"front", "neutral_rest"}


# ---- Fingerprint input -------------------------------------------


def test_axes_fingerprint_input_is_json_serializable() -> None:
    import json

    axes = MatrixAxes.ratified_round_one()
    payload = axes_fingerprint_input(axes)
    # Round-trip JSON to prove no non-serializable types leaked in.
    assert json.loads(json.dumps(payload)) == payload


def test_axes_fingerprint_input_stable_regardless_of_tuple_order() -> None:
    """The fingerprint input helper must not change when the
    caller supplies axis values in a different tuple order.
    That guarantees the run_fingerprint remains stable across
    equivalent axis descriptions."""
    axes_a = MatrixAxes(
        fixture_ids=("fixture_h1", "fixture_h2"),
        directions=("identity_only", "cinematic_naturalistic"),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front", "neutral_rest"),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock", "stability_still"),
        surface_profiles=("compact", "team_card"),
    )
    axes_b = MatrixAxes(
        fixture_ids=("fixture_h2", "fixture_h1"),
        directions=("cinematic_naturalistic", "identity_only"),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("neutral_rest", "front"),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("stability_still", "mock"),
        surface_profiles=("team_card", "compact"),
    )
    from app.services.benchmark_harness.run_identity import (
        compute_run_fingerprint,
    )
    from app.services.benchmark_harness import HARNESS_SCHEMA_VERSION

    fingerprint_kwargs = dict(
        provider_models=None,
        surface_profile_versions={"compact": 1, "team_card": 1},
        background_family_schema_hash="testhash",
        pipeline_versions={"compact": "pv1", "team_card": "pv1"},
        prompt_builder_version="1",
        execution_mode="forced_mock",
        harness_schema_version=HARNESS_SCHEMA_VERSION,
    )
    fixtures = load_ratified_fixtures()
    fp_a = compute_run_fingerprint(
        fixtures=fixtures, axes=axes_a, **fingerprint_kwargs,
    )
    fp_b = compute_run_fingerprint(
        fixtures=fixtures, axes=axes_b, **fingerprint_kwargs,
    )
    assert fp_a == fp_b
