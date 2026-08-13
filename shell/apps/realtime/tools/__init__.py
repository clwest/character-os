"""Realtime tool registry — R7 (realtime arc).

The avatar's LLM invokes tools mid-conversation via WebRTC
data-channel events. Each tool is a server-side handler
registered here; the dispatch surface
(`apps.realtime.dispatch`) looks tools up by name + routes
the invocation through a `RealtimeToolInvocation` audit row.

The registry shape mirrors V's primitive + recipe registries:
declarative `register_tool(name=...)` decorator on each tool
module. Adding a new tool is one new file + one decorated
function. No view-layer changes needed.

Contract rule 6 — workspace-scoped tools — is enforced at
dispatch time, not at registration. Tools declare whether
they need a workspace gate (`workspace_scoped=True`); the
dispatch surface validates the requesting session's
workspace against the resource the tool will touch.

Contract rule 9 (mock-mode) flows through naturally: tools
that call external services check their respective
force-mock flags. The registry itself is provider-agnostic.

v1 catalog (R7.0 ships the first; R7.1 + R7.2 ship the
remaining five):

* `show_videos_tab` (R7.0) — UI-only nav event.
* `recall_knowledge` (R7.1) — RAG against K2.
* `recall_recent_conversations` (R7.1) — read prior
  `Asset(TRANSCRIPT)` rows.
* `handoff_to_spokesperson` (R7.1) — cross-spokesperson
  event in the same workspace.
* `render_video` (R7.2) — async, fires a composition
  starter. The threshold-crossing tool.
* `attach_memory` (R7.2) — async, mid-session memory
  commit.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Protocol


class ToolExecutor(Protocol):
    """Tool executor signature. Receives the session + the
    resolved args dict, returns a JSON-serializable result
    payload. Raises on failure (the dispatcher catches +
    marks the invocation FAILED).
    """

    def __call__(self, session, args: dict) -> dict: ...


# Tier rank — used by `get_workspace_tools` to filter the
# catalog. Higher rank includes everything below it
# (Agency sees all; Starter sees only Starter-tier tools).
_TIER_RANK: dict[str, int] = {
    "starter": 0,
    "pro": 1,
    "agency": 2,
}


def _tier_rank(tier: str) -> int:
    """Defensive lookup — unknown tier strings rank below
    Starter so a misconfigured Workspace can't accidentally
    unlock Pro/Agency tools."""
    return _TIER_RANK.get(tier, -1)


@dataclass(frozen=True, slots=True)
class ToolSpec:
    """Declarative spec for one registered tool.

    Attributes:
        name: stable identifier the LLM uses to invoke
            (matches the WebRTC data-channel event name).
        description: human-readable explanation surfaced to
            the LLM as part of its tool catalog.
        cost_micros: per-invocation cost estimate. Used by
            the dispatch surface to gate approval (any
            tool whose cost > the workspace's threshold
            triggers the approval modal). $0 for free
            tools (UI nav, sync DB reads).
        workspace_scoped: whether the executor needs the
            session's workspace as part of its scope
            guard. UI-only tools (`show_videos_tab`) are
            False — they don't touch workspace-scoped
            resources beyond the session itself, which is
            already workspace-gated at dispatch time.
        executor: the callable that runs the tool.
        is_async: whether the executor should run inline
            (sync) or be deferred to a Celery task. R7.0
            ships sync only; async lands in R7.2 with
            `render_video` + `attach_memory`.
        tier_required: minimum tier that exposes this tool
            (R7.1 — resolves Q-r-4). One of
            ``'starter'`` / ``'pro'`` / ``'agency'``. The
            catalog (returned by `get_workspace_tools`)
            and the dispatcher (defense in depth) both
            consult this. Default ``'starter'`` keeps
            tools open to all tiers.
        dedup_enabled: whether the dispatcher's SESSION 213
            Fix 2A retry-suppression window applies. Default
            True covers the Q-r-2 spam case (avatar can't see
            tool-result events, re-fires the same lookup
            3-4 times). Mutating tools that legitimately fire
            repeatedly with identical args (``attach_memory``'s
            last-write-wins semantics per Q-r-8) opt out by
            setting False.
    """

    name: str
    description: str
    cost_micros: int
    workspace_scoped: bool
    executor: ToolExecutor
    is_async: bool = False
    tier_required: str = "starter"
    dedup_enabled: bool = True


# In-memory registry. Populated at module import via the
# `register_tool` decorator on each tool's module-level
# `executor` function. Module imports happen below at file
# bottom (after registry definitions) so the registry is
# fully populated by import time.
_TOOLS: dict[str, ToolSpec] = {}


def register_tool(
    name: str,
    *,
    description: str,
    cost_micros: int = 0,
    workspace_scoped: bool = True,
    is_async: bool = False,
    tier_required: str = "starter",
    dedup_enabled: bool = True,
) -> Callable[[ToolExecutor], ToolExecutor]:
    """Decorator that registers a tool with the realtime
    catalog.

    Idempotent: re-registering the same name overwrites the
    prior spec (helps test-suite hot-reload + fixture
    helpers). Operators should not rely on this in
    production — it's a development convenience.

    Args:
        name: stable identifier the LLM uses to invoke.
        description: short text describing the tool's effect.
            Surfaced to the avatar's LLM at session-create.
        cost_micros: invocation cost estimate (micros of USD;
            50_000 = $0.05 = the v1 default approval
            threshold). Zero for free tools.
        workspace_scoped: whether the executor's effect is
            workspace-bound. Tools that read or write
            workspace-scoped resources must be True; UI-only
            tools can be False.
        is_async: whether to run via Celery instead of inline.
        tier_required: minimum tier ('starter' / 'pro' /
            'agency') that exposes this tool. Used by
            `get_workspace_tools` + the dispatcher.
        dedup_enabled: whether SESSION 213 Fix 2A retry
            suppression applies. Default True. Set False for
            mutating tools that fire repeatedly by design.
    """

    def _wrap(fn: ToolExecutor) -> ToolExecutor:
        _TOOLS[name] = ToolSpec(
            name=name,
            description=description,
            cost_micros=cost_micros,
            workspace_scoped=workspace_scoped,
            executor=fn,
            is_async=is_async,
            tier_required=tier_required,
            dedup_enabled=dedup_enabled,
        )
        return fn

    return _wrap


def get_tool(name: str) -> ToolSpec:
    """Look up a tool by name. Raises ``KeyError`` if not
    registered — the dispatch surface translates this to
    HTTP 400 ``{detail: 'unknown tool'}``.
    """
    return _TOOLS[name]


def list_tools() -> list[ToolSpec]:
    """Return all registered tools, ordered by name. Used
    by the session-create flow to project the catalog into
    the Runway session's `tools` argument (R7.1+ — R7.0
    only registers `show_videos_tab` so the session-create
    side doesn't change yet).
    """
    return sorted(_TOOLS.values(), key=lambda t: t.name)


def get_workspace_tools(workspace) -> list[ToolSpec]:
    """Return the tool catalog visible to this workspace.

    R7.1 (Q-r-4 resolution): filters by the workspace's
    subscription tier. A tool with ``tier_required='pro'``
    is excluded from Starter workspaces' catalogs; an
    Agency tool would be Pro-or-Agency only. Default
    ``tier_required='starter'`` keeps tools open to all.

    Tier resolution lives in
    ``apps.billing.services.get_workspace_tier`` —
    the function lazily creates a Starter subscription
    when one is missing, matching the rest of the billing
    contract.
    """
    # Lazy import — billing depends on workspace, which can
    # be in mid-load when this module first imports.
    from apps.billing.services import get_workspace_tier

    workspace_rank = _tier_rank(get_workspace_tier(workspace))
    return [
        spec
        for spec in list_tools()
        if _tier_rank(spec.tier_required) <= workspace_rank
    ]


def clear_registry() -> None:
    """Test-only hook. Removes every registered tool — lets
    tests register synthetic tools without polluting
    fixtures across runs. Not called from production code.
    """
    _TOOLS.clear()


# Trigger tool registration. Each module's import side-
# effect is the `register_tool(...)` decorator on its
# executor. Order doesn't matter; the registry is a flat
# dict.
from . import show_videos_tab  # noqa: F401,E402
from . import recall_knowledge  # noqa: F401,E402
from . import recall_recent_conversations  # noqa: F401,E402
from . import handoff_to_teammate  # noqa: F401,E402  (SESSION 240: Python module renamed; registered tool name `handoff_to_spokesperson` preserved as external contract)
from . import render_video  # noqa: F401,E402
from . import attach_memory  # noqa: F401,E402
from . import consult_engine  # noqa: F401,E402
from . import query_spider_data  # noqa: F401,E402
from . import agent_consult  # noqa: F401,E402
