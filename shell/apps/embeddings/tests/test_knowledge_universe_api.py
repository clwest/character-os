"""KnowledgeDocument.universe FK — API + M2M signal tests.

SESSION 261 / Phase 3.
"""
from __future__ import annotations

import pytest
from django.core.exceptions import ValidationError
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.embeddings.models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Universe
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(email="kd-uni@test.local", password="x")


@pytest.fixture
def workspace(user):
    ws = Workspace.objects.filter(owner=user).first() or Workspace.objects.create(
        name="KD WS", owner=user
    )
    Membership.objects.get_or_create(
        user=user, workspace=ws, defaults={"role": Membership.Role.OWNER}
    )
    return ws


@pytest.fixture
def client(user):
    c = APIClient()
    c.force_authenticate(user=user)
    return c


# ---- POST with universe -----------------------------------------------


@pytest.mark.django_db
def test_post_knowledge_with_universe_success(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    resp = client.post(
        "/api/knowledge/",
        data={
            "workspace": str(workspace.id),
            "universe": str(u.id),
            "title": "Workshop doc",
            "text_content": "workshop content",
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["universe"] == str(u.id)


@pytest.mark.django_db
def test_post_knowledge_without_universe_creates_legacy(client, workspace):
    """SUPERSEDED by Slice 20 Q-276-36 — the API previously accepted a
    CREATE payload with no Universe + no spokespeople + no
    ``audience_scope`` marker as a legacy NULL doc. Slice 20 closes
    that branch: the API now requires a positive audience signal.
    Supplying ``audience_scope="workspace"`` (the SPA's "None (legacy)"
    gesture per Slice 12 §189) still lands as a workspace-shared doc
    with ``universe=None``.
    """
    resp = client.post(
        "/api/knowledge/",
        data={
            "workspace": str(workspace.id),
            "title": "Legacy doc",
            "text_content": "legacy content",
            "audience_scope": "workspace",  # SESSION 276 Slice 20 marker
        },
        format="json",
    )
    assert resp.status_code == 201, resp.content
    body = resp.json()
    assert body["universe"] is None
    # audience_scope is write-only; verify via DB read.
    from apps.embeddings.models import KnowledgeDocument, AudienceScope
    doc = KnowledgeDocument.objects.get(pk=body["id"])
    assert doc.audience_scope == AudienceScope.WORKSPACE


@pytest.mark.django_db
def test_post_knowledge_universe_spokesperson_mismatch_rejected(client, workspace):
    """Universe D + legacy sp payload → 400 (Universe-M2M invariant)."""
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    legacy_sp = Teammate.objects.create(workspace=workspace, name="Legacy")

    resp = client.post(
        "/api/knowledge/",
        data={
            "workspace": str(workspace.id),
            "universe": str(u.id),
            "title": "Bad doc",
            "text_content": "content",
            "spokesperson_ids": [str(legacy_sp.id)],
        },
        format="json",
    )
    assert resp.status_code == 400, resp.content


@pytest.mark.django_db
def test_post_knowledge_cross_workspace_universe_rejected(client, workspace):
    """Universe FK to a different workspace's Universe → 400."""
    other_user = User.objects.create_user(email="other-kd@u.test", password="x")
    other_ws = Workspace.objects.filter(owner=other_user).first() or Workspace.objects.create(
        name="Other WS", owner=other_user
    )
    foreign_u = Universe.objects.create(workspace=other_ws, name="Foreign")

    resp = client.post(
        "/api/knowledge/",
        data={
            "workspace": str(workspace.id),
            "universe": str(foreign_u.id),
            "title": "Bad doc",
            "text_content": "content",
        },
        format="json",
    )
    assert resp.status_code == 400, resp.content


# ---- ?universe=<uuid> filter ------------------------------------------


@pytest.mark.django_db
def test_list_filter_by_universe(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    ws_doc = KnowledgeDocument.objects.create(
        workspace=workspace,
        universe=u,
        title="Workshop D",
        document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="wsd", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    legacy_doc = KnowledgeDocument.objects.create(
        workspace=workspace,
        title="Legacy D",
        document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="ld", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )

    resp = client.get(f"/api/knowledge/?workspace={workspace.id}&universe={u.id}")
    body = resp.json()
    results = body if isinstance(body, list) else body["results"]
    ids = {r["id"] for r in results}
    assert str(ws_doc.id) in ids
    assert str(legacy_doc.id) not in ids


@pytest.mark.django_db
def test_list_filter_universe_none_returns_legacy(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    ws_doc = KnowledgeDocument.objects.create(
        workspace=workspace, universe=u,
        title="Workshop D", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="wsd", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    legacy_doc = KnowledgeDocument.objects.create(
        workspace=workspace,
        title="Legacy D", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="ld", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )

    resp = client.get(f"/api/knowledge/?workspace={workspace.id}&universe=none")
    body = resp.json()
    results = body if isinstance(body, list) else body["results"]
    ids = {r["id"] for r in results}
    assert str(legacy_doc.id) in ids
    assert str(ws_doc.id) not in ids


# ---- attach action --------------------------------------------------


@pytest.mark.django_db
def test_attach_cross_universe_rejected(client, workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    other_u = Universe.objects.create(workspace=workspace, name="Bakery")

    doc = KnowledgeDocument.objects.create(
        workspace=workspace, universe=u,
        title="Workshop D", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="wsd", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    other_sp = Teammate.objects.create(
        workspace=workspace, name="Muffin", universe=other_u,
    )

    resp = client.post(
        f"/api/knowledge/{doc.id}/attach/",
        data={"spokesperson_id": str(other_sp.id)},
        format="json",
    )
    assert resp.status_code == 400, resp.content


# ---- signal receivers direct ORM path ----------------------------------


@pytest.mark.django_db
def test_signal_rejects_forward_cross_universe(workspace):
    """doc.spokespeople.add(sp) where sp.universe != doc.universe
    raises ValidationError."""
    u_x = Universe.objects.create(workspace=workspace, name="Workshop")
    u_y = Universe.objects.create(workspace=workspace, name="Bakery")
    doc = KnowledgeDocument.objects.create(
        workspace=workspace, universe=u_x,
        title="X", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="X", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    sp = Teammate.objects.create(workspace=workspace, name="Muffin", universe=u_y)
    with pytest.raises(ValidationError):
        doc.spokespeople.add(sp)


@pytest.mark.django_db
def test_signal_rejects_reverse_cross_universe(workspace):
    """sp.knowledge_documents.add(doc) where doc.universe !=
    sp.universe raises ValidationError."""
    u_x = Universe.objects.create(workspace=workspace, name="Workshop")
    u_y = Universe.objects.create(workspace=workspace, name="Bakery")
    doc = KnowledgeDocument.objects.create(
        workspace=workspace, universe=u_x,
        title="X", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="X", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    sp = Teammate.objects.create(workspace=workspace, name="Muffin", universe=u_y)
    with pytest.raises(ValidationError):
        sp.knowledge_documents.add(doc)


@pytest.mark.django_db
def test_signal_allows_matching_universe(workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    doc = KnowledgeDocument.objects.create(
        workspace=workspace, universe=u,
        title="X", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="X", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    sp = Teammate.objects.create(workspace=workspace, name="Patch", universe=u)
    doc.spokespeople.add(sp)  # no raise


@pytest.mark.django_db
def test_signal_allows_both_legacy(workspace):
    """Legacy sp attached to legacy doc — the classic pre-Universe
    pairing. Must remain allowed by both signal receivers."""
    doc = KnowledgeDocument.objects.create(
        workspace=workspace,
        title="X", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="X", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    sp = Teammate.objects.create(workspace=workspace, name="Legacy")
    doc.spokespeople.add(sp)  # no raise


@pytest.mark.django_db
def test_signal_rejects_legacy_sp_attached_to_universe_doc(workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    doc = KnowledgeDocument.objects.create(
        workspace=workspace, universe=u,
        title="X", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="X", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    sp = Teammate.objects.create(workspace=workspace, name="Legacy")
    with pytest.raises(ValidationError):
        doc.spokespeople.add(sp)


@pytest.mark.django_db
def test_signal_rejects_universe_sp_attached_to_legacy_doc(workspace):
    u = Universe.objects.create(workspace=workspace, name="Workshop")
    doc = KnowledgeDocument.objects.create(
        workspace=workspace,
        title="Legacy D", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="LD", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    sp = Teammate.objects.create(workspace=workspace, name="Patch", universe=u)
    with pytest.raises(ValidationError):
        doc.spokespeople.add(sp)


# ---- workspace signal still fires first (defense in depth) ---


@pytest.mark.django_db
def test_workspace_signal_still_fires_before_universe_signal(workspace):
    """Cross-workspace attach must still raise (workspace signal)
    even in the Universe world."""
    other_user = User.objects.create_user(email="cw-kd@u.test", password="x")
    other_ws = Workspace.objects.filter(owner=other_user).first() or Workspace.objects.create(
        name="Other", owner=other_user
    )
    doc = KnowledgeDocument.objects.create(
        workspace=workspace,
        title="Legacy D", document_type=DocumentType.TEXT,
        raw_content="x", processed_content="x",
        content_hash="LD", ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    foreign_sp = Teammate.objects.create(workspace=other_ws, name="Foreign")
    with pytest.raises(ValidationError):
        doc.spokespeople.add(foreign_sp)
