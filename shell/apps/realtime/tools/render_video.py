"""`render_video` — R7.2 async tool.

The operator says "make me a video about X" mid-conversation;
the avatar invokes this tool. The tool:

1. Checks the workspace's per-month video tier limit.
2. Resolves the recipe (default ``talking_head``; operator
   can override via ``args.recipe``).
3. Fires the recipe's starter — creates a `Composition` +
   the first `CompositionStep` rows.
4. Returns ``{event, composition_id, recipe, message}`` so
   the SPA can render a "rendering…" toast + link to the
   composition status page.

The composition then executes asynchronously via the V arc's
existing `execute_composition` Celery chain. The audit row
(R7.0's `RealtimeToolInvocation`) links to the produced
`Composition` via `produced_composition` for cost
attribution + audit.

**Cost: $0.08 (80_000 micros)** — sits over the v1 approval
threshold ($0.05). This is the load-bearing tool that
exercises R7.0's `awaiting_approval` flow with a real
side-effect, not a synthetic test tool.

**Tier**: starter. The per-month video cap (10 / 30 /
unlimited) lives in `apps.billing.services.check_video_limit`
and gates render execution at the cost-control level
already.

**Q-r-3 (mid-session document refresh)**: not touched here.
The composition runs against the K6 brief synthesis path
the V arc already uses, so K2 retrieval happens at
composition-execute time as usual.
"""
from __future__ import annotations

from typing import Any

from . import register_tool


COST_MICROS = 80_000  # $0.08 — over the $0.05 default threshold

# Default recipe when the avatar invokes without `recipe`
# arg. `talking_head` is the smallest + most generic
# starter; one step, one Runway call.
DEFAULT_RECIPE = "talking_head"


@register_tool(
    name="render_video",
    description=(
        "Render a video clip the operator can share. Use when "
        "they ask for an ad, a short video, or a clip about X. "
        "REQUIRED: `script` — verbatim spoken text (3-5 "
        "sentences). If they give a TOPIC instead, COMPOSE the "
        "script yourself in your voice, then pass it. "
        "SAY ALOUD before invoking: 'Got it — let me put that "
        "together. About 30 seconds.' Then INVOKE. After "
        "invoking, tell them it's rendering (~30-45 sec) and "
        "keep talking — do NOT wait silently."
    ),
    cost_micros=COST_MICROS,
    workspace_scoped=True,
    is_async=True,
    tier_required="starter",
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Fire a composition starter for this session's
    spokesperson.

    Args:
        session: the active `RealtimeSession`. Provides the
            workspace + spokesperson context.
        args: ``{script: str, recipe?: str, name?: str,
            use_knowledge?: bool}``. ``script`` required;
            ``recipe`` defaults to ``"talking_head"``.

    Returns:
        ``{event: "render_video_queued", composition_id,
        recipe, message}``. The generic Celery task
        wrapper (`execute_tool_invocation`) sees the
        ``composition_id`` field and links it to the
        invocation row's ``produced_composition`` FK.

    Raises:
        ``ValueError`` for: missing/empty script, unknown
        recipe, tier limit exceeded. The dispatcher catches
        + records the audit row as FAILED.
    """
    # Lazy imports — keep this tool module decoupled from
    # billing + compositions at module load time.
    from apps.billing.services import TierLimitExceeded, check_video_limit
    from apps.compositions.recipes import RECIPES

    script = (args.get("script") or "").strip()
    if not script:
        raise ValueError("script is required")

    recipe_name = (args.get("recipe") or DEFAULT_RECIPE).strip()
    recipe = RECIPES.get(recipe_name)
    if recipe is None:
        raise ValueError(
            f"unknown recipe: {recipe_name!r} (available: "
            f"{sorted(RECIPES.keys())[:5]}…)"
        )

    # Tier gate — per-month video cap. Catches Starter
    # workspaces past their 10/month, Pro past 30/month,
    # etc. Agency is unlimited.
    try:
        check_video_limit(session.workspace)
    except TierLimitExceeded as exc:
        # Surface the structured upgrade payload as part
        # of the error message so the SPA can render it.
        message = exc.payload.get("message", "video tier limit exceeded")
        raise ValueError(message)

    # Build starter kwargs. Most recipes take
    # ``workspace`` + ``spokesperson`` + a content arg
    # (script / prompt / etc). The recipe registry has a
    # `form_field_map` mapping but for v1 we only support
    # `talking_head` shapes — script-driven starters.
    starter_kwargs: dict[str, Any] = {
        "workspace": session.workspace,
        "spokesperson": session.spokesperson,
        "script": script,
    }
    optional_name = (args.get("name") or "").strip()
    if optional_name:
        starter_kwargs["name"] = optional_name
    if "use_knowledge" in args:
        starter_kwargs["use_knowledge"] = bool(args["use_knowledge"])

    composition = recipe.starter(**starter_kwargs)

    # The V arc's existing `execute_composition` Celery
    # chain runs the steps. The tool returns immediately
    # with the composition id so the audit row can link +
    # the SPA can track to completion via existing
    # composition endpoints.
    from apps.compositions.tasks import execute_composition

    execute_composition.delay(str(composition.id))

    return {
        "event": "render_video_queued",
        "composition_id": str(composition.id),
        "recipe": recipe_name,
        "message": (
            f"Rendering a {recipe_name} clip — I'll let you know "
            "when it's ready."
        ),
    }
