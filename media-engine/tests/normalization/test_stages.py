"""Stage Protocol + NoOpStage contract tests (7.a).

Coverage:

* ``NoOpStage`` implements the ``Stage`` Protocol at runtime.
* NoOp preserves input bytes byte-for-byte (raw preservation
  is a load-bearing pipeline invariant even for pass-through
  stages).
* NoOp records ``status='not_applied'`` — factual, not
  aesthetic — with dimensions matching input and a factual
  ``reason`` in ``details``.
* Registry ``get_stage`` returns a NoOp instance for the
  ``noop`` name and raises loudly for unknown names.
* ``StageContext`` is frozen (attempting mutation raises).
"""
from __future__ import annotations

import dataclasses

import pytest

from app.services.normalization import (
    Background,
    NormalizationConfigError,
    Stage,
    StageContext,
    StageError,
    StageOutput,
    SurfaceProfile,
    SurfaceProfileCrop,
    SurfaceProfileEyeLine,
    SurfaceProfileFramingBehavior,
    SurfaceProfileMargins,
    SurfaceProfileOutput,
    get_stage,
)
from app.services.normalization.stages.noop import NoOpStage


# ---- Fixtures ---------------------------------------------------


def _fake_profile() -> SurfaceProfile:
    return SurfaceProfile(
        profile_id="test",
        version=1,
        framing_family="fam",
        crop=SurfaceProfileCrop(aspect_ratio="1:1", strategy="subject_relative", subject_scale=1.0),
        eye_line=SurfaceProfileEyeLine(position_from_top=0.5, position_from_left=0.5),
        margins=SurfaceProfileMargins(min_edge_padding=0.05),
        output=SurfaceProfileOutput(width_px=256, height_px=256, format="png", color_space="sRGB"),
        framing_behavior=SurfaceProfileFramingBehavior(includes=("face",), excludes=()),
        tonal_environment_class=None,
        schema_hash="0" * 64,
    )


def _fake_background() -> Background:
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


def _seed_ctx(raw: bytes = b"input-bytes", width: int = 320, height: int = 240) -> StageContext:
    return StageContext(
        image_bytes=raw,
        width_px=width,
        height_px=height,
        surface_profile=_fake_profile(),
        background=_fake_background(),
    )


# ---- NoOpStage --------------------------------------------------


def test_noop_is_a_stage_instance() -> None:
    """Runtime-checkable Protocol verifies NoOp satisfies the
    contract without a static type check.
    """
    assert isinstance(NoOpStage(), Stage)


def test_noop_stage_name_and_version_are_class_level() -> None:
    """``pipeline_version`` enumerates stages without
    instantiating; class-level constants preserve that path.
    """
    assert NoOpStage.stage_name == "noop"
    assert NoOpStage.stage_version == 1


def test_noop_preserves_bytes_and_dimensions() -> None:
    ctx = _seed_ctx(raw=b"deterministic-input", width=320, height=240)
    output = NoOpStage().apply(ctx)
    assert isinstance(output, StageOutput)
    assert output.new_context.image_bytes == b"deterministic-input"
    assert output.new_context.width_px == 320
    assert output.new_context.height_px == 240


def test_noop_records_status_not_applied_with_factual_reason() -> None:
    ctx = _seed_ctx()
    execution = NoOpStage().apply(ctx).execution
    assert execution.stage_name == "noop"
    assert execution.stage_version == 1
    assert execution.status == "not_applied"
    assert execution.input_width_px == ctx.width_px
    assert execution.input_height_px == ctx.height_px
    assert execution.output_width_px == ctx.width_px
    assert execution.output_height_px == ctx.height_px
    assert "reason" in execution.details
    # Factual language — no quality judgment.
    for forbidden in ("excellent", "poor", "good", "bad", "quality", "beautiful"):
        assert forbidden not in execution.details["reason"].lower()


def test_noop_context_object_is_a_fresh_instance() -> None:
    """NoOp's frozen-context return contract: even for a
    pass-through, a fresh ``StageContext`` is returned so future
    stages can never rely on identity comparison as a
    same-context signal.
    """
    ctx = _seed_ctx()
    output = NoOpStage().apply(ctx)
    assert output.new_context is not ctx
    assert output.new_context == ctx  # equal by value


def test_stage_context_is_frozen() -> None:
    ctx = _seed_ctx()
    with pytest.raises(dataclasses.FrozenInstanceError):
        ctx.width_px = 999  # type: ignore[misc]


# ---- Registry ---------------------------------------------------


def test_get_stage_returns_noop_instance_for_registered_name() -> None:
    stage = get_stage("noop")
    assert isinstance(stage, NoOpStage)


def test_get_stage_unknown_name_raises() -> None:
    with pytest.raises(StageError, match="unknown stage"):
        get_stage("not_a_real_stage")


def test_get_stage_empty_name_raises() -> None:
    with pytest.raises(StageError):
        get_stage("")
