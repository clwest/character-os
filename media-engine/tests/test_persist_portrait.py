"""SESSION 202 — persist_portrait endpoint behavior.

Two concerns:

1. **Mock-mode safety** — mock avatar_ids and runway_mock=True
   return ``persisted_url=None, mock_mode=True`` without
   touching the network or the filesystem.
2. **Real-mode happy path** — with a mocked Runway thumbnail
   fetcher + mocked image download, the endpoint persists the
   bytes to ``data/_internal/avatar_portraits/<id>.<ext>`` and
   returns the local URL.

Network calls to Runway are patched at the
``fetch_avatar_thumbnail`` import + ``httpx.Client`` levels so
the test is hermetic.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app


@pytest.fixture
def real_mode_client(tmp_path: Path):
    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="present",
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def mock_mode_client(tmp_path: Path):
    """No RUNWAY_API_KEY -> runway_mock=True."""

    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="",
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


def test_persist_portrait_mock_mode_returns_null_url(
    mock_mode_client: TestClient,
) -> None:
    """runway_mock=True → no network, no filesystem write,
    persisted_url=None + mock_mode=True."""
    resp = mock_mode_client.post(
        "/internal/avatars/some-real-looking-id/persist_portrait/",
        json={},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mock_mode"] is True
    assert body["persisted_url"] is None


def test_persist_portrait_mock_avatar_id_returns_null_url(
    real_mode_client: TestClient,
) -> None:
    """Avatar IDs starting with ``mock_`` are stable data URIs
    upstream — no point downloading them. Return null without
    touching Runway."""
    resp = real_mode_client.post(
        "/internal/avatars/mock_avatar_abc123/persist_portrait/",
        json={},
    )
    assert resp.status_code == 200
    body = resp.json()
    assert body["mock_mode"] is True
    assert body["persisted_url"] is None


def test_persist_portrait_happy_path_downloads_and_persists(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """With a fresh URL + 200 download, the endpoint writes the
    bytes to ``data/_internal/avatar_portraits/<id>.png`` and
    returns the local URL Django persists."""
    avatar_id = "abc12345-6789-0000-0000-000000000000"
    fake_jwt_url = f"https://cf.example/avatars/{avatar_id}.png?_jwt=fresh"
    fake_image_bytes = b"\x89PNG\r\n\x1a\nfake-png-bytes"

    # Mock the JWT-refresh + image download.
    fake_response = MagicMock()
    fake_response.status_code = 200
    fake_response.content = fake_image_bytes
    fake_response.headers = {"content-type": "image/png"}
    fake_http = MagicMock()
    fake_http.get.return_value = fake_response
    cm = MagicMock()
    cm.__enter__.return_value = fake_http
    cm.__exit__.return_value = False

    with patch(
        "app.routers.internal.fetch_avatar_thumbnail",
        return_value=fake_jwt_url,
    ), patch(
        "app.routers.internal.httpx.Client", return_value=cm,
    ):
        resp = real_mode_client.post(
            f"/internal/avatars/{avatar_id}/persist_portrait/",
            json={},
        )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is False
    assert body["persisted_url"] == (
        f"/data/_internal/avatar_portraits/{avatar_id}.png"
    )
    assert body["refreshed_jwt_url"] == fake_jwt_url

    # File exists on disk + carries the right bytes.
    persisted_path = (
        tmp_path / "_internal" / "avatar_portraits" / f"{avatar_id}.png"
    )
    assert persisted_path.exists()
    assert persisted_path.read_bytes() == fake_image_bytes


def test_persist_portrait_jwt_refresh_failure_returns_null(
    real_mode_client: TestClient,
) -> None:
    """Runway side returns no fresh URL → persisted_url=None +
    refreshed_jwt_url=None. No exception bubbles up."""
    avatar_id = "deadbeef-0000-0000-0000-000000000000"

    with patch(
        "app.routers.internal.fetch_avatar_thumbnail",
        return_value=None,
    ):
        resp = real_mode_client.post(
            f"/internal/avatars/{avatar_id}/persist_portrait/",
            json={},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["persisted_url"] is None
    assert body["refreshed_jwt_url"] is None


def test_persist_portrait_download_non_200_returns_null_url(
    real_mode_client: TestClient,
) -> None:
    """Download itself returns non-200 → persisted_url=None
    but refreshed_jwt_url is surfaced (caller can fall back
    to it as a short-term workaround)."""
    avatar_id = "feedface-0000-0000-0000-000000000000"
    fake_jwt_url = f"https://cf.example/avatars/{avatar_id}.png?_jwt=fresh"

    fake_response = MagicMock()
    fake_response.status_code = 403
    fake_response.content = b""
    fake_response.headers = {}
    fake_http = MagicMock()
    fake_http.get.return_value = fake_response
    cm = MagicMock()
    cm.__enter__.return_value = fake_http
    cm.__exit__.return_value = False

    with patch(
        "app.routers.internal.fetch_avatar_thumbnail",
        return_value=fake_jwt_url,
    ), patch(
        "app.routers.internal.httpx.Client", return_value=cm,
    ):
        resp = real_mode_client.post(
            f"/internal/avatars/{avatar_id}/persist_portrait/",
            json={},
        )

    assert resp.status_code == 200
    body = resp.json()
    assert body["persisted_url"] is None
    assert body["refreshed_jwt_url"] == fake_jwt_url
