"""BackgroundReplacementStage(v1) — matte + composite tests
(SESSION 246 7.c).

Coverage per operator ratification:

* All five ratified backgrounds accepted through the stage.
* Deterministic byte output over repeated identical runs
  (§10.6 anchor at stage level).
* Rembg failure → StageError; never silent pass-through.
* Output dimensions unchanged from input.
* Composited output is a valid PNG.
* Procedural fill_rgb sourced only from YAML — never a Python
  constant.
* No aesthetic / detection-claim language leaks into evidence.
* All v1 policy negations (no tonal / lighting / relighting /
  sharpening / etc.) recorded as factual False flags.

Live rembg runs are moderately slow (first call loads the
u2net_human_seg ONNX model — ~1 s + ~176 MB). Tests use small
synthetic RGBA inputs (256x256) so the collection completes
in a few seconds after model warm-up.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.normalization import (
    Background,
    ProceduralV1,
    StageContext,
    StageError,
    SurfaceProfile,
    SurfaceProfileCrop,
    SurfaceProfileEyeLine,
    SurfaceProfileFramingBehavior,
    SurfaceProfileMargins,
    SurfaceProfileOutput,
    load_background_family,
)
from app.services.normalization.png import decode_png, dimensions_of, encode_png
from app.services.normalization.stages.background_replacement import (
    BackgroundReplacementStage,
)


RATIFIED_BG_IDS = (
    "neutral_warm_studio",
    "neutral_cool_studio",
    "warm_material_surround",
    "soft_environmental_depth",
    "conversational_darker_surround",
)


# ---- Helpers ----------------------------------------------------


def _rgba_png(width: int = 256, height: int = 256, rgba=(200, 120, 60, 255)) -> bytes:
    return encode_png(Image.new("RGBA", (width, height), rgba))


def _profile_stub() -> SurfaceProfile:
    return SurfaceProfile(
        profile_id="stub",
        version=1,
        framing_family="synthetic",
        crop=SurfaceProfileCrop(
            aspect_ratio="1:1", strategy="subject_relative", subject_scale=1.0,
        ),
        eye_line=SurfaceProfileEyeLine(position_from_top=0.5, position_from_left=0.5),
        margins=SurfaceProfileMargins(min_edge_padding=0.0),
        output=SurfaceProfileOutput(
            width_px=256, height_px=256, format="png", color_space="sRGB",
        ),
        framing_behavior=SurfaceProfileFramingBehavior(includes=(), excludes=()),
        tonal_environment_class=None,
        schema_hash="0" * 64,
    )


def _ctx(raw: bytes, background: Background) -> StageContext:
    w, h = dimensions_of(raw)
    return StageContext(
        image_bytes=raw,
        width_px=w,
        height_px=h,
        surface_profile=_profile_stub(),
        background=background,
    )


def _resolve_ratified_background(bg_id: str) -> Background:
    family = load_background_family()
    for bg in family.backgrounds:
        if bg.background_id == bg_id:
            return bg
    raise AssertionError(f"unknown ratified background id: {bg_id!r}")


# ---- Ratified-background coverage -------------------------------


@pytest.mark.parametrize("bg_id", RATIFIED_BG_IDS)
def test_every_ratified_background_runs_through_stage(bg_id: str) -> None:
    """Every controlled background accepted; produces a valid
    PNG at unchanged dimensions.
    """
    background = _resolve_ratified_background(bg_id)
    raw = _rgba_png(256, 256)
    output = BackgroundReplacementStage().apply(_ctx(raw, background))
    assert output.execution.status == "executed"
    assert output.new_context.width_px == 256
    assert output.new_context.height_px == 256
    decoded = decode_png(output.new_context.image_bytes)
    assert decoded.mode == "RGBA"
    assert decoded.size == (256, 256)


@pytest.mark.parametrize("bg_id", RATIFIED_BG_IDS)
def test_evidence_records_background_source_procedural_v1(bg_id: str) -> None:
    """Every executed stage records ``background_source =
    "procedural_v1"`` with the ratified fill_rgb — sourced only
    from YAML.
    """
    background = _resolve_ratified_background(bg_id)
    output = BackgroundReplacementStage().apply(_ctx(_rgba_png(), background))
    details = output.execution.details
    assert details["background_source"] == "procedural_v1"
    assert details["background_id"] == bg_id
    r, g, b = background.procedural_v1.fill_rgb
    assert details["fill_rgb"] == [r, g, b]
    assert details["tonal_direction"] == background.tonal_direction
    assert details["luminance_class"] == background.luminance_class


# ---- Determinism ------------------------------------------------


def test_stage_output_deterministic_over_repeat_invocation() -> None:
    """§10.6 anchor at stage level: identical input + identical
    background → byte-identical output.
    """
    background = _resolve_ratified_background("neutral_warm_studio")
    raw = _rgba_png(256, 256)
    a = BackgroundReplacementStage().apply(_ctx(raw, background))
    b = BackgroundReplacementStage().apply(_ctx(raw, background))
    assert a.new_context.image_bytes == b.new_context.image_bytes


def test_different_backgrounds_produce_different_bytes_for_same_input() -> None:
    """Two backgrounds with different fill_rgb produce distinct
    composited output. Proves the fill_rgb is actually consumed
    (not silently ignored).
    """
    raw = _rgba_png(256, 256)
    bg_warm = _resolve_ratified_background("neutral_warm_studio")
    bg_dark = _resolve_ratified_background("conversational_darker_surround")
    out_warm = BackgroundReplacementStage().apply(_ctx(raw, bg_warm))
    out_dark = BackgroundReplacementStage().apply(_ctx(raw, bg_dark))
    assert out_warm.new_context.image_bytes != out_dark.new_context.image_bytes


# ---- Composited-pixel correctness -------------------------------


def test_composited_edge_pixels_carry_procedural_fill_when_matte_removes_edges() -> None:
    """Rembg on a small solid-color input matting an implausible
    "subject" typically removes the entire content (nothing
    that looks like a person). The resulting composite should
    show the procedural fill in edge regions.

    This assertion is soft — rembg may or may not remove
    everything from a solid-color synthetic input. The
    load-bearing test is that SOMEWHERE in the output, the
    procedural fill's RGB values appear. If not, the stage
    silently returned the input unchanged.
    """
    background = _resolve_ratified_background("conversational_darker_surround")
    fill_rgb = background.procedural_v1.fill_rgb  # (62, 56, 50)
    raw = _rgba_png(256, 256, rgba=(200, 120, 60, 255))
    output = BackgroundReplacementStage().apply(_ctx(raw, background))
    decoded = decode_png(output.new_context.image_bytes)
    # Sample the corner pixel — rembg's u2net_human_seg reliably
    # removes non-human content from corners. Alpha_composite
    # over the procedural fill produces the fill's RGB there.
    corner_r, corner_g, corner_b, corner_a = decoded.getpixel((0, 0))
    # Corner should be at (or very close to) the procedural fill
    # (rembg alpha may not be exactly 0 at every corner pixel;
    # tolerance of ±3 accounts for edge-of-matte blending).
    assert abs(corner_r - fill_rgb[0]) < 5
    assert abs(corner_g - fill_rgb[1]) < 5
    assert abs(corner_b - fill_rgb[2]) < 5
    assert corner_a == 255


# ---- Failure surface --------------------------------------------


def test_rembg_failure_raises_stage_error_not_silent_pass_through() -> None:
    """Corrupt input bytes cause rembg to raise. The stage must
    surface this as ``StageError``, never return the raw input
    while claiming the stage executed.
    """
    background = _resolve_ratified_background("neutral_warm_studio")
    ctx = StageContext(
        image_bytes=b"not a png",
        width_px=256,
        height_px=256,
        surface_profile=_profile_stub(),
        background=background,
    )
    with pytest.raises(StageError, match="background_replacement_failed"):
        BackgroundReplacementStage().apply(ctx)


def test_evidence_never_contains_aesthetic_or_detection_claim() -> None:
    """Per SESSION 246 operator discipline — no aesthetic /
    detection language in stage evidence.
    """
    background = _resolve_ratified_background("neutral_warm_studio")
    details = (
        BackgroundReplacementStage()
        .apply(_ctx(_rgba_png(), background))
        .execution.details
    )
    blob = repr(details).lower()
    for forbidden in (
        "excellent", "poor", "quality", "beautiful",
        "face_detected", "subject_detected", "silhouette",
        "eye_detected", "landmark",
    ):
        assert forbidden not in blob, (
            f"forbidden substring {forbidden!r} in background replacement "
            f"evidence: {details}"
        )


# ---- v1 policy negations recorded factually ---------------------


def test_v1_policy_negations_recorded_as_false_flags() -> None:
    background = _resolve_ratified_background("neutral_warm_studio")
    details = (
        BackgroundReplacementStage()
        .apply(_ctx(_rgba_png(), background))
        .execution.details
    )
    for negated in (
        "tonal_adjustment_applied",
        "lighting_adjustment_applied",
        "exposure_adjustment_applied",
        "relighting_applied",
        "sharpening_applied",
        "denoise_applied",
        "beautification_applied",
        "shadow_synthesis_applied",
        "color_grading_applied",
        "skin_correction_applied",
    ):
        assert details[negated] is False, (
            f"v1 policy negation {negated!r} not recorded as False"
        )


# ---- Stage contract ---------------------------------------------


def test_background_replacement_stage_class_level_constants() -> None:
    assert BackgroundReplacementStage.stage_name == "background_replacement"
    assert BackgroundReplacementStage.stage_version == 1


def test_procedural_fill_rgb_traceable_to_yaml() -> None:
    """The manifest's fill_rgb must equal the YAML value. Proves
    the stage never invents an RGB — always reads from
    declarative config.
    """
    family = load_background_family()
    for bg in family.backgrounds:
        r, g, b = bg.procedural_v1.fill_rgb
        details = (
            BackgroundReplacementStage()
            .apply(_ctx(_rgba_png(), bg))
            .execution.details
        )
        assert details["fill_rgb"] == [r, g, b]
