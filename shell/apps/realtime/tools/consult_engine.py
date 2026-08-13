"""`consult_engine` — engine-bridge tool (v1 instance of the hookup pattern).

**SESSION 216 — engine-bridge product pattern.** This is the v1
instance of how *any* Character OS customer connects their external
engine (agents, spiders, live knowledge, decision systems) to a
customer-facing spokesperson. The hookup is intentionally an HTTP
boundary — Character OS doesn't absorb the customer's stack, it
just calls into it. v1 target is the sibling project's PA via
``UDB_PA_API_URL``; **queued slice "per-workspace engine config"**
generalises this so customer X's spokesperson calls customer X's
engine.

Narration is **panel-first, not avatar-first**. Runway's LLM can't
see tool results (Q-r-2), so engine answers render in the SPA's
``BridgeAnswerPanel`` for the customer to read during the
conversation. The avatar is the human anchor + conversational
front-end; the panel is the structured-data surface. This is the
intended UX, not a workaround.

A briefer soft-deprecate framing (SESSION 215) treated this as
operator-only dogfood — that framing was wrong; reversed in
SESSION 216. See
``docs/handoffs/SESSION_216_BRIDGE_TOOLS_REFRAME.md``.

The spokesperson invokes this when the operator asks a question that
the workspace knowledge corpus + recent conversations don't answer —
and the question is plausibly about the operator's broader portfolio,
live system state, current priorities, recent decisions, or anything
else only the engine's Rigby (the operator's full agentic PA) would
know.

Architecturally this is the first "engine bridge" tool: Character OS
realtime conversation → HTTP → the sibling project PA → answer text → back into the
realtime conversation. The engine stays put. Character OS becomes a
face for it without absorbing its agent/tool/spider universe.

Why HTTP and not a Python import: the external engine and
character-os are independent processes. The bridge is intentionally a
network call so each side keeps its own boundaries. In a shared
Docker network this can target a service DNS name (e.g.
``engine-shell:8000``); for local dev it targets a localhost port the
operator has chosen.

Latency budget: the sibling project's PA pipeline is GPT-5.2 function calling +
arbitrary tool dispatch; round-trip is typically 2-15 s for simple
queries, longer when the agent fires tools. We poll up to
``MAX_POLL_SECONDS`` then surface a timeout — the avatar should
narrate "the engine's still thinking" rather than waiting silently.

Configuration (env vars on the character-os Django process):

* ``UDB_PA_API_URL`` — base URL of the the sibling project backend (default
  ``http://localhost:8020`` — the alt port the sibling project is bound to when
  it shares the laptop with character-os :8000).
* ``UDB_PA_API_TOKEN`` — DRF auth token for the donkeyking user
  on the the sibling project side. No default — the tool returns a configured-but-
  unreachable error if missing rather than silently failing.

Cost: 5_000 micros ($0.005) — engine PA costs ~$0.0005 per simple
GPT-5.2 turn plus whatever tools it dispatches. The $0.005 estimate
covers the common case; outliers (long agent chains) cost more.
"""
from __future__ import annotations

import json
import logging
import time
import urllib.error
import urllib.request
from typing import Any

from ..engine_bridge import create_bridge_answer_asset, resolve_engine_connection
from . import register_tool


logger = logging.getLogger(__name__)


HTTP_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 1.5
MAX_POLL_SECONDS = 25


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
    name="consult_engine",
    # Kept under the 500-char media-engine Pydantic cap (see
    # recall_knowledge.py for the same constraint). The earlier
    # iteration tried a pre-narration cue ("Before invoking, voice
    # ...") but Runway's LLM ignored it in real-mode dogfood — same
    # class of bias documented at
    # ``feedback_runway_avatar_greeting_bias``. Descriptions reliably
    # gate WHEN tools fire, not WHAT the avatar says around them.
    # Narration of the answer is the SPA's job (BridgeAnswerPanel)
    # and, in v1, the operator's job (read panel + verbally hand
    # back to avatar). A v2 slice will pipe the answer through VO-arc
    # TTS for true mid-conversation narration.
    description=(
        "Asks the operator's deeper engine — Rigby on the sibling project — when "
        "a question concerns the operator's portfolio, current "
        "priorities, recent deliverables, live system state, or "
        "anything the workspace corpus is silent on. Pass the "
        "question as `question`. Do NOT invoke when the loaded "
        "document already answers, for greetings, or for Character-"
        "OS-only topics. The full answer renders on screen for the "
        "operator to read; the avatar's role is to invoke, not "
        "recite."
    ),
    cost_micros=5_000,
    workspace_scoped=True,
    is_async=False,
    tier_required="starter",
    dedup_enabled=True,
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Forward a question to the sibling project's PA and return the answer.

    Args:
        session: the active ``RealtimeSession`` (unused for routing;
            present so the dispatcher can match the tool signature
            and so future workspace gating can hang off it).
        args: ``{question: str}``. ``question`` required, non-empty.

    Returns:
        ``{event: 'engine_consulted', question, answer,
        conversation_id?, latency_ms, engine_url}`` on success;
        ``{event: 'engine_consulted', question, error, latency_ms,
        engine_url}`` on failure (HTTP, auth, timeout). Failures are
        returned (not raised) so the avatar can narrate degraded
        behaviour rather than dropping into a dispatcher error toast.

    Raises:
        ``ValueError`` when ``question`` is missing or blank — the
        dispatcher catches and records the audit row as FAILED.
        Errors talking to the sibling project are NOT raised (see Returns).
    """
    question = (args.get("question") or "").strip()
    if not question:
        raise ValueError("question is required")

    started = time.perf_counter()
    resolved = resolve_engine_connection(session.workspace)

    if resolved is None:
        return {
            "event": "engine_consulted",
            "question": question,
            "error": (
                "Engine bridge is not configured for this workspace "
                "(no EngineConnection row + no UDB_PA_* env fallback, "
                "or workspace tier is below Pro)."
            ),
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "engine_url": "",
        }

    base = resolved.url
    token = resolved.token

    # 1. POST the question, get a task_id.
    payload = {
        "message": question,
        "source": "character-os-consult-engine",
        "platform": "api",
        "context": {
            "source": "character-os-consult-engine",
            "spokesperson_id": str(getattr(session, "spokesperson_id", "") or ""),
            "workspace_id": str(getattr(session, "workspace_id", "") or ""),
        },
    }
    data, status = _http_request(f"{base}/api/pa/chat/", "POST", payload, token)

    if status != 200 or not data.get("success"):
        return {
            "event": "engine_consulted",
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
            "event": "engine_consulted",
            "question": question,
            "error": f"engine POST returned no task_id: {data}",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "engine_url": base,
        }

    # 2. Poll for the result.
    status_url = f"{base}/api/pa/chat/status/{task_id}/"
    while (time.perf_counter() - started) < MAX_POLL_SECONDS:
        time.sleep(POLL_INTERVAL_SECONDS)
        poll_data, poll_status = _http_request(status_url, "GET", None, token)
        if poll_status != 200:
            return {
                "event": "engine_consulted",
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
            answer = poll_data.get("content", "") or ""
            latency_ms = int((time.perf_counter() - started) * 1000)
            conversation_id = poll_data.get("conversation_id")
            intent = poll_data.get("intent")
            payload: dict[str, Any] = {
                "event": "engine_consulted",
                "question": question,
                "answer": answer,
                "conversation_id": conversation_id,
                "intent": intent,
                "tool_runs": poll_data.get("tool_runs", []),
                "latency_ms": latency_ms,
                "engine_url": base,
            }
            # S2887 C3 — persist non-empty answers as Asset(BRIDGE_ANSWER)
            # so the answer survives session end + becomes discoverable in
            # the workspace asset library. Empty answers (rare — usually
            # imply a degraded engine reply) skip persistence so we don't
            # accrete blank rows.
            if answer.strip():
                asset = create_bridge_answer_asset(
                    session,
                    tool_name="consult_engine",
                    question=question,
                    answer=answer,
                    engine_url=base,
                    cost_micros=5_000,
                    conversation_id=conversation_id,
                    latency_ms=latency_ms,
                    intent=intent,
                )
                payload["asset_id"] = str(asset.id)
            return payload
        if task_state == "failed":
            return {
                "event": "engine_consulted",
                "question": question,
                "error": (
                    f"engine task failed: "
                    f"{poll_data.get('error') or 'unknown failure'}"
                ),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "engine_url": base,
            }
        # 'processing' / 'pending' / 'queued' / anything else — keep polling

    return {
        "event": "engine_consulted",
        "question": question,
        "error": (
            f"engine timed out after {MAX_POLL_SECONDS}s — the engine may "
            "still be working; ask again in a moment."
        ),
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "engine_url": base,
    }
