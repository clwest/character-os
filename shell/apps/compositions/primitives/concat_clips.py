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

from apps.compositions.models import Asset, AssetRole, AssetType
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
        # SESSION 200 — optional crossfade between consecutive clips
        # (storyboard polish for the Hook/Action/Payoff hard cuts).
        # Validated >= 0 here; the media-engine endpoint enforces the
        # 0-5000ms ceiling.
        try:
            crossfade_ms = int(params.get("crossfade_ms", 0) or 0)
        except (TypeError, ValueError):
            raise PrimitiveError(
                f"concat_clips crossfade_ms must be an integer; "
                f"got {params.get('crossfade_ms')!r}"
            )
        if crossfade_ms < 0:
            raise PrimitiveError(
                f"concat_clips crossfade_ms must be >= 0; got {crossfade_ms}"
            )
        # SESSION 196 slice 2 — combinator-primitive role override.
        # SESSION 195 dogfood found that A2's unconditional
        # ``role=BACKDROP`` is wrong for dialogue_scene (concat of N
        # talking_heads → final deliverable, not a backdrop). The
        # A7 role-filtered backdrop_clip_id picker would offer the
        # dialogue final as a "backdrop" — nonsensical avatars-over-
        # avatars.
        #
        # Static ``primitive_kind → role`` (SESSION 186 A2) holds for
        # emitter primitives but breaks for combinators whose role
        # depends on what's being combined. Recipe starter passes
        # ``result_role`` in step params; primitive reads + stamps.
        # Backwards-compat default keeps the V18 / storyboard_voiced
        # BACKDROP behavior.
        result_role = (
            params.get("result_role") or AssetRole.BACKDROP.value
        )
        valid_roles = {v for v, _ in AssetRole.choices}
        if result_role not in valid_roles:
            raise PrimitiveError(
                f"concat_clips result_role={result_role!r} is not a "
                f"valid AssetRole. Allowed: {sorted(valid_roles)}"
            )

        if mock_mode:
            # SESSION 200 — when crossfade_ms > 0, each transition
            # overlap shortens the total by crossfade_ms. Reflect
            # that in the mock duration so downstream steps (e.g.
            # mix_audio) see realistic numbers.
            raw_total = sum(
                (c.duration_ms or 0) for c in clips
            ) or len(clips) * 5000
            overlap_loss = max(0, len(clips) - 1) * crossfade_ms
            total_duration_ms = max(1, raw_total - overlap_loss)
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
                    "crossfade_ms": crossfade_ms,
                    "result_role": result_role,
                    # SESSION 257 AI-D5 cleanup — duration provenance.
                    # Shell mock never touches media-engine; the number
                    # above is fabricated from summed inputs (with an
                    # explicit fallback of len(clips)*5000 for empty
                    # inputs). Mark it truthfully so downstream
                    # analytics can filter out mock rows.
                    "duration_source": "estimated",
                    "duration_estimated": True,
                },
                role=result_role,
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
                    crossfade_ms=crossfade_ms,
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
        #
        # SESSION 257 AI-D5 cleanup — stamp duration_source /
        # duration_estimated so the concat asset carries the same
        # provenance shape talking-head-speech steps do
        # (SESSION 253 Stage 2 ffprobe plumbing). Prior to this
        # cleanup, the concat asset had duration_ms populated but
        # source unstamped — downstream analytics couldn't tell
        # whether the number was ffprobed from the real output
        # (media-engine did an authoritative measurement) or
        # summed from inputs (derived, drifts under crossfade).
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)
            # Real-mode media-engine ffprobes the concat output URL
            # (measured). A media_engine mock returns a fabricated
            # number based on summed inputs — that's derived, not
            # measured, even though the field is populated.
            duration_source = (
                "derived_from_inputs" if result.mock_mode else "media_probe"
            )
        else:
            duration_ms = sum((c.duration_ms or 0) for c in clips) or None
            duration_source = "derived_from_inputs"

        extra: dict[str, Any] = {
            "primitive_kind": "concat_clips",
            "input_count": len(clips),
            "input_asset_ids": [str(c.id) for c in clips],
            "reencode": reencode,
            "crossfade_ms": crossfade_ms,
            "result_role": result_role,
            "media_engine_mock_mode": result.mock_mode,
            "duration_source": duration_source,
            "duration_estimated": duration_source != "media_probe",
        }

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_CONCAT_CLIPS_MICROS,
            extra_source_spec=extra,
            role=result_role,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _CONCAT_CLIPS_MICROS
