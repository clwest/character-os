"""Universe model tests.

SESSION 261 — verifies the load-bearing schema properties:

* Per-workspace slug uniqueness (NOT global).
* Auto-slug derivation from name at save.
* Auto-suffix on slug collision within a workspace.
* Blank name rejected by ``clean()``.
* ``archived_at`` lifecycle.
* Reverse-relation counts for deletion preflight.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

from apps.accounts.models import Workspace
from apps.universe.models import Universe
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def workspace(db):
    user = User.objects.create_user(email="uni-a@test.local", password="x")
    ws = Workspace.objects.filter(owner=user).first()
    if ws is None:
        # Signal did not run (repos without ensure_default_workspace) — fall back.
        ws = Workspace.objects.create(name="U-WS", owner=user)
    ws.name = "Universe WS"
    ws.save()
    return ws


@pytest.fixture
def other_workspace(db):
    user = User.objects.create_user(email="uni-b@test.local", password="x")
    ws = Workspace.objects.filter(owner=user).first()
    if ws is None:
        ws = Workspace.objects.create(name="U-WS2", owner=user)
    ws.name = "Universe WS 2"
    ws.save()
    return ws


@pytest.mark.django_db
def test_universe_slug_auto_derived(workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    assert u.slug == "workshop"


@pytest.mark.django_db
def test_universe_slug_collision_auto_suffix(workspace):
    Universe.objects.create(workspace=workspace, name="Workshop")
    u2 = Universe.objects.create(workspace=workspace, name="Workshop")
    assert u2.slug == "workshop-2"
    u3 = Universe.objects.create(workspace=workspace, name="Workshop")
    assert u3.slug == "workshop-3"


@pytest.mark.django_db
def test_universe_slug_uniqueness_is_per_workspace(workspace, other_workspace):
    """Same slug in two workspaces is legal."""
    a = Universe.objects.create(workspace=workspace, name="Workshop")
    b = Universe.objects.create(workspace=other_workspace, name="Workshop")
    assert a.slug == "workshop"
    assert b.slug == "workshop"
    assert a.workspace_id != b.workspace_id


@pytest.mark.django_db
def test_universe_slug_uniqueness_within_workspace_at_db_level(workspace):
    """The DB constraint MUST reject a hand-forged duplicate slug in the
    same workspace (defense in depth beyond the auto-suffix path)."""
    Universe.objects.create(workspace=workspace, name="Workshop")
    with pytest.raises(IntegrityError):
        with transaction.atomic():
            # Bypass save() auto-suffix by writing the slug directly.
            u = Universe(workspace=workspace, name="Another", slug="workshop")
            super(Universe, u).save()  # skip our custom auto-suffix


@pytest.mark.django_db
def test_universe_clean_rejects_blank_name(workspace):
    u = Universe(workspace=workspace, name="   ")
    with pytest.raises(ValidationError):
        u.full_clean()


@pytest.mark.django_db
def test_universe_archived_at_defaults_null(workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    assert u.archived_at is None


@pytest.mark.django_db
def test_universe_str(workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    assert str(u) == "Workshop (Universe WS)"


@pytest.mark.django_db
def test_universe_member_counts_zero_by_default(workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    assert u.teammate_count() == 0
    assert u.knowledge_document_count() == 0
