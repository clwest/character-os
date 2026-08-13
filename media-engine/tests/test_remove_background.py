"""Endpoint surface for ``POST /internal/clips/remove_background/``.

These cover the routing, validation, cache, and mock-mode shape.
The real-mode pipeline (rembg + ffmpeg) is heavy and stateful; an
explicit ``@pytest.mark.heavy`` real-mode test would belong in a
separate file that CI skips by default — out of scope here.
"""
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def client(tmp_path: Path):
    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="",  # empty -> runway_mock True
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


def test_mock_mode_returns_deterministic_stub(client: TestClient) -> None:
    """With no Runway key, the endpoint short-circuits to a stub
    so end-to-end mock-mode tests run without rembg in the loop."""
    resp = client.post(
        "/internal/clips/remove_background/",
        json={"clip_url": "https://example.test/avatar.mp4"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is True
    assert body["output_url"].startswith("/data/_internal/matted/mock-")
    assert body["output_url"].endswith(".webm")
    assert body["size_bytes"] > 0


def test_mock_mode_is_deterministic_for_same_inputs(
    client: TestClient,
) -> None:
    """Same ``clip_url`` + ``model`` -> same cache key -> same
    stub URL. Composition runtime relies on this to dedupe."""
    payload = {
        "clip_url": "https://example.test/avatar.mp4",
        "model": "u2net_human_seg",
    }
    a = client.post("/internal/clips/remove_background/", json=payload).json()
    b = client.post("/internal/clips/remove_background/", json=payload).json()
    assert a["output_url"] == b["output_url"]


def test_different_clip_urls_get_different_cache_keys(
    client: TestClient,
) -> None:
    a = client.post(
        "/internal/clips/remove_background/",
        json={"clip_url": "https://example.test/avatar-a.mp4"},
    ).json()
    b = client.post(
        "/internal/clips/remove_background/",
        json={"clip_url": "https://example.test/avatar-b.mp4"},
    ).json()
    assert a["output_url"] != b["output_url"]


def test_unsupported_model_rejected(client: TestClient) -> None:
    """The v1 catalog ships one model. Future expansions add to
    ``_REMOVE_BACKGROUND_MODELS`` deliberately."""
    resp = client.post(
        "/internal/clips/remove_background/",
        json={
            "clip_url": "https://example.test/avatar.mp4",
            "model": "fancy-future-model",
        },
    )
    assert resp.status_code == 400
    detail = resp.json()
    assert "model must be one of" in detail.get("detail", {}).get(
        "message", "",
    ) or "model must be one of" in str(detail)


def test_empty_clip_url_rejected_by_pydantic(client: TestClient) -> None:
    """Pydantic catches the empty string before the handler runs."""
    resp = client.post(
        "/internal/clips/remove_background/",
        json={"clip_url": ""},
    )
    assert resp.status_code == 422


def test_cached_file_short_circuits(tmp_path: Path) -> None:
    """If the cache file already exists on disk, we skip the
    rembg pipeline entirely and serve the cached file. Drop in
    a real-mode cache file by hand so the route's
    ``output_path.exists()`` branch fires without provider
    being live."""
    import hashlib

    # Real-mode = Runway key present.
    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="present",  # disables runway_mock
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override

    clip_url = "https://example.test/cached.mp4"
    cache_seed = (clip_url + "|model=u2net_human_seg").encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]
    matted_dir = tmp_path / "_internal" / "matted"
    matted_dir.mkdir(parents=True)
    cached = matted_dir / f"{cache_key}.webm"
    cached.write_bytes(b"\x1a\x45\xdf\xa3" + b"\x00" * 100)  # webm magic + filler

    fresh = TestClient(app)
    resp = fresh.post(
        "/internal/clips/remove_background/",
        json={"clip_url": clip_url},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is False
    assert body["output_url"] == f"/data/_internal/matted/{cache_key}.webm"
    assert body["size_bytes"] == cached.stat().st_size

    app.dependency_overrides.pop(get_settings, None)
