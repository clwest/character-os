"""Universe API tests.

SESSION 261 / ``docs/design/UNIVERSE_SCHEMA_V1.md`` §"API contract".
Verifies:

* Workspace member can create; non-member is blocked (permissioned
  at the queryset level — non-members see 404 on detail routes and
  empty list on list routes).
* Slug auto-suffix on collision returns 201 with the suffixed slug.
* ``?workspace=`` and ``?include_archived=`` filters.
* Soft-delete (DELETE without ``?hard=true``) sets ``archived_at``.
* Hard-delete on empty Universe succeeds.
* Hard-delete on populated Universe returns 409 with blocking counts.
* Unarchive action clears ``archived_at``.
"""
from __future__ import annotations

import pytest
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.universe.models import Universe
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def owner_user(db):
    return User.objects.create_user(email="owner@u.test", password="x")


@pytest.fixture
def workspace(owner_user):
    ws = Workspace.objects.filter(owner=owner_user).first()
    if ws is None:
        ws = Workspace.objects.create(name="Owner WS", owner=owner_user)
    Membership.objects.get_or_create(
        user=owner_user, workspace=ws, defaults={"role": Membership.Role.OWNER}
    )
    ws.name = "Owner WS"
    ws.save()
    return ws


@pytest.fixture
def stranger_user(db):
    return User.objects.create_user(email="stranger@u.test", password="x")


@pytest.fixture
def client(owner_user):
    c = APIClient()
    c.force_authenticate(user=owner_user)
    return c


@pytest.fixture
def stranger_client(stranger_user):
    c = APIClient()
    c.force_authenticate(user=stranger_user)
    return c


@pytest.mark.django_db
def test_create_universe_by_member(client, workspace):
    resp = client.post(
        "/api/universes/",
        data={"workspace": str(workspace.id), "name": "Workshop"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["name"] == "Workshop"
    assert body["slug"] == "workshop"
    assert body["workspace"] == str(workspace.id)
    assert body["teammate_count"] == 0
    assert body["knowledge_document_count"] == 0


@pytest.mark.django_db
def test_create_universe_by_non_member_rejected(stranger_client, workspace):
    resp = stranger_client.post(
        "/api/universes/",
        data={"workspace": str(workspace.id), "name": "Workshop"},
        format="json",
    )
    # Serializer's validate_workspace returns 400 with "not a member"
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_slug_collision_auto_suffix(client, workspace):
    client.post(
        "/api/universes/",
        data={"workspace": str(workspace.id), "name": "Workshop"},
        format="json",
    )
    resp = client.post(
        "/api/universes/",
        data={"workspace": str(workspace.id), "name": "Workshop"},
        format="json",
    )
    assert resp.status_code == 201, resp.content
    assert resp.json()["slug"] == "workshop-2"


@pytest.mark.django_db
def test_list_scopes_to_caller_workspaces(client, workspace):
    Universe.objects.create(workspace=workspace, name="W1")
    # A separate workspace with no membership for this caller.
    other_user = User.objects.create_user(email="o@u.test", password="x")
    other_ws = Workspace.objects.filter(owner=other_user).first() or Workspace.objects.create(
        name="Other", owner=other_user
    )
    Universe.objects.create(workspace=other_ws, name="OtherU")

    resp = client.get("/api/universes/")
    assert resp.status_code == 200
    body = resp.json()
    results = body.get("results") if isinstance(body, dict) else body
    assert len(results) == 1
    assert results[0]["name"] == "W1"


@pytest.mark.django_db
def test_list_include_archived_filter(client, workspace):
    from django.utils import timezone
    active = Universe.objects.create(workspace=workspace, name="Active")
    archived = Universe.objects.create(workspace=workspace, name="Archived")
    archived.archived_at = timezone.now()
    archived.save()

    # Default excludes archived
    resp = client.get("/api/universes/")
    results = resp.json() if isinstance(resp.json(), list) else resp.json()["results"]
    ids = {r["id"] for r in results}
    assert str(active.id) in ids and str(archived.id) not in ids

    # include_archived includes both
    resp = client.get("/api/universes/?include_archived=true")
    results = resp.json() if isinstance(resp.json(), list) else resp.json()["results"]
    ids = {r["id"] for r in results}
    assert str(active.id) in ids and str(archived.id) in ids


@pytest.mark.django_db
def test_soft_delete_sets_archived_at(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    resp = client.delete(f"/api/universes/{u.id}/")
    assert resp.status_code == 204
    u.refresh_from_db()
    assert u.archived_at is not None


@pytest.mark.django_db
def test_hard_delete_empty_universe_succeeds(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    resp = client.delete(f"/api/universes/{u.id}/?hard=true")
    assert resp.status_code == 204
    assert not Universe.objects.filter(pk=u.pk).exists()


@pytest.mark.django_db
def test_hard_delete_populated_universe_returns_409(client, workspace):
    """Load-bearing: populated Universes must be blocked from
    hard-delete so children never silently demote to universe=NULL.
    Requires the FK on Teammate + KnowledgeDocument (Phase 2/3)."""
    from apps.spokespeople.models import Teammate

    u = Universe.objects.create(workspace=workspace, name="Workshop")
    Teammate.objects.create(workspace=workspace, name="Patch", universe=u)

    resp = client.delete(f"/api/universes/{u.id}/?hard=true")
    assert resp.status_code == 409, resp.content
    body = resp.json()
    assert body["code"] == "universe_populated"
    assert body["blocking"]["teammate_count"] == 1
    assert body["blocking"]["knowledge_document_count"] == 0
    # Universe row still present.
    assert Universe.objects.filter(pk=u.pk).exists()


@pytest.mark.django_db
def test_workspace_cascade_deletes_populated_universe(workspace):
    """Django's shared-CASCADE-parent rule: RESTRICT on child FKs
    does NOT block CASCADE from the shared parent. Workspace
    deletion must cascade through Universe cleanly.
    """
    from apps.spokespeople.models import Teammate

    u = Universe.objects.create(workspace=workspace, name="Workshop")
    Teammate.objects.create(workspace=workspace, name="Patch", universe=u)
    ws_id = workspace.id
    workspace.delete()
    assert not Universe.objects.filter(pk=u.pk).exists()


@pytest.mark.django_db
def test_unarchive_clears_archived_at(client, workspace):
    from django.utils import timezone
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    u.archived_at = timezone.now()
    u.save()

    resp = client.post(f"/api/universes/{u.id}/unarchive/")
    assert resp.status_code == 200
    body = resp.json()
    assert body["archived_at"] is None
    u.refresh_from_db()
    assert u.archived_at is None


@pytest.mark.django_db
def test_patch_updates_name_and_description(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    resp = client.patch(
        f"/api/universes/{u.id}/",
        data={"name": "Rebranded Workshop", "description": "New prose."},
        format="json",
    )
    assert resp.status_code == 200
    u.refresh_from_db()
    assert u.name == "Rebranded Workshop"
    assert u.description == "New prose."


@pytest.mark.django_db
def test_blank_name_rejected_on_create(client, workspace):
    resp = client.post(
        "/api/universes/",
        data={"workspace": str(workspace.id), "name": "   "},
        format="json",
    )
    assert resp.status_code == 400
