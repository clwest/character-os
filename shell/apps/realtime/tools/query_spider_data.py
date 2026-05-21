"""`query_spider_data` — engine-bridge tool for live spider intelligence.

**SESSION 215 — soft-deprecated alongside ``consult_engine``** as
operator-only dogfood. The real product lives on u-d-b. See
``docs/handoffs/SESSION_215_RIGBY_FACE_TO_FACE_PIVOT.md``. Do not
extend.

Second engine-bridge realtime tool (companion to ``consult_engine``).
Where ``consult_engine`` asks u-d-b's PA an open-ended question,
this tool tells the PA to specifically pull from the spider network
on a named topic and summarise what was collected recently.

Why a dedicated tool: spider data is high-velocity, topical, and
time-sensitive — "what are the spiders saying about X this week"
is a different ask than "what does the engine know about X." The
LLM picks this one when the operator wants live intelligence, not
static knowledge.

Bridge architecture: same HTTP POST → u-d-b ``/api/pa/chat/`` →
poll → return. The PA dispatches internally to spider tools (e.g.
``spider_data_tool``, ``signal_aggregation_tool``).

Configuration: same env vars as ``consult_engine``
(``UDB_PA_API_URL``, ``UDB_PA_API_TOKEN``). Same network path.

Cost: 5_000 micros ($0.005) — PA call cost ~$0.0005 plus
dispatched spider tool calls. Spider lookups don't burn LLM
tokens (they're Postgres / Redis reads), so total is close to
consult_engine.
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
    name="query_spider_data",
    # Under 500-char cap. Pre-narration cue dropped — Runway's LLM
    # ignored it in real-mode dogfood. Narration of the answer
    # belongs to the SPA (BridgeAnswerPanel) + the operator in v1;
    # VO-arc TTS playback is the v2 path. Same constraint as
    # consult_engine.
    description=(
        "Asks the engine's spider network for live data on a topic "
        "— recent news, market signals, sentiment, trending content. "
        "Pass the topic as `topic`. Do NOT use for general portfolio "
        "questions (consult_engine handles those) or for facts the "
        "workspace corpus covers. The summary renders on screen for "
        "the operator to read; the avatar's role is to invoke, not "
        "recite."
    ),
    cost_micros=5_000,
    workspace_scoped=True,
    is_async=False,
    tier_required="starter",
    dedup_enabled=True,
)
def executor(session, args: dict[str, Any]) -> dict[str, Any]:
    """Forward a spider-data query to u-d-b's PA.

    Args:
        session: the active ``RealtimeSession`` (unused for routing).
        args: ``{topic: str}``. ``topic`` required.

    Returns:
        ``{event, topic, answer, conversation_id?, latency_ms,
        engine_url}`` on success, or
        ``{event, topic, error, latency_ms, engine_url}`` on
        failure. Errors are returned, not raised — same contract
        as consult_engine.

    Raises:
        ``ValueError`` when ``topic`` is missing or blank.
    """
    topic = (args.get("topic") or "").strip()
    if not topic:
        raise ValueError("topic is required")

    base = _get_base_url()
    token = _get_token()
    started = time.perf_counter()

    if token is None:
        return {
            "event": "spider_queried",
            "topic": topic,
            "error": "UDB_PA_API_TOKEN is not configured.",
            "latency_ms": int((time.perf_counter() - started) * 1000),
            "engine_url": base,
        }

    # Frame the question so the PA prefers spider / signal tools.
    framed_question = (
        f"Use the spider network and signal aggregation tools to find "
        f"recent intelligence on this topic: {topic}\n\n"
        f"Specifically, query recent SpiderData rows and any "
        f"SignalCluster patterns that touch this topic. Summarise "
        f"what the spiders have caught in the last 7 days. If there "
        f"is nothing relevant, say so plainly."
    )

    payload = {
        "message": framed_question,
        "source": "character-os-query-spider-data",
        "platform": "api",
        "context": {
            "source": "character-os-query-spider-data",
            "topic": topic,
            "spokesperson_id": str(getattr(session, "spokesperson_id", "") or ""),
            "workspace_id": str(getattr(session, "workspace_id", "") or ""),
        },
    }
    data, status = _http_request(f"{base}/api/pa/chat/", "POST", payload, token)

    if status != 200 or not data.get("success"):
        return {
            "event": "spider_queried",
            "topic": topic,
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
            "event": "spider_queried",
            "topic": topic,
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
                "event": "spider_queried",
                "topic": topic,
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
                "event": "spider_queried",
                "topic": topic,
                "answer": poll_data.get("content", ""),
                "conversation_id": poll_data.get("conversation_id"),
                "tool_runs": poll_data.get("tool_runs", []),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "engine_url": base,
            }
        if task_state == "failed":
            return {
                "event": "spider_queried",
                "topic": topic,
                "error": (
                    f"engine task failed: "
                    f"{poll_data.get('error') or 'unknown failure'}"
                ),
                "latency_ms": int((time.perf_counter() - started) * 1000),
                "engine_url": base,
            }

    return {
        "event": "spider_queried",
        "topic": topic,
        "error": f"engine timed out after {MAX_POLL_SECONDS}s.",
        "latency_ms": int((time.perf_counter() - started) * 1000),
        "engine_url": base,
    }
