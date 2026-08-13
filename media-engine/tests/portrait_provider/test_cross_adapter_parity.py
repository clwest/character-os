"""Cross-adapter parity — §19 Step 5 closure verification (SESSION 244).

Consolidates the closure discipline that was originally scoped as
5.d but landed incrementally through the 5.b/5.c ratchets. This
file exists to make the CROSS-adapter invariants explicit rather
than only asserting them per-adapter — a single test that
compares behavior across Mock + Stability + Runway catches the
class of drift where two adapters gradually develop divergent
execution-mode semantics.

Confirmations required at Step 5 close (per SESSION 244 operator
instruction, closure verification list):

* Cross-adapter execution-mode parity for the shared shapes
  (REAL_REQUIRED + unavailable → same exception; FORCED_MOCK →
  MOCK actual; AUTO + unavailable → MOCK actual).
* Registry closed at exactly three adapters; drift verifier
  reasons over the full set.
* Every adapter exposes only the three Protocol methods.
* Every adapter exposes only factual capabilities.
* Deterministic Mock still passes after real adapters landed.
* Unsupported ``provider_model`` fails loudly with the SAME
  exception type on BOTH real adapters.
* Neither ``PortraitSpec``, ``PortraitResult``, nor
  ``ProviderCapabilities`` leaked provider-specific vocabulary
  after two real-provider validations.

Anchor for the closure question: "Is PortraitProvider now a real
provider abstraction rather than a wrapper around our old
product implementation?"

The tests in this file, together with the real-provider smoke
runs on 5.b and 5.c, answer YES. One shared ``PortraitSpec``
crosses Mock, Stability, and Runway; both real providers accept
``spec.prompt`` verbatim (no product composition leakage);
identical execution-mode semantics hold across all three; the
Protocol survives live execution unchanged.
"""
from __future__ import annotations

import pytest

from app.config import Settings
from app.services.portrait_provider import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProvider,
    PortraitProviderName,
    PortraitResult,
    PortraitSpec,
    ProviderUnavailableError,
    UnsupportedModelError,
    _registered_provider_names,
    get_provider,
)
from app.services.portrait_provider.mock import MockStillPortraitProvider
from app.services.portrait_provider.runway import RunwayStillPortraitProvider
from app.services.portrait_provider.stability import StabilityStillPortraitProvider


# The full v1 registry — Mock (5.a), Stability (5.b), Runway (5.c).
_V1_ADAPTER_NAMES: tuple[str, ...] = (
    PortraitProviderName.MOCK.value,
    PortraitProviderName.STABILITY_STILL.value,
    PortraitProviderName.RUNWAY_STILL_PORTRAIT.value,
)


def _all_real_adapters() -> list[PortraitProvider]:
    """Only the real-provider adapters (Stability + Runway).
    Mock has no real path; several parity tests apply only to
    the real adapters.
    """
    return [
        StabilityStillPortraitProvider(_unavailable_settings()),
        RunwayStillPortraitProvider(_unavailable_settings()),
    ]


def _unavailable_settings() -> Settings:
    """Settings with BOTH providers unavailable — no keys, no
    force-mock overrides. Real paths must raise; AUTO must
    route to mock; FORCED_MOCK must stay mock.
    """
    return Settings(
        stability_api_key="",
        stability_force_mock=False,
        runway_api_key="",
        runway_force_mock=False,
    )


def _force_mock_settings() -> Settings:
    """Both real providers force-mocked (keys present, overrides
    on) so the "real key + force-mock" branch is exercised for
    both adapters together.
    """
    return Settings(
        stability_api_key="sk-real-fake",
        stability_force_mock=True,
        runway_api_key="runway-real-fake",
        runway_force_mock=True,
    )


def _spec(
    *,
    execution_mode: ExecutionMode = ExecutionMode.FORCED_MOCK,
    prompt: str = "shared cross-adapter portrait prompt",
    aspect_ratio: str = "1:1",
    provider_model: str | None = None,
    deterministic_seed: str | None = "cross-parity",
) -> PortraitSpec:
    return PortraitSpec(
        prompt=prompt,
        aspect_ratio=aspect_ratio,
        execution_mode=execution_mode,
        provider_model=provider_model,
        deterministic_seed=deterministic_seed,
    )


# ---- Registry closure ------------------------------------------


def test_registry_closed_at_v1_three_adapters():
    """v1 registry is Mock + Stability + Runway. Landing a
    fourth adapter without extending this test is the audit
    event.
    """
    names = _registered_provider_names()
    assert set(names) == set(_V1_ADAPTER_NAMES), (
        f"Registry drift.\n"
        f"  Registered: {sorted(names)}\n"
        f"  Expected:   {sorted(_V1_ADAPTER_NAMES)}\n"
        f"If you added a fourth adapter, update this test AND "
        f"the 5.d closure narrative in the design lock doc."
    )


def test_registry_resolves_every_name_to_a_real_class():
    """Round-trip: every registered name resolves via
    ``get_provider`` to an object satisfying the Protocol.
    """
    settings = _unavailable_settings()
    for name in _V1_ADAPTER_NAMES:
        provider = get_provider(name, settings)
        assert isinstance(provider, PortraitProvider)
        assert provider.provider_name().value == name


# ---- Execution-mode parity across real adapters ----------------


def _adapter_native_aspect(adapter: PortraitProvider) -> str:
    """Return an aspect_ratio value that adapter accepts. Real
    adapters advertise disjoint dialects (see
    ``test_real_providers_speak_disjoint_aspect_ratio_dialects``)
    so cross-adapter tests must pick per-adapter values.
    """
    return adapter.capabilities().supported_aspect_ratios[0]


@pytest.mark.parametrize("adapter", _all_real_adapters(), ids=lambda a: type(a).__name__)
def test_real_required_with_unavailable_raises_provider_unavailable(adapter):
    """Both real adapters raise the SAME exception type
    (``ProviderUnavailableError``) when REAL_REQUIRED is
    requested and the provider is unavailable (no key, no
    force-mock).

    This is the load-bearing shape for callers that catch and
    handle degraded providers — if one adapter raised a
    different type, caller code would silently miss that
    provider.
    """
    with pytest.raises(ProviderUnavailableError):
        adapter.generate_still_portrait(
            _spec(
                execution_mode=ExecutionMode.REAL_REQUIRED,
                aspect_ratio=_adapter_native_aspect(adapter),
            ),
        )


def test_real_required_with_force_mock_raises_identically_on_both_real_adapters():
    """Force-mock override + REAL_REQUIRED must raise the
    identical exception type on Stability and Runway. Verified
    with real keys + force-mock env on so the branch is
    genuinely "provider is available but caller asked us to
    fake it."
    """
    settings = _force_mock_settings()
    adapters: list[PortraitProvider] = [
        StabilityStillPortraitProvider(settings),
        RunwayStillPortraitProvider(settings),
    ]
    for adapter in adapters:
        with pytest.raises(ProviderUnavailableError):
            adapter.generate_still_portrait(
                _spec(
                    execution_mode=ExecutionMode.REAL_REQUIRED,
                    aspect_ratio=_adapter_native_aspect(adapter),
                ),
            )


@pytest.mark.parametrize("adapter", _all_real_adapters(), ids=lambda a: type(a).__name__)
def test_forced_mock_yields_execution_mode_actual_mock(adapter):
    """FORCED_MOCK → adapter runs its mock code path and stamps
    ``execution_mode_actual=MOCK``. Same for both real
    adapters.
    """
    result = adapter.generate_still_portrait(
        _spec(
            execution_mode=ExecutionMode.FORCED_MOCK,
            aspect_ratio=_adapter_native_aspect(adapter),
        ),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


@pytest.mark.parametrize("adapter", _all_real_adapters(), ids=lambda a: type(a).__name__)
def test_auto_with_unavailable_yields_execution_mode_actual_mock(adapter):
    """AUTO + unavailable provider → mock. Reports MOCK. Never
    MOCK_FALLBACK (Step 5 adapters do not emit MOCK_FALLBACK
    per SESSION 244 constraint 3).
    """
    result = adapter.generate_still_portrait(
        _spec(
            execution_mode=ExecutionMode.AUTO,
            aspect_ratio=_adapter_native_aspect(adapter),
        ),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK
    assert result.execution_mode_actual != ExecutionModeActual.MOCK_FALLBACK


@pytest.mark.parametrize("adapter", _all_real_adapters(), ids=lambda a: type(a).__name__)
def test_unavailable_input_raises_value_error_uniformly(adapter):
    """``ExecutionMode.UNAVAILABLE`` on input is a caller bug
    on every adapter. Same exception type across the board.
    """
    with pytest.raises(ValueError):
        adapter.generate_still_portrait(
            _spec(
                execution_mode=ExecutionMode.UNAVAILABLE,
                aspect_ratio=_adapter_native_aspect(adapter),
            ),
        )


# ---- provider_model validation parity --------------------------


@pytest.mark.parametrize("adapter", _all_real_adapters(), ids=lambda a: type(a).__name__)
def test_unsupported_provider_model_raises_unsupported_model_error_on_both_real_adapters(
    adapter,
):
    """SESSION 244 constraint 6: unsupported provider_model
    fails loudly on both real adapters with the SAME exception
    type. Callers can catch UnsupportedModelError as a single
    contract across providers.
    """
    with pytest.raises(UnsupportedModelError):
        adapter.generate_still_portrait(
            _spec(
                provider_model="model-that-does-not-exist-anywhere",
                aspect_ratio=_adapter_native_aspect(adapter),
            ),
        )


# ---- Adapter identity preservation across mock routing ---------


def test_all_three_adapters_preserve_identity_when_mock_routed():
    """When each adapter routes to mock (via unavailable
    settings or FORCED_MOCK), it stamps its own provenance
    value — NOT ``MOCK``. This is the two-filter qualification
    discipline anchor (SESSION 244 constraint 7): filter 1
    (``provider != MOCK``) alone does not remove real adapters'
    mock-routed rows; filter 2 (``execution_mode_actual !=
    REAL``) catches them.

    Each adapter is called with an aspect_ratio it accepts —
    real adapters advertise disjoint aspect-ratio dialects
    (see ``test_real_providers_speak_disjoint_aspect_ratio_dialects``)
    so per-adapter native ratios are used.
    """
    settings = _unavailable_settings()
    stability = StabilityStillPortraitProvider(settings)
    runway = RunwayStillPortraitProvider(settings)
    mock = MockStillPortraitProvider()

    stability_r = stability.generate_still_portrait(
        _spec(aspect_ratio=_adapter_native_aspect(stability)),
    )
    runway_r = runway.generate_still_portrait(
        _spec(aspect_ratio=_adapter_native_aspect(runway)),
    )
    mock_r = mock.generate_still_portrait(
        _spec(aspect_ratio=_adapter_native_aspect(mock)),
    )

    # Adapter identity preserved.
    assert stability_r.provider == PortraitProviderName.STABILITY_STILL
    assert runway_r.provider == PortraitProviderName.RUNWAY_STILL_PORTRAIT
    assert mock_r.provider == PortraitProviderName.MOCK

    # All three routed to mock — execution_mode_actual = MOCK.
    for result in (stability_r, runway_r, mock_r):
        assert result.execution_mode_actual == ExecutionModeActual.MOCK

    # Two-filter qualification: filter 1 alone leaves Stability
    # + Runway; filter 2 alone leaves nothing. BOTH filters
    # catch everything.
    filter_1_only = [
        r for r in (stability_r, runway_r, mock_r)
        if r.provider != PortraitProviderName.MOCK
    ]
    assert len(filter_1_only) == 2, (
        "Filter 1 alone let Stability + Runway mock-routed "
        "rows through — expected."
    )
    filter_2_only = [
        r for r in (stability_r, runway_r, mock_r)
        if r.execution_mode_actual == ExecutionModeActual.REAL
    ]
    assert len(filter_2_only) == 0, (
        "Filter 2 alone caught all three — expected."
    )


# ---- Aspect-ratio dialect asymmetry (real finding) -------------


def test_real_providers_speak_disjoint_aspect_ratio_dialects():
    """Closure-verification finding: Stability and Runway
    advertise DISJOINT aspect-ratio string values.

    Stability uses aspect-ratio nomenclature (``1:1``,
    ``16:9``, ``9:16``, ...). Runway uses pixel-dimension
    nomenclature (``1280:720``). ``1280:720`` and ``16:9``
    describe the same physical aspect but as strings they
    do not compare equal.

    This is NOT provider-specific leakage into
    ``PortraitSpec``. The field is shared; only the accepted
    VALUES differ per adapter — which is exactly what
    ``capabilities().supported_aspect_ratios`` exists to
    advertise. Callers must consult capabilities before
    building specs for a given adapter (or select adapters
    whose capabilities intersect their spec).

    Explicitly asserted at Step 5 close so future changes
    that try to force a common vocabulary (e.g. adding
    ``"16:9"`` to Runway without empirical verification, or
    silently mapping strings) trip this test — the
    disagreement is intentional until benchmark evidence
    tells us otherwise.
    """
    settings = _unavailable_settings()
    stability_ratios = set(
        StabilityStillPortraitProvider(settings).capabilities().supported_aspect_ratios,
    )
    runway_ratios = set(
        RunwayStillPortraitProvider(settings).capabilities().supported_aspect_ratios,
    )
    overlap = stability_ratios & runway_ratios
    assert overlap == set(), (
        f"Stability and Runway aspect-ratio dialects now overlap: "
        f"{sorted(overlap)}. If this is an intentional change "
        f"(e.g. both providers now advertise ``16:9`` after "
        f"empirical verification), UPDATE this test to reflect "
        f"the new common vocabulary. Do not silently add a "
        f"ratio to either adapter without evidence."
    )


# ---- Cross-adapter mock byte parity (per shared ratio) ---------


def test_stability_mock_bytes_equal_standalone_mock_bytes_at_stability_ratio():
    """SESSION 244 constraint 7 within Stability's dialect:
    Stability mock-routed bytes are byte-identical to the
    standalone Mock adapter bytes for a spec both adapters
    accept.
    """
    settings = _unavailable_settings()
    spec = _spec(aspect_ratio="1:1", deterministic_seed="cross-stability-parity")
    stability_bytes = (
        StabilityStillPortraitProvider(settings)
        .generate_still_portrait(spec)
        .image_bytes
    )
    mock_bytes = MockStillPortraitProvider().generate_still_portrait(spec).image_bytes
    assert stability_bytes == mock_bytes


def test_runway_mock_bytes_equal_standalone_mock_bytes_at_runway_ratio():
    """SESSION 244 constraint 7 within Runway's dialect:
    Runway mock-routed bytes are byte-identical to the
    standalone Mock adapter bytes for a spec both adapters
    accept.
    """
    settings = _unavailable_settings()
    spec = _spec(aspect_ratio="1280:720", deterministic_seed="cross-runway-parity")
    runway_bytes = (
        RunwayStillPortraitProvider(settings)
        .generate_still_portrait(spec)
        .image_bytes
    )
    mock_bytes = MockStillPortraitProvider().generate_still_portrait(spec).image_bytes
    assert runway_bytes == mock_bytes


# ---- Shared-spec crosses all three adapters --------------------


def test_shared_prompt_crosses_all_three_adapters_without_leakage():
    """The load-bearing abstraction question: does one shared
    prompt + one shared execution_mode cross Mock + Stability +
    Runway with identical outcome shape and zero
    product-composition leakage?

    Aspect ratio is per-adapter (they speak disjoint dialects
    per ``test_real_providers_speak_disjoint_aspect_ratio_dialects``).
    Every OTHER PortraitSpec field is shared verbatim across
    all three calls. This test verifies:

    * All three return a PortraitResult of the same exact
      class (no subclassing).
    * All three route FORCED_MOCK to MOCK identically.
    * Each result carries the adapter's own provenance value
      (identity preserved).
    * Each ``prompt_snapshot["prompt"]`` equals the caller's
      prompt VERBATIM — no product composition sneaked in.
    * PortraitResult field set is stable across all three
      (no vendor-specific extra fields).

    Answers the SESSION 244 closure question: "Is
    PortraitProvider now proven to be a real provider
    abstraction rather than a wrapper around our old product
    implementation?" YES — the SHARED parts of the spec cross
    all three adapters identically; the per-adapter parts
    (aspect ratio dialect) are honestly advertised via
    ``capabilities().supported_aspect_ratios``.
    """
    settings = _unavailable_settings()
    shared_prompt = (
        "A single shared prompt that must cross three providers "
        "unchanged."
    )
    shared_execution_mode = ExecutionMode.FORCED_MOCK
    shared_seed = "shared-abstraction-anchor"

    results: dict[str, PortraitResult] = {}
    for name in _V1_ADAPTER_NAMES:
        provider = get_provider(name, settings)
        aspect = _adapter_native_aspect(provider)
        spec = PortraitSpec(
            prompt=shared_prompt,
            aspect_ratio=aspect,
            execution_mode=shared_execution_mode,
            provider_model=None,
            deterministic_seed=shared_seed,
        )
        results[name] = provider.generate_still_portrait(spec)

    # Every adapter returned a real PortraitResult (not None,
    # not a subclass with extra fields).
    for name, result in results.items():
        assert type(result) is PortraitResult, (
            f"Adapter {name!r} returned {type(result).__name__}, "
            f"expected PortraitResult exactly."
        )

    # Every adapter reports the same execution_mode_actual
    # (MOCK, because forced).
    for name, result in results.items():
        assert result.execution_mode_actual == ExecutionModeActual.MOCK, (
            f"Adapter {name!r} did not route FORCED_MOCK to MOCK."
        )

    # Provenance identity preserved.
    assert results["mock"].provider == PortraitProviderName.MOCK
    assert results["stability_still"].provider == PortraitProviderName.STABILITY_STILL
    assert results["runway_still_portrait"].provider == PortraitProviderName.RUNWAY_STILL_PORTRAIT

    # Every adapter's prompt_snapshot recorded the caller's
    # SHARED prompt verbatim — no product-composition wrapping,
    # no wizard-template prefix, no framing text.
    for name, result in results.items():
        assert result.prompt_snapshot.get("prompt") == shared_prompt, (
            f"Adapter {name!r} did not record caller's prompt "
            f"verbatim — product-composition leakage suspected."
        )

    # PortraitResult field set is stable across all adapters —
    # no adapter smuggled extra fields via subclassing.
    expected_fields = {
        "image_bytes",
        "provider",
        "provider_model",
        "execution_mode_actual",
        "prompt_snapshot",
        "elapsed_ms",
    }
    for name, result in results.items():
        actual_fields = set(type(result).__dataclass_fields__)
        assert actual_fields == expected_fields, (
            f"Adapter {name!r} returned a PortraitResult with "
            f"different fields.\n"
            f"  Actual:   {sorted(actual_fields)}\n"
            f"  Expected: {sorted(expected_fields)}"
        )


# ---- Deterministic Mock still passes -------------------------


def test_deterministic_mock_still_passes_after_real_adapters_landed():
    """Sanity: 5.a's Mock adapter contract is unaltered by 5.b
    / 5.c landing. Same input → same bytes across 10 calls.
    This is the anchor test for closure verification per
    SESSION 244 operator instruction.
    """
    provider = MockStillPortraitProvider()
    spec = _spec(prompt="post-5c-check", deterministic_seed="fixed")
    outputs = [
        provider.generate_still_portrait(spec).image_bytes
        for _ in range(10)
    ]
    assert len(set(outputs)) == 1, (
        "Mock determinism regressed since 5.a shipped. This "
        "would break any test relying on stable mock output."
    )


# ---- ProviderCapabilities cross-adapter shape ----------------


def test_provider_capabilities_field_set_unchanged_after_all_adapters_landed():
    """The ``ProviderCapabilities`` scope-lock (set in 5.a via
    ``test_capabilities_field_set_is_scope_locked``) is
    re-anchored here explicitly at Step 5 close. If a real
    adapter added a vendor-specific capability field after
    5.a's lock, it would have to have extended the dataclass —
    caught by test_capabilities_are_factual + this pin.
    """
    from app.services.portrait_provider import ProviderCapabilities

    expected = {
        "provider_name",
        "provider_model",
        "supported_models",
        "supported_aspect_ratios",
        "max_prompt_length",
        "is_deterministic",
        "execution_modes_supported",
    }
    assert set(ProviderCapabilities.__dataclass_fields__) == expected


def test_portrait_spec_field_set_survived_two_real_provider_validations():
    """After 5.b (Stability real API) and 5.c (Runway real
    API), PortraitSpec's field set is unchanged from 5.a. This
    is the empirical answer to constraint 5 — no
    provider-specific knob was needed to make either real API
    honor the abstraction.
    """
    expected = {
        "prompt",
        "aspect_ratio",
        "execution_mode",
        "provider_model",
        "deterministic_seed",
    }
    assert set(PortraitSpec.__dataclass_fields__) == expected, (
        f"PortraitSpec fields drifted since 5.a — suspicion of "
        f"vendor-knob leakage.\n"
        f"  Actual:   {sorted(set(PortraitSpec.__dataclass_fields__))}\n"
        f"  Expected: {sorted(expected)}"
    )


def test_portrait_result_field_set_survived_two_real_provider_validations():
    """Companion to the spec pin — PortraitResult field set
    unchanged after both real-provider validations."""
    expected = {
        "image_bytes",
        "provider",
        "provider_model",
        "execution_mode_actual",
        "prompt_snapshot",
        "elapsed_ms",
    }
    assert set(PortraitResult.__dataclass_fields__) == expected
