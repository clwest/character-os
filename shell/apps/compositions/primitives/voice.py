"""V10 voice primitives — design_voice + dub_audio.

SESSION 143 / V10. Restores the hackathon's
audio_client.py capability (production-tested across 29
languages) into the V0+ composition arc.

* ``DesignVoicePrimitive`` — Runway ``/v1/voices`` voice design
  via the ``eleven_multilingual_ttv_v2`` model. Takes a text
  description, returns a VOICE Asset whose ``file_path`` is the
  Runway-hosted preview MP3 URL and whose ``source_spec`` holds
  the underlying Runway voice_id.

* ``DubAudioPrimitive`` — Runway ``/v1/voice_dubbing`` multi-
  language dub via ``eleven_voice_dubbing``. Takes an AUDIO
  Asset + target_language param, returns a dubbed AUDIO Asset.
  Supports the same 29 languages as the hackathon's
  ``SUPPORTED_DUB_LANGS`` enum.

Both primitives short-circuit to deterministic stubs in
mock-mode (RUNWAY_FORCE_MOCK / Composition.mock_mode=True).
"""
from __future__ import annotations

import logging
from typing import Any

from apps.compositions.models import Asset, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# 29 languages — must stay in sync with the media-engine's
# SUPPORTED_DUB_LANGS tuple. We duplicate the list here for
# fail-fast validation (the primitive's execute() catches
# unsupported codes before any RPC).
SUPPORTED_DUB_LANGS: frozenset[str] = frozenset({
    "en", "hi", "pt", "zh", "es", "fr", "de", "ja", "ar", "ru",
    "ko", "id", "it", "nl", "tr", "pl", "sv", "fil", "ms", "ro",
    "uk", "el", "cs", "da", "fi", "bg", "hr", "sk", "ta",
})


# Cost model — Runway voice design is a fixed-cost operation
# (~$0.10 per voice). Dubbing is per-second of source audio
# but we approximate with a small flat fee at v1 since we don't
# probe the input duration here. R&D updates the constants once
# V8/V9 cost telemetry is wired.
_VOICE_DESIGN_MICROS = 100_000   # ~$0.10
_DUB_AUDIO_MICROS = 50_000        # ~$0.05 floor


class DesignVoicePrimitive:
    """``design_voice`` step primitive — Runway custom voice
    creation."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        description = str(params.get("description", "")).strip()
        if len(description) < 4:
            raise PrimitiveError(
                "design_voice requires a description of at least 4 characters"
            )
        name = str(params.get("name", "")).strip() or "Character OS Voice"

        if mock_mode:
            stub_voice_id = f"mock_voice_{str(step.id).replace('-', '')[:12]}"
            return PrimitiveResult(
                asset_type=AssetType.VOICE,
                file_path=_deterministic_path(str(step.id), "-voice-preview.mp3"),
                mime_type="audio/mpeg",
                cost_micros=_VOICE_DESIGN_MICROS,
                extra_source_spec={
                    "primitive_kind": "design_voice",
                    "mock": True,
                    "voice_id": stub_voice_id,
                    "description_chars": len(description),
                    "name": name,
                },
            )

        try:
            with MediaEngineClient() as client:
                result = client.design_voice(
                    description=description,
                    name=name,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine design_voice failed: {exc}"
            ) from exc

        logger.info(
            "design_voice step=%s voice=%s preview=%s mock=%s",
            step.id, result.voice_id, bool(result.preview_url), result.mock_mode,
        )

        return PrimitiveResult(
            asset_type=AssetType.VOICE,
            file_path=result.preview_url or "",
            mime_type="audio/mpeg",
            cost_micros=_VOICE_DESIGN_MICROS,
            extra_source_spec={
                "primitive_kind": "design_voice",
                "voice_id": result.voice_id,
                "description_chars": len(description),
                "name": name,
                "media_engine_mock_mode": result.mock_mode,
            },
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _VOICE_DESIGN_MICROS


class DubAudioPrimitive:
    """``dub_audio`` step primitive — multilingual voice dub.

    Takes exactly one AUDIO Asset (the source) + a
    ``target_language`` param. Returns a new AUDIO Asset in
    the target language.

    v1 doesn't accept CLIP inputs — CLIP-dubbing (extract audio
    track → dub → remux into video) lands in V12 once
    ``transcribe`` adds the audio-extraction primitive.
    """

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        target_language = str(params.get("target_language", "")).strip().lower()
        if not target_language:
            raise PrimitiveError(
                "dub_audio requires a target_language param"
            )
        if target_language not in SUPPORTED_DUB_LANGS:
            raise PrimitiveError(
                f"dub_audio target_language {target_language!r} not supported. "
                f"Supported: {sorted(SUPPORTED_DUB_LANGS)}"
            )

        source = _expect_one_audio(resolved_inputs, primitive="dub_audio")

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.AUDIO,
                file_path=_deterministic_path(
                    str(step.id), f"-dub-{target_language}.mp3",
                ),
                duration_ms=source.duration_ms,
                mime_type="audio/mpeg",
                size_bytes=source.size_bytes or 1024 * 50,
                cost_micros=_DUB_AUDIO_MICROS,
                extra_source_spec={
                    "primitive_kind": "dub_audio",
                    "mock": True,
                    "source_asset_id": str(source.id),
                    "target_language": target_language,
                },
            )

        if not source.file_path:
            raise PrimitiveError(
                "dub_audio: source AUDIO has empty file_path; cannot dub"
            )

        try:
            with MediaEngineClient() as client:
                result = client.dub_audio(
                    audio_url=source.file_path,
                    target_language=target_language,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine dub_audio failed: {exc}"
            ) from exc

        logger.info(
            "dub_audio step=%s lang=%s source=%s output=%s mock=%s",
            step.id, target_language, source.id,
            result.output_url, result.mock_mode,
        )

        duration_ms = source.duration_ms
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)

        return PrimitiveResult(
            asset_type=AssetType.AUDIO,
            file_path=result.output_url,
            duration_ms=duration_ms,
            mime_type="audio/mpeg",
            size_bytes=result.size_bytes,
            cost_micros=_DUB_AUDIO_MICROS,
            extra_source_spec={
                "primitive_kind": "dub_audio",
                "source_asset_id": str(source.id),
                "target_language": target_language,
                "media_engine_mock_mode": result.mock_mode,
            },
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _DUB_AUDIO_MICROS


def _expect_one_audio(resolved_inputs, *, primitive: str) -> Asset:
    """Pick the single AUDIO asset from resolved_inputs. Raises
    PrimitiveError if zero or more than one AUDIO is supplied."""
    audios: list[Asset] = []
    for entry in resolved_inputs or []:
        asset = entry.get("asset")
        if asset is None:
            continue
        if asset.asset_type != AssetType.AUDIO:
            raise PrimitiveError(
                f"{primitive} expects exactly one AUDIO input; got "
                f"{asset.asset_type} in slot {entry.get('slot')!r}"
            )
        audios.append(asset)
    if len(audios) != 1:
        raise PrimitiveError(
            f"{primitive} expects exactly one AUDIO input; got {len(audios)}"
        )
    return audios[0]
