"""Chapter 6 slice-1 — spokesperson Ask + receipt (SESSION 234).

Locks the contract for ``POST /api/spokespeople/{id}/ask/`` and
the ``ask_teammate`` synthesis helper it delegates to.

Ship bar exercised here: **no fabricated citations.** When
retrieval matches, the response's ``citations`` name only docs
whose chunks were placed in the model context; when retrieval
returns nothing, ``citations`` is empty and ``used_knowledge``
is False. There is no synthesis path that produces citations
without corresponding chunks.

Force-mock (``SPOKESPERSON_ASK_FORCE_MOCK=1``) is the default in
these tests — retrieval runs against real workspace data (so
citation dedup + workspace-scope filter are exercised) but the
LLM call is skipped. The mock answer echoes the question + doc
titles so citation flow is assertable without OpenAI credits.
"""
from __future__ import annotations

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
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
    # Skip the LLM but keep retrieval real — same discipline as
    # K6's force-mock test env (RENDER_SCRIPT_FORCE_MOCK).
    pytest.mark.usefixtures("_ask_force_mock"),
]


@pytest.fixture
def _ask_force_mock():
    with override_settings(SPOKESPERSON_ASK_FORCE_MOCK=True):
        yield


# ---- helpers --------------------------------------------------------


def _vec(seed: float) -> list[float]:
    v = [0.0] * EMBEDDING_DIMENSION
    v[0] = seed
    return v


def _make_workspace(email: str) -> tuple[Workspace, "User"]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, user


def _make_teammate(ws: Workspace, *, name: str = "Oliver") -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief="Small-batch coffee roaster in Boulder.",
        tone_archetype="expert",
    )


def _make_doc(
    ws: Workspace,
    title: str,
    *,
    chunk_count: int = 1,
    seed: float = 0.5,
) -> tuple[KnowledgeDocument, list[KnowledgeChunk]]:
    doc = KnowledgeDocument.objects.create(
        workspace=ws,
        title=title,
        document_type=DocumentType.TEXT,
        ingested_via=IngestedVia.PASTE,
        raw_content="x",
        processed_content="x",
        content_hash=f"hash-{title}-{seed}",
        status=DocumentStatus.PROCESSED,
    )
    chunks = [
        KnowledgeChunk.objects.create(
            document=doc,
            chunk_index=i,
            chunk_text=f"chunk-{i} of {title}",
            chunk_size=20,
            embedding_vector=_vec(seed),
        )
        for i in range(chunk_count)
    ]
    return doc, chunks


def _auth(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def _ask(client: APIClient, sp_id, question: str):
    return client.post(
        f"/api/spokespeople/{sp_id}/ask/",
        {"question": question},
        format="json",
    )


# ---- endpoint: input validation ------------------------------------


def test_ask_blank_question_returns_400() -> None:
    ws, user = _make_workspace("ask-blank@t")
    sp = _make_teammate(ws)
    client = _auth(user)
    resp = _ask(client, sp.pk, "")
    assert resp.status_code == http.HTTP_400_BAD_REQUEST
    assert resp.data["code"] == "missing_question"


def test_ask_whitespace_only_returns_400() -> None:
    """Server strips before validating — a copy-paste stray space
    is not a question."""
    ws, user = _make_workspace("ask-ws-only@t")
    sp = _make_teammate(ws)
    client = _auth(user)
    resp = _ask(client, sp.pk, "   \n\t  ")
    assert resp.status_code == http.HTTP_400_BAD_REQUEST
    assert resp.data["code"] == "missing_question"


def test_ask_missing_body_returns_400() -> None:
    ws, user = _make_workspace("ask-missing@t")
    sp = _make_teammate(ws)
    client = _auth(user)
    resp = client.post(f"/api/spokespeople/{sp.pk}/ask/", {}, format="json")
    assert resp.status_code == http.HTTP_400_BAD_REQUEST


# ---- endpoint: workspace scope -------------------------------------


def test_ask_cross_workspace_returns_404() -> None:
    """User A cannot ask a spokesperson in workspace B. The
    viewset queryset filter enforces this — same guarantee as
    every other action on TeammateViewSet."""
    ws_a, user_a = _make_workspace("ask-a@t")
    ws_b, _user_b = _make_workspace("ask-b@t")
    sp_b = _make_teammate(ws_b, name="OtherWorkspaceSpokesperson")
    client = _auth(user_a)
    resp = _ask(client, sp_b.pk, "what do you sell?")
    assert resp.status_code == http.HTTP_404_NOT_FOUND


def test_ask_citations_only_include_own_workspace_docs() -> None:
    """A doc in workspace B whose chunk happens to be
    high-similarity to the query must not surface as a citation
    for a spokesperson in workspace A. Load-bearing K0 privacy
    guarantee — the receipt is the only signal the operator sees
    about which docs Oliver read.
    """
    ws_a, user_a = _make_workspace("ask-scope-a@t")
    ws_b, _ = _make_workspace("ask-scope-b@t")

    sp_a = _make_teammate(ws_a, name="OliverA")

    # Doc in own workspace — should surface.
    doc_own, _ = _make_doc(ws_a, "About Hearth & Hollow Books")
    # Doc in foreign workspace — must NOT surface, even with
    # identical embedding.
    _make_doc(ws_b, "Foreign Workspace Secret")

    client = _auth(user_a)
    resp = _ask(client, sp_a.pk, "what do you sell?")
    assert resp.status_code == http.HTTP_200_OK
    titles = [c["title"] for c in resp.data["citations"]]
    assert "About Hearth & Hollow Books" in titles
    assert "Foreign Workspace Secret" not in titles
    assert str(doc_own.id) in {c["document_id"] for c in resp.data["citations"]}


# ---- endpoint: honest-fallback shape -------------------------------


def test_ask_no_chunks_returns_honest_fallback() -> None:
    """No knowledge docs in the workspace → response signals
    honest fallback: ``used_knowledge=False``, empty
    ``citations``, answer names the honest-fallback text.
    Ship bar (no fabricated citations) enforced here.
    """
    ws, user = _make_workspace("ask-empty@t")
    sp = _make_teammate(ws, name="Oliver")
    client = _auth(user)
    resp = _ask(client, sp.pk, "what do you sell?")
    assert resp.status_code == http.HTTP_200_OK
    assert resp.data["used_knowledge"] is False
    assert resp.data["citations"] == []
    # Copy asserts the honest-fallback voicing (Character OS
    # neutral, name-interpolated).
    assert "Oliver" in resp.data["answer"]
    assert "already knows" in resp.data["answer"]


# ---- endpoint: citation dedup shape --------------------------------


def test_ask_citations_dedupe_by_document() -> None:
    """A doc with N chunks retrieved shows up once in citations
    with ``chunk_count = N``. Matches F6's dedup contract so the
    receipt renders "3 chunks from About Hearth" style — most-
    cited-first ordering is preserved by first-hit rank.
    """
    ws, user = _make_workspace("ask-dedup@t")
    sp = _make_teammate(ws)
    _make_doc(ws, "Store Hours", chunk_count=3, seed=0.9)
    client = _auth(user)
    resp = _ask(client, sp.pk, "when are you open?")
    assert resp.status_code == http.HTTP_200_OK
    assert resp.data["used_knowledge"] is True
    docs = resp.data["citations"]
    assert len(docs) == 1
    assert docs[0]["title"] == "Store Hours"
    assert docs[0]["chunk_count"] == 3


def test_ask_citations_span_multiple_docs() -> None:
    """When retrieval pulls chunks from multiple docs, each
    appears once with its own chunk_count. Design lock: 'multiple
    docs: receipt names each, comma-separated, most-cited first.'
    """
    ws, user = _make_workspace("ask-multi@t")
    sp = _make_teammate(ws)
    _make_doc(ws, "About Hearth & Hollow", chunk_count=2, seed=0.9)
    _make_doc(ws, "Store Hours", chunk_count=1, seed=0.8)
    _make_doc(ws, "Return Policy", chunk_count=2, seed=0.7)
    client = _auth(user)
    resp = _ask(client, sp.pk, "tell me about the store")
    assert resp.status_code == http.HTTP_200_OK
    titles = {c["title"] for c in resp.data["citations"]}
    # Top-5 retrieval covers all three docs (2 + 1 + 2 = 5).
    assert titles == {"About Hearth & Hollow", "Store Hours", "Return Policy"}


# ---- helper: honest-fallback branch reached from failures ----------


def test_honest_fallback_when_only_unprocessed_docs() -> None:
    """A workspace with a doc in ``status=pending`` (Celery
    worker never processed it) must NOT surface citations —
    unprocessed chunks are excluded by retrieve_for_teammate.
    Matches the SESSION 233 boot pathology (6 KDs sat pending
    because the worker was down); Chapter 6's ship bar depends
    on this staying tight."""
    ws, user = _make_workspace("ask-pending@t")
    sp = _make_teammate(ws)
    # Doc + chunk exist but doc status is PENDING (worker never
    # advanced it). Retrieval filters on document__status=processed.
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title="Uploaded but not processed",
        document_type=DocumentType.TEXT,
        ingested_via=IngestedVia.PASTE,
        raw_content="x", processed_content="x",
        content_hash="hash-pending",
        status=DocumentStatus.PENDING,
    )
    KnowledgeChunk.objects.create(
        document=doc, chunk_index=0,
        chunk_text="unprocessed", chunk_size=12,
        embedding_vector=_vec(0.9),
    )
    client = _auth(user)
    resp = _ask(client, sp.pk, "what did i upload?")
    assert resp.status_code == http.HTTP_200_OK
    assert resp.data["used_knowledge"] is False
    assert resp.data["citations"] == []


# ---- direct helper coverage ----------------------------------------


def test_ask_spokesperson_helper_direct_call_no_chunks() -> None:
    """The synthesis helper (imported directly) returns the
    honest-fallback AskResult shape for an empty workspace —
    covers the code path an internal caller might take without
    the viewset."""
    from character_os.teammate_ask import ask_teammate

    ws, _ = _make_workspace("ask-helper-empty@t")
    sp = _make_teammate(ws, name="Sasha")
    result = ask_teammate(sp, "what do you sell?")
    assert result.used_knowledge is False
    assert result.citations == []
    assert "Sasha" in result.answer


def test_ask_spokesperson_helper_blank_question_returns_fallback() -> None:
    """Helper defends against a blank question even though the
    viewset filters upstream — belt + suspenders."""
    from character_os.teammate_ask import ask_teammate

    ws, _ = _make_workspace("ask-helper-blank@t")
    sp = _make_teammate(ws)
    result = ask_teammate(sp, "   ")
    assert result.used_knowledge is False
    assert result.citations == []
