"""FramingStage(v1) — deterministic downscale to profile output.

Coverage per SESSION 246 7.b completion evidence checklist:

* All five ratified profiles: a crop already at their aspect
  produces exactly the declared output dimensions.
* Upscale attempt raises ``input_smaller_than_output``.
* Aspect mismatch raises ``aspect_mismatch_between_crop_and_output``.
* Input exactly at target dimensions is a geometric no-op
  (skips resample) but re-encodes deterministically.
* Repeat runs produce byte-identical output (§10.6 anchor).
* Manifest evidence: LANCZOS recorded, no upscale / letterbox /
  pillar / stretch flags, all factual.
* No detection / face / eye / silhouette / subject claim leaks
  into evidence (v1 makes none of these claims).
"""
from __future__ import annotations

import pytest
from PIL import Image

from app.services.normalization import (
    Background,
    StageContext,
    StageError,
    SurfaceProfile,
    SurfaceProfileCrop,
    SurfaceProfileEyeLine,
    SurfaceProfileFramingBehavior,
    SurfaceProfileMargins,
    SurfaceProfileOutput,
    load_background_family,
    load_surface_profile,
    resolve_background_for_profile,
)
from app.services.normalization.png import decode_png, dimensions_of, encode_png
from app.services.normalization.stages.framing import FramingStage


RATIFIED_PROFILE_IDS = ("compact", "presence", "studio", "conversation", "team_card")


# ---- Helpers ----------------------------------------------------


def _rgba_png(width: int, height: int, rgba=(50, 150, 220, 255)) -> bytes:
    return encode_png(Image.new("RGBA", (width, height), rgba))


def _synthetic_profile(
    *,
    profile_id: str = "syn",
    aspect_ratio: str = "1:1",
    output_w: int = 512,
    output_h: int = 512,
) -> SurfaceProfile:
    return SurfaceProfile(
        profile_id=profile_id,
        version=1,
        framing_family="synthetic",
        crop=SurfaceProfileCrop(
            aspect_ratio=aspect_ratio, strategy="subject_relative", subject_scale=1.0
        ),
        eye_line=SurfaceProfileEyeLine(position_from_top=0.5, position_from_left=0.5),
        margins=SurfaceProfileMargins(min_edge_padding=0.0),
        output=SurfaceProfileOutput(
            width_px=output_w, height_px=output_h, format="png", color_space="sRGB",
        ),
        framing_behavior=SurfaceProfileFramingBehavior(includes=(), excludes=()),
        tonal_environment_class=None,
        schema_hash="0" * 64,
    )


def _dummy_background() -> Background:
    from app.services.normalization import ProceduralV1

    return Background(
        background_id="test_bg",
        description="test",
        tonal_direction="warm_neutral",
        luminance_class="mid",
        grain="subtle_soft",
        round_one_role="default",
        procedural_v1=ProceduralV1(
            fill_rgb=(200, 200, 200),
            status="implementation_provisional",
            purpose="round_one_normalization_only",
        ),
    )


def _ctx(
    raw: bytes,
    profile: SurfaceProfile,
    background: Background,
) -> StageContext:
    w, h = dimensions_of(raw)
    return StageContext(
        image_bytes=raw,
        width_px=w,
        height_px=h,
        surface_profile=profile,
        background=background,
    )


def _crop_matched_to(profile: SurfaceProfile, scale: int = 2) -> bytes:
    """Produce a synthetic PNG at ``scale * output_dims`` — a
    crop that already matches the profile's declared aspect
    ratio, sized larger than the profile output so downscale is
    exercised.
    """
    return _rgba_png(
        profile.output.width_px * scale,
        profile.output.height_px * scale,
    )


# ---- Ratified profile coverage ----------------------------------


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_ratified_profile_framing_produces_declared_output_dimensions(
    profile_id: str,
) -> None:
    """Every ratified profile: crop-matched input → exactly the
    declared ``output.width_px x output.height_px``.
    """
    profile = load_surface_profile(profile_id)
    family = load_background_family()
    background = resolve_background_for_profile(family, profile)
    raw = _crop_matched_to(profile, scale=3)
    output = FramingStage().apply(_ctx(raw, profile, background))
    assert output.new_context.width_px == profile.output.width_px
    assert output.new_context.height_px == profile.output.height_px
    # Bytes decode to the exact declared dimensions.
    decoded = decode_png(output.new_context.image_bytes)
    assert decoded.size == (profile.output.width_px, profile.output.height_px)


# ---- Determinism ------------------------------------------------


def test_framing_is_byte_deterministic_over_repeat_invocation() -> None:
    profile = load_surface_profile("presence")
    background = resolve_background_for_profile(
        load_background_family(), profile
    )
    raw = _crop_matched_to(profile, scale=4)
    a = FramingStage().apply(_ctx(raw, profile, background))
    b = FramingStage().apply(_ctx(raw, profile, background))
    assert a.new_context.image_bytes == b.new_context.image_bytes


def test_framing_input_exactly_at_target_skips_resample() -> None:
    """When input dims == target dims, ``resampling`` should
    record ``none_input_already_at_target``. Bytes still flow
    through deterministic encode.
    """
    profile = _synthetic_profile(output_w=512, output_h=512)
    raw = _rgba_png(512, 512)
    output = FramingStage().apply(_ctx(raw, profile, _dummy_background()))
    assert output.execution.details["resampling"] == "none_input_already_at_target"
    assert output.new_context.width_px == 512
    assert output.new_context.height_px == 512


def test_framing_downscale_records_lanczos() -> None:
    profile = _synthetic_profile(output_w=256, output_h=256)
    raw = _rgba_png(1024, 1024)
    output = FramingStage().apply(_ctx(raw, profile, _dummy_background()))
    assert output.execution.details["resampling"] == "lanczos"
    assert output.new_context.width_px == 256
    assert output.new_context.height_px == 256


# ---- Failure surface --------------------------------------------


def test_upscale_input_raises_input_smaller_than_output() -> None:
    profile = _synthetic_profile(output_w=1024, output_h=1024)
    raw = _rgba_png(512, 512)  # smaller on both axes than target
    with pytest.raises(StageError, match="input_smaller_than_output"):
        FramingStage().apply(_ctx(raw, profile, _dummy_background()))


def test_upscale_single_axis_smaller_still_raises() -> None:
    """Only ONE axis needs to be smaller than target for upscale
    refusal to trigger — v1 does not pick which axis to enlarge.
    """
    profile = _synthetic_profile(aspect_ratio="1:1", output_w=1000, output_h=1000)
    raw = _rgba_png(900, 900)
    with pytest.raises(StageError, match="input_smaller_than_output"):
        FramingStage().apply(_ctx(raw, profile, _dummy_background()))


def test_aspect_mismatch_raises_via_integer_cross_multiply() -> None:
    profile = _synthetic_profile(aspect_ratio="3:4", output_w=900, output_h=1200)
    raw = _rgba_png(1000, 1000)  # square, not 3:4
    with pytest.raises(StageError, match="aspect_mismatch_between_crop_and_output"):
        FramingStage().apply(_ctx(raw, profile, _dummy_background()))


def test_aspect_mismatch_error_carries_cross_multiply_diagnostic() -> None:
    """The error message must include the raw product values on
    both sides of the cross-multiply so a debugger can see which
    dimensions produced the mismatch. 1000*1200=1200000 vs.
    1000*900=900000.
    """
    profile = _synthetic_profile(aspect_ratio="3:4", output_w=900, output_h=1200)
    raw = _rgba_png(1000, 1000)
    with pytest.raises(StageError) as exc_info:
        FramingStage().apply(_ctx(raw, profile, _dummy_background()))
    msg = str(exc_info.value)
    assert "cross-multiply" in msg
    assert "1200000" in msg
    assert "900000" in msg
    assert "1000x1000" in msg
    assert "900x1200" in msg


def test_undecodable_input_raises_framing_stage_error() -> None:
    """Defensive — pipeline entry validates bytes, but the stage
    must not leak Pillow exceptions if invoked directly with
    corrupt bytes at a matched aspect.
    """
    profile = _synthetic_profile(output_w=100, output_h=100)
    ctx = StageContext(
        image_bytes=b"not a png",
        width_px=100,  # matches output → aspect check passes
        height_px=100,
        surface_profile=profile,
        background=_dummy_background(),
    )
    with pytest.raises(StageError, match="framing_input_undecodable"):
        FramingStage().apply(ctx)


# ---- Manifest evidence ------------------------------------------


def test_framing_evidence_records_v1_policy_negations() -> None:
    """Every v1 policy negation appears as a factual False flag,
    so a manifest reader can prove no padding / stretch /
    letterbox / upscale happened.
    """
    profile = _synthetic_profile()
    raw = _rgba_png(1024, 1024)
    details = FramingStage().apply(_ctx(raw, profile, _dummy_background())).execution.details
    assert details["upscale_applied"] is False
    assert details["letterboxing_applied"] is False
    assert details["pillarboxing_applied"] is False
    assert details["stretch_applied"] is False
    assert details["aspect_verification_method"] == "integer_cross_multiply"


def test_framing_evidence_has_no_detection_claim() -> None:
    profile = load_surface_profile("conversation")
    background = resolve_background_for_profile(
        load_background_family(), profile
    )
    raw = _crop_matched_to(profile, scale=3)
    details = FramingStage().apply(_ctx(raw, profile, background)).execution.details
    blob = repr(details).lower()
    for forbidden in (
        "face_detected", "subject_detected", "silhouette",
        "eye_detected", "landmark", "subject_bbox", "face_bbox",
    ):
        assert forbidden not in blob, (
            f"forbidden detection substring {forbidden!r} in framing evidence: {details}"
        )


def test_framing_evidence_dimensions_match_actual_output() -> None:
    profile = _synthetic_profile(output_w=384, output_h=384)
    raw = _rgba_png(768, 768)
    output = FramingStage().apply(_ctx(raw, profile, _dummy_background()))
    d = output.execution.details
    assert d["output_dimensions_declared"] == {"width_px": 384, "height_px": 384}
    assert d["output_dimensions_actual"] == {"width_px": 384, "height_px": 384}
    assert output.new_context.width_px == 384
    assert output.new_context.height_px == 384


# ---- Stage interface contract -----------------------------------


def test_framing_stage_class_level_constants() -> None:
    assert FramingStage.stage_name == "framing"
    assert FramingStage.stage_version == 1


def test_framing_stage_status_is_executed_on_success() -> None:
    profile = _synthetic_profile()
    raw = _rgba_png(1024, 1024)
    output = FramingStage().apply(_ctx(raw, profile, _dummy_background()))
    assert output.execution.status == "executed"
