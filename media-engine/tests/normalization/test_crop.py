"""CropStage(v1) — deterministic center-only aspect crop.

Coverage per SESSION 246 7.b completion evidence checklist:

* All five ratified profiles produce their declared crop aspect.
* Determinism: same input + same profile → same crop_box every
  run + byte-identical cropped bytes.
* Horizontal (landscape) input exercises height-limited crop.
* Vertical (portrait) input exercises width-limited crop.
* Square-matched input produces a full-image crop (geometric
  no-op).
* Extreme aspect ratios still crop cleanly where dimensions
  permit.
* Malformed / corrupt / degenerate inputs raise ``StageError``
  (not raw Pillow exceptions).
* Manifest evidence: all required fields, factual language only,
  no subject/face/eye/silhouette/detection claims.
* Integer cross-multiply invariant holds by construction across
  every profile.
* subject_scale / min_edge_padding / framing_behavior recorded
  as declared-but-not-honored with factual blockers.
"""
from __future__ import annotations

import re

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
from app.services.normalization.stages.crop import CropStage, _parse_aspect_ratio


RATIFIED_PROFILE_IDS = ("compact", "presence", "studio", "conversation", "team_card")


# ---- Helpers ----------------------------------------------------


def _rgba_png(width: int, height: int, rgba=(180, 100, 40, 255)) -> bytes:
    """Deterministic synthetic RGBA input for crop tests."""
    return encode_png(Image.new("RGBA", (width, height), rgba))


def _ctx_from_bytes(
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


def _profile_and_background(profile_id: str) -> tuple[SurfaceProfile, Background]:
    profile = load_surface_profile(profile_id)
    family = load_background_family()
    background = resolve_background_for_profile(family, profile)
    return profile, background


def _synthetic_profile(
    profile_id: str = "syn",
    *,
    aspect_ratio: str = "1:1",
    subject_scale: float = 1.0,
    min_edge_padding: float = 0.0,
    width_px: int = 512,
    height_px: int = 512,
) -> SurfaceProfile:
    """Build a SurfaceProfile in-process for tests that need
    aspect ratios beyond the ratified five profiles.
    """
    return SurfaceProfile(
        profile_id=profile_id,
        version=1,
        framing_family="synthetic",
        crop=SurfaceProfileCrop(
            aspect_ratio=aspect_ratio,
            strategy="subject_relative",
            subject_scale=subject_scale,
        ),
        eye_line=SurfaceProfileEyeLine(position_from_top=0.5, position_from_left=0.5),
        margins=SurfaceProfileMargins(min_edge_padding=min_edge_padding),
        output=SurfaceProfileOutput(
            width_px=width_px,
            height_px=height_px,
            format="png",
            color_space="sRGB",
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


# ---- Ratified profile coverage ----------------------------------


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_ratified_profile_crop_produces_declared_aspect_via_cross_multiply(
    profile_id: str,
) -> None:
    """Each ratified profile's crop, applied to a 2000x2000 input,
    produces output whose ``crop_width * declared_b == crop_height
    * declared_a`` — the operator-locked integer discipline.
    """
    profile, background = _profile_and_background(profile_id)
    ctx = _ctx_from_bytes(_rgba_png(2000, 2000), profile, background)
    output = CropStage().apply(ctx)
    cw = output.new_context.width_px
    ch = output.new_context.height_px
    a, b = _parse_aspect_ratio(profile.crop.aspect_ratio)
    assert cw * b == ch * a, (
        f"{profile_id}: crop {cw}x{ch} not in ratio {a}:{b} "
        f"(cross-multiply {cw * b} != {ch * a})"
    )


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_ratified_profile_crop_evidence_records_declared_not_honored(
    profile_id: str,
) -> None:
    """Every ratified profile's manifest evidence explicitly
    records subject_scale / min_edge_padding / framing_behavior
    as declared-but-not-honored with a factual blocker.
    """
    profile, background = _profile_and_background(profile_id)
    ctx = _ctx_from_bytes(_rgba_png(1024, 1024), profile, background)
    details = CropStage().apply(ctx).execution.details
    assert details["subject_scale_declared"] == profile.crop.subject_scale
    assert details["subject_scale_honored"] is False
    assert details["subject_scale_honor_blocker"]  # non-empty string
    assert details["min_edge_padding_declared"] == profile.margins.min_edge_padding
    assert details["min_edge_padding_honored"] is False
    assert details["framing_behavior_honored"] is False


# ---- Determinism ------------------------------------------------


def test_crop_is_deterministic_over_repeat_invocation() -> None:
    """Same input bytes + same profile → identical crop_box and
    identical output bytes across repeat invocations. §10.6
    determinism anchor at the stage level.
    """
    profile, background = _profile_and_background("presence")
    ctx = _ctx_from_bytes(_rgba_png(1600, 1200), profile, background)
    a = CropStage().apply(ctx)
    b = CropStage().apply(ctx)
    assert a.execution.details["crop_box"] == b.execution.details["crop_box"]
    assert a.new_context.image_bytes == b.new_context.image_bytes


def test_crop_box_matches_cropped_dimensions() -> None:
    """The crop_box coordinates and cropped_dimensions must
    describe the same rectangle. Guards against a divergence
    where evidence and image would drift silently.
    """
    profile, background = _profile_and_background("conversation")
    ctx = _ctx_from_bytes(_rgba_png(2000, 2000), profile, background)
    details = CropStage().apply(ctx).execution.details
    box = details["crop_box"]
    dims = details["cropped_dimensions"]
    assert box["right"] - box["left"] == dims["width_px"]
    assert box["bottom"] - box["top"] == dims["height_px"]


# ---- Directional crop cases -------------------------------------


def test_landscape_input_1_to_1_profile_crops_horizontally() -> None:
    """1000x600 input + 1:1 profile → 600x600 centered crop
    (horizontal margins trimmed).
    """
    profile = _synthetic_profile(aspect_ratio="1:1")
    ctx = _ctx_from_bytes(_rgba_png(1000, 600), profile, _dummy_background())
    output = CropStage().apply(ctx)
    box = output.execution.details["crop_box"]
    assert output.new_context.width_px == 600
    assert output.new_context.height_px == 600
    assert box == {"left": 200, "top": 0, "right": 800, "bottom": 600}


def test_portrait_input_1_to_1_profile_crops_vertically() -> None:
    """600x1000 input + 1:1 profile → 600x600 centered crop
    (vertical margins trimmed).
    """
    profile = _synthetic_profile(aspect_ratio="1:1")
    ctx = _ctx_from_bytes(_rgba_png(600, 1000), profile, _dummy_background())
    output = CropStage().apply(ctx)
    box = output.execution.details["crop_box"]
    assert output.new_context.width_px == 600
    assert output.new_context.height_px == 600
    assert box == {"left": 0, "top": 200, "right": 600, "bottom": 800}


def test_exact_match_input_full_image_crop_is_no_op_geometrically() -> None:
    """900x1200 input + 3:4 profile → 900x1200 crop (full image,
    box == (0,0,900,1200)).
    """
    profile = _synthetic_profile(aspect_ratio="3:4", width_px=900, height_px=1200)
    ctx = _ctx_from_bytes(_rgba_png(900, 1200), profile, _dummy_background())
    output = CropStage().apply(ctx)
    box = output.execution.details["crop_box"]
    assert output.new_context.width_px == 900
    assert output.new_context.height_px == 1200
    assert box == {"left": 0, "top": 0, "right": 900, "bottom": 1200}


def test_aspect_ratio_reduction_1280_720_matches_16_9() -> None:
    """"1280:720" and "16:9" are the same ratio. CropStage must
    treat them identically (gcd reduction in ``_parse_aspect_ratio``).
    """
    p1 = _synthetic_profile(aspect_ratio="1280:720")
    p2 = _synthetic_profile(aspect_ratio="16:9")
    ctx1 = _ctx_from_bytes(_rgba_png(1920, 1080), p1, _dummy_background())
    ctx2 = _ctx_from_bytes(_rgba_png(1920, 1080), p2, _dummy_background())
    d1 = CropStage().apply(ctx1).execution.details
    d2 = CropStage().apply(ctx2).execution.details
    assert d1["cropped_dimensions"] == d2["cropped_dimensions"]
    assert d1["crop_box"] == d2["crop_box"]
    assert d1["target_aspect_ratio_reduced_pair"] == [16, 9]
    assert d2["target_aspect_ratio_reduced_pair"] == [16, 9]


def test_extreme_landscape_aspect_ratio_still_produces_valid_crop() -> None:
    """21:9 profile on a 4200x900 input → 2100x900 landscape
    crop (k = min(4200//21, 900//9) = min(200, 100) = 100 →
    2100x900).
    """
    profile = _synthetic_profile(aspect_ratio="21:9")
    ctx = _ctx_from_bytes(_rgba_png(4200, 900), profile, _dummy_background())
    output = CropStage().apply(ctx)
    assert output.new_context.width_px == 2100
    assert output.new_context.height_px == 900
    assert 2100 * 9 == 900 * 21


def test_extreme_portrait_aspect_ratio_still_produces_valid_crop() -> None:
    """1:3 profile on a 800x2400 input → 800x2400 crop
    (k = min(800//1, 2400//3) = min(800, 800) = 800).
    """
    profile = _synthetic_profile(aspect_ratio="1:3")
    ctx = _ctx_from_bytes(_rgba_png(800, 2400), profile, _dummy_background())
    output = CropStage().apply(ctx)
    assert output.new_context.width_px == 800
    assert output.new_context.height_px == 2400


# ---- Failure surface --------------------------------------------


def test_undecodable_input_raises_stage_error() -> None:
    """Garbage bytes at the stage boundary raise a stage-domain
    error, not a raw Pillow exception. The pipeline entry point
    validates bytes upfront but a stage must not leak Pillow
    types even if invoked directly.
    """
    profile = _synthetic_profile()
    ctx = StageContext(
        image_bytes=b"not a png",
        width_px=100,
        height_px=100,
        surface_profile=profile,
        background=_dummy_background(),
    )
    with pytest.raises(StageError, match="crop_input_undecodable"):
        CropStage().apply(ctx)


def test_tiny_input_below_one_aspect_unit_raises_stage_error() -> None:
    """A 2x2 input with a 16:9 profile cannot fit any integer
    multiple of 16x9 — degenerate case must fail explicitly.
    """
    profile = _synthetic_profile(aspect_ratio="16:9")
    ctx = _ctx_from_bytes(_rgba_png(2, 2), profile, _dummy_background())
    with pytest.raises(StageError, match="crop_impossible_at_input_dimensions"):
        CropStage().apply(ctx)


@pytest.mark.parametrize("ratio", ["not_a_ratio", "1:2:3", "abc:def", ""])
def test_malformed_aspect_ratio_string_raises_stage_error(ratio: str) -> None:
    profile = _synthetic_profile(aspect_ratio=ratio)
    ctx = _ctx_from_bytes(_rgba_png(100, 100), profile, _dummy_background())
    with pytest.raises(StageError, match="invalid_aspect_ratio"):
        CropStage().apply(ctx)


@pytest.mark.parametrize("ratio", ["0:1", "1:0", "-1:2", "3:-2"])
def test_nonpositive_aspect_ratio_raises_stage_error(ratio: str) -> None:
    profile = _synthetic_profile(aspect_ratio=ratio)
    ctx = _ctx_from_bytes(_rgba_png(100, 100), profile, _dummy_background())
    with pytest.raises(StageError, match="invalid_aspect_ratio"):
        CropStage().apply(ctx)


# ---- Manifest language discipline -------------------------------


# Forbidden = claims that would only be true under real detection.
# Kept narrow enough NOT to collide with the permitted key
# ``subject_detection_method: 'none'`` (which necessarily contains
# the substring ``subject_detect``). Broader substrings would false-
# positive against v1's honest disavowal.
_FORBIDDEN_SUBSTRINGS = (
    "face_detected",
    "subject_detected",
    "silhouette",
    "eye_detected",
    "eye_line_detected",
    "landmark",
    "recognized_face",
    "face_detect_score",
    "subject_bbox",
    "face_bbox",
)


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_crop_evidence_makes_no_detection_claim(profile_id: str) -> None:
    """Per SESSION 246 operator discipline: v1 evidence must not
    describe any real detection. The only permitted mention of
    detection is ``subject_detection_method: 'none'``.
    """
    profile, background = _profile_and_background(profile_id)
    ctx = _ctx_from_bytes(_rgba_png(1024, 1024), profile, background)
    details = CropStage().apply(ctx).execution.details
    # subject_detection_method is the ONE permitted use of the
    # word; its value must be exactly "none".
    assert details["subject_detection_method"] == "none"
    # Serialize the full details dict to a lowercase string and
    # search for forbidden claim substrings.
    blob = repr(details).lower()
    for forbidden in _FORBIDDEN_SUBSTRINGS:
        assert forbidden not in blob, (
            f"forbidden detection-claim substring {forbidden!r} "
            f"leaked into crop stage evidence: {details}"
        )


def test_crop_evidence_has_no_aesthetic_language() -> None:
    """No quality claims permitted anywhere in stage evidence.
    Guards against a future refactor that accidentally moves
    aesthetic text into details.
    """
    profile, background = _profile_and_background("presence")
    ctx = _ctx_from_bytes(_rgba_png(1024, 1024), profile, background)
    details = CropStage().apply(ctx).execution.details
    blob = repr(details).lower()
    for forbidden in ("excellent", "poor", "good", "bad", "quality", "beautiful", "attractive"):
        assert forbidden not in blob


# ---- Roll-up summary ---------------------------------------------


def test_profile_semantics_roll_up_records_executed_vs_blocked() -> None:
    """CropStage(v2) roll-up per SESSION 246 7.c ratification:
    aspect_ratio executes; eye_line_position executes under the
    source-center proxy; subject_scale + min_edge_padding +
    framing_behavior remain blocked_by_missing_capability.
    CropStage(v1) (7.b) had no eye_line_position key at all —
    v2 folded eye-line positioning into the crop-window-origin
    decision.
    """
    profile, background = _profile_and_background("presence")
    ctx = _ctx_from_bytes(_rgba_png(1024, 1024), profile, background)
    roll_up = CropStage().apply(ctx).execution.details["profile_semantics_roll_up"]
    assert roll_up == {
        "aspect_ratio": "executed",
        "eye_line_position": "executed_under_source_center_proxy",
        "subject_scale": "blocked_by_missing_capability",
        "min_edge_padding": "blocked_by_missing_capability",
        "framing_behavior": "blocked_by_missing_capability",
    }


# ---- Cropped bytes round-trip via decode --------------------------


def test_cropped_bytes_decode_to_expected_dimensions() -> None:
    """The cropped bytes must round-trip cleanly through
    ``decode_png`` and produce an image whose size matches
    ``cropped_dimensions`` verbatim.
    """
    profile = _synthetic_profile(aspect_ratio="3:4")
    ctx = _ctx_from_bytes(_rgba_png(1500, 2000), profile, _dummy_background())
    output = CropStage().apply(ctx)
    decoded = decode_png(output.new_context.image_bytes)
    assert decoded.size == (
        output.new_context.width_px,
        output.new_context.height_px,
    )


# ---- No padding / stretch / letterbox behavior -------------------


def test_crop_never_adds_padding_or_letterbox() -> None:
    """The cropped output dimensions must be a strict inward
    crop — never larger than the input on either axis. Guards
    against a bug that would silently pad to reach target
    dimensions.
    """
    profile = _synthetic_profile(aspect_ratio="1:1")
    ctx = _ctx_from_bytes(_rgba_png(400, 300), profile, _dummy_background())
    output = CropStage().apply(ctx)
    assert output.new_context.width_px <= 400
    assert output.new_context.height_px <= 300


# ---- Stage interface contract ------------------------------------


def test_crop_stage_class_level_constants() -> None:
    """SESSION 246 7.c bumps ``CropStage`` from v1 to v2 —
    v2 folds eye-line positioning into the crop-window-origin
    decision (see module docstring). Version bump is the
    audit-visible signal.
    """
    assert CropStage.stage_name == "crop"
    assert CropStage.stage_version == 2


def test_crop_stage_status_is_executed_on_success() -> None:
    profile = _synthetic_profile()
    ctx = _ctx_from_bytes(_rgba_png(400, 400), profile, _dummy_background())
    assert CropStage().apply(ctx).execution.status == "executed"


# ---- Aspect-ratio parser ----------------------------------------


@pytest.mark.parametrize(
    "ratio,expected",
    [
        ("1:1", (1, 1)),
        ("3:4", (3, 4)),
        ("4:5", (4, 5)),
        ("16:9", (16, 9)),
        ("1280:720", (16, 9)),  # gcd-reduced
        ("100:100", (1, 1)),
    ],
)
def test_parse_aspect_ratio_reduces_to_lowest_terms(
    ratio: str, expected: tuple[int, int]
) -> None:
    assert _parse_aspect_ratio(ratio) == expected


# ---- CropStage v2 eye-line-target coverage (SESSION 246 7.c) ----


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_v2_evidence_records_eye_line_method_and_target(profile_id: str) -> None:
    """Every ratified profile's crop evidence emits the v2
    eye-line block with a factual method identifier and the
    profile's declared target vertical fraction.
    """
    profile, background = _profile_and_background(profile_id)
    ctx = _ctx_from_bytes(_rgba_png(2000, 2000), profile, background)
    ela = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
    assert ela["eye_line_method"] == "source_center_proxy"
    assert ela["eye_line_target_from_top"] == profile.eye_line.position_from_top
    assert ela["eye_line_target_from_left"] == profile.eye_line.position_from_left


def test_v2_requested_origin_is_deterministic_over_repeat_invocation() -> None:
    """Same input + same profile → identical requested origin +
    identical applied origin every run.
    """
    profile, background = _profile_and_background("presence")
    ctx = _ctx_from_bytes(_rgba_png(2000, 2000), profile, background)
    a = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
    b = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
    assert a["requested_crop_origin"] == b["requested_crop_origin"]
    assert a["applied_crop_origin"] == b["applied_crop_origin"]


def test_v2_headroom_produces_nonzero_applied_shift() -> None:
    """With sufficient vertical headroom, v2 applies a nonzero
    shift so the source-center proxy lands at the profile's
    declared eye-line target inside the crop.

    Studio profile: aspect 3:4, eye_line_target_from_top=0.34.
    Input 400x1000 → k = min(400//3, 1000//4) = 133 →
    crop 399x532. Vertical legal range [0, 468]. Requested top
    = 500 (source_center) − round(0.34*532)=181 → 319 (legal,
    no clamp). Applied shift vs v1-centered origin ((1000-532)//2
    = 234) = 319 − 234 = +85 (crop top pushed downward, moving
    the source center higher in the frame → eye above center,
    matching Studio's 0.34 intent).
    """
    profile, background = _profile_and_background("studio")
    ctx = _ctx_from_bytes(_rgba_png(400, 1000), profile, background)
    ela = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
    assert ela["eye_line_clamped"] is False
    assert ela["eye_line_applied_shift_px"]["vertical"] != 0
    # Direction check: 0.34 < 0.5, so eye is above center → crop
    # top pushed DOWN from a centered position → positive shift.
    assert ela["eye_line_applied_shift_px"]["vertical"] > 0


def test_v2_no_headroom_clamps_deterministically_to_zero_applied_shift() -> None:
    """When the crop fully covers the input on the vertical
    axis (no headroom), the applied crop origin clamps to the
    centered origin — applied_shift_px equals 0 with
    ``eye_line_clamped=True`` and a factual clamp reason.
    """
    # Compact profile: aspect 1:1. Square input → k*1 = min
    # dim → full-image crop → zero headroom either axis.
    profile, background = _profile_and_background("compact")
    ctx = _ctx_from_bytes(_rgba_png(2000, 2000), profile, background)
    ela = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
    assert ela["eye_line_applied_shift_px"]["vertical"] == 0
    assert ela["eye_line_clamped_vertical"] is True
    assert ela["eye_line_clamp_reason"] != "not_clamped"


def test_v2_partial_headroom_clamps_to_maximum_legal_shift() -> None:
    """When the requested shift exceeds available headroom by
    some amount, applied origin clamps to the legal boundary
    (0 for the top edge). Records
    ``eye_line_clamped_vertical=True``.
    """
    # Studio profile: 3:4 aspect, eye_line 0.34. Input
    # 300x600 → k = min(300//3, 600//4) = min(100, 150) = 100 →
    # crop 300x400. Vertical legal range [0, 200]. Request:
    # source_center_y (300) - 0.34*400 (136) = 164. Legal, no
    # clamp. To force clamp, use a smaller input.
    #
    # Use 300x420 → k = min(300//3, 420//4) = min(100, 105) =
    # 100 → crop 300x400. Vertical legal range [0, 20]. Request:
    # source_center_y (210) - 0.34*400 (136) = 74. Since 74 > 20,
    # clamp to 20.
    profile, background = _profile_and_background("studio")
    ctx = _ctx_from_bytes(_rgba_png(300, 420), profile, background)
    ela = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
    assert ela["applied_crop_origin"]["top"] == 20  # legal_top_max
    assert ela["eye_line_clamped_vertical"] is True
    assert "vertical_requested_below_source" in ela["eye_line_clamp_reason"]


def test_v2_clamp_never_produces_negative_origin() -> None:
    """A clamped applied origin is always ≥ 0. Guards against a
    subtle sign bug where clamping to ``legal_top_min`` (which
    is 0) might produce a stale negative value elsewhere.
    """
    profile, background = _profile_and_background("conversation")
    for input_dims in [(200, 200), (500, 500), (1000, 1000), (1500, 2500)]:
        ctx = _ctx_from_bytes(_rgba_png(*input_dims), profile, background)
        details = CropStage().apply(ctx).execution.details
        box = details["crop_box"]
        assert box["left"] >= 0, f"negative left for {input_dims}: {box}"
        assert box["top"] >= 0, f"negative top for {input_dims}: {box}"


def test_v2_crop_never_exceeds_input_dimensions() -> None:
    """No matter what eye-line target the profile declares, the
    applied crop stays fully within the source image — proves
    the clamp discipline prevents ANY exposure of empty pixels.
    """
    profile, background = _profile_and_background("compact")
    for input_dims in [(200, 200), (300, 500), (900, 800), (2000, 1500)]:
        ctx = _ctx_from_bytes(_rgba_png(*input_dims), profile, background)
        details = CropStage().apply(ctx).execution.details
        box = details["crop_box"]
        assert box["left"] >= 0
        assert box["top"] >= 0
        assert box["right"] <= input_dims[0]
        assert box["bottom"] <= input_dims[1]


def test_v2_horizontal_target_is_0_5_across_all_profiles() -> None:
    """Every ratified profile declares
    ``position_from_left: 0.5`` — v2 records this factually.
    Horizontal clamp should never trip for a centered target
    when the crop's horizontal fit permits a symmetric window.
    """
    for pid in RATIFIED_PROFILE_IDS:
        profile, background = _profile_and_background(pid)
        ctx = _ctx_from_bytes(_rgba_png(2000, 2000), profile, background)
        ela = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
        assert ela["eye_line_target_from_left"] == 0.5
        assert ela["eye_line_clamped_horizontal"] is False


def test_v2_eye_line_evidence_has_no_detection_claim() -> None:
    """Same language discipline as v1: no face/subject/eye/
    landmark detection claims in the eye-line evidence.
    """
    profile, background = _profile_and_background("presence")
    ctx = _ctx_from_bytes(_rgba_png(1500, 2500), profile, background)
    ela = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
    blob = repr(ela).lower()
    for forbidden in _FORBIDDEN_SUBSTRINGS:
        assert forbidden not in blob, (
            f"forbidden claim {forbidden!r} in v2 eye-line evidence: {ela}"
        )


def test_v2_manifest_records_legal_ranges_for_debug() -> None:
    """Evidence includes both requested and legal ranges so a
    debugger can see WHY a clamp fired without reproducing the
    input dimensions locally.
    """
    profile, background = _profile_and_background("presence")
    ctx = _ctx_from_bytes(_rgba_png(1500, 2500), profile, background)
    ela = CropStage().apply(ctx).execution.details["eye_line_adjustments"]
    assert "legal_top_range" in ela
    assert "legal_left_range" in ela
    assert ela["legal_top_range"][0] == 0
    assert ela["legal_left_range"][0] == 0


# ---- Regex safety for language check -----------------------------


def test_forbidden_substrings_pattern_actually_matches_a_hostile_string() -> None:
    """Self-check: the forbidden-substring list catches naive
    drift ("face_detected: true", "subject_bbox: [12, 34, ...]")
    that a future stage might accidentally introduce. Also
    proves the list does NOT collide with v1's permitted
    ``subject_detection_method: 'none'`` disavowal.
    """
    hostile = "we now have face_detected=true, subject_bbox=[10,20,30,40]"
    assert any(sub in hostile for sub in _FORBIDDEN_SUBSTRINGS)
    # v1's honest disavowal string is NOT hostile.
    benign = "deterministic_center_aspect_crop / subject_detection_method: none"
    assert not any(sub in benign for sub in _FORBIDDEN_SUBSTRINGS), (
        f"forbidden list matches v1's honest disavowal: "
        f"{[s for s in _FORBIDDEN_SUBSTRINGS if s in benign]}"
    )


# ---- Diagnostic regex demo (kept for readability) ----------------


def test_regex_helper_evidence_ready_for_review() -> None:
    """CropStage(v2) records
    ``crop_method="deterministic_center_proxy_eye_line_crop"``
    verbatim so a manifest reader can grep for it. CropStage(v1)
    used ``"deterministic_center_aspect_crop"``; the identifier
    change is deliberate and audit-visible.
    """
    profile, background = _profile_and_background("presence")
    ctx = _ctx_from_bytes(_rgba_png(1024, 1024), profile, background)
    details = CropStage().apply(ctx).execution.details
    assert re.fullmatch(
        r"deterministic_center_proxy_eye_line_crop",
        details["crop_method"],
    )
