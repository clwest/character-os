"""MockVoiceProvider — §19 Step 6.a (SESSION 245).

Deterministic voice-identity synthesis for tests, contract
testing, and adapter mock routing (6.b will reuse
``synth_mock_voice_id`` so force-mock inside the Runway adapter
produces identical ``voice_id`` values to this adapter for the
same spec).

CRITICAL — SESSION 245 constraints (mirror SESSION 244
constraint 7): this is qualification plumbing, never
qualification evidence. Records stamped ``provider=MOCK`` and
records with ``execution_mode_actual=MOCK`` are BOTH
non-qualifying. Two orthogonal filters — both must be applied
when isolating qualification-quality evidence. Tests in this
package assert the distinction is preserved.

The mock's job is to prove:
* deterministic voice-identity generation;
* Protocol method contracts (design + clone);
* execution-mode behavior;
* capability behavior;
* registry / drift behavior.

It is NOT qualification evidence and does NOT need fake media.
``preview_url`` is always ``None`` — do not fabricate a playable
URL for an audio file that does not exist (SESSION 245
ratification 5).
"""
from __future__ import annotations

import hashlib
import time

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
    VoiceProviderUnavailableError,
)


_MOCK_DESIGN_MODEL = "deterministic-mock"
_SUPPORTED_DESIGN_MODELS: tuple[str, ...] = (_MOCK_DESIGN_MODEL,)
# Mirror Runway's acceptance set (from ``voice_clone_client.SUPPORTED_AUDIO_MIMES``).
# The mock adapter accepts what a real adapter would accept so tests exercising
# clone-spec plumbing can share fixtures.
_ACCEPTED_AUDIO_MIMES: tuple[str, ...] = (
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/mp4",
    "audio/m4a",
    "audio/x-m4a",
    "audio/webm",
    "audio/ogg",
)
# Runway's documented cap for reference audio is 10 MB
# (``voice_clone_client.py`` docstring §PR AN). The client-side
# code in that module accepts up to 15 MB as a friendly-error
# zone before hitting the wire, but the honest provider limit is
# 10 MB — the mock advertises Runway's real ceiling so
# adapter-fungible tests are not misled.
_MAX_REFERENCE_BYTES = 10 * 1024 * 1024
# Runway's documented floor for design descriptions is 20 chars
# (``audio_client.py`` docstring in
# ``build_voice_description``). The HTTP schema
# ``InternalVoiceDesignCreate`` currently accepts 4+ but that is
# a composition-layer envelope — Runway rejects <20. The mock
# advertises Runway's real floor.
_MIN_DESCRIPTION_CHARS = 20
_MAX_DESCRIPTION_CHARS = 1000


def synth_mock_voice_id(
    *,
    operation: VoiceOperation,
    seed_bytes: bytes,
    name: str | None,
) -> str:
    """Deterministic ``voice_id`` from operation + seed bytes.

    Public in this module so 6.b will call the same synthesis
    when the Runway adapter routes to mock (force-mock env or
    ``AUTO`` without an API key). Cross-adapter equality for
    identical specs is a determinism test landing in the 6.b
    parity suite.

    The operation prefix (``design`` vs ``clone``) is part of
    the hash so identical byte inputs cannot collide across
    operations.

    Not exported from the package ``__all__`` — consumers who
    want mock voice IDs should use ``MockVoiceProvider`` so
    provenance is stamped correctly.
    """
    hasher = hashlib.sha256()
    hasher.update(operation.value.encode("utf-8"))
    hasher.update(b"|")
    hasher.update((name or "").encode("utf-8"))
    hasher.update(b"|")
    hasher.update(seed_bytes)
    digest = hasher.hexdigest()[:16]
    return f"mock_voice_{digest}"


class MockVoiceProvider:
    """VoiceDesignProvider returning deterministic mock voice
    IDs. Never touches an external API. Emits ``provider=MOCK``.
    """

    def design_voice(self, spec: VoiceDesignSpec) -> VoiceAuthoringResult:
        _validate_design_spec(spec)
        if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
            raise VoiceProviderUnavailableError(
                "MockVoiceProvider cannot satisfy REAL_REQUIRED — "
                "it has no real provider. Callers requesting real "
                "voice authoring must pick a real adapter."
            )
        start = time.monotonic()
        # Adapter fallback defaults are DELIBERATELY not folded
        # into seed material — cross-adapter parity requires that
        # ``synth_mock_voice_id`` sees identical bytes across the
        # Mock adapter and the Runway adapter for identical
        # specs. Each adapter defaults ``provider_model`` to
        # something different when the caller leaves it None
        # (Mock: "deterministic-mock"; Runway:
        # "eleven_multilingual_ttv_v2"). Including that default
        # would mean the same spec produced different voice_ids
        # on different adapters. Only spec-observable fields
        # contribute to the seed.
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
            provider=VoiceProviderName.MOCK,
            operation=VoiceOperation.DESIGN,
            execution_mode_actual=ExecutionModeActual.MOCK,
            provider_model=spec.provider_model or _MOCK_DESIGN_MODEL,
            preview_url=None,
            prompt_snapshot={
                "operation": VoiceOperation.DESIGN.value,
                "description": spec.description,
                "name": spec.name,
                "deterministic_seed": spec.deterministic_seed,
                "requested_execution_mode": spec.execution_mode.value,
            },
            elapsed_ms=elapsed_ms,
        )

    def clone_voice(self, spec: VoiceCloneSpec) -> VoiceAuthoringResult:
        _validate_clone_spec(spec)
        if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
            raise VoiceProviderUnavailableError(
                "MockVoiceProvider cannot satisfy REAL_REQUIRED — "
                "it has no real provider. Callers requesting real "
                "voice authoring must pick a real adapter."
            )
        start = time.monotonic()
        # Hash the reference audio bytes for determinism without
        # embedding the full audio into the seed material.
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
            provider=VoiceProviderName.MOCK,
            operation=VoiceOperation.CLONE,
            execution_mode_actual=ExecutionModeActual.MOCK,
            # Clone has no model concept on either Runway or the
            # mock — honest ``None`` rather than a placeholder.
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
            },
            elapsed_ms=elapsed_ms,
        )

    def capabilities(self) -> VoiceProviderCapabilities:
        return VoiceProviderCapabilities(
            provider_name=VoiceProviderName.MOCK,
            supports_design=True,
            supports_clone=True,
            supported_design_models=_SUPPORTED_DESIGN_MODELS,
            accepted_audio_mimes=_ACCEPTED_AUDIO_MIMES,
            max_reference_bytes=_MAX_REFERENCE_BYTES,
            # Runway's docs state 10s min and 5min max for
            # clone reference audio. The mock advertises the
            # same envelope so tests targeting adapter
            # capability parity work uniformly.
            min_reference_seconds=10.0,
            max_reference_seconds=300.0,
            min_description_chars=_MIN_DESCRIPTION_CHARS,
            max_description_chars=_MAX_DESCRIPTION_CHARS,
            # Mock returns immediately — 0 upper bound would
            # underflow the type; use a small honest number.
            max_authoring_seconds=1,
            is_synchronous=True,
            execution_modes_supported=frozenset(
                {ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO},
            ),
        )


def _validate_design_spec(spec: VoiceDesignSpec) -> None:
    """Shared design-input validation. Errors are the same
    regardless of ``execution_mode`` — if the adapter can't
    accept the input for real, it can't accept it for mock
    either (mock represents what the real path would return).

    Byte-count / length validation happens BEFORE credit-spending
    provider calls at the adapter/domain boundary
    (SESSION 245 ratification carry-in: "Validate design-
    description and clone-input constraints at the
    adapter/domain boundary before spending credits where
    practical").
    """
    if spec.execution_mode == ExecutionMode.UNAVAILABLE:
        raise ValueError(
            "VoiceDesignSpec.execution_mode=UNAVAILABLE is invalid "
            "on input. Callers use REAL_REQUIRED, AUTO, or "
            "FORCED_MOCK to describe the request."
        )
    if spec.provider_model is not None and spec.provider_model not in _SUPPORTED_DESIGN_MODELS:
        raise UnsupportedModelError(
            f"provider_model={spec.provider_model!r} not in "
            f"supported_design_models={list(_SUPPORTED_DESIGN_MODELS)}. "
            f"Unknown models fail loudly (mirrors Step 5 "
            f"constraint 6)."
        )
    if len(spec.description) < _MIN_DESCRIPTION_CHARS:
        raise ValueError(
            f"VoiceDesignSpec.description too short: "
            f"{len(spec.description)} chars < "
            f"{_MIN_DESCRIPTION_CHARS} minimum. Real Runway "
            f"design would reject with a 400."
        )
    if len(spec.description) > _MAX_DESCRIPTION_CHARS:
        raise ValueError(
            f"VoiceDesignSpec.description too long: "
            f"{len(spec.description)} chars > "
            f"{_MAX_DESCRIPTION_CHARS} maximum. Real Runway "
            f"design would reject with a 400."
        )


def _validate_clone_spec(spec: VoiceCloneSpec) -> None:
    """Shared clone-input validation. Same discipline as
    ``_validate_design_spec``.
    """
    if spec.execution_mode == ExecutionMode.UNAVAILABLE:
        raise ValueError(
            "VoiceCloneSpec.execution_mode=UNAVAILABLE is invalid "
            "on input. Callers use REAL_REQUIRED, AUTO, or "
            "FORCED_MOCK to describe the request."
        )
    if spec.reference_mime not in _ACCEPTED_AUDIO_MIMES:
        raise UnsupportedAudioFormatError(
            f"reference_mime={spec.reference_mime!r} not in "
            f"accepted_audio_mimes={list(_ACCEPTED_AUDIO_MIMES)}. "
            f"Adapters raise rather than silently converting."
        )
    if len(spec.reference_audio) == 0:
        raise ValueError(
            "VoiceCloneSpec.reference_audio is empty. Real Runway "
            "clone would reject."
        )
    if len(spec.reference_audio) > _MAX_REFERENCE_BYTES:
        raise ReferenceAudioTooLargeError(
            f"reference_audio {len(spec.reference_audio)} bytes > "
            f"{_MAX_REFERENCE_BYTES} maximum. Adapters raise "
            f"rather than silently truncating."
        )
