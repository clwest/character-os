"""MockVoiceProvider tests — §19 Step 6.a (SESSION 245).

Covers:
* Design + clone both return well-formed VoiceAuthoringResult
* Byte-for-byte determinism of the returned voice_id
* Execution-mode semantics (mirror SESSION 244 constraint 3
  shape)
* Loud failure on invalid spec inputs
* Provider-vs-execution-mode-actual as two orthogonal
  qualification filters (SESSION 245 mirroring SESSION 244
  constraint 7 pedagogy)
* Registry lookup + closed-registry audit
* SESSION 245 ratification 5: preview_url is always None
"""
from __future__ import annotations

import pytest

from app.services.voice_provider import (
    ExecutionMode,
    ExecutionModeActual,
    ReferenceAudioTooLargeError,
    UnsupportedAudioFormatError,
    UnsupportedModelError,
    VoiceAuthoringResult,
    VoiceCloneSpec,
    VoiceDesignSpec,
    VoiceOperation,
    VoiceProviderError,
    VoiceProviderName,
    VoiceProviderUnavailableError,
    get_provider,
)
from app.services.voice_provider.mock import MockVoiceProvider


# ---- Fixtures --------------------------------------------------


def _design_spec(
    *,
    execution_mode: ExecutionMode = ExecutionMode.FORCED_MOCK,
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
    execution_mode: ExecutionMode = ExecutionMode.FORCED_MOCK,
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


# ---- Design output shape ---------------------------------------


def test_design_returns_voice_authoring_result():
    result = MockVoiceProvider().design_voice(_design_spec())
    assert isinstance(result, VoiceAuthoringResult)
    assert result.voice_id.startswith("mock_voice_")


def test_design_stamps_provider_mock():
    result = MockVoiceProvider().design_voice(_design_spec())
    assert result.provider == VoiceProviderName.MOCK


def test_design_stamps_operation_design():
    result = MockVoiceProvider().design_voice(_design_spec())
    assert result.operation == VoiceOperation.DESIGN


def test_design_preview_url_is_none():
    """SESSION 245 ratification 5 — mock never fabricates a
    playable URL."""
    result = MockVoiceProvider().design_voice(_design_spec())
    assert result.preview_url is None


def test_design_provider_model_defaults_to_mock_model():
    result = MockVoiceProvider().design_voice(
        _design_spec(provider_model=None),
    )
    assert result.provider_model == "deterministic-mock"


def test_design_prompt_snapshot_records_request_evidence():
    """Snapshot content is what a GenerationRecord row would
    persist for provenance."""
    spec = _design_spec(
        description="test description exercising snapshot capture",
        deterministic_seed="fixed-seed",
        execution_mode=ExecutionMode.AUTO,
    )
    result = MockVoiceProvider().design_voice(spec)
    snap = result.prompt_snapshot
    assert snap["operation"] == "design"
    assert snap["description"] == "test description exercising snapshot capture"
    assert snap["deterministic_seed"] == "fixed-seed"
    assert snap["requested_execution_mode"] == "auto"


# ---- Clone output shape ---------------------------------------


def test_clone_returns_voice_authoring_result():
    result = MockVoiceProvider().clone_voice(_clone_spec())
    assert isinstance(result, VoiceAuthoringResult)
    assert result.voice_id.startswith("mock_voice_")


def test_clone_stamps_provider_mock():
    result = MockVoiceProvider().clone_voice(_clone_spec())
    assert result.provider == VoiceProviderName.MOCK


def test_clone_stamps_operation_clone():
    result = MockVoiceProvider().clone_voice(_clone_spec())
    assert result.operation == VoiceOperation.CLONE


def test_clone_provider_model_is_none():
    """Clone has no model concept on Runway either — honest None
    rather than a placeholder string."""
    result = MockVoiceProvider().clone_voice(_clone_spec())
    assert result.provider_model is None


def test_clone_preview_url_is_none():
    result = MockVoiceProvider().clone_voice(_clone_spec())
    assert result.preview_url is None


def test_clone_prompt_snapshot_records_reference_metadata_not_audio():
    """Snapshot must not include raw audio bytes — hash only.
    Persisting multi-megabyte reference audio into a JSON column
    would be a mistake; the digest is enough for provenance.
    """
    audio = b"AUDIO-BYTES-A" * 100
    result = MockVoiceProvider().clone_voice(
        _clone_spec(reference_audio=audio),
    )
    snap = result.prompt_snapshot
    assert snap["operation"] == "clone"
    assert snap["reference_mime"] == "audio/mpeg"
    assert snap["reference_bytes"] == len(audio)
    assert isinstance(snap["reference_audio_sha256"], str)
    assert len(snap["reference_audio_sha256"]) == 64  # sha256 hex
    # Raw bytes MUST NOT be embedded.
    for value in snap.values():
        if isinstance(value, (bytes, bytearray)):
            pytest.fail(
                f"prompt_snapshot leaked raw bytes: {value[:32]!r}..."
            )


# ---- Determinism ----------------------------------------------


def test_design_same_spec_produces_identical_voice_id():
    """Ten calls with the same spec must produce identical
    voice_ids. Cross-call determinism is the qualification-
    plumbing contract — tests that expect stable mock voice_ids
    depend on it.
    """
    provider = MockVoiceProvider()
    spec = _design_spec(
        description="stable prompt for determinism test",
        deterministic_seed="fixed",
    )
    ids = [provider.design_voice(spec).voice_id for _ in range(10)]
    assert len(set(ids)) == 1, (
        f"Mock design voice_id is not deterministic — 10 calls "
        f"produced {len(set(ids))} distinct ids: {sorted(set(ids))}"
    )


def test_clone_same_spec_produces_identical_voice_id():
    provider = MockVoiceProvider()
    spec = _clone_spec(reference_audio=b"stable" * 500, deterministic_seed="fixed")
    ids = [provider.clone_voice(spec).voice_id for _ in range(10)]
    assert len(set(ids)) == 1


def test_design_different_description_produces_different_voice_id():
    provider = MockVoiceProvider()
    a = provider.design_voice(_design_spec(description="alpha voice description")).voice_id
    b = provider.design_voice(_design_spec(description="beta voice description")).voice_id
    assert a != b


def test_clone_different_audio_produces_different_voice_id():
    provider = MockVoiceProvider()
    a = provider.clone_voice(_clone_spec(reference_audio=b"AAAA" * 1024)).voice_id
    b = provider.clone_voice(_clone_spec(reference_audio=b"BBBB" * 1024)).voice_id
    assert a != b


def test_design_different_seed_produces_different_voice_id():
    provider = MockVoiceProvider()
    a = provider.design_voice(_design_spec(deterministic_seed="alpha")).voice_id
    b = provider.design_voice(_design_spec(deterministic_seed="beta")).voice_id
    assert a != b


def test_design_and_clone_seeds_do_not_collide():
    """Design and clone with identical seed material must yield
    different voice_ids — the operation prefix is part of the
    hash so provenance stays unambiguous.
    """
    provider = MockVoiceProvider()
    same_seed = "shared-seed"
    d = provider.design_voice(_design_spec(deterministic_seed=same_seed)).voice_id
    c = provider.clone_voice(_clone_spec(deterministic_seed=same_seed)).voice_id
    assert d != c


# ---- Execution-mode semantics ---------------------------------


def test_design_forced_mock_yields_actual_mock():
    result = MockVoiceProvider().design_voice(
        _design_spec(execution_mode=ExecutionMode.FORCED_MOCK),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_clone_forced_mock_yields_actual_mock():
    result = MockVoiceProvider().clone_voice(
        _clone_spec(execution_mode=ExecutionMode.FORCED_MOCK),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_design_auto_yields_actual_mock_on_mock_adapter():
    """AUTO on Mock adapter → mock runs (Mock has no real
    path). Actual = MOCK.
    """
    result = MockVoiceProvider().design_voice(
        _design_spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_clone_auto_yields_actual_mock_on_mock_adapter():
    result = MockVoiceProvider().clone_voice(
        _clone_spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_design_real_required_raises_provider_unavailable():
    """REAL_REQUIRED on Mock adapter is a caller error — Mock
    has no real provider. Must raise VoiceProviderUnavailableError.
    Never silently emit MOCK (SESSION 245 ratification 4 shape).
    """
    with pytest.raises(VoiceProviderUnavailableError):
        MockVoiceProvider().design_voice(
            _design_spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


def test_clone_real_required_raises_provider_unavailable():
    with pytest.raises(VoiceProviderUnavailableError):
        MockVoiceProvider().clone_voice(
            _clone_spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


def test_design_unavailable_input_raises_value_error():
    with pytest.raises(ValueError):
        MockVoiceProvider().design_voice(
            _design_spec(execution_mode=ExecutionMode.UNAVAILABLE),
        )


def test_clone_unavailable_input_raises_value_error():
    with pytest.raises(ValueError):
        MockVoiceProvider().clone_voice(
            _clone_spec(execution_mode=ExecutionMode.UNAVAILABLE),
        )


def test_never_emits_mock_fallback():
    """Step 6 adapters emit REAL or MOCK — never MOCK_FALLBACK.
    Verified across all supported execution modes.
    """
    provider = MockVoiceProvider()
    for mode in (ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO):
        d = provider.design_voice(_design_spec(execution_mode=mode))
        c = provider.clone_voice(_clone_spec(execution_mode=mode))
        assert d.execution_mode_actual != ExecutionModeActual.MOCK_FALLBACK
        assert c.execution_mode_actual != ExecutionModeActual.MOCK_FALLBACK


# ---- Design input validation ----------------------------------


def test_design_description_too_short_raises_value_error():
    with pytest.raises(ValueError):
        MockVoiceProvider().design_voice(_design_spec(description="hi"))


def test_design_description_too_long_raises_value_error():
    with pytest.raises(ValueError):
        MockVoiceProvider().design_voice(
            _design_spec(description="x" * 1001),
        )


def test_design_unsupported_model_raises_loud():
    """provider_model override outside
    capabilities.supported_design_models fails loudly — never
    silently substituted with the default.
    """
    with pytest.raises(UnsupportedModelError):
        MockVoiceProvider().design_voice(
            _design_spec(provider_model="not-a-real-mock-model"),
        )


def test_design_supported_model_override_accepted():
    provider = MockVoiceProvider()
    supported = provider.capabilities().supported_design_models
    assert len(supported) >= 1
    result = provider.design_voice(_design_spec(provider_model=supported[0]))
    assert result.provider_model == supported[0]


# ---- Clone input validation -----------------------------------


def test_clone_empty_audio_raises_value_error():
    with pytest.raises(ValueError):
        MockVoiceProvider().clone_voice(_clone_spec(reference_audio=b""))


def test_clone_unsupported_mime_raises_loud():
    with pytest.raises(UnsupportedAudioFormatError):
        MockVoiceProvider().clone_voice(
            _clone_spec(reference_mime="application/octet-stream"),
        )


def test_clone_oversized_audio_raises_loud():
    """Byte-size validation happens BEFORE any provider call —
    even for the mock, mirroring the discipline that will
    apply to Runway (validate at the adapter boundary before
    spending credits).
    """
    provider = MockVoiceProvider()
    max_bytes = provider.capabilities().max_reference_bytes
    assert max_bytes is not None
    oversize = b"x" * (max_bytes + 1)
    with pytest.raises(ReferenceAudioTooLargeError):
        provider.clone_voice(_clone_spec(reference_audio=oversize))


def test_clone_all_advertised_mimes_are_accepted():
    """Whatever capabilities().accepted_audio_mimes advertises,
    the adapter must actually accept. Catches drift between the
    advertisement and the internal acceptance set.
    """
    provider = MockVoiceProvider()
    for mime in provider.capabilities().accepted_audio_mimes:
        result = provider.clone_voice(_clone_spec(reference_mime=mime))
        assert result.voice_id.startswith("mock_voice_")


# ---- Two-filter qualification-plumbing discipline -------------


def test_result_is_non_qualifying_via_provider_filter():
    """Qualification-layer filter 1: ``provider != MOCK``. The
    Mock adapter's result is filtered out by this alone.

    Encoded in a test rather than only in docs (SESSION 245
    mirroring SESSION 244 constraint 7: 'Make that distinction
    visible in code/tests, not just documentation').
    """
    real_providers = {VoiceProviderName.RUNWAY_VOICE}
    d = MockVoiceProvider().design_voice(_design_spec())
    c = MockVoiceProvider().clone_voice(_clone_spec())
    assert d.provider not in real_providers
    assert c.provider not in real_providers


def test_result_is_non_qualifying_via_execution_mode_filter():
    """Qualification-layer filter 2: ``execution_mode_actual !=
    REAL``. The Mock adapter's result is also filtered out by
    this alone. Both filters must exist independently — a real
    adapter (6.b) routing to mock will pass filter 1 but must be
    caught by filter 2.
    """
    for mode in (ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO):
        d = MockVoiceProvider().design_voice(_design_spec(execution_mode=mode))
        c = MockVoiceProvider().clone_voice(_clone_spec(execution_mode=mode))
        assert d.execution_mode_actual != ExecutionModeActual.REAL
        assert c.execution_mode_actual != ExecutionModeActual.REAL


# ---- Registry -------------------------------------------------


def test_get_provider_returns_mock_for_mock_name():
    from app.config import Settings

    provider = get_provider("mock", Settings())
    assert isinstance(provider, MockVoiceProvider)


def test_get_provider_raises_for_unknown_name():
    from app.config import Settings

    with pytest.raises(VoiceProviderError):
        get_provider("nope", Settings())


def test_get_provider_step_6b_registry_registers_mock_and_runway():
    """Deliberate ratchet from 6.a: the v1 registry is closed
    with two adapters — Mock (6.a) + Runway (6.b). This
    assertion evolves per SESSION 244 operator instruction
    carried into SESSION 245 ("ratchet the registry/drift tests
    deliberately... rather than deleting the audit lock without
    explanation").

    Any future adapter that lands and gets registered without
    also updating this test fails here — the failure IS the
    audit event for the registry change.
    """
    from app.config import Settings

    from app.services.voice_provider.runway import RunwayVoiceProvider

    # 6.a shipped: mock resolves.
    assert isinstance(get_provider("mock", Settings()), MockVoiceProvider)
    # 6.b shipped: runway_voice resolves.
    assert isinstance(
        get_provider("runway_voice", Settings()),
        RunwayVoiceProvider,
    )
    # No third adapter — audit event if one lands unregistered.
    with pytest.raises(VoiceProviderError):
        get_provider("elevenlabs_voice", Settings())


# ---- Cross-method consistency ---------------------------------


def test_design_and_clone_both_report_provider_from_capabilities():
    """Provenance surfaces on results and on capabilities must
    agree — if they diverge, downstream tooling that reads one
    can disagree with tooling that reads the other.
    """
    provider = MockVoiceProvider()
    caps_provider = provider.capabilities().provider_name
    d = provider.design_voice(_design_spec())
    c = provider.clone_voice(_clone_spec())
    assert d.provider == caps_provider
    assert c.provider == caps_provider


def test_elapsed_ms_is_non_negative():
    provider = MockVoiceProvider()
    d = provider.design_voice(_design_spec())
    c = provider.clone_voice(_clone_spec())
    assert d.elapsed_ms >= 0
    assert c.elapsed_ms >= 0
