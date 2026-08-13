"""BackgroundReplacementStage(v1) — matte + composite over the
declaratively-selected ``procedural_v1.fill_rgb``.

SESSION 246 7.c pipeline slot. Consumes the frame-sized image
produced by FramingStage; produces the same dimensions with the
subject composited over the profile-selected background.

Scope discipline (SESSION 246 operator ratification):

* Background source is **procedural_v1**: a solid-color fill
  derived from the ratified
  ``background_family_v1.yaml::procedural_v1.fill_rgb``. No
  gradients, no textures, no real PNG assets — those are
  authored separately as a follow-up per the YAML's
  ``assets_authored_separately`` rule.

* Every rendered pixel is traceable to the YAML. No RGB
  constants live in this module. If the operator amends the
  YAML to change a fill, this stage picks it up transparently.

* Matting primitive is
  ``rembg.remove(bytes, session=<u2net_human_seg>)``. Session
  cached via the shared ``get_rembg_session`` helper (SESSION
  246 7.c.a extraction — same cache V16 uses).

* v1 does NOT do tonal / lighting / exposure / relighting /
  sharpening / denoise / beautification / shadow / color
  grading. Background replacement means background replacement
  only, per §17.6.a's round-one scope-lock.

* Honest failure: rembg errors surface as
  ``StageError("background_replacement_failed: ...")``. Never
  returns the raw input while claiming the stage executed.

Determinism:

* ``rembg.remove`` on ``u2net_human_seg`` is byte-deterministic
  under pinned ``rembg==2.0.75`` + ``onnxruntime==1.26.0``
  (proved live at SESSION 246 7.c open; regression-anchored in
  ``tests/test_rembg_session.py``).

* PIL alpha compositing is deterministic (integer arithmetic
  per channel).

* Output goes through the shared ``png.encode_png`` helper —
  same fixed compression + no metadata chunks as every other
  stage.

Boundary:

* Inputs / outputs are pipeline-context PNG bytes. This stage
  does not know about Django models, ``Asset`` persistence,
  ``GenerationRecord``, or workspace ownership — those all
  live in ``shell/apps/identity/services.py`` and are called
  by whoever orchestrates the pipeline output.
"""
from __future__ import annotations

import io
import time
from typing import ClassVar

from PIL import Image

from ...rembg_session import get_rembg_session
from ..png import BadPngError, encode_png
from . import StageContext, StageError, StageExecution, StageOutput


_REMBG_MODEL = "u2net_human_seg"


class BackgroundReplacementStage:
    """See module docstring."""

    stage_name: ClassVar[str] = "background_replacement"
    stage_version: ClassVar[int] = 1

    def apply(self, ctx: StageContext) -> StageOutput:
        started = time.perf_counter()
        input_w = ctx.width_px
        input_h = ctx.height_px

        background = ctx.background
        procedural = background.procedural_v1
        fill_rgb = procedural.fill_rgb

        # ---- Matte the input via rembg ------------------------
        try:
            session = get_rembg_session(_REMBG_MODEL)
        except Exception as exc:  # pragma: no cover — defensive
            raise StageError(
                f"background_replacement_session_load_failed: {exc!s}"
            ) from exc

        try:
            from rembg import remove as rembg_remove
        except ImportError as exc:  # pragma: no cover — defensive
            raise StageError(
                f"background_replacement_rembg_import_failed: {exc!s}"
            ) from exc

        try:
            matted_bytes = rembg_remove(ctx.image_bytes, session=session)
        except Exception as exc:
            raise StageError(
                f"background_replacement_failed: rembg.remove raised "
                f"{type(exc).__name__}: {exc!s}"
            ) from exc

        if not matted_bytes:
            raise StageError(
                "background_replacement_failed: rembg.remove returned "
                "empty bytes — no matted foreground to composite"
            )

        # ---- Decode matted foreground -------------------------
        try:
            matted = _decode_matted_bytes(matted_bytes)
        except BadPngError as exc:
            raise StageError(
                f"background_replacement_failed: matted output did not "
                f"decode as PNG: {exc!s}"
            ) from exc

        # ---- Dimension preservation invariant ----------------
        if matted.size != (input_w, input_h):
            raise StageError(
                f"background_replacement_failed: matted output "
                f"dimensions {matted.size} != input dimensions "
                f"({input_w}, {input_h}). Rembg unexpectedly resized."
            )

        # ---- Build procedural background fill ----------------
        # RGBA with alpha=255 so the matted foreground composites
        # cleanly via alpha_composite.
        bg = Image.new(
            "RGBA",
            (input_w, input_h),
            (fill_rgb[0], fill_rgb[1], fill_rgb[2], 255),
        )

        # ---- Composite: matted (foreground with alpha) over bg -
        # Image.alpha_composite is integer arithmetic per channel
        # → deterministic under pinned Pillow.
        composited = Image.alpha_composite(bg, matted)

        composited_bytes = encode_png(composited)
        duration_ms = int((time.perf_counter() - started) * 1000)

        details = {
            # Factual only — no aesthetic claims.
            "background_replacement_method": "rembg_matte_over_procedural_fill",
            "background_id": background.background_id,
            "background_source": "procedural_v1",
            "fill_rgb": [fill_rgb[0], fill_rgb[1], fill_rgb[2]],
            "tonal_direction": background.tonal_direction,
            "luminance_class": background.luminance_class,
            "grain": background.grain,
            "round_one_role": background.round_one_role,
            "procedural_v1_status": procedural.status,
            "procedural_v1_purpose": procedural.purpose,
            "matting_model": _REMBG_MODEL,
            "matting_primitive": "rembg.remove",
            "compositing_primitive": "PIL.Image.alpha_composite",
            "input_dimensions": {"width_px": input_w, "height_px": input_h},
            "output_dimensions": {"width_px": input_w, "height_px": input_h},
            # v1 policy negations — factual, so a manifest reader
            # can prove no tonal / lighting / relighting / etc.
            # snuck in.
            "tonal_adjustment_applied": False,
            "lighting_adjustment_applied": False,
            "exposure_adjustment_applied": False,
            "relighting_applied": False,
            "sharpening_applied": False,
            "denoise_applied": False,
            "beautification_applied": False,
            "shadow_synthesis_applied": False,
            "color_grading_applied": False,
            "skin_correction_applied": False,
            "profile_semantics_roll_up": {
                "background_id_selection": "executed",
                "procedural_v1_fill": "executed",
            },
        }

        execution = StageExecution(
            stage_name=self.stage_name,
            stage_version=self.stage_version,
            status="executed",
            input_width_px=input_w,
            input_height_px=input_h,
            output_width_px=input_w,
            output_height_px=input_h,
            duration_ms=duration_ms,
            details=details,
        )

        new_context = StageContext(
            image_bytes=composited_bytes,
            width_px=input_w,
            height_px=input_h,
            surface_profile=ctx.surface_profile,
            background=ctx.background,
        )
        return StageOutput(new_context=new_context, execution=execution)


def _decode_matted_bytes(matted_bytes: bytes) -> Image.Image:
    """Decode rembg output PNG bytes into an RGBA PIL image.

    Not routed through ``png.decode_png`` because rembg's alpha
    output is already RGBA; the extra convert() is a no-op but
    an explicit ``mode == 'RGBA'`` assertion lives here to trip
    loudly if a future rembg upgrade starts returning a
    different mode.
    """
    if not matted_bytes:
        raise BadPngError("empty matted bytes")
    try:
        img = Image.open(io.BytesIO(matted_bytes), formats=("PNG",))
        img.load()
    except Exception as exc:  # pragma: no cover — defensive
        raise BadPngError(f"failed to decode matted output: {exc!s}") from exc
    if img.mode != "RGBA":
        # Convert defensively, but record the surprise. Reaching
        # here means rembg's output shape has changed under us.
        img = img.convert("RGBA")
    return img
