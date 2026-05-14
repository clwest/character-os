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

Out of scope (per K7 What's NOT):
* Following links beyond the one URL
* Auto re-fetch
* Site-specific extractors (newspaper, readability fallback)
* Authentication / cookies (no logged-in sites in v1)
"""
from __future__ import annotations

import logging
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
