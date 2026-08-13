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
    long_text = "Sentence " + ("number one. " * 30)
    with patch.dict("os.environ", {"OPENAI_API_KEY": "stub"}, clear=False), patch(
        "apps.compositions.script_splitter._is_force_mock",
        return_value=False,
    ), patch(
        "apps.compositions.script_splitter._gpt5_split",
        return_value=["chunk a", "chunk b", "chunk c"],
    ):
        chunks = split_script_with_llm(long_text, max_chars=280)
    assert chunks == ["chunk a", "chunk b", "chunk c"]
