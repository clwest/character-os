"""`consult_engine` — bridge tool to unified-donkey-betz Rigby (PA).

**SESSION 215 — soft-deprecated as a v1 dogfood seam.** The bridge
shape (Character OS spokesperson → HTTP → u-d-b PA → answer in SPA
panel) only solves a use case where the operator is using a
spokesperson as a face for their own engine. End customers of
Character OS don't have a u-d-b. The real product — "talk to Rigby
face-to-face" — belongs on u-d-b with a push-to-speak avatar (HeyGen
/ D-ID) where Rigby IS the LLM and the avatar lip-syncs Rigby's
existing PA responses. See
``docs/handoffs/SESSION_215_RIGBY_FACE_TO_FACE_PIVOT.md``.

This tool remains functional for operator-only dogfood. Do not
extend it (no new params, no new narration tricks). When end-customer
gating lands, gate via ``tier_required='agency'`` or a dedicated
operator-only flag.

The spokesperson invokes this when the operator asks a question that
the workspace knowledge corpus + recent conversations don't answer —
and the question is plausibly about the operator's broader portfolio,
live system state, current priorities, recent decisions, or anything
else only the engine's Rigby (the operator's full agentic PA) would
know.

Architecturally this is the first "engine bridge" tool: Character OS
realtime conversation → HTTP → u-d-b PA → answer text → back into the
realtime conversation. The engine stays put. Character OS becomes a
face for it without absorbing its agent/tool/spider universe.

Why HTTP and not a Python import: u-d-b and character-os are
independent Django projects with their own settings, models, and
data. The bridge is intentionally a network call so each side keeps
its boundaries. Both apps' data services share `fleet-net` (see
``/Users/donkeyking/development/infra/README.md``) so eventually
this can target `udb-shell:8000` directly; for now it targets a
localhost port the operator has chosen.

Latency budget: u-d-b's PA pipeline is GPT-5.2 function calling +
arbitrary tool dispatch; round-trip is typically 2-15 s for simple
queries, longer when the agent fires tools. We poll up to
``MAX_POLL_SECONDS`` then surface a timeout — the avatar should
narrate "the engine's still thinking" rather than waiting silently.

Configuration (env vars on the character-os Django process):

* ``UDB_PA_API_URL`` — base URL of the u-d-b backend (default
  ``http://localhost:8020`` — the alt port u-d-b is bound to when
  it shares the laptop with character-os :8000).
* ``UDB_PA_API_TOKEN`` — DRF auth token for the donkeyking user
  on the u-d-b side. No default — the tool returns a configured-but-
  unreachable error if missing rather than silently failing.

Cost: 5_000 micros ($0.005) — engine PA costs ~$0.0005 per simple
GPT-5.2 turn plus whatever tools it dispatches. The $0.005 estimate
covers the common case; outliers (long agent chains) cost more.
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


DEFAULT_BASE_URL = "http://localhost:8020"
HTTP_TIMEOUT_SECONDS = 10
POLL_INTERVAL_SECONDS = 1.5
MAX_POLL_SECONDS = 25


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
        "Asks the operator's deeper engine — Rigby on u-d-b — when "
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
    """Forward a question to u-d-b's PA and return the answer.

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
        Errors talking to u-d-b are NOT raised (see Returns).
    """
    question = (args.get("question") or "").strip()
    if not question:
        raise ValueError("question is required")

    base = _get_base_url()
    token = _get_token()
    started = time.perf_counter()

    if token is None:
        return {
            "event": "engine_consulted",
            "question": question,
            "error": (
                "UDB_PA_API_TOKEN is not configured on this character-os "
                "process; cannot reach the engine."
            ),
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "engine_url": base,
        }

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
            return {
                "event": "engine_consulted",
                "question": question,
                "answer": poll_data.get("content", ""),
                "conversation_id": poll_data.get("conversation_id"),
                "intent": poll_data.get("intent"),
                "tool_runs": poll_data.get("tool_runs", []),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "engine_url": base,
            }
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
