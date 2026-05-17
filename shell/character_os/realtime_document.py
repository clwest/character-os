"""Realtime document composer — R4 (realtime arc).

Builds the Runway document body for a realtime session at
session-create time. The avatar's LLM gets this document as
its grounding context — it's the single most architecturally
significant moment in the realtime arc.

The Runway document is **derived** from `KnowledgeDocument`
rows. K layer remains the system of record; we never write
back to it from the realtime path.

Knowledge changes mid-session don't propagate — the doc is
frozen at session-create. The next session re-composes from
fresh knowledge.

Shape (matches the hackathon's
`documents_client.build_campaign_brief_markdown` for
familiarity, but takes primitives instead of a Campaign):

    # {Spokesperson Name}

    ## About

    {business_brief}

    ## Knowledge

    ### {doc title}

    {chunk_text}

    ...

Capped at Runway's documented 40,000-char limit; over-budget
content drops tail chunks first (the cosine-distance
ordering means tail chunks are least relevant to the
spokesperson's business_brief anchor).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from apps.embeddings.retrieval import retrieve_for_spokesperson
from character_os.realtime_memory import compose_session_memory

if TYPE_CHECKING:
    from apps.spokespeople.models import Spokesperson

logger = logging.getLogger(__name__)


# Runway's documented hard limit on document body size.
# Conservative — leaves headroom for header / separator
# bytes Runway might count differently than us.
DEFAULT_MAX_CHARS = 40_000

# How many chunks to consider at session-create. 30 is the
# scope-lock default — enough breadth for the avatar to
# answer a wide range of questions without blowing the
# context budget.
DEFAULT_TOP_K = 30


@dataclass(slots=True)
class RealtimeDocumentResult:
    """Composed document + provenance for the broker to
    persist on RealtimeSession.

    ``memory_session_ids`` (R6) records which prior
    sessions' transcripts fed the ``## Recent Conversations``
    section, so admins can audit the memory loop. Empty when
    no memory was injected (first-ever session for a
    spokesperson) or when the section was dropped to fit
    the ``max_chars`` budget.
    """

    body: str
    chunk_ids: list[str] = field(default_factory=list)
    truncated: bool = False
    chars: int = 0
    memory_session_ids: list[str] = field(default_factory=list)


def compose_realtime_document(
    spokesperson: "Spokesperson",
    *,
    top_k: int = DEFAULT_TOP_K,
    max_chars: int = DEFAULT_MAX_CHARS,
) -> RealtimeDocumentResult:
    """Build the Runway document body for this spokesperson.

    Anchors retrieval on the spokesperson's ``business_brief``
    so the most semantically-relevant chunks rank highest.
    Falls back to the spokesperson's name when the brief is
    empty.

    Returns a result with the ready-to-send markdown body +
    the chunk ids that contributed (for citation persistence
    on ``RealtimeSession.knowledge_chunk_ids``).

    The function never raises on retrieval failure — empty
    chunk list, embedding service down, etc. degrade to a
    "business_brief only" document that still gives the
    avatar identity. R-arc keeps working even when the K-arc
    surface is unavailable.
    """
    name = (spokesperson.name or "").strip() or "Spokesperson"
    brief = (spokesperson.business_brief or "").strip()
    # W11.y (SESSION 175) — personality / business_brief split.
    # Personality describes HOW the avatar speaks (voice,
    # mannerisms); business_brief describes WHAT the business is
    # (facts). Both belong in the Runway document. Pre-W11.y
    # rows have personality backfilled from business_brief so
    # this is additive only.
    personality = (
        getattr(spokesperson, "personality", "") or ""
    ).strip()
    # Retrieval query stays anchored on business_brief because
    # facts make better retrieval queries than voice descriptions
    # ("AcmeCorp inventory" pulls relevant chunks; "patient
    # teacher" doesn't). Falls back to name when brief empty.
    query = brief or name

    try:
        chunks = retrieve_for_spokesperson(spokesperson, query=query, top_k=top_k)
    except Exception:
        logger.exception(
            "compose_realtime_document: retrieval failed sp=%s; degrading",
            spokesperson.pk,
        )
        chunks = []

    # R6 — pull prior-session memory. Never raises; returns
    # an empty result when there's nothing to project.
    memory = compose_session_memory(spokesperson)

    # Build the markdown body, tracking the byte budget so
    # we know which sections to drop on truncation. Drop
    # order under budget (per scope-lock §R4): memory first,
    # then knowledge tail chunks. About + header never drop.
    header_lines = [f"# {name}", ""]
    # W11.y — Voice section drives HOW the avatar speaks; About
    # section drives WHAT they speak about. Voice comes first so
    # Runway anchors tone before facts.
    if personality:
        header_lines += ["## Voice", "", personality, ""]
    if brief:
        header_lines += ["## About", "", brief, ""]
    header = "\n".join(header_lines)

    memory_block = ""
    memory_session_ids: list[str] = []
    if memory.body:
        candidate = (
            "## Recent Conversations\n\n"
            + memory.body.rstrip()
            + "\n\n"
        )
        # Reserve room for at least the knowledge header
        # even if zero chunks fit; if memory alone would
        # exhaust the budget, drop it entirely (per
        # scope-lock priority order).
        reserve = len(header) + len("## Knowledge\n\n")
        if len(candidate) + reserve <= max_chars:
            memory_block = candidate
            memory_session_ids = list(memory.session_ids)
        else:
            logger.info(
                "compose_realtime_document: dropping memory section "
                "sp=%s (would exceed max_chars=%d)",
                spokesperson.pk, max_chars,
            )

    if not chunks:
        body = (header + memory_block).rstrip() + "\n"
        return RealtimeDocumentResult(
            body=body,
            chunk_ids=[],
            truncated=False,
            chars=len(body),
            memory_session_ids=memory_session_ids,
        )

    # Group chunks by document so the avatar sees coherent
    # source titles, not a flat chunk list. Within each
    # group, chunk order preserves retrieval ranking (closest
    # match first).
    doc_buckets: dict[str, dict] = {}
    doc_order: list[str] = []
    for chunk in chunks:
        doc_id = str(chunk.document_id)
        if doc_id not in doc_buckets:
            doc_buckets[doc_id] = {
                "title": chunk.document.title,
                "chunks": [],
            }
            doc_order.append(doc_id)
        doc_buckets[doc_id]["chunks"].append(chunk)

    # Assemble the knowledge section incrementally so we can
    # stop when we'd exceed max_chars. Budget already
    # accounts for the (possibly empty) memory block.
    knowledge_lines = ["## Knowledge", ""]
    used_chunk_ids: list[str] = []
    truncated = False
    current_chars = (
        len(header) + len(memory_block) + len("\n".join(knowledge_lines))
    )

    for doc_id in doc_order:
        bucket = doc_buckets[doc_id]
        title_block = f"### {bucket['title']}\n"
        if current_chars + len(title_block) > max_chars:
            truncated = True
            break
        knowledge_lines.append(title_block.rstrip())
        knowledge_lines.append("")
        current_chars += len(title_block) + 1  # +1 for the join newline

        for chunk in bucket["chunks"]:
            chunk_block = chunk.chunk_text.strip() + "\n\n"
            if current_chars + len(chunk_block) > max_chars:
                truncated = True
                break
            knowledge_lines.append(chunk.chunk_text.strip())
            knowledge_lines.append("")
            used_chunk_ids.append(str(chunk.id))
            current_chars += len(chunk_block) + 1
        if truncated:
            break

    body = header + memory_block + "\n".join(knowledge_lines).rstrip() + "\n"
    return RealtimeDocumentResult(
        body=body,
        chunk_ids=used_chunk_ids,
        truncated=truncated,
        chars=len(body),
        memory_session_ids=memory_session_ids,
    )
