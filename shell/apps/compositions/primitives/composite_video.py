"""The ``composite_video`` step primitive.

SESSION 143 / V7. Synchronous ffmpeg overlay via the
media-engine's new ``/internal/clips/composite/`` route.
Takes N CLIP inputs + a layout_spec param, produces one
composited CLIP output.

The leg that unlocks all the scene-composition starters
(`pip_layout`, `backdrop_layout`, `cohost_layout`,
`broll_splice`) plus serves as the dependency V8
(`talking_head_with_backdrop`) needs.

### Inputs

Every entry in ``resolved_inputs`` whose ``asset.asset_type``
is ``CLIP`` is sent as a composite input in input-list order.
Non-CLIP entries raise ``PrimitiveError`` — operator's intent
was unambiguous.

### Params

* ``layout_spec`` (dict, required) — ``{"kind": str, "options":
  {...}}``. Kind ∈ ``{pip, backdrop, cohost, broll}``.
  Options are layout-specific (see media-engine endpoint
  comments for the full reference).
* ``reencode`` — not a knob here; the media-engine endpoint
  re-encodes by default (composite always changes the video
  stream shape).

### Output

One CLIP Asset whose ``file_path`` is the cached composite
MP4 URL. ``duration_ms`` is summed from the inputs (the
composite primitive doesn't know exact output duration
without ffprobing — defer that to the cost-telemetry slice).
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


_COMPOSITE_VIDEO_MICROS = 100  # CPU-bound; same as concat_clips


_VALID_LAYOUT_KINDS = {"pip", "backdrop", "cohost", "broll"}


class CompositeVideoPrimitive:
    """``composite_video`` step primitive — ffmpeg filter_complex
    overlay via the media-engine."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        layout_spec = (step.params or {}).get("layout_spec")
        if not isinstance(layout_spec, dict):
            raise PrimitiveError(
                "composite_video requires a layout_spec dict param "
                "with at least a 'kind' key"
            )
        kind = (layout_spec.get("kind") or "").strip()
        if kind not in _VALID_LAYOUT_KINDS:
            raise PrimitiveError(
                f"composite_video layout_spec.kind must be one of "
                f"{sorted(_VALID_LAYOUT_KINDS)}; got {kind!r}"
            )

        clips: list[Asset] = []
        for entry in resolved_inputs or []:
            asset = entry.get("asset")
            if asset is None:
                continue
            if asset.asset_type != AssetType.CLIP:
                raise PrimitiveError(
                    f"composite_video expects CLIP inputs; got "
                    f"{asset.asset_type} in slot {entry.get('slot')!r}"
                )
            clips.append(asset)

        if len(clips) < 2:
            raise PrimitiveError(
                f"composite_video requires at least two CLIP inputs "
                f"(base + overlay); got {len(clips)}"
            )

        # SESSION 184 polish — null-duration inputs would silently
        # let the media-engine pick the base clip's length as the
        # composite trim target. For V8 ``backdrop`` that means
        # speech-shaped inputs produce backdrop-length output with
        # a trailing silent tail (SESSION 183 Sunset 2 finding).
        # Refuse the dispatch and surface the upstream primitive
        # that didn't persist duration. Mock and real paths both
        # gate on the same check so unit tests catch the contract
        # break.
        missing_duration = [c for c in clips if c.duration_ms is None]
        if missing_duration:
            ids = ", ".join(str(c.id) for c in missing_duration)
            raise PrimitiveError(
                f"composite_video inputs must have duration_ms set; "
                f"{len(missing_duration)} of {len(clips)} input asset(s) "
                f"have duration_ms=None ({ids}). Fix the upstream "
                f"primitive that produced them — duration is required "
                f"so the composite can trim to the shortest input "
                f"instead of silently using the base clip's length."
            )

        if mock_mode:
            total_duration_ms = sum(
                (c.duration_ms or 0) for c in clips
            ) // max(len(clips), 1) or 5000
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), f"-composite-{kind}.mp4"),
                duration_ms=total_duration_ms,
                width=1280,
                height=720,
                mime_type="video/mp4",
                size_bytes=1024 * 1024,
                cost_micros=_COMPOSITE_VIDEO_MICROS,
                extra_source_spec={
                    "primitive_kind": "composite_video",
                    "mock": True,
                    "layout_kind": kind,
                    "input_count": len(clips),
                    "input_asset_ids": [str(c.id) for c in clips],
                },
                role=AssetRole.COMPOSITE_OUTPUT.value,
            )

        # ---- real-mode path -----------------------------------

        clip_urls = [c.file_path for c in clips if c.file_path]
        if len(clip_urls) != len(clips):
            raise PrimitiveError(
                f"composite_video: {len(clips) - len(clip_urls)} input "
                "assets have empty file_path; cannot composite"
            )

        try:
            with MediaEngineClient() as client:
                result = client.create_composite(
                    clip_urls=clip_urls,
                    layout_spec=layout_spec,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine create_composite failed: {exc}"
            ) from exc

        logger.info(
            "composite_video step=%s kind=%s inputs=%d output=%s mock=%s",
            step.id, kind, len(clips), result.output_url, result.mock_mode,
        )

        # Duration estimation: prefer media-engine response, else
        # take the base clip's duration (input 0 is always the
        # base in all v1 layouts).
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)
        else:
            duration_ms = clips[0].duration_ms

        extra: dict[str, Any] = {
            "primitive_kind": "composite_video",
            "layout_kind": kind,
            "input_count": len(clips),
            "input_asset_ids": [str(c.id) for c in clips],
            "media_engine_mock_mode": result.mock_mode,
        }

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_COMPOSITE_VIDEO_MICROS,
            extra_source_spec=extra,
            role=AssetRole.COMPOSITE_OUTPUT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _COMPOSITE_VIDEO_MICROS
