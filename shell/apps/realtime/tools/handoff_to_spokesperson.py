"""`handoff_to_spokesperson` — R7.1 sync tool.

The avatar suggests ending the current session and
opening a new one with a different spokesperson in the
same workspace. Returns a structured nav event the SPA
dispatches on (similar shape to `show_videos_tab`); the
session itself doesn't end here — the operator confirms
in the SPA, ends this session, and creates the next one
via `POST /api/realtime_sessions/`.

Cross-workspace handoffs are rejected (contract rule 6 +
the explicit scope-lock requirement). Same-spokesperson
handoffs are rejected (no-op).

Pro+ tier only: Starter workspaces have spokespeople=1
in their tier limits, so handoff is structurally
meaningless. The tier gate at the catalog + dispatcher
level prevents Starter sessions from even seeing this
tool.

Cost: $0 (one DB lookup). Sync.
"""
from __future__ import annotations

from typing import Any

from . import register_tool


@register_tool(
    name="handoff_to_spokesperson",
    description=(
        "Suggest switching to a different spokesperson in "
        "this workspace. Use when the operator's question is "
        "clearly outside this spokesperson's expertise. "
        "Pass `target_spokesperson_id`. "
        "SAY ALOUD before invoking: 'I think <Name> would be "
        "a better fit for that — want me to hand you off?' "
        "Then INVOKE. After invoking, the SPA offers a "
        "confirm dialog. Keep the conversation alive in case "
        "they decline."
    ),
    cost_micros=0,
    workspace_scoped=True,
    is_async=False,
    tier_required="pro",
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Build the handoff nav event after validating the
    target spokesperson.

    Args:
        session: the active `RealtimeSession`.
        args: ``{target_spokesperson_id: str}`` — required.

    Returns:
        ``{event, target_spokesperson_id,
        target_spokesperson_name, message}`` — the SPA
        dispatches on `event` and offers the operator an
        "Open session with X?" confirm.

    Raises:
        ``ValueError`` if ``target_spokesperson_id`` is
        missing, names a spokesperson in a different
        workspace, or names this session's spokesperson.
    """
    # Lazy import — avoids cross-app coupling at module
    # load time.
    from apps.spokespeople.models import Spokesperson

    target_id = (args.get("target_spokesperson_id") or "").strip()
    if not target_id:
        raise ValueError("target_spokesperson_id is required")

    if str(target_id) == str(session.spokesperson_id):
        raise ValueError(
            "can't hand off to the same spokesperson — pick a different one"
        )

    try:
        target = Spokesperson.objects.get(
            pk=target_id, workspace=session.workspace,
        )
    except Spokesperson.DoesNotExist:
        # Could be cross-workspace or genuinely-unknown.
        # Same error either way — don't leak existence of
        # other-workspace spokespeople through the message.
        raise ValueError(
            f"spokesperson {target_id!r} not in this workspace"
        )

    return {
        "event": "handoff_to_spokesperson",
        "target_spokesperson_id": str(target.id),
        "target_spokesperson_name": target.name,
        "message": (
            f"Want to switch to {target.name}? "
            "End this session and I'll suggest opening one with them."
        ),
    }
