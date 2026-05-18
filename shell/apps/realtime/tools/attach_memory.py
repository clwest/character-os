"""`attach_memory` — R7.3 async tool.

Mid-session memory commit. The operator (or the avatar
on its own initiative) invokes this when they want the
spokesperson to remember the current conversation from
the next session onward, without waiting for the natural
session-end transcript-capture flow.

Pairs with **R6.1** (SESSION 152) — the R6 query was
widened to include any `RealtimeSession` with a
`transcript_asset` attached, regardless of status. The
next session's `compose_realtime_document` therefore
picks up the snapshot this tool commits even while the
current session is still READY.

The tool delegates to ``apps.realtime.tasks.capture_transcript``
(extracted from R5's session-end task in SESSION 152 so
both code paths share one implementation). The snapshot
replaces any existing `transcript_asset` on this session
— last-write-wins — which resolves **Q-r-8** (cross-
session tool side effects: the operation is idempotent
and the race window is the standard media-engine fetch
delay, not a multi-write merge problem).

**Cost: ~$0.001 (1_000 micros)** — well under the v1
approval threshold. One media-engine call (pulls the
partial transcript from Runway). No LLM call here; the
R6 LLM synthesis happens at the NEXT session-create
time.

**Tier: pro**. Mid-session memory commits are a power-
user feature for long planning calls; Starter operators
get end-of-session memory automatically via R5.

**Async**: the media-engine call is network I/O. The
generic Celery wrapper (`execute_tool_invocation`) picks
up `asset_id` from the return payload and links it to
the invocation row's `produced_asset` FK for audit.
"""
from __future__ import annotations

from typing import Any

from . import register_tool


COST_MICROS = 1_000  # ~$0.001 — one media-engine call


@register_tool(
    name="attach_memory",
    description=(
        "Save the current conversation so I remember it next "
        "time. MANDATORY TRIGGERS: 'save what we talked "
        "about', 'remember this', 'lock this in', 'keep this "
        "for later'. "
        "SAY ALOUD before invoking: 'Good idea — saving that "
        "now so I remember next time.' Then INVOKE. Fire-"
        "and-forget — no confirmation comes back. After "
        "invoking, keep the conversation going naturally. Do "
        "NOT wait for verification."
    ),
    cost_micros=COST_MICROS,
    workspace_scoped=True,
    is_async=True,
    tier_required="pro",
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Capture the current session's transcript snapshot
    as an ``Asset(TRANSCRIPT)`` so R6 can project it into
    the next session's grounding document.

    Args:
        session: the active `RealtimeSession`. The
            snapshot is keyed to this session's id;
            R6's widened query (R6.1) picks it up
            regardless of session status.
        args: ignored in v1. Future extensions
            (an explicit "label" for the memory snapshot,
            say) can land without changing the registry
            shape.

    Returns:
        ``{event: "memory_committed", asset_id, session_id,
        status, message}``. The Celery wrapper sees
        ``asset_id`` and links it to the invocation row's
        ``produced_asset`` FK.

        Status values:
        * ``persisted`` — fresh transcript captured + Asset
          created.
        * ``empty`` — Runway hasn't recorded enough audio
          yet (early in the session). Operator should
          wait + try again.
        * ``upstream_error`` — media-engine call failed.
          Not retried here (the failure surfaces to the
          operator immediately); the natural session-end
          R5 task will retry at session-end.

    Raises:
        Never — the helper handles failures cleanly. The
        generic Celery wrapper marks the invocation
        SUCCEEDED with the structured result; the SPA
        renders the appropriate UX based on ``status``.
    """
    # Lazy import — avoids tool-load-time circular dep
    # with apps.realtime.tasks.
    from apps.realtime.tasks import capture_transcript

    result = capture_transcript(session)

    status = result.get("status", "unknown")
    asset_id = result.get("asset_id")

    if status == "persisted":
        message = "I'll remember this conversation next time we talk."
    elif status == "empty":
        message = (
            "Not enough has been recorded yet — try again "
            "after we've talked a bit more."
        )
    elif status == "upstream_error":
        message = (
            "I couldn't capture the snapshot just now. "
            "Don't worry — I'll save it at the end of "
            "our session."
        )
    else:
        message = "Memory commit attempted."

    payload: dict[str, Any] = {
        "event": "memory_committed",
        "session_id": str(session.id),
        "status": status,
        "message": message,
    }
    if asset_id:
        payload["asset_id"] = asset_id
    if result.get("chars"):
        payload["chars"] = result["chars"]
    return payload
