"""RunwayVoiceProvider — §19 Step 6.b (SESSION 245).

Wraps the reusable Runway voice-authoring transport functions
introduced (renamed) in this same slice:

* ``audio_client.runway_design_voice_transport`` — POST
  ``/v1/voices`` with ``from.type=text`` + poll to READY.
* ``voice_clone_client.runway_clone_voice_transport`` — POST
  ``/v1/voices`` with ``from.type=audio`` + poll to READY.

Both are transport-boundary primitives (thin HTTP + poll, no
composition, no persistence, no business logic). The adapter
composes only what the VoiceDesignProvider contract requires:
input validation before spending credits, execution-mode
routing, provenance stamping.

Deliberate NON-couplings:

* Does NOT call the ``/internal/voices/design/`` or
  ``/internal/voices/`` HTTP routes. Those are frozen paths per
  §17.9.a; delegation lives in Step 11.
* Does NOT call the ``design_brand_voice()`` composition
  service (idempotency, campaign persistence, file I/O — all
  live above the transport boundary).
* Does NOT call any ``TextToSpeechProvider`` code (§17.4.a
  bullet 1: voice authoring never synthesizes speech).
* Does NOT import from ``shell/`` (monorepo boundary
  conventions).

Mock code paths (``FORCED_MOCK``, or ``AUTO`` when the provider
is unavailable) call ``synth_mock_voice_id`` from the mock
module so the Runway adapter's mock output is BYTE-FOR-BYTE
identical to ``MockVoiceProvider``'s output for the same spec.
Cross-adapter parity is a Step 6 contract; a future cross-
adapter parity test will pin it.

SESSION 245 ratification 4: ``AUTO`` never silently falls back
to mock after a real request has begun and failed. Real
failures raise ``VoiceProviderRequestFailedError``; mock is
purely an availability-routing decision made BEFORE any wire
call.
"""
from __future__ import annotations

import time

import httpx

from ...config import Settings
from ..audio_client import AudioError, runway_design_voice_transport
from ..voice_clone_client import (
    SUPPORTED_AUDIO_MIMES,
    runway_clone_voice_transport,
)
from . import (
    ExecutionMode,
    ExecutionModeActual,
    ReferenceAudioTooLargeError,
    UnsupportedAudioFormatError,
    UnsupportedModelError,
    VoiceAuthoringResult,
    VoiceCloneSpec,
    VoiceDesignSpec,
    VoiceOperation,
    VoiceProviderCapabilities,
    VoiceProviderName,
    VoiceProviderRequestFailedError,
    VoiceProviderUnavailableError,
)
from .mock import synth_mock_voice_id


# Runway design uses ElevenLabs' text-to-voice model surfaced
# through Runway's ``/v1/voices`` endpoint. The constant mirrors
# ``audio_client._VOICE_DESIGN_MODEL`` — not imported to keep
# the coupling one-directional (adapter reads transport
# constants only through function calls, not private module
# state).
_RUNWAY_DESIGN_MODEL = "eleven_multilingual_ttv_v2"
_SUPPORTED_DESIGN_MODELS: tuple[str, ...] = (_RUNWAY_DESIGN_MODEL,)

# Runway documented cap for reference audio is 10 MB. Advertised
# honestly so callers can pre-validate before spending credits.
_MAX_REFERENCE_BYTES = 10 * 1024 * 1024
_MIN_DESCRIPTION_CHARS = 20  # Runway's documented floor
_MAX_DESCRIPTION_CHARS = 1000  # matches the HTTP schema envelope
_MAX_AUTHORING_SECONDS = 90  # Runway design/clone poll deadline

_DEFAULT_VOICE_NAME = "Character OS Voice"
_ACCEPTED_AUDIO_MIMES: tuple[str, ...] = tuple(sorted(SUPPORTED_AUDIO_MIMES.keys()))


class RunwayVoiceProvider:
    """VoiceDesignProvider adapter for Runway's ``/v1/voices``
    endpoint (both design and clone operations).

    Adapter identity is preserved across mock/real routing per
    Step 5 discipline: force-mock and unavailable-in-AUTO both
    still stamp ``provider=RUNWAY_VOICE``; only
    ``execution_mode_actual`` distinguishes what actually ran.
    """

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    # ---- Protocol methods --------------------------------------

    def design_voice(self, spec: VoiceDesignSpec) -> VoiceAuthoringResult:
        _validate_design_spec(spec)
        if spec.execution_mode == ExecutionMode.FORCED_MOCK:
            return self._mock_design(spec)
        if self._settings.runway_mock:
            if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
                raise VoiceProviderUnavailableError(
                    "RunwayVoiceProvider cannot satisfy REAL_REQUIRED — "
                    "settings.runway_mock is True (missing "
                    "RUNWAY_API_KEY or RUNWAY_FORCE_MOCK=1). Callers "
                    "must configure a live Runway API key to run real."
                )
            return self._mock_design(spec)
        return self._real_design(spec)

    def clone_voice(self, spec: VoiceCloneSpec) -> VoiceAuthoringResult:
        _validate_clone_spec(spec)
        if spec.execution_mode == ExecutionMode.FORCED_MOCK:
            return self._mock_clone(spec)
        if self._settings.runway_mock:
            if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
                raise VoiceProviderUnavailableError(
                    "RunwayVoiceProvider cannot satisfy REAL_REQUIRED — "
                    "settings.runway_mock is True (missing "
                    "RUNWAY_API_KEY or RUNWAY_FORCE_MOCK=1). Callers "
                    "must configure a live Runway API key to run real."
                )
            return self._mock_clone(spec)
        return self._real_clone(spec)

    def capabilities(self) -> VoiceProviderCapabilities:
        return VoiceProviderCapabilities(
            provider_name=VoiceProviderName.RUNWAY_VOICE,
            supports_design=True,
            supports_clone=True,
            supported_design_models=_SUPPORTED_DESIGN_MODELS,
            accepted_audio_mimes=_ACCEPTED_AUDIO_MIMES,
            max_reference_bytes=_MAX_REFERENCE_BYTES,
            min_reference_seconds=10.0,
            max_reference_seconds=300.0,
            min_description_chars=_MIN_DESCRIPTION_CHARS,
            max_description_chars=_MAX_DESCRIPTION_CHARS,
            max_authoring_seconds=_MAX_AUTHORING_SECONDS,
            is_synchronous=True,
            execution_modes_supported=frozenset(
                {
                    ExecutionMode.FORCED_MOCK,
                    ExecutionMode.AUTO,
                    ExecutionMode.REAL_REQUIRED,
                },
            ),
        )

    # ---- Real code paths --------------------------------------

    def _real_design(self, spec: VoiceDesignSpec) -> VoiceAuthoringResult:
        start = time.monotonic()
        name = spec.name or _DEFAULT_VOICE_NAME
        try:
            voice_id, preview_url = runway_design_voice_transport(
                description=spec.description,
                name=name,
                settings=self._settings,
            )
        except AudioError as exc:
            raise VoiceProviderRequestFailedError(
                f"runway design failed: {exc}",
                status_code=None,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise VoiceProviderRequestFailedError(
                f"runway design http error: {exc}",
                status_code=exc.response.status_code if exc.response else None,
            ) from exc
        except httpx.HTTPError as exc:
            raise VoiceProviderRequestFailedError(
                f"runway design transport error: {exc}",
                status_code=None,
            ) from exc
        elapsed_ms = int((time.monotonic() - start) * 1000)
        # The provider-model override, if the caller supplied one,
        # matched supported_design_models via _validate_design_spec.
        # Runway's current API accepts only the one model; we stamp
        # what was actually used.
        model_used = spec.provider_model or _RUNWAY_DESIGN_MODEL
        return VoiceAuthoringResult(
            voice_id=voice_id,
            provider=VoiceProviderName.RUNWAY_VOICE,
            operation=VoiceOperation.DESIGN,
            execution_mode_actual=ExecutionModeActual.REAL,
            provider_model=model_used,
            preview_url=preview_url or None,
            prompt_snapshot={
                "operation": VoiceOperation.DESIGN.value,
                "description": spec.description,
                "name": name,
                "provider_model": model_used,
                "requested_execution_mode": spec.execution_mode.value,
                "runway_api_base": self._settings.runway_api_base,
            },
            elapsed_ms=elapsed_ms,
        )

    def _real_clone(self, spec: VoiceCloneSpec) -> VoiceAuthoringResult:
        start = time.monotonic()
        name = spec.name or _DEFAULT_VOICE_NAME
        try:
            voice_id, final_status, preview_url = runway_clone_voice_transport(
                name=name,
                audio_bytes=spec.reference_audio,
                mime=spec.reference_mime,
                settings=self._settings,
            )
        except RuntimeError as exc:
            raise VoiceProviderRequestFailedError(
                f"runway clone failed: {exc}",
                status_code=None,
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise VoiceProviderRequestFailedError(
                f"runway clone http error: {exc}",
                status_code=exc.response.status_code if exc.response else None,
            ) from exc
        except httpx.HTTPError as exc:
            raise VoiceProviderRequestFailedError(
                f"runway clone transport error: {exc}",
                status_code=None,
            ) from exc
        elapsed_ms = int((time.monotonic() - start) * 1000)
        # Clone has no model concept on Runway either — honest
        # None rather than a placeholder string.
        return VoiceAuthoringResult(
            voice_id=voice_id,
            provider=VoiceProviderName.RUNWAY_VOICE,
            operation=VoiceOperation.CLONE,
            execution_mode_actual=ExecutionModeActual.REAL,
            provider_model=None,
            preview_url=preview_url or None,
            prompt_snapshot={
                "operation": VoiceOperation.CLONE.value,
                "name": name,
                "reference_mime": spec.reference_mime,
                "reference_bytes": len(spec.reference_audio),
                "final_status": final_status,
                "requested_execution_mode": spec.execution_mode.value,
                "runway_api_base": self._settings.runway_api_base,
            },
            elapsed_ms=elapsed_ms,
        )

    # ---- Mock code paths (adapter identity preserved) ----------

    def _mock_design(self, spec: VoiceDesignSpec) -> VoiceAuthoringResult:
        start = time.monotonic()
        # See MockVoiceProvider.design_voice — cross-adapter
        # parity requires seed material to be adapter-independent;
        # ``provider_model or ""`` (not
        # ``... or _RUNWAY_DESIGN_MODEL``) is deliberate.
        seed_bytes = (
            spec.description
            + "|"
            + (spec.deterministic_seed or "")
            + "|"
            + (spec.provider_model or "")
        ).encode("utf-8")
        voice_id = synth_mock_voice_id(
            operation=VoiceOperation.DESIGN,
            seed_bytes=seed_bytes,
            name=spec.name,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return VoiceAuthoringResult(
            voice_id=voice_id,
            # Adapter identity preserved: still stamps RUNWAY_VOICE
            # even in mock. The second filter
            # (execution_mode_actual) is what marks this row as
            # non-qualifying evidence.
            provider=VoiceProviderName.RUNWAY_VOICE,
            operation=VoiceOperation.DESIGN,
            execution_mode_actual=ExecutionModeActual.MOCK,
            provider_model=spec.provider_model or _RUNWAY_DESIGN_MODEL,
            preview_url=None,
            prompt_snapshot={
                "operation": VoiceOperation.DESIGN.value,
                "description": spec.description,
                "name": spec.name,
                "deterministic_seed": spec.deterministic_seed,
                "requested_execution_mode": spec.execution_mode.value,
                "mock_reason": (
                    "forced_mock"
                    if spec.execution_mode == ExecutionMode.FORCED_MOCK
                    else "runway_unavailable"
                ),
            },
            elapsed_ms=elapsed_ms,
        )

    def _mock_clone(self, spec: VoiceCloneSpec) -> VoiceAuthoringResult:
        import hashlib

        start = time.monotonic()
        audio_digest = hashlib.sha256(spec.reference_audio).digest()
        seed_bytes = (
            audio_digest
            + b"|"
            + spec.reference_mime.encode("utf-8")
            + b"|"
            + (spec.deterministic_seed or "").encode("utf-8")
        )
        voice_id = synth_mock_voice_id(
            operation=VoiceOperation.CLONE,
            seed_bytes=seed_bytes,
            name=spec.name,
        )
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return VoiceAuthoringResult(
            voice_id=voice_id,
            provider=VoiceProviderName.RUNWAY_VOICE,
            operation=VoiceOperation.CLONE,
            execution_mode_actual=ExecutionModeActual.MOCK,
            provider_model=None,
            preview_url=None,
            prompt_snapshot={
                "operation": VoiceOperation.CLONE.value,
                "reference_mime": spec.reference_mime,
                "reference_bytes": len(spec.reference_audio),
                "reference_audio_sha256": audio_digest.hex(),
                "name": spec.name,
                "deterministic_seed": spec.deterministic_seed,
                "requested_execution_mode": spec.execution_mode.value,
                "mock_reason": (
                    "forced_mock"
                    if spec.execution_mode == ExecutionMode.FORCED_MOCK
                    else "runway_unavailable"
                ),
            },
            elapsed_ms=elapsed_ms,
        )


# ---- Shared spec validation --------------------------------------
# Duplicates mock.py's validation for two honest reasons:
# 1. Import isolation — the mock module owns MockVoiceProvider's
#    plumbing; the Runway adapter owns its own validation with
#    real-provider constants. Sharing a helper across adapters
#    would either force a public helper module or accept a
#    cross-adapter import — the current three-file layout
#    (Protocol / Mock / Runway) mirrors PortraitProvider exactly
#    and stays uniform.
# 2. Real values differ from mock values (though 6.b has aligned
#    them to Runway reality). Duplicated code makes the divergence
#    obvious if it ever reappears.


def _validate_design_spec(spec: VoiceDesignSpec) -> None:
    if spec.execution_mode == ExecutionMode.UNAVAILABLE:
        raise ValueError(
            "VoiceDesignSpec.execution_mode=UNAVAILABLE is invalid "
            "on input. Callers use REAL_REQUIRED, AUTO, or "
            "FORCED_MOCK to describe the request."
        )
    if (
        spec.provider_model is not None
        and spec.provider_model not in _SUPPORTED_DESIGN_MODELS
    ):
        raise UnsupportedModelError(
            f"provider_model={spec.provider_model!r} not in "
            f"supported_design_models={list(_SUPPORTED_DESIGN_MODELS)}. "
            f"Unknown models fail loudly."
        )
    if len(spec.description) < _MIN_DESCRIPTION_CHARS:
        raise ValueError(
            f"VoiceDesignSpec.description too short: "
            f"{len(spec.description)} chars < "
            f"{_MIN_DESCRIPTION_CHARS} minimum. Runway would "
            f"reject."
        )
    if len(spec.description) > _MAX_DESCRIPTION_CHARS:
        raise ValueError(
            f"VoiceDesignSpec.description too long: "
            f"{len(spec.description)} chars > "
            f"{_MAX_DESCRIPTION_CHARS} maximum."
        )


def _validate_clone_spec(spec: VoiceCloneSpec) -> None:
    if spec.execution_mode == ExecutionMode.UNAVAILABLE:
        raise ValueError(
            "VoiceCloneSpec.execution_mode=UNAVAILABLE is invalid "
            "on input."
        )
    if spec.reference_mime not in _ACCEPTED_AUDIO_MIMES:
        raise UnsupportedAudioFormatError(
            f"reference_mime={spec.reference_mime!r} not in "
            f"accepted_audio_mimes={list(_ACCEPTED_AUDIO_MIMES)}."
        )
    if len(spec.reference_audio) == 0:
        raise ValueError(
            "VoiceCloneSpec.reference_audio is empty. Runway "
            "would reject."
        )
    if len(spec.reference_audio) > _MAX_REFERENCE_BYTES:
        raise ReferenceAudioTooLargeError(
            f"reference_audio {len(spec.reference_audio)} bytes > "
            f"{_MAX_REFERENCE_BYTES} maximum. Runway's documented "
            f"cap; adapter refuses rather than sending an "
            f"over-cap payload."
        )
