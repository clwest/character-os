"""Engine-bridge resolver — EB.2 (SESSION 217).

Single lookup the three bridge tools (``consult_engine`` /
``query_spider_data`` / ``agent_consult``) call instead of reading
``os.environ`` directly. Generalises the SESSION 215 env-var
hardcode into a per-workspace ``EngineConnection`` row so customer
N's spokesperson talks to customer N's engine.

See ``docs/design/ENGINE_BRIDGE_V1.md`` — 8 contract rules.

Resolution order (contract rules 2, 3, 5, 8):

1. **Pro+ tier gate.** Starter workspaces resolve to ``None``
   regardless of row state.
2. **Enabled DB row.** ``EngineConnection`` matching
   ``(workspace, engine_kind='udb_pa', enabled=True)``.
3. **Env-var fallback.** ``UDB_PA_API_TOKEN`` + (optional)
   ``UDB_PA_API_URL``. The fallback is a deprecation runway —
   it keeps the SESSION 215 24/7-Global-AI deployment alive
   until the SPA admin (EB.4) ships and the operator pastes the
   URL into a row.
4. **``None``** — bridge tools then return their existing
   ``configured-but-unreachable`` error shape.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from apps.accounts.models import Workspace
from apps.billing.services import get_workspace_tier

from .models import EngineConnection


# Default base URL for the env-var fallback. Aligns with
# consult_engine.py's prior value (8020 = alt port the sibling project binds to
# when it shares the laptop with character-os:8000). Resolves
# Q-eb-5 — query_spider_data.py + agent_consult.py used to default
# to :8000 which collides with character-os itself.
ENV_DEFAULT_BASE_URL = "http://localhost:8020"


# Pro+ tier set (rule 8). Mirrors R7.1's _TIER_RANK pattern but
# only needs the binary "is Pro+ or higher" answer here.
_PRO_OR_HIGHER = frozenset({"pro", "agency"})


@dataclass(frozen=True)
class ResolvedEngine:
    """Resolved engine endpoint, ready for the bridge tools to call.

    ``source`` indicates which path resolved — ``"db"`` for a
    workspace ``EngineConnection`` row, ``"env"`` for the env-var
    fallback. Surfaces in audit/logging so the deprecation status
    of a given workspace is visible.

    ``enabled`` is always ``True`` on a ``ResolvedEngine`` — disabled
    rows never resolve. The field exists so callers can record what
    they saw without re-querying.
    """

    url: str
    token: str
    kind: str
    source: Literal["db", "env"]
    enabled: bool = True


def resolve_engine_connection(workspace: Workspace) -> ResolvedEngine | None:
    """Resolve the engine-bridge connection for a workspace.

    Returns ``None`` when the workspace is Starter, when no enabled
    row exists AND no env fallback is configured, or when both an
    explicitly disabled row exists AND no env fallback. The bridge
    tools translate ``None`` into their existing
    ``configured-but-unreachable`` error response.
    """
    # Rule 8: Pro+ tier gate at the resolver, not just the SPA.
    # Starter workspaces with stray rows (e.g. tier downgrade)
    # cannot use them.
    tier = get_workspace_tier(workspace)
    if tier not in _PRO_OR_HIGHER:
        return None

    # Rule 1 + 2: workspace-scoped lookup. ``unique_together``
    # guarantees at most one enabled row per (workspace, kind);
    # ``.first()`` is sufficient.
    row = EngineConnection.objects.filter(
        workspace=workspace,
        engine_kind=EngineConnection.Kind.UDB_PA,
        enabled=True,
    ).first()
    if row is not None:
        return ResolvedEngine(
            url=row.engine_url.rstrip("/"),
            token=row.engine_token,
            kind=row.engine_kind,
            source="db",
        )

    # Rule 3: env-var fallback. ``UDB_PA_API_TOKEN`` is the
    # required-to-resolve key; ``UDB_PA_API_URL`` falls back to
    # ``ENV_DEFAULT_BASE_URL`` when unset. Matches the prior
    # bridge-tool behaviour byte-for-byte.
    env_token = os.environ.get("UDB_PA_API_TOKEN", "").strip()
    if env_token:
        env_url = (
            os.environ.get("UDB_PA_API_URL", ENV_DEFAULT_BASE_URL)
            .strip()
            .rstrip("/")
        )
        return ResolvedEngine(
            url=env_url,
            token=env_token,
            kind=EngineConnection.Kind.UDB_PA.value,
            source="env",
        )

    return None


# ─── C3 (S2887 side-step) ────────────────────────────────────────────
# Bridge-answer Asset persistence. Each of the three bridge tools
# (consult_engine / query_spider_data / agent_consult) calls this
# helper on the success path to durably persist the engine's answer as
# an ``Asset(role=BRIDGE_ANSWER)``. Sync dispatch (`_execute_inline`)
# harvests the returned ``asset_id`` and links it to the invocation
# row's ``produced_asset`` FK, mirroring the async wrapper's shape.
#
# The engine bridge is Character OS's HTTP boundary into an external
# customer engine (agent framework, live data system). v1 concrete
# engine kind is `udb_pa` — the reference implementation targets a
# customer's Personal Assistant HTTP surface.


# Title cap headroom — the `[tool_name] ` prefix consumes up to 24
# chars (e.g. `[query_spider_data] `), so we cap the question tail at
# 96 chars to guarantee the composed title fits inside the Asset.title
# CharField(max_length=120) contract.
_BRIDGE_ANSWER_TITLE_QUESTION_CAP = 96


def create_bridge_answer_asset(
    session,
    *,
    tool_name: str,
    question: str,
    answer: str,
    engine_url: str,
    cost_micros: int,
    conversation_id: str | None = None,
    latency_ms: int | None = None,
    intent: str | None = None,
):
    """Persist an engine-bridge answer as an ``Asset(BRIDGE_ANSWER)``.

    Called only on the success path (a non-empty ``answer``). Failures
    (config missing, unreachable engine, timeout) return their existing
    error dict without invoking this helper.

    Returns the created ``Asset`` instance. The bridge tool's caller
    surfaces ``str(asset.id)`` in its return dict under the ``asset_id``
    key so both async and sync dispatch link it to
    ``RealtimeToolInvocation.produced_asset``.
    """
    # Lazy imports keep the module load-time surface tight and avoid a
    # circular between apps.realtime and apps.compositions.
    from apps.compositions.models import Asset, AssetRole, AssetType

    q = (question or "").strip()
    truncated = q[:_BRIDGE_ANSWER_TITLE_QUESTION_CAP]
    title = f"[{tool_name}] {truncated}"

    source_spec: dict[str, object] = {
        "tool_name": tool_name,
        "engine_url": engine_url,
        "question": q,
    }
    if conversation_id:
        source_spec["conversation_id"] = conversation_id
    if latency_ms is not None:
        source_spec["latency_ms"] = latency_ms
    if intent:
        source_spec["intent"] = intent

    return Asset.objects.create(
        workspace=session.workspace,
        asset_type=AssetType.TRANSCRIPT,
        role=AssetRole.BRIDGE_ANSWER,
        title=title,
        file_path="",
        inline_content=answer or "",
        source_spec=source_spec,
        cost_micros=cost_micros,
        composition=None,
    )
