"""YouTube transcript extractor — K7.x v2 (SESSION 175).

Replaces the K7.x v1 up-front rejection (SESSION 174) of
YouTube URLs in ``url_fetch.fetch_url``. v1 caught the
silent-failure mode where trafilatura returned YouTube's
nav-bar boilerplate ("About Press Copyright Contact us
Creators…") as "main content" — chunks were short, generic,
and polluted retrieval at distance ~0.85 across the entire
workspace. v1 fixed it by rejecting up-front with an
operator-actionable error ("Paste the transcript directly").

v2 makes the URL actually ingestable: route YouTube URLs to
``youtube-transcript-api`` (already a project dep), pull the
captions, concatenate snippets into prose, return as an
``ExtractedUrl`` shape the existing ingestion path consumes.

What's in scope:

* Video ID extraction from every reasonable YouTube URL
  variant (watch?v= / youtu.be/ID / embed/ID / shorts/ID /
  m.youtube.com / music.youtube.com / youtube-nocookie.com).
* English transcript fetch via ``YouTubeTranscriptApi.fetch``.
* Snippet concatenation with light cleanup (collapse
  whitespace, drop pure-music markers like "[♪♪♪]" / "[Music]"
  that don't carry semantic content).
* Operator-actionable errors for the common failure modes:
  transcripts disabled, no English transcript, video private/
  unavailable, age-gated, IP-blocked.
* Snapshot semantics (per K7 scope-lock): one fetch at ingest,
  never re-fetched.

What's out of scope (queued for v3 if operators ask):

* Title fetch via oEmbed — for v2 the title falls back to
  ``f"YouTube · {video_id}"``. Operator renames via the doc
  title field after ingest.
* Multi-language preference. v2 fetches English only.
* Timestamps in the extracted text. Snippets carry start +
  duration but we drop them; the embedding pipeline chunks by
  character count, not time.
* Channel / author metadata.
"""
from __future__ import annotations

import logging
import re
from typing import Any
from urllib.parse import parse_qs, urlparse

from .url_fetch import ExtractedUrl, UrlFetchError

logger = logging.getLogger(__name__)


# YouTube video IDs are exactly 11 chars, base64url-ish
# (alphanumeric, hyphen, underscore). Tighter than just
# "anything in the path" so we reject garbage paths cleanly.
_VIDEO_ID_RE = re.compile(r"^[A-Za-z0-9_-]{11}$")


# Hosts the extractor recognises. Defense in depth — fetch_url's
# _is_youtube_url already gates calls, but a direct call to
# extract_video_id with a non-YouTube URL would otherwise happily
# pluck the ``v`` query param off, say, an example.com/watch URL.
_KNOWN_HOSTS: frozenset[str] = frozenset({
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
})


def _extract_video_id(url: str) -> str | None:
    """Pull the video ID out of any reasonable YouTube URL shape.

    Returns the 11-char video ID or ``None`` when the URL
    doesn't carry one (e.g. a channel page, a playlist with
    no ``v`` query param, a malformed URL) OR the URL host
    isn't a recognised YouTube property.

    Handles:
      * ``youtube.com/watch?v=ID`` (also ``m.``, ``music.``)
      * ``youtu.be/ID``
      * ``youtube.com/embed/ID``
      * ``youtube.com/shorts/ID``
      * ``youtube.com/live/ID``
      * ``youtube-nocookie.com/embed/ID``
    """
    parsed = urlparse(url)
    host = (parsed.netloc or "").lower().split(":", 1)[0]
    path = parsed.path or ""

    # Defense in depth — reject any host that isn't a known
    # YouTube property. Caller should already have routed only
    # YouTube URLs here, but plucking ``v=ID`` from an
    # arbitrary host would silently misclassify.
    if not any(host == h or host.endswith("." + h) for h in _KNOWN_HOSTS):
        return None

    # youtu.be short URL: path IS the video id.
    if host.endswith("youtu.be"):
        candidate = path.strip("/").split("/", 1)[0]
        return candidate if _VIDEO_ID_RE.match(candidate) else None

    # Path-based variants: /embed/ID, /shorts/ID, /live/ID, /v/ID.
    parts = [p for p in path.split("/") if p]
    if len(parts) >= 2 and parts[0] in {"embed", "shorts", "live", "v"}:
        candidate = parts[1]
        return candidate if _VIDEO_ID_RE.match(candidate) else None

    # Standard watch URL: ?v=ID.
    if path == "/watch" or path == "/watch/":
        v = parse_qs(parsed.query).get("v", [""])[0]
        return v if _VIDEO_ID_RE.match(v) else None

    return None


# Pure-music snippets that auto-captioning emits. Dropping
# them before concatenation gets us cleaner text for chunking;
# they carry no semantic content for retrieval.
_MUSIC_MARKER_RE = re.compile(
    r"^\s*[\[\(](?:music|♪+|applause|laughter|inaudible)[\]\)]\s*$",
    re.IGNORECASE,
)


def _clean_transcript_text(snippets: list[Any]) -> str:
    """Concatenate snippet texts into a single prose blob.

    Drops pure-music / applause markers, collapses runs of
    internal whitespace, and joins with single spaces so the
    text-splitter can chunk on sentence boundaries.
    """
    pieces: list[str] = []
    for snip in snippets:
        text = (getattr(snip, "text", "") or "").strip()
        if not text:
            continue
        if _MUSIC_MARKER_RE.match(text):
            continue
        # Replace internal newlines (some captions embed them)
        # with spaces — chunker handles sentence boundaries.
        pieces.append(re.sub(r"\s+", " ", text))
    return " ".join(pieces).strip()


def extract_youtube_transcript(url: str) -> ExtractedUrl:
    """Fetch + extract a YouTube video's transcript as
    ``ExtractedUrl``.

    Args:
        url: any reasonable YouTube URL shape (see
            ``_extract_video_id``).

    Returns:
        ``ExtractedUrl`` carrying the concatenated transcript
        text + metadata (video_id, transcript_segments,
        extracted_chars).

    Raises:
        ``UrlFetchError`` for any of:
        * URL doesn't contain a video ID (e.g. channel page)
        * Transcripts disabled for the video
        * No English transcript available
        * Video is private / deleted / region-blocked
        * Video requires age-gate / login
        * Network failure talking to YouTube
        * Transcript came back empty after cleanup
    """
    # Lazy import — keeps the module-level import graph cheap
    # for non-YouTube ingestion paths.
    from youtube_transcript_api import (
        YouTubeTranscriptApi,
        _errors as yt_errors,
    )

    video_id = _extract_video_id(url)
    if not video_id:
        raise UrlFetchError(
            f"Couldn't extract a YouTube video ID from {url!r}. "
            "URL must point at a single video (watch, shorts, "
            "embed, or youtu.be link), not a channel or playlist."
        )

    api = YouTubeTranscriptApi()
    try:
        result = api.fetch(video_id, languages=("en",))
    except yt_errors.TranscriptsDisabled as exc:
        raise UrlFetchError(
            f"YouTube video {video_id} has transcripts disabled "
            "by the uploader. Paste the description or your own "
            "notes directly as text instead."
        ) from exc
    except yt_errors.NoTranscriptFound as exc:
        raise UrlFetchError(
            f"YouTube video {video_id} has no English transcript "
            "available. Paste your own notes directly as text "
            "instead."
        ) from exc
    except yt_errors.VideoUnavailable as exc:
        raise UrlFetchError(
            f"YouTube video {video_id} is unavailable — likely "
            "private, deleted, or region-blocked."
        ) from exc
    except yt_errors.VideoUnplayable as exc:
        raise UrlFetchError(
            f"YouTube video {video_id} can't be played — likely "
            "members-only or otherwise restricted."
        ) from exc
    except yt_errors.AgeRestricted as exc:
        raise UrlFetchError(
            f"YouTube video {video_id} is age-restricted and "
            "requires login. Paste the transcript directly "
            "instead."
        ) from exc
    except (yt_errors.IpBlocked, yt_errors.RequestBlocked) as exc:
        raise UrlFetchError(
            f"YouTube blocked the transcript fetch for {video_id}. "
            "This usually means YouTube is rate-limiting the "
            "server's IP. Try again later, or paste the "
            "transcript directly."
        ) from exc
    except yt_errors.PoTokenRequired as exc:
        raise UrlFetchError(
            f"YouTube requires a PO token for {video_id} — "
            "transcript fetch isn't possible without browser "
            "auth. Paste the transcript directly."
        ) from exc
    except yt_errors.CouldNotRetrieveTranscript as exc:
        # Catch-all for other transcript-retrieval failures.
        raise UrlFetchError(
            f"YouTube transcript fetch failed for {video_id}: "
            f"{exc!s}"
        ) from exc
    except Exception as exc:  # noqa: BLE001
        # Network / unexpected. Wrap with a clean operator
        # message; the original exception chains via ``from``.
        logger.exception(
            "youtube_extractor unexpected error video_id=%s",
            video_id,
        )
        raise UrlFetchError(
            f"YouTube transcript fetch failed for {video_id} "
            f"(unexpected: {type(exc).__name__})"
        ) from exc

    snippets = list(getattr(result, "snippets", None) or [])
    if not snippets:
        raise UrlFetchError(
            f"YouTube returned an empty transcript for {video_id}."
        )

    text = _clean_transcript_text(snippets)
    if not text or len(text) < 50:
        raise UrlFetchError(
            f"YouTube transcript for {video_id} was too short "
            f"after cleanup ({len(text)} chars). Likely a "
            "music-only or near-silent video."
        )

    metadata = {
        "source": "youtube",
        "video_id": video_id,
        "transcript_segments": len(snippets),
        "extracted_chars": len(text),
        "hostname": (urlparse(url).netloc or "").lower(),
    }

    logger.info(
        "youtube transcript extracted video_id=%s segments=%d chars=%d",
        video_id, len(snippets), len(text),
    )

    return ExtractedUrl(
        url=url,
        # K7.x v2 default title — operator-renamable post-ingest.
        # v3 could call YouTube oEmbed for the real video title.
        title=f"YouTube · {video_id}",
        text=text,
        metadata=metadata,
    )
