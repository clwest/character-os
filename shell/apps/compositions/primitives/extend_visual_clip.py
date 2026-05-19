"""The ``extend_visual_clip`` step primitive.

SESSION 182 / V17.1. Operator-visible capability: extend a
rendered video clip beyond Runway's per-render 10s ceiling. V17
post-close addition (V1 rules 10-13 cover the primitive contract).

### The pivot — Q-v17-1 resolution (SESSION 182)

The V17 proposal originally posited a ``/v1/video_to_video`` extend
mode (gen4_turbo / gen4.5). Live API check at V17.0 slice-open
surfaced that ``/v1/video_to_video`` only accepts ``gen4_aleph``
(V11 style remix). The implementation pivot — last-frame
extraction + ``/v1/image_to_video`` (gen4_turbo) + ffmpeg concat —
lives on the media-engine side; this primitive is the contract
layer.

### Inputs

Exactly one CLIP — the source to extend. Non-CLIP raises
PrimitiveError. The single-input restriction is deliberate;
multi-CLIP chains are operator-visible recipes (V17.2's
``cinematic_visual_extended`` will chain N extend primitives),
not a single-primitive concern.

### Params

* ``prompt`` (str, required) — continuation prompt. Conditions
  the new segment's content; the last frame of the source is
  the implicit visual anchor.
* ``duration`` (int, optional) — new-segment duration in
  seconds. Defaults to 5. Bounded by ``gen4_turbo``'s
  per-render limit (5s only today).
* ``ratio`` (str, optional) — output ratio. Defaults to
  ``1280:720``. Must match the source clip's ratio at the
  media-engine layer; mismatched dims fail loudly during the
  ffmpeg concat (intentional — silently scaling would mask
  operator misconfiguration).
* ``seed`` (int, optional) — Runway seed for reproducibility.

### Output

One CLIP Asset whose ``file_path`` is the cached MP4 URL.
``duration_ms`` carries the SOURCE + NEW SEGMENT sum (the
operator-facing duration of the extended clip). ``source_spec``
records both component durations so audit + cost reconciliation
can split them. ``mime_type`` is ``video/mp4``.

### Cost

Per V17 rule 13. New-segment seconds × $0.05 (Runway gen4_turbo
billed rate), with a floor at the 5s minimum. The source clip
isn't re-rendered (we only download + ffmpeg-concat it), so the
operator only pays for the new segment.
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


# Cost model. Same per-second rate as V4 generate_visual_clip
# (Runway gen4_turbo bills at ~$0.05/sec). Only the NEW segment
# is charged — the source clip is downloaded + ffmpeg-concatted
# locally, not re-rendered. Q-v17-5 (open) covers cost estimation
# when source duration is unknown at recipe-time; v1 estimates
# from the operator-supplied new-segment duration only.
_EXTEND_MICROS_PER_SECOND = 50_000
_EXTEND_MIN_MICROS = 250_000


class ExtendVisualClipPrimitive:
    """``extend_visual_clip`` step primitive — last-frame
    conditioned video continuation via the media-engine."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}

        prompt = str(params.get("prompt", "")).strip()
        if not prompt:
            raise PrimitiveError(
                "extend_visual_clip requires a non-empty prompt param"
            )

        duration_param = params.get("duration")
        try:
            duration_s = int(duration_param) if duration_param else 5
        except (TypeError, ValueError):
            raise PrimitiveError(
                f"extend_visual_clip duration must be an integer; "
                f"got {duration_param!r}"
            )

        ratio = str(params.get("ratio") or "1280:720").strip()
        seed = params.get("seed")
        if seed is not None:
            try:
                seed = int(seed)
            except (TypeError, ValueError):
                raise PrimitiveError(
                    "extend_visual_clip seed must be an integer"
                )

        source = _expect_one_clip(resolved_inputs)

        if mock_mode:
            # Carry source dims through (output has same shape as
            # input — the new segment is at the source's ratio).
            # Duration is source + new; downstream concat/trim
            # steps need a consistent number.
            src_duration_ms = source.duration_ms or 5000
            total_duration_ms = src_duration_ms + (duration_s * 1000)
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(
                    str(step.id), "-extended.mp4",
                ),
                duration_ms=total_duration_ms,
                width=source.width,
                height=source.height,
                mime_type="video/mp4",
                size_bytes=(source.size_bytes or 1024 * 1024) * 2,
                cost_micros=ExtendVisualClipPrimitive.estimate_cost(params),
                extra_source_spec={
                    "primitive_kind": "extend_visual_clip",
                    "mock": True,
                    "source_asset_id": str(source.id),
                    "source_duration_ms": src_duration_ms,
                    "new_segment_duration_ms": duration_s * 1000,
                    "prompt_chars": len(prompt),
                    "ratio": ratio,
                    "seed": seed,
                },
            )

        # ---- real-mode path -----------------------------------

        if not source.file_path:
            raise PrimitiveError(
                "extend_visual_clip: source clip has empty file_path; "
                "cannot extend"
            )

        try:
            with MediaEngineClient() as client:
                result = client.extend_clip(
                    source_clip_url=source.file_path,
                    prompt=prompt,
                    duration=duration_s,
                    ratio=ratio,
                    seed=seed,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine extend_clip failed: {exc}"
            ) from exc

        logger.info(
            "extend_visual_clip step=%s task=%s source_dur=%.2f new_dur=%d "
            "total=%.2f mock=%s",
            step.id, result.task_id, result.source_duration_seconds,
            duration_s, result.duration_seconds, result.mock_mode,
        )

        extra: dict[str, Any] = {
            "primitive_kind": "extend_visual_clip",
            "task_id": result.task_id,
            "source_asset_id": str(source.id),
            "source_duration_ms": int(
                result.source_duration_seconds * 1000
            ),
            "new_segment_duration_ms": int(
                result.new_segment_duration_seconds * 1000
            ),
            "ratio": ratio,
            "seed": seed,
            "media_engine_mock_mode": result.mock_mode,
        }

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=int(result.duration_seconds * 1000),
            width=source.width,
            height=source.height,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=ExtendVisualClipPrimitive.estimate_cost(params),
            extra_source_spec=extra,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        """Cost in micros. Charges only for the NEW segment —
        the source clip isn't re-rendered. Per V17 rule 13."""
        duration = (params or {}).get("duration") or 5
        try:
            duration_s = int(duration)
        except (TypeError, ValueError):
            duration_s = 5
        return max(
            _EXTEND_MIN_MICROS,
            duration_s * _EXTEND_MICROS_PER_SECOND,
        )


def _expect_one_clip(resolved_inputs) -> Asset:
    """Pick the single CLIP asset from resolved_inputs.

    Same restriction as V11 style_remix and V16
    remove_avatar_background — multi-source primitives are an
    anti-pattern; multi-clip operations live at the recipe layer
    (V17.2's `cinematic_visual_extended` chains N extends)."""
    clips: list[Asset] = []
    for entry in resolved_inputs or []:
        asset = entry.get("asset")
        if asset is None:
            continue
        if asset.asset_type != AssetType.CLIP:
            raise PrimitiveError(
                f"extend_visual_clip expects exactly one CLIP input; got "
                f"{asset.asset_type} in slot {entry.get('slot')!r}"
            )
        clips.append(asset)
    if len(clips) != 1:
        raise PrimitiveError(
            f"extend_visual_clip expects exactly one CLIP input; "
            f"got {len(clips)}"
        )
    return clips[0]
