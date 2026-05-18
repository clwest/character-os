"""`recall_knowledge` — R7.1 sync tool.

RAG against the K2 retrieval surface. The avatar invokes
this mid-conversation when it needs to look up a specific
fact in the workspace's knowledge corpus. Returns the
top-K matching chunks as a structured payload the SPA
can render (citation panel; "here's what your knowledge
says" toast).

Same workspace + visibility rules as K6/K8 — retrieval
is scoped by `spokesperson.workspace` and the M2M
visibility filter, structurally. Cross-workspace leak is
impossible by construction (contract rule 5 of the
knowledge layer).

Cost: ~$0.001 per call (one OpenAI embedding for the
query + one Postgres CosineDistance scan). Well under
the v1 approval threshold; always executes inline.
Honors `EMBEDDING_FORCE_MOCK` automatically — the
embedding service checks the flag internally.
"""
from __future__ import annotations

from typing import Any

from apps.embeddings.retrieval import retrieve_for_spokesperson

from . import register_tool


DEFAULT_TOP_K = 3
MAX_TOP_K = 5


@register_tool(
    name="recall_knowledge",
    description=(
        "Search the spokesperson's workspace knowledge for a "
        "specific fact. Use when the operator asks a question "
        "whose answer might be in an attached doc. Pass the "
        "topic as `query`. "
        "SAY ALOUD before invoking: 'Let me check what I have "
        "on that.' Then INVOKE. The SPA renders a citation "
        "panel listing matched chunks. AFTER invoking, briefly "
        "summarise the key point in your own words ('From what "
        "I'm seeing, …') and keep going — don't recite chunks "
        "verbatim; the operator already sees them."
    ),
    cost_micros=1_000,  # ~$0.001 per call
    workspace_scoped=True,
    is_async=False,
    tier_required="starter",
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Run a knowledge query for this session's spokesperson.

    Args:
        session: the active `RealtimeSession`. Carries the
            spokesperson + workspace context.
        args: ``{query: str, top_k: int}``. ``query``
            required; ``top_k`` optional (default 3, cap 5).

    Returns:
        ``{query, count, matches: [{chunk_id, document_id,
        document_title, text}]}`` — structured for the SPA
        to render a citation list. Empty ``matches`` is
        valid (no docs visible / no match).

    Raises:
        ``ValueError`` when ``query`` is missing or blank —
        the dispatcher catches + records the audit row as
        FAILED with the error message.
    """
    query = (args.get("query") or "").strip()
    if not query:
        raise ValueError("query is required")

    top_k = args.get("top_k", DEFAULT_TOP_K)
    try:
        top_k = int(top_k)
    except (TypeError, ValueError):
        top_k = DEFAULT_TOP_K
    top_k = max(1, min(top_k, MAX_TOP_K))

    chunks = retrieve_for_spokesperson(
        session.spokesperson, query=query, top_k=top_k,
    )
    return {
        "query": query,
        "count": len(chunks),
        "matches": [
            {
                "chunk_id": str(chunk.id),
                "document_id": str(chunk.document_id),
                "document_title": chunk.document.title,
                "text": chunk.chunk_text,
            }
            for chunk in chunks
        ],
    }
