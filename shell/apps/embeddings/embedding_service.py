"""Embedding service — turns text into 1536-dim vectors.

SESSION 138 / K3. The service is the single chokepoint for
all ``text-embedding-3-small`` calls in shell. Three reasons
the chokepoint matters:

1. **Cost.** Redis-cached by ``sha256(text)`` so identical
   text is embedded exactly once across the workspace's
   lifetime (cache TTL = 30 days; see ``CACHES`` in
   ``character_os/settings.py``).
2. **Determinism in tests + dev.** ``EMBEDDING_FORCE_MOCK=1``
   (env var) or settings ``EMBEDDING_FORCE_MOCK=True``
   short-circuits the OpenAI call and returns a deterministic
   pseudo-vector derived from ``sha256(text)``. Mirrors the
   ``RUNWAY_FORCE_MOCK`` pattern in media-engine.
3. **Cost telemetry.** Every embed call returns the actual
   USD cost in micros so callers (``tasks.embed_document``)
   can persist it onto ``KnowledgeChunk.embedding_cost_micros``.

The mock path returns vectors that are deterministic but
**not** semantically meaningful. They satisfy the type
contract (1536 floats summing to a unit-ish vector) and let
ingestion + retrieval pipelines run end-to-end without
burning OpenAI credits. Real-mode is for production +
operator workflows where actual semantic search matters.
"""
from __future__ import annotations

import hashlib
import logging
import os
import time
from dataclasses import dataclass

from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


# Locked v1 model + dimension (scope-lock §"Out of scope" —
# multi-model embedding is a re-embed-all event we defer).
EMBEDDING_MODEL = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536

# ``text-embedding-3-small`` pricing as of K3 ship date:
# $0.02 per 1M tokens. 1 token ≈ 4 chars (English). Convert to
# micros per character so cost telemetry stays in integers.
#
#   $0.02 / 1_000_000 tokens × 1 token / 4 chars
#     = $0.000_000_005 / char
#     = 0.005 micros / char  (1 USD = 1_000_000 micros)
#
# Stored per-chunk in ``KnowledgeChunk.embedding_cost_micros``.
COST_MICROS_PER_CHAR = 0.005


@dataclass(slots=True)
class EmbedResult:
    """One embed call's result. ``cached`` is True when the
    vector came from Redis rather than OpenAI; cost is 0 in
    that case."""

    vector: list[float]
    model: str
    dimension: int
    cost_micros: int
    cached: bool
    elapsed_ms: int


def _is_force_mock() -> bool:
    """``EMBEDDING_FORCE_MOCK=1`` env or Django settings.

    Same shape as the ``RUNWAY_FORCE_MOCK`` override in
    media-engine. Settings beats env so a runtime ``override_settings``
    in tests wins."""
    settings_flag = getattr(settings, "EMBEDDING_FORCE_MOCK", None)
    if settings_flag is not None:
        return bool(settings_flag)
    env = os.environ.get("EMBEDDING_FORCE_MOCK", "").strip().lower()
    return env in {"1", "true", "yes", "on"}


def _is_real_mode_possible() -> bool:
    """Returns True if a real OpenAI call could succeed —
    ``OPENAI_API_KEY`` is set and force-mock is not enabled."""
    if _is_force_mock():
        return False
    key = os.environ.get("OPENAI_API_KEY", "").strip()
    return bool(key)


def _cache_key(text: str) -> str:
    """``char_os_embed:<model>:<sha256-of-text>`` — the
    namespace prefix is handled by Django's CACHES config."""
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return f"{EMBEDDING_MODEL}:{digest}"


def _deterministic_mock_vector(text: str) -> list[float]:
    """Hash the text into a deterministic 1536-dim vector.

    Each chunk of 4 hash hex chars (16 bits = 65,536 values)
    maps to one float in roughly ``[-1, 1]``. Same text →
    same vector. Different text → different vector. **Not**
    semantically meaningful — use this for ingestion +
    retrieval shape testing, not for relevance evaluation.
    """
    seed = hashlib.sha256(text.encode("utf-8")).digest()
    # We need 1536 floats. Each float costs 2 bytes of hash.
    # 1536 × 2 = 3072 bytes. sha256 emits 32 bytes, so we
    # cycle the digest as a keystream.
    vec: list[float] = []
    i = 0
    while len(vec) < EMBEDDING_DIMENSION:
        a = seed[i % len(seed)]
        b = seed[(i + 1) % len(seed)]
        # Map two bytes into one signed-ish float in [-1, 1].
        as_int = (a << 8) | b
        vec.append((as_int - 32768) / 32768.0)
        i += 2
    return vec


def _real_embed(text: str) -> list[float]:
    """Call OpenAI ``text-embedding-3-small`` and return the
    raw vector. Raises if the API key is missing or the call
    fails; callers decide whether to surface or swallow."""
    from openai import OpenAI

    client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
    resp = client.embeddings.create(model=EMBEDDING_MODEL, input=text)
    return list(resp.data[0].embedding)


def embed(text: str) -> EmbedResult:
    """Embed one piece of text. Real-mode results cached by
    ``sha256(text)`` for 30 days. ``EMBEDDING_FORCE_MOCK=1``
    short-circuits to a deterministic pseudo-vector and
    **bypasses the cache entirely** — both read and write.

    The cache-bypass is load-bearing: pre-SESSION-214, mock
    and real shared the cache key, so a mock-mode run would
    poison subsequent real-mode reads (vectors looked cached,
    cost reported $0, but the floats were the deterministic
    hash garbage). Since the mock path is already deterministic
    from ``sha256(text)``, caching it buys nothing — recompute
    is microseconds. Skipping the cache eliminates the
    cross-mode collision by construction.

    Raises ``ValueError`` if ``text`` is empty or whitespace-
    only — embedding empty strings is always a bug.
    Raises ``RuntimeError`` if real-mode is requested
    (no force-mock) but ``OPENAI_API_KEY`` is unset.
    """
    if not text or not text.strip():
        raise ValueError("Cannot embed empty text")

    started = time.perf_counter()

    # Mock mode: skip cache entirely so we cannot poison real
    # reads. Vector is already deterministic from sha256(text).
    if _is_force_mock():
        vec = _deterministic_mock_vector(text)
        return EmbedResult(
            vector=vec,
            model=f"{EMBEDDING_MODEL} (mock)",
            dimension=EMBEDDING_DIMENSION,
            cost_micros=0,
            cached=False,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    key = _cache_key(text)
    cached = cache.get(key)
    if cached is not None:
        return EmbedResult(
            vector=cached,
            model=EMBEDDING_MODEL,
            dimension=EMBEDDING_DIMENSION,
            cost_micros=0,
            cached=True,
            elapsed_ms=int((time.perf_counter() - started) * 1000),
        )

    if not _is_real_mode_possible():
        raise RuntimeError(
            "Real-mode embedding requested but OPENAI_API_KEY is unset. "
            "Set OPENAI_API_KEY in the environment OR set "
            "EMBEDDING_FORCE_MOCK=1 for deterministic dev/test vectors."
        )

    try:
        vec = _real_embed(text)
    except Exception:
        logger.exception("OpenAI embedding call failed for text len=%d", len(text))
        raise

    cache.set(key, vec)
    cost_micros = max(1, round(len(text) * COST_MICROS_PER_CHAR))
    return EmbedResult(
        vector=vec,
        model=EMBEDDING_MODEL,
        dimension=EMBEDDING_DIMENSION,
        cost_micros=cost_micros,
        cached=False,
        elapsed_ms=int((time.perf_counter() - started) * 1000),
    )
