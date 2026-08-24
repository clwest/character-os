"""Story-direction suggestion service (SESSION 280 v1).

Given a Universe with at least one existing Episode, generate a
small number of possible next-Episode directions the operator MAY
choose to pursue. Ephemeral: nothing is persisted; the operator is
authoritative.

Lifts the Q280.5-1 probe logic
(``scripts/session280_q280_5_1_suggestion_probe.py``) into a
production service. Reuses the same LLM call shape as
``character_os.dialogue_synthesis._call_dialogue_api``.

See docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md §56-§68
for the design; §69+ for the implementation slice.

Isolation:

* Read-only over existing substrate. No DB writes.
* Cache is Redis-backed via Django's default cache alias with a
  short TTL. Cache key includes the Universe id + latest Episode
  activity so a new Episode invalidates naturally when its
  ``created_at`` is fresher than the cached snapshot.
* The prompt language avoids implementation vocabulary (no
  "memory kind", "retrieval", "PROMISE", "DIALOGUE_CALLBACK");
  the LLM is asked to notice possibilities from prior events.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from django.core.cache import cache

if TYPE_CHECKING:
    from apps.universe.models import Universe


logger = logging.getLogger(__name__)


# Same model + reasoning/format shape as
# character_os.dialogue_synthesis._call_dialogue_api.
_SUGGESTION_MODEL = "gpt-5.6-terra"
_MAX_OUTPUT_TOKENS = 1200
_REASONING_EFFORT = "low"

# Server-side memoization horizon. Passive page loads within the
# same 10-minute window re-use the same suggestion set. Explicit
# refresh (``use_cache=False``) always bypasses. Any new Episode /
# Memory activity naturally invalidates because ``latest_*_at``
# rolls into the cache key.
_CACHE_TTL_SECONDS = 600

_DEFAULT_N = 3
_MIN_N = 1
_MAX_N = 5


class NextEpisodeSuggestionError(RuntimeError):
    """Base class for service-layer errors."""


class NextEpisodeSuggestionUpstreamError(NextEpisodeSuggestionError):
    """LLM provider was unreachable or returned unusable output."""


@dataclass(frozen=True)
class _SubstrateSnapshot:
    """Read-only view of what the LLM will see for one Universe."""

    universe_id: str
    universe_name: str
    universe_brief: str
    episodes: list[dict]
    memories: list[dict]
    cast: list[dict]
    latest_episode_at: str
    latest_memory_at: str


def _snapshot(universe: "Universe") -> _SubstrateSnapshot:
    """Read-only snapshot of the Universe's story substrate.

    Every read is scoped to the Universe. Archived Episodes are
    excluded (they wouldn't be plausible-next material). Memory
    rows must be REMEMBERED and not-yet-archived; the same filter
    ``retrieve_universe_memory`` uses.
    """
    from apps.compositions.models import Composition  # local import — Django app boot
    from apps.memory.models import (  # local import — same
        NarrativeMemory,
        NarrativeMemoryStatus,
    )
    from apps.spokespeople.models import Teammate  # local import — same
    from apps.universe.models import Episode  # local import — same

    episodes_qs = (
        Episode.objects
        .filter(universe=universe, archived_at__isnull=True)
        .order_by("created_at")
    )
    episodes = list(episodes_qs)

    memories_qs = (
        NarrativeMemory.objects
        .filter(
            universe=universe,
            status=NarrativeMemoryStatus.REMEMBERED,
            archived_at__isnull=True,
        )
        .order_by("created_at")
    )
    memories = list(memories_qs)

    # Reference-count each memory across attached Compositions.
    # Reused straight from the Q280.5-1 probe.
    ref_counter: Counter = Counter()
    if memories:
        target_ids = {str(m.id) for m in memories}
        for c in (
            Composition.objects
            .filter(workspace_id=universe.workspace_id)
            .exclude(episode__isnull=True)
            .only("id", "memory_ids", "episode_id")
        ):
            for mid in c.memory_ids or []:
                if mid in target_ids:
                    ref_counter[mid] += 1

    cast = list(Teammate.objects.filter(universe=universe))

    latest_episode_at = (
        max((e.created_at for e in episodes), default=None)
    )
    latest_memory_at = (
        max((m.created_at for m in memories), default=None)
    )

    return _SubstrateSnapshot(
        universe_id=str(universe.id),
        universe_name=universe.name or "",
        universe_brief=(universe.brief or "").strip(),
        episodes=[
            {
                "id": str(e.id),
                "title": e.title or "",
                "operator_topic": e.operator_topic or "",
                "created_at": e.created_at.isoformat(),
            }
            for e in episodes
        ],
        memories=[
            {
                "id": str(m.id),
                "kind": m.kind,
                "weight": m.weight,
                "witnessed_by": sorted(
                    [t.name for t in m.witnessed_by.all()]
                ),
                "body": (m.body or "").strip(),
                "created_at": m.created_at.isoformat(),
                "referenced_count": ref_counter.get(str(m.id), 0),
            }
            for m in memories
        ],
        cast=[
            {
                "id": str(t.id),
                "name": t.name,
                "tone": t.tone_archetype or "",
                "personality_prefix": (t.personality or "")[:220],
            }
            for t in cast
        ],
        latest_episode_at=(
            latest_episode_at.isoformat() if latest_episode_at else ""
        ),
        latest_memory_at=(
            latest_memory_at.isoformat() if latest_memory_at else ""
        ),
    )


# System prompt — no implementation vocabulary. Talks about
# "story", "characters", "past events", "possible directions".
_SYSTEM_PROMPT = (
    "You are a story-development assistant. Your job is to notice "
    "possible next-Episode directions the operator MAY choose.\n\n"
    "GUARDRAILS:\n"
    "- These are POSSIBILITIES, never obligations.\n"
    "- The operator remains the director. Never imply the next "
    "Episode must continue any specific thread.\n"
    "- Do not decide for the operator. Do not commit to a linear "
    "story arc.\n"
    "- Do not describe implementation, do not say 'the system "
    "will'; describe possible in-world Episode premises the "
    "operator could pick up.\n"
    "- Where possible, pick up unresolved threads visible in past "
    "events. At least one suggestion may be a new direction if it "
    "fits the world.\n"
    "- Keep each suggestion short enough to work as an Episode "
    "topic without operator rewriting.\n\n"
    "OUTPUT FORMAT: JSON object with a single key 'suggestions' "
    "whose value is a list of exactly N strings. Each string is "
    "ONE sentence describing a possible next Episode. Do NOT "
    "number them."
)


def _build_task_message(snap: _SubstrateSnapshot, *, n: int) -> str:
    lines: list[str] = []
    lines.append(f"UNIVERSE: {snap.universe_name}")
    if snap.universe_brief:
        lines.append("")
        lines.append("WORLD BRIEF:")
        lines.append(snap.universe_brief)

    lines.append("")
    lines.append("CAST:")
    for t in snap.cast:
        pieces = []
        if t["tone"]:
            pieces.append(f"tone={t['tone']}")
        pers = t["personality_prefix"].strip()
        if pers:
            pieces.append(f"personality={pers!r}")
        detail = "; ".join(pieces) if pieces else "(no voice detail)"
        lines.append(f"- {t['name']}: {detail}")

    lines.append("")
    if snap.episodes:
        lines.append("EPISODES SO FAR (earliest first):")
        for i, e in enumerate(snap.episodes, 1):
            topic = (e["operator_topic"] or "").strip().replace("\n", " ")
            lines.append(f"{i:>3}. {e['title']!r}")
            if topic and topic != e["title"]:
                lines.append(f"     topic: {topic}")
    else:
        lines.append("EPISODES SO FAR: (none)")

    lines.append("")
    if snap.memories:
        lines.append(
            "PAST EVENTS THE STORY HAS RECORDED "
            "(operator-promoted; the durable record of what has "
            "happened in this world):"
        )
        for m in snap.memories:
            witnesses = ",".join(m["witnessed_by"]) or "whole-cast"
            body = (m["body"] or "").strip().replace("\n", " ")
            lines.append(
                f"- (kind={m['kind']}, weight={m['weight']}, "
                f"witnesses={witnesses}): {body}"
            )
    else:
        lines.append("PAST EVENTS: (none recorded yet)")

    lines.append("")
    lines.append(
        f"TASK: Suggest {n} possible next Episode directions for "
        "this Universe, one sentence each. These are "
        "possibilities the operator may pick, ignore, or override. "
        "Where possible, pick up unresolved threads from prior "
        "Episodes or past events. Keep each short enough to work "
        "as an Episode topic without rewriting."
    )
    return "\n".join(lines)


def _call_openai(*, system_prompt: str, task_message: str) -> tuple[str, int, int]:
    """Single Responses-API call with JSON-object output.

    Same shape as
    ``character_os.dialogue_synthesis._call_dialogue_api``.
    """
    from openai import OpenAI

    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise NextEpisodeSuggestionUpstreamError(
            "OPENAI_API_KEY is not configured"
        )

    client = OpenAI(api_key=api_key)
    try:
        response = client.responses.create(
            model=_SUGGESTION_MODEL,
            input=f"{system_prompt}\n\nUser: {task_message}",
            max_output_tokens=_MAX_OUTPUT_TOKENS,
            reasoning={"effort": _REASONING_EFFORT},
            text={"format": {"type": "json_object"}},
        )
    except Exception as exc:
        raise NextEpisodeSuggestionUpstreamError(
            f"LLM provider call failed: {exc}"
        ) from exc

    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


def _parse_suggestions(raw: str, *, n: int) -> list[str]:
    """Robust parse — accept ``suggestions: [str, ...]`` OR
    ``suggestions: [{"text": ...}, ...]`` shapes. Drop empty
    entries. Trim to at most ``n``. Never pad."""
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise NextEpisodeSuggestionUpstreamError(
            f"LLM returned invalid JSON: {exc}"
        ) from exc

    raw_list = payload.get("suggestions") if isinstance(payload, dict) else None
    if not isinstance(raw_list, list):
        raise NextEpisodeSuggestionUpstreamError(
            "LLM response missing 'suggestions' array"
        )

    out: list[str] = []
    for s in raw_list:
        if isinstance(s, str):
            text = s.strip()
        elif isinstance(s, dict):
            text = str(s.get("text") or s.get("suggestion") or "").strip()
        else:
            text = str(s).strip()
        if text:
            out.append(text)
        if len(out) >= n:
            break
    return out


def _cache_key(snap: _SubstrateSnapshot, *, n: int) -> str:
    payload = (
        f"{snap.universe_id}|{snap.latest_episode_at}|"
        f"{snap.latest_memory_at}|{n}"
    )
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]
    return f"next_ep_sugg:{snap.universe_id}:{digest}"


def suggest_next_episodes(
    universe: "Universe",
    *,
    n: int = _DEFAULT_N,
    use_cache: bool = True,
) -> dict[str, Any]:
    """Return a payload of possible next-Episode direction suggestions.

    Returns a dict with keys:

    * ``suggestions``: ``list[dict]`` — each ``{"text": str}``.
      **May be shorter than n; may be empty.** Empty when the
      Universe has zero eligible Episodes (nothing to build on).
    * ``substrate_summary``: ``dict`` — counts used for prompting.
    * ``generated_at``: ISO timestamp.
    * ``model``: LLM model identifier used.
    * ``cache``: ``{"hit": bool, "ttl_seconds": int}``.

    Raises ``NextEpisodeSuggestionUpstreamError`` on provider
    error / invalid response — callers should map to HTTP 502.

    Does NOT raise on empty-substrate — returns
    ``suggestions=[]`` so the SPA can hide the surface without
    error-state noise.
    """
    if n < _MIN_N or n > _MAX_N:
        n = _DEFAULT_N

    snap = _snapshot(universe)

    substrate_summary = {
        "episodes_used": len(snap.episodes),
        "memories_used": len(snap.memories),
        "cast_count": len(snap.cast),
    }

    # Empty-Universe short-circuit — no LLM call, no error.
    if not snap.episodes:
        return {
            "suggestions": [],
            "substrate_summary": substrate_summary,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "model": _SUGGESTION_MODEL,
            "cache": {"hit": False, "ttl_seconds": _CACHE_TTL_SECONDS},
        }

    key = _cache_key(snap, n=n)

    if use_cache:
        cached = cache.get(key)
        if cached is not None:
            cached_copy = dict(cached)
            cached_copy["cache"] = {
                "hit": True,
                "ttl_seconds": _CACHE_TTL_SECONDS,
            }
            return cached_copy

    task_message = _build_task_message(snap, n=n)
    raw, tokens_in, tokens_out = _call_openai(
        system_prompt=_SYSTEM_PROMPT,
        task_message=task_message,
    )
    suggestions = _parse_suggestions(raw, n=n)

    payload = {
        "suggestions": [{"text": s} for s in suggestions],
        "substrate_summary": substrate_summary,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "model": _SUGGESTION_MODEL,
        "cache": {"hit": False, "ttl_seconds": _CACHE_TTL_SECONDS},
        "tokens_input": tokens_in,
        "tokens_output": tokens_out,
    }

    # Cache the OUTGOING payload with cache={"hit": False, ...}
    # so a subsequent read can flip hit=True without mutating the
    # original stored copy.
    if use_cache and suggestions:
        cache.set(key, payload, timeout=_CACHE_TTL_SECONDS)

    return payload
