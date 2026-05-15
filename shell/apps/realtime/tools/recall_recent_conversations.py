"""`recall_recent_conversations` — R7.1 sync tool.

Reads prior `Asset(TRANSCRIPT)` rows for this session's
spokesperson and returns per-session previews. Distinct
from R6's `compose_session_memory` (which summarizes
multiple prior sessions into one composed projection at
session-create time) — this tool returns the raw
session-by-session list so the avatar can quote a
specific prior session in-conversation.

Cost: $0 (single Postgres query). Sync. Honors
contract rule 1 — query filters by ``spokesperson``
which carries the workspace anchor.
"""
from __future__ import annotations

from typing import Any

from . import register_tool


DEFAULT_MAX_SESSIONS = 3
MAX_MAX_SESSIONS = 5

# Per-session preview cap — operator-facing snippet, not
# a full transcript. The avatar's LLM gets enough text to
# remember the topic without bloating the response.
PREVIEW_CHAR_BUDGET = 500


@register_tool(
    name="recall_recent_conversations",
    description=(
        "List recent past conversations this operator has "
        "had with this spokesperson. Returns session ids, "
        "end timestamps, and a short transcript preview "
        "for each."
    ),
    cost_micros=0,
    workspace_scoped=True,
    is_async=False,
    tier_required="starter",
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Return per-session previews of prior conversations.

    Args:
        session: the active `RealtimeSession`. Used to
            scope the query to its spokesperson + exclude
            this session itself from the results (the
            avatar shouldn't quote its own in-progress
            conversation).
        args: ``{max_sessions: int}`` — optional cap on
            the number of prior sessions to surface.

    Returns:
        ``{count, sessions: [{session_id, ended_at,
        preview}]}`` — newest first. ``preview`` is the
        first ~500 chars of the transcript text.
    """
    # Lazy import — avoids tools package needing
    # apps.realtime.models at module-import time, which
    # would create a circular dep with the dispatcher.
    from apps.realtime.models import RealtimeSession

    max_sessions = args.get("max_sessions", DEFAULT_MAX_SESSIONS)
    try:
        max_sessions = int(max_sessions)
    except (TypeError, ValueError):
        max_sessions = DEFAULT_MAX_SESSIONS
    max_sessions = max(1, min(max_sessions, MAX_MAX_SESSIONS))

    prior = list(
        RealtimeSession.objects.filter(
            spokesperson=session.spokesperson,
            status=RealtimeSession.Status.ENDED,
            transcript_asset__isnull=False,
        )
        .exclude(pk=session.pk)
        .select_related("transcript_asset")
        .order_by("-ended_at")[:max_sessions]
    )

    return {
        "count": len(prior),
        "sessions": [
            _format_session(s) for s in prior
        ],
    }


def _format_session(s) -> dict[str, Any]:
    asset = s.transcript_asset
    text = (asset.inline_content or "").strip() if asset else ""
    if len(text) > PREVIEW_CHAR_BUDGET:
        text = text[:PREVIEW_CHAR_BUDGET].rstrip() + "…"
    return {
        "session_id": str(s.id),
        "ended_at": s.ended_at.isoformat() if s.ended_at else None,
        "duration_seconds": s.duration_seconds,
        "preview": text,
    }
