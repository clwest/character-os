"""StabilityStillPortraitProvider tests — §19 Step 5.b (SESSION 244).

Covers:
* Capability advertisement matches the shipped Stability model /
  aspect / prompt-length constraints
* Execution-mode semantics (SESSION 244 constraint 3): force-mock
  overrides key presence; REAL_REQUIRED + unavailable raises;
  AUTO reports actual accurately; real reports REAL
* Spec validation (constraint 6): unsupported model raises loudly;
  unsupported aspect raises loudly; overlong prompt raises
* Cross-adapter parity: force-mock inside Stability produces
  byte-identical output to the standalone Mock adapter for the
  same PortraitSpec (constraint 7 determinism-across-adapters)
* Transport contract: adapter calls
  ``stability_request_with_retry`` with the caller's prompt
  VERBATIM — no wizard-style composition (Option A / architectural
  finding)
* Failure handling: transport-level failure raises
  ``ProviderRequestFailedError`` carrying status_code + message

Real-provider smoke lives in ``test_stability_real_smoke.py`` and
is skipped unless ``PORTRAIT_PROVIDER_REAL_SMOKE=1`` is set with
a real ``STABILITY_API_KEY``.
"""
from __future__ import annotations

from typing import Any

import pytest

from app.config import Settings
from app.services.portrait_provider import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProviderName,
    PortraitSpec,
    ProviderRequestFailedError,
    ProviderUnavailableError,
    UnsupportedAspectRatioError,
    UnsupportedModelError,
)
from app.services.portrait_provider.mock import (
    MockStillPortraitProvider,
    synth_mock_portrait_bytes,
)
from app.services.portrait_provider.stability import (
    StabilityStillPortraitProvider,
    _ENDPOINTS,
    _MAX_PROMPT_LENGTH,
    _SUPPORTED_MODELS,
)


# ---- Fixtures --------------------------------------------------


def _spec(
    *,
    execution_mode: ExecutionMode = ExecutionMode.FORCED_MOCK,
    prompt: str = "final composed prompt for stability",
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


def _mock_settings(
    *, api_key: str = "sk-real-fake", force_mock: bool = False,
) -> Settings:
    return Settings(
        stability_api_key=api_key,
        stability_force_mock=force_mock,
    )


class _StubTransport:
    """Records every ``stability_request_with_retry`` call and
    returns a canned response so tests can assert on the exact
    request shape.
    """

    def __init__(
        self,
        *,
        content: bytes = b"\x89PNG\r\n\x1a\nSTUB",
        success: bool = True,
        error: str | None = None,
        status_code: int | None = 200,
    ) -> None:
        self.calls: list[dict[str, Any]] = []
        self._content = content
        self._success = success
        self._error = error
        self._status_code = status_code

    def __call__(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        if self._success:
            return {
                "success": True,
                "content": self._content,
                "retries_used": 0,
                "status_code": self._status_code or 200,
            }
        return {
            "success": False,
            "error": self._error or "stub failure",
            "status_code": self._status_code,
            "retries_used": 0,
        }


# ---- Capabilities ----------------------------------------------


def test_capabilities_returns_stability_provenance():
    provider = StabilityStillPortraitProvider(_mock_settings())
    caps = provider.capabilities()
    assert caps.provider_name == PortraitProviderName.STABILITY_STILL
    assert caps.provider_model == "sd3-large"
    assert caps.max_prompt_length == _MAX_PROMPT_LENGTH
    assert caps.is_deterministic is False
    assert "1:1" in caps.supported_aspect_ratios
    assert "16:9" in caps.supported_aspect_ratios


def test_capabilities_supported_models_matches_shipped_endpoints():
    """Every advertised model must have an endpoint mapping. If
    someone adds a model to ``_SUPPORTED_MODELS`` without also
    updating ``_endpoint_and_model_field``, this fails at the
    adapter's next invocation — this test catches it earlier.
    """
    provider = StabilityStillPortraitProvider(_mock_settings())
    for model in provider.capabilities().supported_models:
        endpoint, _ = provider._endpoint_and_model_field(model)
        assert endpoint in _ENDPOINTS.values()


def test_capabilities_execution_modes_include_real_required():
    """Unlike Mock (which cannot satisfy REAL_REQUIRED), Stability
    supports all three input modes."""
    caps = StabilityStillPortraitProvider(_mock_settings()).capabilities()
    assert ExecutionMode.REAL_REQUIRED in caps.execution_modes_supported
    assert ExecutionMode.FORCED_MOCK in caps.execution_modes_supported
    assert ExecutionMode.AUTO in caps.execution_modes_supported


def test_provider_name_method_matches_capabilities():
    provider = StabilityStillPortraitProvider(_mock_settings())
    assert provider.provider_name() == provider.capabilities().provider_name


# ---- Input validation ------------------------------------------


def test_unsupported_model_raises_loud():
    with pytest.raises(UnsupportedModelError):
        StabilityStillPortraitProvider(_mock_settings()).generate_still_portrait(
            _spec(provider_model="dall-e-3"),
        )


def test_supported_model_override_accepted():
    """Overriding provider_model to a value in
    ``supported_models`` must be accepted."""
    provider = StabilityStillPortraitProvider(_mock_settings())
    for model in _SUPPORTED_MODELS:
        result = provider.generate_still_portrait(
            _spec(execution_mode=ExecutionMode.FORCED_MOCK, provider_model=model),
        )
        assert result.provider_model == model


def test_unsupported_aspect_ratio_raises_loud():
    with pytest.raises(UnsupportedAspectRatioError):
        StabilityStillPortraitProvider(_mock_settings()).generate_still_portrait(
            _spec(aspect_ratio="42:1"),
        )


def test_overlong_prompt_raises_value_error():
    prompt = "x" * (_MAX_PROMPT_LENGTH + 1)
    with pytest.raises(ValueError):
        StabilityStillPortraitProvider(_mock_settings()).generate_still_portrait(
            _spec(prompt=prompt),
        )


def test_unavailable_input_raises_value_error():
    with pytest.raises(ValueError):
        StabilityStillPortraitProvider(_mock_settings()).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.UNAVAILABLE),
        )


# ---- Execution-mode semantics (constraint 3 core) --------------


def test_force_mock_env_makes_adapter_report_unavailable_for_real_required():
    """STABILITY_FORCE_MOCK=1 overrides key presence — even with
    a real key set, REAL_REQUIRED must raise.
    """
    settings = _mock_settings(api_key="sk-real-fake", force_mock=True)
    with pytest.raises(ProviderUnavailableError):
        StabilityStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


def test_missing_key_makes_adapter_report_unavailable_for_real_required():
    """No key present — REAL_REQUIRED raises."""
    settings = _mock_settings(api_key="", force_mock=False)
    with pytest.raises(ProviderUnavailableError):
        StabilityStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


def test_force_mock_with_real_key_still_routes_auto_to_mock():
    """AUTO + force-mock → runs mock; reports MOCK. Does not
    silently execute real just because the key is present.
    """
    settings = _mock_settings(api_key="sk-real-fake", force_mock=True)
    result = StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK
    assert result.provider == PortraitProviderName.STABILITY_STILL


def test_missing_key_routes_auto_to_mock():
    """AUTO + no key → runs mock; reports MOCK."""
    settings = _mock_settings(api_key="", force_mock=False)
    result = StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_forced_mock_always_routes_to_mock_regardless_of_key():
    """FORCED_MOCK never touches Stability — even with a real
    key + no force-mock env.
    """
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    result = StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.FORCED_MOCK),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_auto_with_real_key_and_no_force_mock_calls_transport_and_reports_real(
    monkeypatch,
):
    """AUTO + real key + no force-mock → real path runs;
    reports REAL. Uses transport monkey-patch to avoid a live
    call in the standard suite.
    """
    stub = _StubTransport()
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    result = StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    assert result.image_bytes == b"\x89PNG\r\n\x1a\nSTUB"
    assert len(stub.calls) == 1


def test_real_required_with_real_key_calls_transport_and_reports_real(
    monkeypatch,
):
    stub = _StubTransport()
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    result = StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
    )
    assert result.execution_mode_actual == ExecutionModeActual.REAL


def test_never_emits_mock_fallback():
    """SESSION 244 constraint 3: adapters never emit
    MOCK_FALLBACK. REAL_REQUIRED raises rather than degrading.
    """
    settings = _mock_settings(api_key="", force_mock=False)  # unavailable
    provider = StabilityStillPortraitProvider(settings)
    # FORCED_MOCK → MOCK
    r = provider.generate_still_portrait(_spec(execution_mode=ExecutionMode.FORCED_MOCK))
    assert r.execution_mode_actual != ExecutionModeActual.MOCK_FALLBACK
    # AUTO → MOCK (unavailable)
    r = provider.generate_still_portrait(_spec(execution_mode=ExecutionMode.AUTO))
    assert r.execution_mode_actual != ExecutionModeActual.MOCK_FALLBACK


# ---- Transport contract (Option A architectural discipline) ----


def test_transport_receives_spec_prompt_verbatim(monkeypatch):
    """Architectural anchor for the SESSION 244 5.b Option A
    ratification: PortraitProvider consumes the already-composed
    final prompt and dispatches it verbatim through the
    transport helper. If the adapter ever secretly wraps the
    prompt in wizard-style composition (template prefix,
    framing text, style suffix), THIS test fails — the transport
    would receive something other than the caller's prompt.

    The failure IS the audit event.
    """
    stub = _StubTransport()
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    caller_prompt = (
        "A tight studio portrait of a solitary woodland fox with "
        "amber eyes; front-facing composition; neutral background."
    )
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(
            execution_mode=ExecutionMode.REAL_REQUIRED,
            prompt=caller_prompt,
        ),
    )
    assert len(stub.calls) == 1
    sent_form = stub.calls[0]["data"]
    assert sent_form["prompt"] == caller_prompt, (
        f"Adapter mutated the prompt before dispatch — Option A "
        f"discipline broken.\n"
        f"  Caller provided: {caller_prompt!r}\n"
        f"  Adapter sent:    {sent_form['prompt']!r}"
    )


def test_transport_does_not_receive_negative_prompt(monkeypatch):
    """Corollary to Option A: PortraitProvider does not add
    provider-specific knobs to the request. Stability's
    ``negative_prompt`` form field must be ABSENT unless the
    Protocol grows a shared field for it — which it does not
    in 5.b (SESSION 244 constraint 5).
    """
    stub = _StubTransport()
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
    )
    sent_form = stub.calls[0]["data"]
    assert "negative_prompt" not in sent_form, (
        "Adapter added Stability-specific ``negative_prompt`` "
        "without a shared PortraitSpec field. SESSION 244 "
        "constraint 5 violation."
    )


def test_transport_receives_aspect_ratio_and_output_format(monkeypatch):
    stub = _StubTransport()
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED, aspect_ratio="16:9"),
    )
    form = stub.calls[0]["data"]
    assert form["aspect_ratio"] == "16:9"
    assert form["output_format"] == "png"


def test_transport_endpoint_selected_by_model(monkeypatch):
    """Per-model endpoint routing — sd3 sub-models share the sd3
    endpoint with a model form field; ultra + core have their
    own endpoints and no model form field.
    """
    stub = _StubTransport()
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    provider = StabilityStillPortraitProvider(settings)

    for model, expected_endpoint_key, expected_form_model in [
        ("sd3-large", "sd3", "sd3-large"),
        ("sd3-large-turbo", "sd3", "sd3-large-turbo"),
        ("sd3-medium", "sd3", "sd3-medium"),
        ("core", "core", None),
        ("ultra", "ultra", None),
    ]:
        stub.calls.clear()
        provider.generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED, provider_model=model),
        )
        call = stub.calls[0]
        assert call["url"] == _ENDPOINTS[expected_endpoint_key], (
            f"Expected endpoint {expected_endpoint_key} for model "
            f"{model}, got {call['url']}"
        )
        if expected_form_model is None:
            assert "model" not in call["data"]
        else:
            assert call["data"].get("model") == expected_form_model


def test_transport_receives_auth_header(monkeypatch):
    stub = _StubTransport()
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    settings = _mock_settings(api_key="sk-key-123", force_mock=False)
    StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
    )
    headers = stub.calls[0]["headers"]
    assert headers["authorization"] == "Bearer sk-key-123"
    assert headers["accept"] == "image/*"


# ---- Failure handling ------------------------------------------


def test_transport_failure_raises_provider_request_failed(monkeypatch):
    stub = _StubTransport(success=False, error="rate limited", status_code=429)
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    with pytest.raises(ProviderRequestFailedError) as exc_info:
        StabilityStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )
    assert "rate limited" in str(exc_info.value)
    assert exc_info.value.status_code == 429


def test_transport_zero_bytes_raises(monkeypatch):
    stub = _StubTransport(content=b"")
    monkeypatch.setattr(
        "app.services.portrait_provider.stability.stability_request_with_retry",
        stub,
    )
    settings = _mock_settings(api_key="sk-real-fake", force_mock=False)
    with pytest.raises(ProviderRequestFailedError):
        StabilityStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


# ---- Cross-adapter mock parity (constraint 7 determinism) ------


def test_stability_mock_bytes_equal_standalone_mock_bytes():
    """SESSION 244 constraint 7: when Stability routes to mock,
    it emits byte-identical output to the standalone Mock
    adapter for the same PortraitSpec. Verified so tests that
    expect stable mock outputs across adapters can depend on
    the property.
    """
    settings = _mock_settings(api_key="", force_mock=False)
    stability = StabilityStillPortraitProvider(settings)
    mock_adapter = MockStillPortraitProvider()
    spec = _spec(execution_mode=ExecutionMode.FORCED_MOCK)
    stability_bytes = stability.generate_still_portrait(spec).image_bytes
    mock_bytes = mock_adapter.generate_still_portrait(spec).image_bytes
    assert stability_bytes == mock_bytes


def test_stability_mock_bytes_equal_synth_helper_bytes():
    """The adapter's mock path calls the shared synthesis
    helper. Byte equality with a direct helper call proves
    the adapter isn't diverging.
    """
    settings = _mock_settings(api_key="", force_mock=False)
    spec = _spec(execution_mode=ExecutionMode.FORCED_MOCK)
    stability_bytes = (
        StabilityStillPortraitProvider(settings)
        .generate_still_portrait(spec)
        .image_bytes
    )
    assert stability_bytes == synth_mock_portrait_bytes(spec)


# ---- Provenance identity preserved -----------------------------


def test_provider_stamp_is_stability_even_when_routed_to_mock():
    """SESSION 244 constraint 7: adapter identity is preserved
    across mock/real routing. Stability adapter routing to mock
    stamps ``provider=STABILITY_STILL``, not ``MOCK``.
    Qualification-layer tooling relies on this for two-filter
    discipline.
    """
    settings = _mock_settings(api_key="", force_mock=False)  # forces mock
    for mode in (ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO):
        result = StabilityStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=mode),
        )
        assert result.provider == PortraitProviderName.STABILITY_STILL
        assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_stability_result_is_non_qualifying_via_execution_mode_filter():
    """Stability record with execution_mode_actual=MOCK is
    filtered out by the execution-mode qualification filter —
    even though provider != MOCK (adapter identity preserved).
    Both filters ARE needed; this test proves it.
    """
    settings = _mock_settings(api_key="", force_mock=False)
    result = StabilityStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    # Adapter identity is Stability — passes provider filter.
    assert result.provider != PortraitProviderName.MOCK
    # But execution mode reveals mock routing — caught by
    # execution-mode filter.
    assert result.execution_mode_actual != ExecutionModeActual.REAL
