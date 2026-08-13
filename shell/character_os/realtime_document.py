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

    # {Teammate Name}

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

from apps.embeddings.retrieval import retrieve_for_teammate
from character_os.realtime_memory import compose_session_memory

if TYPE_CHECKING:
    from apps.spokespeople.models import Teammate

logger = logging.getLogger(__name__)


# Runway's documented hard limit on document body size.
# Conservative — leaves headroom for header / separator
# bytes Runway might count differently than us.
DEFAULT_MAX_CHARS = 40_000

# How many chunks to consider at session-create. SESSION 213
# Fix 3B raised the default 30 → 50 to bake more answers into
# the document. Pairs with `recall_knowledge`'s tightened
# non-trigger guidance: more chunks in memory = fewer cases
# where the avatar has to fire the tool = fewer Q-r-2 strikes.
# 50 fits well inside the 40k-char cap (~10k char headroom
# observed in real-mode dogfood).
DEFAULT_TOP_K = 50


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
    spokesperson: "Teammate",
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
    name = (spokesperson.name or "").strip() or "Teammate"
    brief = (spokesperson.business_brief or "").strip()
    operator_handle = _resolve_operator_handle(spokesperson)
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
        chunks = retrieve_for_teammate(spokesperson, query=query, top_k=top_k)
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
    # Platform-wide session-open behavior — applies to every
    # Character. Placed before Voice/About so the avatar's LLM
    # anchors on the conversational pattern before it conditions
    # on persona facts. Descriptive third-person form so
    # Runway's content filter accepts it (imperative "you must"
    # patterns get rejected; cf. SESSION 212 personality
    # calibration).
    header_lines += [
        "## Conversation Style",
        "",
        _conversation_style_block(name=name, operator=operator_handle),
        "",
    ]
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


def _resolve_operator_handle(spokesperson: "Teammate") -> str:
    """Return a friendly operator-facing name for the workspace
    owner. Falls back through display fields → email handle →
    a generic "the operator" so the document never carries an
    empty placeholder.

    Email handle is the v1 truth — User model is email-only.
    Future shape: add a `display_name` field on User; this helper
    automatically prefers it without re-touching the document
    composer."""
    try:
        owner = spokesperson.workspace.owner
    except AttributeError:
        return "the operator"
    for attr in ("display_name", "first_name", "name"):
        value = (getattr(owner, attr, "") or "").strip()
        if value:
            return value
    email = (getattr(owner, "email", "") or "").strip()
    if email and "@" in email:
        handle = email.split("@", 1)[0].strip()
        if handle:
            return handle[:1].upper() + handle[1:]
    return "the operator"


def _conversation_style_block(*, name: str, operator: str) -> str:
    """Platform-wide session-open behavior baked into every
    Character's realtime document. Descriptive third-person form
    so the Runway content filter accepts it (cf. SESSION 212 —
    imperative "you must" / "never X" phrasings get rejected).

    Encodes four patterns the R-arc dogfood surfaced as missing
    defaults:

    1. **Greet by name immediately.** No silent gap waiting on
       a session-open tool fire.
    2. **No automatic lookups.** Tools only fire after the
       operator has named a topic the lookup would serve.
    3. **Acknowledge lookup latency.** When a lookup IS needed,
       the Character narrates the wait conversationally rather
       than going silent (Q-r-2 mitigation — the avatar can't
       receive tool-result events back from the SDK, so it has
       to keep speaking from its cached context).
    4. **New topics get direct answers.** Recent-conversation
       lookups only happen when the operator references the past.
    """
    return (
        f"The operator in this session is named {operator}. "
        f"{name} is speaking with {operator} right now.\n\n"
        f"{name}'s opening turn always begins with the literal "
        f"phrase \"Hi {operator}\" or \"Hello {operator}\" — "
        f"never a generic \"Hello\" or \"Hi there\". The "
        f"opener uses {operator}'s name out loud and is "
        f"followed by an open invitation question such as "
        f"\"what can we work on today?\" or \"what would you "
        f"like to discuss?\". No tools are invoked, no lookups "
        f"are performed, and no prior conversations are "
        f"recalled until {operator} has stated a topic.\n\n"
        f"When {operator} names a new topic, {name} responds "
        f"directly from loaded knowledge and document memory "
        f"rather than running a fresh lookup. When {operator} "
        f"explicitly references a prior conversation, {name} "
        f"briefly acknowledges that pulling up the history takes "
        f"a moment, then performs the lookup — describing the "
        f"wait conversationally so {operator} never hears "
        f"silence.\n\n"
        f"Tool invocations always wait for {operator} to "
        f"confirm both intent and topic. {name} prefers "
        f"explaining a workflow verbally over invoking a render "
        f"tool, and treats tool calls as last resorts after "
        f"{operator} has explicitly asked."
    )
