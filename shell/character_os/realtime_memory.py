"""Cross-session memory projection — prior transcripts → next session's grounding.

SESSION 148 / R6. The "returning operator" loop: when an
operator opens a new realtime session, the avatar should
know what was said last time. R5 persisted those
conversations as ``Asset(asset_type=TRANSCRIPT)`` rows
hanging off ``RealtimeSession.transcript_asset``; this
module reads them, summarizes via gpt-5-mini, and projects
the result into the Runway document body the next session
opens with (R4's ``compose_realtime_document``).

Three operating modes mirror K6 + K9:

* **Force-mock** (``REALTIME_MEMORY_FORCE_MOCK=1`` env or
  ``settings.REALTIME_MEMORY_FORCE_MOCK=True``): no OpenAI
  call. Deterministic stub that references the session count
  + transcript ids so tests can assert provenance without
  parsing real LLM output. Sixth force-mock flag in the
  family (``RUNWAY``, ``EMBEDDING``, ``RENDER_SCRIPT``,
  ``SERPER``, ``CONVERSATION_REPLY``, now this one).

* **No prior sessions / no OpenAI key / synthesis failure**:
  graceful degradation — return an empty result with
  ``body=""``. The composer treats empty memory as "skip the
  ``## Recent Conversations`` section entirely." Realtime
  sessions keep working; the avatar just opens cold.

* **Real mode**: one ``gpt-5-mini`` Responses-API call,
  ``reasoning_effort='low'``. Same model + shape as K6's
  ``script_synthesis._call_responses_api``. Locked to the
  Responses API (NOT chat-completions) per the project
  memory at
  ``~/.claude/projects/.../feedback_openai_gpt5_responses_api.md``.

Contract rule alignment (``REALTIME_AVATAR_V1.md``):

* Rule 1 — workspace anchor — preserved: the session query
  filters by ``spokesperson.workspace`` indirectly via
  ``spokesperson=...`` (the spokesperson FK carries the
  workspace; cross-workspace transcripts never appear).
* Rule 4 — Asset shape — preserved: reads the existing
  ``Asset(TRANSCRIPT)`` rows R5 already persists. No new
  persistence shape.
* Rule 9 — mock mode — preserved: force-mock flag honors the
  same env-or-settings pattern the rest of the realtime
  arc uses.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    from apps.spokespeople.models import Spokesperson

logger = logging.getLogger(__name__)


# SESSION 171 — promoted from gpt-5-mini to gpt-5 (full).
# Same rationale as K6 / K9 — generative summarization where
# capability quality matters and per-call cost stays tiny.
# REASONING_EFFORT stays 'low' — summarization is genuinely
# pattern-matching across transcripts.
MEMORY_MODEL = "gpt-5"
MAX_OUTPUT_TOKENS = 400
REASONING_EFFORT = "low"

# How many prior sessions to include. Three covers the
# returning-operator case without bloating the document
# budget; older sessions stay in the database but don't
# project forward.
DEFAULT_MAX_SESSIONS = 3

# How much of each transcript to feed the summarizer. Real
# transcripts can be thousands of characters; the model
# only needs the first chunk to summarize a 5-minute
# conversation. Caps cost without dropping context.
PER_TRANSCRIPT_CHAR_BUDGET = 4_000


@dataclass(slots=True)
class MemoryResult:
    """The composed memory projection.

    ``body`` is the ready-to-paste markdown — empty string
    when no memory is available (the composer treats empty
    as "skip the section"). ``session_ids`` is the
    provenance trail for the broker to log + for tests to
    assert against.
    """

    body: str = ""
    session_ids: list[str] = field(default_factory=list)
    used_synthesis: bool = False
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0


def _is_force_mock() -> bool:
    """Settings beats env. Same shape as the other five
    force-mock flags in the family."""
    settings_flag = getattr(settings, "REALTIME_MEMORY_FORCE_MOCK", None)
    if settings_flag is not None:
        return bool(settings_flag)
    env = os.environ.get("REALTIME_MEMORY_FORCE_MOCK", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def compose_session_memory(
    spokesperson: "Spokesperson",
    *,
    max_sessions: int = DEFAULT_MAX_SESSIONS,
) -> MemoryResult:
    """Build the memory projection for the next session.

    Queries prior ``RealtimeSession`` rows for this
    spokesperson that have a ``transcript_asset`` attached,
    newest first. Includes any status — ENDED sessions
    from the natural session-end flow (R5) and READY
    sessions from a mid-session ``attach_memory`` commit
    (R7.3). Summarizes up to ``max_sessions`` of them via
    ``gpt-5-mini`` Responses API. Returns a
    ``MemoryResult`` whose ``body`` is empty when there's
    nothing to project (composer skips the section) and
    populated markdown otherwise.

    R6.1 (SESSION 152) — dropped the ``status=ENDED``
    filter. Sessions with a transcript Asset are
    structurally evidence of a real conversation worth
    remembering, regardless of whether the operator
    formally ended the session before the next one
    opened. Edge case: a FAILED or crashed session that
    somehow has a transcript still surfaces — the
    operator-facing payoff is minor ("we started talking
    about X earlier today") and the architectural
    simplicity is worth it.

    Never raises. Failure paths log + return an empty
    result.
    """
    # Lazy import — avoids circular dep with apps.realtime
    # at module load (this lives in character_os/ which
    # other apps import).
    from apps.realtime.models import RealtimeSession

    sessions = list(
        RealtimeSession.objects.filter(
            spokesperson=spokesperson,
            transcript_asset__isnull=False,
        )
        .select_related("transcript_asset")
        .order_by("-ended_at")[:max_sessions]
    )

    if not sessions:
        return MemoryResult()

    session_ids = [str(s.id) for s in sessions]

    # Force-mock: skip the LLM call entirely. Deterministic
    # body that tests + dev workflows can rely on.
    if _is_force_mock():
        return MemoryResult(
            body=_mock_body(spokesperson, sessions),
            session_ids=session_ids,
            used_synthesis=True,  # mock counts as "synthesis ran"
            model=f"{MEMORY_MODEL} (mock)",
        )

    if not _has_openai_key():
        # Real mode requested but no key — degrade quietly.
        # Same shape as K6: log a warning, return empty.
        logger.warning(
            "compose_session_memory: prior sessions exist but "
            "OPENAI_API_KEY unset — degrading to empty memory "
            "(set REALTIME_MEMORY_FORCE_MOCK=1 for dev determinism)"
        )
        return MemoryResult(session_ids=session_ids)

    try:
        text, tokens_in, tokens_out = _call_responses_api(
            spokesperson, sessions,
        )
    except Exception:
        logger.exception(
            "compose_session_memory: OpenAI responses.create failed "
            "sp=%s sessions=%d — degrading to empty memory",
            spokesperson.pk, len(sessions),
        )
        return MemoryResult(session_ids=session_ids)

    body = text.strip()
    if not body:
        return MemoryResult(session_ids=session_ids)

    return MemoryResult(
        body=body,
        session_ids=session_ids,
        used_synthesis=True,
        model=MEMORY_MODEL,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
    )


# ---- LLM call --------------------------------------------------


def _call_responses_api(
    spokesperson: "Spokesperson",
    sessions: list,
) -> tuple[str, int, int]:
    """Single Responses-API call. Returns ``(text, tokens_in,
    tokens_out)``. Raises on API error — caller handles
    degradation."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    transcripts_block = "\n\n".join(
        _format_session(i + 1, session)
        for i, session in enumerate(sessions)
    )

    system = _system_prompt(spokesperson)
    user = (
        "Prior conversations between this operator and the "
        f"spokesperson, newest first:\n\n{transcripts_block}\n\n"
        "Write a brief memory block the spokesperson can use to "
        "open the next session warmly. Two short paragraphs max:\n"
        "  1. A 2-3 sentence summary of what's been discussed across "
        "these sessions (topics, decisions, open threads).\n"
        "  2. One natural opener cue (1 sentence) the spokesperson "
        "could use to acknowledge the prior conversation without "
        "sounding scripted.\n"
        "Use only what's in the transcripts above. Don't invent "
        "details. Keep it under 120 words total."
    )

    response = client.responses.create(
        model=MEMORY_MODEL,
        input=f"{system}\n\nUser: {user}",
        max_output_tokens=MAX_OUTPUT_TOKENS,
        reasoning={"effort": REASONING_EFFORT},
    )

    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


def _format_session(ordinal: int, session) -> str:
    """Format one session's transcript for the synthesizer.

    Caps per-transcript content at ``PER_TRANSCRIPT_CHAR_BUDGET``
    so a single long session doesn't blow the input budget.
    Includes the relative recency cue ("Most recent" /
    "Two sessions ago" / "Three sessions ago") so the model
    can phrase the opener naturally.
    """
    recency_label = {
        1: "Most recent session",
        2: "Two sessions ago",
        3: "Three sessions ago",
    }.get(ordinal, f"{ordinal} sessions ago")

    when = ""
    if session.ended_at:
        when = f" (ended {session.ended_at.date().isoformat()})"

    asset = session.transcript_asset
    content = (asset.inline_content or "").strip() if asset else ""
    if len(content) > PER_TRANSCRIPT_CHAR_BUDGET:
        content = content[:PER_TRANSCRIPT_CHAR_BUDGET].rstrip() + "\n…[truncated]"
    if not content:
        content = "(empty transcript)"

    return f"[{recency_label}{when}]\n{content}"


def _system_prompt(spokesperson: "Spokesperson") -> str:
    """Anchor the model to the spokesperson identity so the
    opener cue lands in the right voice. Same shape pattern
    as K6 + K9 system prompts."""
    tone = spokesperson.tone_archetype or "expert"
    name = spokesperson.name or "the spokesperson"
    return (
        f"You are summarizing prior conversations for {name}, an "
        f"on-camera spokesperson (tone archetype: {tone!r}). The "
        "summary you write will be injected into the spokesperson's "
        "next session document so they can open with continuity. "
        "Stay factual — pull only from the transcripts. Do not "
        "invent details. Keep the tone aligned with the spokesperson's "
        "archetype."
    )


# ---- mock path -----------------------------------------------


def _mock_body(spokesperson: "Spokesperson", sessions: list) -> str:
    """Deterministic body for force-mock + tests. Includes
    session ids in a parseable suffix so tests can assert
    provenance without parsing LLM output."""
    name = spokesperson.name or "the spokesperson"
    count = len(sessions)
    plural = "session" if count == 1 else "sessions"
    ids_suffix = ",".join(str(s.id) for s in sessions)
    return (
        f"Across the last {count} {plural}, the operator and "
        f"{name} continued an ongoing conversation. "
        f"{name} can open with: \"Good to see you again — picking "
        "up where we left off.\"\n\n"
        f"[memory: {count} prior {plural}: {ids_suffix}]"
    )
