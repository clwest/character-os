"""The ``synthesize_voiceover_audio`` step primitive.

SESSION 211 / VO.1. First primitive in the voiceover arc.
Generates a standalone AUDIO asset from text + a voice_spec
WITHOUT firing the avatar-video pipeline (rule 3 of
``docs/design/VOICEOVER_V1.md``). ~$0.01 per call vs ~$0.25
for the existing "fire a whole ``talking_head`` and
``audio_extract`` from it" workaround — 25× cheaper, which is
the entire reason this primitive exists.

The output is an ``Asset(AUDIO, VOICEOVER_AUDIO)`` row carrying
the script text + resolved voice_id + provider + duration +
cost in ``source_spec`` so VO.2's ``overlay_audio_at_offset``
can read everything it needs from the AUDIO asset alone.

### Params

* ``script`` (str, required) — the text to speak.
* ``voice_spec`` (dict, required) — exactly-one-of:
  * ``{spokesperson_id: <uuid>}`` — looks up the Teammate
    in the composition's workspace + uses ``Teammate.voice_id``.
    Workspace mismatch raises (rule 2).
  * ``{voice_id: <runway/eleven id>}`` — uses the id directly.
  * ``{voice_design: <text prompt>}`` — fires ``design_voice``
    as a sub-call to mint a new voice_id, then synthesizes.
* ``model`` (str, optional) — TTS model id. Default
  ``eleven_multilingual_v2``.
* ``provider`` (str, optional) — provider chain override.
  Default ``auto`` (Runway-first with ElevenLabs fallback per
  Q-vo-2). Other values: ``runway`` / ``elevenlabs`` / ``mock``.

### Output

One ``Asset(asset_type=AUDIO, role=VOICEOVER_AUDIO)`` whose
``file_path`` is the media-engine-served MP3 URL and whose
``source_spec`` carries the contract-rule-1 provenance fields.

### Workspace isolation

Rule 2 enforced shell-side. The spokesperson lookup goes through
the composition's workspace; cross-workspace voice_specs raise
``PrimitiveError`` rather than silently leaking the wrong voice.
"""
from __future__ import annotations

import logging
import uuid
from typing import Any

from apps.compositions.models import AssetRole, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# Cost model — TTS is cheap. The placeholder mirrors the scope-
# lock's "~$0.01" target; refine after VO.6 dogfood actuals.
# Voice-design path adds the existing V10 design cost.
_TTS_MICROS = 10_000           # ~$0.01
_VOICE_DESIGN_MICROS = 100_000  # ~$0.10 — same shape as V10's _VOICE_DESIGN_MICROS

# Hard upper limit on script length. Mirrors the media-engine
# Pydantic ``max_length=5000`` on ``InternalTtsCreate.text`` so
# the shell fails before the HTTP roundtrip rather than after.
_MAX_SCRIPT_CHARS = 5000

# Estimated chars/sec for the mock-mode duration heuristic.
# Same constant as ``avatar_speech._AVATAR_SPEECH_CHARS_PER_SECOND``
# so VO.2's offset math is stable between mock and real renders.
_TTS_CHARS_PER_SECOND = 11
_TTS_MIN_DURATION_MS = 1_000
_TTS_MAX_DURATION_MS = 60_000


def _estimate_duration_ms(chars: int) -> int:
    """Floor / ceiling-clamped mock duration in ms."""
    chars = max(0, chars)
    if chars == 0:
        return _TTS_MIN_DURATION_MS
    seconds = chars / _TTS_CHARS_PER_SECOND
    return max(
        _TTS_MIN_DURATION_MS,
        min(_TTS_MAX_DURATION_MS, int(seconds * 1000)),
    )


def _resolve_voice_spec(
    voice_spec: dict[str, Any] | None, composition,
) -> tuple[str, dict[str, Any], int]:
    """Resolve ``voice_spec`` to a concrete voice_id + the
    provenance dict to merge into ``source_spec``.

    Returns ``(voice_id, provenance, extra_cost_micros)``.

    Exactly-one-of discriminator (Q-vo-4): the operator supplies
    one of ``spokesperson_id`` / ``voice_id`` / ``voice_design``.
    Multiple keys or none raises ``PrimitiveError``.

    Rule 2 — workspace-scoped resolution. The Teammate path
    rejects cross-workspace refs at lookup time.
    """
    if not isinstance(voice_spec, dict) or not voice_spec:
        raise PrimitiveError(
            "voice_spec is required; pass exactly one of "
            "{spokesperson_id} / {voice_id} / {voice_design}"
        )

    keys = {k for k in voice_spec if voice_spec.get(k)}
    expected = {"spokesperson_id", "voice_id", "voice_design"}
    populated = keys & expected
    if len(populated) != 1:
        raise PrimitiveError(
            f"voice_spec must have exactly one of {sorted(expected)} "
            f"set; got {sorted(populated)!r} populated"
        )
    discriminator = next(iter(populated))

    if discriminator == "spokesperson_id":
        return _resolve_spokesperson_path(voice_spec, composition)
    if discriminator == "voice_id":
        return _resolve_voice_id_path(voice_spec)
    return _resolve_voice_design_path(voice_spec, composition)


def _resolve_spokesperson_path(voice_spec, composition) -> tuple[str, dict, int]:
    """``{spokesperson_id: <uuid>}`` — workspace-scoped lookup."""
    raw = str(voice_spec["spokesperson_id"]).strip()
    try:
        sp_id = uuid.UUID(raw)
    except (ValueError, TypeError) as exc:
        raise PrimitiveError(
            f"voice_spec.spokesperson_id is not a valid UUID: {raw!r}"
        ) from exc

    from apps.spokespeople.models import Teammate

    try:
        spokesperson = Teammate.objects.get(
            id=sp_id,
            workspace_id=composition.workspace_id,
        )
    except Teammate.DoesNotExist as exc:
        raise PrimitiveError(
            f"voice_spec.spokesperson_id {sp_id} not found in workspace "
            f"{composition.workspace_id} (rule 2: cross-workspace "
            f"voice_specs are rejected)"
        ) from exc

    if not spokesperson.voice_id:
        raise PrimitiveError(
            f"spokesperson {spokesperson.name!r} has no voice_id bound; "
            f"design a voice first or pass voice_spec.voice_id directly"
        )

    return (
        spokesperson.voice_id,
        {
            "voice_spec_discriminator": "spokesperson_id",
            "spokesperson_id": str(sp_id),
            "spokesperson_name": spokesperson.name,
        },
        0,
    )


def _resolve_voice_id_path(voice_spec) -> tuple[str, dict, int]:
    """``{voice_id: <str>}`` — used as-is."""
    raw = str(voice_spec["voice_id"]).strip()
    if not raw:
        raise PrimitiveError("voice_spec.voice_id cannot be empty")
    return (
        raw,
        {
            "voice_spec_discriminator": "voice_id",
            "voice_id": raw,
        },
        0,
    )


def _resolve_voice_design_path(voice_spec, composition) -> tuple[str, dict, int]:
    """``{voice_design: <prompt>}`` — fire design_voice sub-call."""
    description = str(voice_spec["voice_design"]).strip()
    if len(description) < 4:
        raise PrimitiveError(
            "voice_spec.voice_design must be at least 4 characters"
        )
    name = str(voice_spec.get("name") or "VO Voice")

    try:
        with MediaEngineClient() as client:
            result = client.design_voice(
                description=description,
                name=name,
            )
    except MediaEngineError as exc:
        raise PrimitiveError(
            f"media-engine design_voice failed during voice_design "
            f"resolution: {exc}"
        ) from exc

    if not result.voice_id:
        raise PrimitiveError(
            "media-engine design_voice returned empty voice_id"
        )

    return (
        result.voice_id,
        {
            "voice_spec_discriminator": "voice_design",
            "voice_id": result.voice_id,
            "voice_design_description": description,
            "voice_design_name": name,
            "design_mock_mode": result.mock_mode,
        },
        _VOICE_DESIGN_MICROS,
    )


def _mime_for_audio_url(audio_url: str) -> str:
    """Best-effort mime from the URL suffix. TTS providers emit
    MP3 by default; defensive defaulting for variants."""
    lowered = audio_url.lower()
    if lowered.endswith(".wav"):
        return "audio/wav"
    if lowered.endswith(".aac") or lowered.endswith(".m4a"):
        return "audio/mp4"
    return "audio/mpeg"


class SynthesizeVoiceoverAudioPrimitive:
    """``synthesize_voiceover_audio`` step primitive — TTS-only
    voiceover synthesis. VO.1 ships behind the
    ``TextToSpeechProvider`` Protocol; this shell side handles
    the voice_spec discriminator + Asset persistence."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        script = str(params.get("script", "")).strip()
        if not script:
            raise PrimitiveError(
                "synthesize_voiceover_audio requires a non-empty script"
            )
        if len(script) > _MAX_SCRIPT_CHARS:
            raise PrimitiveError(
                f"script exceeds {_MAX_SCRIPT_CHARS}-char cap "
                f"(got {len(script)} chars)"
            )

        voice_spec = params.get("voice_spec")
        model = str(params.get("model") or "eleven_multilingual_v2")
        provider_pref = str(params.get("provider") or "auto").strip().lower()

        composition = step.composition

        # Resolve voice_spec → concrete voice_id + provenance.
        # Voice-design path may incur an extra cost (design_voice
        # sub-call); accumulate into total cost_micros.
        voice_id, voice_provenance, extra_cost = _resolve_voice_spec(
            voice_spec, composition,
        )

        if mock_mode:
            duration_ms = _estimate_duration_ms(len(script))
            return PrimitiveResult(
                asset_type=AssetType.AUDIO,
                file_path=_deterministic_path(
                    str(step.id), "-voiceover.mp3",
                ),
                duration_ms=duration_ms,
                mime_type="audio/mpeg",
                size_bytes=1024 * 50,
                cost_micros=_TTS_MICROS + extra_cost,
                extra_source_spec={
                    "primitive_kind": "synthesize_voiceover_audio",
                    "mock": True,
                    "script": script,
                    "script_chars": len(script),
                    "voice_id": voice_id,
                    "model": model,
                    "provider": "mock",
                    "provider_pref": provider_pref,
                    **voice_provenance,
                },
                role=AssetRole.VOICEOVER_AUDIO.value,
            )

        try:
            with MediaEngineClient() as client:
                result = client.tts(
                    text=script,
                    voice_id=voice_id,
                    model=model,
                    provider=provider_pref,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine tts failed: {exc}"
            ) from exc

        # Defensive: media-engine should always echo back the
        # voice_id we sent; if it's empty (provider bug), use
        # our resolved value so the Asset row stays consistent.
        echoed_voice_id = result.voice_id or voice_id

        # Duration in ms — provider returns seconds. Floor at the
        # mock estimator value so VO.2's offset math has a
        # non-zero anchor even on a provider that returned 0.
        if result.duration_seconds > 0:
            duration_ms = int(result.duration_seconds * 1000)
        else:
            duration_ms = _estimate_duration_ms(len(script))

        logger.info(
            "synthesize_voiceover_audio step=%s voice=%s provider=%s "
            "chars=%d duration=%dms cost_micros=%d",
            step.id, echoed_voice_id, result.provider,
            len(script), duration_ms,
            result.cost_micros + extra_cost,
        )

        return PrimitiveResult(
            asset_type=AssetType.AUDIO,
            file_path=result.audio_url,
            duration_ms=duration_ms,
            mime_type=_mime_for_audio_url(result.audio_url),
            size_bytes=result.size_bytes or None,
            cost_micros=result.cost_micros + extra_cost,
            extra_source_spec={
                "primitive_kind": "synthesize_voiceover_audio",
                "script": script,
                "script_chars": len(script),
                "voice_id": echoed_voice_id,
                "model": result.model,
                "provider": result.provider,
                "provider_pref": provider_pref,
                "media_engine_mock_mode": result.mock_mode,
                **voice_provenance,
            },
            role=AssetRole.VOICEOVER_AUDIO.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        """Per-step cost estimate. Voice-design path costs more
        (one design_voice call + one TTS call); otherwise it's
        TTS-only."""
        voice_spec = (params or {}).get("voice_spec") or {}
        if isinstance(voice_spec, dict) and voice_spec.get("voice_design"):
            return _TTS_MICROS + _VOICE_DESIGN_MICROS
        return _TTS_MICROS
