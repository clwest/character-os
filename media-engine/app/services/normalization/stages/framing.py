"""FramingStage(v1) — deterministic downscale to profile output.

SESSION 246 ratification (7.b):

* Consumes CropStage's output (which already matches
  ``profile.crop.aspect_ratio`` via integer construction) and
  produces an image at exactly ``profile.output.width_px x
  profile.output.height_px``.

* Refuses upscale. If the incoming crop is smaller than the
  target on either axis, raises ``StageError`` with reason
  ``input_smaller_than_output``. Provider outputs are expected
  to be sufficiently large for round-one profiles; a smaller
  input is evidence, not something to silently repair. If Step
  8 shows real provider outputs that violate this expectation,
  the fix is an explicit upscale-policy decision — not a v1
  silent enlarge.

* Refuses aspect mismatch. Verifies
  ``input_w * output_h == input_h * output_w`` (integer
  cross-multiply per operator discipline — no floating-point
  equality). Raises ``aspect_mismatch_between_crop_and_output``
  if the check fails. FramingStage never letterboxes,
  pillarboxes, pads, or stretches to compensate.

* Uses ``PIL.Image.Resampling.LANCZOS`` for downscale.
  Deterministic under pinned Pillow; recorded verbatim in
  manifest ``details.resampling`` so a future Pillow upgrade
  that changes filter behavior is visible in the manifest
  diff.

* No re-resample when input dimensions already match target —
  Pillow's ``Image.resize`` with equal input/output size is
  not documented as a strict no-op, so we skip the call
  entirely to preserve byte-level determinism.

Failure surface:

* ``aspect_mismatch_between_crop_and_output`` — verified via
  integer cross-multiply.
* ``input_smaller_than_output`` — refuses upscale.
* ``framing_input_undecodable`` — bytes from upstream stage
  did not decode (defensive; upstream stages produce valid
  PNGs).
"""
from __future__ import annotations

import time
from typing import ClassVar

from PIL import Image

from ..png import BadPngError, decode_png, encode_png
from . import StageContext, StageError, StageExecution, StageOutput


_RESAMPLING_NAME = "lanczos"


class FramingStage:
    """See module docstring."""

    stage_name: ClassVar[str] = "framing"
    stage_version: ClassVar[int] = 1

    def apply(self, ctx: StageContext) -> StageOutput:
        started = time.perf_counter()
        profile = ctx.surface_profile
        input_w = ctx.width_px
        input_h = ctx.height_px
        target_w = profile.output.width_px
        target_h = profile.output.height_px

        # Aspect-ratio verification — integer cross-multiply.
        # ``crop_width * output_height == crop_height * output_width``.
        # Per operator discipline: never floating-point equality.
        # CropStage(v1) guarantees this holds by construction; the
        # check exists to catch a future stage-composition bug
        # where a non-CropStage upstream produces a mismatched
        # crop, or a future CropStage version silently drops the
        # exact-ratio invariant.
        if input_w * target_h != input_h * target_w:
            raise StageError(
                f"aspect_mismatch_between_crop_and_output: crop "
                f"{input_w}x{input_h} (ratio {input_w}:{input_h}) does not "
                f"match output {target_w}x{target_h} (ratio {target_w}:{target_h}); "
                f"cross-multiply {input_w * target_h} != {input_h * target_w}"
            )

        # Upscale refusal. Both axes must be >= target — v1 does
        # not choose which axis is "close enough" to enlarge.
        if input_w < target_w or input_h < target_h:
            raise StageError(
                f"input_smaller_than_output: crop {input_w}x{input_h} "
                f"is smaller than requested output {target_w}x{target_h} "
                f"on at least one axis; v1 policy refuses upscale."
            )

        try:
            image = decode_png(ctx.image_bytes)
        except BadPngError as exc:
            raise StageError(f"framing_input_undecodable: {exc!s}") from exc

        if input_w == target_w and input_h == target_h:
            # Pillow's Image.resize is not documented as a no-op
            # for equal sizes; skipping the call preserves bytes
            # under the stage's determinism contract.
            resampling_recorded = "none_input_already_at_target"
            framed = image
        else:
            resampling_recorded = _RESAMPLING_NAME
            framed = image.resize(
                (target_w, target_h),
                Image.Resampling.LANCZOS,
            )

        framed_bytes = encode_png(framed)
        duration_ms = int((time.perf_counter() - started) * 1000)

        details = {
            "framing_method": "deterministic_downscale_to_profile_output",
            "resampling": resampling_recorded,
            "input_dimensions": {
                "width_px": input_w,
                "height_px": input_h,
            },
            "output_dimensions_declared": {
                "width_px": target_w,
                "height_px": target_h,
            },
            "output_dimensions_actual": {
                "width_px": target_w,
                "height_px": target_h,
            },
            # v1 policy negations — factual, so a manifest reader
            # can prove no letterbox / pillar / stretch happened
            # without inspecting bytes.
            "upscale_applied": False,
            "letterboxing_applied": False,
            "pillarboxing_applied": False,
            "stretch_applied": False,
            "aspect_verification_method": "integer_cross_multiply",
            "profile_semantics_roll_up": {
                "output_dimensions": "executed",
                "output_format": "executed",
                "output_color_space": "executed",
            },
        }

        execution = StageExecution(
            stage_name=self.stage_name,
            stage_version=self.stage_version,
            status="executed",
            input_width_px=input_w,
            input_height_px=input_h,
            output_width_px=target_w,
            output_height_px=target_h,
            duration_ms=duration_ms,
            details=details,
        )

        new_context = StageContext(
            image_bytes=framed_bytes,
            width_px=target_w,
            height_px=target_h,
            surface_profile=ctx.surface_profile,
            background=ctx.background,
        )
        return StageOutput(new_context=new_context, execution=execution)
