"""RunwayVoiceProvider tests — §19 Step 6.b (SESSION 245).

Exercises the adapter WITHOUT hitting the real Runway API. Real-
provider smoke lives in ``test_runway_real_smoke.py`` and is
opt-in via env vars.

Coverage:
* Force-mock routing: adapter identity preserved
  (``provider=RUNWAY_VOICE``) while ``execution_mode_actual=MOCK``
* AUTO routing when API key absent: routes to mock, preserves
  identity, records ``mock_reason=runway_unavailable``
* REAL_REQUIRED without API key: raises
  ``VoiceProviderUnavailableError`` (never silently degrades)
* Real-code path error mapping: transport-layer exceptions
  wrap to ``VoiceProviderRequestFailedError`` (verified via
  ``monkeypatch`` on the transport functions — no wire calls)
* Capability accuracy against Runway's documented limits
* Cross-adapter mock parity: same spec + identical seed
  produces identical ``voice_id`` on both Mock and Runway
  adapters (SESSION 245 6.b contract)
* Spec validation happens BEFORE any transport call is
  attempted (SESSION 245 carry-in: validate at the adapter
  boundary before spending credits)
"""
from __future__ import annotations

from unittest.mock import patch

import httpx
import pytest

from app.config import Settings
from app.services.audio_client import AudioError
from app.services.voice_provider import (
    ExecutionMode,
    ExecutionModeActual,
    ReferenceAudioTooLargeError,
    UnsupportedAudioFormatError,
    UnsupportedModelError,
    VoiceCloneSpec,
    VoiceDesignSpec,
    VoiceOperation,
    VoiceProviderName,
    VoiceProviderRequestFailedError,
    VoiceProviderUnavailableError,
    get_provider,
)
from app.services.voice_provider.mock import MockVoiceProvider
from app.services.voice_provider.runway import RunwayVoiceProvider


# ---- Settings helpers -----------------------------------------


def _mock_settings() -> Settings:
    """Settings with runway_mock=True (no API key). Verifies
    force-mock and AUTO-without-key routing paths.
    """
    s = Settings()
    s.runway_api_key = ""
    s.runway_force_mock = False
    # Property runway_mock returns True when key is empty.
    assert s.runway_mock is True
    return s


def _real_settings() -> Settings:
    """Settings that look like a live Runway environment.
    Never actually hits the wire in this file — always paired
    with a monkeypatched transport function.
    """
    s = Settings()
    s.runway_api_key = "TEST-KEY-NOT-A-REAL-CREDENTIAL"
    s.runway_force_mock = False
    assert s.runway_mock is False
    return s


def _design_spec(
    *,
    execution_mode: ExecutionMode = ExecutionMode.AUTO,
    description: str = "warm mid-range narrator voice, US English",
    name: str | None = "Test Voice",
    provider_model: str | None = None,
    deterministic_seed: str | None = "seed-a",
) -> VoiceDesignSpec:
    return VoiceDesignSpec(
        description=description,
        execution_mode=execution_mode,
        name=name,
        provider_model=provider_model,
        deterministic_seed=deterministic_seed,
    )


def _clone_spec(
    *,
    execution_mode: ExecutionMode = ExecutionMode.AUTO,
    reference_audio: bytes | None = None,
    reference_mime: str = "audio/mpeg",
    name: str | None = "Test Clone",
    deterministic_seed: str | None = "seed-a",
) -> VoiceCloneSpec:
    return VoiceCloneSpec(
        reference_audio=reference_audio if reference_audio is not None else b"\x00" * 4096,
        reference_mime=reference_mime,
        execution_mode=execution_mode,
        name=name,
        deterministic_seed=deterministic_seed,
    )


# ---- Registry -------------------------------------------------


def test_get_provider_returns_runway_for_runway_voice_name():
    provider = get_provider("runway_voice", Settings())
    assert isinstance(provider, RunwayVoiceProvider)


# ---- Capabilities ---------------------------------------------


def test_capabilities_supports_both_design_and_clone():
    caps = RunwayVoiceProvider(Settings()).capabilities()
    assert caps.supports_design is True
    assert caps.supports_clone is True


def test_capabilities_provider_name_is_runway_voice():
    caps = RunwayVoiceProvider(Settings()).capabilities()
    assert caps.provider_name == VoiceProviderName.RUNWAY_VOICE


def test_capabilities_design_model_is_eleven_multilingual():
    """Provider-model is Runway's ElevenLabs-backed model
    (documented in ``audio_client._VOICE_DESIGN_MODEL``).
    """
    caps = RunwayVoiceProvider(Settings()).capabilities()
    assert caps.supported_design_models == ("eleven_multilingual_ttv_v2",)


def test_capabilities_reference_audio_limits_match_runway_docs():
    """10 MB / 10-300s per Runway's documented limits (see
    ``voice_clone_client.py`` docstring).
    """
    caps = RunwayVoiceProvider(Settings()).capabilities()
    assert caps.max_reference_bytes == 10 * 1024 * 1024
    assert caps.min_reference_seconds == 10.0
    assert caps.max_reference_seconds == 300.0


def test_capabilities_mimes_include_common_audio_formats():
    caps = RunwayVoiceProvider(Settings()).capabilities()
    for expected in ("audio/mpeg", "audio/wav", "audio/mp4"):
        assert expected in caps.accepted_audio_mimes


def test_capabilities_supports_all_three_execution_modes():
    caps = RunwayVoiceProvider(Settings()).capabilities()
    assert ExecutionMode.FORCED_MOCK in caps.execution_modes_supported
    assert ExecutionMode.AUTO in caps.execution_modes_supported
    assert ExecutionMode.REAL_REQUIRED in caps.execution_modes_supported


def test_capabilities_is_synchronous_true():
    """Runway's voice-design/clone are synchronous polling in
    the request — the adapter blocks until READY/FAILED.
    """
    caps = RunwayVoiceProvider(Settings()).capabilities()
    assert caps.is_synchronous is True


def test_capabilities_max_authoring_seconds_matches_runway_deadline():
    caps = RunwayVoiceProvider(Settings()).capabilities()
    assert caps.max_authoring_seconds == 90


# ---- Force-mock routing (adapter identity preserved) ----------


def test_design_forced_mock_preserves_runway_identity():
    """FORCED_MOCK on the Runway adapter stamps
    ``provider=RUNWAY_VOICE`` (not MOCK) — adapter identity is
    preserved across mock/real routing per SESSION 244 constraint
    carried into SESSION 245.

    The second filter (``execution_mode_actual``) is what marks
    the row as non-qualifying evidence.
    """
    provider = RunwayVoiceProvider(_real_settings())
    result = provider.design_voice(_design_spec(execution_mode=ExecutionMode.FORCED_MOCK))
    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    assert result.execution_mode_actual == ExecutionModeActual.MOCK
    assert result.operation == VoiceOperation.DESIGN
    assert result.preview_url is None
    assert result.prompt_snapshot["mock_reason"] == "forced_mock"


def test_clone_forced_mock_preserves_runway_identity():
    provider = RunwayVoiceProvider(_real_settings())
    result = provider.clone_voice(_clone_spec(execution_mode=ExecutionMode.FORCED_MOCK))
    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    assert result.execution_mode_actual == ExecutionModeActual.MOCK
    assert result.operation == VoiceOperation.CLONE
    assert result.prompt_snapshot["mock_reason"] == "forced_mock"


def test_design_auto_without_key_routes_to_mock():
    """AUTO on a Runway adapter with no API key routes to mock.
    Provider stays RUNWAY_VOICE; execution_mode_actual=MOCK.
    Records ``mock_reason=runway_unavailable`` in the snapshot
    so provenance distinguishes this from FORCED_MOCK.
    """
    provider = RunwayVoiceProvider(_mock_settings())
    result = provider.design_voice(_design_spec(execution_mode=ExecutionMode.AUTO))
    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    assert result.execution_mode_actual == ExecutionModeActual.MOCK
    assert result.prompt_snapshot["mock_reason"] == "runway_unavailable"


def test_clone_auto_without_key_routes_to_mock():
    provider = RunwayVoiceProvider(_mock_settings())
    result = provider.clone_voice(_clone_spec(execution_mode=ExecutionMode.AUTO))
    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    assert result.execution_mode_actual == ExecutionModeActual.MOCK
    assert result.prompt_snapshot["mock_reason"] == "runway_unavailable"


def test_design_real_required_without_key_raises():
    """SESSION 245 ratification 4: never silently degrades on
    REAL_REQUIRED. Availability routing runs BEFORE any wire
    call.
    """
    provider = RunwayVoiceProvider(_mock_settings())
    with pytest.raises(VoiceProviderUnavailableError):
        provider.design_voice(_design_spec(execution_mode=ExecutionMode.REAL_REQUIRED))


def test_clone_real_required_without_key_raises():
    provider = RunwayVoiceProvider(_mock_settings())
    with pytest.raises(VoiceProviderUnavailableError):
        provider.clone_voice(_clone_spec(execution_mode=ExecutionMode.REAL_REQUIRED))


# ---- Real-code path error mapping (no wire calls) -------------


def test_design_real_wraps_audio_error_as_provider_failed():
    """The design transport raises ``AudioError`` on non-200
    creates, missing ids, FAILED status, or timeouts. The
    adapter maps it to ``VoiceProviderRequestFailedError`` and
    NEVER silently returns mock (SESSION 245 ratification 4).
    """
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_design_voice_transport",
        side_effect=AudioError("Runway rejected the voice design request."),
    ):
        with pytest.raises(VoiceProviderRequestFailedError) as excinfo:
            provider.design_voice(_design_spec(execution_mode=ExecutionMode.REAL_REQUIRED))
    assert "runway design failed" in str(excinfo.value)


def test_design_real_wraps_http_error_as_provider_failed():
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_design_voice_transport",
        side_effect=httpx.ConnectError("connection refused"),
    ):
        with pytest.raises(VoiceProviderRequestFailedError):
            provider.design_voice(_design_spec(execution_mode=ExecutionMode.REAL_REQUIRED))


def test_clone_real_wraps_runtime_error_as_provider_failed():
    """The clone transport raises ``RuntimeError`` on failure
    (not ``AudioError`` — different module). Adapter still maps
    it correctly.
    """
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_clone_voice_transport",
        side_effect=RuntimeError("voice clone did not reach READY"),
    ):
        with pytest.raises(VoiceProviderRequestFailedError) as excinfo:
            provider.clone_voice(_clone_spec(execution_mode=ExecutionMode.REAL_REQUIRED))
    assert "runway clone failed" in str(excinfo.value)


def test_clone_real_wraps_http_error_as_provider_failed():
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_clone_voice_transport",
        side_effect=httpx.TimeoutException("upstream timed out"),
    ):
        with pytest.raises(VoiceProviderRequestFailedError):
            provider.clone_voice(_clone_spec(execution_mode=ExecutionMode.REAL_REQUIRED))


def test_design_real_success_returns_runway_stamped_result():
    """Happy path via monkeypatch. Verifies the adapter
    correctly stamps provenance for a successful real call
    (without spending credits).
    """
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_design_voice_transport",
        return_value=("runway_voice_xyz789", "https://runway.example/preview.mp3"),
    ):
        result = provider.design_voice(_design_spec(execution_mode=ExecutionMode.REAL_REQUIRED))
    assert result.voice_id == "runway_voice_xyz789"
    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    assert result.operation == VoiceOperation.DESIGN
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    assert result.provider_model == "eleven_multilingual_ttv_v2"
    assert result.preview_url == "https://runway.example/preview.mp3"
    assert result.prompt_snapshot["operation"] == "design"
    assert result.elapsed_ms >= 0


def test_clone_real_success_returns_runway_stamped_result():
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_clone_voice_transport",
        return_value=("runway_clone_abc456", "READY", "https://runway.example/clone.mp3"),
    ):
        result = provider.clone_voice(_clone_spec(execution_mode=ExecutionMode.REAL_REQUIRED))
    assert result.voice_id == "runway_clone_abc456"
    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    assert result.operation == VoiceOperation.CLONE
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    assert result.provider_model is None  # Clone has no model concept.
    assert result.preview_url == "https://runway.example/clone.mp3"
    assert result.prompt_snapshot["final_status"] == "READY"


def test_real_design_never_calls_transport_when_route_would_mock():
    """FORCED_MOCK routing must not reach the transport
    function. Belt-and-braces test that mock routing happens
    BEFORE any wire attempt.
    """
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_design_voice_transport",
    ) as mock_transport:
        provider.design_voice(_design_spec(execution_mode=ExecutionMode.FORCED_MOCK))
        assert mock_transport.call_count == 0


def test_real_clone_never_calls_transport_when_route_would_mock():
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_clone_voice_transport",
    ) as mock_transport:
        provider.clone_voice(_clone_spec(execution_mode=ExecutionMode.FORCED_MOCK))
        assert mock_transport.call_count == 0


def test_auto_never_silently_degrades_after_real_dispatch():
    """The critical SESSION 245 ratification 4 invariant: once
    the adapter has decided to run real (AUTO with API key
    configured), a transport failure MUST raise rather than
    silently produce a mock result.

    If this test ever fails, availability routing has been
    corrupted into error hiding.
    """
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_design_voice_transport",
        side_effect=AudioError("upstream failure"),
    ):
        with pytest.raises(VoiceProviderRequestFailedError):
            provider.design_voice(_design_spec(execution_mode=ExecutionMode.AUTO))


# ---- Spec validation before credit spending -------------------


def test_design_invalid_spec_never_reaches_transport():
    """Spec validation runs BEFORE the transport call. Sending
    a too-short description must not spend a Runway API call.
    """
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_design_voice_transport",
    ) as mock_transport:
        with pytest.raises(ValueError):
            provider.design_voice(
                _design_spec(
                    description="hi",  # < 20 chars minimum
                    execution_mode=ExecutionMode.REAL_REQUIRED,
                ),
            )
        assert mock_transport.call_count == 0


def test_clone_invalid_mime_never_reaches_transport():
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_clone_voice_transport",
    ) as mock_transport:
        with pytest.raises(UnsupportedAudioFormatError):
            provider.clone_voice(
                _clone_spec(
                    reference_mime="application/octet-stream",
                    execution_mode=ExecutionMode.REAL_REQUIRED,
                ),
            )
        assert mock_transport.call_count == 0


def test_clone_oversized_audio_never_reaches_transport():
    provider = RunwayVoiceProvider(_real_settings())
    caps = provider.capabilities()
    assert caps.max_reference_bytes is not None
    oversize = b"x" * (caps.max_reference_bytes + 1)
    with patch(
        "app.services.voice_provider.runway.runway_clone_voice_transport",
    ) as mock_transport:
        with pytest.raises(ReferenceAudioTooLargeError):
            provider.clone_voice(
                _clone_spec(
                    reference_audio=oversize,
                    execution_mode=ExecutionMode.REAL_REQUIRED,
                ),
            )
        assert mock_transport.call_count == 0


def test_design_unsupported_model_never_reaches_transport():
    provider = RunwayVoiceProvider(_real_settings())
    with patch(
        "app.services.voice_provider.runway.runway_design_voice_transport",
    ) as mock_transport:
        with pytest.raises(UnsupportedModelError):
            provider.design_voice(
                _design_spec(
                    provider_model="not-a-real-runway-model",
                    execution_mode=ExecutionMode.REAL_REQUIRED,
                ),
            )
        assert mock_transport.call_count == 0


def test_design_unavailable_execution_mode_raises_value_error():
    provider = RunwayVoiceProvider(_real_settings())
    with pytest.raises(ValueError):
        provider.design_voice(_design_spec(execution_mode=ExecutionMode.UNAVAILABLE))


def test_clone_unavailable_execution_mode_raises_value_error():
    provider = RunwayVoiceProvider(_real_settings())
    with pytest.raises(ValueError):
        provider.clone_voice(_clone_spec(execution_mode=ExecutionMode.UNAVAILABLE))


def test_clone_empty_audio_raises_value_error():
    provider = RunwayVoiceProvider(_real_settings())
    with pytest.raises(ValueError):
        provider.clone_voice(_clone_spec(reference_audio=b""))


# ---- Cross-adapter mock parity --------------------------------


def test_design_mock_parity_between_mock_and_runway_adapters():
    """The 6.b cross-adapter parity contract: identical specs
    routed to mock must produce identical ``voice_id`` values on
    both the Mock adapter and the Runway adapter in force-mock.
    Guarantees that mock output is truly adapter-fungible for
    determinism tests.

    Note: parity holds on ``voice_id``. Provider stamp and
    ``prompt_snapshot["mock_reason"]`` differ intentionally
    (Runway adapter records ``mock_reason``; Mock adapter has
    no such field because it has no real path to explain away).
    """
    spec = _design_spec(
        description="stable mock parity voice description",
        deterministic_seed="parity-seed",
        execution_mode=ExecutionMode.FORCED_MOCK,
    )
    mock_result = MockVoiceProvider().design_voice(spec)
    runway_result = RunwayVoiceProvider(_real_settings()).design_voice(spec)
    assert mock_result.voice_id == runway_result.voice_id, (
        f"Mock parity broken:\n"
        f"  MockVoiceProvider: {mock_result.voice_id}\n"
        f"  RunwayVoiceProvider (force-mock): {runway_result.voice_id}"
    )


def test_clone_mock_parity_between_mock_and_runway_adapters():
    spec = _clone_spec(
        reference_audio=b"identical bytes for parity" * 200,
        deterministic_seed="parity-seed",
        execution_mode=ExecutionMode.FORCED_MOCK,
    )
    mock_result = MockVoiceProvider().clone_voice(spec)
    runway_result = RunwayVoiceProvider(_real_settings()).clone_voice(spec)
    assert mock_result.voice_id == runway_result.voice_id


def test_mock_parity_holds_regardless_of_mock_reason():
    """FORCED_MOCK and AUTO-without-key both produce the same
    ``voice_id`` from the Runway adapter for identical specs
    (differing only in ``prompt_snapshot["mock_reason"]``).
    """
    provider_forced = RunwayVoiceProvider(_real_settings())
    provider_auto = RunwayVoiceProvider(_mock_settings())
    forced = provider_forced.design_voice(
        _design_spec(execution_mode=ExecutionMode.FORCED_MOCK),
    )
    auto_mock = provider_auto.design_voice(
        _design_spec(execution_mode=ExecutionMode.AUTO),
    )
    assert forced.voice_id == auto_mock.voice_id
    assert forced.prompt_snapshot["mock_reason"] == "forced_mock"
    assert auto_mock.prompt_snapshot["mock_reason"] == "runway_unavailable"


# ---- Two-filter qualification-plumbing discipline -------------


def test_forced_mock_result_is_non_qualifying_via_execution_mode_filter():
    """Adapter identity is preserved (provider=RUNWAY_VOICE) so
    the provider filter alone (``provider != MOCK``) is
    insufficient — this row would pass filter 1 but be caught
    by filter 2 (``execution_mode_actual != REAL``).

    This test proves both filters must exist independently. Fix
    the cross-adapter provenance model, not this test.
    """
    result = RunwayVoiceProvider(_real_settings()).design_voice(
        _design_spec(execution_mode=ExecutionMode.FORCED_MOCK),
    )
    # Filter 1 (provider != MOCK) would ACCEPT this row.
    assert result.provider == VoiceProviderName.RUNWAY_VOICE
    # Filter 2 (execution_mode_actual != REAL) correctly REJECTS.
    assert result.execution_mode_actual != ExecutionModeActual.REAL
