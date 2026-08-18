"""The ONE retrieval surface for the knowledge layer.

SESSION 138 / K2 — locked in
``docs/design/KNOWLEDGE_LAYER.md`` §"Retrieval surface". Public
functions:

* ``retrieve_for_teammate()`` — workspace-scoped doc
  retrieval. Used at video render time (K6) and as the
  first half of the conversation retrieval path.
* ``retrieve_for_thread()`` — conversation-scoped retrieval.
  Mixes doc-knowledge (via the first function) with
  this-thread-only conversational history. Used at
  conversation reply time (K9).
* ``retrieve_universe_canon()`` — Universe-scoped shared-tier
  retrieval (SESSION 263). Returns chunks whose document is
  visible to *every* teammate in ``cast`` and is scope-shared
  (M2M-null broadcast OR M2M covers every cast member).
* ``retrieve_universe_memory()`` — Universe-scoped operator-
  promoted ``NarrativeMemory`` retrieval (SESSION 264 Slice 2).
  Its own lane; NEVER returns ``KnowledgeChunk`` rows, NEVER
  mutates canon.

**Discipline:** no code outside this module is allowed to
import ``KnowledgeChunk`` or ``ConversationEmbedding``.
That's contract rule 2 of the scope lock and is enforced by
``apps.embeddings.tests.test_retrieval_isolation`` —
edits to bypass it should fail review. ``NarrativeMemory``
(in ``apps.memory.models``) is a separate model and is not
covered by rule 2; the "narrow retrieval surface" spirit is
preserved by only exposing it through ``retrieve_universe_memory``
in this same module.

The cross-workspace / cross-thread isolation tests in the
same module are the load-bearing privacy guarantee. If the
filter logic here changes, those tests must continue to pass.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from django.db.models import Count, Q
from pgvector.django import CosineDistance

from apps.conversations.models import ConversationEmbedding, ConversationThread
from apps.spokespeople.models import Teammate

from .models import KnowledgeChunk, KnowledgeDocument

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


def retrieve_for_teammate(
    spokesperson: Teammate,
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

    qs = KnowledgeChunk.objects.filter(
        document__workspace=spokesperson.workspace,
        document__is_active=True,
        document__status="processed",
    )

    # SESSION 261 — Universe isolation predicate. Applied BEFORE
    # the M2M-visibility filter so empty-M2M docs are naturally
    # scoped to the retrieving teammate's Universe (row 6 of the
    # truth table in UNIVERSE_SCHEMA_V1.md).
    #
    # The branching form is load-bearing: Django's ORM emits
    # ``document.universe_id = NULL`` for a raw
    # ``.filter(document__universe=None)`` call, which SQL treats
    # as NEVER true — silently returning zero rows and breaking
    # legacy retrieval (row 1). ``__isnull=True`` emits the
    # correct ``IS NULL`` predicate.
    if spokesperson.universe_id is None:
        qs = qs.filter(document__universe__isnull=True)
    else:
        qs = qs.filter(document__universe_id=spokesperson.universe_id)

    qs = (
        qs.filter(
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
    ``retrieve_for_teammate``). ``history_chunks`` is
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
        _query_vector: see ``retrieve_for_teammate``.

    Returns:
        Tuple ``(doc_chunks, history_chunks)`` — both lists
        ordered closest-first. Prompt assembly is the caller's
        responsibility; the two lists are returned separately
        so the assembler can visually divide them in the LLM
        prompt.
    """
    vector = list(_query_vector) if _query_vector is not None else _embed_query(query)

    doc_chunks = retrieve_for_teammate(
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


def retrieve_universe_canon(
    workspace,
    universe,
    cast: "Sequence[Teammate]",
    query: str = "",
    top_k: int = 2,
    *,
    _query_vector: "Sequence[float] | None" = None,
) -> list[KnowledgeChunk]:
    """Return the top-k shared-tier canon chunks for a dialogue cast.

    SESSION 263 / Slice B — the intentional Universe canon lane.
    Companion to :func:`retrieve_for_teammate`; does NOT change
    that function's semantics or budget.

    "Shared-tier" per ``UNIVERSE_CANON_RETRIEVAL_LANE_AUDIT_SESSION_263``:
    a document is canon iff its Universe scope matches and it is
    legitimately visible to every teammate in ``cast``. Concretely:

    1. ``workspace = <given>`` — tenant wall (matches
       ``retrieve_for_teammate`` §1).
    2. ``universe = <given>`` — Universe isolation (matches row 9
       of the retrieval truth table).
    3. ``is_active`` + ``status='processed'`` — same lifecycle
       gates as ``retrieve_for_teammate``.
    4. Either the M2M is empty (universe-wide broadcast, row 6)
       OR every cast member is present in the M2M (row 7 for the
       full cast). A doc scoped to only some cast members is
       NOT canon for this synthesis — it belongs in per-character
       retrieval.

    Cosine distance ordering + ``LIMIT top_k`` mirror
    ``retrieve_for_teammate``. The default ``top_k=2`` matches the
    audit's ``shared_top_k`` recommendation for the first landing;
    callers may override for other consumers.

    Args:
        workspace: the composition's workspace (tenant anchor).
        universe: the Universe this dialogue is anchored in. Must
            not be ``None``; a legacy universe-less dialogue has
            no canon lane (returns empty list).
        cast: the ordered speakers. Every cast member must belong
            to ``universe``; mixing legacy + Universe teammates or
            crossing Universes returns empty list (defensive; the
            dialogue synth guard already rejects those).
        query: the natural-language query. Ignored when
            ``_query_vector`` is supplied.
        top_k: max canon chunks to return (default 2).
        _query_vector: pre-computed embedding vector. Test path
            (see ``test_retrieval_universe.py``).

    Returns:
        A list of ``KnowledgeChunk`` rows, ordered by cosine
        distance ascending. Empty list when: no Universe was
        provided, cast is empty, cast spans Universes, ``top_k``
        is zero, or no shared-tier doc exists.
    """
    if top_k <= 0 or universe is None or not cast:
        return []

    # Cast-Universe defensive gate. ``synthesize_dialogue`` already
    # enforces same-workspace membership before it calls this; the
    # Universe consistency check here is defense in depth for any
    # future caller that skips that gate.
    universe_id = getattr(universe, "id", None) or getattr(universe, "pk", None)
    if universe_id is None:
        return []
    for tm in cast:
        if getattr(tm, "universe_id", None) != universe_id:
            return []

    vector = list(_query_vector) if _query_vector is not None else _embed_query(query)

    # Shared-tier predicate is resolved at the DOCUMENT level first,
    # then the chunk-level cosine ranking runs on chunks belonging
    # to those documents. Splitting doc-scope from chunk-ranking
    # keeps the M2M "has all cast" expression readable and avoids
    # annotation-on-chained-M2M-joins subtleties (which silently
    # dropped rows in an earlier draft).
    doc_qs = KnowledgeDocument.objects.filter(
        workspace=workspace,
        universe_id=universe_id,
        is_active=True,
        status="processed",
    )

    # Branch 1 — M2M-null (universe-wide broadcast; row 6 of the
    # retrieval truth table).
    null_doc_ids = list(
        doc_qs.filter(spokespeople__isnull=True).values_list("id", flat=True)
    )

    # Branch 2 — M2M explicitly covers every cast member AND
    # M2M count > 1. The chained ``.filter(spokespeople=tm)`` for
    # each cast member is Django's canonical "has all of" M2M
    # expression (each filter adds a fresh join alias); the count
    # gate rules out the coincidental single-teammate case where
    # cast == [that teammate].
    #
    # Load-bearing subtlety: the count check MUST NOT be an
    # annotation on the same queryset that carries the "has all
    # of" chained filters. Django emits the annotation as
    # ``COUNT(DISTINCT T_n.spokesperson_id)`` where ``T_n`` is
    # the filter-joined alias — and that alias is already
    # restricted to the last-filtered spokesperson, so the count
    # returns 1 by construction and every candidate silently
    # drops. Resolve the "has all of" candidates to IDs first,
    # then run a fresh unaggregated Count on those IDs.
    many_docs = doc_qs
    for tm in cast:
        many_docs = many_docs.filter(spokespeople=tm)
    covers_all_ids = set(many_docs.values_list("id", flat=True).distinct())
    if covers_all_ids:
        many_doc_ids = list(
            KnowledgeDocument.objects.filter(id__in=covers_all_ids)
            .annotate(_c=Count("spokespeople", distinct=True))
            .filter(_c__gt=1)
            .values_list("id", flat=True)
        )
    else:
        many_doc_ids = []

    candidate_doc_ids = set(null_doc_ids) | set(many_doc_ids)
    if not candidate_doc_ids:
        return []

    qs = (
        KnowledgeChunk.objects.filter(document_id__in=candidate_doc_ids)
        .annotate(distance=CosineDistance("embedding_vector", vector))
        .order_by("distance")
    )
    return list(qs[:top_k])


# ============================================================
# SESSION 264 Slice 2 — Universe narrative-memory retrieval lane
# ============================================================
#
# Third retrieval lane. Sits alongside ``retrieve_universe_canon``
# (static shared canon) and ``retrieve_for_teammate`` (per-character
# K2). NEVER returns ``KnowledgeChunk`` rows; NEVER mutates any
# ``KnowledgeDocument``.
#
# Predicate mirrors the audit §13.2 recommendation verbatim:
#   * workspace = <given>                        (tenant wall)
#   * universe  = <given>                        (Universe scope)
#   * status    = REMEMBERED                     (excludes archived + superseded)
#   * archived_at IS NULL                        (defense-in-depth)
#   * embedding_vector IS NOT NULL               (skip unembedded rows)
#   * witnessed_by is empty  OR
#     witnessed_by ∩ current-cast is non-empty   (whole-cast default OR overlap)
#
# top_k fixed at 1 for v1 per the SESSION 264 Slice 2 brief. Not
# configurable yet — matches the audit's conservative default and
# gives us falsifiable evidence before tuning.


def retrieve_universe_memory(
    workspace,
    universe,
    cast: "Sequence[Teammate]",
    query: str = "",
    top_k: int = 1,
    *,
    _query_vector: "Sequence[float] | None" = None,
) -> list:
    """Return the top-k active narrative-memory rows for a dialogue cast.

    SESSION 264 Slice 2. Companion to ``retrieve_universe_canon``
    and ``retrieve_for_teammate``; does NOT change their semantics
    or budgets.

    Returns a list of ``apps.memory.models.NarrativeMemory`` rows
    (never ``KnowledgeChunk``). Empty list when:
      * ``universe`` is ``None`` (memory is a Universe primitive)
      * ``cast`` is empty
      * ``top_k <= 0``
      * cast spans Universes (defensive; matches canon lane)
      * no active + embedded rows match the visibility predicate

    Args:
        workspace: the composition's workspace (tenant anchor).
        universe: the Universe this dialogue is anchored in.
        cast: ordered speakers; every cast member must belong to
            ``universe``.
        query: natural-language query. Ignored when
            ``_query_vector`` is passed (test hatch — same shape
            as ``retrieve_universe_canon``).
        top_k: bounded number of rows to return (default 1).

    Isolation guarantees mirror canon lane:
        * Cross-Workspace impossible (workspace filter is
          unconditional and not overridable).
        * Cross-Universe impossible (universe filter is
          unconditional; cross-Universe cast returns []).
    """
    # Local import so this module doesn't force ``apps.memory`` to
    # load at boot time; apps.memory itself imports embeddings for
    # ``embedding_service`` so a top-level import here would create
    # a cycle at Django app-registry init.
    from apps.memory.models import NarrativeMemory, NarrativeMemoryStatus

    if top_k <= 0 or universe is None or not cast:
        return []

    universe_id = getattr(universe, "id", None) or getattr(universe, "pk", None)
    if universe_id is None:
        return []
    for tm in cast:
        if getattr(tm, "universe_id", None) != universe_id:
            return []

    vector = list(_query_vector) if _query_vector is not None else _embed_query(query)

    cast_ids = [getattr(tm, "id", None) or getattr(tm, "pk", None) for tm in cast]
    cast_ids = [c for c in cast_ids if c is not None]

    # Base predicate — status, archive, embed, workspace, universe.
    base_qs = NarrativeMemory.objects.filter(
        workspace=workspace,
        universe_id=universe_id,
        status=NarrativeMemoryStatus.REMEMBERED,
        archived_at__isnull=True,
        embedding_vector__isnull=False,
    )

    # Visibility filter — witness-empty (whole cast, matches the
    # ``KnowledgeDocument.spokespeople`` empty-M2M-is-broadcast
    # convention) OR at least one witness overlaps the current
    # cast. We compute the two sets separately then union IDs to
    # avoid the Django ORM annotation-on-chained-M2M bug that
    # ``retrieve_universe_canon`` had to work around (line 380+).
    if cast_ids:
        # Whole-cast (witnessed_by empty) — annotate + filter is
        # safe here because the annotation runs on a fresh queryset
        # with no chained M2M filter.
        whole_cast_ids = list(
            base_qs.annotate(_wc=Count("witnessed_by"))
            .filter(_wc=0)
            .values_list("id", flat=True)
        )
        # At-least-one-overlap — separate queryset over the M2M.
        overlap_ids = list(
            base_qs.filter(witnessed_by__id__in=cast_ids)
            .values_list("id", flat=True)
            .distinct()
        )
        candidate_ids = set(whole_cast_ids) | set(overlap_ids)
    else:
        # No cast IDs — only whole-cast rows are visible. Defensive
        # (already returned [] for empty cast above).
        candidate_ids = set()

    if not candidate_ids:
        return []

    qs = (
        NarrativeMemory.objects.filter(id__in=candidate_ids)
        .annotate(distance=CosineDistance("embedding_vector", vector))
        .order_by("distance")
    )
    return list(qs[:top_k])
