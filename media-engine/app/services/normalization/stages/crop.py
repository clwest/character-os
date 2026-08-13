"""CropStage(v2) — deterministic aspect crop + eye-line-target
origin under a source-center proxy.

SESSION 246 7.c architectural correction:

Pre-inspection, Step 7's ratified chain included a standalone
``EyeLineStage`` after ``FramingStage``. Inspection at 7.c
open surfaced that eye-line positioning after Framing has
zero legal headroom under the no-padding invariant — every
requested shift clamps to 0, making the stage decorative for
all five ratified profiles. Rather than ship a class whose
only pixel behavior is a permanent no-op, the operator
ratified folding eye-line positioning into CropStage. This is
version 2 of CropStage; v1 (7.b) shipped a centered crop that
did not consult ``profile.eye_line.position_from_top``.

What v2 owns (two related deterministic geometry decisions):

* **Aspect crop dimensions** — same integer-cross-multiply math
  as v1: ``k = min(input_w // a, input_h // b)`` with
  ``crop_w = k * a``, ``crop_h = k * b``.

* **Crop-window origin** — deterministic placement so that the
  source-image geometric center (the round-one proxy for "eye
  line") lands at the profile's declared
  ``eye_line.position_from_top`` inside the resulting crop.
  Both axes are computed; horizontal always centers because
  every ratified profile declares ``position_from_left: 0.5``.

* **Clamp to legal source bounds.** If the requested origin
  would expose empty pixels outside the source, clamp
  deterministically to the nearest legal value. Never pad.
  Never synthesize content. Manifest records the clamp
  request/applied/reason so Step 8/10 evidence can distinguish
  "eye-line landed at target" from "clamped short of target."

What v2 does NOT do:

* No subject detection. No face detection. No eye detection.
  No landmark detection. The source-image center is a
  deterministic geometric proxy — factually recorded in the
  manifest as ``eye_line_method="source_center_proxy"``.

* No honoring of ``subject_scale``, ``margins.min_edge_padding``,
  or ``framing_behavior.includes/excludes`` — those still
  require real subject geometry v1/v2 do not have. Recorded
  as declared-but-not-honored with factual blockers, same as
  v1's discipline.

Determinism:

* All geometry math uses integer arithmetic except for one
  ``round(target_from_top * crop_h)`` step. Under IEEE 754 +
  CPython, this is deterministic within a single Python
  version + platform. Recorded live at SESSION 246 7.c open
  as byte-identical across repeat runs.
"""
from __future__ import annotations

import math
import time
from typing import ClassVar

from ..png import BadPngError, decode_png, encode_png
from . import StageContext, StageError, StageExecution, StageOutput


class CropStage:
    """See module docstring."""

    stage_name: ClassVar[str] = "crop"
    stage_version: ClassVar[int] = 2

    def apply(self, ctx: StageContext) -> StageOutput:
        started = time.perf_counter()
        profile = ctx.surface_profile

        # ---- Aspect + crop-dimension math (unchanged from v1) --

        aspect_a, aspect_b = _parse_aspect_ratio(profile.crop.aspect_ratio)

        try:
            image = decode_png(ctx.image_bytes)
        except BadPngError as exc:
            raise StageError(f"crop_input_undecodable: {exc!s}") from exc

        max_k_by_width = ctx.width_px // aspect_a
        max_k_by_height = ctx.height_px // aspect_b
        k = min(max_k_by_width, max_k_by_height)
        if k <= 0:
            raise StageError(
                f"crop_impossible_at_input_dimensions: input "
                f"{ctx.width_px}x{ctx.height_px} cannot contain any crop "
                f"of aspect {aspect_a}:{aspect_b}"
            )
        crop_width = k * aspect_a
        crop_height = k * aspect_b

        # ---- Eye-line-target origin computation (v2 addition) --
        #
        # Source-center proxy: assume the "eye line" is at the
        # geometric center of the input image. This is a
        # deterministic geometric proxy, NOT any form of
        # detection.
        #
        # We want the source center to land at
        # ``target_from_top * crop_height`` inside the crop (i.e.,
        # at the profile's declared eye-line position within the
        # normalized frame). Therefore:
        #
        #     requested_top = source_center_y - target_from_top * crop_h
        #     requested_left = source_center_x - target_from_left * crop_w
        #
        # Then clamp both to legal bounds so the crop stays inside
        # the source image. Clamping is expected — a target of
        # 0.34 with a crop that fully covers the input has no
        # vertical headroom to shift, so applied_top will
        # be 0.
        target_from_top = profile.eye_line.position_from_top
        target_from_left = profile.eye_line.position_from_left

        proxy_source_x_px = ctx.width_px // 2
        proxy_source_y_px = ctx.height_px // 2

        requested_top = proxy_source_y_px - int(
            round(target_from_top * crop_height)
        )
        requested_left = proxy_source_x_px - int(
            round(target_from_left * crop_width)
        )

        legal_top_min = 0
        legal_top_max = ctx.height_px - crop_height
        legal_left_min = 0
        legal_left_max = ctx.width_px - crop_width

        applied_top = _clamp(requested_top, legal_top_min, legal_top_max)
        applied_left = _clamp(requested_left, legal_left_min, legal_left_max)

        eye_line_clamped_vertical = requested_top != applied_top
        eye_line_clamped_horizontal = requested_left != applied_left
        eye_line_clamped = eye_line_clamped_vertical or eye_line_clamped_horizontal

        clamp_reason_parts: list[str] = []
        if requested_top < legal_top_min:
            clamp_reason_parts.append("vertical_requested_below_source_top_edge")
        elif requested_top > legal_top_max:
            clamp_reason_parts.append("vertical_requested_below_source_bottom_edge")
        if requested_left < legal_left_min:
            clamp_reason_parts.append("horizontal_requested_left_of_source")
        elif requested_left > legal_left_max:
            clamp_reason_parts.append("horizontal_requested_right_of_source")
        eye_line_clamp_reason = (
            "|".join(clamp_reason_parts) if clamp_reason_parts else "not_clamped"
        )

        # Applied eye-line position (in normalized-fraction terms)
        # for evidence — where the source center actually ended up
        # inside the crop.
        applied_source_y_in_crop = proxy_source_y_px - applied_top
        applied_source_x_in_crop = proxy_source_x_px - applied_left
        applied_position_from_top = (
            applied_source_y_in_crop / crop_height if crop_height > 0 else 0.0
        )
        applied_position_from_left = (
            applied_source_x_in_crop / crop_width if crop_width > 0 else 0.0
        )

        right = applied_left + crop_width
        bottom = applied_top + crop_height

        cropped = image.crop((applied_left, applied_top, right, bottom))
        cropped_bytes = encode_png(cropped)
        duration_ms = int((time.perf_counter() - started) * 1000)

        details = {
            # Method identifier is explicit about the proxy nature;
            # reviewers reading a manifest can distinguish this
            # evidence class from a future subject-aware CropStage.
            "crop_method": "deterministic_center_proxy_eye_line_crop",
            "subject_detection_method": "none",
            "input_dimensions": {
                "width_px": ctx.width_px,
                "height_px": ctx.height_px,
            },
            "crop_box": {
                "left": applied_left,
                "top": applied_top,
                "right": right,
                "bottom": bottom,
            },
            "cropped_dimensions": {
                "width_px": crop_width,
                "height_px": crop_height,
            },
            "target_aspect_ratio_declared": profile.crop.aspect_ratio,
            "target_aspect_ratio_reduced_pair": [aspect_a, aspect_b],
            "crop_strategy_declared": profile.crop.strategy,
            # v2 eye-line evidence — pipeline hoists this nested
            # block into the manifest's ``eye_line_adjustments``
            # field verbatim.
            "eye_line_adjustments": {
                "eye_line_method": "source_center_proxy",
                "eye_line_target_from_top": target_from_top,
                "eye_line_target_from_left": target_from_left,
                "proxy_source_x_px": proxy_source_x_px,
                "proxy_source_y_px": proxy_source_y_px,
                "requested_crop_origin": {
                    "left": requested_left,
                    "top": requested_top,
                },
                "applied_crop_origin": {
                    "left": applied_left,
                    "top": applied_top,
                },
                "eye_line_requested_shift_px": {
                    "horizontal": requested_left - applied_left,
                    "vertical": requested_top - applied_top,
                },
                "eye_line_applied_shift_px": {
                    # Distance the applied origin moved AWAY from
                    # a purely centered origin — the "amount of
                    # eye-line honoring achieved" under the proxy.
                    "horizontal": applied_left - _centered_origin(
                        ctx.width_px, crop_width
                    ),
                    "vertical": applied_top - _centered_origin(
                        ctx.height_px, crop_height
                    ),
                },
                "applied_position_from_top": applied_position_from_top,
                "applied_position_from_left": applied_position_from_left,
                "eye_line_clamped": eye_line_clamped,
                "eye_line_clamped_vertical": eye_line_clamped_vertical,
                "eye_line_clamped_horizontal": eye_line_clamped_horizontal,
                "eye_line_clamp_reason": eye_line_clamp_reason,
                "legal_top_range": [legal_top_min, legal_top_max],
                "legal_left_range": [legal_left_min, legal_left_max],
            },
            # Declared-but-not-honored profile fields, with
            # explicit blockers (same discipline as v1).
            "subject_scale_declared": profile.crop.subject_scale,
            "subject_scale_honored": False,
            "subject_scale_honor_blocker": "requires_real_subject_geometry",
            "min_edge_padding_declared": profile.margins.min_edge_padding,
            "min_edge_padding_honored": False,
            "min_edge_padding_honor_blocker": "requires_real_subject_geometry",
            "framing_behavior_declared": {
                "includes": list(profile.framing_behavior.includes),
                "excludes": list(profile.framing_behavior.excludes),
            },
            "framing_behavior_honored": False,
            "framing_behavior_honor_blocker": "requires_real_subject_geometry",
            # Roll-up summary — one field per declared-semantic
            # bucket. eye_line moves from
            # blocked_by_missing_capability (v1) to
            # executed_under_proxy (v2) since v2 does honor the
            # profile's eye-line target via the source-center
            # proxy — even if clamping renders no shift in some
            # profile/input combinations.
            "profile_semantics_roll_up": {
                "aspect_ratio": "executed",
                "eye_line_position": "executed_under_source_center_proxy",
                "subject_scale": "blocked_by_missing_capability",
                "min_edge_padding": "blocked_by_missing_capability",
                "framing_behavior": "blocked_by_missing_capability",
            },
        }

        execution = StageExecution(
            stage_name=self.stage_name,
            stage_version=self.stage_version,
            status="executed",
            input_width_px=ctx.width_px,
            input_height_px=ctx.height_px,
            output_width_px=crop_width,
            output_height_px=crop_height,
            duration_ms=duration_ms,
            details=details,
        )

        new_context = StageContext(
            image_bytes=cropped_bytes,
            width_px=crop_width,
            height_px=crop_height,
            surface_profile=ctx.surface_profile,
            background=ctx.background,
        )
        return StageOutput(new_context=new_context, execution=execution)


def _clamp(value: int, lo: int, hi: int) -> int:
    """Clamp ``value`` into ``[lo, hi]``. If ``hi < lo`` (which
    only happens when the crop equals the input on this axis,
    making the legal range empty except at 0), the clamp
    collapses to ``lo``.
    """
    if hi < lo:
        return lo
    if value < lo:
        return lo
    if value > hi:
        return hi
    return value


def _centered_origin(source_dim: int, crop_dim: int) -> int:
    """Where a v1-style centered crop would place its origin on
    this axis. Used to compute ``eye_line_applied_shift_px`` —
    the difference between v2's eye-line-target origin and v1's
    centered origin.
    """
    return (source_dim - crop_dim) // 2


def _parse_aspect_ratio(ratio_str: str) -> tuple[int, int]:
    """Parse ``"a:b"`` into ``(a, b)`` reduced to lowest terms.

    Reduction defends against a profile author writing
    ``"1280:720"`` vs ``"16:9"`` for the same ratio — crop math
    depends on the reduced pair, not on the literal form.

    Raises ``StageError`` (not ``ValueError``) so pipeline
    callers see one exception class at the stage boundary.
    """
    parts = ratio_str.split(":")
    if len(parts) != 2:
        raise StageError(
            f"invalid_aspect_ratio_format: {ratio_str!r} "
            f"(expected 'a:b' with exactly one colon)"
        )
    try:
        a = int(parts[0])
        b = int(parts[1])
    except ValueError as exc:
        raise StageError(
            f"invalid_aspect_ratio_integers: {ratio_str!r}"
        ) from exc
    if a <= 0 or b <= 0:
        raise StageError(
            f"invalid_aspect_ratio_nonpositive: {ratio_str!r}"
        )
    g = math.gcd(a, b)
    return (a // g, b // g)
