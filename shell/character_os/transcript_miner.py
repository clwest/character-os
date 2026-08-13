"""LLM-driven transcript highlight selection.

B-arc slice B1.1 (SESSION 202). Reads an
``Asset(asset_type=TRANSCRIPT)`` row's ``inline_content`` body
and returns 3-5 shareable highlights via one ``gpt-5-mini``
Responses-API call. Each highlight carries the text, the
character offsets into the source body, and the LLM's
reasoning so the operator can verify the pick in the SPA.

Three operating modes mirror ``character_os.realtime_memory``
+ ``character_os.script_synthesis``:

* **Force-mock** (``TRANSCRIPT_MINER_FORCE_MOCK=1`` env or
  ``settings.TRANSCRIPT_MINER_FORCE_MOCK=True``): no OpenAI
  call. Deterministic stub that picks the longest assistant
  turns by simple length heuristic + records placeholder
  reasoning so tests can assert provenance without LLM
  output. Seventh force-mock flag in the family
  (``RUNWAY``, ``EMBEDDING``, ``RENDER_SCRIPT``, ``SERPER``,
  ``CONVERSATION_REPLY``, ``REALTIME_MEMORY``, now this one).

* **No transcript content / no OpenAI key / synthesis
  failure**: graceful degradation — return an empty result
  (``picks=[]``). The mine-endpoint caller treats empty as
  "nothing to mine" and surfaces that to the operator
  (no row persistence; no spend). Same shape as
  ``realtime_memory.compose_session_memory``.

* **Real mode**: one ``gpt-5-mini`` Responses-API call,
  ``reasoning_effort='low'``. Structured output via
  ``response_format={"type": "json_object"}`` — the prompt
  enforces the JSON shape; the parser validates against the
  source body and discards picks whose declared offsets
  don't match the declared text (contract rule 3 — LLM
  selection must be auditable).

Contract rule alignment (``TRANSCRIPT_MINER_V1.md``):

* Rule 1 — source-only — the helper accepts a single
  in-memory body string; no external ingestion paths.
* Rule 3 — auditable — every returned ``HighlightCandidate``
  carries ``char_start``, ``char_end``, and
  ``llm_reasoning``; mismatched offsets are dropped at
  parse time, not persisted.
* Rule 8 — 280-char cap — picks exceeding the cap are
  trimmed at parse time (truncated to a sentence boundary
  ≤ 280 chars), not rejected outright. The LLM is told the
  cap in the prompt; defense in depth at parse.
"""
from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from django.conf import settings

if TYPE_CHECKING:
    pass

logger = logging.getLogger(__name__)


# Default model: gpt-5-mini per CONTENT_FORMAT_BACKLOG.md §B-1
# cost estimate ("~$0.001 per mining call"). Same Responses-API
# shape as ``realtime_memory.py`` + ``script_synthesis.py``.
# Promotion to gpt-5 (full) would be a SESSION 171-style call
# if dogfood shows quality issues.
MINER_MODEL = "gpt-5-mini"
MAX_OUTPUT_TOKENS = 2000
REASONING_EFFORT = "low"

# Per the scope-lock Q-b-1: default 5 highlights,
# operator-overridable 1-10.
DEFAULT_TARGET_COUNT = 5
MIN_TARGET_COUNT = 1
MAX_TARGET_COUNT = 10

# Per the scope-lock rule 8: 280-char hard cap per highlight.
# Maps to ~25-30s of speech at typical avatar pace.
MAX_HIGHLIGHT_CHARS = 280


@dataclass(frozen=True)
class HighlightCandidate:
    """One LLM-picked highlight with audit metadata.

    Frozen so callers can't mutate after the parser has
    validated the offsets against the source body.
    """

    text: str
    char_start: int
    char_end: int
    llm_reasoning: str

    @property
    def length(self) -> int:
        return self.char_end - self.char_start


@dataclass
class MiningResult:
    """Aggregate result of one mining call.

    Empty ``picks`` indicates either no source content,
    missing API key, LLM failure, or all picks failed
    validation. Callers should treat empty as "nothing to
    persist" — no row creation, no LLM cost accrual beyond
    what was already spent.
    """

    picks: list[HighlightCandidate] = field(default_factory=list)
    used_synthesis: bool = False
    model: str = ""
    tokens_input: int = 0
    tokens_output: int = 0


def _is_force_mock() -> bool:
    """Settings beats env. Same shape as the other six
    force-mock flags in the family."""
    settings_flag = getattr(settings, "TRANSCRIPT_MINER_FORCE_MOCK", None)
    if settings_flag is not None:
        return bool(settings_flag)
    env = os.environ.get("TRANSCRIPT_MINER_FORCE_MOCK", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _has_openai_key() -> bool:
    return bool(os.environ.get("OPENAI_API_KEY", "").strip())


def select_transcript_highlights(
    transcript_body: str,
    *,
    target_count: int = DEFAULT_TARGET_COUNT,
    max_chars: int = MAX_HIGHLIGHT_CHARS,
) -> MiningResult:
    """Pick ``target_count`` highlights from ``transcript_body``.

    Args:
        transcript_body: The transcript text. Typically the
            ``Asset(TRANSCRIPT).inline_content`` field from a
            realtime session capture (R5).
        target_count: How many highlights to ask the LLM for.
            Clamped to ``[MIN_TARGET_COUNT, MAX_TARGET_COUNT]``.
            Default 5 per scope-lock Q-b-1.
        max_chars: Per-highlight character cap. Default 280
            per rule 8.

    Returns:
        ``MiningResult`` whose ``picks`` is empty on any
        degraded path (no content, no key, LLM error,
        offsets unverifiable) and populated otherwise.

    Never raises. Failure paths log + return an empty result.
    """
    body = (transcript_body or "").strip()
    if not body:
        return MiningResult()

    target_count = max(MIN_TARGET_COUNT, min(MAX_TARGET_COUNT, target_count))

    if _is_force_mock():
        picks = _mock_picks(body, target_count, max_chars)
        return MiningResult(
            picks=picks,
            used_synthesis=True,  # mock counts as "synthesis ran"
            model=f"{MINER_MODEL} (mock)",
        )

    if not _has_openai_key():
        logger.warning(
            "select_transcript_highlights: transcript has content but "
            "OPENAI_API_KEY unset — degrading to empty result "
            "(set TRANSCRIPT_MINER_FORCE_MOCK=1 for dev determinism)"
        )
        return MiningResult()

    try:
        raw_json, tokens_in, tokens_out = _call_responses_api(
            body, target_count, max_chars,
        )
    except Exception:
        logger.exception(
            "select_transcript_highlights: OpenAI responses.create "
            "failed — degrading to empty result"
        )
        return MiningResult()

    picks = _parse_and_validate(raw_json, body, max_chars)
    return MiningResult(
        picks=picks,
        used_synthesis=True,
        model=MINER_MODEL,
        tokens_input=tokens_in,
        tokens_output=tokens_out,
    )


# ---- LLM call --------------------------------------------------


def _call_responses_api(
    transcript_body: str,
    target_count: int,
    max_chars: int,
) -> tuple[str, int, int]:
    """One Responses-API call. Returns ``(raw_text, tokens_in,
    tokens_out)``. Raises on API error — caller degrades."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

    system = (
        "You select shareable highlights from a realtime "
        "conversation transcript. Your job is to find the most "
        "punchy, quotable moments — phrases the operator could "
        "share as standalone social clips. Avoid filler, avoid "
        "context-dependent statements (\"as I said earlier\"), "
        "prefer self-contained insights, declarations, or vivid "
        "moments."
    )

    user = (
        f"Transcript:\n```\n{transcript_body}\n```\n\n"
        f"Return UP TO {target_count} highlights as JSON in "
        "this shape:\n"
        "{\n"
        "  \"highlights\": [\n"
        "    {\n"
        "      \"text\": \"the exact substring copied verbatim "
        "from the transcript\",\n"
        "      \"reasoning\": \"1-2 sentences on why this is "
        "shareable\"\n"
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Rules:\n"
        f"* Each text MUST be ≤ {max_chars} characters.\n"
        "* Each text MUST be copied VERBATIM from the "
        "transcript — same words, same punctuation, same "
        "casing. The parser will reject any text that isn't "
        "found as a substring of the transcript.\n"
        "* Pick from the assistant's lines (lines beginning "
        "with \"Assistant:\") — those are the spokesperson's "
        "words, which is what the re-bake renders. Do NOT "
        "include the \"Assistant: \" prefix in the text "
        "field — just the words after it.\n"
        f"* If the transcript doesn't have {target_count} "
        "distinct shareable moments, return fewer — don't "
        "pad with weak picks.\n"
        "Output ONLY the JSON object, no prose around it."
    )

    response = client.responses.create(
        model=MINER_MODEL,
        input=f"{system}\n\nUser: {user}",
        max_output_tokens=MAX_OUTPUT_TOKENS,
        reasoning={"effort": REASONING_EFFORT},
        text={"format": {"type": "json_object"}},
    )

    text = response.output_text or ""
    usage = getattr(response, "usage", None)
    tokens_in = getattr(usage, "input_tokens", 0) or 0
    tokens_out = getattr(usage, "output_tokens", 0) or 0
    return text, tokens_in, tokens_out


# ---- Parser + validator ----------------------------------------


def _parse_and_validate(
    raw_json: str, source_body: str, max_chars: int,
) -> list[HighlightCandidate]:
    """Parse LLM JSON; locate each pick's offsets via
    ``source_body.find(text)``; drop picks whose text isn't a
    verbatim substring of the source.

    **SESSION 202 B1.7 post-close fix**: the LLM no longer
    returns offsets. Asking gpt-5-mini to compute character
    offsets in addition to picking quotes burned the entire
    output token budget on reasoning (1984 of 2000 tokens
    consumed before any visible output — the recurring
    "gpt-5 reasoning eats output budget silently" calibration
    pattern). Pure-text picks + parser-side ``find()`` is
    much cheaper for the model and structurally equivalent
    for rule 3 audit purposes — the operator can verify the
    pick by char-range highlight either way.

    Rule 3 still in action: a pick whose text isn't found
    verbatim in ``source_body`` is LLM-hallucinated and gets
    dropped (logged at DEBUG).

    Rule 8 in action: picks exceeding ``max_chars`` are
    truncated to a sentence boundary ≤ ``max_chars``; if no
    sentence boundary fits, hard-truncated. The trimmed text
    is re-located in the body so offsets stay accurate.

    Multiple-occurrence handling: if the LLM returns a quote
    that appears more than once in ``source_body`` (e.g. a
    short stock phrase), the parser takes the FIRST
    occurrence. v1 simplification; the operator can verify
    via hover-highlight which range was picked.
    """
    if not raw_json or not raw_json.strip():
        return []
    try:
        parsed = json.loads(raw_json)
    except json.JSONDecodeError:
        logger.warning(
            "select_transcript_highlights: LLM returned non-JSON "
            "output (first 120 chars: %r)",
            raw_json[:120],
        )
        return []

    raw_picks = parsed.get("highlights", []) if isinstance(parsed, dict) else []
    if not isinstance(raw_picks, list):
        return []

    out: list[HighlightCandidate] = []
    for entry in raw_picks:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text")
        reasoning = entry.get("reasoning") or ""

        if not isinstance(text, str) or not text.strip():
            continue

        # Locate the verbatim quote in the source body. If the
        # LLM returned a paraphrase / hallucination instead of
        # a verbatim copy, ``find()`` returns -1 and we drop.
        text = text.strip()
        cs = source_body.find(text)
        if cs < 0:
            logger.debug(
                "transcript_miner: dropped pick — text not found "
                "in source: declared=%r", text[:80],
            )
            continue
        ce = cs + len(text)

        if len(text) > max_chars:
            text, ce = _trim_to_max(text, cs, max_chars)

        out.append(HighlightCandidate(
            text=text,
            char_start=cs,
            char_end=ce,
            llm_reasoning=str(reasoning),
        ))
    return out


def _trim_to_max(text: str, char_start: int, max_chars: int) -> tuple[str, int]:
    """Trim ``text`` to at most ``max_chars`` chars, preferring
    a sentence boundary (``.`` / ``!`` / ``?``) within the
    last 60 chars of the cap. Returns ``(trimmed_text,
    new_char_end)`` so audit math stays consistent."""
    if len(text) <= max_chars:
        return text, char_start + len(text)
    candidate = text[:max_chars]
    # Look for last sentence terminator in the trailing region
    # so we don't lop off mid-word more than necessary.
    best_idx = max(
        candidate.rfind(". "),
        candidate.rfind("! "),
        candidate.rfind("? "),
    )
    if best_idx >= max_chars - 60:
        # Keep through the terminator + space.
        trimmed = candidate[: best_idx + 1].rstrip()
    else:
        # No nice boundary — hard-trim at the cap.
        trimmed = candidate.rstrip()
    return trimmed, char_start + len(trimmed)


# ---- Mock branch -----------------------------------------------


def _mock_picks(
    body: str, target_count: int, max_chars: int,
) -> list[HighlightCandidate]:
    """Deterministic stub for ``TRANSCRIPT_MINER_FORCE_MOCK``.

    Picks the longest "Assistant:" lines (or just the longest
    lines overall if no Assistant prefix exists), since that
    matches what the real LLM is supposed to do (favor
    self-contained spokesperson statements). Caps each pick
    at ``max_chars`` via ``_trim_to_max`` so the mock output
    obeys rule 8 the same way the real path does.

    Reasoning string is a placeholder that names the mock —
    tests assert this exact string to confirm the mock path
    fired (no leaks of real LLM output into mock-mode test
    expectations).
    """
    assistant_prefix = "Assistant:"
    candidates: list[tuple[int, int, str]] = []  # (start, end, text)

    pos = 0
    for line in body.splitlines(keepends=True):
        bare = line.rstrip("\n").rstrip()
        # Strip the "Assistant:" prefix from the matchable
        # substring while keeping the position math anchored
        # to the original body.
        if bare.startswith(assistant_prefix):
            inner_start = pos + len(assistant_prefix)
            inner_end = pos + len(bare)
            inner = body[inner_start:inner_end].strip()
            if inner:
                # Re-anchor start to the first non-space char
                # after "Assistant:" so the persisted text
                # matches the slice.
                offset = body[inner_start:inner_end].find(inner)
                cs = inner_start + offset
                ce = cs + len(inner)
                candidates.append((cs, ce, inner))
        pos += len(line)

    if not candidates:
        # Fallback — pick longest lines overall.
        pos = 0
        for line in body.splitlines(keepends=True):
            bare = line.rstrip("\n").rstrip()
            if bare:
                candidates.append((pos, pos + len(bare), bare))
            pos += len(line)

    # Sort by length descending so we pick the longest
    # self-contained statements first.
    candidates.sort(key=lambda c: len(c[2]), reverse=True)

    picks: list[HighlightCandidate] = []
    for cs, ce, text in candidates[:target_count]:
        if len(text) > max_chars:
            text, ce = _trim_to_max(text, cs, max_chars)
        picks.append(HighlightCandidate(
            text=text,
            char_start=cs,
            char_end=ce,
            llm_reasoning="mock pick (TRANSCRIPT_MINER_FORCE_MOCK)",
        ))
    return picks
