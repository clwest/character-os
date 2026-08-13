"""K7.x v2 (SESSION 175) — YouTube transcript extractor tests.

Mocks ``YouTubeTranscriptApi`` so tests stay hermetic — no
real YouTube calls. Covers video_id extraction from every
URL shape, transcript concatenation + music-marker dropping,
and the operator-actionable error path for each documented
youtube-transcript-api failure mode.
"""
from __future__ import annotations

from dataclasses import dataclass
from unittest.mock import MagicMock, patch

import pytest

from apps.embeddings.url_fetch import UrlFetchError, fetch_url
from apps.embeddings.youtube_extractor import (
    _clean_transcript_text,
    _extract_video_id,
    extract_youtube_transcript,
)


# ---- video_id extraction -----------------------------------------


@pytest.mark.parametrize("url,expected", [
    # Standard watch URLs.
    ("https://www.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://m.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://music.youtube.com/watch?v=dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    # Short URL.
    ("https://youtu.be/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    # Embed / shorts / live / v.
    ("https://www.youtube.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/shorts/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/live/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    ("https://www.youtube.com/v/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    # youtube-nocookie.
    ("https://www.youtube-nocookie.com/embed/dQw4w9WgXcQ", "dQw4w9WgXcQ"),
    # Watch URL with extra query params (playlist, timestamp).
    (
        "https://www.youtube.com/watch?v=dQw4w9WgXcQ&list=PL1234&t=42s",
        "dQw4w9WgXcQ",
    ),
])
def test_extract_video_id_from_url_shape(url: str, expected: str) -> None:
    assert _extract_video_id(url) == expected


@pytest.mark.parametrize("url", [
    # No video ID at all.
    "https://www.youtube.com/",
    "https://www.youtube.com/channel/UC_abc",
    "https://www.youtube.com/c/SomeCreator",
    "https://www.youtube.com/playlist?list=PL1234",
    # Malformed / not YouTube.
    "https://example.com/watch?v=dQw4w9WgXcQ",
])
def test_extract_video_id_returns_none_for_non_video_urls(url: str) -> None:
    assert _extract_video_id(url) is None


def test_extract_video_id_rejects_garbage_path_after_embed() -> None:
    """Tight regex — only valid 11-char IDs pass."""
    assert _extract_video_id("https://youtube.com/embed/not-a-real-id") is None


# ---- transcript text cleaner -------------------------------------


@dataclass
class _Snip:
    text: str
    start: float = 0.0
    duration: float = 1.0


def test_clean_transcript_text_joins_snippets_with_spaces() -> None:
    snips = [_Snip("Hello world."), _Snip("Second sentence.")]
    assert _clean_transcript_text(snips) == "Hello world. Second sentence."


def test_clean_transcript_text_drops_music_markers() -> None:
    snips = [
        _Snip("[♪♪♪]"),
        _Snip("Verse one line."),
        _Snip("[Music]"),
        _Snip("Verse two line."),
        _Snip("(Applause)"),
    ]
    cleaned = _clean_transcript_text(snips)
    assert "Verse one line. Verse two line." == cleaned
    assert "♪" not in cleaned
    assert "Music" not in cleaned
    assert "Applause" not in cleaned


def test_clean_transcript_text_collapses_internal_whitespace() -> None:
    snips = [_Snip("Line\nwith\nnewlines"), _Snip("and  multiple  spaces")]
    assert _clean_transcript_text(snips) == (
        "Line with newlines and multiple spaces"
    )


def test_clean_transcript_text_drops_empty_snippets() -> None:
    snips = [_Snip(""), _Snip("real text"), _Snip("   ")]
    assert _clean_transcript_text(snips) == "real text"


# ---- happy path ---------------------------------------------------


def _mock_api_returning(snippets: list) -> MagicMock:
    fake_api = MagicMock()
    fake_result = MagicMock()
    fake_result.snippets = snippets
    fake_api.fetch.return_value = fake_result
    api_cls = MagicMock(return_value=fake_api)
    return api_cls


def test_extract_returns_extracted_url_with_transcript() -> None:
    snippets = [
        _Snip("Welcome to the lesson on retrieval augmented generation."),
        _Snip("Chunking strategy matters more than people realize."),
        _Snip("Use sentence-level boundaries when possible."),
    ]
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi",
        _mock_api_returning(snippets),
    ):
        result = extract_youtube_transcript(
            "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
        )
    assert result.url == "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
    assert result.title == "YouTube · dQw4w9WgXcQ"
    assert "retrieval augmented generation" in result.text
    assert "Chunking strategy" in result.text
    assert result.metadata["source"] == "youtube"
    assert result.metadata["video_id"] == "dQw4w9WgXcQ"
    assert result.metadata["transcript_segments"] == 3
    assert result.metadata["extracted_chars"] == len(result.text)


def test_extract_via_fetch_url_routes_youtube_to_extractor() -> None:
    """The K7.x v2 wiring: fetch_url() routes YouTube URLs to
    the new extractor instead of rejecting up-front (the v1
    behavior)."""
    snippets = [_Snip("Hello world this is enough text to pass the 50-char minimum cleanup gate.")]
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi",
        _mock_api_returning(snippets),
    ), patch("httpx.Client") as mock_httpx:
        result = fetch_url("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        # No HTTP roundtrip via trafilatura.
        mock_httpx.assert_not_called()
    assert result.title.startswith("YouTube · ")
    assert "Hello world" in result.text


# ---- error paths --------------------------------------------------


def test_extract_rejects_non_video_url_before_api_call() -> None:
    with patch("youtube_transcript_api.YouTubeTranscriptApi") as api_cls:
        with pytest.raises(UrlFetchError, match="Couldn't extract a YouTube video ID"):
            extract_youtube_transcript("https://www.youtube.com/channel/UC_abc")
        api_cls.assert_not_called()


def test_extract_transcripts_disabled_raises_actionable() -> None:
    from youtube_transcript_api import _errors as yt_errors

    fake_api = MagicMock()
    fake_api.fetch.side_effect = yt_errors.TranscriptsDisabled("vid")
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi",
        return_value=fake_api,
    ):
        with pytest.raises(UrlFetchError, match="transcripts disabled"):
            extract_youtube_transcript(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )


def test_extract_no_transcript_raises_actionable() -> None:
    from youtube_transcript_api import _errors as yt_errors

    fake_api = MagicMock()
    fake_api.fetch.side_effect = yt_errors.NoTranscriptFound(
        "vid", ["en"], MagicMock(),
    )
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi",
        return_value=fake_api,
    ):
        with pytest.raises(UrlFetchError, match="no English transcript"):
            extract_youtube_transcript(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )


def test_extract_video_unavailable_raises_actionable() -> None:
    from youtube_transcript_api import _errors as yt_errors

    fake_api = MagicMock()
    fake_api.fetch.side_effect = yt_errors.VideoUnavailable("vid")
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi",
        return_value=fake_api,
    ):
        with pytest.raises(UrlFetchError, match="unavailable"):
            extract_youtube_transcript(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )


def test_extract_empty_transcript_raises() -> None:
    """Defense in depth — if YouTube returns zero snippets,
    we surface a clear message instead of an empty Asset."""
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi",
        _mock_api_returning([]),
    ):
        with pytest.raises(UrlFetchError, match="empty transcript"):
            extract_youtube_transcript(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )


def test_extract_music_only_video_raises_too_short() -> None:
    """A video that's all music markers cleans up to nothing
    or near-nothing — surface that as too-short rather than
    storing a useless 0-chunk doc."""
    snippets = [_Snip("[♪♪♪]"), _Snip("[Music]"), _Snip("(Applause)")]
    with patch(
        "youtube_transcript_api.YouTubeTranscriptApi",
        _mock_api_returning(snippets),
    ):
        with pytest.raises(UrlFetchError, match="too short"):
            extract_youtube_transcript(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
            )
