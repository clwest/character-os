"""SESSION 277 Slice 5 (Q-277-5) — CREATE-time Universe requirement.

The serializer must reject ordinary teammate CREATE that omits or
sends NULL ``universe``. Existing legacy ``universe=NULL`` rows must
remain readable + PATCH-able (Slice 4 §78 compatibility rule).

Load-bearing:

* POST /api/spokespeople/ without ``universe`` → 400 with structured
  ``universe_required_on_create`` code.
* POST with ``universe=null`` explicit → same 400.
* POST with a valid workspace-consistent Universe → 201.
* PATCH of an existing legacy (universe=NULL) row → 200; no forced
  Universe assignment.
* Cross-workspace Universe still rejected (Slice-1 pre-existing guard
  survives).
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="s277-slice5@test.local", password="x")


@pytest.fixture
def workspace(user):
    ws = Workspace.objects.filter(owner=user).first() or Workspace.objects.create(
        name="S277 Slice5 WS", owner=user
    )
    Membership.objects.get_or_create(
        user=user, workspace=ws, defaults={"role": Membership.Role.OWNER}
    )
    return ws


@pytest.fixture
def other_workspace(db):
    other = User.objects.create_user(email="s277-other@test.local", password="x")
    ws = Workspace.objects.filter(owner=other).first() or Workspace.objects.create(
        name="S277 Other WS", owner=other
    )
    return ws


@pytest.fixture
def universe(workspace):
    return Universe.objects.create(workspace=workspace, name="Fox & Flour Bakery")


@pytest.fixture
def cross_universe(other_workspace):
    return Universe.objects.create(workspace=other_workspace, name="Other World")


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---- CREATE rejections --------------------------------------------------


def test_create_without_universe_returns_400(client, workspace):
    """POST omitting ``universe`` is rejected — new teammates must
    belong to a World (SESSION 277 Slice 5)."""
    resp = client.post(
        "/api/spokespeople/",
        data={
            "workspace": str(workspace.id),
            "name": "Ruby",
            "business_brief": "Baker.",
        },
        format="json",
    )
    assert resp.status_code == 400, resp.content
    body = resp.json()
    assert "universe" in body
    # Structured payload — mirror of Delta ``audience_scope_required_on_create``.
    detail = body["universe"]
    if isinstance(detail, dict):
        assert detail.get("code") == "universe_required_on_create"
    else:
        # DRF sometimes wraps the dict in a list; accept either shape.
        assert any(
            (isinstance(d, dict) and d.get("code") == "universe_required_on_create")
            for d in detail
        ), body
    assert Teammate.objects.filter(workspace=workspace, name="Ruby").count() == 0


def test_create_with_explicit_null_universe_returns_400(client, workspace):
    """Explicit ``universe: null`` is treated identically to omission —
    the guard checks the resolved value, not the payload key presence."""
    resp = client.post(
        "/api/spokespeople/",
        data={
            "workspace": str(workspace.id),
            "name": "Ruby",
            "business_brief": "Baker.",
            "universe": None,
        },
        format="json",
    )
    assert resp.status_code == 400, resp.content
    body = resp.json()
    assert "universe" in body
    assert Teammate.objects.filter(workspace=workspace, name="Ruby").count() == 0


def test_create_with_valid_universe_returns_201(client, workspace, universe):
    """Happy path — creating a teammate inside a World succeeds."""
    resp = client.post(
        "/api/spokespeople/",
        data={
            "workspace": str(workspace.id),
            "name": "Ruby",
            "business_brief": "Baker.",
            "universe": str(universe.id),
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["universe"] == str(universe.id)
    tm = Teammate.objects.get(id=body["id"])
    assert tm.universe_id == universe.id
    assert tm.workspace_id == workspace.id


def test_create_with_cross_workspace_universe_returns_400(
    client, workspace, cross_universe
):
    """Pre-existing SESSION 261 cross-workspace guard still fires and
    takes precedence over the Slice-5 positive-value guard — the more
    specific error wins."""
    resp = client.post(
        "/api/spokespeople/",
        data={
            "workspace": str(workspace.id),
            "name": "Ruby",
            "business_brief": "Baker.",
            "universe": str(cross_universe.id),
        },
        format="json",
    )
    assert resp.status_code == 400, resp.content
    body = resp.json()
    assert "universe" in body
    # The pre-existing guard's message ("Universe belongs to a
    # different workspace...") must be what surfaces, not the
    # positive-value guard's ``universe_required_on_create`` code.
    payload = body["universe"]
    text_forms = [payload] if isinstance(payload, (str, dict)) else list(payload)
    surfaced_str = "".join(str(x) for x in text_forms)
    assert "different workspace" in surfaced_str, body


# ---- Legacy compatibility (UPDATE path) ---------------------------------


def test_patch_existing_legacy_row_without_universe_returns_200(
    client, workspace
):
    """Existing NULL-Universe teammate must remain PATCH-able without a
    forced World assignment. The Slice-5 guard is CREATE-only per the
    compatibility rule (Slice 4 §78 + §68-§86)."""
    legacy = Teammate.objects.create(
        workspace=workspace, name="LegacyRuby", business_brief="pre-Universe"
    )
    assert legacy.universe_id is None

    resp = client.patch(
        f"/api/spokespeople/{legacy.id}/",
        data={"business_brief": "still legacy, still editable"},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    legacy.refresh_from_db()
    assert legacy.universe_id is None
    assert legacy.business_brief == "still legacy, still editable"


def test_patch_legacy_row_to_add_universe_returns_200(
    client, workspace, universe
):
    """The existing SESSION 261 ``SpokespersonUniversePanel`` PATCH path
    — legacy row picks up a Universe — still works."""
    legacy = Teammate.objects.create(
        workspace=workspace, name="LegacyRuby2", business_brief="pre-Universe"
    )
    resp = client.patch(
        f"/api/spokespeople/{legacy.id}/",
        data={"universe": str(universe.id)},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    legacy.refresh_from_db()
    assert legacy.universe_id == universe.id


def test_get_existing_legacy_row_returns_200(client, workspace):
    """Existing legacy rows are still readable via the detail
    endpoint (Slice 4 §78 compatibility guarantee)."""
    legacy = Teammate.objects.create(
        workspace=workspace, name="LegacyRuby3", business_brief="."
    )
    resp = client.get(f"/api/spokespeople/{legacy.id}/")
    assert resp.status_code == 200, resp.content
    assert resp.json()["universe"] is None


def test_list_includes_legacy_rows(client, workspace, universe):
    """LIST returns both Universe-bound and legacy rows — the SPA
    detail pages depend on legacy rows appearing in listings."""
    legacy = Teammate.objects.create(
        workspace=workspace, name="LegacyList", business_brief="."
    )
    bound = Teammate.objects.create(
        workspace=workspace, name="BoundList", business_brief=".",
        universe=universe,
    )
    resp = client.get("/api/spokespeople/")
    assert resp.status_code == 200, resp.content
    ids = {row["id"] for row in resp.json()}
    assert str(legacy.id) in ids
    assert str(bound.id) in ids
