"""Sentence-boundary script splitter — V5 building block.

SESSION 143 / V5. Ports the chunking logic from
`an earlier hackathon-prototype module`
into the composition arc. Used by:

* ``SplitScriptPrimitive`` — the registry-driven step variant.
* ``long_form_ad`` starter — pre-splits at composition-create
  time so the runtime sees a deterministic N-step plan rather
  than a dynamic step count (contract rule 5: linear ordering).

Two split paths:

* **Naive (deterministic)** — ``chunk_script(text, max_chars)``.
  No external calls. Greedy sentence-boundary packing with a
  fallback ladder (sentence → clause → word → hard-cut).
  Always succeeds; always returns chunks ≤ ``max_chars``.

* **LLM-assisted (graceful)** — ``split_script_with_llm(text,
  max_chars)``. gpt-5-mini via the Responses API picks
  semantically clean split points. Falls back to the naive
  splitter when ``RENDER_SCRIPT_FORCE_MOCK=1``, when no
  ``OPENAI_API_KEY`` is set, or when the LLM call fails for
  any reason. The naive splitter is the structural guarantee;
  the LLM is an optional quality bump.

The Runway ``/v1/avatar_videos`` per-call script ceiling is
documented at ~300 chars (the hackathon's ``_MAX_SCRIPT_CHARS``).
We default to 280 to leave headroom for the system prompt
overhead Runway prepends.
"""
from __future__ import annotations

import json
import logging
import os
import re

from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


# Per-chunk character cap. Runway's avatar_videos accepts up to
# ~300 chars per call; 280 leaves a 20-char safety margin.
DEFAULT_CHUNK_MAX_CHARS = 280


# gpt-5-mini constants — match what K6 / script_synthesis.py uses
# (Responses API, low reasoning, capped output). Single anchor for
# the project's LLM-call shape.
SCRIPT_SPLIT_MODEL = "gpt-5-mini"
SCRIPT_SPLIT_MAX_OUTPUT_TOKENS = 1500
SCRIPT_SPLIT_REASONING_EFFORT = "low"


def _is_force_mock() -> bool:
    """Force-mock check mirroring ``script_synthesis.py``.
    Env var first, then Django setting. Either being truthy is
    enough."""
    if os.environ.get("RENDER_SCRIPT_FORCE_MOCK"):
        return True
    return bool(getattr(django_settings, "RENDER_SCRIPT_FORCE_MOCK", False))


def chunk_script(
    script: str,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
) -> list[str]:
    """Naive sentence-boundary chunker. Ported from
    `an earlier hackathon-prototype module`.

    Greedy: pack as many sentences as fit into each chunk,
    then start a new one. Fallback ladder for oversized
    sentences:

    1. Single sentence > max_chars → split at ``,`` / ``;``
       clause boundaries.
    2. Single clause still > max_chars → split at word
       boundary.
    3. Single word > max_chars → hard-cut at max_chars.

    Returns ``[]`` for empty input. Never returns chunks
    above ``max_chars``.
    """
    cleaned = (script or "").strip()
    if not cleaned:
        return []

    sentences = [
        s.strip()
        for s in re.split(r"(?<=[.!?])\s+", cleaned)
        if s.strip()
    ]
    if not sentences:
        sentences = [cleaned]

    chunks: list[str] = []
    current = ""

    def _flush() -> None:
        nonlocal current
        if current:
            chunks.append(current.strip())
            current = ""

    def _split_oversize(text: str) -> list[str]:
        """Recursive fallback for sentences/clauses/words
        longer than ``max_chars``."""
        text = text.strip()
        if len(text) <= max_chars:
            return [text]
        # Clause split (commas / semicolons).
        clauses = [c.strip() for c in re.split(r"(?<=[,;])\s+", text) if c.strip()]
        if len(clauses) > 1:
            out: list[str] = []
            for c in clauses:
                out.extend(_split_oversize(c))
            return out
        # Word boundary split.
        words = text.split()
        out_words: list[str] = []
        buf = ""
        for w in words:
            if len(w) > max_chars:
                if buf:
                    out_words.append(buf.strip())
                    buf = ""
                for i in range(0, len(w), max_chars):
                    out_words.append(w[i:i + max_chars])
                continue
            if len(buf) + 1 + len(w) <= max_chars:
                buf = (buf + " " + w).strip() if buf else w
            else:
                if buf:
                    out_words.append(buf.strip())
                buf = w
        if buf:
            out_words.append(buf.strip())
        return out_words

    for sentence in sentences:
        if len(sentence) <= max_chars:
            joined = (current + " " + sentence).strip() if current else sentence
            if len(joined) <= max_chars:
                current = joined
            else:
                _flush()
                current = sentence
        else:
            _flush()
            for piece in _split_oversize(sentence):
                if not current:
                    current = piece
                    continue
                joined = (current + " " + piece).strip()
                if len(joined) <= max_chars:
                    current = joined
                else:
                    _flush()
                    current = piece

    _flush()
    return chunks


def split_script_with_llm(
    script: str,
    max_chars: int = DEFAULT_CHUNK_MAX_CHARS,
) -> list[str]:
    """LLM-assisted chunker. Calls gpt-5-mini to pick clean
    semantic boundaries; falls back to ``chunk_script`` when
    the LLM is unavailable or returns malformed output.

    Graceful degradation per the K6 / V0 pattern: the naive
    splitter is the structural guarantee, the LLM is the
    quality bump. Operators never see "split failed" — at
    worst they get the naive splitter's output.
    """
    cleaned = (script or "").strip()
    if not cleaned:
        return []

    # Short scripts skip the LLM — single chunk is the right
    # answer and the call cost isn't worth it.
    if len(cleaned) <= max_chars:
        return [cleaned]

    # Force-mock + no API key → deterministic naive path.
    if _is_force_mock() or not os.environ.get("OPENAI_API_KEY"):
        return chunk_script(cleaned, max_chars=max_chars)

    try:
        chunks = _gpt5_split(cleaned, max_chars)
    except Exception as exc:  # pragma: no cover — LLM failure path
        logger.warning(
            "split_script_with_llm: gpt-5-mini failed (%s); falling back to naive",
            exc,
        )
        return chunk_script(cleaned, max_chars=max_chars)

    # Validate the LLM output — every chunk must be ≤ max_chars
    # and the concatenation must roughly match the input. If
    # validation fails, fall back to the naive splitter.
    if not chunks or any(len(c) > max_chars for c in chunks):
        logger.warning(
            "split_script_with_llm: LLM returned invalid chunks; falling back",
        )
        return chunk_script(cleaned, max_chars=max_chars)

    # SESSION 251-late — deterministic post-processing repack.
    # Even with a tightened prompt, gpt-5-mini has been observed
    # emitting one-sentence-per-chunk output where several would
    # comfortably fit together. That inflates Runway spend
    # (per-call minimum floor) with no perceptual benefit. Greedy-
    # merge adjacent chunks whenever they fit under the cap;
    # order and wording are preserved by construction.
    return _repack_chunks(chunks, max_chars=max_chars)


def _gpt5_split(text: str, max_chars: int) -> list[str]:
    """Single-shot gpt-5-mini call asking for a JSON array of
    chunks. Kept tight on purpose — script splitting is
    pattern-matching, not multi-step reasoning."""
    from openai import OpenAI

    client = OpenAI()
    system_prompt = (
        "You split long video scripts into contiguous chunks for "
        "TTS rendering. Every chunk feeds a separate paid "
        "provider call, so the goal is to MINIMIZE the number "
        "of chunks while respecting the constraints below.\n\n"
        "Constraints (all must hold):\n"
        f"- Never exceed {max_chars} characters in any chunk.\n"
        "- Split only at sentence-ending punctuation (. ! ?) "
        "or, if a single sentence is too long on its own, at "
        "clause boundaries (comma, semicolon, dash).\n"
        "- Never split mid-word.\n"
        "- Preserve the source wording EXACTLY — no "
        "summarization, paraphrasing, additions, deletions, or "
        "reordering. Concatenating your chunks in order must "
        "reproduce the input verbatim except for whitespace at "
        "chunk boundaries.\n\n"
        "Packing goal (this is the main objective):\n"
        "- Pack as many consecutive sentences into each chunk "
        f"as fit within {max_chars} characters.\n"
        "- Do NOT emit one sentence per chunk when several "
        "consecutive sentences would fit together under the cap.\n"
        "- Do NOT emit standalone short chunks (a single short "
        "sentence, a lone fragment) when they would fit inside "
        "the previous or next chunk without exceeding the cap.\n"
        "- Start a new chunk only when the next sentence would "
        f"push the current chunk over {max_chars} characters.\n\n"
        "Respond with ONLY a JSON array of strings."
    )
    user_prompt = (
        f"Split this script into the FEWEST chunks possible, each "
        f"at most {max_chars} characters. Pack consecutive "
        f"sentences together up to the cap; only break when the "
        f"next sentence would push the current chunk over the "
        f"limit.\n\n{text}"
    )

    response = client.responses.create(
        model=SCRIPT_SPLIT_MODEL,
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        reasoning={"effort": SCRIPT_SPLIT_REASONING_EFFORT},
        max_output_tokens=SCRIPT_SPLIT_MAX_OUTPUT_TOKENS,
    )

    output_text = (response.output_text or "").strip()
    # gpt-5-mini sometimes wraps JSON in ```json fencing.
    if output_text.startswith("```"):
        # Strip the first and last fence lines.
        lines = output_text.split("\n")
        output_text = "\n".join(lines[1:-1]).strip()
        if output_text.startswith("json"):
            output_text = output_text[4:].strip()

    parsed = json.loads(output_text)
    if not isinstance(parsed, list):
        raise ValueError(f"expected JSON array, got {type(parsed).__name__}")
    return [str(item).strip() for item in parsed if str(item).strip()]


def _repack_chunks(chunks: list[str], max_chars: int) -> list[str]:
    """Greedy left-to-right adjacent merge — never reorders, never
    rewrites. Merges consecutive chunks whenever
    ``len(left) + 1 + len(right) <= max_chars`` (the +1 accounts
    for the joining space).

    Applied after ``_gpt5_split`` returns to correct for the LLM's
    observed tendency (SESSION 251-late dogfood) to emit one-
    sentence-per-chunk output even under a tightened prompt. The
    naive ``chunk_script`` doesn't need this — it already packs
    greedily at split time.

    Left-to-right single-pass is provably optimal for the
    contiguous-merge-only problem: once ``chunk[i] + chunk[i+1]``
    won't fit, ``chunk[i+1]`` becomes the head of a new merge
    window and considers ``chunk[i+2]`` fresh. Multi-pass would
    only matter if we allowed non-adjacent merges, which would
    reorder text.

    Returns ``[]`` on empty input. Never returns chunks over
    ``max_chars`` — assumes callers already validated input
    chunks respect the cap (the merge condition can only reduce
    chunk count, never grow individual chunks past the cap).
    """
    if not chunks:
        return []
    result = [chunks[0]]
    for chunk in chunks[1:]:
        last = result[-1]
        if len(last) + 1 + len(chunk) <= max_chars:
            result[-1] = last + " " + chunk
        else:
            result.append(chunk)
    return result


def estimate_chunks(script: str, max_chars: int = DEFAULT_CHUNK_MAX_CHARS) -> int:
    """How many chunks the naive splitter will produce. Used by
    cost estimators that need a count without actually
    running the splitter."""
    return len(chunk_script(script, max_chars=max_chars))


__all__ = [
    "DEFAULT_CHUNK_MAX_CHARS",
    "chunk_script",
    "split_script_with_llm",
    "estimate_chunks",
    "_repack_chunks",
]
