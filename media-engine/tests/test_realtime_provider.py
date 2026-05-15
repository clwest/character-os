"""R2 tests — realtime provider abstraction + media-engine
endpoints.

Mock mode is the primary test surface. Real-mode against
Runway is exercised manually before launch; the route + the
provider abstraction are the load-bearing surfaces and both
have identical code paths in mock vs real (the provider
registry is the only branch).

Covered:

* `get_provider("runway", settings)` returns the Runway
  impl when `runway_api_key` is set; returns the mock when
  the key is empty.
* Mock provider's `create_session` returns deterministic
  payloads (same inputs → same session_id).
* Mock provider implements all 6 Protocol methods.
* Runway provider raises `RealtimeProviderError` when
  instantiated without an API key.
* Runway provider's `attach_documents` /
  `create_document` / `fetch_transcript` /
  `end_session` raise NotImplementedError (deferred to
  later R-slices).
* POST `/internal/realtime_sessions/` happy path in mock
  mode.
* GET `/internal/realtime_sessions/{id}/` happy path in
  mock mode.
* POST validation (avatar_id required).
* Provider name mismatch → 503.
* session_key + provider session_key never appear in
  server logs (caplog assertion).
"""
from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterator

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.realtime_provider import (
    RealtimeProviderError,
    ToolDef,
    get_provider,
)
from app.services.realtime_provider.mock import MockRealtimeProvider
from app.services.realtime_provider.runway import RunwayRealtimeProvider


@pytest.fixture
def mock_client(tmp_path: Path) -> Iterator[TestClient]:
    settings = Settings(runway_api_key="", data_dir=str(tmp_path))
    app.dependency_overrides[get_settings] = lambda: settings
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


# ---- provider registry ------------------------------------------


def test_get_provider_returns_mock_when_runway_mock_true(tmp_path):
    settings = Settings(runway_api_key="", data_dir=str(tmp_path))
    assert settings.runway_mock is True
    provider = get_provider("runway", settings)
    assert isinstance(provider, MockRealtimeProvider)


def test_get_provider_returns_runway_when_key_set(tmp_path):
    settings = Settings(runway_api_key="rwk_test_123", data_dir=str(tmp_path))
    assert settings.runway_mock is False
    provider = get_provider("runway", settings)
    assert isinstance(provider, RunwayRealtimeProvider)


def test_get_provider_unknown_name_raises(tmp_path):
    settings = Settings(runway_api_key="rwk_test_123", data_dir=str(tmp_path))
    with pytest.raises(RealtimeProviderError, match="unknown realtime provider"):
        get_provider("synthesia", settings)


def test_runway_provider_requires_api_key(tmp_path):
    settings = Settings(runway_api_key="", data_dir=str(tmp_path))
    # Force-instantiating without going through the registry
    # — the registry would have routed to mock; we want to
    # exercise the constructor's own guard.
    with pytest.raises(RealtimeProviderError, match="requires RUNWAY_API_KEY"):
        RunwayRealtimeProvider(settings)


# ---- mock provider shape ----------------------------------------


def test_mock_create_session_is_deterministic():
    p = MockRealtimeProvider()
    a = p.create_session("av_1", "you are a brand voice", "hello", [], [])
    b = p.create_session("av_1", "you are a brand voice", "hello", [], [])
    assert a.session_id == b.session_id
    assert a.session_key == b.session_key
    assert a.status == "ready"
    assert a.avatar_id == "av_1"


def test_mock_create_session_varies_with_inputs():
    p = MockRealtimeProvider()
    a = p.create_session("av_1", "p", "s", ["doc1"], [])
    b = p.create_session("av_1", "p", "s", ["doc2"], [])
    assert a.session_id != b.session_id


def test_mock_poll_returns_ready_immediately():
    p = MockRealtimeProvider()
    state = p.poll_session("mock_session_abc")
    assert state.session_id == "mock_session_abc"
    assert state.status == "ready"


def test_mock_implements_all_six_protocol_methods():
    p = MockRealtimeProvider()
    p.create_session("av", "p", "s", [], [])
    p.poll_session("s")
    p.attach_documents("av", ["d"])
    doc = p.create_document("name", "content")
    assert doc.document_id.startswith("mock_doc_")
    t = p.fetch_transcript("s")
    assert "[mock transcript for session s]" in t.text
    assert p.end_session("s") is None


# ---- runway provider stubs raise --------------------------------


def test_runway_attach_documents_requires_avatar_id(tmp_path):
    """R4 — attach_documents now implemented; raises
    RealtimeProviderError on missing avatar_id rather than
    NotImplementedError."""
    settings = Settings(runway_api_key="rwk_test_123", data_dir=str(tmp_path))
    p = RunwayRealtimeProvider(settings)
    with pytest.raises(RealtimeProviderError, match="avatar_id is required"):
        p.attach_documents("", ["d"])


def test_runway_create_document_requires_name(tmp_path):
    """R4 — Runway provider's create_document now
    implemented; raises RealtimeProviderError on missing
    inputs rather than NotImplementedError."""
    settings = Settings(runway_api_key="rwk_test_123", data_dir=str(tmp_path))
    p = RunwayRealtimeProvider(settings)
    with pytest.raises(RealtimeProviderError, match="name is required"):
        p.create_document("", "content")


def test_runway_create_document_requires_content(tmp_path):
    settings = Settings(runway_api_key="rwk_test_123", data_dir=str(tmp_path))
    p = RunwayRealtimeProvider(settings)
    with pytest.raises(RealtimeProviderError, match="content is required"):
        p.create_document("name", "")


def test_runway_fetch_transcript_raises_not_implemented(tmp_path):
    settings = Settings(runway_api_key="rwk_test_123", data_dir=str(tmp_path))
    p = RunwayRealtimeProvider(settings)
    with pytest.raises(NotImplementedError, match="R5"):
        p.fetch_transcript("s")


def test_runway_end_session_requires_session_id(tmp_path):
    """R3 — Runway provider's end_session now implemented;
    raises on empty session_id rather than NotImplementedError."""
    settings = Settings(runway_api_key="rwk_test_123", data_dir=str(tmp_path))
    p = RunwayRealtimeProvider(settings)
    with pytest.raises(RealtimeProviderError, match="session_id is required"):
        p.end_session("")


# ---- POST /internal/realtime_sessions/ --------------------------


def test_post_create_session_mock_mode(mock_client):
    response = mock_client.post(
        "/internal/realtime_sessions/",
        json={
            "avatar_id": "av_test_1",
            "personality": "warm brand voice",
            "start_script": "Hello, ask me anything.",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["session_id"].startswith("mock_session_")
    assert data["session_key"].startswith("mock_session_key_")
    assert data["status"] == "ready"
    assert data["avatar_id"] == "av_test_1"
    assert data["mock_mode"] is True


def test_post_create_session_requires_avatar_id(mock_client):
    response = mock_client.post(
        "/internal/realtime_sessions/",
        json={"avatar_id": ""},
    )
    assert response.status_code == 422


def test_post_create_session_with_tools(mock_client):
    response = mock_client.post(
        "/internal/realtime_sessions/",
        json={
            "avatar_id": "av_test_2",
            "tools": [
                {
                    "name": "recall_knowledge",
                    "description": "Search the workspace docs",
                    "parameters": {"q": "string"},
                },
            ],
        },
    )
    assert response.status_code == 200
    assert response.json()["session_id"].startswith("mock_session_")


def test_post_create_session_unknown_provider_503(mock_client):
    """The 'synthesia' provider isn't registered.
    Should return 503 realtime_unavailable.

    Note: in mock mode (runway_mock=True from the fixture),
    `get_provider` short-circuits to mock REGARDLESS of
    `provider` name — so this test exercises the real-mode
    branch by overriding settings with a fake key.
    """
    settings = Settings(runway_api_key="rwk_test_123", data_dir=str(mock_client.app.state.__dict__.get("data_dir", "/tmp")))
    # Re-override with real-mode settings.
    app.dependency_overrides[get_settings] = lambda: settings
    try:
        response = mock_client.post(
            "/internal/realtime_sessions/",
            json={"avatar_id": "av", "provider": "synthesia"},
        )
        assert response.status_code == 503
        data = response.json()
        # _error() returns a JSONResponse with {error: {...}}.
        assert "synthesia" in str(data).lower() or "unknown" in str(data).lower()
    finally:
        # Restore mock-mode override from the fixture.
        app.dependency_overrides[get_settings] = lambda: Settings(
            runway_api_key="", data_dir=str(mock_client.app.state.__dict__.get("data_dir", "/tmp")),
        )


# ---- GET /internal/realtime_sessions/{id}/ ----------------------


def test_get_poll_session_mock_mode(mock_client):
    create = mock_client.post(
        "/internal/realtime_sessions/",
        json={"avatar_id": "av_test_3"},
    )
    session_id = create.json()["session_id"]
    poll = mock_client.get(f"/internal/realtime_sessions/{session_id}/")
    assert poll.status_code == 200
    data = poll.json()
    assert data["session_id"] == session_id
    assert data["status"] == "ready"
    assert data["mock_mode"] is True


# ---- security: session_key never leaks to logs ------------------


def test_post_create_document_mock_mode(mock_client):
    """R4 — POST /internal/realtime_documents/ in mock mode
    returns a deterministic document_id."""
    response = mock_client.post(
        "/internal/realtime_documents/",
        json={
            "name": "Spokesperson Sasha",
            "content": "# Sasha\n\n## About\n\nA brand voice.",
        },
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["document_id"].startswith("mock_doc_")
    assert data["mock_mode"] is True


def test_post_create_document_requires_name(mock_client):
    response = mock_client.post(
        "/internal/realtime_documents/",
        json={"name": "", "content": "x"},
    )
    assert response.status_code == 422


def test_post_create_document_requires_content(mock_client):
    response = mock_client.post(
        "/internal/realtime_documents/",
        json={"name": "x", "content": ""},
    )
    assert response.status_code == 422


def test_session_key_not_logged(mock_client, caplog):
    with caplog.at_level(logging.INFO):
        response = mock_client.post(
            "/internal/realtime_sessions/",
            json={"avatar_id": "av_test_secret"},
        )
    assert response.status_code == 200
    session_key = response.json()["session_key"]
    # Sanity check the mock value is non-empty so the
    # assertion below is meaningful.
    assert session_key
    # The router logs session_id (we want that) but must
    # NEVER log session_key (contract rule 9).
    for record in caplog.records:
        assert session_key not in record.getMessage()
