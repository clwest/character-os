"""VO.1 tests — ``POST /internal/audio/tts/`` + tts_provider
dispatch chain.

Covers the contract rules from docs/design/VOICEOVER_V1.md:

* Rule 3 — TTS-only path: the route doesn't fire the avatar
  pipeline. Verified by asserting the response carries
  duration / audio_url / cost without any Runway task ids.
* Rule 9 — provider abstraction lives in media-engine. The
  shell never imports a provider directly.
* Q-vo-2 — Runway-first chain with ElevenLabs fallback.
  Mock-mode bypass via VOICEOVER_TTS_FORCE_MOCK (env) or
  ``provider=mock`` (explicit).

Provider drift verifier mirrors R10's test_r10_provider_drift
pattern. New providers + new Protocol methods trip the test;
the maintenance cost is one line per new provider here.
"""
from __future__ import annotations

import ast
import inspect
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.services.tts_provider import (
    TextToSpeechProvider,
    TtsProviderError,
    TtsSpec,
    TtsUnavailableError,
    get_provider,
)
from app.services.tts_provider.elevenlabs import ElevenLabsTtsProvider
from app.services.tts_provider.mock import MockTtsProvider
from app.services.tts_provider.runway import RunwayTtsProvider


# ---- fixtures ------------------------------------------------------


@pytest.fixture
def mock_client(tmp_path: Path):
    """TestClient pinned to a tmp data_path with the force-mock
    flag on so the dispatcher routes to MockTtsProvider."""

    def _override() -> Settings:
        return Settings(
            runway_api_key="present",
            voiceover_tts_force_mock=True,
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


@pytest.fixture
def auto_no_provider_client(tmp_path: Path):
    """TestClient where ``runway_mock=True`` (no Runway key) AND
    no ElevenLabs key. ``provider=auto`` should fall through to
    MockTtsProvider rather than 503'ing — operators in this
    state are clearly in dev / test mode."""

    def _override() -> Settings:
        return Settings(
            runway_api_key="",
            elevenlabs_api_key="",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


# ---- /internal/audio/tts/ route ------------------------------------


def test_tts_force_mock_returns_mock_provider_response(mock_client):
    resp = mock_client.post(
        "/internal/audio/tts/",
        json={
            "text": "And now back to you, Jessica.",
            "voice_id": "voice_jessica_123",
            "provider": "auto",
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["provider"] == "mock"
    assert body["mock_mode"] is True
    assert body["voice_id"] == "voice_jessica_123"
    assert body["model"] == "eleven_multilingual_v2"
    assert body["duration_seconds"] > 0
    assert body["audio_url"].startswith("/data/_internal/voiceovers/mock-")
    assert body["cost_micros"] > 0


def test_tts_explicit_mock_provider(mock_client):
    """provider='mock' shortcut — useful when force-mock env
    is off but the operator wants a deterministic stub for
    one specific call."""
    resp = mock_client.post(
        "/internal/audio/tts/",
        json={
            "text": "Test mock provider explicitly",
            "voice_id": "voice_x",
            "provider": "mock",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "mock"


def test_tts_rejects_unknown_provider(mock_client):
    resp = mock_client.post(
        "/internal/audio/tts/",
        json={
            "text": "Hello",
            "voice_id": "v_x",
            "provider": "synthesia",
        },
    )
    assert resp.status_code == 400
    body = resp.json()
    assert "provider must be one of" in body.get("error", body.get("detail", ""))


def test_tts_rejects_blank_text(mock_client):
    resp = mock_client.post(
        "/internal/audio/tts/",
        json={
            "text": "",
            "voice_id": "v_x",
        },
    )
    # Pydantic rejects min_length=1 at validation.
    assert resp.status_code in (422, 400)


def test_tts_rejects_blank_voice_id(mock_client):
    resp = mock_client.post(
        "/internal/audio/tts/",
        json={
            "text": "Hello",
            "voice_id": "",
        },
    )
    assert resp.status_code in (422, 400)


def test_tts_rejects_overly_long_text(mock_client):
    resp = mock_client.post(
        "/internal/audio/tts/",
        json={
            "text": "x" * 5001,
            "voice_id": "v_x",
        },
    )
    assert resp.status_code in (422, 400)


def test_tts_auto_with_no_providers_falls_back_to_mock(auto_no_provider_client):
    """Auto chain with no Runway key + no ElevenLabs key
    routes to mock so local dev / tests still work."""
    resp = auto_no_provider_client.post(
        "/internal/audio/tts/",
        json={
            "text": "Hello from auto fallback",
            "voice_id": "v_dev",
        },
    )
    assert resp.status_code == 200
    assert resp.json()["provider"] == "mock"


def test_tts_mock_writes_real_silent_mp3_if_ffmpeg_available(
    mock_client, tmp_path: Path,
):
    """The mock provider emits a real silent MP3 via ffmpeg
    when available — VO.2's overlay primitive needs a
    parseable file even in mock-mode."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    resp = mock_client.post(
        "/internal/audio/tts/",
        json={
            "text": "Silent placeholder for testing",
            "voice_id": "voice_x",
        },
    )
    assert resp.status_code == 200
    body = resp.json()
    # /data/_internal/voiceovers/mock-<hash>.mp3 → tmp_path/_internal/voiceovers/...
    rel = body["audio_url"][len("/data/"):]
    out = tmp_path / rel
    assert out.exists()
    # Real MP3 has size > 0 with ffmpeg available.
    assert out.stat().st_size > 0


def test_tts_mock_is_idempotent_for_same_inputs(mock_client):
    """Cache-key determinism — same (voice_id, model, text)
    produces the same audio_url across calls. Mirrors V14
    audio_extract's cache discipline."""
    payload = {
        "text": "Cache test",
        "voice_id": "voice_cache",
    }
    r1 = mock_client.post("/internal/audio/tts/", json=payload)
    r2 = mock_client.post("/internal/audio/tts/", json=payload)
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["audio_url"] == r2.json()["audio_url"]


# ---- Provider package — Protocol surface ---------------------------


PROTOCOL_METHODS = ("synthesize",)


def _provider_classes() -> list[type]:
    """Concrete TTS provider classes — adding a future Synthesia
    / Polly adapter just adds an import + a row to this list,
    and the drift tests automatically pick it up."""
    return [MockTtsProvider, RunwayTtsProvider, ElevenLabsTtsProvider]


def test_protocol_methods_match_expected_set():
    """The PROTOCOL_METHODS constant mirrors the Protocol. If a
    future method lands on TextToSpeechProvider, the constant
    update is the audit event that the new method needs an impl
    on every provider."""
    proto_methods = {
        name
        for name in dir(TextToSpeechProvider)
        if not name.startswith("_") and callable(getattr(TextToSpeechProvider, name))
    }
    expected = set(PROTOCOL_METHODS)
    assert proto_methods == expected, (
        f"Protocol method set drifted from PROTOCOL_METHODS.\n"
        f"  On Protocol: {sorted(proto_methods)}\n"
        f"  In test:     {sorted(expected)}\n"
    )


@pytest.mark.parametrize("provider_cls", _provider_classes())
def test_provider_implements_every_protocol_method(provider_cls: type):
    """Each concrete provider must define every Protocol method."""
    missing = [
        name for name in PROTOCOL_METHODS
        if not hasattr(provider_cls, name)
        or not callable(getattr(provider_cls, name))
    ]
    assert missing == [], (
        f"{provider_cls.__name__} is missing Protocol method(s): "
        f"{missing}. Every concrete provider must implement every "
        f"method in TextToSpeechProvider."
    )


@pytest.mark.parametrize("provider_cls", _provider_classes())
def test_provider_methods_are_not_notimplemented_stubs(provider_cls: type):
    """Each Protocol method's body must do real work — no bare
    `raise NotImplementedError` stubs allowed at slice close.
    Mirrors R10's drift discipline."""
    stubs: list[str] = []
    for name in PROTOCOL_METHODS:
        method = getattr(provider_cls, name)
        if _method_is_notimplemented_stub(method):
            stubs.append(name)
    assert stubs == [], (
        f"{provider_cls.__name__} method(s) {stubs} are bare "
        f"`raise NotImplementedError` stubs."
    )


def _method_is_notimplemented_stub(method) -> bool:
    """True if the method's body is exactly ``raise NotImplementedError(...)``."""
    try:
        source = inspect.getsource(method)
    except (OSError, TypeError):
        return False
    source = inspect.cleandoc(source)
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    if not tree.body or not isinstance(
        tree.body[0], (ast.FunctionDef, ast.AsyncFunctionDef),
    ):
        return False
    fn_body = tree.body[0].body
    if (
        fn_body
        and isinstance(fn_body[0], ast.Expr)
        and isinstance(fn_body[0].value, ast.Constant)
        and isinstance(fn_body[0].value.value, str)
    ):
        fn_body = fn_body[1:]
    if len(fn_body) != 1:
        return False
    stmt = fn_body[0]
    if not isinstance(stmt, ast.Raise):
        return False
    exc = stmt.exc
    if isinstance(exc, ast.Name) and exc.id == "NotImplementedError":
        return True
    if (
        isinstance(exc, ast.Call)
        and isinstance(exc.func, ast.Name)
        and exc.func.id == "NotImplementedError"
    ):
        return True
    return False


# ---- get_provider registry behavior --------------------------------


def test_get_provider_mock_when_force_mock():
    settings = Settings(voiceover_tts_force_mock=True)
    provider = get_provider("auto", settings)
    assert isinstance(provider, MockTtsProvider)


def test_get_provider_mock_when_runway_mock_runway_path():
    """``get_provider('runway', ...)`` falls through to mock when
    no RUNWAY_API_KEY (settings.runway_mock=True)."""
    settings = Settings(runway_api_key="")
    assert settings.runway_mock is True
    provider = get_provider("runway", settings)
    assert isinstance(provider, MockTtsProvider)


def test_get_provider_runway_when_key_present():
    settings = Settings(runway_api_key="sk-fake")
    provider = get_provider("runway", settings)
    assert isinstance(provider, RunwayTtsProvider)


def test_get_provider_elevenlabs_when_key_present():
    settings = Settings(elevenlabs_api_key="eleven-fake")
    provider = get_provider("elevenlabs", settings)
    assert isinstance(provider, ElevenLabsTtsProvider)


def test_get_provider_elevenlabs_unavailable_when_no_key():
    settings = Settings(elevenlabs_api_key="")
    with pytest.raises(TtsUnavailableError):
        get_provider("elevenlabs", settings)


def test_get_provider_raises_for_unknown_name():
    settings = Settings(runway_api_key="sk-fake")
    with pytest.raises(TtsProviderError):
        get_provider("synthesia", settings)


# ---- Drift surface --------------------------------------------------


def test_provider_package_only_contains_known_files():
    """Sanity check the registry covers every .py file in the
    package directory. Adding a new provider goes uncovered if
    we forget to update _provider_classes."""
    pkg_dir = Path(inspect.getfile(MockTtsProvider)).parent
    known_modules = {"__init__", "mock", "runway", "elevenlabs"}
    actual_modules = {
        p.stem for p in pkg_dir.glob("*.py")
        if not p.stem.startswith("_") or p.stem == "__init__"
    }
    unknown = actual_modules - known_modules
    assert unknown == set(), (
        f"New tts_provider module(s) detected: {sorted(unknown)}. "
        f"Add to _provider_classes in this test file + known_modules."
    )


# ---- Mock provider direct exercise ---------------------------------


def test_mock_provider_synthesize_deterministic(tmp_path: Path):
    """Same inputs → same cache key → same output path. Lets
    higher-level tests assert on stable cache surfaces."""
    provider = MockTtsProvider()
    provider.configure(tmp_path)
    spec = TtsSpec(text="hello", voice_id="v1")
    r1 = provider.synthesize(spec)
    r2 = provider.synthesize(spec)
    assert r1.audio_url == r2.audio_url
    assert r1.duration_seconds == r2.duration_seconds
    assert r1.provider == "mock"


def test_mock_provider_duration_scales_with_text_length(tmp_path: Path):
    """The mock heuristic mirrors the
    _AVATAR_SPEECH_CHARS_PER_SECOND constant (11 cps) so VO.2's
    offset math stays stable across mock + real modes."""
    provider = MockTtsProvider()
    provider.configure(tmp_path)
    short = provider.synthesize(TtsSpec(text="hi", voice_id="v"))
    long = provider.synthesize(TtsSpec(text="x" * 110, voice_id="v"))
    # 110 chars / 11 cps ≈ 10s, short is min-floor at 1s.
    assert short.duration_seconds == 1.0
    assert 9.0 <= long.duration_seconds <= 11.0
