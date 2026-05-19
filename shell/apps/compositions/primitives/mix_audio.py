"""The ``mix_audio`` step primitive.

SESSION 143 / V7. Synchronous ffmpeg audio mix via the
media-engine's ``/internal/audio/mix/`` route. Takes one base
CLIP + N AUDIO assets + a mix_spec, produces one CLIP with the
new audio mix.

v1 ships the music_bed pattern: a single AUDIO track sits at
``mix_spec.music_gain_db`` (default -18 dB) under the base
clip's voice. The API accepts a list for forwards-compat with
multi-track mixing (V9+ might add SFX overlays).

### Inputs

* Slot ``base`` (or input[0] when no slot label) — must be a
  CLIP asset. The video stream is preserved; only audio is
  remixed.
* Slot ``music`` or ``audio`` — one or more AUDIO assets that
  get mixed underneath the base.

### Params

* ``mix_spec`` (dict, optional). v1 keys:
  * ``music_gain_db`` (float, default -18). How loud the music
    sits relative to the base voice.
  * ``fade_in_ms`` (int, default 1000) / ``fade_out_ms``
    (int, default 2000). Smooth boundary.

### Output

One CLIP Asset whose ``file_path`` is the cached mixed MP4.
Duration carried from the base clip — mix doesn't change the
video length.
"""
from __future__ import annotations

import logging
from typing import Any

from apps.compositions.models import Asset, AssetRole, AssetType
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

from .mock import PrimitiveError, PrimitiveResult, _deterministic_path

logger = logging.getLogger(__name__)


_MIX_AUDIO_MICROS = 50  # cheaper than composite (no video re-encode)


class MixAudioPrimitive:
    """``mix_audio`` step primitive."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        base_clip: Asset | None = None
        audio_tracks: list[Asset] = []

        for entry in resolved_inputs or []:
            asset = entry.get("asset")
            if asset is None:
                continue
            slot = (entry.get("slot") or "").lower()
            if asset.asset_type == AssetType.CLIP:
                if base_clip is None:
                    base_clip = asset
                else:
                    raise PrimitiveError(
                        f"mix_audio expects exactly one CLIP input; "
                        f"got a second one in slot {slot!r}"
                    )
            elif asset.asset_type == AssetType.AUDIO:
                audio_tracks.append(asset)
            else:
                raise PrimitiveError(
                    f"mix_audio expects CLIP + AUDIO inputs; got "
                    f"{asset.asset_type} in slot {slot!r}"
                )

        if base_clip is None:
            raise PrimitiveError("mix_audio requires one CLIP input as the base")
        if not audio_tracks:
            raise PrimitiveError(
                "mix_audio requires at least one AUDIO input to mix under the base"
            )

        mix_spec = (step.params or {}).get("mix_spec") or {}

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-mix.mp4"),
                duration_ms=base_clip.duration_ms,
                width=base_clip.width,
                height=base_clip.height,
                mime_type="video/mp4",
                size_bytes=base_clip.size_bytes or 1024 * 1024,
                cost_micros=_MIX_AUDIO_MICROS,
                extra_source_spec={
                    "primitive_kind": "mix_audio",
                    "mock": True,
                    "base_asset_id": str(base_clip.id),
                    "audio_asset_ids": [str(a.id) for a in audio_tracks],
                    "mix_spec": mix_spec,
                },
                role=AssetRole.COMPOSITE_OUTPUT.value,
            )

        # ---- real-mode path -----------------------------------

        if not base_clip.file_path:
            raise PrimitiveError(
                "mix_audio: base CLIP has empty file_path; cannot mix"
            )
        audio_urls: list[str] = []
        for a in audio_tracks:
            if not a.file_path:
                raise PrimitiveError(
                    "mix_audio: AUDIO input has empty file_path; cannot mix"
                )
            audio_urls.append(a.file_path)

        try:
            with MediaEngineClient() as client:
                result = client.mix_audio(
                    base_clip_url=base_clip.file_path,
                    audio_urls=audio_urls,
                    mix_spec=mix_spec,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine mix_audio failed: {exc}"
            ) from exc

        logger.info(
            "mix_audio step=%s base=%s tracks=%d output=%s mock=%s",
            step.id, base_clip.id, len(audio_tracks),
            result.output_url, result.mock_mode,
        )

        # Duration follows the base clip; audio mix doesn't
        # change video length.
        duration_ms = base_clip.duration_ms
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)

        extra: dict[str, Any] = {
            "primitive_kind": "mix_audio",
            "base_asset_id": str(base_clip.id),
            "audio_asset_ids": [str(a.id) for a in audio_tracks],
            "mix_spec": mix_spec,
            "media_engine_mock_mode": result.mock_mode,
        }

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            width=base_clip.width,
            height=base_clip.height,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_MIX_AUDIO_MICROS,
            extra_source_spec=extra,
            role=AssetRole.COMPOSITE_OUTPUT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _MIX_AUDIO_MICROS
