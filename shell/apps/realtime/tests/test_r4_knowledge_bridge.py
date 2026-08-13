"""R4 tests — knowledge → Runway document bridge.

Three pieces this slice ships:

1. `compose_realtime_document(spokesperson)` — builds the
   markdown body + chunk_ids from K2 retrieval.
2. `MediaEngineClient.realtime_document_create()` — posts to
   the media-engine.
3. Broker create flow — composes doc → pushes to media-engine
   → persists `provider_document_id` + `knowledge_chunk_ids`
   on the session → passes `document_ids` into session
   create.

Covered:

* Composer with no knowledge → degraded body (business_brief
  only), empty chunk_ids.
* Composer with knowledge → chunks appear in markdown, ids
  collected.
* Composer respects max_chars (truncates tail chunks).
* Composer never raises on retrieval failure.
* Broker create persists `provider_document_id` +
  `knowledge_chunk_ids` when knowledge is available.
* Broker create still works for an empty-knowledge workspace
  (provider_document_id stays empty, chunk_ids empty list).
* Broker passes `document_ids=[provider_document_id]` into
  the session_create call.
* Composer ignores chunks from other workspaces (K0
  privacy holds end-to-end).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    EMBEDDING_DIMENSION,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.realtime.models import RealtimeSession
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import (
    RealtimeDocumentResult,
    RealtimeSessionResult,
)
from character_os.realtime_document import compose_realtime_document

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mocks():
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
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


def _make_teammate(
    ws: Workspace,
    *,
    name: str = "Sasha",
    brief: str = "Sells artisan bicycle bells.",
) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name, runway_avatar_id="av_test",
        portrait_path="https://fake/p.png",
        business_brief=brief,
    )


def _make_doc_with_chunks(
    ws: Workspace, *, title: str, chunks: list[str], seed: float = 0.9,
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


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- composer ---------------------------------------------------


def test_compose_no_knowledge_returns_brief_only() -> None:
    ws, _u = _make_workspace("r4nokno@test")
    sp = _make_teammate(ws)
    result = compose_realtime_document(sp)
    assert sp.business_brief in result.body
    assert sp.name in result.body
    assert "## Knowledge" not in result.body
    assert result.chunk_ids == []
    assert result.truncated is False


def test_compose_includes_chunks_and_returns_ids() -> None:
    ws, _u = _make_workspace("r4inkno@test")
    sp = _make_teammate(ws)
    _make_doc_with_chunks(
        ws, title="FAQ",
        chunks=[
            "Our spring launch starts in March.",
            "The early-bird discount is 20% off.",
        ],
        seed=0.99,
    )
    result = compose_realtime_document(sp, top_k=10)
    assert "## Knowledge" in result.body
    assert "### FAQ" in result.body
    assert "spring launch" in result.body.lower()
    assert "early-bird" in result.body.lower()
    assert len(result.chunk_ids) == 2
    assert result.truncated is False


def test_compose_respects_max_chars() -> None:
    """Tail chunks drop when the budget would be exceeded.
    The body still ends cleanly + truncated=True.

    The mandatory header (name + Conversation Style + Voice +
    About) is non-droppable platform infrastructure, so the
    budget test uses a max_chars sized to fit the header plus
    a handful of chunks, then verifies chunks at the tail drop.
    """
    ws, _u = _make_workspace("r4cap@test")
    sp = _make_teammate(ws)
    # Each chunk ~ 200 chars; with max_chars=2000 we fit the
    # mandatory header (~900 chars including the platform-wide
    # Conversation Style block) plus a few chunks, with the
    # tail forced to drop.
    big_chunks = ["A" * 200 for _ in range(10)]
    _make_doc_with_chunks(
        ws, title="Big", chunks=big_chunks, seed=0.95,
    )
    result = compose_realtime_document(sp, top_k=30, max_chars=2000)
    assert result.truncated is True
    assert result.chars <= 2000 + 50  # small over-shoot allowed
    assert len(result.chunk_ids) < 10


def test_compose_ignores_other_workspace_chunks() -> None:
    """K0 privacy holds. Workspace A's spokesperson should
    never see workspace B's chunks in the composed doc."""
    ws_a, _u = _make_workspace("r4xa@test", "A")
    ws_b, _u2 = _make_workspace("r4xb@test", "B")
    sp_a = _make_teammate(ws_a, name="A-speaker")
    _make_doc_with_chunks(
        ws_b, title="B-secret",
        chunks=["This is B-workspace private content."], seed=0.99,
    )
    result = compose_realtime_document(sp_a, top_k=30)
    assert "B-workspace private" not in result.body
    assert "B-secret" not in result.body
    assert result.chunk_ids == []


def test_compose_degrades_on_retrieval_failure() -> None:
    """Embedding service down / retrieval exception →
    business_brief-only doc. Avatar still functions with
    identity but no facts."""
    ws, _u = _make_workspace("r4ret@test")
    sp = _make_teammate(ws)
    with patch(
        "character_os.realtime_document.retrieve_for_teammate",
        side_effect=RuntimeError("embed down"),
    ):
        result = compose_realtime_document(sp)
    assert sp.business_brief in result.body
    assert "## Knowledge" not in result.body
    assert result.chunk_ids == []


# ---- broker create flow ------------------------------------------


def _patch_broker_clients(
    *, doc_id: str | None = "doc_123",
    session_id: str = "sess_xyz",
):
    """Patch the broker's MediaEngineClient. Returns the
    (patcher, fake_client) tuple."""
    fake = MagicMock()
    fake.realtime_document_create.return_value = RealtimeDocumentResult(
        document_id=doc_id or "doc_default", mock_mode=True,
    )
    fake.realtime_session_create.return_value = RealtimeSessionResult(
        session_id=session_id,
        session_key="eyJ.session.token",
        status="ready",
        expires_at=None,
        avatar_id="av_test",
        mock_mode=True,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    patcher = patch(
        "apps.realtime.views.MediaEngineClient", return_value=cm,
    )
    return patcher, fake


def test_broker_create_persists_provider_document_id() -> None:
    ws, user = _make_workspace("r4brokerdoc@test")
    sp = _make_teammate(ws)
    _make_doc_with_chunks(
        ws, title="Pricing",
        chunks=["Premium tier is $99/mo.", "Free tier covers 5 sessions."],
        seed=0.99,
    )
    client = APIClient()
    _login(client, user)
    patcher, fake = _patch_broker_clients(doc_id="doc_pricing")
    with patcher:
        # `real_mode=True` — SESSION 227 P1 2.8-b flipped the
        # server default to draft-only, which skips the doc-push +
        # session-create round trip. Provider-document tests only
        # exercise the paid path.
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    session_id = response.json()["id"]
    session = RealtimeSession.objects.get(id=session_id)
    assert session.provider_document_id == "doc_pricing"
    assert len(session.knowledge_chunk_ids) == 2


def test_broker_passes_document_ids_to_session_create() -> None:
    ws, user = _make_workspace("r4ids@test")
    sp = _make_teammate(ws)
    _make_doc_with_chunks(
        ws, title="One", chunks=["Single chunk."], seed=0.99,
    )
    client = APIClient()
    _login(client, user)
    patcher, fake = _patch_broker_clients(doc_id="doc_one")
    with patcher:
        # Paid-path assertion — draft mode never calls the
        # media-engine, so `real_mode=True` is load-bearing.
        client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    fake.realtime_document_create.assert_called_once()
    fake.realtime_session_create.assert_called_once()
    session_kwargs = fake.realtime_session_create.call_args.kwargs
    assert session_kwargs["document_ids"] == ["doc_one"]


def test_broker_create_works_without_knowledge() -> None:
    """Empty-knowledge workspace still produces a usable
    session — composer returns a business_brief-only body,
    media-engine still creates a (small) doc, and the
    session gets bound to it."""
    ws, user = _make_workspace("r4empty@test")
    sp = _make_teammate(ws)
    # No KnowledgeDocument rows in this workspace.
    client = APIClient()
    _login(client, user)
    patcher, fake = _patch_broker_clients(doc_id="doc_empty")
    with patcher:
        # Paid-path — the empty-knowledge composer still
        # produces a header + brief, so the doc-push happens
        # only when `real_mode=True`.
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED
    session_id = response.json()["id"]
    session = RealtimeSession.objects.get(id=session_id)
    # The composer always produces SOME body (header + brief),
    # so a document IS created even for empty-knowledge
    # workspaces.
    assert session.provider_document_id == "doc_empty"
    # Empty chunk_ids list because retrieval returned no
    # chunks.
    assert session.knowledge_chunk_ids == []


def test_broker_chunk_ids_match_composer_output() -> None:
    """End-to-end provenance — the chunk_ids persisted on
    RealtimeSession should match what the composer
    extracted from retrieval."""
    ws, user = _make_workspace("r4provenance@test")
    sp = _make_teammate(ws)
    doc = _make_doc_with_chunks(
        ws, title="Audit",
        chunks=["Chunk A.", "Chunk B.", "Chunk C."],
        seed=0.99,
    )
    composer_result = compose_realtime_document(sp, top_k=10)
    expected_ids = composer_result.chunk_ids
    assert len(expected_ids) == 3

    client = APIClient()
    _login(client, user)
    patcher, _ = _patch_broker_clients(doc_id="doc_audit")
    with patcher:
        # Provenance persistence lives on the paid path.
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED
    session = RealtimeSession.objects.get(id=response.json()["id"])
    # Both lists should contain the same chunk ids (order may
    # not match — set comparison is the load-bearing check
    # for provenance).
    assert set(session.knowledge_chunk_ids) == set(expected_ids)


def test_broker_create_passes_document_name_with_spokesperson() -> None:
    ws, user = _make_workspace("r4docname@test")
    sp = _make_teammate(ws, name="Riggs")
    _make_doc_with_chunks(ws, title="X", chunks=["one"], seed=0.99)
    client = APIClient()
    _login(client, user)
    patcher, fake = _patch_broker_clients()
    with patcher:
        # Doc-name propagation is a paid-path concern.
        client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    doc_kwargs = fake.realtime_document_create.call_args.kwargs
    assert "Riggs" in doc_kwargs["name"]
