"""RunwayStillPortraitProvider tests — §19 Step 5.c (SESSION 244).

Covers the Runway adapter's Protocol contract using
``monkeypatch`` on ``_portrait_task_attempt`` and
``_download_image_to_disk`` — both imported from
``character_studio_client``. The adapter's transport-boundary
choice is anchored by ``test_transport_receives_spec_prompt_verbatim``:
if the adapter ever sneaks composition in before the transport
call, that test fires.

Real-provider smoke lives in ``test_runway_real_smoke.py`` and
is opt-in via ``PORTRAIT_PROVIDER_REAL_SMOKE=1`` + a real
``RUNWAY_API_KEY``.
"""
from __future__ import annotations

from pathlib import Path
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
from app.services.portrait_provider.runway import (
    RunwayStillPortraitProvider,
    _SUPPORTED_ASPECT_RATIOS,
    _SUPPORTED_MODELS,
)


# ---- Fixtures --------------------------------------------------


def _spec(
    *,
    execution_mode: ExecutionMode = ExecutionMode.FORCED_MOCK,
    prompt: str = "final composed prompt for runway",
    aspect_ratio: str = "1280:720",
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


def _real_settings(
    *, api_key: str = "runway-fake-key", force_mock: bool = False,
) -> Settings:
    return Settings(
        runway_api_key=api_key,
        runway_force_mock=force_mock,
    )


def _stub_task_attempt(
    output_url: str = "https://runway.example/output.png",
    task_id: str = "task_stub",
) -> "_StubTaskAttempt":
    return _StubTaskAttempt(output_url=output_url, task_id=task_id)


class _StubTaskAttempt:
    """Records each ``_portrait_task_attempt`` call and returns a
    canned ``(url, payload)`` tuple. Also supports a
    ``raise_exc`` mode that raises ``CharacterStudioError`` for
    retry-path testing.
    """

    def __init__(
        self,
        *,
        output_url: str = "https://runway.example/output.png",
        task_id: str = "task_stub",
        raise_exc: BaseException | None = None,
        raise_only_on_attempt: int | None = None,
    ) -> None:
        self.calls: list[tuple[dict, Any]] = []
        self._output_url = output_url
        self._task_id = task_id
        self._raise_exc = raise_exc
        self._raise_only_on_attempt = raise_only_on_attempt

    def __call__(self, body: dict, settings: Any, **kwargs: Any):
        attempt = len(self.calls) + 1
        self.calls.append((body, settings))
        if self._raise_exc is not None:
            if (
                self._raise_only_on_attempt is None
                or attempt == self._raise_only_on_attempt
            ):
                raise self._raise_exc
        return (self._output_url, {"id": self._task_id, "status": "SUCCEEDED"})


def _stub_download(content: bytes = b"\x89PNG\r\n\x1a\nSTUB-RUNWAY"):
    """Returns a callable that writes ``content`` bytes to the
    target path — mirrors ``_download_image_to_disk`` shape.
    """
    def _download(url: str, target: Path, timeout: float = 60.0) -> int:
        Path(target).write_bytes(content)
        return len(content)
    return _download


def _patch_transport(
    monkeypatch,
    *,
    task_attempt=None,
    download=None,
) -> _StubTaskAttempt:
    """Install stubs onto both call sites (the adapter imports
    the helpers directly — patch the imported names in the
    adapter's module namespace, not the source module)."""
    ta = task_attempt or _stub_task_attempt()
    dl = download or _stub_download()
    monkeypatch.setattr(
        "app.services.portrait_provider.runway._portrait_task_attempt",
        ta,
    )
    monkeypatch.setattr(
        "app.services.portrait_provider.runway._download_image_to_disk",
        dl,
    )
    return ta


# ---- Capabilities ----------------------------------------------


def test_capabilities_returns_runway_still_portrait_provenance():
    provider = RunwayStillPortraitProvider(_real_settings())
    caps = provider.capabilities()
    assert caps.provider_name == PortraitProviderName.RUNWAY_STILL_PORTRAIT
    assert caps.provider_model == "gen4_image"
    # SESSION 244 pre-5.a decision: still-portrait provenance is
    # RUNWAY_STILL_PORTRAIT, never RUNWAY_AVATAR.
    assert caps.provider_name.value == "runway_still_portrait"


def test_capabilities_supported_models_is_current_shipped_set():
    """Adapter advertises only what the current shipped code
    exercises. gen4_image_turbo is documented but not shipped
    (SESSION 077 regression audit); adding it back to
    supported_models requires reintroducing the seed-reference
    logic + upstream Runway resolving the ratio issue.
    """
    caps = RunwayStillPortraitProvider(_real_settings()).capabilities()
    assert caps.supported_models == ("gen4_image",)


def test_capabilities_supported_aspect_ratios_is_1280x720_only():
    """Runway supports more ratios in principle; adapter
    advertises only the ratio the shipped code has verified
    against the current model (factual capabilities per §9.5).
    """
    caps = RunwayStillPortraitProvider(_real_settings()).capabilities()
    assert caps.supported_aspect_ratios == ("1280:720",)


def test_capabilities_max_prompt_length_is_none():
    """Runway does not document a hard prompt-length ceiling for
    gen4_image and the adapter has not empirically validated
    one. ``None`` is the factual answer.
    """
    caps = RunwayStillPortraitProvider(_real_settings()).capabilities()
    assert caps.max_prompt_length is None


def test_capabilities_execution_modes_include_all_three():
    caps = RunwayStillPortraitProvider(_real_settings()).capabilities()
    assert ExecutionMode.REAL_REQUIRED in caps.execution_modes_supported
    assert ExecutionMode.AUTO in caps.execution_modes_supported
    assert ExecutionMode.FORCED_MOCK in caps.execution_modes_supported


def test_capabilities_is_deterministic_false():
    caps = RunwayStillPortraitProvider(_real_settings()).capabilities()
    assert caps.is_deterministic is False


def test_provider_name_method_matches_capabilities():
    provider = RunwayStillPortraitProvider(_real_settings())
    assert provider.provider_name() == provider.capabilities().provider_name


# ---- Input validation ------------------------------------------


def test_unsupported_model_raises_loud():
    with pytest.raises(UnsupportedModelError):
        RunwayStillPortraitProvider(_real_settings()).generate_still_portrait(
            _spec(provider_model="gen4_image_turbo"),
        )


def test_supported_model_override_accepted():
    provider = RunwayStillPortraitProvider(_real_settings())
    for model in _SUPPORTED_MODELS:
        result = provider.generate_still_portrait(
            _spec(execution_mode=ExecutionMode.FORCED_MOCK, provider_model=model),
        )
        assert result.provider_model == model


def test_unsupported_aspect_ratio_raises_loud():
    with pytest.raises(UnsupportedAspectRatioError):
        RunwayStillPortraitProvider(_real_settings()).generate_still_portrait(
            _spec(aspect_ratio="1:1"),
        )


def test_all_advertised_aspect_ratios_accepted_by_validation():
    """Whatever ``capabilities().supported_aspect_ratios``
    advertises, the adapter's own validation must accept.
    Catches drift between the advertisement and the internal
    check.
    """
    provider = RunwayStillPortraitProvider(_real_settings())
    for aspect in _SUPPORTED_ASPECT_RATIOS:
        result = provider.generate_still_portrait(
            _spec(execution_mode=ExecutionMode.FORCED_MOCK, aspect_ratio=aspect),
        )
        assert result.image_bytes.startswith(b"\x89PNG")


def test_unavailable_input_raises_value_error():
    with pytest.raises(ValueError):
        RunwayStillPortraitProvider(_real_settings()).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.UNAVAILABLE),
        )


# ---- Execution-mode semantics (constraint 3 core) --------------


def test_force_mock_env_makes_adapter_report_unavailable_for_real_required():
    settings = _real_settings(force_mock=True)
    with pytest.raises(ProviderUnavailableError):
        RunwayStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


def test_missing_key_makes_adapter_report_unavailable_for_real_required():
    settings = _real_settings(api_key="")
    with pytest.raises(ProviderUnavailableError):
        RunwayStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


def test_force_mock_with_real_key_routes_auto_to_mock():
    """AUTO + force-mock → mock; reports MOCK. Does NOT silently
    execute real despite the key being present."""
    settings = _real_settings(api_key="runway-key", force_mock=True)
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_missing_key_routes_auto_to_mock():
    settings = _real_settings(api_key="")
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_forced_mock_always_routes_to_mock_regardless_of_key():
    settings = _real_settings(api_key="runway-key")
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.FORCED_MOCK),
    )
    assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_auto_with_real_key_calls_transport_and_reports_real(monkeypatch):
    ta = _patch_transport(monkeypatch)
    settings = _real_settings(api_key="runway-key")
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    assert result.image_bytes == b"\x89PNG\r\n\x1a\nSTUB-RUNWAY"
    assert len(ta.calls) == 1


def test_real_required_with_real_key_calls_transport_and_reports_real(monkeypatch):
    ta = _patch_transport(monkeypatch)
    settings = _real_settings(api_key="runway-key")
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
    )
    assert result.execution_mode_actual == ExecutionModeActual.REAL
    assert len(ta.calls) == 1


def test_never_emits_mock_fallback():
    """SESSION 244 constraint 3: adapters never emit
    MOCK_FALLBACK. REAL_REQUIRED raises rather than degrading.
    """
    settings = _real_settings(api_key="")
    provider = RunwayStillPortraitProvider(settings)
    for mode in (ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO):
        r = provider.generate_still_portrait(_spec(execution_mode=mode))
        assert r.execution_mode_actual != ExecutionModeActual.MOCK_FALLBACK


# ---- Transport contract (Option A architectural discipline) ----


def test_transport_receives_spec_prompt_verbatim(monkeypatch):
    """Architectural anchor for the SESSION 244 Option A
    ratification (mirrored from 5.b Stability): PortraitProvider
    consumes the already-composed final prompt and dispatches it
    verbatim through the transport helper. If the adapter ever
    reintroduces wizard-style composition (template prefix,
    framing text, style suffix) before dispatch, THIS test
    fails.

    The failure IS the audit event.
    """
    ta = _patch_transport(monkeypatch)
    caller_prompt = (
        "A tight studio portrait of a solitary woodland fox with "
        "amber eyes; front-facing; neutral gray background."
    )
    settings = _real_settings()
    RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED, prompt=caller_prompt),
    )
    assert len(ta.calls) == 1
    body, _ = ta.calls[0]
    assert body["promptText"] == caller_prompt, (
        f"Adapter mutated the prompt before dispatch — Option A "
        f"discipline broken.\n"
        f"  Caller provided: {caller_prompt!r}\n"
        f"  Adapter sent:    {body['promptText']!r}"
    )


def test_transport_body_shape_matches_runway_contract(monkeypatch):
    """Body includes model + promptText + ratio only. No
    reference_images, no template, no subject, no style. If a
    future change starts sending Runway-specific knobs that
    aren't on PortraitSpec, this test fires (SESSION 244
    constraint 5 anchor).
    """
    ta = _patch_transport(monkeypatch)
    settings = _real_settings()
    RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
    )
    body, _ = ta.calls[0]
    assert set(body.keys()) == {"model", "promptText", "ratio"}, (
        f"Body added vendor-specific knobs — expected exactly "
        f"{{model, promptText, ratio}}, got {sorted(body.keys())}"
    )


def test_transport_sends_gen4_image_model(monkeypatch):
    ta = _patch_transport(monkeypatch)
    settings = _real_settings()
    RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
    )
    body, _ = ta.calls[0]
    assert body["model"] == "gen4_image"
    assert body["ratio"] == "1280:720"


# ---- Retry & failure handling ----------------------------------


def test_transient_failure_triggers_one_retry(monkeypatch):
    """Runway ``[code=INTERNAL.*]`` on first attempt → adapter
    retries once. Reuses the ``_is_transient_failure`` helper
    from ``character_studio_client``.
    """
    from app.services.character_studio_client import CharacterStudioError

    ta = _stub_task_attempt()
    # Make it raise transient on attempt 1, succeed on attempt 2.
    ta._raise_exc = CharacterStudioError(
        "portrait task FAILED: internal glitch [code=INTERNAL.BAD_OUTPUT.CODE01]"
    )
    ta._raise_only_on_attempt = 1
    _patch_transport(monkeypatch, task_attempt=ta)

    settings = _real_settings()
    # Speed up the 2-second retry sleep in the adapter to keep
    # tests fast.
    monkeypatch.setattr(
        "app.services.portrait_provider.runway.time.sleep",
        lambda *_a, **_k: None,
    )
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
    )
    # Should have called transport twice — first failed, second
    # succeeded.
    assert len(ta.calls) == 2
    assert result.execution_mode_actual == ExecutionModeActual.REAL


def test_non_transient_failure_raises_immediately(monkeypatch):
    """Runway rejection that is NOT transient (no INTERNAL.*
    prefix, no timeout) → surfaces immediately, no retry."""
    from app.services.character_studio_client import CharacterStudioError

    ta = _stub_task_attempt()
    ta._raise_exc = CharacterStudioError(
        "portrait task FAILED: content policy violation"
    )
    _patch_transport(monkeypatch, task_attempt=ta)

    settings = _real_settings()
    with pytest.raises(ProviderRequestFailedError) as exc_info:
        RunwayStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )
    assert "content policy violation" in str(exc_info.value)
    # Non-transient — exactly one attempt.
    assert len(ta.calls) == 1


def test_persistent_transient_failure_raises_after_second_attempt(monkeypatch):
    """Transient failure on BOTH attempts → surfaces as
    ProviderRequestFailedError after the second attempt (no
    third try)."""
    from app.services.character_studio_client import CharacterStudioError

    ta = _stub_task_attempt()
    ta._raise_exc = CharacterStudioError(
        "portrait task timed out"
    )
    # No raise_only_on_attempt — raises every time.
    _patch_transport(monkeypatch, task_attempt=ta)

    settings = _real_settings()
    monkeypatch.setattr(
        "app.services.portrait_provider.runway.time.sleep",
        lambda *_a, **_k: None,
    )
    with pytest.raises(ProviderRequestFailedError) as exc_info:
        RunwayStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )
    assert "timed out" in str(exc_info.value)
    # Two attempts, then raise.
    assert len(ta.calls) == 2


def test_download_failure_raises_provider_request_failed(monkeypatch):
    """A successful task_attempt followed by a download failure
    surfaces as ProviderRequestFailedError, wrapping the
    ``CharacterStudioError`` from ``_download_image_to_disk``.
    """
    from app.services.character_studio_client import CharacterStudioError

    ta = _stub_task_attempt()

    def _failing_download(url: str, target: Path, timeout: float = 60.0) -> int:
        raise CharacterStudioError("download error: signature mismatch")

    _patch_transport(monkeypatch, task_attempt=ta, download=_failing_download)

    settings = _real_settings()
    with pytest.raises(ProviderRequestFailedError) as exc_info:
        RunwayStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )
    assert "download" in str(exc_info.value).lower()


def test_empty_bytes_raises(monkeypatch):
    ta = _stub_task_attempt()
    _patch_transport(
        monkeypatch,
        task_attempt=ta,
        download=_stub_download(content=b""),
    )
    settings = _real_settings()
    with pytest.raises(ProviderRequestFailedError):
        RunwayStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
        )


# ---- Cross-adapter mock parity (constraint 7 determinism) ------


def test_runway_mock_bytes_equal_standalone_mock_bytes():
    """SESSION 244 constraint 7: when Runway routes to mock, it
    emits byte-identical output to the standalone Mock adapter
    for the same PortraitSpec.
    """
    settings = _real_settings(api_key="")  # unavailable → force mock path
    runway = RunwayStillPortraitProvider(settings)
    mock_adapter = MockStillPortraitProvider()
    spec = _spec(execution_mode=ExecutionMode.FORCED_MOCK)
    runway_bytes = runway.generate_still_portrait(spec).image_bytes
    mock_bytes = mock_adapter.generate_still_portrait(spec).image_bytes
    assert runway_bytes == mock_bytes


def test_runway_mock_bytes_equal_synth_helper_bytes():
    settings = _real_settings(api_key="")
    spec = _spec(execution_mode=ExecutionMode.FORCED_MOCK)
    runway_bytes = (
        RunwayStillPortraitProvider(settings)
        .generate_still_portrait(spec)
        .image_bytes
    )
    assert runway_bytes == synth_mock_portrait_bytes(spec)


# ---- Provenance identity preserved -----------------------------


def test_provider_stamp_is_runway_still_portrait_even_when_routed_to_mock():
    """SESSION 244 constraint 7: adapter identity is preserved
    across mock/real routing. Runway adapter routing to mock
    stamps ``provider=RUNWAY_STILL_PORTRAIT``, not ``MOCK``.
    """
    settings = _real_settings(api_key="")  # forces mock
    for mode in (ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO):
        result = RunwayStillPortraitProvider(settings).generate_still_portrait(
            _spec(execution_mode=mode),
        )
        assert result.provider == PortraitProviderName.RUNWAY_STILL_PORTRAIT
        assert result.execution_mode_actual == ExecutionModeActual.MOCK


def test_runway_provider_stamp_is_never_runway_avatar():
    """SESSION 244 pre-5.a decision anchor: still-portrait
    provenance is RUNWAY_STILL_PORTRAIT, never RUNWAY_AVATAR.
    §17.9.a Amendment on Avatar prevents domain-boundary
    conflation.
    """
    settings = _real_settings(api_key="")
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(_spec())
    # Runway avatar realtime creation stamps 'runway_avatar' —
    # still-portrait must not stamp that value even when mock-
    # routed.
    assert result.provider.value == "runway_still_portrait"
    assert result.provider.value != "runway_avatar"


def test_runway_result_is_non_qualifying_via_execution_mode_filter():
    """Runway record with ``execution_mode_actual=MOCK`` is
    filtered out by the execution-mode qualification filter —
    even though ``provider=RUNWAY_STILL_PORTRAIT`` passes the
    provider filter. Both filters are required (constraint 7).
    """
    settings = _real_settings(api_key="")
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.provider != PortraitProviderName.MOCK
    assert result.execution_mode_actual != ExecutionModeActual.REAL


# ---- Result payload shape --------------------------------------


def test_real_result_prompt_snapshot_records_task_id(monkeypatch):
    """Provenance evidence: ``prompt_snapshot`` includes the
    Runway task_id from the transport payload so a
    ``GenerationRecord`` can trace back to the exact task.
    """
    ta = _stub_task_attempt(task_id="task_xyz_123")
    _patch_transport(monkeypatch, task_attempt=ta)
    settings = _real_settings()
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED),
    )
    assert result.prompt_snapshot["task_id"] == "task_xyz_123"


def test_mock_result_prompt_snapshot_records_mock_reason():
    """Mock-routed result records WHY the mock path ran — force-
    mock vs missing key — for provenance / debugging."""
    # Force-mock reason.
    settings = _real_settings(api_key="runway-key", force_mock=True)
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.prompt_snapshot["mock_reason"] == "runway_force_mock"

    # Missing-key reason.
    settings = _real_settings(api_key="")
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.AUTO),
    )
    assert result.prompt_snapshot["mock_reason"] == "runway_api_key_absent"


def test_provider_model_defaults_to_gen4_image_when_none(monkeypatch):
    """When spec omits ``provider_model``, the adapter defaults
    to ``gen4_image`` and stamps that on the result.
    """
    ta = _patch_transport(monkeypatch)
    settings = _real_settings()
    result = RunwayStillPortraitProvider(settings).generate_still_portrait(
        _spec(execution_mode=ExecutionMode.REAL_REQUIRED, provider_model=None),
    )
    assert result.provider_model == "gen4_image"
    body, _ = ta.calls[0]
    assert body["model"] == "gen4_image"
