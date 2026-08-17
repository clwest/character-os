"""Teammate.universe FK + Universe move preview tests.

SESSION 261 / Phase 2. Load-bearing:

* Assign a Teammate to a Universe via PATCH.
* Detach via PATCH ``universe: null``.
* Cross-workspace Universe rejected with 400.
* ``?universe=<uuid>`` filter narrows list.
* ``universe-move-preview`` returns offending M2M attach rows.
* Cross-workspace Universe rejected by ``.clean()`` at the model
  level as defense-in-depth.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="tm-uni@test.local", password="x")


@pytest.fixture
def workspace(user):
    ws = Workspace.objects.filter(owner=user).first() or Workspace.objects.create(
        name="TM WS", owner=user
    )
    Membership.objects.get_or_create(
        user=user, workspace=ws, defaults={"role": Membership.Role.OWNER}
    )
    return ws


@pytest.fixture
def other_workspace(db):
    other = User.objects.create_user(email="tm-uni-b@test.local", password="x")
    ws = Workspace.objects.filter(owner=other).first() or Workspace.objects.create(
        name="TM WS 2", owner=other
    )
    return ws


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---- model-level clean() ------------------------------------------------


@pytest.mark.django_db
def test_teammate_clean_rejects_cross_workspace_universe(workspace, other_workspace):
    """UNIVERSE_SCHEMA_V1.md §"Universe consistency invariant" —
    Teammate.clean() rejects a Universe FK to a different
    Workspace's Universe.
    """
    other_universe = Universe.objects.create(
        workspace=other_workspace, name="ForeignU"
    )
    tm = Teammate(workspace=workspace, name="Patch", universe=other_universe)
    with pytest.raises(ValidationError):
        tm.full_clean()


@pytest.mark.django_db
def test_teammate_clean_accepts_null_universe(workspace):
    tm = Teammate(workspace=workspace, name="Legacy")
    tm.full_clean()  # no ValidationError


@pytest.mark.django_db
def test_teammate_clean_accepts_matching_workspace_universe(workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    tm = Teammate(workspace=workspace, name="Patch", universe=u)
    tm.full_clean()  # no ValidationError


# ---- API PATCH ----------------------------------------------------------


@pytest.mark.django_db
def test_patch_assigns_universe(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    tm = Teammate.objects.create(workspace=workspace, name="Patch")

    resp = client.patch(
        f"/api/spokespeople/{tm.id}/",
        data={"universe": str(u.id)},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    tm.refresh_from_db()
    assert tm.universe_id == u.id


@pytest.mark.django_db
def test_patch_detaches_universe(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    tm = Teammate.objects.create(workspace=workspace, name="Patch", universe=u)

    resp = client.patch(
        f"/api/spokespeople/{tm.id}/",
        data={"universe": None},
        format="json",
    )
    assert resp.status_code == 200, resp.content
    tm.refresh_from_db()
    assert tm.universe_id is None


@pytest.mark.django_db
def test_patch_cross_workspace_universe_rejected(client, workspace, other_workspace):
    foreign_u = Universe.objects.create(
        workspace=other_workspace, name="ForeignU"
    )
    tm = Teammate.objects.create(workspace=workspace, name="Patch")

    resp = client.patch(
        f"/api/spokespeople/{tm.id}/",
        data={"universe": str(foreign_u.id)},
        format="json",
    )
    assert resp.status_code == 400, resp.content
    tm.refresh_from_db()
    assert tm.universe_id is None


# ---- list ?universe=<uuid> filter ---------------------------------------


@pytest.mark.django_db
def test_list_filter_by_universe(client, workspace):
    u1 = Universe.objects.create(workspace=workspace, name="Workshop")
    u2 = Universe.objects.create(workspace=workspace, name="Bakery")
    Teammate.objects.create(workspace=workspace, name="Patch", universe=u1)
    Teammate.objects.create(workspace=workspace, name="Muffin", universe=u2)
    Teammate.objects.create(workspace=workspace, name="Legacy")

    resp = client.get(f"/api/spokespeople/?universe={u1.id}")
    body = resp.json()
    results = body if isinstance(body, list) else body["results"]
    assert len(results) == 1
    assert results[0]["name"] == "Patch"


@pytest.mark.django_db
def test_list_filter_universe_none_returns_legacy(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    Teammate.objects.create(workspace=workspace, name="Patch", universe=u)
    Teammate.objects.create(workspace=workspace, name="Legacy")

    resp = client.get("/api/spokespeople/?universe=none")
    body = resp.json()
    results = body if isinstance(body, list) else body["results"]
    assert len(results) == 1
    assert results[0]["name"] == "Legacy"


# ---- universe-move-preview ---------------------------------------------


@pytest.mark.django_db
def test_universe_move_preview_no_attachments(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    tm = Teammate.objects.create(workspace=workspace, name="Patch")

    resp = client.get(
        f"/api/spokespeople/{tm.id}/universe-move-preview/?target={u.id}"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_universe"] is None
    assert body["target_universe"] == str(u.id)
    assert body["offending_documents"] == []


@pytest.mark.django_db
def test_universe_move_preview_flags_orphans(client, workspace):
    """A legacy teammate attached to legacy docs would orphan
    those attaches if moved into a Universe."""
    from apps.embeddings.models import DocumentStatus, DocumentType, IngestedVia, KnowledgeDocument

    u = Universe.objects.create(workspace=workspace, name="Workshop")
    tm = Teammate.objects.create(workspace=workspace, name="Legacy")

    d1 = KnowledgeDocument.objects.create(
        workspace=workspace,
        title="Legacy Doc 1",
        document_type=DocumentType.TEXT,
        raw_content="x",
        processed_content="x",
        content_hash="lucid-h1",
        ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    d1.spokespeople.set([tm])

    resp = client.get(
        f"/api/spokespeople/{tm.id}/universe-move-preview/?target={u.id}"
    )
    body = resp.json()
    assert body["target_universe"] == str(u.id)
    offending_ids = {d["id"] for d in body["offending_documents"]}
    assert str(d1.id) in offending_ids


@pytest.mark.django_db
def test_universe_move_preview_target_null(client, workspace):
    """Moving a Universe-scoped teammate to legacy flags every
    Universe-scoped attach as offending."""
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    tm = Teammate.objects.create(workspace=workspace, name="Patch", universe=u)

    resp = client.get(
        f"/api/spokespeople/{tm.id}/universe-move-preview/?target=null"
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["current_universe"] == str(u.id)
    assert body["target_universe"] is None
