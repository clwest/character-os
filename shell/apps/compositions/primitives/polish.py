"""V9 polish primitives — captions / intro_outro / trim / reformat.

SESSION 143 / V9. Four ffmpeg-backed primitives that polish or
reformat existing CLIPs. None of them call Runway; each is a
single synchronous POST to the media-engine.

They share enough shape that consolidating into one file keeps
the V9 surface scannable. Each primitive class follows the V2
contract (``execute()`` + ``estimate_cost()`` static methods).

Adding a fifth polish primitive (e.g., color grade, watermark)
would land in this file alongside the existing four.
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


# Cost model — all local ffmpeg work (no provider billing).
# Small fixed costs so they still register in operator-visible
# totals.
_CAPTIONS_MICROS = 80
_INTRO_OUTRO_MICROS = 80
_TRIM_MICROS = 30
_REFORMAT_MICROS = 80
_IMAGE_OVERLAY_MICROS = 80  # SESSION 256


_IMAGE_OVERLAY_VALID_CORNERS = (
    "top_right", "top_left", "bottom_right", "bottom_left",
)


# ---- AddCaptionsPrimitive -----------------------------------------


class AddCaptionsPrimitive:
    """Burn-in subtitles from operator-supplied caption timing,
    or — V12 auto mode — from a TRANSCRIPT input slot.

    Two paths:

    * **Manual mode** (V9 default): ``params["captions"]`` is a
      list of ``{start_s, end_s, text}``. The primitive sends
      it straight to the media-engine. Operator-supplied
      timing wins when both modes are available.
    * **Auto mode** (V12+): ``params["captions"]`` is omitted
      and a TRANSCRIPT asset arrives via a step input. The
      primitive parses its ``inline_content`` as the V12
      transcript shape (``{"segments": [...]}`` or a bare
      array) and uses the segments as captions.

    The TRANSCRIPT input is identified by slot name
    (``transcript``) or by asset_type; non-TRANSCRIPT inputs
    are ignored in auto mode so a CLIP + TRANSCRIPT pair
    works cleanly.
    """

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        captions = params.get("captions")

        # Auto mode (V12) — derive captions from a TRANSCRIPT
        # input if the manual list isn't supplied. The
        # TRANSCRIPT's inline_content holds the V12 transcript
        # JSON; we read ``segments`` (or the array directly).
        if not (isinstance(captions, list) and captions):
            captions = _captions_from_transcript_input(resolved_inputs)

        if not isinstance(captions, list) or not captions:
            raise PrimitiveError(
                "add_captions requires either a non-empty captions list in "
                "params OR a TRANSCRIPT input asset (auto mode)"
            )

        base = _expect_one_clip(resolved_inputs, primitive="add_captions")

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-captions.mp4"),
                duration_ms=base.duration_ms,
                width=base.width,
                height=base.height,
                mime_type="video/mp4",
                size_bytes=base.size_bytes or 1024 * 1024,
                cost_micros=_CAPTIONS_MICROS,
                extra_source_spec={
                    "primitive_kind": "add_captions",
                    "mock": True,
                    "base_asset_id": str(base.id),
                    "caption_count": len(captions),
                },
                role=AssetRole.POLISH_OUTPUT.value,
            )

        if not base.file_path:
            raise PrimitiveError("add_captions: base CLIP has empty file_path")

        try:
            with MediaEngineClient() as client:
                result = client.add_captions(
                    clip_url=base.file_path,
                    captions=captions,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(f"media-engine add_captions failed: {exc}") from exc

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=base.duration_ms,
            width=base.width,
            height=base.height,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_CAPTIONS_MICROS,
            extra_source_spec={
                "primitive_kind": "add_captions",
                "base_asset_id": str(base.id),
                "caption_count": len(captions),
                "media_engine_mock_mode": result.mock_mode,
            },
            role=AssetRole.POLISH_OUTPUT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _CAPTIONS_MICROS


# ---- AddIntroOutroPrimitive --------------------------------------


class AddIntroOutroPrimitive:
    """Prepend an intro card and/or append an outro card to the
    base CLIP. At least one of ``params["intro"]`` /
    ``params["outro"]`` is required."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        intro = params.get("intro")
        outro = params.get("outro")
        if intro is None and outro is None:
            raise PrimitiveError(
                "add_intro_outro requires at least one of intro / outro in params"
            )
        if intro is not None and not isinstance(intro, dict):
            raise PrimitiveError("add_intro_outro intro must be a dict")
        if outro is not None and not isinstance(outro, dict):
            raise PrimitiveError("add_intro_outro outro must be a dict")
        if intro is not None and not str(intro.get("text", "")).strip():
            raise PrimitiveError("add_intro_outro intro requires a non-empty text")
        if outro is not None and not str(outro.get("text", "")).strip():
            raise PrimitiveError("add_intro_outro outro requires a non-empty text")

        base = _expect_one_clip(resolved_inputs, primitive="add_intro_outro")

        extra_duration_ms = (
            int((intro.get("duration_s") or 3) * 1000) if intro else 0
        ) + (
            int((outro.get("duration_s") or 3) * 1000) if outro else 0
        )

        if mock_mode:
            new_duration = (base.duration_ms or 0) + extra_duration_ms
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-intro_outro.mp4"),
                duration_ms=new_duration or None,
                width=base.width,
                height=base.height,
                mime_type="video/mp4",
                size_bytes=base.size_bytes or 1024 * 1024,
                cost_micros=_INTRO_OUTRO_MICROS,
                extra_source_spec={
                    "primitive_kind": "add_intro_outro",
                    "mock": True,
                    "base_asset_id": str(base.id),
                    "has_intro": intro is not None,
                    "has_outro": outro is not None,
                },
                role=AssetRole.POLISH_OUTPUT.value,
            )

        if not base.file_path:
            raise PrimitiveError("add_intro_outro: base CLIP has empty file_path")

        try:
            with MediaEngineClient() as client:
                result = client.add_intro_outro(
                    clip_url=base.file_path,
                    intro=intro,
                    outro=outro,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(f"media-engine add_intro_outro failed: {exc}") from exc

        duration_ms: int | None = None
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)
        elif base.duration_ms is not None:
            duration_ms = base.duration_ms + extra_duration_ms

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            width=base.width,
            height=base.height,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_INTRO_OUTRO_MICROS,
            extra_source_spec={
                "primitive_kind": "add_intro_outro",
                "base_asset_id": str(base.id),
                "has_intro": intro is not None,
                "has_outro": outro is not None,
                "media_engine_mock_mode": result.mock_mode,
            },
            role=AssetRole.POLISH_OUTPUT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _INTRO_OUTRO_MICROS


# ---- ImageOverlayPrimitive ---------------------------------------


class ImageOverlayPrimitive:
    """SESSION 256 — overlay a still IMAGE on a base CLIP.

    Reusable visual-callout / PiP primitive. Wraps the
    media-engine's ``POST /internal/clips/image_overlay/``
    endpoint. Local ffmpeg only — no provider spend.

    ### Inputs

    * One CLIP asset (the base). Additional assets in
      ``resolved_inputs`` are ignored.

    ### Params

    * ``image_source`` (str, required) — a data URI OR a
      ``/data/`` local URL pointing at an IMAGE Asset. Recipe-
      layer resolvers unwrap workspace IMAGE assets to their
      ``file_path`` (SESSION 174 / cinematic_visual pattern);
      the primitive forwards it to the media-engine's polymorphic
      resolver.
    * ``corner`` (str, default "top_right") — one of top_right /
      top_left / bottom_right / bottom_left.
    * ``overlay_width`` (int, default 320).
    * ``margin_x`` / ``margin_y`` (int, default 40 each).
    * ``start_time_s`` / ``end_time_s`` (float, both optional).
      Both None = overlay covers the full base duration
      (SESSION 256 default). ``enable=between(t,s,e)`` semantics
      apply on the media-engine side.
    * ``border`` (bool, default True), ``shadow`` (bool, default
      True) — presentation treatment for a floating callout.

    ### Output

    One CLIP Asset whose ``duration_ms`` matches the base clip
    (overlays never alter base duration; guaranteed both by
    the media-engine's ``-t <base_dur>`` and by the primitive's
    fallback to ``base.duration_ms`` when media-engine returns
    None).
    """

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        image_source = (params.get("image_source") or "").strip()
        if not image_source:
            raise PrimitiveError(
                "image_overlay requires a non-empty 'image_source' param "
                "(data URI or /data/ URL to a workspace IMAGE asset)"
            )
        corner = (params.get("corner") or "top_right").strip().lower()
        if corner not in _IMAGE_OVERLAY_VALID_CORNERS:
            raise PrimitiveError(
                f"image_overlay 'corner' must be one of "
                f"{list(_IMAGE_OVERLAY_VALID_CORNERS)}; got {corner!r}"
            )
        # Numeric params — coerce defensively (DRF may hand strings
        # off recipe forms).
        try:
            overlay_width = int(params.get("overlay_width", 320))
            margin_x = int(params.get("margin_x", 40))
            margin_y = int(params.get("margin_y", 40))
        except (TypeError, ValueError) as exc:
            raise PrimitiveError(
                f"image_overlay overlay_width / margin_x / margin_y "
                f"must be integers; got {params!r}"
            ) from exc

        start_time_s = params.get("start_time_s")
        end_time_s = params.get("end_time_s")
        # Coerce nullable floats (empty string from a DRF form
        # arrives here as "" and should collapse to None so the
        # media-engine sees a truly-absent field).
        if start_time_s in ("", None):
            start_time_s = None
        else:
            try:
                start_time_s = float(start_time_s)
            except (TypeError, ValueError) as exc:
                raise PrimitiveError(
                    f"image_overlay start_time_s must be a number or blank; "
                    f"got {start_time_s!r}"
                ) from exc
        if end_time_s in ("", None):
            end_time_s = None
        else:
            try:
                end_time_s = float(end_time_s)
            except (TypeError, ValueError) as exc:
                raise PrimitiveError(
                    f"image_overlay end_time_s must be a number or blank; "
                    f"got {end_time_s!r}"
                ) from exc
        if (
            start_time_s is not None
            and end_time_s is not None
            and end_time_s <= start_time_s
        ):
            raise PrimitiveError(
                f"image_overlay end_time_s ({end_time_s}) must be strictly "
                f"greater than start_time_s ({start_time_s})"
            )
        if start_time_s is not None and start_time_s < 0:
            raise PrimitiveError(
                f"image_overlay start_time_s must be >= 0; got {start_time_s}"
            )

        border = bool(params.get("border", True))
        shadow = bool(params.get("shadow", True))

        base = _expect_one_clip(resolved_inputs, primitive="image_overlay")

        if mock_mode:
            # Deterministic mock output. Duration mirrors the base
            # exactly per the SESSION 256 contract; no ffmpeg runs.
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-image-overlay.mp4"),
                duration_ms=base.duration_ms,
                width=base.width,
                height=base.height,
                mime_type="video/mp4",
                size_bytes=base.size_bytes or 1024 * 1024,
                cost_micros=_IMAGE_OVERLAY_MICROS,
                extra_source_spec={
                    "primitive_kind": "image_overlay",
                    "mock": True,
                    "base_asset_id": str(base.id),
                    "corner": corner,
                    "overlay_width": overlay_width,
                    "has_start_time": start_time_s is not None,
                    "has_end_time": end_time_s is not None,
                    "border": border,
                    "shadow": shadow,
                },
                role=AssetRole.POLISH_OUTPUT.value,
            )

        if not base.file_path:
            raise PrimitiveError(
                "image_overlay: base CLIP has empty file_path"
            )

        try:
            with MediaEngineClient() as client:
                result = client.image_overlay(
                    clip_url=base.file_path,
                    image_source=image_source,
                    corner=corner,
                    overlay_width=overlay_width,
                    margin_x=margin_x,
                    margin_y=margin_y,
                    start_time_s=start_time_s,
                    end_time_s=end_time_s,
                    border=border,
                    shadow=shadow,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(
                f"media-engine image_overlay failed: {exc}"
            ) from exc

        # Duration — media-engine ffprobes the output and returns
        # the measured value. Fall back to base.duration_ms so the
        # SESSION 253 duration-provenance discipline holds even if
        # a future media-engine change stops populating the field.
        if result.duration_seconds is not None:
            duration_ms = int(result.duration_seconds * 1000)
        else:
            duration_ms = base.duration_ms

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            width=base.width,
            height=base.height,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_IMAGE_OVERLAY_MICROS,
            extra_source_spec={
                "primitive_kind": "image_overlay",
                "base_asset_id": str(base.id),
                "corner": corner,
                "overlay_width": overlay_width,
                "margin_x": margin_x,
                "margin_y": margin_y,
                "start_time_s": start_time_s,
                "end_time_s": end_time_s,
                "border": border,
                "shadow": shadow,
                "media_engine_mock_mode": result.mock_mode,
            },
            role=AssetRole.POLISH_OUTPUT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _IMAGE_OVERLAY_MICROS


# ---- TrimClipPrimitive --------------------------------------------


class TrimClipPrimitive:
    """Stream-copy trim of a single CLIP to the requested
    ``[start_ms, end_ms]`` range."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        params = step.params or {}
        start_ms = params.get("start_ms")
        end_ms = params.get("end_ms")
        if start_ms is None or end_ms is None:
            raise PrimitiveError(
                "trim_clip requires both start_ms and end_ms in params"
            )
        try:
            start_ms = int(start_ms)
            end_ms = int(end_ms)
        except (TypeError, ValueError):
            raise PrimitiveError("trim_clip start_ms/end_ms must be integers")
        if start_ms < 0 or end_ms <= start_ms:
            raise PrimitiveError(
                f"trim_clip requires 0 <= start_ms < end_ms (got "
                f"start={start_ms}, end={end_ms})"
            )

        base = _expect_one_clip(resolved_inputs, primitive="trim_clip")
        trimmed_duration_ms = end_ms - start_ms

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-trim.mp4"),
                duration_ms=trimmed_duration_ms,
                width=base.width,
                height=base.height,
                mime_type="video/mp4",
                size_bytes=base.size_bytes or 1024 * 1024,
                cost_micros=_TRIM_MICROS,
                extra_source_spec={
                    "primitive_kind": "trim_clip",
                    "mock": True,
                    "base_asset_id": str(base.id),
                    "start_ms": start_ms,
                    "end_ms": end_ms,
                },
                role=AssetRole.POLISH_OUTPUT.value,
            )

        if not base.file_path:
            raise PrimitiveError("trim_clip: base CLIP has empty file_path")

        try:
            with MediaEngineClient() as client:
                result = client.trim_clip(
                    clip_url=base.file_path,
                    start_ms=start_ms,
                    end_ms=end_ms,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(f"media-engine trim_clip failed: {exc}") from exc

        duration_ms = (
            int(result.duration_seconds * 1000)
            if result.duration_seconds is not None
            else trimmed_duration_ms
        )

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=duration_ms,
            width=base.width,
            height=base.height,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_TRIM_MICROS,
            extra_source_spec={
                "primitive_kind": "trim_clip",
                "base_asset_id": str(base.id),
                "start_ms": start_ms,
                "end_ms": end_ms,
                "media_engine_mock_mode": result.mock_mode,
            },
            role=AssetRole.POLISH_OUTPUT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _TRIM_MICROS


# ---- ReformatClipPrimitive ---------------------------------------


_REFORMAT_RATIO_DIMS = {
    "1280:720": (1280, 720),
    "720:1280": (720, 1280),
    "960:960": (960, 960),
}


class ReformatClipPrimitive:
    """Scale + crop to a target aspect ratio. Canonical use case
    is Reels conversion (``1280:720`` → ``720:1280``)."""

    @staticmethod
    def execute(step, resolved_inputs, mock_mode: bool) -> PrimitiveResult:
        target_ratio = (step.params or {}).get("target_ratio")
        if not target_ratio or target_ratio not in _REFORMAT_RATIO_DIMS:
            raise PrimitiveError(
                f"reformat_clip target_ratio must be one of "
                f"{sorted(_REFORMAT_RATIO_DIMS.keys())}; got {target_ratio!r}"
            )

        base = _expect_one_clip(resolved_inputs, primitive="reformat_clip")
        new_w, new_h = _REFORMAT_RATIO_DIMS[target_ratio]

        if mock_mode:
            return PrimitiveResult(
                asset_type=AssetType.CLIP,
                file_path=_deterministic_path(str(step.id), "-reformat.mp4"),
                duration_ms=base.duration_ms,
                width=new_w,
                height=new_h,
                mime_type="video/mp4",
                size_bytes=base.size_bytes or 1024 * 1024,
                cost_micros=_REFORMAT_MICROS,
                extra_source_spec={
                    "primitive_kind": "reformat_clip",
                    "mock": True,
                    "base_asset_id": str(base.id),
                    "target_ratio": target_ratio,
                },
                role=AssetRole.POLISH_OUTPUT.value,
            )

        if not base.file_path:
            raise PrimitiveError("reformat_clip: base CLIP has empty file_path")

        try:
            with MediaEngineClient() as client:
                result = client.reformat_clip(
                    clip_url=base.file_path,
                    target_ratio=target_ratio,
                )
        except MediaEngineError as exc:
            raise PrimitiveError(f"media-engine reformat_clip failed: {exc}") from exc

        return PrimitiveResult(
            asset_type=AssetType.CLIP,
            file_path=result.output_url,
            duration_ms=base.duration_ms,
            width=new_w,
            height=new_h,
            mime_type="video/mp4",
            size_bytes=result.size_bytes,
            cost_micros=_REFORMAT_MICROS,
            extra_source_spec={
                "primitive_kind": "reformat_clip",
                "base_asset_id": str(base.id),
                "target_ratio": target_ratio,
                "media_engine_mock_mode": result.mock_mode,
            },
            role=AssetRole.POLISH_OUTPUT.value,
        )

    @staticmethod
    def estimate_cost(params: dict) -> int:
        return _REFORMAT_MICROS


# ---- shared helpers ----------------------------------------------


def _expect_one_clip(resolved_inputs, *, primitive: str) -> Asset:
    """Pick the single CLIP asset from resolved_inputs. Other
    asset types (e.g. TRANSCRIPT for V12 add_captions auto
    mode) are tolerated — only the CLIP count matters.
    Raises PrimitiveError if zero or more than one CLIP is
    supplied."""
    clips: list[Asset] = []
    for entry in resolved_inputs or []:
        asset = entry.get("asset")
        if asset is None:
            continue
        if asset.asset_type == AssetType.CLIP:
            clips.append(asset)
            continue
        # Non-CLIP assets are OK for primitives that take
        # auxiliary inputs (e.g. add_captions's TRANSCRIPT
        # slot). The helper's job is just to pick the one CLIP.
    if len(clips) != 1:
        raise PrimitiveError(
            f"{primitive} expects exactly one CLIP input; got {len(clips)}"
        )
    return clips[0]


def _captions_from_transcript_input(resolved_inputs) -> list[dict] | None:
    """V12 auto-mode helper for add_captions. Looks for a
    TRANSCRIPT input in resolved_inputs and parses its
    ``inline_content`` as the V12 transcript JSON. Returns a
    list of caption dicts ``[{start_s, end_s, text}, ...]``
    suitable for the media-engine, or ``None`` if no
    TRANSCRIPT was supplied.

    Tolerates two transcript shapes:
        {"segments": [{start_s, end_s, text}, ...], ...}
        [{start_s, end_s, text}, ...]
    """
    import json as _json

    for entry in resolved_inputs or []:
        asset = entry.get("asset")
        if asset is None:
            continue
        if asset.asset_type != AssetType.TRANSCRIPT:
            continue
        raw = (asset.inline_content or "").strip()
        if not raw:
            continue
        try:
            parsed = _json.loads(raw)
        except (ValueError, TypeError):
            return None
        if isinstance(parsed, dict):
            segments = parsed.get("segments")
        else:
            segments = parsed
        if not isinstance(segments, list) or not segments:
            return None
        out: list[dict] = []
        for seg in segments:
            if not isinstance(seg, dict):
                continue
            start = seg.get("start_s") or seg.get("start") or 0
            end = seg.get("end_s") or seg.get("end") or 0
            text = (seg.get("text") or "").strip()
            if text and float(end) > float(start):
                out.append({
                    "start_s": float(start),
                    "end_s": float(end),
                    "text": text,
                })
        return out or None
    return None
