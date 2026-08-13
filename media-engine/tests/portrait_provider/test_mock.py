"""MockStillPortraitProvider tests — §19 Step 5.a (SESSION 244).

Covers:
* PNG validity of adapter output
* Byte-for-byte determinism (SESSION 244 constraint 7 core)
* Execution-mode semantics (SESSION 244 constraint 3 shape)
* Loud failure on invalid spec inputs (constraint 6)
* Provider-vs-execution-mode-actual as two orthogonal
  qualification filters (constraint 7 pedagogy)
"""
from __future__ import annotations

import pytest

from app.services.portrait_provider import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProviderName,
    PortraitResult,
    PortraitSpec,
    ProviderUnavailableError,
    UnsupportedAspectRatioError,
    UnsupportedModelError,
    get_provider,
)
from app.services.portrait_provider.mock import MockStillPortraitProvider


# ---- Fixtures --------------------------------------------------


def _spec(
    *,
    execution_mode: ExecutionMode = ExecutionMode.FORCED_MOCK,
    prompt: str = "test portrait",
    aspect_ratio: str = "1:1",
    provider_model: str | None = None,
    deterministic_seed: str | None = "seed-a",
) -> PortraitSpec:
    return PortraitSpec(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        execution_mode=execution_mode,
        provider_model=provider_model,
        deterministic_seed=deterministic_seed,
    )


# ---- Output shape ----------------------------------------------


def test_mock_returns_valid_png_bytes():
    """Output must start with the PNG magic signature so
    downstream image-processing code accepts it."""
    result = MockStillPortraitProvider().generate_still_portrait(_spec())
    assert isinstance(result, PortraitResult)
    assert result.image_bytes.startswith(b"\x89PNG\r\n\x1a\n"), (
        "Mock output is not a valid PNG — signature missing"
    )
    # Basic sanity — must have IHDR and IEND chunks.
    assert b"IHDR" in result.image_bytes
    assert b"IEND" in result.image_bytes


def test_mock_provider_stamp_is_mock():
    """Provenance discipline: the Mock adapter stamps
    ``provider=MOCK`` on every result. Callers use this to
    filter out plumbing from qualification queries."""
    result = MockStillPortraitProvider().generate_still_portrait(_spec())
    assert result.provider == PortraitProviderName.MOCK


def test_mock_provider_name_matches_capabilities():
    """The three provider-name surfaces
    (``provider_name()``, ``capabilities().provider_name``,
    result.provider) must agree — otherwise provenance tooling
    can disagree with itself."""
    provider = MockStillPortraitProvider()
    result = provider.generate_still_portrait(_spec())
    assert (
        provider.provider_name()
        == provider.capabilities().provider_name
        == result.provider
        == PortraitProviderName.MOCK
    )


# ---- Determinism -----------------------------------------------


def test_mock_same_spec_produces_identical_bytes_across_calls():
    """Ten calls with the same spec must produce identical
    bytes. This is the qualification-plumbing determinism
    contract — tests that expect mock stability depend on it.
    """
    provider = MockStillPortraitProvider()
    spec = _spec(prompt="stable prompt", deterministic_seed="fixed")
    outputs = [
        provider.generate_still_portrait(spec).image_bytes
        for _ in range(10)
    ]
    assert len(set(outputs)) == 1, (
        "Mock output is not deterministic — 10 calls with the "
        "same spec produced different bytes. This breaks tests "
        "that rely on stable mock output."
    )


def test_mock_different_prompt_produces_different_bytes():
    """Different prompts must produce different outputs so
    tests can distinguish mock outputs for different inputs.
    """
    provider = MockStillPortraitProvider()
    a = provider.generate_still_portrait(_spec(prompt="prompt-a")).image_bytes
    b = provider.generate_still_portrait(_spec(prompt="prompt-b")).image_bytes
    assert a != b


def test_mock_different_seed_produces_different_bytes():
    """Different deterministic_seed values must produce
    different outputs so tests exercising the seed knob can
    verify it flows into synthesis.
    """
    provider = MockStillPortraitProvider()
    a = provider.generate_still_portrait(_spec(deterministic_seed="alpha")).image_bytes
    b = provider.generate_still_portrait(_spec(deterministic_seed="beta")).image_bytes
    assert a != b


def test_mock_different_aspect_produces_different_bytes():
    """Different aspect ratios must produce different outputs
    (different dimensions → different pixel counts → different
    IDAT).
    """
    provider = MockStillPortraitProvider()
    a = provider.generate_still_portrait(_spec(aspect_ratio="1:1")).image_bytes
    b = provider.generate_still_portrait(_spec(aspect_ratio="16:9")).image_bytes
    assert a != b


# ---- Execution-mode semantics ----------------------------------


def test_mock_forced_mock_yields_actual_mock():
    """FORCED_MOCK → execution_mode_actual = MOCK."""
    result = MockStillPortraitProvider().generate_still_portrait(
        _spec(execution_mode=ExecutionMode.FORCED_MOCK),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_mock_auto_yields_actual_mock():
    """AUTO on Mock adapter → mock runs (Mock has no real
    path). Actual = MOCK.
    """
    result = MockStillPortraitProvider().generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_mock_real_required_raises_provider_unavailable():
    """REAL_REQUIRED on Mock adapter is a caller error — Mock
    has no real provider. Must raise ProviderUnavailableError.
    Never silently emit MOCK (SESSION 244 constraint 3).
    """
    with pytest.raises(ProviderUnavailableError):
        MockStillPortraitProvider().generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


def test_mock_unavailable_input_raises_value_error():
    """UNAVAILABLE is an OUTPUT-side value, not an input value.
    Sending it as input is a caller bug and must raise
    ValueError (not silently accept it).
    """
    with pytest.raises(ValueError):
        MockStillPortraitProvider().generate_still_portrait(
            _spec(execution_mode=ExecutionMode.UNAVAILABLE),
        )


def test_mock_never_emits_mock_fallback():
    """Step 5 adapters emit REAL or MOCK — never MOCK_FALLBACK.
    Verified across all supported execution modes (SESSION 244
    constraint 3).
    """
    provider = MockStillPortraitProvider()
    for mode in (ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO):
        result = provider.generate_still_portrait(_spec(execution_mode=mode))
        assert result.execution_mode_actual != ExecutionModeActual.MOCK_FALLBACK


# ---- Input validation ------------------------------------------


def test_mock_unsupported_model_raises_loud():
    """provider_model override outside capabilities.supported_models
    fails loudly — never silently substituted with the default
    (SESSION 244 constraint 6).
    """
    with pytest.raises(UnsupportedModelError):
        MockStillPortraitProvider().generate_still_portrait(
            _spec(provider_model="not-a-real-mock-model"),
        )


def test_mock_supported_model_override_accepted():
    """When the override matches supported_models, adapter
    stamps it on the result rather than the default.
    """
    provider = MockStillPortraitProvider()
    supported = provider.capabilities().supported_models
    assert len(supported) >= 1
    result = provider.generate_still_portrait(
        _spec(provider_model=supported[0]),
    )
    assert result.provider_model == supported[0]


def test_mock_unsupported_aspect_ratio_raises_loud():
    """aspect_ratio outside capabilities.supported_aspect_ratios
    fails loudly — never silently substituted.
    """
    with pytest.raises(UnsupportedAspectRatioError):
        MockStillPortraitProvider().generate_still_portrait(
            _spec(aspect_ratio="42:1"),
        )


def test_mock_all_advertised_aspect_ratios_are_actually_supported():
    """Whatever capabilities().supported_aspect_ratios advertises,
    the adapter must actually accept. Catches drift between the
    advertisement and the internal dim table.
    """
    provider = MockStillPortraitProvider()
    for aspect in provider.capabilities().supported_aspect_ratios:
        result = provider.generate_still_portrait(_spec(aspect_ratio=aspect))
        assert result.image_bytes.startswith(b"\x89PNG")


# ---- Two-filter qualification-plumbing discipline --------------


def test_mock_result_is_non_qualifying_via_provider_filter():
    """Qualification-layer filter 1: ``provider != MOCK``. The
    Mock adapter's result is filtered out by this alone.

    Encoded in a test rather than only in docs (SESSION 244
    constraint 7: 'Make that distinction visible in code/tests,
    not just documentation').
    """
    result = MockStillPortraitProvider().generate_still_portrait(_spec())
    real_providers = {
        PortraitProviderName.RUNWAY_STILL_PORTRAIT,
        PortraitProviderName.STABILITY_STILL,
    }
    assert result.provider not in real_providers, (
        "Mock adapter output must be identifiable as non-real "
        "via provider-name filter alone. If Mock ever stamps a "
        "real provider name, qualification tooling silently "
        "accepts mock evidence."
    )


def test_mock_result_is_non_qualifying_via_execution_mode_filter():
    """Qualification-layer filter 2: ``execution_mode_actual !=
    REAL``. The Mock adapter's result is also filtered out by
    this alone. Both filters must exist independently — a real
    adapter routing to mock will pass filter 1 but must be
    caught by filter 2 (verified in 5.b/5.c).
    """
    for mode in (ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO):
        result = MockStillPortraitProvider().generate_still_portrait(
            _spec(execution_mode=mode),
        )
        assert result.execution_mode_actual != ExecutionModeActual.REAL, (
            "Mock adapter output must be identifiable as non-real "
            "via execution_mode_actual filter alone."
        )


# ---- Registry --------------------------------------------------


def test_get_provider_returns_mock_for_mock_name():
    """Registry lookup: ``get_provider('mock', settings)``
    returns the Mock adapter."""
    from app.config import Settings

    provider = get_provider("mock", Settings())
    assert isinstance(provider, MockStillPortraitProvider)


def test_get_provider_raises_for_unknown_name():
    """Unknown names raise (fail-fast on misconfigured
    callers)."""
    from app.config import Settings

    from app.services.portrait_provider import PortraitProviderError

    with pytest.raises(PortraitProviderError):
        get_provider("nope", Settings())


def test_get_provider_step_5c_registry_registers_all_three_v1_adapters():
    """Deliberate ratchet from 5.b: the v1 registry is closed
    with three adapters — Mock (5.a) + Stability (5.b) + Runway
    still-portrait (5.c). This assertion evolves per SESSION 244
    operator instruction ("ratchet the registry/drift tests
    deliberately... rather than deleting the 5.b audit lock
    without explanation").

    Any future adapter that lands and gets registered without
    also updating this test fails here — the failure IS the
    audit event for the registry change.
    """
    from app.config import Settings

    from app.services.portrait_provider import PortraitProviderError
    from app.services.portrait_provider.runway import (
        RunwayStillPortraitProvider,
    )
    from app.services.portrait_provider.stability import (
        StabilityStillPortraitProvider,
    )

    # 5.a shipped: mock resolves.
    assert isinstance(get_provider("mock", Settings()), MockStillPortraitProvider)
    # 5.b shipped: stability_still resolves.
    assert isinstance(
        get_provider("stability_still", Settings()),
        StabilityStillPortraitProvider,
    )
    # 5.c shipped: runway_still_portrait resolves.
    assert isinstance(
        get_provider("runway_still_portrait", Settings()),
        RunwayStillPortraitProvider,
    )
    # No fourth adapter yet — audit event if one lands
    # unregistered.
    with pytest.raises(PortraitProviderError):
        get_provider("dall_e_3", Settings())
