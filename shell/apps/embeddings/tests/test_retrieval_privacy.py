"""K2 privacy-guarantee tests.

Named in ``docs/design/KNOWLEDGE_LAYER.md`` §"How to verify the
privacy guarantee" — these three tests are the load-bearing
contract for the knowledge layer. Implementation can vary;
these tests cannot fail.

* ``test_cross_workspace_chunk_isolation``: querying for a
  spokesperson never returns chunks from another workspace,
  even when those chunks are a closer vector match.
* ``test_cross_thread_conversation_isolation``: querying for a
  thread never returns conversation embeddings from another
  thread, even within the same workspace.
* ``test_only_retrieval_module_queries_chunk_tables``: a
  repo-level grep test ensures no code outside the sanctioned
  retrieval module imports the chunk-level models. Privacy
  by construction depends on the surface staying narrow.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

from apps.accounts.models import Workspace
from apps.conversations.models import (
    ConversationEmbedding,
    ConversationMessage,
    ConversationThread,
)
from apps.embeddings.models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.embeddings.retrieval import (
    retrieve_for_teammate,
    retrieve_for_thread,
)
from apps.spokespeople.models import Teammate
from django.contrib.auth import get_user_model

User = get_user_model()


# ---- helpers --------------------------------------------------------

EMBEDDING_DIM = 1536


def _vec(seed: float) -> list[float]:
    """1536-dim vector with a known first component. The first
    component dominates cosine distance for unit-ish vectors,
    so we can engineer near-perfect matches predictably."""
    v = [0.0] * EMBEDDING_DIM
    v[0] = seed
    return v


def _make_workspace(user_email: str, ws_name: str) -> Workspace:
    """Create a User + Workspace pair. The post_save signal on
    User would normally auto-create the workspace; we let the
    signal fire then look up the workspace it produced (the
    signal naming honors the user's email prefix)."""
    user = User.objects.create_user(email=user_email, password="x")
    # The accounts.signals.ensure_default_workspace receiver
    # created a workspace owned by this user. Pull it.
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None, "signal failed to create workspace"
    ws.name = ws_name
    ws.save()
    return ws


def _make_teammate(ws: Workspace, name: str) -> Teammate:
    return Teammate.objects.create(workspace=ws, name=name)


def _make_doc_with_chunk(
    ws: Workspace,
    title: str,
    text: str,
    vector: list[float],
    spokespeople: list[Teammate] | None = None,
) -> KnowledgeDocument:
    """Create a processed KnowledgeDocument with one chunk
    bearing the supplied vector. Optional spokesperson M2M
    attach narrows visibility."""
    doc = KnowledgeDocument.objects.create(
        workspace=ws,
        title=title,
        document_type=DocumentType.TEXT,
        raw_content=text,
        processed_content=text,
        content_hash=f"hash-{title}",
        ingested_via=IngestedVia.PASTE,
        status=DocumentStatus.PROCESSED,
    )
    if spokespeople:
        doc.spokespeople.set(spokespeople)
    KnowledgeChunk.objects.create(
        document=doc,
        chunk_index=0,
        chunk_text=text,
        chunk_size=len(text),
        embedding_vector=vector,
    )
    return doc


# ---- the three guarantees ------------------------------------------


@pytest.mark.django_db
def test_cross_workspace_chunk_isolation() -> None:
    """A query for a spokesperson in workspace A must NEVER
    return chunks from workspace B, even when the workspace-B
    chunk is a perfect vector match.
    """
    ws_a = _make_workspace("alice@privacy.test", "Alice's WS")
    ws_b = _make_workspace("bob@privacy.test", "Bob's WS")

    sp_a = _make_teammate(ws_a, "Riggs A")
    sp_b = _make_teammate(ws_b, "Riggs B")  # never queried

    # Both workspaces have a doc with the SAME embedding vector —
    # the only thing distinguishing them is the workspace anchor.
    same_vector = _vec(1.0)
    doc_a = _make_doc_with_chunk(ws_a, "A doc", "alice content", same_vector)
    doc_b = _make_doc_with_chunk(ws_b, "B doc", "bob content", same_vector)

    # Query as Alice's spokesperson.
    results = retrieve_for_teammate(sp_a, _query_vector=same_vector, top_k=10)

    # Should return doc A's chunk, never doc B's.
    result_doc_ids = {chunk.document_id for chunk in results}
    assert doc_a.id in result_doc_ids
    assert doc_b.id not in result_doc_ids
    # Bob's spokesperson was never used — guard against accidental scope.
    assert sp_b not in [r.document.spokespeople.first() for r in results if r.document.spokespeople.exists()]


@pytest.mark.django_db
def test_spokesperson_m2m_narrows_visibility_within_workspace() -> None:
    """When two spokespeople share a workspace, an M2M-attached
    doc is visible only to its attached spokespeople. Empty
    M2M means visible to everyone in the workspace."""
    ws = _make_workspace("carol@privacy.test", "Carol's WS")
    sp_general = _make_teammate(ws, "General")
    sp_specific = _make_teammate(ws, "Specific")

    # One doc visible to all (no M2M)
    doc_open = _make_doc_with_chunk(ws, "Open doc", "shared", _vec(1.0))

    # One doc visible only to sp_specific
    doc_locked = _make_doc_with_chunk(
        ws, "Locked doc", "private",
        _vec(1.0),
        spokespeople=[sp_specific],
    )

    # sp_general queries: sees only the open doc
    general_results = retrieve_for_teammate(sp_general, _query_vector=_vec(1.0), top_k=10)
    general_doc_ids = {c.document_id for c in general_results}
    assert doc_open.id in general_doc_ids
    assert doc_locked.id not in general_doc_ids

    # sp_specific queries: sees both
    specific_results = retrieve_for_teammate(sp_specific, _query_vector=_vec(1.0), top_k=10)
    specific_doc_ids = {c.document_id for c in specific_results}
    assert doc_open.id in specific_doc_ids
    assert doc_locked.id in specific_doc_ids


@pytest.mark.django_db
def test_cross_thread_conversation_isolation() -> None:
    """A query for thread A must NEVER return conversation
    embeddings from thread B, even when threads share a
    spokesperson AND workspace.
    """
    ws = _make_workspace("dave@privacy.test", "Dave's WS")
    sp = _make_teammate(ws, "Maya")

    thread_a = ConversationThread.objects.create(spokesperson=sp, title="Thread A")
    thread_b = ConversationThread.objects.create(spokesperson=sp, title="Thread B")

    msg_a = ConversationMessage.objects.create(
        thread=thread_a,
        role=ConversationMessage.Role.USER,
        content="hello from A",
    )
    msg_b = ConversationMessage.objects.create(
        thread=thread_b,
        role=ConversationMessage.Role.USER,
        content="hello from B",
    )

    same_vector = _vec(1.0)
    emb_a = ConversationEmbedding.objects.create(
        message=msg_a, chunk_index=0, chunk_text=msg_a.content,
        chunk_size=len(msg_a.content), embedding_vector=same_vector,
    )
    emb_b = ConversationEmbedding.objects.create(
        message=msg_b, chunk_index=0, chunk_text=msg_b.content,
        chunk_size=len(msg_b.content), embedding_vector=same_vector,
    )

    # Query for thread A: must NEVER include emb_b
    _docs, history = retrieve_for_thread(
        thread_a, _query_vector=same_vector,
        top_k_docs=0, top_k_history=10,
    )
    history_ids = {emb.id for emb in history}
    assert emb_a.id in history_ids
    assert emb_b.id not in history_ids


@pytest.mark.django_db
def test_workspace_anchor_required() -> None:
    """``KnowledgeDocument.workspace`` is required. Attempting
    to create one without a workspace must fail at the DB level
    (NOT NULL constraint)."""
    from django.db import IntegrityError

    with pytest.raises(IntegrityError):
        KnowledgeDocument.objects.create(
            workspace=None,  # type: ignore[arg-type]
            title="Stray doc",
            document_type=DocumentType.TEXT,
            processed_content="x",
            content_hash="stray",
            ingested_via=IngestedVia.PASTE,
        )


@pytest.mark.django_db
def test_m2m_blocks_cross_workspace_spokesperson_attach() -> None:
    """``doc.spokespeople.add(sp)`` where ``sp`` is in a
    different workspace must raise. The m2m_changed signal
    in ``apps.embeddings.signals`` enforces this."""
    from django.core.exceptions import ValidationError

    ws_a = _make_workspace("eve@privacy.test", "Eve's WS")
    ws_b = _make_workspace("frank@privacy.test", "Frank's WS")

    doc = _make_doc_with_chunk(ws_a, "A doc", "x", _vec(1.0))
    foreign_sp = _make_teammate(ws_b, "Foreign SP")

    with pytest.raises(ValidationError):
        doc.spokespeople.add(foreign_sp)


@pytest.mark.django_db
def test_content_hash_dedup_is_per_workspace() -> None:
    """``(workspace, content_hash)`` is unique — same hash in a
    different workspace is fine; same hash in same workspace
    is rejected."""
    from django.db import IntegrityError

    ws_a = _make_workspace("gina@privacy.test", "Gina's WS")
    ws_b = _make_workspace("hank@privacy.test", "Hank's WS")

    KnowledgeDocument.objects.create(
        workspace=ws_a, title="A1",
        document_type=DocumentType.TEXT,
        processed_content="dup", content_hash="SHARED-HASH",
        ingested_via=IngestedVia.PASTE,
    )

    # Same hash in ws_b — OK
    KnowledgeDocument.objects.create(
        workspace=ws_b, title="B1",
        document_type=DocumentType.TEXT,
        processed_content="dup", content_hash="SHARED-HASH",
        ingested_via=IngestedVia.PASTE,
    )

    # Same hash in ws_a again — rejected
    with pytest.raises(IntegrityError):
        KnowledgeDocument.objects.create(
            workspace=ws_a, title="A2",
            document_type=DocumentType.TEXT,
            processed_content="dup", content_hash="SHARED-HASH",
            ingested_via=IngestedVia.PASTE,
        )


# ---- repo-level grep test ------------------------------------------


# Files allowed to query (.objects.*) the chunk tables. The
# privacy contract is about RETRIEVAL/READ shape — writers
# (ingestion / Celery tasks) and admin (read-only audit) are
# sanctioned because they cannot leak across workspaces or
# threads on the read path.
ALLOWED_FILES = {
    # Model definitions themselves
    "apps/embeddings/models.py",
    "apps/conversations/models.py",
    # The retrieval surface — the only sanctioned consumer
    "apps/embeddings/retrieval.py",
    # Read-only admin audit surfaces
    "apps/embeddings/admin.py",
    "apps/conversations/admin.py",
    # Sanctioned writers — ingestion creates, tasks embed
    "apps/embeddings/ingestion.py",
    "apps/embeddings/tasks.py",
    # This test file itself + the ingestion test
    "apps/embeddings/tests/test_retrieval_privacy.py",
    "apps/embeddings/tests/test_ingestion.py",
    # F4 preview endpoint tests seed chunks directly to
    # exercise the doc-level grouping path.
    "apps/embeddings/tests/test_preview.py",
    # F6 citation tests seed KnowledgeChunk rows to exercise
    # the chunk-id-to-doc resolver.
    "apps/compositions/tests/test_f6_citations.py",
    # F7 reverse-lookup tests seed chunks to exercise the
    # doc → compositions reverse endpoint.
    "apps/embeddings/tests/test_f7_compositions_reverse.py",
    # K8 message-embedding tests verify the pipeline via
    # the read-side queries — counting ConversationEmbedding
    # rows after the signal fires.
    "apps/conversations/tests/test_embed_message.py",
    # K8 task itself writes ConversationEmbedding rows — the
    # sanctioned-writer side of the K0 contract (mirrors
    # `embed_document`).
    "apps/conversations/tasks.py",
    # R4 knowledge-bridge tests seed KnowledgeChunk rows
    # directly to exercise the document composer.
    "apps/realtime/tests/test_r4_knowledge_bridge.py",
    # R6 cross-session-memory tests seed KnowledgeChunk
    # rows to verify memory + knowledge co-exist in the
    # composed document body.
    "apps/realtime/tests/test_r6_session_memory.py",
    # R7.1 sync-tool tests seed KnowledgeChunk rows to
    # exercise `recall_knowledge` (RAG path) + the
    # cross-workspace privacy assertion.
    "apps/realtime/tests/test_r7_1_sync_tools.py",
    # K9 endpoint tests do read-side queries on
    # ConversationEmbedding to verify the K8 ↔ K9 pipeline
    # integration (count of embeddings produced after send).
    "apps/conversations/tests/test_k9_messages.py",
    # Chapter 6 slice-1 ask tests seed KnowledgeChunk rows to
    # exercise `ask_teammate` (RAG path) + cross-workspace
    # citation isolation + status=pending filter behavior
    # (SESSION 234).
    "apps/spokespeople/tests/test_ask.py",
    # SESSION 261 Phase 3 — Universe-aware retrieval truth-table
    # tests. Seeds KnowledgeChunk rows directly to exercise all
    # nine (T.universe, D.universe, M2M) permutations of
    # ``retrieve_for_teammate`` per
    # ``docs/design/UNIVERSE_SCHEMA_V1.md`` §"Retrieval truth
    # table". Same sanction as ``test_retrieval_privacy.py``.
    "apps/embeddings/tests/test_retrieval_universe.py",
}

# The pattern we actually care about: ``<Model>.objects`` —
# the queryset entry point. Mentions in docstrings / module
# constants are not a privacy concern.
QUERY_PATTERN = re.compile(
    r"\b(KnowledgeChunk|ConversationEmbedding)\.objects\b"
)


def test_only_retrieval_module_queries_chunk_tables() -> None:
    """The privacy contract requires that no code outside
    ``apps.embeddings.retrieval`` runs a queryset against the
    chunk tables. This test walks the repo, looks for
    ``KnowledgeChunk.objects`` / ``ConversationEmbedding.objects``
    patterns, and fails if any hit lands in an unsanctioned
    file.

    Why ``.objects`` specifically: that's the queryset entry
    point. Docstring mentions and constant imports of the
    chunk model names are fine — the privacy concern is the
    *reads*. Sanctioned writers (ingestion, embed_document
    Celery task) are in ALLOWED_FILES.

    The retrieval guarantees in ``retrieve_for_teammate``
    and ``retrieve_for_thread`` depend on the read surface
    staying narrow. The moment a view, a serializer, or an
    ad-hoc helper writes ``KnowledgeChunk.objects.filter(...)``,
    the structural guarantee becomes a procedural one.
    """
    shell_root = Path(__file__).resolve().parents[3]
    assert shell_root.name == "shell", f"unexpected root: {shell_root}"

    offenders: list[tuple[str, int, str]] = []
    for py_path in shell_root.rglob("*.py"):
        rel = py_path.relative_to(shell_root).as_posix()

        if "/migrations/" in rel or rel.startswith("migrations/"):
            continue
        if rel.startswith(".venv/") or "/__pycache__/" in rel:
            continue
        if rel in ALLOWED_FILES:
            continue

        try:
            content = py_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for lineno, line in enumerate(content.splitlines(), start=1):
            if QUERY_PATTERN.search(line):
                offenders.append((rel, lineno, line.strip()))

    if offenders:
        msg_lines = [
            "Forbidden chunk-model query outside the retrieval surface:",
        ]
        msg_lines.extend(
            f"  {rel}:{lineno}  {snippet}" for rel, lineno, snippet in offenders[:10]
        )
        if len(offenders) > 10:
            msg_lines.append(f"  ... and {len(offenders) - 10} more")
        msg_lines.append(
            "Route through apps.embeddings.retrieval instead. "
            "If a legitimate caller needs to be added, update "
            "ALLOWED_FILES in this test with a code-review note."
        )
        pytest.fail("\n".join(msg_lines))
