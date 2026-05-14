"""SESSION 140 / K7 — url_fetch.py unit tests.

Mocks httpx + trafilatura so tests stay hermetic — no real
network calls. Covers schema validation, size cap, 4xx/5xx
handling, trafilatura empty-extract handling, the
ExtractedUrl shape.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from apps.embeddings.url_fetch import (
    MAX_HTML_BYTES,
    UrlFetchError,
    fetch_url,
)


# ---- URL shape validation ------------------------------------


def test_rejects_non_http_schemes() -> None:
    with pytest.raises(UrlFetchError, match="must use http"):
        fetch_url("ftp://example.com/file.txt")
    with pytest.raises(UrlFetchError, match="must use http"):
        fetch_url("file:///etc/passwd")
    with pytest.raises(UrlFetchError, match="must use http"):
        fetch_url("javascript:alert(1)")


def test_rejects_url_without_host() -> None:
    with pytest.raises(UrlFetchError, match="no host"):
        fetch_url("http:///path-only")


# ---- HTTP error path ------------------------------------


def _mock_response(status_code: int = 200, content: bytes = b"", text: str | None = None):
    r = MagicMock()
    r.status_code = status_code
    r.content = content
    # httpx .text triggers decoding lazily; mock as a property.
    r.text = text if text is not None else content.decode("utf-8", errors="replace")
    return r


def test_4xx_response_raises() -> None:
    with patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = _mock_response(status_code=404)
        with pytest.raises(UrlFetchError, match="404"):
            fetch_url("https://example.com/missing")


def test_5xx_response_raises() -> None:
    with patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = _mock_response(status_code=503)
        with pytest.raises(UrlFetchError, match="503"):
            fetch_url("https://example.com/down")


def test_oversized_response_raises() -> None:
    big = b"<html>" + (b"x" * (MAX_HTML_BYTES + 1)) + b"</html>"
    with patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = _mock_response(status_code=200, content=big)
        with pytest.raises(UrlFetchError, match="exceeded"):
            fetch_url("https://example.com/giant")


def test_httpx_exception_wraps_into_url_fetch_error() -> None:
    import httpx

    with patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.get.side_effect = httpx.ConnectError("DNS failure")
        with pytest.raises(UrlFetchError, match="fetch failed"):
            fetch_url("https://nonexistent.character-os.test/")


# ---- trafilatura path --------------------------------------


def test_successful_extraction_returns_text_and_title() -> None:
    html = b"<html><head><title>Sample</title></head><body><p>Hello world.</p></body></html>"

    fake_doc = MagicMock()
    fake_doc.text = "Hello world."
    fake_doc.title = "Sample Article"
    fake_doc.author = "Jane Doe"
    fake_doc.date = "2026-05-14"
    fake_doc.sitename = "Example"
    fake_doc.hostname = "example.com"

    with patch("httpx.Client") as mock_client, \
         patch("trafilatura.bare_extraction", return_value=fake_doc):
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = _mock_response(status_code=200, content=html)

        result = fetch_url("https://example.com/article")

    assert result.url == "https://example.com/article"
    assert result.title == "Sample Article"
    assert result.text == "Hello world."
    assert result.metadata["author"] == "Jane Doe"
    assert result.metadata["date"] == "2026-05-14"
    assert result.metadata["hostname"] == "example.com"
    assert result.metadata["fetched_chars"] == len(html.decode("utf-8"))
    assert result.metadata["extracted_chars"] == len("Hello world.")


def test_extraction_returns_none_raises_paywall_hint() -> None:
    html = b"<html><body>paywall</body></html>"
    with patch("httpx.Client") as mock_client, \
         patch("trafilatura.bare_extraction", return_value=None):
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = _mock_response(status_code=200, content=html)
        with pytest.raises(UrlFetchError, match="paywall"):
            fetch_url("https://paywall.example.com/article")


def test_extraction_returns_empty_text_raises() -> None:
    html = b"<html><body>x</body></html>"
    fake_doc = MagicMock()
    fake_doc.text = "   "  # whitespace-only
    fake_doc.title = ""
    fake_doc.author = ""
    fake_doc.date = ""
    fake_doc.sitename = ""
    fake_doc.hostname = ""

    with patch("httpx.Client") as mock_client, \
         patch("trafilatura.bare_extraction", return_value=fake_doc):
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = _mock_response(status_code=200, content=html)
        with pytest.raises(UrlFetchError, match="empty text"):
            fetch_url("https://empty.example.com/article")


def test_extraction_with_no_title_falls_back_to_hostname() -> None:
    html = b"<html><body>x</body></html>"
    fake_doc = MagicMock()
    fake_doc.text = "Some content."
    fake_doc.title = None
    fake_doc.author = None
    fake_doc.date = None
    fake_doc.sitename = None
    fake_doc.hostname = "blog.example.com"

    with patch("httpx.Client") as mock_client, \
         patch("trafilatura.bare_extraction", return_value=fake_doc):
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = _mock_response(status_code=200, content=html)
        result = fetch_url("https://blog.example.com/post")

    assert result.title == "blog.example.com"


def test_empty_html_raises() -> None:
    with patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.get.return_value = _mock_response(status_code=200, content=b"   ")
        with pytest.raises(UrlFetchError, match="empty"):
            fetch_url("https://example.com/blank")
