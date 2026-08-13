"""StabilityStillPortraitProvider — §19 Step 5.b (SESSION 244).

Wraps the low-level Stability transport helper
(``app.services.stability_ai_service.stability_request_with_retry``)
which owns HTTP, exponential-backoff retry, timeout adaptation,
response decoding, and provider error mapping.

Architectural note (SESSION 244, ratified during 5.b):

    The existing ``stability_portrait.generate_stability_portrait``
    top-level service is NOT the correct provider abstraction
    boundary. It is a legacy product-specific composition service
    that happens to perform provider transport afterward — it
    consumes ``subject`` + ``template`` + ``purpose`` and composes
    a final prompt via ``build_stability_prompt`` before
    dispatching. Wrapping it would make PortraitProvider inherit
    old wizard assumptions the abstraction was built to shed.

    PortraitProvider sits BELOW product composition and ABOVE
    provider transport. The adapter here consumes the already-
    composed final ``PortraitSpec.prompt`` and dispatches it
    verbatim through the transport helper. The composition
    layer (``build_stability_prompt``,
    ``build_stability_negative_prompt``, and the top-level
    ``generate_stability_portrait``) is untouched and continues
    to serve the frozen ``/internal/image_stability/`` direct-call
    path per §17.9.a freeze rule.

    Adapter translation this adapter owns (thin, non-reusable):

    * endpoint URL selection based on ``spec.provider_model``
    * form field assembly (prompt, output_format, aspect_ratio,
      per-model form fields where applicable)
    * timeout selection via ``calculate_adaptive_timeout``
    * response byte extraction from the transport response dict

    Adapter translation this adapter does NOT own (delegated to
    the transport helper):

    * HTTP client, retries, exponential backoff
    * transport-level errors (timeout, connection error)
    * response decoding
    * provider status-code interpretation (429/5xx retry, other
      errors surfaced)

SESSION 244 constraint 3: force-mock overrides key presence;
``REAL_REQUIRED`` while force-mock or key-absent raises
``ProviderUnavailableError`` (never silently mocks); ``AUTO``
may route to mock and reports ``execution_mode_actual=MOCK``;
real execution reports ``REAL``.

SESSION 244 constraint 6: ``spec.provider_model`` outside
``capabilities().supported_models`` raises ``UnsupportedModelError``
rather than being silently replaced with the default.

SESSION 244 constraint 7: when this adapter routes to mock, it
delegates to ``synth_mock_portrait_bytes`` so cross-adapter byte
equality for identical specs holds. The result carries
``provider=STABILITY_STILL`` (adapter identity preserved) and
``execution_mode_actual=MOCK`` (routing recorded). Two
orthogonal qualification filters remain honest.
"""
from __future__ import annotations

import time
from typing import Any

from ...config import Settings
from ..stability_ai_service import (
    calculate_adaptive_timeout,
    stability_request_with_retry,
)
from . import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProviderName,
    PortraitResult,
    PortraitSpec,
    ProviderCapabilities,
    ProviderRequestFailedError,
    ProviderUnavailableError,
    UnsupportedAspectRatioError,
    UnsupportedModelError,
)
from .mock import synth_mock_portrait_bytes


# Stability v2beta endpoints. Matches ``stability_portrait._ENDPOINTS``
# structurally but is owned here — endpoint selection is adapter
# translation, not shared transport.
_ENDPOINTS = {
    "sd3": "https://api.stability.ai/v2beta/stable-image/generate/sd3",
    "core": "https://api.stability.ai/v2beta/stable-image/generate/core",
    "ultra": "https://api.stability.ai/v2beta/stable-image/generate/ultra",
}

_DEFAULT_MODEL = "sd3-large"

# Models the adapter accepts on ``spec.provider_model``. Kept in
# sync with the shipped Stability model set. Unknown values raise
# ``UnsupportedModelError`` (SESSION 244 constraint 6).
_SUPPORTED_MODELS: tuple[str, ...] = (
    "sd3-large",
    "sd3-large-turbo",
    "sd3-medium",
    "core",
    "ultra",
)

# Aspect ratios Stability v2beta advertises. Kept intentionally
# narrower than the wild-card side of the API so unsupported
# combos fail loudly at spec-validation time rather than at
# HTTP-error time.
_SUPPORTED_ASPECT_RATIOS: tuple[str, ...] = (
    "1:1",
    "16:9",
    "9:16",
    "21:9",
    "9:21",
    "2:3",
    "3:2",
    "4:5",
    "5:4",
)

# Stability v2beta documented prompt length ceiling.
_MAX_PROMPT_LENGTH = 10_000


class StabilityStillPortraitProvider:
    """PortraitProvider bound to Stability AI's v2beta still-image
    endpoints. Uses the shared transport helper for HTTP; owns
    endpoint / form / timeout selection.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ---- Protocol methods --------------------------------------

    def generate_still_portrait(self, spec: PortraitSpec) -> PortraitResult:
        self._validate_spec(spec)

        # Execution-mode routing (SESSION 244 constraint 3).
        if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
            if self._settings.stability_mock:
                raise ProviderUnavailableError(
                    "Stability is unavailable — force-mock is on or "
                    "STABILITY_API_KEY is unset. REAL_REQUIRED cannot "
                    "silently degrade to mock (SESSION 244 constraint 3)."
                )
            return self._run_real(spec)

        if spec.execution_mode == ExecutionMode.FORCED_MOCK:
            return self._run_mock(spec)

        # AUTO — real if available, else mock.
        if self._settings.stability_mock:
            return self._run_mock(spec)
        return self._run_real(spec)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=PortraitProviderName.STABILITY_STILL,
            provider_model=_DEFAULT_MODEL,
            supported_models=_SUPPORTED_MODELS,
            supported_aspect_ratios=_SUPPORTED_ASPECT_RATIOS,
            max_prompt_length=_MAX_PROMPT_LENGTH,
            is_deterministic=False,
            execution_modes_supported=frozenset({
                ExecutionMode.FORCED_MOCK,
                ExecutionMode.AUTO,
                ExecutionMode.REAL_REQUIRED,
            }),
        )

    def provider_name(self) -> PortraitProviderName:
        return PortraitProviderName.STABILITY_STILL

    # ---- Internal helpers --------------------------------------

    def _validate_spec(self, spec: PortraitSpec) -> None:
        if spec.execution_mode == ExecutionMode.UNAVAILABLE:
            raise ValueError(
                "PortraitSpec.execution_mode=UNAVAILABLE is invalid on "
                "input. Callers use REAL_REQUIRED, AUTO, or FORCED_MOCK."
            )
        if spec.provider_model is not None and spec.provider_model not in _SUPPORTED_MODELS:
            raise UnsupportedModelError(
                f"provider_model={spec.provider_model!r} not in "
                f"supported_models={list(_SUPPORTED_MODELS)}. Unknown "
                f"models fail loudly per SESSION 244 constraint 6."
            )
        if spec.aspect_ratio not in _SUPPORTED_ASPECT_RATIOS:
            raise UnsupportedAspectRatioError(
                f"aspect_ratio={spec.aspect_ratio!r} not in "
                f"supported_aspect_ratios={list(_SUPPORTED_ASPECT_RATIOS)}."
            )
        if len(spec.prompt) > _MAX_PROMPT_LENGTH:
            raise ValueError(
                f"prompt length {len(spec.prompt)} exceeds "
                f"Stability's documented ceiling of {_MAX_PROMPT_LENGTH}."
            )

    def _run_mock(self, spec: PortraitSpec) -> PortraitResult:
        start = time.monotonic()
        image_bytes = synth_mock_portrait_bytes(spec)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return PortraitResult(
            image_bytes=image_bytes,
            provider=PortraitProviderName.STABILITY_STILL,
            provider_model=spec.provider_model or _DEFAULT_MODEL,
            execution_mode_actual=ExecutionModeActual.MOCK,
            prompt_snapshot={
                "prompt": spec.prompt,
                "aspect_ratio": spec.aspect_ratio,
                "provider_model": spec.provider_model or _DEFAULT_MODEL,
                "requested_execution_mode": spec.execution_mode.value,
                "mock_reason": (
                    "stability_force_mock" if self._settings.stability_force_mock
                    else "stability_api_key_absent"
                ),
            },
            elapsed_ms=elapsed_ms,
        )

    def _run_real(self, spec: PortraitSpec) -> PortraitResult:
        api_key = (self._settings.stability_api_key or "").strip()
        if not api_key:
            # Belt-and-braces: ``stability_mock`` returned False AND
            # the key is missing — should be unreachable, but a
            # defensive raise here beats a mysterious 401 from
            # Stability.
            raise ProviderUnavailableError(
                "Stability adapter reached real path but "
                "STABILITY_API_KEY is empty."
            )

        model = spec.provider_model or _DEFAULT_MODEL
        endpoint, sd3_model_field = self._endpoint_and_model_field(model)
        headers = {
            "authorization": f"Bearer {api_key}",
            "accept": "image/*",
        }
        form: dict[str, Any] = {
            "prompt": spec.prompt,
            "output_format": "png",
            "aspect_ratio": spec.aspect_ratio,
        }
        if sd3_model_field is not None:
            form["model"] = sd3_model_field

        timeout = calculate_adaptive_timeout(
            "sd3" if model.startswith("sd3") else model,
            num_images=1,
        )

        start = time.monotonic()
        result = stability_request_with_retry(
            url=endpoint,
            headers=headers,
            files={"none": ""},  # multipart/form-data per Stability contract
            data=form,
            timeout=timeout,
            max_retries=3,
            accept_type="image/*",
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)

        if not result.get("success"):
            raise ProviderRequestFailedError(
                f"stability api: {result.get('error', 'unknown error')[:300]}",
                status_code=result.get("status_code"),
            )
        image_bytes = result.get("content") or b""
        if not image_bytes:
            raise ProviderRequestFailedError(
                "stability returned zero bytes",
                status_code=result.get("status_code"),
            )

        return PortraitResult(
            image_bytes=image_bytes,
            provider=PortraitProviderName.STABILITY_STILL,
            provider_model=model,
            execution_mode_actual=ExecutionModeActual.REAL,
            prompt_snapshot={
                "prompt": spec.prompt,
                "aspect_ratio": spec.aspect_ratio,
                "provider_model": model,
                "requested_execution_mode": spec.execution_mode.value,
                "endpoint": endpoint,
                "retries_used": result.get("retries_used", 0),
            },
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _endpoint_and_model_field(model: str) -> tuple[str, str | None]:
        """Resolve endpoint URL and per-model form field for the
        given Stability model. sd3 sub-models (large / large-turbo
        / medium) share the sd3 endpoint and select via the
        ``model`` form field; ``core`` and ``ultra`` have their
        own endpoints and no form field.

        Assumes ``model`` has already been validated against
        ``_SUPPORTED_MODELS`` by ``_validate_spec``. Unreachable
        branch raises loudly.
        """
        if model.startswith("sd3"):
            return _ENDPOINTS["sd3"], model
        if model == "core":
            return _ENDPOINTS["core"], None
        if model == "ultra":
            return _ENDPOINTS["ultra"], None
        raise AssertionError(
            f"model {model!r} passed spec validation but has no "
            f"endpoint mapping — _SUPPORTED_MODELS + _ENDPOINTS drifted."
        )
