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


def resolve_chunk_ids_to_docs(
    chunk_ids: list[str],
    *,
    workspace=None,
) -> list[dict]:
    """Resolve a flat list of chunk ids into a deduped
    document-level summary list.

    Added in F6 (workspace fabric arc) so the composition
    detail page can show "this render drew from <doc A> (3
    chunks), <doc B> (1 chunk)" by resolving the K6-populated
    ``Composition.knowledge_chunk_ids`` JSON list.

    Output is ``[{"id", "title", "chunk_count"}]`` ordered by
    first occurrence in the input list — same convention as
    F4's preview endpoint so the panel shapes line up.

    Optional ``workspace`` filter drops any chunk whose
    document doesn't belong to that workspace. K0 contract
    rule 2 — chunk-level access stays in this module. K6
    only writes in-workspace chunk ids today, but defense in
    depth: a future bug could leak a foreign id into the JSON
    field and this resolver must not silently surface it.
    """
    if not chunk_ids:
        return []
    qs = KnowledgeChunk.objects.filter(id__in=chunk_ids).select_related(
        "document",
    )
    if workspace is not None:
        qs = qs.filter(document__workspace=workspace)
    chunks_by_id: dict[str, KnowledgeChunk] = {
        str(chunk.id): chunk for chunk in qs
    }

    doc_order: list[str] = []
    doc_titles: dict[str, str] = {}
    counts: dict[str, int] = {}
    for raw_id in chunk_ids:
        chunk = chunks_by_id.get(str(raw_id))
        if chunk is None:
            continue
        doc_id = str(chunk.document_id)
        if doc_id not in doc_titles:
            doc_titles[doc_id] = chunk.document.title
            doc_order.append(doc_id)
            counts[doc_id] = 0
        counts[doc_id] += 1
    return [
        {
            "id": doc_id,
            "title": doc_titles[doc_id],
            "chunk_count": counts[doc_id],
        }
        for doc_id in doc_order
    ]


def list_chunk_ids_for_document(document) -> list[str]:
    """Return the list of active chunk ids belonging to a
    KnowledgeDocument as strings.

    Added in F7 (workspace fabric arc) so the "used in N
    compositions" reverse panel on the doc detail page can
    look up its chunks without importing the chunk model
    directly — K0 contract rule 2. Only ids escape this
    function; no chunk content.
    """
    return [
        str(cid)
        for cid in KnowledgeChunk.objects.filter(
            document=document,
        ).values_list("id", flat=True)
    ]


def count_chunks_for_workspace(workspace) -> int:
    """Return the total number of active chunks in a workspace.

    Added in F3 (workspace fabric arc) so the dashboard overview
    endpoint can show "N chunks" without importing the chunk
    model directly — K0 contract rule 2 keeps chunk-level access
    inside this module. The count never leaves chunk content
    across workspaces; only an integer escapes.

    Workspace is passed as the FK target, not by id, to match
    the function signatures above. Empty / inactive docs are
    excluded so the count matches what the SPA's
    `/workspace/knowledge` list sees.
    """
    return KnowledgeChunk.objects.filter(
        document__workspace=workspace,
        document__is_active=True,
    ).count()


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
