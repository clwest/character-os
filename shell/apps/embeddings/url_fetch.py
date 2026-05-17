"""URL fetch + main-content extraction via trafilatura.

SESSION 140 / K7. The fetch half of the URL ingestion path:
operator paste OR serper-discovery → ``fetch_url(url)`` →
``ingestion.ingest_url`` → ``embed_document``.

Snapshot semantics per the scope-lock:
> URL freshness contract: snapshot at ingest, never re-fetch.
> If the operator wants fresh, they delete and re-ingest.

So this module's job is to faithfully extract what the URL
returned *at this moment* — no re-fetching, no scheduled
refresh, no following redirects beyond httpx's default 5
redirect ceiling.

What's in scope:
* httpx GET with a realistic user-agent (some sites refuse
  the default python-requests UA)
* trafilatura main-content extraction (strips nav, ads,
  footer, sidebars)
* title + author + date metadata when trafilatura can find them
* size cap (10 MB raw HTML — same as the PDF cap)
* timeout cap (15 s wall-clock)
* known-bad host rejection (YouTube — see K7.x note below)
* boilerplate-signature detection (trafilatura returns
  navigation chrome as "main content" on JS-heavy sites
  that defeat its extractor)

Out of scope (per K7 What's NOT):
* Following links beyond the one URL
* Auto re-fetch
* Site-specific extractors (newspaper, readability fallback)
* Authentication / cookies (no logged-in sites in v1)
* Per-host extractors (YouTube transcript API, oEmbed) —
  deferred to K7.x (the proper-fix path; this slice just
  closes the silent-failure surface)

K7.x (SESSION 174) — YouTube ingest fix
========================================
SESSION 173's MEMORY entry + SESSION 174's real-mode
embedding dogfood both confirmed: trafilatura on a YouTube
URL returns the page's navigation boilerplate ("About Press
Copyright Contact us Creators Advertise Developers Terms
Privacy Policy & Safety How YouTube works…") as
"main content" instead of any video metadata. The resulting
single short generic chunk pollutes semantic retrieval
across the entire workspace — distance ~0.85 to almost any
query because nav-text is generic enough to be semantically
close to everything.

Two complementary defenses landed this slice:

1. **Host-based rejection.** Any youtube.com / m.youtube.com /
   youtu.be / youtube-nocookie.com URL is rejected up-front
   with an operator-actionable error before any HTTP request
   fires. Saves the wasted roundtrip + makes the failure
   path identical to other always-rejects (file://, etc.)
   Operators paste the transcript or description instead.

2. **Boilerplate signature detection.** Post-extraction, if
   the cleaned text matches a known nav-boilerplate
   signature (e.g. the "About Press Copyright Contact us
   Creators Advertise" sequence), reject as a generic
   extraction-failure-with-noise. Catches future host
   classes that fool trafilatura the same way.

When the proper YouTube extractor lands (K7.x v2), the
host-rejection layer flips to "route to youtube_extractor"
instead of raising. Boilerplate detection stays as a safety
net for other JS-heavy sites.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

logger = logging.getLogger(__name__)


# Reasonable wall-clock caps. trafilatura itself is fast (<1s
# for typical pages); the network round-trip dominates.
FETCH_TIMEOUT_SECONDS = 15.0

# Match the PDF cap from K3 — 10 MB of raw HTML before we
# bail. A real article fits in <500 KB; anything bigger is
# almost certainly a dump page, not content.
MAX_HTML_BYTES = 10 * 1024 * 1024

# Be a polite citizen — identify as a browser-shaped UA so
# sites that block python-requests / curl don't 403 us, but
# don't lie about who we are.
USER_AGENT = (
    "Mozilla/5.0 (compatible; CharacterOS-Bot/1.0; "
    "+https://github.com/clwest/character-os)"
)


# K7.x (SESSION 174) — known-bad hosts that defeat trafilatura.
# Match the parsed netloc lowercased, optionally with a leading
# subdomain ("www." / "m." / "music."). Membership check uses
# endswith on a normalised host to allow forward-compat with
# Shorts / Music / mobile variants.
_YOUTUBE_HOSTS: frozenset[str] = frozenset({
    "youtube.com",
    "youtu.be",
    "youtube-nocookie.com",
})


def _is_youtube_url(parsed) -> bool:
    """True when ``parsed.netloc`` is any YouTube property.

    Strips leading subdomain (``www.``, ``m.``, ``music.``)
    and checks against the host frozenset. Forward-compatible
    with new YouTube subdomains (Shorts, Studio, Music)
    because the check is on the registrable domain suffix,
    not the exact host.
    """
    host = (parsed.netloc or "").lower().strip()
    if not host:
        return False
    # Strip user@ if present + port if present.
    host = host.rsplit("@", 1)[-1].split(":", 1)[0]
    # Endswith ensures every subdomain variant matches.
    return any(host == h or host.endswith("." + h) for h in _YOUTUBE_HOSTS)


# K7.x — boilerplate signature. The verbatim opening of the
# YouTube nav-footer sequence trafilatura extracts when it
# can't find real article content. Match is substring,
# case-insensitive, and intentionally specific so we don't
# false-positive on legitimate articles that happen to
# mention any individual word.
_BOILERPLATE_SIGNATURES: tuple[re.Pattern[str], ...] = (
    # YouTube nav-bar. Six consecutive footer terms is a very
    # high-confidence signal that extraction returned chrome,
    # not content.
    re.compile(
        r"about\s+press\s+copyright\s+contact\s+us\s+creators",
        re.IGNORECASE,
    ),
)


def _looks_like_boilerplate(text: str) -> bool:
    """Heuristic: does ``text`` look like extracted page chrome
    instead of main content?

    v1 checks a small frozenset of high-confidence signatures.
    Each signature is a short verbatim sequence that only
    appears in well-known nav / footer blocks, never in real
    article prose. Adding a signature here is cheap (one
    regex); the cost is operator-curation drift, same shape
    as KNOWN_TECH_TERMS in the verifier.
    """
    if not text:
        return False
    return any(p.search(text) for p in _BOILERPLATE_SIGNATURES)


@dataclass(slots=True)
class ExtractedUrl:
    """Result of a URL fetch + extraction."""

    url: str
    title: str
    text: str
    metadata: dict = field(default_factory=dict)
    """Free-form: trafilatura author, date, sitename, hostname.
    Goes into ``KnowledgeDocument.source_metadata``."""


class UrlFetchError(Exception):
    """Raised when fetch or extraction fails. Callers turn this
    into a clean 400 for the operator."""


def fetch_url(url: str, *, timeout: float = FETCH_TIMEOUT_SECONDS) -> ExtractedUrl:
    """Fetch ``url`` and extract its main content.

    Args:
        url: an HTTP(S) URL. Anything else (file://, ftp://, ...)
            is rejected up front.
        timeout: wall-clock cap in seconds.

    Returns:
        ``ExtractedUrl`` with the cleaned text + metadata.

    Raises:
        ``UrlFetchError`` for any of:
        * malformed URL or non-http(s) scheme
        * connection / DNS / TLS failure
        * 4xx / 5xx response
        * response body > ``MAX_HTML_BYTES``
        * trafilatura returns no usable text (likely a
          paywall, login wall, or pure-JS app — operator
          should paste content instead)
    """
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise UrlFetchError(
            f"URL must use http or https, got {parsed.scheme!r}"
        )
    if not parsed.netloc:
        raise UrlFetchError(f"URL has no host: {url!r}")

    # K7.x v2 (SESSION 175) — YouTube URLs route to the
    # dedicated transcript extractor instead of trafilatura.
    # v1 (SESSION 174) rejected up-front because trafilatura
    # only returned nav-bar boilerplate; v2 actually ingests
    # the video by pulling captions via youtube-transcript-api.
    # The extractor raises UrlFetchError with operator-actionable
    # messages for the failure modes that trafilatura can't
    # work around either (transcripts disabled, age-gated,
    # IP-blocked, etc.) — same UX shape as before, just with
    # a working happy path.
    if _is_youtube_url(parsed):
        from .youtube_extractor import extract_youtube_transcript
        return extract_youtube_transcript(url)

    html = _fetch(url, timeout=timeout)
    return _extract(url, html)


def _fetch(url: str, *, timeout: float) -> str:
    """Single httpx GET. Surfaces 4xx/5xx as ``UrlFetchError``."""
    # Lazily imported — httpx is in the deps; this keeps the
    # module importable for tests that mock everything.
    import httpx

    try:
        with httpx.Client(
            headers={"User-Agent": USER_AGENT},
            timeout=timeout,
            follow_redirects=True,
        ) as client:
            response = client.get(url)
    except httpx.HTTPError as exc:
        raise UrlFetchError(f"fetch failed: {exc}") from exc

    if response.status_code >= 400:
        raise UrlFetchError(
            f"server returned {response.status_code} for {url}"
        )

    # Size guard — read response bytes, then decode.
    raw = response.content
    if len(raw) > MAX_HTML_BYTES:
        raise UrlFetchError(
            f"response body exceeded {MAX_HTML_BYTES // (1024*1024)} MB "
            f"(got {len(raw) // (1024*1024)} MB)"
        )

    # httpx already does charset detection; .text gives a
    # decoded str. Fall back to utf-8 with replacement when
    # decoding fails (better than raising; trafilatura will
    # still try to extract).
    try:
        return response.text
    except UnicodeDecodeError:
        return raw.decode("utf-8", errors="replace")


def _extract(url: str, html: str) -> ExtractedUrl:
    """Run trafilatura over the fetched HTML."""
    import trafilatura

    if not html.strip():
        raise UrlFetchError("response body was empty")

    # bare_extraction returns a dict-ish Document object with
    # both text and metadata. Falls back to None on extraction
    # failure (typical for paywalls + login walls + pure-JS).
    extracted = trafilatura.bare_extraction(
        html,
        url=url,
        include_comments=False,
        include_tables=True,
        include_links=False,
        favor_recall=False,
        with_metadata=True,
    )

    if extracted is None:
        raise UrlFetchError(
            "trafilatura returned no content — likely a paywall, "
            "login wall, or pure-JS app. Paste the content "
            "directly instead."
        )

    # bare_extraction returns either a dict (older versions)
    # or a Document dataclass (newer). Handle both.
    text = _get_attr(extracted, "text", "")
    if not text or not text.strip():
        raise UrlFetchError(
            "extraction yielded empty text — same caveat as the "
            "no-content case above."
        )

    # K7.x (SESSION 174) — boilerplate-only catch. Some sites
    # defeat trafilatura's content/chrome heuristic and return
    # page chrome as "main content" — a short generic block
    # that looks valid but pollutes retrieval across the
    # workspace. Reject with the same actionable advice as the
    # paywall path.
    if _looks_like_boilerplate(text):
        raise UrlFetchError(
            "extraction returned page navigation / footer "
            "content, not the article body. This typically "
            "means the site renders content via JavaScript or "
            "blocks the extractor. Paste the content directly "
            "as text instead."
        )

    title = _get_attr(extracted, "title", "") or _hostname(url)

    metadata = {
        "author": _get_attr(extracted, "author", "") or "",
        "date": _get_attr(extracted, "date", "") or "",
        "sitename": _get_attr(extracted, "sitename", "") or "",
        "hostname": _get_attr(extracted, "hostname", "") or _hostname(url),
        "fetched_chars": len(html),
        "extracted_chars": len(text),
    }
    # Drop empties so source_metadata stays tidy.
    metadata = {k: v for k, v in metadata.items() if v != ""}

    return ExtractedUrl(url=url, title=title, text=text, metadata=metadata)


def _get_attr(obj, name: str, default=None):
    """Trafilatura's bare_extraction returns either a dict or
    a dataclass depending on version. This handles both."""
    if isinstance(obj, dict):
        return obj.get(name, default)
    return getattr(obj, name, default)


def _hostname(url: str) -> str:
    return urlparse(url).netloc or url
