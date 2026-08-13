"""Unit tests for the embedding service — focuses on the
mock path and the cache, since real-mode is OpenAI and tested
manually via ``--real`` on the smoke command."""
from __future__ import annotations

import os

import pytest
from django.test import override_settings

from apps.embeddings.embedding_service import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL,
    embed,
)


@pytest.mark.django_db  # uses the cache, which is fine via Redis
def test_embed_empty_text_raises() -> None:
    with override_settings(EMBEDDING_FORCE_MOCK=True):
        with pytest.raises(ValueError):
            embed("")
        with pytest.raises(ValueError):
            embed("   \n   ")


@pytest.mark.django_db
def test_mock_vector_shape_and_determinism() -> None:
    with override_settings(EMBEDDING_FORCE_MOCK=True):
        from django.core.cache import cache

        cache.clear()
        r1 = embed("hello character os")
        r2 = embed("hello character os")

    assert r1.dimension == EMBEDDING_DIMENSION
    assert len(r1.vector) == EMBEDDING_DIMENSION
    assert r1.cost_micros == 0  # mock-mode is free
    assert "mock" in r1.model
    # Same text → same vector via deterministic hash, not cache.
    assert r1.vector == r2.vector
    # Mock-mode bypasses the cache entirely (SESSION 214 fix for
    # cross-mode key collision) — every call recomputes.
    assert r1.cached is False
    assert r2.cached is False


@pytest.mark.django_db
def test_mock_does_not_poison_real_mode_cache() -> None:
    """Regression test for the SESSION 214 cache-collision bug.

    Pre-fix: mock-mode wrote vectors under ``{model}:{sha256}``;
    a subsequent real-mode call for the same text would return
    the mock vector from cache silently (``cached=True``,
    ``cost_micros=0``, but the floats are hash garbage).

    Post-fix: mock-mode bypasses the cache. After a mock embed
    of text X, real-mode for the same X must not see a cached
    value — it must take the real path (and here, raise because
    no OPENAI_API_KEY is set)."""
    from django.core.cache import cache

    text = "collision-canary text — SESSION 214 regression"

    # Step 1: embed in mock mode.
    with override_settings(EMBEDDING_FORCE_MOCK=True):
        cache.clear()
        mock_result = embed(text)
        assert "mock" in mock_result.model
        assert mock_result.cached is False

    # Step 2: cache must contain nothing for this text.
    from apps.embeddings.embedding_service import _cache_key
    assert cache.get(_cache_key(text)) is None, (
        "Mock-mode leaked a vector into the cache — "
        "this would poison real-mode reads."
    )

    # Step 3: real-mode (no API key) must refuse rather than
    # silently return the mock vector.
    with override_settings(EMBEDDING_FORCE_MOCK=False):
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        old_env_mock = os.environ.pop("EMBEDDING_FORCE_MOCK", None)
        try:
            with pytest.raises(RuntimeError):
                embed(text)
        finally:
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key
            if old_env_mock is not None:
                os.environ["EMBEDDING_FORCE_MOCK"] = old_env_mock


@pytest.mark.django_db
def test_mock_different_text_yields_different_vectors() -> None:
    with override_settings(EMBEDDING_FORCE_MOCK=True):
        from django.core.cache import cache

        cache.clear()
        a = embed("alpha text").vector
        b = embed("beta text").vector

    assert a != b


@pytest.mark.django_db
def test_real_mode_without_key_raises() -> None:
    """When force-mock is off and no OPENAI_API_KEY is set,
    the service must refuse rather than fall back silently —
    silent fallback would mask production misconfig."""
    # Ensure force-mock is off in settings AND env
    with override_settings(EMBEDDING_FORCE_MOCK=False):
        old_key = os.environ.pop("OPENAI_API_KEY", None)
        old_env_mock = os.environ.pop("EMBEDDING_FORCE_MOCK", None)
        try:
            from django.core.cache import cache

            cache.clear()
            with pytest.raises(RuntimeError):
                embed("would burn tokens if it worked")
        finally:
            if old_key is not None:
                os.environ["OPENAI_API_KEY"] = old_key
            if old_env_mock is not None:
                os.environ["EMBEDDING_FORCE_MOCK"] = old_env_mock


@pytest.mark.django_db
def test_settings_force_mock_beats_env() -> None:
    """``settings.EMBEDDING_FORCE_MOCK`` should beat
    ``EMBEDDING_FORCE_MOCK=0`` env var. Lets tests
    override-settings into mock mode regardless of the
    shell environment they were launched in."""
    os.environ["EMBEDDING_FORCE_MOCK"] = "0"
    try:
        with override_settings(EMBEDDING_FORCE_MOCK=True):
            from django.core.cache import cache

            cache.clear()
            result = embed("test")
            assert "mock" in result.model
            assert result.cost_micros == 0
    finally:
        os.environ.pop("EMBEDDING_FORCE_MOCK", None)


@pytest.mark.django_db
def test_real_model_constant_is_text_embedding_3_small() -> None:
    """v1 locks to text-embedding-3-small (scope-lock §"Out of scope")."""
    assert EMBEDDING_MODEL == "text-embedding-3-small"
    assert EMBEDDING_DIMENSION == 1536
