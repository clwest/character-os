"""`agent_consult` — invoke a specific u-d-b agent by name.

**SESSION 216 — engine-bridge product pattern.** Companion to
``consult_engine``; same product framing. v1 instance of the hookup
that lets a Character OS spokesperson route to a specific named
agent inside the customer's engine. Per-workspace engine config is
the queued generalisation. See
``docs/handoffs/SESSION_216_BRIDGE_TOOLS_REFRAME.md``.

Third engine-bridge realtime tool (companion to ``consult_engine``
and ``query_spider_data``). Where ``consult_engine`` is the general
"ask the engine's PA anything" tool, this one names a specific
expert agent inside u-d-b's AGENT_MAP (e.g. ``CTOAgent``,
``COOAgent``, ``MarketIntelligenceAgent``) so the answer comes
back with that agent's specific framing + analytic lens.

When to use:
- ``CTOAgent`` for system architecture, technical debt, scaling
- ``COOAgent`` for roadmap, sprint planning, operational risk
- ``MarketIntelligenceAgent`` for market signals + competitive
- ``CreativeDirectorAgent`` for content strategy + brand voice
- Other AGENT_MAP entries by name

Bridge architecture: same HTTP POST → u-d-b ``/api/pa/chat/`` →
poll → return. The PA dispatches to the named agent internally
via its agent routing layer.

Configuration: same env vars as ``consult_engine``.

Cost: 7_500 micros ($0.0075). Slightly higher than the generic
consult_engine because named-agent dispatch typically chains
several agent-internal tool calls. Still well under most tier
thresholds.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

from . import register_tool


logger = logging.getLogger(__name__)


DEFAULT_BASE_URL = "http://localhost:8000"
HTTP_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 1.5
MAX_POLL_SECONDS = 35


def _get_base_url() -> str:
    return os.environ.get("UDB_PA_API_URL", DEFAULT_BASE_URL).rstrip("/")


def _get_token() -> str | None:
    token = os.environ.get("UDB_PA_API_TOKEN", "").strip()
    return token or None


def _http_request(url: str, method: str, body: dict | None, token: str):
    data = json.dumps(body).encode("utf-8") if body is not None else None
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Token {token}",
    }
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=HTTP_TIMEOUT_SECONDS) as resp:
            return json.loads(resp.read().decode("utf-8")), resp.status
    except urllib.error.HTTPError as exc:
        body_text = exc.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(body_text)
        except json.JSONDecodeError:
            parsed = {"error": body_text}
        return parsed, exc.code


@register_tool(
    name="agent_consult",
    # Under 500-char cap. Pre-narration cue dropped — Runway's LLM
    # ignored it in real-mode dogfood. Narration of the answer
    # belongs to the SPA (BridgeAnswerPanel) + the operator in v1;
    # VO-arc TTS playback is the v2 path. Same constraint as
    # consult_engine.
    description=(
        "Invokes a specific u-d-b expert agent by name when a "
        "question wants a specific lens: CTOAgent for architecture, "
        "COOAgent for roadmap, MarketIntelligenceAgent for market "
        "signals, CreativeDirectorAgent for content strategy. Pass "
        "`agent_name` and `question`. For general questions, prefer "
        "consult_engine. The agent's response renders on screen "
        "for the operator to read; the avatar's role is to invoke, "
        "not recite."
    ),
    cost_micros=7_500,
    workspace_scoped=True,
    is_async=False,
    tier_required="starter",
    dedup_enabled=True,
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Ask u-d-b's PA to invoke a named agent.

    Args:
        session: the active ``RealtimeSession`` (unused for routing).
        args: ``{agent_name: str, question: str}``. Both required.

    Returns:
        ``{event, agent_name, question, answer, conversation_id?,
        latency_ms, engine_url}`` on success, or error variant on
        failure. Errors returned, not raised.

    Raises:
        ``ValueError`` when ``agent_name`` or ``question`` is
        missing or blank.
    """
    agent_name = (args.get("agent_name") or "").strip()
    question = (args.get("question") or "").strip()
    if not agent_name:
        raise ValueError("agent_name is required")
    if not question:
        raise ValueError("question is required")

    base = _get_base_url()
    token = _get_token()
    started = time.perf_counter()

    if token is None:
        return {
            "event": "agent_consulted",
            "agent_name": agent_name,
            "question": question,
            "error": "UDB_PA_API_TOKEN is not configured.",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "engine_url": base,
        }

    # Frame the request so PA dispatches to the named agent.
    framed_question = (
        f"Route this to {agent_name} via agent_router and return "
        f"that agent's response (do not paraphrase before "
        f"returning):\n\n{question}"
    )

    payload = {
        "message": framed_question,
        "source": "character-os-agent-consult",
        "platform": "api",
        "context": {
            "source": "character-os-agent-consult",
            "agent_name": agent_name,
            "spokesperson_id": str(getattr(session, "spokesperson_id", "") or ""),
            "workspace_id": str(getattr(session, "workspace_id", "") or ""),
        },
    }
    data, status = _http_request(f"{base}/api/pa/chat/", "POST", payload, token)

    if status != 200 or not data.get("success"):
        return {
            "event": "agent_consulted",
            "agent_name": agent_name,
            "question": question,
            "error": (
                f"engine POST failed: HTTP {status} "
                f"{data.get('error') or data.get('detail') or data}"
            ),
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "engine_url": base,
        }

    task_id = data.get("task_id")
    if not task_id:
        return {
            "event": "agent_consulted",
            "agent_name": agent_name,
            "question": question,
            "error": f"engine POST returned no task_id: {data}",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "engine_url": base,
        }

    status_url = f"{base}/api/pa/chat/status/{task_id}/"
    while (time.perf_counter() - started) < MAX_POLL_SECONDS:
        time.sleep(POLL_INTERVAL_SECONDS)
        poll_data, poll_status = _http_request(status_url, "GET", None, token)
        if poll_status != 200:
            return {
                "event": "agent_consulted",
                "agent_name": agent_name,
                "question": question,
                "error": (
                    f"engine poll failed: HTTP {poll_status} "
                    f"{poll_data.get('error') or poll_data}"
                ),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "engine_url": base,
            }

        task_state = poll_data.get("status", "unknown")
        if task_state == "completed":
            return {
                "event": "agent_consulted",
                "agent_name": agent_name,
                "question": question,
                "answer": poll_data.get("content", ""),
                "conversation_id": poll_data.get("conversation_id"),
                "tool_runs": poll_data.get("tool_runs", []),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "engine_url": base,
            }
        if task_state == "failed":
            return {
                "event": "agent_consulted",
                "agent_name": agent_name,
                "question": question,
                "error": (
                    f"engine task failed: "
                    f"{poll_data.get('error') or 'unknown failure'}"
                ),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "engine_url": base,
            }

    return {
        "event": "agent_consulted",
        "agent_name": agent_name,
        "question": question,
        "error": f"engine timed out after {MAX_POLL_SECONDS}s.",
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "engine_url": base,
    }
