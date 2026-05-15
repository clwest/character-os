"""R7.1 tests — three sync tools + tier-aware filtering.

What this slice ships:

1. Three new sync tools registered in
   ``apps/realtime/tools/``:
   * ``recall_knowledge`` (starter tier; RAG via
     K2 retrieval).
   * ``recall_recent_conversations`` (starter tier;
     prior `Asset(TRANSCRIPT)` reader).
   * ``handoff_to_spokesperson`` (pro tier;
     cross-spokesperson nav with workspace-scope check).

2. ``ToolSpec.tier_required`` field + ``register_tool``
   kwarg + ``_TIER_RANK`` / ``_tier_rank`` helpers.

3. ``get_workspace_tools(workspace)`` filters by
   workspace tier — Starter sees only starter-tier
   tools; Pro/Agency see all.

4. Defense-in-depth tier check inside ``dispatch_tool``
   — rejects with 403 when a workspace tries to invoke
   an over-tier tool (e.g., a buggy SPA bypassing the
   catalog filter).

5. ``apps.billing.services.get_workspace_tier`` public
   helper.

Covered (17 tests):

* Tier filtering: Starter / Pro / Agency catalogs.
* Tier registry: ``ToolSpec.tier_required`` defaults to
  ``starter``.
* Dispatch tier gate: starter invoking pro tool → 403.
* `recall_knowledge` happy path + empty-query rejection
  + workspace-scoped privacy (other-workspace chunks
  excluded).
* `recall_recent_conversations` happy path +
  current-session exclusion + ENDED-only filter +
  cross-workspace exclusion.
* `handoff_to_spokesperson` happy path + missing
  target rejection + same-spokesperson rejection +
  cross-workspace rejection.
* REST integration: `recall_knowledge` end-to-end
  through ``POST /invoke_tool/``.
"""
from __future__ import annotations

from datetime import datetime, timezone

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.billing.models import Subscription
from apps.compositions.models import Asset, AssetType
from apps.embeddings.models import (
    EMBEDDING_DIMENSION,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.realtime.dispatch import DispatchError, dispatch_tool
from apps.realtime.models import RealtimeSession
from apps.realtime.tools import get_workspace_tools, list_tools
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mocks():
    """Force-mock embeddings so `recall_knowledge` test
    paths don't need a real OpenAI key."""
    with override_settings(EMBEDDING_FORCE_MOCK=True):
        yield


def _vec(seed: float) -> list[float]:
    v = [0.0] * EMBEDDING_DIMENSION
    v[0] = seed
    return v


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _set_tier(workspace: Workspace, tier: str) -> None:
    """Set the workspace's subscription tier. Creates a
    Subscription row if one doesn't exist (mirrors the
    behavior of `apps.billing.services._subscription_for`)."""
    sub, _ = Subscription.objects.get_or_create(
        workspace=workspace,
        defaults={
            "tier": tier,
            "status": Subscription.Status.ACTIVE,
        },
    )
    sub.tier = tier
    sub.save()


def _make_spokesperson(
    ws: Workspace, *, name: str = "Sasha", brief: str = "brief",
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id="av_test",
        portrait_path="https://fake/p.png", business_brief=brief,
    )


def _make_session(ws: Workspace, sp: Spokesperson) -> RealtimeSession:
    return RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.READY,
        provider_session_id="rt_x",
    )


def _make_doc_with_chunks(
    ws: Workspace, *, title: str, chunks: list[str], seed: float = 0.99,
) -> KnowledgeDocument:
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        ingested_via=IngestedVia.PASTE,
        raw_content="\n\n".join(chunks),
        processed_content="\n\n".join(chunks),
        content_hash=f"hash-{title}-{seed}",
        status=DocumentStatus.PROCESSED,
    )
    for i, text in enumerate(chunks):
        KnowledgeChunk.objects.create(
            document=doc,
            chunk_index=i,
            chunk_text=text,
            chunk_size=len(text),
            embedding_vector=_vec(seed),
        )
    return doc


def _make_transcript_asset(
    ws: Workspace, *, text: str,
) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.TRANSCRIPT,
        file_path="",
        inline_content=text,
        source_spec={"primitive_kind": "realtime_transcript"},
        mime_type="text/plain",
        size_bytes=len(text.encode("utf-8")),
    )


def _make_ended_session(
    ws: Workspace, sp: Spokesperson, *,
    transcript_text: str,
    ended_at: datetime | None = None,
) -> RealtimeSession:
    asset = _make_transcript_asset(ws, text=transcript_text)
    return RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.ENDED,
        provider_session_id="rt_ended",
        transcript_asset=asset,
        ended_at=ended_at or datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        duration_seconds=180,
    )


# ---- tier filtering ---------------------------------------------


def test_starter_workspace_catalog_excludes_pro_tools():
    ws, _u = _make_workspace("r71st@test")
    _set_tier(ws, "starter")
    catalog = {t.name for t in get_workspace_tools(ws)}
    assert "show_videos_tab" in catalog
    assert "recall_knowledge" in catalog
    assert "recall_recent_conversations" in catalog
    # handoff_to_spokesperson is pro-only
    assert "handoff_to_spokesperson" not in catalog


def test_pro_workspace_catalog_includes_pro_tools():
    ws, _u = _make_workspace("r71pro@test")
    _set_tier(ws, "pro")
    catalog = {t.name for t in get_workspace_tools(ws)}
    assert "handoff_to_spokesperson" in catalog
    # Pro sees everything starter sees too.
    assert {"show_videos_tab", "recall_knowledge",
            "recall_recent_conversations"} <= catalog


def test_agency_workspace_catalog_full():
    ws, _u = _make_workspace("r71ag@test")
    _set_tier(ws, "agency")
    catalog = {t.name for t in get_workspace_tools(ws)}
    # Agency sees every registered tool.
    expected = {t.name for t in list_tools()}
    assert catalog == expected


def test_tool_default_tier_required_is_starter():
    """show_videos_tab + recall_knowledge etc. don't pass
    tier_required explicitly; they should default to
    starter."""
    from apps.realtime.tools import get_tool
    assert get_tool("show_videos_tab").tier_required == "starter"
    assert get_tool("recall_knowledge").tier_required == "starter"
    assert get_tool("recall_recent_conversations").tier_required == "starter"
    assert get_tool("handoff_to_spokesperson").tier_required == "pro"


# ---- dispatch tier defense in depth ------------------------------


def test_dispatch_rejects_overtier_tool_with_403():
    """Starter workspace invoking a Pro tool → DispatchError
    with http_status=403. Defense in depth — even if the
    catalog filter is bypassed (buggy SPA, direct REST
    call), the dispatcher refuses."""
    ws, user = _make_workspace("r71over@test")
    _set_tier(ws, "starter")
    sp = _make_spokesperson(ws)
    other = _make_spokesperson(ws, name="Donny")
    session = _make_session(ws, sp)
    with pytest.raises(DispatchError) as ctx:
        dispatch_tool(
            session, "handoff_to_spokesperson",
            {"target_spokesperson_id": str(other.id)},
            user=user,
        )
    assert ctx.value.http_status == 403


# ---- recall_knowledge -------------------------------------------


def test_recall_knowledge_returns_chunks():
    ws, user = _make_workspace("r71rk1@test")
    sp = _make_spokesperson(ws)
    _make_doc_with_chunks(
        ws, title="Pricing",
        chunks=["Premium tier is $99/mo.", "Free tier covers 5 sessions."],
    )
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "recall_knowledge", {"query": "pricing"}, user=user,
    )
    assert result.state == "succeeded"
    payload = result.result
    assert payload["query"] == "pricing"
    assert payload["count"] >= 1
    assert any("Premium" in m["text"] for m in payload["matches"])
    # Document title flows through
    assert any(m["document_title"] == "Pricing" for m in payload["matches"])


def test_recall_knowledge_empty_query_failed():
    ws, user = _make_workspace("r71rk2@test")
    sp = _make_spokesperson(ws)
    _make_doc_with_chunks(ws, title="X", chunks=["something"])
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "recall_knowledge", {"query": "   "}, user=user,
    )
    assert result.state == "failed"
    assert "query is required" in result.error_message


def test_recall_knowledge_other_workspace_chunks_excluded():
    """Workspace A's spokesperson must never surface
    workspace B's chunks through `recall_knowledge`.
    Privacy parity with K0."""
    ws_a, user_a = _make_workspace("r71rkx1@test", "A")
    ws_b, _ub = _make_workspace("r71rkx2@test", "B")
    sp_a = _make_spokesperson(ws_a)
    _make_doc_with_chunks(
        ws_b, title="B-secret",
        chunks=["This is B-workspace private content."],
    )
    session_a = _make_session(ws_a, sp_a)
    result = dispatch_tool(
        session_a, "recall_knowledge", {"query": "anything"},
        user=user_a,
    )
    payload = result.result
    for match in payload["matches"]:
        assert "B-workspace private" not in match["text"]
        assert match["document_title"] != "B-secret"


# ---- recall_recent_conversations --------------------------------


def test_recall_recent_conversations_returns_prior_sessions():
    ws, user = _make_workspace("r71rc1@test")
    sp = _make_spokesperson(ws)
    older = _make_ended_session(
        ws, sp, transcript_text="Older talk about bicycles.",
        ended_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
    )
    newer = _make_ended_session(
        ws, sp, transcript_text="Newer talk about brakes.",
        ended_at=datetime(2026, 5, 13, 12, 0, tzinfo=timezone.utc),
    )
    current = _make_session(ws, sp)
    result = dispatch_tool(
        current, "recall_recent_conversations", {}, user=user,
    )
    assert result.state == "succeeded"
    payload = result.result
    assert payload["count"] == 2
    # Newest first
    assert payload["sessions"][0]["session_id"] == str(newer.id)
    assert payload["sessions"][1]["session_id"] == str(older.id)
    assert "brakes" in payload["sessions"][0]["preview"]


def test_recall_recent_conversations_excludes_current_session():
    """The current in-progress session must NOT appear in
    its own recall — the avatar shouldn't quote itself."""
    ws, user = _make_workspace("r71rc2@test")
    sp = _make_spokesperson(ws)
    # Mark current as ENDED + give it a transcript, to
    # confirm the exclusion is by-pk not by-status.
    current = _make_ended_session(
        ws, sp, transcript_text="This is the current session.",
    )
    result = dispatch_tool(
        current, "recall_recent_conversations", {}, user=user,
    )
    payload = result.result
    assert payload["count"] == 0


def test_recall_recent_conversations_only_ended_sessions():
    """READY/CREATING/FAILED sessions are excluded — only
    completed conversations count."""
    ws, user = _make_workspace("r71rc3@test")
    sp = _make_spokesperson(ws)
    for st in (
        RealtimeSession.Status.READY,
        RealtimeSession.Status.CREATING,
        RealtimeSession.Status.FAILED,
    ):
        RealtimeSession.objects.create(
            workspace=ws, spokesperson=sp, status=st,
            transcript_asset=_make_transcript_asset(
                ws, text="should not surface",
            ),
        )
    current = _make_session(ws, sp)
    result = dispatch_tool(
        current, "recall_recent_conversations", {}, user=user,
    )
    payload = result.result
    assert payload["count"] == 0


def test_recall_recent_conversations_other_workspace_excluded():
    ws_a, user_a = _make_workspace("r71rcx1@test", "A")
    ws_b, _ub = _make_workspace("r71rcx2@test", "B")
    sp_a = _make_spokesperson(ws_a, name="A-speaker")
    sp_b = _make_spokesperson(ws_b, name="B-speaker")
    _make_ended_session(
        ws_b, sp_b, transcript_text="B-workspace conversation",
    )
    session_a = _make_session(ws_a, sp_a)
    result = dispatch_tool(
        session_a, "recall_recent_conversations", {}, user=user_a,
    )
    payload = result.result
    assert payload["count"] == 0


# ---- handoff_to_spokesperson ------------------------------------


def test_handoff_to_spokesperson_happy_path():
    ws, user = _make_workspace("r71h1@test")
    _set_tier(ws, "pro")  # handoff is pro-only
    sp = _make_spokesperson(ws, name="Sasha")
    target = _make_spokesperson(ws, name="Donny")
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "handoff_to_spokesperson",
        {"target_spokesperson_id": str(target.id)},
        user=user,
    )
    assert result.state == "succeeded"
    payload = result.result
    assert payload["event"] == "handoff_to_spokesperson"
    assert payload["target_spokesperson_id"] == str(target.id)
    assert payload["target_spokesperson_name"] == "Donny"
    assert "Donny" in payload["message"]


def test_handoff_missing_target_failed():
    ws, user = _make_workspace("r71h2@test")
    _set_tier(ws, "pro")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "handoff_to_spokesperson", {}, user=user,
    )
    assert result.state == "failed"
    assert "target_spokesperson_id" in result.error_message


def test_handoff_same_spokesperson_failed():
    ws, user = _make_workspace("r71h3@test")
    _set_tier(ws, "pro")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "handoff_to_spokesperson",
        {"target_spokesperson_id": str(sp.id)},
        user=user,
    )
    assert result.state == "failed"
    assert "same spokesperson" in result.error_message


def test_handoff_cross_workspace_failed():
    ws_a, user_a = _make_workspace("r71h4a@test", "A")
    ws_b, _ub = _make_workspace("r71h4b@test", "B")
    _set_tier(ws_a, "pro")
    sp_a = _make_spokesperson(ws_a, name="A-speaker")
    sp_b = _make_spokesperson(ws_b, name="B-speaker")
    session = _make_session(ws_a, sp_a)
    result = dispatch_tool(
        session, "handoff_to_spokesperson",
        {"target_spokesperson_id": str(sp_b.id)},
        user=user_a,
    )
    # Cross-workspace target appears "not found" — the
    # error message intentionally doesn't leak existence
    # of other-workspace spokespeople.
    assert result.state == "failed"
    assert "not in this workspace" in result.error_message


# ---- REST integration -------------------------------------------


def test_invoke_recall_knowledge_endpoint():
    """End-to-end through `POST /api/realtime_sessions/<id>/invoke_tool/`.
    Confirms the dispatcher's args + result wiring works
    through the REST surface, not just the Python entry."""
    ws, user = _make_workspace("r71rest@test")
    sp = _make_spokesperson(ws)
    _make_doc_with_chunks(
        ws, title="Hours", chunks=["Open Mon-Fri 9-5."],
    )
    session = _make_session(ws, sp)
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "recall_knowledge", "args": {"query": "hours"}},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    payload = response.json()
    assert payload["state"] == "succeeded"
    assert payload["result"]["count"] >= 1
    assert "Open Mon-Fri" in payload["result"]["matches"][0]["text"]
