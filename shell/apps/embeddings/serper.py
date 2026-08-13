"""Serper.dev search wrapper — Google search results via API.

SESSION 140 / K7. Operator types a query → ``search(query)``
returns up to N ``{title, url, snippet}`` triples → operator
picks one → SPA POSTs to ``/api/knowledge/`` with that URL
which flows through the same K7 fetch+extract pipeline.

Shape ported from the sibling project's
``core/tools/web_search.py:WebSearchTool._search_text``:

    POST https://google.serper.dev/search
    headers: X-API-KEY: <SERPER_API_KEY>, Content-Type: application/json
    body: {"q": "<query>", "num": <max_results>}
    -> {"organic": [{"title", "link", "snippet"}, ...]}

Caching: Django cache (Redis db 2) keyed by sha256(query)
with 1-hour TTL. The query "what is character os" doesn't
need to hit serper a second time within the hour.

Force-mock: ``SERPER_FORCE_MOCK=1`` env / setting returns
deterministic stub results. Same shape as the three other
force-mocks in shell. No API call, no key required.
"""
from __future__ import annotations

import hashlib
import logging
import os
from dataclasses import asdict, dataclass

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


SERPER_URL = "https://google.serper.dev/search"

# 1-hour cache — search results drift on the order of days, so
# an hour is a reasonable midpoint between freshness and cost.
CACHE_TTL_SECONDS = 60 * 60

DEFAULT_TOP_K = 8
MAX_TOP_K = 20

# Wall-clock cap on the serper call. The API typically returns
# in <1s; 10s catches network blips without being annoying.
TIMEOUT_SECONDS = 10.0


@dataclass(slots=True)
class SearchResult:
    """One serper organic result."""
    title: str
    url: str
    snippet: str
    position: int  # 1-indexed rank within the result set


class SerperError(Exception):
    """Raised on serper API failure. Callers decide whether
    to surface or fall back."""


def _is_force_mock() -> bool:
    """Same shape as the other three force-mocks. Settings
    beats env."""
    settings_flag = getattr(settings, "SERPER_FORCE_MOCK", None)
    if settings_flag is not None:
        return bool(settings_flag)
    env = os.environ.get("SERPER_FORCE_MOCK", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _has_serper_key() -> bool:
    return bool(os.environ.get("SERPER_API_KEY", "").strip())


def _cache_key(query: str, top_k: int) -> str:
    digest = hashlib.sha256(f"{query}|{top_k}".encode("utf-8")).hexdigest()
    return f"serper:{digest}"


def search(query: str, *, top_k: int = DEFAULT_TOP_K) -> list[SearchResult]:
    """Search the web. Returns up to ``top_k`` organic results.

    Args:
        query: the operator's typed search string.
        top_k: max results to return (clamped to MAX_TOP_K).

    Returns:
        List of ``SearchResult``. Empty list when the query
        returned no organic hits.

    Raises:
        ``ValueError`` for empty query / invalid top_k.
        ``SerperError`` when the API call fails AND force-mock
        is not enabled AND no cached result is available.
    """
    query = (query or "").strip()
    if not query:
        raise ValueError("search query must not be empty")
    top_k = max(1, min(int(top_k), MAX_TOP_K))

    if _is_force_mock():
        return _mock_results(query, top_k)

    key = _cache_key(query, top_k)
    cached = cache.get(key)
    if cached is not None:
        # Cache stores the raw dicts; rehydrate the dataclasses.
        return [SearchResult(**r) for r in cached]

    if not _has_serper_key():
        raise SerperError(
            "SERPER_API_KEY is unset. Set the env var, or use "
            "SERPER_FORCE_MOCK=1 for dev determinism."
        )

    results = _call_serper(query, top_k)

    # Cache as plain dicts (Django cache prefers JSON-friendly).
    # ``asdict`` works with ``@dataclass(slots=True)``; ``__dict__``
    # doesn't (slots disable it).
    cache.set(key, [asdict(r) for r in results], CACHE_TTL_SECONDS)
    return results


def _call_serper(query: str, top_k: int) -> list[SearchResult]:
    """Single serper.dev POST. Surfaces failures as ``SerperError``."""
    import httpx

    api_key = os.environ["SERPER_API_KEY"]
    headers = {"X-API-KEY": api_key, "Content-Type": "application/json"}
    payload = {"q": query, "num": top_k}

    try:
        with httpx.Client(timeout=TIMEOUT_SECONDS) as client:
            response = client.post(SERPER_URL, json=payload, headers=headers)
    except httpx.HTTPError as exc:
        logger.warning("serper request failed: %s", exc)
        raise SerperError(f"serper request failed: {exc}") from exc

    if response.status_code >= 400:
        logger.warning(
            "serper API returned %d for query=%r", response.status_code, query,
        )
        raise SerperError(
            f"serper API returned {response.status_code}"
        )

    try:
        body = response.json()
    except ValueError as exc:
        raise SerperError(f"serper returned non-JSON: {exc}") from exc

    organic = body.get("organic") or []
    results: list[SearchResult] = []
    for i, item in enumerate(organic[:top_k], start=1):
        url = (item.get("link") or "").strip()
        if not url:
            continue
        results.append(
            SearchResult(
                title=(item.get("title") or "").strip(),
                url=url,
                snippet=(item.get("snippet") or "").strip(),
                position=i,
            )
        )
    return results


def _mock_results(query: str, top_k: int) -> list[SearchResult]:
    """Deterministic stub results for force-mock mode. The
    query is echoed into the result text so tests can assert
    "the query carried through" without needing real
    network access."""
    digest = hashlib.sha256(query.encode("utf-8")).hexdigest()[:8]
    return [
        SearchResult(
            title=f"Mock result {i} for {query!r}",
            url=f"https://mock.character-os.test/{digest}/result-{i}",
            snippet=f"Synthetic snippet for query {query!r} (rank {i}).",
            position=i,
        )
        for i in range(1, top_k + 1)
    ]
