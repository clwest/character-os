"""EPISODE_COMPOSITION_WORKFLOW_V1 (SESSION 262) — backend tests.

Deterministic tests for the ?episode=<uuid> filter on
CompositionViewSet.list + the episode_title field on
CompositionSerializer / CompositionListSerializer. Both are the
minimum-scope backend hooks that let the SPA render the Episode
detail's attached-Composition list and the Composition detail's
Episode backlink title without extra round-trips.

Sanctioned test-side writer for Composition table per SESSION 262
test isolation policy (ALLOWED_FILES in test_isolation.py).
"""
from __future__ import annotations

from http import HTTPStatus as http

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import Composition
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode, Universe

User = get_user_model()
pytestmark = pytest.mark.django_db


def _make_workspace_with_user(email: str) -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    if ws is None:
        ws = Workspace.objects.create(name="EWCW-WS", owner=user)
    Membership.objects.get_or_create(
        user=user, workspace=ws,
        defaults={"role": Membership.Role.OWNER},
    )
    return ws, user


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_teammate(ws, universe, name: str) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, universe=universe, name=name,
        runway_avatar_id=f"av-{name.lower()}",
        portrait_path="https://fake/p.png",
        business_brief=f"{name} does X.",
    )


# ---- ?episode= filter -------------------------------------------


def test_list_filters_by_episode_returns_only_attached():
    """/api/compositions/?episode=<uuid> returns only Compositions
    with that FK; siblings in the same workspace are excluded."""
    ws, user = _make_workspace_with_user("filter1@t")
    universe = Universe.objects.create(workspace=ws, name="U")
    tm = _make_teammate(ws, universe, "P")
    ep = Episode.objects.create(
        universe=universe, title="E", operator_topic="p",
    )
    attached = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="attached",
        episode=ep, operator_topic="p",
    )
    standalone = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="standalone",
    )

    client = APIClient()
    _login(client, user)
    resp = client.get(f"/api/compositions/?episode={ep.pk}")
    assert resp.status_code == http.OK
    ids = {row["id"] for row in resp.json()["results"]}
    assert str(attached.pk) in ids
    assert str(standalone.pk) not in ids


def test_list_filters_by_episode_ignores_other_episodes():
    """Two Episodes in same Universe; filter narrows to one."""
    ws, user = _make_workspace_with_user("filter2@t")
    universe = Universe.objects.create(workspace=ws, name="U")
    tm = _make_teammate(ws, universe, "P")
    e1 = Episode.objects.create(
        universe=universe, title="E1", operator_topic="p",
    )
    e2 = Episode.objects.create(
        universe=universe, title="E2", operator_topic="p",
    )
    c1 = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="c1", episode=e1,
        operator_topic="p",
    )
    Composition.objects.create(
        workspace=ws, spokesperson=tm, name="c2", episode=e2,
        operator_topic="p",
    )

    client = APIClient()
    _login(client, user)
    resp = client.get(f"/api/compositions/?episode={e1.pk}")
    assert resp.status_code == http.OK
    ids = {row["id"] for row in resp.json()["results"]}
    assert ids == {str(c1.pk)}


def test_list_without_episode_filter_unchanged():
    """Absence of ?episode= preserves the pre-existing list shape
    (all workspace Compositions, no Episode-based narrowing)."""
    ws, user = _make_workspace_with_user("filter3@t")
    universe = Universe.objects.create(workspace=ws, name="U")
    tm = _make_teammate(ws, universe, "P")
    ep = Episode.objects.create(
        universe=universe, title="E", operator_topic="p",
    )
    attached = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="attached",
        episode=ep, operator_topic="p",
    )
    standalone = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="standalone",
    )

    client = APIClient()
    _login(client, user)
    resp = client.get("/api/compositions/")
    ids = {row["id"] for row in resp.json()["results"]}
    assert str(attached.pk) in ids
    assert str(standalone.pk) in ids


# ---- episode_title on serializers -------------------------------


def test_list_row_carries_episode_title_when_attached():
    ws, user = _make_workspace_with_user("title1@t")
    universe = Universe.objects.create(workspace=ws, name="U")
    tm = _make_teammate(ws, universe, "P")
    ep = Episode.objects.create(
        universe=universe, title="AI took over the lab",
        operator_topic="p",
    )
    Composition.objects.create(
        workspace=ws, spokesperson=tm, name="c",
        episode=ep, operator_topic="p",
    )
    client = APIClient()
    _login(client, user)
    resp = client.get(f"/api/compositions/?episode={ep.pk}")
    rows = resp.json()["results"]
    assert rows[0]["episode_title"] == "AI took over the lab"
    assert rows[0]["episode"] == str(ep.pk)


def test_list_row_episode_title_null_when_standalone():
    ws, user = _make_workspace_with_user("title2@t")
    universe = Universe.objects.create(workspace=ws, name="U")
    tm = _make_teammate(ws, universe, "P")
    c = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="solo",
    )
    client = APIClient()
    _login(client, user)
    resp = client.get(f"/api/compositions/?workspace={ws.pk}")
    rows = resp.json()["results"]
    row = next(r for r in rows if r["id"] == str(c.pk))
    assert row["episode"] is None
    assert row["episode_title"] is None


def test_detail_carries_episode_title_when_attached():
    ws, user = _make_workspace_with_user("title3@t")
    universe = Universe.objects.create(workspace=ws, name="U")
    tm = _make_teammate(ws, universe, "P")
    ep = Episode.objects.create(
        universe=universe, title="Detail title", operator_topic="p",
    )
    c = Composition.objects.create(
        workspace=ws, spokesperson=tm, name="c",
        episode=ep, operator_topic="p",
    )
    client = APIClient()
    _login(client, user)
    resp = client.get(f"/api/compositions/{c.pk}/")
    assert resp.status_code == http.OK
    data = resp.json()
    assert data["episode"] == str(ep.pk)
    assert data["episode_title"] == "Detail title"


# ---- Episode.cast added_at ordering (UI-default contract) --------


def test_episode_cast_serialized_in_added_at_order_not_alphabetic():
    """UI convention: first-added Teammate is default primary
    performer slot. Ordering is by EpisodeCast.added_at, NOT the
    Teammate name — verify against a case where the two would
    differ.

    Also asserts that this is documented as a UI convention only
    (see EpisodeSerializer.get_cast docstring); NOT a schema-level
    role designation. If a future slice needs protagonist / lead /
    narrator, that lands as its own migration.
    """
    ws, user = _make_workspace_with_user("castorder@t")
    universe = Universe.objects.create(workspace=ws, name="U")
    # Add Zed FIRST, Alpha SECOND. Alphabetic would put Alpha
    # before Zed; added_at ordering keeps Zed first.
    zed = _make_teammate(ws, universe, "Zed")
    alpha = _make_teammate(ws, universe, "Alpha")
    ep = Episode.objects.create(
        universe=universe, title="E", operator_topic="p",
    )
    ep.cast.add(zed)
    ep.cast.add(alpha)

    client = APIClient()
    _login(client, user)
    resp = client.get(f"/api/episodes/{ep.pk}/")
    assert resp.status_code == http.OK
    cast_names = [c["name"] for c in resp.json()["cast"]]
    assert cast_names == ["Zed", "Alpha"], (
        f"Expected added_at order [Zed, Alpha]; got {cast_names}"
    )


def test_episode_cast_ordering_is_ui_default_not_a_role():
    """Regression guard: swapping the M2M attach order changes the
    default-primary. Nothing else moves; per SESSION 262 dogfood
    audit, added_at is a UI seed only — no schema field encodes
    protagonist / narrator / lead semantics.
    """
    ws, _ = _make_workspace_with_user("castorder2@t")
    universe = Universe.objects.create(workspace=ws, name="U")
    a = _make_teammate(ws, universe, "A")
    b = _make_teammate(ws, universe, "B")

    e1 = Episode.objects.create(
        universe=universe, title="E1", operator_topic="p",
    )
    e1.cast.add(a); e1.cast.add(b)
    e2 = Episode.objects.create(
        universe=universe, title="E2", operator_topic="p",
    )
    e2.cast.add(b); e2.cast.add(a)

    def _serialize(ep):
        from apps.universe.serializers import EpisodeSerializer
        return EpisodeSerializer(ep).data["cast"]

    e1_cast = [c["name"] for c in _serialize(e1)]
    e2_cast = [c["name"] for c in _serialize(e2)]
    assert e1_cast == ["A", "B"]
    assert e2_cast == ["B", "A"]
