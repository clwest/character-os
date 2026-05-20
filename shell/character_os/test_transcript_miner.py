"""B1.1 — ``select_transcript_highlights`` LLM helper.

Three test groups mirror the test split in
``apps/realtime/tests/test_r6_session_memory.py``:

1. **Force-mock + edge cases** — deterministic, no Django ORM,
   no network. Covers empty body, mock picks, target_count
   clamping, and the 280-char trim.

2. **Parser/validator** — feed crafted JSON shapes through
   ``_parse_and_validate`` directly. Covers contract rule 3
   (offset verification) + rule 8 (char cap) + malformed
   inputs.

3. **Degradation** — no OPENAI_API_KEY, real-mode requested,
   LLM exception. All return ``MiningResult(picks=[])``
   without raising.

The real ``responses.create`` path is covered indirectly via
the mock + a single ``monkeypatch.setattr`` test that asserts
the helper invokes ``_call_responses_api`` with the expected
shape — full end-to-end against OpenAI lands in B1.7 dogfood.
"""
from __future__ import annotations

import json

from django.test import override_settings

from character_os.transcript_miner import (
    DEFAULT_TARGET_COUNT,
    MAX_HIGHLIGHT_CHARS,
    MAX_TARGET_COUNT,
    MIN_TARGET_COUNT,
    MINER_MODEL,
    _parse_and_validate,
    _trim_to_max,
    select_transcript_highlights,
)


# ---- force-mock path ------------------------------------------


@override_settings(TRANSCRIPT_MINER_FORCE_MOCK=True)
def test_mock_picks_longest_assistant_lines() -> None:
    """The mock branch favors ``Assistant:``-prefixed lines
    sorted by length (longest first). This mirrors the real
    LLM's intended behavior — pick punchy spokesperson
    moments — so downstream tests can rely on the mock as a
    deterministic stand-in."""
    body = (
        "Assistant: Short line one.\n"
        "User: hello\n"
        "Assistant: This is the longest assistant line in the "
        "transcript and should be picked first because length "
        "is the mock heuristic for shareability.\n"
        "Assistant: Medium length statement about something.\n"
    )
    result = select_transcript_highlights(body, target_count=2)
    assert result.used_synthesis is True
    assert result.model == f"{MINER_MODEL} (mock)"
    assert len(result.picks) == 2
    # Longest assistant line first.
    assert "longest assistant line" in result.picks[0].text
    # Mock reasoning is the deterministic stub string.
    for p in result.picks:
        assert "mock" in p.llm_reasoning.lower()


@override_settings(TRANSCRIPT_MINER_FORCE_MOCK=True)
def test_mock_offsets_match_source_body() -> None:
    """Every mock pick must satisfy
    ``body[char_start:char_end] == text``. Contract rule 3."""
    body = (
        "Assistant: First insight here.\n"
        "Assistant: A second, longer insight worth sharing.\n"
    )
    result = select_transcript_highlights(body, target_count=5)
    for p in result.picks:
        assert body[p.char_start:p.char_end] == p.text


@override_settings(TRANSCRIPT_MINER_FORCE_MOCK=True)
def test_mock_returns_empty_for_blank_body() -> None:
    body = "   \n\n  "
    result = select_transcript_highlights(body)
    assert result.picks == []
    assert result.used_synthesis is False


@override_settings(TRANSCRIPT_MINER_FORCE_MOCK=True)
def test_mock_clamps_target_count_high() -> None:
    body = "\n".join(f"Assistant: line {i}" for i in range(20))
    result = select_transcript_highlights(body, target_count=999)
    assert len(result.picks) <= MAX_TARGET_COUNT


@override_settings(TRANSCRIPT_MINER_FORCE_MOCK=True)
def test_mock_clamps_target_count_low() -> None:
    body = "\n".join(f"Assistant: line {i}" for i in range(5))
    result = select_transcript_highlights(body, target_count=0)
    assert len(result.picks) >= MIN_TARGET_COUNT


@override_settings(TRANSCRIPT_MINER_FORCE_MOCK=True)
def test_mock_falls_back_to_longest_lines_without_assistant_prefix() -> None:
    """When the transcript has no ``Assistant:`` markers, the
    mock falls back to the longest lines overall — useful for
    transcripts that weren't captured via R5's standard
    formatting."""
    body = (
        "Some plain text without speaker markers.\n"
        "Another short line.\n"
        "The longest line in this transcript should still get "
        "picked because the mock degrades gracefully when "
        "speaker prefixes are missing.\n"
    )
    result = select_transcript_highlights(body, target_count=1)
    assert len(result.picks) == 1
    assert "longest line" in result.picks[0].text


@override_settings(TRANSCRIPT_MINER_FORCE_MOCK=True)
def test_mock_caps_pick_at_280_chars() -> None:
    """Rule 8 — even mock picks honor the 280-char cap. A
    500-char assistant line gets trimmed."""
    long_text = "x " * 250  # 500 chars
    body = f"Assistant: {long_text.strip()}\n"
    result = select_transcript_highlights(body, target_count=1)
    assert len(result.picks) == 1
    assert len(result.picks[0].text) <= MAX_HIGHLIGHT_CHARS


# ---- _parse_and_validate ---------------------------------------


def test_parser_drops_offset_mismatch() -> None:
    """Contract rule 3 enforcement — if the LLM claims
    ``text="X"`` at offsets ``[5, 10]`` but the source at that
    range is something else, the pick is dropped."""
    source = "The quick brown fox jumps over the lazy dog."
    raw = json.dumps({
        "highlights": [
            {
                "text": "GHOST TEXT NOT IN SOURCE",
                "char_start": 5, "char_end": 10,
                "reasoning": "fabricated by the LLM",
            },
            {
                "text": "quick brown",  # source[4:15] = "quick brown"
                "char_start": 4, "char_end": 15,
                "reasoning": "valid pick",
            },
        ]
    })
    picks = _parse_and_validate(raw, source, MAX_HIGHLIGHT_CHARS)
    assert len(picks) == 1
    assert picks[0].text == "quick brown"


def test_parser_drops_picks_with_negative_offsets() -> None:
    source = "abc def ghi"
    raw = json.dumps({
        "highlights": [
            {"text": "a", "char_start": -1, "char_end": 2, "reasoning": ""},
        ]
    })
    assert _parse_and_validate(raw, source, MAX_HIGHLIGHT_CHARS) == []


def test_parser_drops_picks_with_end_le_start() -> None:
    source = "abc def ghi"
    raw = json.dumps({
        "highlights": [
            {"text": "", "char_start": 5, "char_end": 5, "reasoning": ""},
            {"text": "x", "char_start": 5, "char_end": 3, "reasoning": ""},
        ]
    })
    assert _parse_and_validate(raw, source, MAX_HIGHLIGHT_CHARS) == []


def test_parser_drops_picks_past_source_end() -> None:
    source = "abc"
    raw = json.dumps({
        "highlights": [
            {"text": "abc", "char_start": 0, "char_end": 100, "reasoning": ""},
        ]
    })
    assert _parse_and_validate(raw, source, MAX_HIGHLIGHT_CHARS) == []


def test_parser_drops_non_dict_entries() -> None:
    """Defensive — LLM might return a list of strings or nulls."""
    source = "abc def"
    raw = json.dumps({"highlights": ["just a string", None, 42]})
    assert _parse_and_validate(raw, source, MAX_HIGHLIGHT_CHARS) == []


def test_parser_handles_non_json() -> None:
    """Malformed LLM output → empty list, not exception."""
    source = "abc def"
    assert _parse_and_validate("this is not json", source, MAX_HIGHLIGHT_CHARS) == []
    assert _parse_and_validate("", source, MAX_HIGHLIGHT_CHARS) == []
    assert _parse_and_validate("  \n  ", source, MAX_HIGHLIGHT_CHARS) == []


def test_parser_handles_missing_highlights_key() -> None:
    """LLM returns wrong shape — empty result, no exception."""
    source = "abc def"
    assert _parse_and_validate('{"picks": []}', source, MAX_HIGHLIGHT_CHARS) == []
    assert _parse_and_validate('[]', source, MAX_HIGHLIGHT_CHARS) == []


def test_parser_trims_oversize_pick_at_sentence_boundary() -> None:
    """Rule 8 — a 350-char pick that contains a sentence
    boundary near the cap gets trimmed to the boundary."""
    source = (
        "Hello there. This is sentence one. This is the second "
        "and considerably longer sentence that crosses the cap "
        "somewhere near the middle of its body. "
    ) + ("x " * 150)
    # Pick the whole long region
    raw = json.dumps({
        "highlights": [
            {
                "text": source.strip(),
                "char_start": 0, "char_end": len(source.strip()),
                "reasoning": "long",
            }
        ]
    })
    picks = _parse_and_validate(raw, source.strip(), MAX_HIGHLIGHT_CHARS)
    assert len(picks) == 1
    assert len(picks[0].text) <= MAX_HIGHLIGHT_CHARS
    # The trim should re-locate char_end so audit math holds.
    assert picks[0].char_end == picks[0].char_start + len(picks[0].text)


def test_trim_helper_prefers_sentence_boundary() -> None:
    """``_trim_to_max`` should prefer a sentence terminator
    within the trailing 60 chars of the cap window."""
    text = (
        "This sentence ends here. "
        "Then more content runs on and on without obvious "
        "punctuation for a while xxx xxx xxx xxx xxx xxx xxx xxx"
    )
    trimmed, new_end = _trim_to_max(text, char_start=0, max_chars=40)
    assert trimmed == "This sentence ends here."
    assert new_end == len(trimmed)


def test_trim_helper_hard_trims_when_no_boundary() -> None:
    text = "a" * 300
    trimmed, new_end = _trim_to_max(text, char_start=10, max_chars=50)
    assert len(trimmed) <= 50
    assert new_end == 10 + len(trimmed)


# ---- degradation paths -----------------------------------------


def test_returns_empty_when_no_openai_key(monkeypatch) -> None:
    """Real-mode requested, no key, no force-mock → empty
    result + warning log. Doesn't crash."""
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("TRANSCRIPT_MINER_FORCE_MOCK", raising=False)
    with override_settings(TRANSCRIPT_MINER_FORCE_MOCK=False):
        result = select_transcript_highlights("Assistant: hello world")
    assert result.picks == []
    assert result.used_synthesis is False


def test_returns_empty_when_responses_api_raises(monkeypatch) -> None:
    """LLM call blows up → empty result + exception logged."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")

    def _boom(*_args, **_kwargs):
        raise RuntimeError("OpenAI unreachable")

    monkeypatch.setattr(
        "character_os.transcript_miner._call_responses_api", _boom,
    )
    with override_settings(TRANSCRIPT_MINER_FORCE_MOCK=False):
        result = select_transcript_highlights("Assistant: hello world")
    assert result.picks == []
    assert result.used_synthesis is False


def test_calls_responses_api_with_expected_shape(monkeypatch) -> None:
    """The helper passes the source body + target_count +
    max_chars through to the OpenAI wrapper. Verifies the
    plumbing without hitting the network."""
    monkeypatch.setenv("OPENAI_API_KEY", "test-key-not-real")
    captured = {}

    def _fake(body, target, max_c):
        captured["body"] = body
        captured["target"] = target
        captured["max_c"] = max_c
        return ("{}", 0, 0)  # empty highlights, no usage

    monkeypatch.setattr(
        "character_os.transcript_miner._call_responses_api", _fake,
    )
    with override_settings(TRANSCRIPT_MINER_FORCE_MOCK=False):
        select_transcript_highlights(
            "Assistant: a sample transcript body.",
            target_count=3,
            max_chars=200,
        )
    assert captured["target"] == 3
    assert captured["max_c"] == 200
    assert "sample transcript body" in captured["body"]


def test_defaults_target_count_to_five() -> None:
    """Default target is 5 per scope-lock Q-b-1."""
    assert DEFAULT_TARGET_COUNT == 5
