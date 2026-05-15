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
    persist on RealtimeSession."""

    body: str
    chunk_ids: list[str] = field(default_factory=list)
    truncated: bool = False
    chars: int = 0


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
    # Use the business_brief as the implicit query so chunks
    # most-related to the spokesperson's identity float to
    # the top. Falls back to the name when brief is empty.
    query = brief or name

    try:
        chunks = retrieve_for_spokesperson(spokesperson, query=query, top_k=top_k)
    except Exception:
        logger.exception(
            "compose_realtime_document: retrieval failed sp=%s; degrading",
            spokesperson.pk,
        )
        chunks = []

    # Build the markdown body, tracking the byte budget so
    # we know which chunks to drop on truncation.
    header_lines = [f"# {name}", ""]
    if brief:
        header_lines += ["## About", "", brief, ""]
    header = "\n".join(header_lines)

    if not chunks:
        body = header.rstrip() + "\n"
        return RealtimeDocumentResult(
            body=body, chunk_ids=[], truncated=False, chars=len(body),
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
    # stop when we'd exceed max_chars.
    knowledge_lines = ["## Knowledge", ""]
    used_chunk_ids: list[str] = []
    truncated = False
    current_chars = len(header) + len("\n".join(knowledge_lines))

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

    body = header + "\n".join(knowledge_lines).rstrip() + "\n"
    return RealtimeDocumentResult(
        body=body,
        chunk_ids=used_chunk_ids,
        truncated=truncated,
        chars=len(body),
    )
