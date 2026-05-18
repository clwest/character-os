"""`show_videos_tab` — R7.0's first tool.

UI-only navigation event. The avatar invokes this when the
operator says "show me my videos" or equivalent; the SPA
receives the event payload via its session's WebSocket /
SDK client-event channel and flips the route to the
spokesperson's videos page.

No backend side effect — no workspace gate beyond the
session itself (which is already workspace-scoped at
dispatch time). No external service call. No persistence
beyond the audit row the dispatcher creates.

Cost: $0. Well under the v1 approval threshold; always
executes inline.
"""
from __future__ import annotations

from typing import Any

from . import register_tool


@register_tool(
    name="show_videos_tab",
    description=(
        "Navigate the operator's SPA to this spokesperson's "
        "videos tab. Use when they ask to 'see my videos', "
        "'show me what I've made', 'open the videos page'. "
        "SAY ALOUD before invoking: 'Pulling those up now.' "
        "Then INVOKE. The SPA flips routes immediately — you "
        "do not need a follow-up message."
    ),
    cost_micros=0,
    workspace_scoped=False,
    is_async=False,
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Return the nav event the SPA consumes.

    Args:
        session: the active `RealtimeSession`. Carries the
            spokesperson + workspace context.
        args: ignored in v1 — no parameters needed. Future
            extensions (a `filter` arg to pre-filter the
            videos list, say) can land without changing
            the registry shape.

    Returns:
        A JSON-serializable nav event:
        ``{"event": "show_videos_tab", "spokesperson_id": ...}``.
        The SPA dispatches on `event` and renders the
        appropriate route.
    """
    return {
        "event": "show_videos_tab",
        "spokesperson_id": str(session.spokesperson_id),
    }
