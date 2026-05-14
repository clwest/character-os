"""The ``concat_clips`` step primitive.

SESSION 143 / V5. Synchronous ffmpeg-backed concat: takes N
CLIP assets from earlier steps + returns one combined CLIP.

The third leg of the ``long_form_ad`` composition (after
``split_script`` + N× ``generate_avatar_speech``). Also usable
in any later composition that needs to stitch clips —
``storyboard_voiced``, ``dialogue_scene``, the V12
``recut_teaser`` flow.

Synchronous shape (no polling) matches the media-engine's
``/internal/clips/concat/`` route: ffmpeg concat is CPU-bound
and typically finishes in 5-30 seconds.

### Inputs

* Every entry in ``resolved_inputs`` whose ``asset.asset_type``
  is ``CLIP`` is included as a concat input, in the order they
  appear in ``step.inputs``. Non-CLIP entries raise
  ``PrimitiveError`` — the operator's intent was unambiguous;
  silent skipping would surprise.

### Params

* ``reencode`` (bool, default False) — when True, forces
  filter_complex normalization on the media-engine side. Use
  when inputs come from different Runway models with
  heterogeneous codecs/dims. Default False (``-c copy``,
  fast, requires uniform inputs).

### Output

One CLIP Asset whose ``file_path`` is the cached concat MP4
URL. ``duration_ms`` is populated from the media-engine's
response when available; otherwise summed from input assets.
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


# Cost model — ffmpeg concat is local CPU only; no provider
# billing. A non-zero token covers compute time so concat steps
# don't slip below operator-visible cost thresholds.
_CONCAT_CLIPS_MICROS = 100


class ConcatClipsPrimitive:
    """``concat_clips`` step primitive — ffmpeg stitch via
    the media-engine's synchronous endpoint."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        clips: list[Asset] = []
        for entry in resolved_inputs or []:
            asset = entry.get("asset")
            if asset is None:
                continue
            if asset.asset_type != AssetType.CLIP:
                raise PrimitiveError(
                    f"concat_clips expects CLIP inputs; got "
                    f"{asset.asset_type} in slot {entry.get('slot')!r}"
                )
            clips.append(asset)

        if not clips:
            raise PrimitiveError(
                "concat_clips requires at least one CLIP input"
            )

        params = step.params or {}
        reencode = bool(params.get("reencode"))

        if mock_mode:
            total_duration_ms = sum(
                (c.duration_ms or 0) for c in clips
            ) or len(clips) * 5000
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-concat.mp4"),
                duration_ms=total_duration_ms,
                width=1280,
                height=720,
                mime_type="video/mp4",
                size_bytes=1024 * 1024,
                cost_micros=_CONCAT_CLIPS_MICROS,
                extra_source_spec={
                    "primitive_kind": "concat_clips",
                    "mock": True,
                    "input_count": len(clips),
                    "input_asset_ids": [str(c.id) for c in clips],
                    "reencode": reencode,
                },
            )

        # ---- real-mode path -----------------------------------

        clip_urls = [c.file_path for c in clips if c.file_path]
        if len(clip_urls) != len(clips):
            raise PrimitiveError(
                f"concat_clips: {len(clips) - len(clip_urls)} input assets "
                f"have empty file_path; cannot concat"
            )

        try:
            with MediaEngineClient() as client:
                result = client.concat_clips(
                    clip_urls=clip_urls,
                    reencode=reencode,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine concat_clips failed: {exc}"
            ) from exc

        logger.info(
            "concat_clips step=%s inputs=%d output=%s mock=%s",
            step.id, len(clip_urls), result.output_url, result.mock_mode,
        )

        # Prefer the media-engine's reported duration; fall back
        # to summing input durations.
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)
        else:
            duration_ms = sum((c.duration_ms or 0) for c in clips) or None

        extra: dict[str, Any] = {
            "primitive_kind": "concat_clips",
            "input_count": len(clips),
            "input_asset_ids": [str(c.id) for c in clips],
            "reencode": reencode,
            "media_engine_mock_mode": result.mock_mode,
        }

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_CONCAT_CLIPS_MICROS,
            extra_source_spec=extra,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _CONCAT_CLIPS_MICROS
