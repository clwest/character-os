"""Tests for the canonical ``frozen_candidate_id`` identity (SESSION 249 Finding 1).

Load-bearing invariants proved here:

* ``frozen_candidate_id`` is globally unique across the 560-cell
  frozen 9.a run — the plan's central correction from Revision Pass 2.
* Multiple candidates DO legitimately share the same ``cell_id``
  (differing only in direction + provider), and remain distinct via
  the four-part identifier. Using ``cell_id`` alone as an identity
  key would collapse them — regression coverage prevents that.
* Parse ⇔ build round-trip is stable.
* Path-traversal-flavored inputs are refused.
* Unauthorized run IDs are refused at construction time.
"""
from __future__ import annotations

import pytest

from apps.bootstrap_review.evidence import (
    AUTHORIZED_DIRECTIONS,
    AUTHORIZED_FIXTURE_IDS,
    AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES,
    AUTHORIZED_PROVIDERS,
    AUTHORIZED_RUN_IDS,
    AUTHORIZED_SURFACE_PROFILES,
    FrozenCandidateId,
    InvalidFrozenCandidateId,
    UnauthorizedRunId,
    enumerate_planned_slot_grid,
)

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"


def test_authorized_vocabulary_frozen():
    """The four component vocabularies are what SESSION 249 ratified."""
    assert FROZEN_RUN_ID in AUTHORIZED_RUN_IDS
    assert AUTHORIZED_FIXTURE_IDS == frozenset(
        {"fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4"}
    )
    assert AUTHORIZED_DIRECTIONS == frozenset(
        {"identity_only", "softened_photographic"}
    )
    assert AUTHORIZED_PROVIDERS == frozenset(
        {"stability_still", "runway_still_portrait"}
    )
    assert AUTHORIZED_SURFACE_PROFILES == frozenset(
        {"compact", "team_card", "presence", "studio", "conversation"}
    )


def test_parse_build_roundtrip():
    fcid_from_parts = FrozenCandidateId.build(
        run_id=FROZEN_RUN_ID,
        direction="identity_only",
        provider="stability_still",
        cell_id="fixture_h1__portrait_reference__front__compact",
    )
    parsed = FrozenCandidateId.parse(fcid_from_parts.value)
    assert parsed == fcid_from_parts
    assert parsed.value == (
        f"{FROZEN_RUN_ID}/identity_only/stability_still/"
        "fixture_h1__portrait_reference__front__compact"
    )
    assert parsed.fixture_id == "fixture_h1"
    assert parsed.reference_kind == "portrait_reference"
    assert parsed.reference_purpose == "front"
    assert parsed.surface_profile == "compact"


def test_cell_id_is_not_globally_unique_but_frozen_candidate_id_is():
    """This is the SESSION 249 Finding 1 regression guard.

    Three real candidates in fixture_h1 share
    ``cell_id=fixture_h1__portrait_reference__front__compact`` and
    differ only in direction / provider. Proving that ``cell_id``
    alone would collapse them + that ``frozen_candidate_id`` keeps
    them distinct.
    """
    cell_id = "fixture_h1__portrait_reference__front__compact"
    permutations = [
        ("identity_only", "stability_still"),
        ("identity_only", "runway_still_portrait"),
        ("softened_photographic", "stability_still"),
        ("softened_photographic", "runway_still_portrait"),
    ]
    fcids = [
        FrozenCandidateId.build(
            run_id=FROZEN_RUN_ID,
            direction=direction,
            provider=provider,
            cell_id=cell_id,
        )
        for direction, provider in permutations
    ]
    # All share the same cell_id.
    assert len({f.cell_id for f in fcids}) == 1
    # None share a frozen_candidate_id.
    assert len({f.value for f in fcids}) == len(fcids)


def test_full_run_frozen_candidate_ids_are_globally_unique():
    """Enumerate every ratified candidate under the frozen run and
    assert 560 distinct ``frozen_candidate_id`` values."""
    all_ids: list[str] = []
    for fixture_id in sorted(AUTHORIZED_FIXTURE_IDS):
        for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
            slot_ids = enumerate_planned_slot_grid(
                run_id=FROZEN_RUN_ID,
                fixture_id=fixture_id,
                reference_kind="portrait_reference",
                reference_purpose=purpose,
            )
            all_ids.extend(fcid.value for fcid in slot_ids)
    # 4 fixtures × 7 purposes × 20 (direction × provider × profile)
    # = 560.
    assert len(all_ids) == 560
    assert len(set(all_ids)) == 560


def test_unauthorized_run_id_refused():
    with pytest.raises(UnauthorizedRunId):
        FrozenCandidateId.build(
            run_id="bootstrap_someone_else",
            direction="identity_only",
            provider="stability_still",
            cell_id="fixture_h1__portrait_reference__front__compact",
        )


def test_unauthorized_direction_refused():
    with pytest.raises(InvalidFrozenCandidateId):
        FrozenCandidateId.build(
            run_id=FROZEN_RUN_ID,
            direction="cinematic_naturalistic",  # ratified but not in 9.a
            provider="stability_still",
            cell_id="fixture_h1__portrait_reference__front__compact",
        )


def test_unauthorized_provider_refused():
    with pytest.raises(InvalidFrozenCandidateId):
        FrozenCandidateId.build(
            run_id=FROZEN_RUN_ID,
            direction="identity_only",
            provider="elevenlabs_tts",
            cell_id="fixture_h1__portrait_reference__front__compact",
        )


def test_unauthorized_fixture_refused():
    """fixture_nh1 stays off the 9.b.1 surface (§Q24)."""
    with pytest.raises(InvalidFrozenCandidateId):
        FrozenCandidateId.build(
            run_id=FROZEN_RUN_ID,
            direction="identity_only",
            provider="stability_still",
            cell_id="fixture_nh1__canonical_reference__front__compact",
        )


def test_cell_id_shape_refused_when_missing_components():
    with pytest.raises(InvalidFrozenCandidateId):
        FrozenCandidateId.build(
            run_id=FROZEN_RUN_ID,
            direction="identity_only",
            provider="stability_still",
            cell_id="fixture_h1__portrait_reference__front",  # no profile
        )


@pytest.mark.parametrize(
    "component,value",
    [
        ("run_id", ""),
        ("direction", ""),
        ("provider", ""),
        ("cell_id", ""),
        ("run_id", ".."),
        ("run_id", "./x"),
        ("direction", "identity_only/../shell"),
        ("provider", "stability_still\\..\\etc"),
        ("cell_id", ".hidden__portrait_reference__front__compact"),
        ("cell_id", "fixture_h1__portrait_reference__front__compact\x00"),
    ],
)
def test_path_traversal_flavored_inputs_refused(component, value):
    kwargs = dict(
        run_id=FROZEN_RUN_ID,
        direction="identity_only",
        provider="stability_still",
        cell_id="fixture_h1__portrait_reference__front__compact",
    )
    kwargs[component] = value
    with pytest.raises((InvalidFrozenCandidateId, UnauthorizedRunId)):
        FrozenCandidateId.build(**kwargs)


def test_parse_refuses_wrong_number_of_components():
    for bad in ("", "a", "a/b", "a/b/c", "a/b/c/d/e"):
        with pytest.raises(InvalidFrozenCandidateId):
            FrozenCandidateId.parse(bad)
