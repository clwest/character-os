"""V5 unit tests for the script splitter helper.

Covers the naive chunker (deterministic, no I/O) +
``split_script_with_llm`` graceful degradation paths. The
LLM-success path is tested by patching OpenAI; the LLM-
failure path verifies the fallback to naive splitting.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from apps.compositions.script_splitter import (
    DEFAULT_CHUNK_MAX_CHARS,
    _repack_chunks,
    chunk_script,
    estimate_chunks,
    split_script_with_llm,
)


# ---- naive splitter ----------------------------------------


def test_chunk_script_empty_returns_empty() -> None:
    assert chunk_script("") == []
    assert chunk_script("   \n  ") == []


def test_chunk_script_short_input_returns_single_chunk() -> None:
    text = "One short sentence."
    chunks = chunk_script(text, max_chars=280)
    assert chunks == [text]


def test_chunk_script_packs_sentences_greedily() -> None:
    """Five short sentences fit comfortably in one chunk at
    max_chars=280."""
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
    chunks = chunk_script(text, max_chars=280)
    assert len(chunks) == 1
    assert "Sentence one" in chunks[0]
    assert "Sentence five" in chunks[0]


def test_chunk_script_splits_when_total_exceeds_max() -> None:
    sentences = [f"Sentence number {i}." for i in range(1, 21)]
    text = " ".join(sentences)
    chunks = chunk_script(text, max_chars=80)
    assert len(chunks) >= 4
    for c in chunks:
        assert len(c) <= 80


def test_chunk_script_falls_back_to_clause_for_long_sentence() -> None:
    """A single sentence longer than max_chars should be split
    at clause boundaries."""
    text = (
        "This is one very long sentence, with multiple clauses, "
        "each separated by commas, and the splitter should pack "
        "them into multiple chunks rather than overflowing."
    )
    chunks = chunk_script(text, max_chars=60)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 60


def test_chunk_script_hard_cuts_pathological_word() -> None:
    word = "x" * 200
    chunks = chunk_script(word, max_chars=50)
    assert len(chunks) >= 4
    for c in chunks:
        assert len(c) <= 50


def test_estimate_chunks_matches_actual() -> None:
    text = "One. Two. Three. " * 20
    assert estimate_chunks(text, max_chars=50) == len(
        chunk_script(text, max_chars=50)
    )


# ---- LLM-assisted splitter --------------------------------


def test_split_script_with_llm_short_input_skips_llm() -> None:
    """Scripts shorter than max_chars get returned as a single
    chunk without any LLM call."""
    text = "Hello world."
    with patch(
        "apps.compositions.script_splitter._gpt5_split"
    ) as fake_gpt:
        chunks = split_script_with_llm(text, max_chars=280)
    assert chunks == [text]
    fake_gpt.assert_not_called()


def test_split_script_with_llm_empty_returns_empty() -> None:
    with patch(
        "apps.compositions.script_splitter._gpt5_split"
    ) as fake_gpt:
        assert split_script_with_llm("") == []
    fake_gpt.assert_not_called()


def test_split_script_with_llm_falls_back_when_force_mock() -> None:
    """``RENDER_SCRIPT_FORCE_MOCK=1`` short-circuits to the
    naive splitter."""
    long_text = "Sentence number one. " * 30
    from django.test import override_settings

    with override_settings(RENDER_SCRIPT_FORCE_MOCK=True), patch(
        "apps.compositions.script_splitter._gpt5_split"
    ) as fake_gpt:
        chunks = split_script_with_llm(long_text, max_chars=80)
    fake_gpt.assert_not_called()
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 80


def test_split_script_with_llm_falls_back_when_api_failure() -> None:
    """Any exception from the LLM call falls back to naive."""
    long_text = "Sentence " + ("number one. " * 30)
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        side_effect=RuntimeError("openai exploded"),
    ):
        chunks = split_script_with_llm(long_text, max_chars=80)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 80


def test_split_script_with_llm_falls_back_when_chunks_too_long() -> None:
    """The LLM returned a chunk longer than max_chars → fall
    back to naive (the LLM didn't honor the constraint)."""
    long_text = "Sentence " + ("number one. " * 30)
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        return_value=["x" * 500],  # too long
    ):
        chunks = split_script_with_llm(long_text, max_chars=80)
    # Fallback ran — every chunk respects the cap.
    for c in chunks:
        assert len(c) <= 80


def test_split_script_with_llm_uses_llm_output_on_success() -> None:
    """LLM-returned chunks that DO NOT fit together (each is
    already near the cap) flow through unchanged after the
    repack pass — repack only merges when the joined length
    still fits ≤ max_chars."""
    long_text = "Sentence " + ("number one. " * 30)
    already_full = "a" * 260  # 260 + 1 + 260 = 521 > 280, cannot merge
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        return_value=[already_full, already_full, already_full],
    ):
        chunks = split_script_with_llm(long_text, max_chars=280)
    assert chunks == [already_full, already_full, already_full]


def test_split_script_with_llm_repacks_short_llm_chunks() -> None:
    """SESSION 251-late — LLM returning small chunks that fit
    together must be greedily merged. Regression test for the
    "23 chunks where 7 would do" behavior observed in composition
    75258423 dogfood."""
    long_text = "Some longer script text goes here " * 20
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        return_value=["chunk a", "chunk b", "chunk c"],
    ):
        chunks = split_script_with_llm(long_text, max_chars=280)
    # 3 short chunks (~7 chars each) all fit into one 280-char chunk.
    assert chunks == ["chunk a chunk b chunk c"]


# ---- _repack_chunks unit tests -----------------------------


def test_repack_empty() -> None:
    assert _repack_chunks([], max_chars=280) == []


def test_repack_single_chunk_passthrough() -> None:
    assert _repack_chunks(["hello world"], max_chars=280) == ["hello world"]


def test_repack_merges_when_pair_fits() -> None:
    """Two chunks whose joined length + 1 space fits under the
    cap must merge into one."""
    result = _repack_chunks(["one", "two"], max_chars=280)
    assert result == ["one two"]


def test_repack_does_not_merge_when_pair_overflows() -> None:
    """Boundary: two 140-char chunks + 1 space = 281 > 280 —
    must not merge."""
    a = "a" * 140
    b = "b" * 140
    result = _repack_chunks([a, b], max_chars=280)
    assert result == [a, b]


def test_repack_boundary_inclusive() -> None:
    """The cap is inclusive: 139 + 1 + 140 = 280 must merge."""
    a = "a" * 139
    b = "b" * 140
    result = _repack_chunks([a, b], max_chars=280)
    assert result == [f"{a} {b}"]


def test_repack_preserves_order() -> None:
    """Left-to-right merge never reorders. Give it a sequence
    with a growing running-total pattern and check order."""
    inputs = ["one", "two", "three", "four", "five"]
    result = _repack_chunks(inputs, max_chars=280)
    # All fit together comfortably.
    assert result == ["one two three four five"]


def test_repack_preserves_wording_exactly() -> None:
    """Repack must never rewrite text — only join with a single
    space and only when the joined length fits."""
    inputs = ["Hello world.", "How are you?", "Fine, thanks."]
    result = _repack_chunks(inputs, max_chars=280)
    # Reconstruct: split on the single spaces the repack introduced
    # and verify every input's words appear in order.
    joined = " ".join(result)
    for chunk in inputs:
        assert chunk in joined


def test_repack_handles_multi_pass_scenario_in_single_pass() -> None:
    """Left-to-right single pass is provably optimal for
    contiguous merges. Verify against a shape where a naive
    per-pair check might stop early: [big, small, small, big]
    where big+small doesn't fit but small+small does."""
    big = "b" * 200
    small = "s" * 30
    result = _repack_chunks([big, small, small, big], max_chars=280)
    # big + " " + small = 231 <= 280 — merges.
    # (big+small) + " " + small = 262 <= 280 — merges again.
    # (big+small+small) + " " + big = 462 > 280 — flushes.
    # Result: [big+small+small, big] = 2 chunks.
    assert len(result) == 2
    assert result[0] == f"{big} {small} {small}"
    assert result[1] == big


# ---- Regression: reconstructed Penny script ----------------


# Reconstruction of composition 75258423-5217-4d53-b71a-565918831523's
# manually-provided script. This is the exact fixture that made the
# 23-chunk defect observable in dogfood. Reconstructed by joining the
# persisted chunks with single spaces — matches the input the naive
# splitter would need to reproduce the packed shape.
_PENNY_RECONSTRUCTED = " ".join([
    "There\u2019s something funny about standing at the edge of the water.",
    "From shore, everything can look a little intimidating.",
    "You see the kayaks, the paddles, all that open water, and suddenly "
    "your brain starts asking questions like, \u201cWait\u2026 do I "
    "actually know how to do this?\u201d",
    "Hi, I\u2019m Penny, and as an otter, I may be slightly biased about "
    "getting in the water.",
    "But here\u2019s the thing: you don\u2019t have to arrive as an expert.",
    "At Riverstone Outdoor Adventures, beginners are welcome.",
    "Learning, asking questions, and getting comfortable are all part of "
    "the experience.",
    "Maybe your adventure is kayaking.",
    "Maybe it\u2019s trying a paddleboard for the first time.",
    "Maybe you want to go rafting, explore nature, or simply experience "
    "Colorado from a perspective you haven\u2019t seen before.",
    "Whatever brings you to the water, you can start where you are.",
    "Take the time to learn.",
    "Listen to your guides.",
    "Respect the water, the wildlife, and the places you\u2019ve come "
    "to enjoy.",
    "And don\u2019t worry about looking like an expert.",
    "Adventure isn\u2019t about proving you already know everything.",
    "Sometimes, it\u2019s about being willing to try something new.",
    "And there\u2019s a pretty incredible moment when the shoreline "
    "starts getting farther away, you find your rhythm, and that nervous "
    "feeling begins turning into, \u201cOkay\u2026 I can do this.\u201d",
    "That\u2019s the part I love.",
    "Well, that and swimming.",
    "So if you\u2019ve been waiting until you feel like an outdoors "
    "person before having an outdoor adventure, maybe you don\u2019t have "
    "to.",
    "Come curious.",
    "We\u2019ll see you on the water.",
])


# The 23-chunk output that would come back from an old-behavior LLM
# splitter — one sentence per chunk. This is the fixture the repack
# pass must correct.
_PENNY_LLM_ONE_SENTENCE_PER_CHUNK = [
    "There\u2019s something funny about standing at the edge of the water.",
    "From shore, everything can look a little intimidating.",
    "You see the kayaks, the paddles, all that open water, and suddenly "
    "your brain starts asking questions like, \u201cWait\u2026 do I "
    "actually know how to do this?\u201d",
    "Hi, I\u2019m Penny, and as an otter, I may be slightly biased about "
    "getting in the water.",
    "But here\u2019s the thing: you don\u2019t have to arrive as an expert.",
    "At Riverstone Outdoor Adventures, beginners are welcome.",
    "Learning, asking questions, and getting comfortable are all part of "
    "the experience.",
    "Maybe your adventure is kayaking.",
    "Maybe it\u2019s trying a paddleboard for the first time.",
    "Maybe you want to go rafting, explore nature, or simply experience "
    "Colorado from a perspective you haven\u2019t seen before.",
    "Whatever brings you to the water, you can start where you are.",
    "Take the time to learn.",
    "Listen to your guides.",
    "Respect the water, the wildlife, and the places you\u2019ve come "
    "to enjoy.",
    "And don\u2019t worry about looking like an expert.",
    "Adventure isn\u2019t about proving you already know everything.",
    "Sometimes, it\u2019s about being willing to try something new.",
    "And there\u2019s a pretty incredible moment when the shoreline "
    "starts getting farther away, you find your rhythm, and that nervous "
    "feeling begins turning into, \u201cOkay\u2026 I can do this.\u201d",
    "That\u2019s the part I love.",
    "Well, that and swimming.",
    "So if you\u2019ve been waiting until you feel like an outdoors "
    "person before having an outdoor adventure, maybe you don\u2019t have "
    "to.",
    "Come curious.",
    "We\u2019ll see you on the water.",
]


def test_penny_reconstruction_matches_source() -> None:
    """Fixture sanity: the reconstructed script and the joined
    one-sentence-per-chunk fixture agree at the character
    level."""
    assert _PENNY_RECONSTRUCTED == " ".join(_PENNY_LLM_ONE_SENTENCE_PER_CHUNK)
    assert len(_PENNY_LLM_ONE_SENTENCE_PER_CHUNK) == 23


def test_penny_naive_chunker_produces_seven_chunks() -> None:
    """Baseline for the regression: the naive greedy packer
    (use_llm_split=False path) produces 7 packed chunks from
    the Penny script."""
    chunks = chunk_script(_PENNY_RECONSTRUCTED, max_chars=280)
    assert len(chunks) == 7
    for c in chunks:
        assert len(c) <= 280


def test_penny_llm_path_repacks_23_to_naive_equivalent() -> None:
    """SESSION 251-late regression — the LLM splitter emitting
    the historical one-sentence-per-chunk output (23 chunks)
    must, after the deterministic repack pass, converge on the
    same or near-equivalent packed shape as the naive path (7
    chunks)."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        return_value=list(_PENNY_LLM_ONE_SENTENCE_PER_CHUNK),
    ):
        packed = split_script_with_llm(
            _PENNY_RECONSTRUCTED, max_chars=280,
        )

    naive = chunk_script(_PENNY_RECONSTRUCTED, max_chars=280)

    # Same chunk count (or at most 1 different if the sentence
    # boundaries the LLM chose differ from the regex's).
    assert abs(len(packed) - len(naive)) <= 1, (
        f"LLM path produced {len(packed)} chunks after repack, "
        f"naive produced {len(naive)}; expected within 1"
    )

    # Every chunk respects the cap.
    for c in packed:
        assert len(c) <= 280, f"chunk exceeded 280 chars: {len(c)}"

    # No absurdly short standalone chunks — the pathological
    # 13-char "Come curious." should have been absorbed into a
    # neighbor.
    for c in packed:
        # Anything under 30 chars would only occur if it truly
        # can't fit with a neighbor. In Penny's script, none of
        # the short sentences are that isolated.
        assert len(c) > 30, (
            f"repack left a suspiciously short standalone chunk "
            f"({len(c)} chars): {c!r}"
        )


def test_penny_llm_path_preserves_wording_and_order() -> None:
    """Concatenating the repacked chunks (with single spaces
    between them, matching the repack's join glue) must
    reproduce the source wording and order exactly. Repack
    never rewrites or reorders."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        return_value=list(_PENNY_LLM_ONE_SENTENCE_PER_CHUNK),
    ):
        packed = split_script_with_llm(
            _PENNY_RECONSTRUCTED, max_chars=280,
        )

    # Reconstitute the concatenation and compare to the source.
    reconstituted = " ".join(packed)
    assert reconstituted == _PENNY_RECONSTRUCTED


def test_penny_come_curious_absorbed_into_neighbor() -> None:
    """The 13-char \"Come curious.\" sentence must merge into
    an adjacent chunk when there's capacity. Explicit assertion
    of the pathological-tiny-chunk absorption behavior the
    operator called out."""
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        return_value=list(_PENNY_LLM_ONE_SENTENCE_PER_CHUNK),
    ):
        packed = split_script_with_llm(
            _PENNY_RECONSTRUCTED, max_chars=280,
        )
    # "Come curious." must appear INSIDE another chunk, not as
    # its own row.
    standalone = [c for c in packed if c == "Come curious."]
    assert standalone == [], (
        f"\"Come curious.\" survived repack as a standalone chunk. "
        f"Final packed chunks: {[len(c) for c in packed]}"
    )
    merged_chunks = [c for c in packed if "Come curious." in c]
    assert len(merged_chunks) == 1


def test_llm_path_cannot_regress_to_one_sentence_per_chunk() -> None:
    """SESSION 251-late — hard guarantee that no matter what
    the LLM emits, the final output CANNOT be one-sentence-per-
    chunk when adjacent chunks fit together under the cap. This
    is the load-bearing invariant of the repack pass.

    Constructs a synthetic worst-case: 10 sentences of ~40 chars
    each, all under the cap. Any two adjacent fit together; the
    repack must reduce them to fewer than 10 chunks. Ideally
    they pack into ~2 chunks at 280 chars.
    """
    sentences = [
        f"Sentence number {i} with padding words." for i in range(1, 11)
    ]
    # Each sentence is ~40 chars; adjacent pairs total ~80 chars
    # with a space, easily under 280.
    assert all(len(s) < 45 for s in sentences)
    full_text = " ".join(sentences)
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        return_value=list(sentences),  # simulate one-per-chunk
    ):
        packed = split_script_with_llm(full_text, max_chars=280)

    # Cannot be 10 chunks — repack must have merged.
    assert len(packed) < 10, (
        f"repack failed to merge; got {len(packed)} chunks from "
        f"10 short sentences that all fit under the cap"
    )
    # Every chunk under cap.
    for c in packed:
        assert len(c) <= 280
    # Wording preserved.
    assert " ".join(packed) == full_text
