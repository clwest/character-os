"""SESSION 140 / K7 — serper.py unit tests.

Covers the three operating modes:
  * Force-mock returns deterministic SearchResult stubs.
  * Real mode hits ``google.serper.dev/search`` (mocked).
  * Cache hit avoids the API call on the second request.

Plus error paths: missing query, missing API key, 4xx/5xx
upstream response.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.core.cache import cache
from django.test import override_settings

from apps.embeddings.serper import (
    DEFAULT_TOP_K,
    SerperError,
    search,
)


pytestmark = pytest.mark.django_db  # uses Django cache


# ---- force-mock path ----------------------------------------


@override_settings(SERPER_FORCE_MOCK=True)
def test_force_mock_returns_deterministic_results() -> None:
    cache.clear()
    results = search("character os", top_k=3)
    assert len(results) == 3
    for i, r in enumerate(results, start=1):
        assert r.position == i
        assert "character os" in r.title
        assert r.url.startswith("https://mock.character-os.test/")
        assert "character os" in r.snippet


@override_settings(SERPER_FORCE_MOCK=True)
def test_force_mock_top_k_clamps() -> None:
    cache.clear()
    results = search("anything", top_k=999)
    # Clamped to MAX_TOP_K = 20
    assert len(results) == 20


@override_settings(SERPER_FORCE_MOCK=True)
def test_force_mock_same_query_returns_same_results() -> None:
    cache.clear()
    a = search("deterministic", top_k=2)
    b = search("deterministic", top_k=2)
    # The deterministic URL hash means same input → same output
    assert a[0].url == b[0].url


# ---- input validation --------------------------------------


@override_settings(SERPER_FORCE_MOCK=True)
def test_empty_query_raises() -> None:
    with pytest.raises(ValueError):
        search("")
    with pytest.raises(ValueError):
        search("   ")


# ---- real-mode (mocked httpx) -------------------------------


def test_real_mode_without_key_raises() -> None:
    """When force-mock is OFF and no cache hit and no API key,
    the function must raise rather than fall back silently."""
    import os

    cache.clear()
    old_key = os.environ.pop("SERPER_API_KEY", None)
    try:
        with override_settings(SERPER_FORCE_MOCK=False):
            with pytest.raises(SerperError, match="SERPER_API_KEY is unset"):
                search("unkeyed query", top_k=3)
    finally:
        if old_key is not None:
            os.environ["SERPER_API_KEY"] = old_key


def _mock_serper_response(status_code: int, body: dict | None = None) -> MagicMock:
    r = MagicMock()
    r.status_code = status_code
    r.json.return_value = body or {}
    return r


def test_real_mode_success() -> None:
    import os

    cache.clear()
    fake_response = _mock_serper_response(200, {
        "organic": [
            {"title": "Title 1", "link": "https://a.example.com/1", "snippet": "snip 1"},
            {"title": "Title 2", "link": "https://b.example.com/2", "snippet": "snip 2"},
            # Empty link should be filtered out
            {"title": "Title 3", "link": "", "snippet": "snip 3"},
        ],
    })

    with override_settings(SERPER_FORCE_MOCK=False), \
         patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}), \
         patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.post.return_value = fake_response

        results = search("real query", top_k=5)

    assert len(results) == 2  # third one had empty link
    assert results[0].title == "Title 1"
    assert results[0].url == "https://a.example.com/1"
    assert results[0].position == 1
    assert results[1].position == 2


def test_real_mode_http_error_raises_serper_error() -> None:
    import os

    cache.clear()
    fake_response = _mock_serper_response(403)

    with override_settings(SERPER_FORCE_MOCK=False), \
         patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}), \
         patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.post.return_value = fake_response

        with pytest.raises(SerperError, match="403"):
            search("forbidden", top_k=3)


def test_real_mode_connection_error_raises_serper_error() -> None:
    import os

    import httpx

    cache.clear()
    with override_settings(SERPER_FORCE_MOCK=False), \
         patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}), \
         patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.post.side_effect = httpx.ConnectError("network is down")

        with pytest.raises(SerperError, match="fail"):
            search("net broken", top_k=3)


# ---- cache hit -----------------------------------------------


def test_cache_hit_skips_api_call() -> None:
    import os

    cache.clear()
    fake_response = _mock_serper_response(200, {
        "organic": [{"title": "T", "link": "https://x.test/", "snippet": "S"}],
    })

    with override_settings(SERPER_FORCE_MOCK=False), \
         patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}), \
         patch("httpx.Client") as mock_client:
        instance = mock_client.return_value.__enter__.return_value
        instance.post.return_value = fake_response

        # First call hits API
        first = search("cached query", top_k=5)
        # Second call must NOT hit API
        instance.post.reset_mock()
        second = search("cached query", top_k=5)
        instance.post.assert_not_called()

    assert first[0].url == second[0].url
    assert second[0].position == 1
