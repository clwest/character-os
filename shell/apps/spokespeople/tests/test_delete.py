"""SESSION 251 — customer-facing Teammate delete.

Contract locked here:

* Workspace owner can DELETE their own Teammate via
  ``DELETE /api/spokespeople/<id>/`` and gets a 204.
* Cross-workspace DELETE gets 404 (queryset filter hides the row
  from other workspaces).
* Deleted teammate is gone from LIST + retrieve returns 404.
* Knowledge M2M attachments are detached (CASCADE on the through
  row); the underlying ``KnowledgeDocument`` + chunks survive.
* Historical ``Composition`` + ``Asset`` rows survive, with
  ``spokesperson_id`` nulled per SESSION 251 SET_NULL migration.
* Historical ``RealtimeSession`` survives (+ its transcript
  ``Asset(TRANSCRIPT)``); ``spokesperson_id`` nulled.
* Historical ``Script`` and ``ConversationThread`` survive.
* Deletion never raises ``ProtectedError`` or crashes with a 500
  even when the teammate has compositions, sessions, scripts,
  campaigns, threads, and attached knowledge — everything the
  SESSION 251 SET_NULL migrations were designed to preserve.

If any of these assertions fails, the deletion contract is
broken. Do not "fix" the tests. Fix the model or the migration.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.campaigns.models import PersonalizedCampaign
from apps.compositions.models import Asset, AssetType, Composition
from apps.conversations.models import ConversationThread
from apps.embeddings.models import DocumentType, KnowledgeDocument
from apps.realtime.models import RealtimeSession
from apps.scripts.models import Script
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str) -> tuple[Workspace, "User"]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, user


def _make_teammate(ws: Workspace, *, name: str = "Delete Me") -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief="short brief",
    )


def _client_for(user) -> APIClient:
    c = APIClient()
    c.force_login(user)
    return c


# ---- 1. owner can delete ---------------------------------------------


def test_owner_can_delete_their_teammate():
    ws, user = _make_workspace("owner-delete@t")
    t = _make_teammate(ws)
    r = _client_for(user).delete(f"/api/spokespeople/{t.id}/")
    assert r.status_code == http.HTTP_204_NO_CONTENT
    assert not Teammate.objects.filter(pk=t.id).exists()


# ---- 2. cross-workspace protection ----------------------------------


def test_cannot_delete_another_workspaces_teammate():
    ws_a, user_a = _make_workspace("wsa@t")
    ws_b, _user_b = _make_workspace("wsb@t")
    t_b = _make_teammate(ws_b, name="Not Yours")
    r = _client_for(user_a).delete(f"/api/spokespeople/{t_b.id}/")
    # Queryset filter → row invisible to user_a → 404, not 403 (DRF
    # returns 404 rather than leak existence to non-members).
    assert r.status_code == http.HTTP_404_NOT_FOUND
    assert Teammate.objects.filter(pk=t_b.id).exists(), "must not delete"


# ---- 3. list + detail 404 after delete ------------------------------


def test_deleted_teammate_absent_from_list_and_detail():
    ws, user = _make_workspace("gone@t")
    keep = _make_teammate(ws, name="Keep")
    doomed = _make_teammate(ws, name="Doomed")
    c = _client_for(user)
    c.delete(f"/api/spokespeople/{doomed.id}/")

    listing = c.get("/api/spokespeople/")
    assert listing.status_code == http.HTTP_200_OK
    ids = {row["id"] for row in listing.json()}
    assert str(keep.id) in ids
    assert str(doomed.id) not in ids

    detail = c.get(f"/api/spokespeople/{doomed.id}/")
    assert detail.status_code == http.HTTP_404_NOT_FOUND


# ---- 4. knowledge M2M detached, doc survives ------------------------


def test_delete_detaches_knowledge_but_keeps_document():
    ws, user = _make_workspace("k-detach@t")
    t = _make_teammate(ws)
    doc = KnowledgeDocument.objects.create(
        workspace=ws,
        title="notes",
        document_type=DocumentType.TEXT,
        processed_content="body",
        content_hash="hash-k-detach",
        ingested_via="paste",
    )
    doc.spokespeople.add(t)
    assert doc.spokespeople.filter(pk=t.id).exists()

    _client_for(user).delete(f"/api/spokespeople/{t.id}/")

    doc.refresh_from_db()
    assert not doc.spokespeople.filter(pk=t.id).exists(), "M2M must detach"
    assert KnowledgeDocument.objects.filter(pk=doc.id).exists(), "doc must survive"


# ---- 5. compositions + assets survive with nulled attribution ------


def test_delete_preserves_compositions_and_assets_with_nulled_attribution():
    ws, user = _make_workspace("comp-survive@t")
    t = _make_teammate(ws)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=t,
        name="Historical render",
        template_kind="talking_head",
    )
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.CLIP,
        file_path="/tmp/x.mp4",
        spokesperson=t,
    )

    _client_for(user).delete(f"/api/spokespeople/{t.id}/")

    comp.refresh_from_db()
    asset.refresh_from_db()
    assert comp.spokesperson_id is None
    assert comp.workspace_id == ws.id
    assert comp.name == "Historical render"
    assert asset.spokesperson_id is None
    assert asset.workspace_id == ws.id


# ---- 6. realtime session + transcript survive -----------------------


def test_delete_preserves_realtime_session_and_transcript_asset():
    ws, user = _make_workspace("rt-survive@t")
    t = _make_teammate(ws)
    session = RealtimeSession.objects.create(
        workspace=ws,
        spokesperson=t,
    )
    transcript = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.TRANSCRIPT,
        file_path="/tmp/t.txt",
        spokesperson=t,
    )
    session.transcript_asset = transcript
    session.save(update_fields=["transcript_asset"])

    _client_for(user).delete(f"/api/spokespeople/{t.id}/")

    session.refresh_from_db()
    transcript.refresh_from_db()
    assert session.spokesperson_id is None
    assert session.workspace_id == ws.id
    assert session.transcript_asset_id == transcript.id
    assert transcript.spokesperson_id is None


# ---- 7. scripts, campaigns, threads survive -------------------------


def test_delete_preserves_scripts_campaigns_and_threads():
    ws, user = _make_workspace("hist@t")
    t = _make_teammate(ws)
    script = Script.objects.create(
        workspace=ws,
        spokesperson=t,
        name="Historical script",
        prompt="draft this",
    )
    campaign = PersonalizedCampaign.objects.create(
        workspace=ws,
        spokesperson=t,
        name="Historical campaign",
        template="Hi {name}",
    )
    thread = ConversationThread.objects.create(
        spokesperson=t,
        title="Historical thread",
    )

    _client_for(user).delete(f"/api/spokespeople/{t.id}/")

    for obj, kind in [(script, "script"), (campaign, "campaign"), (thread, "thread")]:
        obj.refresh_from_db()
        assert obj.spokesperson_id is None, f"{kind} should have nulled FK"
    assert Script.objects.filter(pk=script.id).exists()
    assert PersonalizedCampaign.objects.filter(pk=campaign.id).exists()
    assert ConversationThread.objects.filter(pk=thread.id).exists()


# ---- 8. no ProtectedError / no 500 with the full fan-out ------------


def test_delete_with_full_dependency_graph_succeeds_without_500():
    """Regression: before SESSION 251, Composition.spokesperson +
    RealtimeSession.spokesperson were PROTECT, which meant
    ``instance.delete()`` raised ``django.db.models.ProtectedError``
    → DRF returned an unhandled 500. Now everything SET_NULLs and
    the delete succeeds even with the full fan-out attached."""
    ws, user = _make_workspace("fanout@t")
    t = _make_teammate(ws)
    # All dependents at once.
    Composition.objects.create(
        workspace=ws, spokesperson=t, name="c", template_kind="talking_head"
    )
    RealtimeSession.objects.create(workspace=ws, spokesperson=t)
    Script.objects.create(workspace=ws, spokesperson=t, name="s", prompt="p")
    PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=t, name="p", template="Hi {name}"
    )
    ConversationThread.objects.create(spokesperson=t)
    doc = KnowledgeDocument.objects.create(
        workspace=ws,
        title="k",
        document_type=DocumentType.TEXT,
        processed_content="body",
        content_hash="hash-fanout",
        ingested_via="paste",
    )
    doc.spokespeople.add(t)

    r = _client_for(user).delete(f"/api/spokespeople/{t.id}/")
    assert r.status_code == http.HTTP_204_NO_CONTENT
    assert not Teammate.objects.filter(pk=t.id).exists()


# ---- 9. anonymous cannot delete -------------------------------------


def test_anonymous_delete_forbidden():
    ws, _user = _make_workspace("anon@t")
    t = _make_teammate(ws)
    r = APIClient().delete(f"/api/spokespeople/{t.id}/")
    assert r.status_code in (http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN)
    assert Teammate.objects.filter(pk=t.id).exists()
