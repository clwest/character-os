"""SESSION 272 Slice F — production ``_expansion_hint`` anchor swap.

Pins the smallest bounded production change:

  * The corrective-expansion hint opens with ``EXPAND YOUR SCRIPT``.
  * The pre-Slice-F opening ``REWRITE THE SAME NARRATIVE ABOVE`` is
    gone from the expansion hint entirely.
  * Every other piece of production hint wording is preserved
    byte-for-byte — character-shortfall math, arc / narrator /
    factual-grounding preservation, ``Expand secondary detail from
    the knowledge chunks``, ``Do NOT restart with a new opening``,
    ``Do NOT add a second call to action``, ``Do NOT invent facts
    not present in the knowledge chunks``.
  * No previous_draft behaviour is activated (Q-270-15c remains
    env-gated; ``synthesize_with_duration_gate`` continues to omit
    the kwarg from its public signature).
  * The unrelated ``_compression_hint`` (BELOW variant) is
    untouched.

Evidence — see docs/design/SESSION_272_KNOWLEDGE_AUTHORING_SHAPE_AUDIT.md
§19 (3-condition n=5 ablation) and §20 (production-fix rationale).
"""
from __future__ import annotations

import inspect

from character_os.duration_contract import (
    _compression_hint,
    _expansion_hint,
    synthesize_with_duration_gate,
)


_FIXED_ARGS = dict(
    actual_chars=568,
    actual_words=100,
    actual_seconds=39,
    target_duration_seconds=81,
    effective_ideal=1215,
    effective_min=972,
    effective_max=1458,
)


def _expansion_sample() -> str:
    return _expansion_hint(**_FIXED_ARGS)


def _compression_sample() -> str:
    return _compression_hint(**_FIXED_ARGS)


# ---- Slice F production change ------------------------------------


def test_expansion_hint_opens_with_expand_your_script():
    """The Slice F production anchor is present in the emitted hint."""
    text = _expansion_sample()
    assert "EXPAND YOUR SCRIPT TO AT LEAST" in text


def test_expansion_hint_no_longer_contains_rewrite_narrative_above():
    """The pre-Slice-F misleading anchor is gone from the expansion
    hint. It referred to a Draft A that only exists when Q-270-15c
    is active — see audit doc §18.2 + §19."""
    text = _expansion_sample()
    assert "REWRITE THE SAME NARRATIVE ABOVE" not in text
    assert "REWRITE THE SAME NARRATIVE" not in text


# ---- Preserved wording (all other production text intact) ---------


def test_expansion_hint_preserves_character_shortfall_math():
    text = _expansion_hint(
        actual_chars=568,
        actual_words=100,
        actual_seconds=39,
        target_duration_seconds=81,
        effective_ideal=1215,
        effective_min=972,
        effective_max=1458,
    )
    assert "Your previous draft was 568 characters" in text
    assert "(100 words, estimated ~39s of speech)" in text
    assert "Target is 81s" in text
    assert "AT LEAST 972 CHARACTERS" in text
    assert "aim for ~1215" in text
    assert "do not exceed 1458" in text
    # Shortfall math: min(972) - actual(568) = 404
    assert "at least 404 more characters" in text


def test_expansion_hint_preserves_arc_narrator_grounding_language():
    text = _expansion_sample()
    assert "Preserve the central arc" in text
    assert "opening → development → payoff → single closing invitation" in text
    assert "narrator perspective" in text
    assert "factual grounding from the knowledge chunks" in text


def test_expansion_hint_preserves_expand_from_knowledge_chunks_instruction():
    """The Slice F change is anchor-only; the knowledge-chunk expansion
    instruction is INTENTIONALLY retained per §19 evidence — CORRECT_ANCHOR
    (retaining these references) achieved the largest attractor reduction
    while NO_KNOWLEDGE_REF (removing them) reduced identity markers more
    and produced no additional benefit."""
    text = _expansion_sample()
    assert "Expand secondary detail from the knowledge chunks" in text
    assert "sensory / emotional beats already implied" in text


def test_expansion_hint_preserves_all_prohibitions():
    text = _expansion_sample()
    assert "Do NOT restart with a new opening" in text
    assert "Do NOT add a second call to action" in text
    assert "Do NOT invent facts not present in the knowledge chunks" in text


# ---- Q-270-15c contract remains OFF by default -------------------


def test_synthesize_with_duration_gate_signature_still_omits_previous_draft():
    """Slice F does NOT change the public signature. Q-270-15c
    remains env-gated inside the function body and cannot be
    activated by caller kwargs."""
    sig = inspect.signature(synthesize_with_duration_gate)
    assert "previous_draft" not in sig.parameters


# ---- Compression hint (unrelated) is untouched -------------------


def test_compression_hint_unchanged_by_slice_f():
    """Slice F scope is expansion-only. The compression hint's
    ``REWRITE THE SAME NARRATIVE BELOW`` anchor was NOT experimentally
    evaluated in Slice E and must remain byte-stable in Slice F."""
    text = _compression_sample()
    assert "REWRITE THE SAME NARRATIVE BELOW" in text
    # Compression hint does NOT contain the Slice F expansion anchor.
    assert "EXPAND YOUR SCRIPT" not in text
    # Compression hint's factual-grounding wording is a different
    # phrasing than the expansion hint's — verify it survives.
    assert "the factual grounding" in text
    assert "the closing call to action" in text
    assert "Do NOT invent facts not present in the knowledge chunks" in text
