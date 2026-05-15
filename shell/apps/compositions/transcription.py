"""Sentence-pick helper for the V12 transcription arc.

SESSION 143 / V12. The transcription itself is media-engine
side (via OpenAI Whisper); this module ships the sentence
selection logic that the ``recut_teaser`` starter calls
synchronously at composition-create time.

Pattern mirrors V5's ``script_splitter`` — a small helper that
both the registry primitive AND a starter factory can call.
The starter pre-computes timing so the runtime sees a
deterministic step plan (V0 contract rule 5: linear ordering
only, no dynamic step expansion).

### What "strongest sentence" means in v1

* If the operator supplies ``criterion="first"``: just return
  the first segment. Deterministic, no LLM call.
* If the operator supplies ``criterion="last"``: the last
  segment.
* If ``criterion="hook"`` (the default in ``recut_teaser``):
  gpt-5-mini picks the segment with the most attention-
  grabbing one-line claim. Falls back to the longest segment
  on any LLM failure (graceful degradation per the K6 /
  script_splitter pattern).

### Why no separate primitive

V12 ships the ``transcribe`` primitive in the registry but
does NOT ship a ``pick_sentence`` primitive. Reason: the V2
runtime resolves inputs to whole Asset rows, not to fields
inside them. A ``pick_sentence`` step that produced a
subset TRANSCRIPT would still need downstream ``trim_clip``
to read its timing — which trim_clip can't do (it takes
``start_ms``/``end_ms`` from params). Rather than extend the
runtime, the starter takes the synchronous Whisper hit at
create-time and bakes the picked timing into the trim step's
params. Operator-visible latency: ~30s at starter creation,
~10s at composition execute.
"""
from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Literal

from django.conf import settings as django_settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Segment:
    start_s: float
    end_s: float
    text: str

    @property
    def duration_s(self) -> float:
        return max(self.end_s - self.start_s, 0.0)


SentencePickCriterion = Literal["first", "last", "longest", "hook"]


def _is_force_mock() -> bool:
    if os.environ.get("RENDER_SCRIPT_FORCE_MOCK"):
        return True
    return bool(getattr(django_settings, "RENDER_SCRIPT_FORCE_MOCK", False))


def pick_strongest_segment(
    segments: list[Segment],
    *,
    criterion: SentencePickCriterion = "hook",
) -> Segment:
    """Pick one segment from a transcript.

    Pure function — no I/O for deterministic criteria. The
    "hook" criterion calls gpt-5-mini; falls back to "longest"
    on any LLM failure. Always returns a Segment (never None);
    raises ValueError only if segments is empty.
    """
    if not segments:
        raise ValueError("pick_strongest_segment requires at least one segment")

    if criterion == "first":
        return segments[0]
    if criterion == "last":
        return segments[-1]
    if criterion == "longest":
        return max(segments, key=lambda s: s.duration_s)

    # "hook" → gpt-5-mini selection. Graceful degradation:
    # fall back to longest if force-mock, missing API key, or
    # any LLM failure.
    if _is_force_mock() or not os.environ.get("OPENAI_API_KEY"):
        return max(segments, key=lambda s: s.duration_s)

    try:
        idx = _gpt5_pick_hook_index(segments)
    except Exception as exc:  # pragma: no cover — graceful degradation
        logger.warning(
            "pick_strongest_segment: gpt-5-mini failed (%s); falling back to longest",
            exc,
        )
        return max(segments, key=lambda s: s.duration_s)

    if not isinstance(idx, int) or idx < 0 or idx >= len(segments):
        logger.warning(
            "pick_strongest_segment: gpt-5-mini returned invalid index %r; "
            "falling back to longest",
            idx,
        )
        return max(segments, key=lambda s: s.duration_s)

    return segments[idx]


def _gpt5_pick_hook_index(segments: list[Segment]) -> int:
    """Single-shot gpt-5-mini call asking for the index of the
    most hook-worthy segment. Returns the integer index."""
    from openai import OpenAI

    client = OpenAI()
    enumerated = "\n".join(
        f"[{i}] {s.text}" for i, s in enumerate(segments)
    )
    system_prompt = (
        "You pick the single most hook-worthy line from a transcript. "
        "A hook is short, declarative, surprising, or emotionally "
        "loaded — the kind of line that makes a viewer keep watching. "
        "Respond with ONLY the integer index (e.g. 2), nothing else."
    )
    user_prompt = (
        "Pick the index of the strongest hook line:\n\n" + enumerated
    )
    response = client.responses.create(
        model="gpt-5-mini",
        input=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        reasoning={"effort": "low"},
        max_output_tokens=20,
    )
    output_text = (response.output_text or "").strip()
    # Strip non-digits — model sometimes wraps the integer.
    digits = "".join(c for c in output_text if c.isdigit())
    if not digits:
        raise ValueError(f"gpt-5-mini returned non-numeric: {output_text!r}")
    return int(digits)


def fetch_transcript(source_url: str, *, extract_audio: bool = True) -> list[Segment]:
    """Helper used by ``recut_teaser`` starter to synchronously
    transcribe a CLIP/AUDIO URL via the media-engine. Returns
    the segment list (typed). Raises if the media-engine call
    fails — operators see a clean error at starter time."""
    from character_os.clients.media_engine import (
        MediaEngineClient,
        MediaEngineError,
    )

    with MediaEngineClient() as client:
        result = client.transcribe(source_url=source_url, extract_audio=extract_audio)
    return [
        Segment(start_s=s.start_s, end_s=s.end_s, text=s.text)
        for s in result.segments
    ]


__all__ = [
    "Segment",
    "SentencePickCriterion",
    "fetch_transcript",
    "pick_strongest_segment",
]
