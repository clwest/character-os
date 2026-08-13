"""RunwayStillPortraitProvider — §19 Step 5.c (SESSION 244).

Wraps Runway's low-level image-generation primitives from
``app.services.character_studio_client``:

* ``_portrait_task_attempt`` — the actual provider transport
  (POST ``/v1/text_to_image`` + poll ``/v1/tasks/{id}`` until
  SUCCEEDED / FAILED / timeout, with Runway's ``failureCode``
  preserved in the raised error message)
* ``_download_image_to_disk`` — signed-URL streaming download
  with content-type check and size cap
* ``_is_transient_failure`` — pure error-message inspector that
  distinguishes Runway-side flakes (INTERNAL.* codes, timeouts)
  from operator-fixable rejections (content policy, prompt
  moderation)
* ``_runway_headers`` — reused indirectly via ``_portrait_task_attempt``

Layering finding (SESSION 244, 5.c inspection — a specific
instance of the 5.b architectural finding):

    Runway's image stack has a clean seam BELOW composition.
    ``_generate_portrait_real(prompt, target, settings)`` already
    accepts a raw prompt (no composition inside) but writes to
    disk. The public ``generate_portrait(character, template,
    subject, style, ...)`` composes a prompt via ``build_prompt``
    before calling ``_generate_portrait_real`` — same
    composition-above-transport shape as
    ``generate_stability_portrait``.

    5.c wraps ``_portrait_task_attempt`` + ``_download_image_to_disk``
    directly rather than ``_generate_portrait_real``. Two reasons:
    (1) ``_generate_portrait_real`` returns disk-write byte count,
    not bytes — the Protocol wants bytes, so the adapter would
    need to round-trip through a temp file either way; (2) the
    retry loop in ``_generate_portrait_real`` is a small
    orchestration on top of the two reusable primitives, and
    owning it in the adapter makes the retry-plus-download path
    testable without disk-mocking. Adapter translation is thin
    (~40 lines of body + retry + temp-file + PortraitResult
    construction); it is not "duplicating substantial Runway HTTP
    behavior."

SESSION 244 constraint 3: force-mock overrides key presence;
``REAL_REQUIRED`` while force-mock or key-absent raises
``ProviderUnavailableError`` (never silently mocks); ``AUTO``
may route to mock and reports ``execution_mode_actual=MOCK``;
real execution reports ``REAL``.

SESSION 244 constraint 6: ``spec.provider_model`` outside
``capabilities().supported_models`` raises ``UnsupportedModelError``.
The current shipped model is ``gen4_image`` (SESSION 077 regression
audit locked out ``gen4_image_turbo`` — it returned
``INTERNAL.BAD_OUTPUT.CODE01`` at every ratio for our account).
Adapter advertises only what the current shipped code exercises;
adding ``gen4_image_turbo`` requires reintroducing the seed-
reference logic AND upstream Runway resolving the ratio issue.

SESSION 244 constraint 7: mock routing delegates to
``synth_mock_portrait_bytes`` for cross-adapter byte parity.
Result carries ``provider=RUNWAY_STILL_PORTRAIT`` (adapter
identity preserved) + ``execution_mode_actual=MOCK`` (routing
recorded).

Provenance: this adapter stamps
``PortraitProviderName.RUNWAY_STILL_PORTRAIT`` per §17.9.a
Amendment on Avatar (SESSION 244 pre-5.a). NEVER
``RUNWAY_AVATAR`` — that value belongs to the realtime avatar
creation lifecycle, not still-portrait generation.

Frozen paths (unchanged): ``/internal/portrait/``,
``CharacterStudioClient.generate_portrait`` public entry, wizard
Step 2 UI, ``spokespeople/views.py::generate_portrait`` action,
``MediaEngineClient.create_portrait``.
"""
from __future__ import annotations

import logging
import tempfile
import time
from pathlib import Path
from typing import Optional

from ...config import Settings
from ..character_studio_client import (
    CharacterStudioError,
    _download_image_to_disk,
    _is_transient_failure,
    _portrait_task_attempt,
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

logger = logging.getLogger(__name__)

# Canonical still-portrait model per SESSION 077 regression audit
# (see ``character_studio_client._IMAGE_MODEL`` docstring). Adapter
# advertises only this model — reintroducing gen4_image_turbo would
# require the seed-reference logic AND upstream Runway resolving
# the ratio issue.
_DEFAULT_MODEL = "gen4_image"
_SUPPORTED_MODELS: tuple[str, ...] = (_DEFAULT_MODEL,)

# The shipped Runway still-portrait code exercises 1280:720 only.
# Runway's gen4_image API accepts other ratios in principle, but
# advertising unverified combos would violate factual-capabilities
# discipline (§9.5). Add more from live evidence.
_SUPPORTED_ASPECT_RATIOS: tuple[str, ...] = ("1280:720",)


class RunwayStillPortraitProvider:
    """PortraitProvider bound to Runway's still-image endpoints
    via the low-level task/download primitives from
    ``character_studio_client``.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ---- Protocol methods --------------------------------------

    def generate_still_portrait(self, spec: PortraitSpec) -> PortraitResult:
        self._validate_spec(spec)

        # Execution-mode routing (SESSION 244 constraint 3).
        if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
            if self._settings.runway_mock:
                raise ProviderUnavailableError(
                    "Runway is unavailable — force-mock is on or "
                    "RUNWAY_API_KEY is unset. REAL_REQUIRED cannot "
                    "silently degrade to mock (SESSION 244 constraint 3)."
                )
            return self._run_real(spec)

        if spec.execution_mode == ExecutionMode.FORCED_MOCK:
            return self._run_mock(spec)

        # AUTO — real if available, mock otherwise.
        if self._settings.runway_mock:
            return self._run_mock(spec)
        return self._run_real(spec)

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=PortraitProviderName.RUNWAY_STILL_PORTRAIT,
            provider_model=_DEFAULT_MODEL,
            supported_models=_SUPPORTED_MODELS,
            supported_aspect_ratios=_SUPPORTED_ASPECT_RATIOS,
            # Runway does not document a hard prompt-length ceiling
            # for gen4_image and the adapter has not empirically
            # validated one. Advertising a number would be
            # aesthetic-adjacent invention; None is the factual
            # answer until benchmark evidence sets a floor.
            max_prompt_length=None,
            is_deterministic=False,
            execution_modes_supported=frozenset({
                ExecutionMode.FORCED_MOCK,
                ExecutionMode.AUTO,
                ExecutionMode.REAL_REQUIRED,
            }),
        )

    def provider_name(self) -> PortraitProviderName:
        return PortraitProviderName.RUNWAY_STILL_PORTRAIT

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
                f"supported_aspect_ratios={list(_SUPPORTED_ASPECT_RATIOS)}. "
                f"Runway still-portrait shipped code exercises 1280:720 "
                f"only; other ratios would need empirical verification "
                f"before being advertised."
            )

    def _run_mock(self, spec: PortraitSpec) -> PortraitResult:
        start = time.monotonic()
        image_bytes = synth_mock_portrait_bytes(spec)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return PortraitResult(
            image_bytes=image_bytes,
            provider=PortraitProviderName.RUNWAY_STILL_PORTRAIT,
            provider_model=spec.provider_model or _DEFAULT_MODEL,
            execution_mode_actual=ExecutionModeActual.MOCK,
            prompt_snapshot={
                "prompt": spec.prompt,
                "aspect_ratio": spec.aspect_ratio,
                "provider_model": spec.provider_model or _DEFAULT_MODEL,
                "requested_execution_mode": spec.execution_mode.value,
                "mock_reason": (
                    "runway_force_mock" if self._settings.runway_force_mock
                    else "runway_api_key_absent"
                ),
            },
            elapsed_ms=elapsed_ms,
        )

    def _run_real(self, spec: PortraitSpec) -> PortraitResult:
        api_key = (self._settings.runway_api_key or "").strip()
        if not api_key:
            # Belt-and-braces: ``runway_mock`` returned False AND
            # the key is missing — should be unreachable, but a
            # defensive raise beats a mysterious 401 from Runway.
            raise ProviderUnavailableError(
                "Runway adapter reached real path but RUNWAY_API_KEY "
                "is empty."
            )

        model = spec.provider_model or _DEFAULT_MODEL
        body: dict = {
            "model": model,
            "promptText": spec.prompt,
            "ratio": spec.aspect_ratio,
        }

        start = time.monotonic()
        # Single retry on transient INTERNAL.* / timeout — same
        # shape as ``_generate_portrait_real`` but orchestrated
        # here so it can be exercised without disk-mocking.
        last_exc: Optional[CharacterStudioError] = None
        out_url: Optional[str] = None
        payload: Optional[dict] = None
        for attempt in (1, 2):
            try:
                out_url, payload = _portrait_task_attempt(body, self._settings)
                break
            except CharacterStudioError as exc:
                last_exc = exc
                if attempt == 1 and _is_transient_failure(str(exc)):
                    logger.warning(
                        "runway still-portrait transient-fail attempt=%d "
                        "msg=%s — retrying once",
                        attempt, exc,
                    )
                    time.sleep(2)
                    continue
                raise ProviderRequestFailedError(
                    f"runway task: {exc!s}"[:300],
                    status_code=None,
                ) from exc

        if out_url is None:
            # Defensive — the loop above always returns or raises.
            raise ProviderRequestFailedError(
                f"runway task: {last_exc!s}"[:300]
                if last_exc
                else "runway task: exhausted attempts with no result",
                status_code=None,
            )

        # Download to a temp file, then read back to bytes. The
        # temp-file dance is deliberate: reuses the shipped
        # ``_download_image_to_disk`` which owns streaming, size
        # cap, and content-type verification. A separate
        # bytes-returning helper would duplicate ~25 lines of
        # streaming logic for marginal benefit.
        with tempfile.NamedTemporaryFile(
            suffix=".png", delete=False,
        ) as tmp:
            tmp_path = Path(tmp.name)
        try:
            try:
                _download_image_to_disk(out_url, tmp_path)
            except CharacterStudioError as exc:
                raise ProviderRequestFailedError(
                    f"runway download: {exc!s}"[:300],
                    status_code=None,
                ) from exc
            image_bytes = tmp_path.read_bytes()
        finally:
            tmp_path.unlink(missing_ok=True)

        elapsed_ms = int((time.monotonic() - start) * 1000)

        if not image_bytes:
            raise ProviderRequestFailedError(
                "runway returned zero bytes",
                status_code=None,
            )

        return PortraitResult(
            image_bytes=image_bytes,
            provider=PortraitProviderName.RUNWAY_STILL_PORTRAIT,
            provider_model=model,
            execution_mode_actual=ExecutionModeActual.REAL,
            prompt_snapshot={
                "prompt": spec.prompt,
                "aspect_ratio": spec.aspect_ratio,
                "provider_model": model,
                "requested_execution_mode": spec.execution_mode.value,
                "task_id": (payload or {}).get("id") if payload else None,
                "output_url_scheme": (
                    out_url.split(":", 1)[0] if ":" in out_url else None
                ),
            },
            elapsed_ms=elapsed_ms,
        )
