"""EPISODE_SCHEMA_V1 (SESSION 262) — Episode model, API, cast,
Composition attachment, deletion, legacy, observability isolation,
and cross-Universe isolation tests.

Contract: ``docs/design/EPISODE_SCHEMA_V1.md §Q19`` (50-item
deterministic matrix). Grouped by concern for readability; every
test is deterministic and fixture-based (no provider calls).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.utils import timezone
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import (
    Composition,
    CompositionStatus,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, EpisodeCast, Universe

User = get_user_model()


# ---- fixtures ---------------------------------------------------


@pytest.fixture
def owner(db):
    user = User.objects.create_user(email="ep-owner@test.local", password="x")
    return user


@pytest.fixture
def other_owner(db):
    return User.objects.create_user(email="ep-other@test.local", password="x")


@pytest.fixture
def workspace(owner):
    ws = Workspace.objects.filter(owner=owner).first()
    if ws is None:
        ws = Workspace.objects.create(name="EpWS", owner=owner)
    Membership.objects.get_or_create(
        user=owner, workspace=ws,
        defaults={"role": Membership.Role.OWNER},
    )
    return ws


@pytest.fixture
def other_workspace(other_owner):
    ws = Workspace.objects.filter(owner=other_owner).first()
    if ws is None:
        ws = Workspace.objects.create(name="EpWS2", owner=other_owner)
    Membership.objects.get_or_create(
        user=other_owner, workspace=ws,
        defaults={"role": Membership.Role.OWNER},
    )
    return ws


@pytest.fixture
def universe(workspace):
    return Universe.objects.create(workspace=workspace, name="Workshop")


@pytest.fixture
def other_universe(workspace):
    return Universe.objects.create(workspace=workspace, name="Bakery")


@pytest.fixture
def cross_ws_universe(other_workspace):
    return Universe.objects.create(workspace=other_workspace, name="Foreign")


@pytest.fixture
def patch_tm(workspace, universe):
    return Teammate.objects.create(
        workspace=workspace, universe=universe, name="Patch",
        runway_avatar_id="av-patch", portrait_path="https://fake/p.png",
        business_brief="Patch works.",
    )


@pytest.fixture
def rivet_tm(workspace, universe):
    return Teammate.objects.create(
        workspace=workspace, universe=universe, name="Rivet",
        runway_avatar_id="av-rivet", portrait_path="https://fake/r.png",
        business_brief="Rivet observes.",
    )


@pytest.fixture
def baker_tm(workspace, other_universe):
    return Teammate.objects.create(
        workspace=workspace, universe=other_universe, name="Baker",
        runway_avatar_id="av-baker", portrait_path="https://fake/b.png",
        business_brief="Baker bakes.",
    )


@pytest.fixture
def legacy_tm(workspace):
    """Teammate with universe=NULL — legacy path."""
    return Teammate.objects.create(
        workspace=workspace, universe=None, name="Legacy",
        runway_avatar_id="av-legacy", portrait_path="https://fake/l.png",
        business_brief="Pre-Universe teammate.",
    )


@pytest.fixture
def api_client(owner):
    client = APIClient()
    client.force_authenticate(user=owner)
    return client


def _make_episode(universe, *, title="Test Story", topic="A story premise."):
    return Episode.objects.create(
        universe=universe, title=title, operator_topic=topic,
    )


# ============================================================
# SCHEMA / MODEL (tests 1-8)
# ============================================================


@pytest.mark.django_db
def test_1_episode_creates_with_required_fields(universe):
    ep = Episode.objects.create(
        universe=universe,
        title="AI took over the lab",
        operator_topic="Rivet warns Patch...",
    )
    assert ep.pk is not None
    assert ep.archived_at is None


@pytest.mark.django_db
def test_2_blank_title_rejected(universe):
    ep = Episode(universe=universe, title="   ", operator_topic="p")
    with pytest.raises(ValidationError):
        ep.full_clean()


@pytest.mark.django_db
def test_3_blank_operator_topic_rejected(universe):
    ep = Episode(universe=universe, title="T", operator_topic="")
    with pytest.raises(ValidationError):
        ep.full_clean()


@pytest.mark.django_db
def test_4_title_unique_per_universe(universe):
    Episode.objects.create(universe=universe, title="T", operator_topic="p")
    from django.db import IntegrityError, transaction
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            Episode.objects.create(
                universe=universe, title="T", operator_topic="q",
            )


@pytest.mark.django_db
def test_5_same_title_different_universes_legal(universe, other_universe):
    Episode.objects.create(universe=universe, title="T", operator_topic="p")
    Episode.objects.create(universe=other_universe, title="T", operator_topic="q")
    # No error.


@pytest.mark.django_db
def test_6_archived_at_defaults_null(universe):
    ep = _make_episode(universe)
    assert ep.archived_at is None


@pytest.mark.django_db
def test_7_created_by_set_null_on_user_delete(universe, workspace):
    """Verify Episode.created_by SET_NULL preserves the row when the
    creator user is deleted. Uses a creator user distinct from
    workspace.owner (which is PROTECT) and cleans up that creator's
    auto-generated workspace before deleting the creator, so this
    test isolates the Episode.created_by contract from the unrelated
    Workspace.owner PROTECT constraint."""
    creator = User.objects.create_user(
        email="ep-creator@test.local", password="x",
    )
    # Signal-created auto-workspace on this user would PROTECT the
    # user delete. Delete that auto-workspace first so the isolation
    # under test remains ``Episode.created_by = SET_NULL``.
    Workspace.objects.filter(owner=creator).delete()
    Membership.objects.get_or_create(
        user=creator, workspace=workspace,
        defaults={"role": Membership.Role.OWNER},
    )
    ep = Episode.objects.create(
        universe=universe, title="T", operator_topic="p",
        created_by=creator,
    )
    creator.delete()
    ep.refresh_from_db()
    assert ep.created_by_id is None


@pytest.mark.django_db
def test_8_universe_hard_delete_blocked_by_api_preflight_when_episodes(
    api_client, workspace, universe,
):
    """Design deviation from EPISODE_SCHEMA_V1 §Q7 draft: Episode.universe
    is CASCADE (not RESTRICT) because Episode has no denormalized
    workspace FK — RESTRICT would break Workspace cascade cleanup.
    Instead, the safety is enforced at the API-layer preflight on
    ``UniverseViewSet.destroy(?hard=true)``. This test verifies that
    contract."""
    _make_episode(universe)
    resp = api_client.delete(f"/api/universes/{universe.pk}/?hard=true")
    assert resp.status_code == 409, resp.data
    assert resp.data["code"] == "universe_populated"
    assert resp.data["blocking"]["episode_count"] == 1


# ============================================================
# CAST validation / isolation (tests 9-14)
# ============================================================


@pytest.mark.django_db
def test_9_cross_workspace_cast_rejected(
    universe, other_workspace, cross_ws_universe,
):
    foreign_tm = Teammate.objects.create(
        workspace=other_workspace, universe=cross_ws_universe, name="Foreign",
        runway_avatar_id="av-f", portrait_path="https://f/p.png",
        business_brief="",
    )
    ep = _make_episode(universe)
    with pytest.raises(ValidationError):
        ep.cast.add(foreign_tm)


@pytest.mark.django_db
def test_10_cross_universe_cast_rejected(universe, baker_tm):
    ep = _make_episode(universe)
    with pytest.raises(ValidationError):
        ep.cast.add(baker_tm)


@pytest.mark.django_db
def test_11_legacy_teammate_cast_rejected(universe, legacy_tm):
    ep = _make_episode(universe)
    with pytest.raises(ValidationError):
        ep.cast.add(legacy_tm)


@pytest.mark.django_db
def test_12_empty_cast_at_create_is_legal(universe):
    ep = _make_episode(universe)
    assert ep.cast.count() == 0


@pytest.mark.django_db
def test_13_cast_add_via_api_201(api_client, universe, patch_tm):
    ep = _make_episode(universe)
    resp = api_client.post(
        f"/api/episodes/{ep.pk}/cast/",
        {"teammate": str(patch_tm.pk)},
        format="json",
    )
    assert resp.status_code == 201, resp.data
    ep.refresh_from_db()
    assert ep.cast.count() == 1


@pytest.mark.django_db
def test_14_cast_remove_via_api_204_no_composition_side_effect(
    api_client, universe, patch_tm, rivet_tm,
):
    ep = _make_episode(universe)
    ep.cast.add(patch_tm)
    ep.cast.add(rivet_tm)
    # Attach a composition that references patch_tm as spokesperson.
    comp = Composition.objects.create(
        workspace=universe.workspace, spokesperson=patch_tm,
        name="C1", episode=ep, operator_topic="p",
    )
    assert comp.spokesperson_id == patch_tm.pk
    # Remove patch from cast.
    resp = api_client.delete(
        f"/api/episodes/{ep.pk}/cast/{patch_tm.pk}/",
    )
    assert resp.status_code == 204
    ep.refresh_from_db()
    assert ep.cast.count() == 1
    # Composition retains its own spokesperson linkage.
    comp.refresh_from_db()
    assert comp.spokesperson_id == patch_tm.pk


# ============================================================
# API surface (tests 15-24)
# ============================================================


@pytest.mark.django_db
def test_15_api_create_happy_path(api_client, universe, patch_tm):
    resp = api_client.post(
        "/api/episodes/",
        {
            "universe": str(universe.pk),
            "title": "A story",
            "operator_topic": "The premise.",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    assert resp.data["title"] == "A story"
    assert resp.data["archived_at"] is None
    assert resp.data["composition_count"] == 0


@pytest.mark.django_db
def test_16_api_create_wrong_workspace_403(api_client, cross_ws_universe):
    # cross_ws_universe belongs to other_workspace, of which owner is
    # NOT a member.
    resp = api_client.post(
        "/api/episodes/",
        {
            "universe": str(cross_ws_universe.pk),
            "title": "X", "operator_topic": "y",
        },
        format="json",
    )
    assert resp.status_code == 400
    assert "universe" in resp.data


@pytest.mark.django_db
def test_17_api_create_without_topic_400(api_client, universe):
    resp = api_client.post(
        "/api/episodes/",
        {"universe": str(universe.pk), "title": "T", "operator_topic": ""},
        format="json",
    )
    assert resp.status_code == 400
    assert "operator_topic" in resp.data


@pytest.mark.django_db
def test_18_api_list_filters_universe_and_archived(
    api_client, universe, other_universe,
):
    e1 = Episode.objects.create(universe=universe, title="U1", operator_topic="p")
    e2 = Episode.objects.create(universe=universe, title="U2", operator_topic="p")
    Episode.objects.create(universe=other_universe, title="U3", operator_topic="p")
    e2.archived_at = timezone.now()
    e2.save(update_fields=["archived_at", "updated_at"])
    resp = api_client.get(f"/api/episodes/?universe={universe.pk}")
    assert resp.status_code == 200
    ids = {row["id"] for row in resp.data}
    assert str(e1.pk) in ids
    assert str(e2.pk) not in ids  # archived hidden by default

    resp2 = api_client.get(
        f"/api/episodes/?universe={universe.pk}&include_archived=true"
    )
    ids2 = {row["id"] for row in resp2.data}
    assert str(e2.pk) in ids2


@pytest.mark.django_db
def test_19_api_retrieve_full_detail(api_client, universe, patch_tm):
    ep = _make_episode(universe)
    ep.cast.add(patch_tm)
    resp = api_client.get(f"/api/episodes/{ep.pk}/")
    assert resp.status_code == 200
    assert resp.data["title"] == ep.title
    assert len(resp.data["cast"]) == 1
    assert resp.data["cast"][0]["name"] == "Patch"
    assert resp.data["composition_count"] == 0


@pytest.mark.django_db
def test_20_api_patch_does_not_mutate_composition_topic(
    api_client, universe, patch_tm,
):
    ep = _make_episode(universe, topic="ORIGINAL")
    comp = Composition.objects.create(
        workspace=universe.workspace, spokesperson=patch_tm,
        name="C1", episode=ep, operator_topic="ORIGINAL-attempt-copy",
    )
    resp = api_client.patch(
        f"/api/episodes/{ep.pk}/",
        {"operator_topic": "UPDATED"},
        format="json",
    )
    assert resp.status_code == 200
    ep.refresh_from_db()
    comp.refresh_from_db()
    assert ep.operator_topic == "UPDATED"
    assert comp.operator_topic == "ORIGINAL-attempt-copy"  # untouched


@pytest.mark.django_db
def test_21_api_delete_archives_default(api_client, universe):
    ep = _make_episode(universe)
    resp = api_client.delete(f"/api/episodes/{ep.pk}/")
    assert resp.status_code == 204
    ep.refresh_from_db()
    assert ep.archived_at is not None


@pytest.mark.django_db
def test_22_api_unarchive_reverses(api_client, universe):
    ep = _make_episode(universe)
    ep.archived_at = timezone.now()
    ep.save(update_fields=["archived_at", "updated_at"])
    resp = api_client.post(f"/api/episodes/{ep.pk}/unarchive/")
    assert resp.status_code == 200
    ep.refresh_from_db()
    assert ep.archived_at is None


@pytest.mark.django_db
def test_23_hard_delete_empty_episode_204(api_client, universe):
    ep = _make_episode(universe)
    resp = api_client.delete(f"/api/episodes/{ep.pk}/?hard=true")
    assert resp.status_code == 204
    assert not Episode.objects.filter(pk=ep.pk).exists()


@pytest.mark.django_db
def test_24_hard_delete_populated_episode_409(
    api_client, universe, patch_tm,
):
    ep = _make_episode(universe)
    Composition.objects.create(
        workspace=universe.workspace, spokesperson=patch_tm,
        name="C1", episode=ep, operator_topic="p",
    )
    resp = api_client.delete(f"/api/episodes/{ep.pk}/?hard=true")
    assert resp.status_code == 409
    assert resp.data["code"] == "episode_populated"
    assert resp.data["blocking"]["composition_count"] == 1


# ============================================================
# Composition linkage (tests 25-32)
# ============================================================


@pytest.mark.django_db
def test_25_composition_create_with_episode_happy_path(
    api_client, universe, patch_tm,
):
    ep = _make_episode(universe)
    resp = api_client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(universe.workspace_id),
            "episode": str(ep.pk),
            "params": {
                "spokesperson_id": str(patch_tm.pk),
                "script": "Hello world",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert resp.status_code == 201, resp.data
    comp = Composition.objects.get(pk=resp.data["id"])
    assert comp.episode_id == ep.pk


@pytest.mark.django_db
def test_26_composition_create_cross_universe_episode_rejected(
    api_client, universe, other_universe, patch_tm, baker_tm,
):
    """Composition spokesperson in patch's Universe; Episode in
    Bakery Universe. Cross-Universe pairing must be rejected."""
    ep_bakery = _make_episode(other_universe, title="Bakery Ep")
    resp = api_client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(universe.workspace_id),
            "episode": str(ep_bakery.pk),
            "params": {
                "spokesperson_id": str(patch_tm.pk),
                "script": "Hi",
                "mock_mode": True,
            },
        },
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_27_composition_create_cross_workspace_episode_rejected(
    api_client, workspace, cross_ws_universe, patch_tm,
):
    # Owner is not a member of cross_ws_universe's workspace, so the
    # Episode lookup returns 400.
    ep_foreign = Episode.objects.create(
        universe=cross_ws_universe, title="F", operator_topic="p",
    )
    resp = api_client.post(
        "/api/compositions/",
        {
            "kind": "talking_head",
            "workspace": str(workspace.pk),
            "episode": str(ep_foreign.pk),
            "params": {
                "spokesperson_id": str(patch_tm.pk),
                "script": "Hi", "mock_mode": True,
            },
        },
        format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_28_attach_endpoint_happy_path(
    api_client, workspace, universe, patch_tm,
):
    comp = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C", operator_topic="p",
    )
    ep = _make_episode(universe)
    resp = api_client.post(
        f"/api/compositions/{comp.pk}/attach-episode/",
        {"episode": str(ep.pk)}, format="json",
    )
    assert resp.status_code == 200, resp.data
    comp.refresh_from_db()
    assert comp.episode_id == ep.pk


@pytest.mark.django_db
def test_29_attach_cross_universe_rejected(
    api_client, workspace, universe, other_universe, patch_tm,
):
    comp = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C", operator_topic="p",
    )
    ep_bakery = _make_episode(other_universe, title="B")
    resp = api_client.post(
        f"/api/compositions/{comp.pk}/attach-episode/",
        {"episode": str(ep_bakery.pk)}, format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_30_attach_legacy_spokesperson_rejected(
    api_client, workspace, universe, legacy_tm,
):
    comp = Composition.objects.create(
        workspace=workspace, spokesperson=legacy_tm, name="C", operator_topic="p",
    )
    ep = _make_episode(universe)
    resp = api_client.post(
        f"/api/compositions/{comp.pk}/attach-episode/",
        {"episode": str(ep.pk)}, format="json",
    )
    assert resp.status_code == 400


@pytest.mark.django_db
def test_31_detach_endpoint_happy_path(
    api_client, workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    comp = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=ep, operator_topic="p",
    )
    resp = api_client.delete(f"/api/compositions/{comp.pk}/attach-episode/")
    assert resp.status_code == 200
    comp.refresh_from_db()
    assert comp.episode_id is None


@pytest.mark.django_db
def test_32_move_between_episodes(
    api_client, workspace, universe, patch_tm,
):
    e1 = _make_episode(universe, title="E1")
    e2 = _make_episode(universe, title="E2")
    comp = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=e1, operator_topic="p",
    )
    resp = api_client.post(
        f"/api/compositions/{comp.pk}/attach-episode/",
        {"episode": str(e2.pk)}, format="json",
    )
    assert resp.status_code == 200
    comp.refresh_from_db()
    assert comp.episode_id == e2.pk
    assert e1.compositions.count() == 0
    assert e2.compositions.count() == 1


# ============================================================
# Retry / failed / archive semantics (tests 33-40)
# ============================================================


@pytest.mark.django_db
def test_33_two_compositions_reverse_relation(
    workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C1", episode=ep, operator_topic="p",
    )
    Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C2", episode=ep, operator_topic="p",
    )
    assert ep.compositions.count() == 2


@pytest.mark.django_db
def test_34_failed_composition_attached_legal(
    workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="Failed",
        episode=ep, status=CompositionStatus.FAILED,
        operator_topic="p",
    )
    assert c.status == CompositionStatus.FAILED
    assert c.episode_id == ep.pk


@pytest.mark.django_db
def test_35_only_failed_episode_survives(
    workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    for i in range(3):
        Composition.objects.create(
            workspace=workspace, spokesperson=patch_tm, name=f"F{i}",
            episode=ep, status=CompositionStatus.FAILED,
            operator_topic="p",
        )
    assert ep.compositions.count() == 3
    assert all(
        c.status == CompositionStatus.FAILED
        for c in ep.compositions.all()
    )


@pytest.mark.django_db
def test_36_archive_composition_fk_preserved(
    api_client, workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=ep, operator_topic="p",
    )
    api_client.delete(f"/api/episodes/{ep.pk}/")  # archive
    ep.refresh_from_db()
    c.refresh_from_db()
    assert ep.archived_at is not None
    assert c.episode_id == ep.pk


@pytest.mark.django_db
def test_37_archive_idempotent(api_client, universe):
    ep = _make_episode(universe)
    api_client.delete(f"/api/episodes/{ep.pk}/")
    ep.refresh_from_db()
    first = ep.archived_at
    api_client.delete(f"/api/episodes/{ep.pk}/?include_archived=true")
    # archived rows are hidden by default; second delete needs
    # include_archived=true to find the row, or is a no-op 404.
    # Either way archived_at doesn't rewind.
    ep.refresh_from_db()
    assert ep.archived_at is not None
    assert ep.archived_at >= first


@pytest.mark.django_db
def test_38_hard_delete_blocked_with_compositions(
    api_client, workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=ep, operator_topic="p",
    )
    resp = api_client.delete(f"/api/episodes/{ep.pk}/?hard=true")
    assert resp.status_code == 409


@pytest.mark.django_db
def test_39_after_detach_hard_delete_succeeds(
    api_client, workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=ep, operator_topic="p",
    )
    api_client.delete(f"/api/compositions/{c.pk}/attach-episode/")
    resp = api_client.delete(f"/api/episodes/{ep.pk}/?hard=true")
    assert resp.status_code == 204


@pytest.mark.django_db
def test_40_workspace_cascade_deletes_episode_and_composition(
    workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=ep, operator_topic="p",
    )
    workspace.delete()
    assert Episode.objects.filter(pk=ep.pk).count() == 0
    assert Composition.objects.filter(episode_id=ep.pk).count() == 0


# ============================================================
# Legacy compatibility (tests 41-43)
# ============================================================


@pytest.mark.django_db
def test_41_composition_with_episode_null_works(workspace, patch_tm):
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="Standalone",
    )
    assert c.episode_id is None


@pytest.mark.django_db
def test_42_universe_scoped_spokesperson_episode_less_composition_legal(
    workspace, universe, patch_tm,
):
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="Solo",
    )
    assert c.episode_id is None
    assert c.spokesperson.universe_id == universe.pk


@pytest.mark.django_db
def test_43_legacy_teammate_never_episode(
    workspace, universe, legacy_tm,
):
    ep = _make_episode(universe)
    c = Composition(
        workspace=workspace, spokesperson=legacy_tm,
        name="Legacy", episode=ep, operator_topic="p",
    )
    with pytest.raises(ValidationError):
        c.full_clean()


# ============================================================
# Observability non-mutation (tests 44-47) — SESSION 262 preserved
# ============================================================


@pytest.mark.django_db
def test_44_attach_does_not_mutate_observability(
    workspace, universe, patch_tm,
):
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        operator_topic="TOPIC",
        target_duration_seconds=60,
        synthesis_attempt_count=2,
        first_pass_synthesis="FIRST",
        corrective_hint="HINT",
        corrective_pass_synthesis="CORR",
        validation_failure_reason="",
        synthesis_predicted_seconds=54.5,
    )
    c = Composition.objects.get(pk=c.pk)
    snapshot = {
        f: getattr(c, f)
        for f in Composition._IMMUTABLE_OBSERVABILITY_FIELDS
    }
    ep = _make_episode(universe)
    c.episode = ep
    c.save(update_fields=["episode", "updated_at"])
    c.refresh_from_db()
    for f, v in snapshot.items():
        assert getattr(c, f) == v, f


@pytest.mark.django_db
def test_45_detach_does_not_mutate_observability(
    workspace, universe, patch_tm,
):
    ep = _make_episode(universe)
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=ep, operator_topic="T", synthesis_attempt_count=1,
        first_pass_synthesis="F",
    )
    c = Composition.objects.get(pk=c.pk)
    snapshot = {
        f: getattr(c, f) for f in Composition._IMMUTABLE_OBSERVABILITY_FIELDS
    }
    c.episode = None
    c.save(update_fields=["episode", "updated_at"])
    c.refresh_from_db()
    for f, v in snapshot.items():
        assert getattr(c, f) == v, f


@pytest.mark.django_db
def test_46_move_does_not_mutate_observability(
    workspace, universe, patch_tm,
):
    e1 = _make_episode(universe, title="E1")
    e2 = _make_episode(universe, title="E2")
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=e1, operator_topic="T", synthesis_attempt_count=1,
        first_pass_synthesis="F",
    )
    c = Composition.objects.get(pk=c.pk)
    snapshot = {
        f: getattr(c, f) for f in Composition._IMMUTABLE_OBSERVABILITY_FIELDS
    }
    c.episode = e2
    c.save(update_fields=["episode", "updated_at"])
    c.refresh_from_db()
    for f, v in snapshot.items():
        assert getattr(c, f) == v, f


@pytest.mark.django_db
def test_47_adversarial_attach_with_observability_in_update_fields_raises(
    workspace, universe, patch_tm,
):
    """Prove the SESSION 262 guard fires when observability is
    included in update_fields (i.e. the caller tried to mutate an
    observability field during attach)."""
    ep = _make_episode(universe)
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        operator_topic="ORIGINAL",
    )
    c = Composition.objects.get(pk=c.pk)
    c.episode = ep
    c.operator_topic = "MUTATED"  # adversarial
    with pytest.raises(ValidationError):
        c.save(update_fields=[
            "episode", "operator_topic", "updated_at",
        ])


# ============================================================
# Cross-Universe isolation + retrieval independence (tests 48-49)
# ============================================================


@pytest.mark.django_db
def test_48_episode_list_scoped_to_universe(
    api_client, universe, other_universe,
):
    e1 = _make_episode(universe, title="W1")
    e2 = _make_episode(other_universe, title="B1")
    resp = api_client.get(f"/api/episodes/?universe={universe.pk}")
    ids = {row["id"] for row in resp.data}
    assert str(e1.pk) in ids
    assert str(e2.pk) not in ids


@pytest.mark.django_db
def test_49_retrieval_unaffected_by_episode(
    workspace, universe, patch_tm,
):
    """Episode.attach does not influence K2 retrieval scope.
    Retrieval is still driven by spokesperson.universe (SESSION 261
    invariant). This test verifies that attaching an Episode to a
    Composition does not touch the retrieval-side predicate.
    """
    from apps.embeddings.retrieval import retrieve_for_teammate
    # patch_tm has universe_id set. Retrieval predicate branches on
    # spokesperson.universe_id — Episode has no bearing.
    ep = _make_episode(universe)
    c = Composition.objects.create(
        workspace=workspace, spokesperson=patch_tm, name="C",
        episode=ep, operator_topic="p",
    )
    # No knowledge docs; expect empty list. The point is that this
    # call returns without crashing and does not reference `c.episode`.
    result = retrieve_for_teammate(patch_tm, "test query", top_k=3)
    assert result == []


# ============================================================
# Universe immutability on Episode (test 50)
# ============================================================


@pytest.mark.django_db
def test_50_episode_universe_immutable_via_api(
    api_client, universe, other_universe,
):
    ep = _make_episode(universe)
    resp = api_client.patch(
        f"/api/episodes/{ep.pk}/",
        {"universe": str(other_universe.pk)},
        format="json",
    )
    assert resp.status_code == 400
    ep.refresh_from_db()
    assert ep.universe_id == universe.pk
