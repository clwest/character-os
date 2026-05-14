"""The ONE retrieval surface for the knowledge layer.

SESSION 138 / K2 — locked in
``docs/design/KNOWLEDGE_LAYER.md`` §"Retrieval surface". Two
public functions, period:

* ``retrieve_for_spokesperson()`` — workspace-scoped doc
  retrieval. Used at video render time (K6) and as the
  first half of the conversation retrieval path.
* ``retrieve_for_thread()`` — conversation-scoped retrieval.
  Mixes doc-knowledge (via the first function) with
  this-thread-only conversational history. Used at
  conversation reply time (K9).

**Discipline:** no code outside this module is allowed to
import ``KnowledgeChunk`` or ``ConversationEmbedding``.
That's contract rule 2 of the scope lock and is enforced by
``apps.embeddings.tests.test_retrieval_isolation`` —
edits to bypass it should fail review.

The cross-workspace / cross-thread isolation tests in the
same module are the load-bearing privacy guarantee. If the
filter logic here changes, those tests must continue to pass.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Q
from pgvector.django import CosineDistance

from apps.conversations.models import ConversationEmbedding, ConversationThread
from apps.spokespeople.models import Spokesperson

from .models import KnowledgeChunk

if TYPE_CHECKING:
    from collections.abc import Sequence


# SESSION 138 / K3 — wired to the real embedding service.
# ``EMBEDDING_FORCE_MOCK=1`` returns deterministic mock vectors;
# real mode requires ``OPENAI_API_KEY``. Tests can still pass
# an explicit ``_query_vector`` to bypass embedding entirely.
def _embed_query(query: str) -> list[float]:
    from .embedding_service import embed

    return embed(query).vector


def retrieve_for_spokesperson(
    spokesperson: Spokesperson,
    query: str = "",
    top_k: int = 5,
    *,
    _query_vector: "Sequence[float] | None" = None,
) -> list[KnowledgeChunk]:
    """Return the top-k knowledge chunks for this spokesperson.

    Workspace filter is unconditional — derived from
    ``spokesperson.workspace`` directly. There is no
    ``workspace=`` parameter; there is no ``bypass`` flag.
    Cross-workspace leak is structurally impossible by
    construction (contract rule 3).

    Args:
        spokesperson: the spokesperson asking. Their workspace
            is the scope.
        query: the natural-language query. Ignored when
            ``_query_vector`` is supplied (test path).
        top_k: max chunks to return.
        _query_vector: pre-computed embedding vector. Test
            helper — production callers omit and let
            ``_embed_query`` handle it.

    Returns:
        A list of ``KnowledgeChunk`` rows, ordered by cosine
        distance ascending (closest match first). Empty list
        when no docs are visible or none match.
    """
    if top_k <= 0:
        return []

    vector = list(_query_vector) if _query_vector is not None else _embed_query(query)

    qs = (
        KnowledgeChunk.objects.filter(
            document__workspace=spokesperson.workspace,
            document__is_active=True,
            document__status="processed",
        )
        .filter(
            Q(document__spokespeople__isnull=True)
            | Q(document__spokespeople=spokesperson)
        )
        .distinct()
        .annotate(distance=CosineDistance("embedding_vector", vector))
        .order_by("distance")
    )

    return list(qs[:top_k])


def retrieve_for_thread(
    thread: ConversationThread,
    query: str = "",
    top_k_docs: int = 3,
    top_k_history: int = 5,
    *,
    _query_vector: "Sequence[float] | None" = None,
) -> tuple[list[KnowledgeChunk], list[ConversationEmbedding]]:
    """Return ``(doc_chunks, history_chunks)`` for this thread.

    ``doc_chunks`` is the workspace knowledge visible to this
    thread's spokesperson (delegates to
    ``retrieve_for_spokesperson``). ``history_chunks`` is
    past conversational turns *in this thread only* — no
    cross-thread bleed is possible because the queryset is
    filtered by ``message__thread=thread`` with a hard
    equality match, and the conversation embedding table is
    not queryable from the doc-retrieval path.

    Args:
        thread: the conversation thread being responded to.
        query: the natural-language query. Ignored when
            ``_query_vector`` is supplied.
        top_k_docs: max workspace-knowledge chunks to return.
        top_k_history: max past-turn chunks to return.
        _query_vector: see ``retrieve_for_spokesperson``.

    Returns:
        Tuple ``(doc_chunks, history_chunks)`` — both lists
        ordered closest-first. Prompt assembly is the caller's
        responsibility; the two lists are returned separately
        so the assembler can visually divide them in the LLM
        prompt.
    """
    vector = list(_query_vector) if _query_vector is not None else _embed_query(query)

    doc_chunks = retrieve_for_spokesperson(
        thread.spokesperson,
        query=query,
        top_k=top_k_docs,
        _query_vector=vector,
    )

    history_qs = (
        ConversationEmbedding.objects.filter(message__thread=thread)
        .annotate(distance=CosineDistance("embedding_vector", vector))
        .order_by("distance")
    )
    history_chunks = list(history_qs[:top_k_history])

    return doc_chunks, history_chunks
