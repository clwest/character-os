"""The ``audio_extract`` step primitive.

SESSION 143 / V14. Extract the audio track from a CLIP via
the media-engine's ``/internal/audio/extract/`` route. Pulls
the audio out as a standalone MP3 (or AAC / WAV) AUDIO Asset.

Unblocks the deferred ``storyboard_voiced`` starter from V13:
the recipe is storyboard concat (silent visual) +
generate_avatar_speech (narration CLIP) + audio_extract on
the narration + mix_audio over the storyboard.

### Inputs

Exactly one CLIP. Non-CLIP raises PrimitiveError.

### Params

* ``format`` (str, optional) — ``mp3`` (default) | ``aac`` |
  ``wav``. mp3 is the safest default; aac is smaller; wav is
  uncompressed and useful when feeding downstream Whisper /
  voice dubs that don't want re-encoding loss.

### Output

One AUDIO Asset whose ``file_path`` is the cached audio
file URL. ``duration_ms`` carries from the source CLIP.
"""
from __future__ import annotations

import logging

from apps.compositions.models import Asset, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


# Cost model — local ffmpeg only, no provider billing. Same
# floor as the V9 polish primitives.
_AUDIO_EXTRACT_MICROS = 40


SUPPORTED_AUDIO_FORMATS: frozenset[str] = frozenset({"mp3", "aac", "wav"})


class AudioExtractPrimitive:
    """``audio_extract`` step primitive — ffmpeg `-vn` extract."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        fmt = str(params.get("format", "mp3")).strip().lower()
        if fmt not in SUPPORTED_AUDIO_FORMATS:
            raise PrimitiveError(
                f"audio_extract format {fmt!r} not supported. "
                f"Supported: {sorted(SUPPORTED_AUDIO_FORMATS)}"
            )

        base = _expect_one_clip(resolved_inputs)
        mime_by_format = {
            "mp3": "audio/mpeg",
            "aac": "audio/mp4",
            "wav": "audio/wav",
        }

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.AUDIO,
                file_path=_deterministic_path(str(step.id), f"-extract.{fmt}"),
                duration_ms=base.duration_ms,
                mime_type=mime_by_format[fmt],
                size_bytes=base.size_bytes or 1024 * 50,
                cost_micros=_AUDIO_EXTRACT_MICROS,
                extra_source_spec={
                    "primitive_kind": "audio_extract",
                    "mock": True,
                    "source_asset_id": str(base.id),
                    "format": fmt,
                },
            )

        if not base.file_path:
            raise PrimitiveError(
                "audio_extract: base CLIP has empty file_path"
            )

        try:
            with MediaEngineClient() as client:
                result = client.audio_extract(
                    clip_url=base.file_path,
                    format=fmt,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine audio_extract failed: {exc}"
            ) from exc

        logger.info(
            "audio_extract step=%s base=%s format=%s output=%s",
            step.id, base.id, fmt, result.output_url,
        )

        return PrimitiveResult(
            asset_type=AssetType.AUDIO,
            file_path=result.output_url,
            duration_ms=base.duration_ms,
            mime_type=mime_by_format[fmt],
            size_bytes=result.size_bytes,
            cost_micros=_AUDIO_EXTRACT_MICROS,
            extra_source_spec={
                "primitive_kind": "audio_extract",
                "source_asset_id": str(base.id),
                "format": fmt,
                "media_engine_mock_mode": result.mock_mode,
            },
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _AUDIO_EXTRACT_MICROS


def _expect_one_clip(resolved_inputs) -> Asset:
    clips = []
    for entry in resolved_inputs or []:
        asset = entry.get("asset")
        if asset is None:
            continue
        if asset.asset_type != AssetType.CLIP:
            raise PrimitiveError(
                f"audio_extract expects exactly one CLIP input; got "
                f"{asset.asset_type} in slot {entry.get('slot')!r}"
            )
        clips.append(asset)
    if len(clips) != 1:
        raise PrimitiveError(
            f"audio_extract expects exactly one CLIP input; got {len(clips)}"
        )
    return clips[0]
