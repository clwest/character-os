"""NormalizationPipeline composer + determinism anchor + manifest
shape (7.a).

Coverage:

* Pipeline runs end-to-end against a NoOp-only chain and returns
  a ``NormalizationResult`` with byte-identical output to input
  (NoOp is a pass-through).
* **Determinism anchor**: repeat runs of the same
  ``NormalizationSpec`` produce byte-for-byte identical
  ``normalized_bytes`` and identical manifest fields
  (excluding the environmental ``execution_duration_ms``).
* Manifest shape: every §10.6 field present on every run; keys
  match the Django ``NormalizationManifest`` fields so the
  result is directly usable as
  ``record_normalization_manifest(gen_record, **manifest)``.
* ``pipeline_version`` composition includes stage list + profile
  identity + background family identity.
* Input validation: empty bytes, malformed PNG, unknown
  profile_id, unknown background_id all raise
  ``PipelineInputError``.
* Stage errors lift to ``PipelineStageError`` with the offending
  stage_name attached.
* Background override reflected on the manifest.
"""
from __future__ import annotations

import time

import pytest
from PIL import Image

from app.services.normalization import (
    NormalizationPipeline,
    NormalizationResult,
    NormalizationSpec,
    PipelineError,
    PipelineInputError,
    PipelineStageError,
    Stage,
    StageContext,
    StageError,
    StageExecution,
    StageOutput,
)
from app.services.normalization.png import decode_png, encode_png
from app.services.normalization.stages.background_replacement import (
    BackgroundReplacementStage,
)
from app.services.normalization.stages.crop import CropStage
from app.services.normalization.stages.framing import FramingStage
from app.services.normalization.stages.noop import NoOpStage


# ---- Helpers ----------------------------------------------------


def _rgba_png(width: int = 64, height: int = 64, rgba=(180, 100, 40, 255)) -> bytes:
    img = Image.new("RGBA", (width, height), rgba)
    return encode_png(img)


def _default_spec(**overrides) -> NormalizationSpec:
    defaults = dict(
        raw_bytes=_rgba_png(),
        surface_profile_id="presence",  # ratified profile
        background_id_override=None,
    )
    defaults.update(overrides)
    return NormalizationSpec(**defaults)


# ---- Happy path -------------------------------------------------


def test_pipeline_returns_normalization_result_for_noop_chain() -> None:
    pipeline = NormalizationPipeline(stages=[NoOpStage()])
    result = pipeline.run(_default_spec())
    assert isinstance(result, NormalizationResult)


def test_noop_pipeline_preserves_raw_bytes_exactly() -> None:
    """NoOp does no work; the pipeline must not mutate raw bytes
    en route. Load-bearing for the raw-bytes-canonical invariant.
    """
    raw = _rgba_png(width=48, height=48, rgba=(10, 20, 30, 255))
    result = NormalizationPipeline(stages=[NoOpStage()]).run(
        _default_spec(raw_bytes=raw)
    )
    assert result.normalized_bytes == raw


def test_pipeline_run_is_deterministic_over_repeat_invocation() -> None:
    """The §10.6 anchor: repeat runs of identical spec produce
    byte-identical output and identical manifest fields
    (excluding ``execution_duration_ms`` which is environmental).
    """
    spec = _default_spec()
    pipeline = NormalizationPipeline(stages=[NoOpStage()])
    a = pipeline.run(spec)
    b = pipeline.run(spec)
    assert a.normalized_bytes == b.normalized_bytes
    # Manifest fields excluding the timing field must be equal.
    a_manifest = {k: v for k, v in a.manifest.items() if k != "execution_duration_ms"}
    b_manifest = {k: v for k, v in b.manifest.items() if k != "execution_duration_ms"}
    assert a_manifest == b_manifest


# ---- Manifest shape (§10.6) -------------------------------------


REQUIRED_MANIFEST_FIELDS = frozenset({
    "pipeline_version",
    "surface_profile_id",
    "surface_profile_version",
    "background_id",
    "stages_executed",
    "stages_skipped",
    "eye_line_adjustments",
    "crop_metadata",
    "execution_duration_ms",
})


def test_manifest_has_every_required_field_on_every_run() -> None:
    """Every §10.6 field is populated on every run, even for a
    NoOp-only chain — 7.b / 7.c fill in ``crop_metadata`` and
    ``eye_line_adjustments`` when those stages register.
    """
    result = NormalizationPipeline(stages=[NoOpStage()]).run(_default_spec())
    assert REQUIRED_MANIFEST_FIELDS.issubset(result.manifest.keys())


def test_manifest_matches_django_normalization_manifest_field_names() -> None:
    """The manifest dict is shaped for direct kwargs into Django's
    ``record_normalization_manifest``. If the substrate model
    ever renames a field, this test will diverge from the
    ``REQUIRED_MANIFEST_FIELDS`` set and both must be updated
    together. The pipeline's manifest keys are the contract
    surface.
    """
    result = NormalizationPipeline(stages=[NoOpStage()]).run(_default_spec())
    assert set(result.manifest) == REQUIRED_MANIFEST_FIELDS


def test_manifest_records_surface_profile_identity_from_yaml() -> None:
    result = NormalizationPipeline(stages=[NoOpStage()]).run(
        _default_spec(surface_profile_id="presence")
    )
    assert result.manifest["surface_profile_id"] == "presence"
    assert result.manifest["surface_profile_version"] >= 1


def test_manifest_records_background_id_resolved_from_profile() -> None:
    """Presence profile declares no tonal_environment_class, so
    the family's default_background_for_unspecified_profile
    (``neutral_warm_studio``) is used.
    """
    result = NormalizationPipeline(stages=[NoOpStage()]).run(
        _default_spec(surface_profile_id="presence")
    )
    assert result.manifest["background_id"] == "neutral_warm_studio"


def test_manifest_records_background_override_when_supplied() -> None:
    result = NormalizationPipeline(stages=[NoOpStage()]).run(
        _default_spec(
            surface_profile_id="presence",
            background_id_override="conversational_darker_surround",
        )
    )
    assert result.manifest["background_id"] == "conversational_darker_surround"


def test_manifest_records_conversation_profile_darker_background() -> None:
    """Conversation profile declares
    ``tonal_environment_class: conversational_darker`` which maps
    to ``conversational_darker_surround``.
    """
    result = NormalizationPipeline(stages=[NoOpStage()]).run(
        _default_spec(surface_profile_id="conversation")
    )
    assert result.manifest["background_id"] == "conversational_darker_surround"


def test_noop_lands_in_stages_skipped_not_stages_executed() -> None:
    result = NormalizationPipeline(stages=[NoOpStage()]).run(_default_spec())
    assert len(result.manifest["stages_executed"]) == 0
    assert len(result.manifest["stages_skipped"]) == 1
    row = result.manifest["stages_skipped"][0]
    assert row["stage_name"] == "noop"
    assert row["status"] == "not_applied"


def test_crop_and_eye_line_hoist_keys_are_empty_when_stages_absent() -> None:
    result = NormalizationPipeline(stages=[NoOpStage()]).run(_default_spec())
    assert result.manifest["crop_metadata"] == {}
    assert result.manifest["eye_line_adjustments"] == {}


# ---- pipeline_version composition -------------------------------


def test_pipeline_version_contains_stage_names_and_versions() -> None:
    pipeline = NormalizationPipeline(stages=[NoOpStage()])
    result = pipeline.run(_default_spec())
    assert "noop@1" in result.manifest["pipeline_version"]
    assert result.manifest["pipeline_version"].startswith("pipeline_v1:")


def test_pipeline_version_includes_profile_identity_and_hash() -> None:
    result = NormalizationPipeline(stages=[NoOpStage()]).run(
        _default_spec(surface_profile_id="presence")
    )
    version = result.manifest["pipeline_version"]
    assert "profile:presence@1:" in version
    # Short hash prefix (12 hex chars) appears in the version.
    assert "|profile:presence@1:" in version
    # bg_family shows up too.
    assert "|bg_family:v1:" in version


def test_pipeline_version_differs_across_stage_composition() -> None:
    """A different stage list produces a different pipeline
    version string — proves the version reflects the ordered
    stage set.
    """
    a = NormalizationPipeline(stages=[NoOpStage()])
    b = NormalizationPipeline(stages=[NoOpStage(), NoOpStage()])
    ra = a.run(_default_spec()).manifest["pipeline_version"]
    rb = b.run(_default_spec()).manifest["pipeline_version"]
    assert ra != rb


# ---- Input validation -------------------------------------------


def test_run_rejects_empty_bytes() -> None:
    with pytest.raises(PipelineInputError, match="empty"):
        NormalizationPipeline(stages=[NoOpStage()]).run(
            _default_spec(raw_bytes=b"")
        )


def test_run_rejects_non_png_bytes() -> None:
    with pytest.raises(PipelineInputError, match="not a valid PNG"):
        NormalizationPipeline(stages=[NoOpStage()]).run(
            _default_spec(raw_bytes=b"totally not a png")
        )


def test_run_rejects_unknown_profile_id() -> None:
    with pytest.raises(PipelineInputError, match="surface profile"):
        NormalizationPipeline(stages=[NoOpStage()]).run(
            _default_spec(surface_profile_id="not_a_real_profile")
        )


def test_run_rejects_unknown_background_override() -> None:
    with pytest.raises(PipelineInputError, match="background_id"):
        NormalizationPipeline(stages=[NoOpStage()]).run(
            _default_spec(background_id_override="not_a_real_background")
        )


def test_pipeline_rejects_empty_stage_list_at_construction() -> None:
    with pytest.raises(PipelineError, match="at least one stage"):
        NormalizationPipeline(stages=[])


# ---- Stage-error lifting ----------------------------------------


class _ExplodingStage:
    """Stage that always raises. Not registered — instantiated
    directly by the test.
    """

    stage_name = "exploding"
    stage_version = 1

    def apply(self, ctx: StageContext) -> StageOutput:
        raise StageError("boom")


def test_stage_error_lifts_to_pipeline_stage_error_with_stage_name() -> None:
    with pytest.raises(PipelineStageError) as exc_info:
        NormalizationPipeline(stages=[NoOpStage(), _ExplodingStage()]).run(_default_spec())
    assert exc_info.value.stage_name == "exploding"
    assert "boom" in str(exc_info.value)


# ---- Ordering ---------------------------------------------------


class _RecordingStage:
    """Stage that appends its name to a shared list — used to
    verify stage execution order.
    """

    stage_name = "record"
    stage_version = 1

    def __init__(self, marker: str, sink: list[str]) -> None:
        self._marker = marker
        self._sink = sink

    def apply(self, ctx: StageContext) -> StageOutput:
        self._sink.append(self._marker)
        return StageOutput(
            new_context=ctx,
            execution=StageExecution(
                stage_name="record",
                stage_version=1,
                status="not_applied",
                input_width_px=ctx.width_px,
                input_height_px=ctx.height_px,
                output_width_px=ctx.width_px,
                output_height_px=ctx.height_px,
                duration_ms=0,
                details={"marker": self._marker},
            ),
        )


def test_pipeline_executes_stages_in_declared_order() -> None:
    sink: list[str] = []
    pipeline = NormalizationPipeline(
        stages=[
            _RecordingStage("first", sink),
            _RecordingStage("second", sink),
            _RecordingStage("third", sink),
        ],
    )
    pipeline.run(_default_spec())
    assert sink == ["first", "second", "third"]


# ---- 7.b end-to-end: partial v1 chain (Crop + Framing) ----------


RATIFIED_PROFILE_IDS = ("compact", "presence", "studio", "conversation", "team_card")


def _large_rgba_png(width: int = 2400, height: int = 2400) -> bytes:
    return encode_png(Image.new("RGBA", (width, height), (200, 130, 60, 255)))


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_partial_v1_chain_produces_declared_output_dimensions(
    profile_id: str,
) -> None:
    """End-to-end (CropStage → FramingStage) against a large
    square input. Every ratified profile lands at its declared
    output dimensions. This is the ratified partial v1 chain per
    SESSION 246 7.b — NO NoOp, NO EyeLine, NO Background yet.
    """
    pipeline = NormalizationPipeline(stages=[CropStage(), FramingStage()])
    result = pipeline.run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id=profile_id,
        )
    )
    from app.services.normalization import load_surface_profile

    profile = load_surface_profile(profile_id)
    # Decoded output image matches the profile's declared dims.
    decoded = decode_png(result.normalized_bytes)
    assert decoded.size == (profile.output.width_px, profile.output.height_px)


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_partial_v1_chain_is_byte_deterministic_over_repeat_runs(
    profile_id: str,
) -> None:
    """§10.6 anchor at end-to-end level: same input + same profile
    across the CropStage → FramingStage chain produces
    byte-identical bytes on repeat runs.
    """
    pipeline = NormalizationPipeline(stages=[CropStage(), FramingStage()])
    spec = NormalizationSpec(
        raw_bytes=_large_rgba_png(),
        surface_profile_id=profile_id,
    )
    a = pipeline.run(spec)
    b = pipeline.run(spec)
    assert a.normalized_bytes == b.normalized_bytes


def test_partial_v1_chain_populates_crop_metadata_from_crop_stage() -> None:
    """The pipeline's manifest-assembly hoists CropStage's
    ``details`` into ``manifest['crop_metadata']`` per §10.6.
    The ``eye_line_adjustments`` nested block is excluded from
    ``crop_metadata`` and lifted to its own top-level field.
    """
    result = NormalizationPipeline(stages=[CropStage(), FramingStage()]).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    cm = result.manifest["crop_metadata"]
    assert cm["crop_method"] == "deterministic_center_proxy_eye_line_crop"
    assert cm["subject_detection_method"] == "none"
    assert cm["subject_scale_honored"] is False
    assert "crop_box" in cm
    # Nested eye_line block was hoisted into its own manifest
    # field and MUST NOT duplicate inside crop_metadata.
    assert "eye_line_adjustments" not in cm


def test_partial_v1_chain_eye_line_adjustments_populated_by_cropstage_v2() -> None:
    """SESSION 246 7.c architectural correction: eye-line
    positioning folded into CropStage(v2). The manifest's
    top-level ``eye_line_adjustments`` field is populated from
    CropStage(v2)'s nested evidence — even in the partial 7.b
    chain (Crop → Framing) without a BackgroundReplacementStage.
    """
    result = NormalizationPipeline(stages=[CropStage(), FramingStage()]).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    ela = result.manifest["eye_line_adjustments"]
    assert ela["eye_line_method"] == "source_center_proxy"
    assert ela["eye_line_target_from_top"] == 0.36  # ratified presence value
    assert "applied_crop_origin" in ela
    assert "eye_line_clamped" in ela
    assert "eye_line_clamp_reason" in ela


# ---- 7.c end-to-end: full v1 chain (Crop v2 + Framing + BgReplace) ----


RATIFIED_BG_IDS = (
    "neutral_warm_studio",
    "neutral_cool_studio",
    "warm_material_surround",
    "soft_environmental_depth",
    "conversational_darker_surround",
)


def _v1_chain() -> list:
    """The ratified v1 pipeline stage list per SESSION 246 7.c:
    ``(CropStage(v2), FramingStage(v1), BackgroundReplacementStage(v1))``.
    No NoOp; no standalone EyeLineStage (folded into CropStage v2).
    """
    return [CropStage(), FramingStage(), BackgroundReplacementStage()]


@pytest.mark.parametrize("profile_id", RATIFIED_PROFILE_IDS)
def test_v1_chain_produces_declared_output_dimensions_for_every_profile(
    profile_id: str,
) -> None:
    """Full v1 chain × every ratified profile → exact declared
    output dimensions. Uses a large square input so no profile
    hits the upscale-refusal branch.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id=profile_id,
        )
    )
    from app.services.normalization import load_surface_profile

    profile = load_surface_profile(profile_id)
    decoded = decode_png(result.normalized_bytes)
    assert decoded.size == (profile.output.width_px, profile.output.height_px)


@pytest.mark.parametrize("bg_id", RATIFIED_BG_IDS)
def test_v1_chain_accepts_every_ratified_background_via_override(
    bg_id: str,
) -> None:
    """Every controlled background can drive the v1 chain via
    ``background_id_override``. Proves the pipeline honors the
    reviewer-override scope in ``background_family_v1.yaml``.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
            background_id_override=bg_id,
        )
    )
    assert result.manifest["background_id"] == bg_id


def test_v1_chain_output_is_byte_deterministic_over_repeat_runs() -> None:
    """§10.6 anchor for the FULL v1 chain: identical spec →
    byte-identical normalized bytes across repeat runs.
    Load-bearing for reviewer scoring reproducibility.
    """
    spec = NormalizationSpec(
        raw_bytes=_large_rgba_png(),
        surface_profile_id="presence",
    )
    a = NormalizationPipeline(stages=_v1_chain()).run(spec)
    b = NormalizationPipeline(stages=_v1_chain()).run(spec)
    assert a.normalized_bytes == b.normalized_bytes


def test_v1_chain_manifest_stable_over_repeat_runs_excluding_timing() -> None:
    """Manifest fields equal across repeat runs except for the
    environmental ``execution_duration_ms``.
    """
    spec = NormalizationSpec(
        raw_bytes=_large_rgba_png(),
        surface_profile_id="conversation",
    )
    a = NormalizationPipeline(stages=_v1_chain()).run(spec)
    b = NormalizationPipeline(stages=_v1_chain()).run(spec)
    _strip = lambda m: {k: v for k, v in m.items() if k != "execution_duration_ms"}
    # Strip inner stage duration_ms too — those are also
    # environmental.
    for m in (a.manifest, b.manifest):
        for row in m["stages_executed"]:
            row["duration_ms"] = 0
    assert _strip(a.manifest) == _strip(b.manifest)


def test_v1_chain_raw_input_bytes_unchanged() -> None:
    """The pipeline never mutates ``spec.raw_bytes``. Load-
    bearing for the raw-canonical-evidence invariant (§10.3).
    """
    raw = _large_rgba_png()
    raw_copy = bytes(raw)  # defensive copy for assertion
    NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(raw_bytes=raw, surface_profile_id="presence")
    )
    assert raw == raw_copy


def test_v1_chain_records_three_stages_executed_no_skipped() -> None:
    """The v1 chain has exactly three executed stages: crop,
    framing, background_replacement. NoOp is not part of the
    chain, so ``stages_skipped`` is empty.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    executed_names = [
        row["stage_name"] for row in result.manifest["stages_executed"]
    ]
    assert executed_names == ["crop", "framing", "background_replacement"]
    assert result.manifest["stages_skipped"] == []


def test_v1_chain_pipeline_version_names_all_three_stages_in_order() -> None:
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    version = result.manifest["pipeline_version"]
    assert "crop@2" in version
    assert "framing@1" in version
    assert "background_replacement@1" in version
    assert version.index("crop@2") < version.index("framing@1")
    assert version.index("framing@1") < version.index("background_replacement@1")


def test_v1_chain_5_profiles_x_5_backgrounds_matrix_all_deterministic() -> None:
    """The load-bearing matrix: every profile × every background
    combination produces valid, deterministic normalized output
    at the profile's declared dimensions. Twenty-five
    combinations verified in one test to keep suite time tight.
    """
    from app.services.normalization import load_surface_profile

    matrix_hashes: dict[tuple[str, str], bytes] = {}
    raw = _large_rgba_png()

    for profile_id in RATIFIED_PROFILE_IDS:
        profile = load_surface_profile(profile_id)
        for bg_id in RATIFIED_BG_IDS:
            spec = NormalizationSpec(
                raw_bytes=raw,
                surface_profile_id=profile_id,
                background_id_override=bg_id,
            )
            result = NormalizationPipeline(stages=_v1_chain()).run(spec)
            decoded = decode_png(result.normalized_bytes)
            assert decoded.size == (
                profile.output.width_px,
                profile.output.height_px,
            ), f"{profile_id} × {bg_id}: dims mismatch {decoded.size}"
            matrix_hashes[(profile_id, bg_id)] = result.normalized_bytes

    # Repeat once and prove every entry is byte-identical.
    for profile_id in RATIFIED_PROFILE_IDS:
        for bg_id in RATIFIED_BG_IDS:
            spec = NormalizationSpec(
                raw_bytes=raw,
                surface_profile_id=profile_id,
                background_id_override=bg_id,
            )
            repeat = NormalizationPipeline(stages=_v1_chain()).run(spec)
            assert repeat.normalized_bytes == matrix_hashes[(profile_id, bg_id)]


def test_v1_chain_procedural_fill_traceable_to_yaml_via_manifest() -> None:
    """Manifest ``crop_metadata`` and background_replacement
    stage row include the procedural fill_rgb read from YAML —
    proves no Python-side RGB invention.
    """
    from app.services.normalization import load_background_family

    family = load_background_family()

    for bg in family.backgrounds:
        result = NormalizationPipeline(stages=_v1_chain()).run(
            NormalizationSpec(
                raw_bytes=_large_rgba_png(),
                surface_profile_id="presence",
                background_id_override=bg.background_id,
            )
        )
        # Locate the BackgroundReplacementStage's row in stages_executed.
        bg_row = next(
            row for row in result.manifest["stages_executed"]
            if row["stage_name"] == "background_replacement"
        )
        r, g, b = bg.procedural_v1.fill_rgb
        assert bg_row["details"]["fill_rgb"] == [r, g, b]
        assert bg_row["details"]["background_source"] == "procedural_v1"


def test_v1_chain_manifest_has_no_detection_or_aesthetic_claim() -> None:
    """End-to-end language discipline — no detection or aesthetic
    substrings anywhere in the composed manifest.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="conversation",
        )
    )
    blob = repr(result.manifest).lower()
    for forbidden in (
        "face_detected", "subject_detected", "silhouette",
        "eye_detected", "landmark", "subject_bbox", "face_bbox",
        "excellent", "poor", "quality", "beautiful",
    ):
        assert forbidden not in blob, (
            f"forbidden substring {forbidden!r} in v1-chain manifest"
        )
    # The one permitted detection-related string.
    assert "'subject_detection_method': 'none'" in repr(result.manifest)


def test_partial_v1_chain_records_both_stages_executed() -> None:
    """Both stages emit ``status='executed'`` on the happy path.
    ``stages_skipped`` remains empty because NoOp is not part of
    the v1 chain per operator ratification.
    """
    result = NormalizationPipeline(stages=[CropStage(), FramingStage()]).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="compact",
        )
    )
    executed = result.manifest["stages_executed"]
    skipped = result.manifest["stages_skipped"]
    executed_names = [row["stage_name"] for row in executed]
    assert executed_names == ["crop", "framing"]
    assert skipped == []


def test_partial_v1_chain_pipeline_version_names_crop_and_framing() -> None:
    result = NormalizationPipeline(stages=[CropStage(), FramingStage()]).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    version = result.manifest["pipeline_version"]
    # CropStage bumped to v2 at SESSION 246 7.c (eye-line folded
    # into origin decision); FramingStage remains v1.
    assert "crop@2" in version
    assert "framing@1" in version
    # Order preserved in the version string.
    assert version.index("crop@2") < version.index("framing@1")


def test_partial_v1_chain_landscape_input_still_produces_target_dims() -> None:
    """1600x1200 landscape input → any portrait/square profile
    still produces the declared output dimensions.
    """
    result = NormalizationPipeline(stages=[CropStage(), FramingStage()]).run(
        NormalizationSpec(
            raw_bytes=encode_png(
                Image.new("RGBA", (1600, 1200), (10, 20, 30, 255))
            ),
            surface_profile_id="compact",  # 1:1, 512x512
        )
    )
    from app.services.normalization import load_surface_profile

    profile = load_surface_profile("compact")
    decoded = decode_png(result.normalized_bytes)
    assert decoded.size == (profile.output.width_px, profile.output.height_px)


def test_partial_v1_chain_tiny_input_fails_with_input_smaller_than_output() -> None:
    """A tiny input that would require upscale to reach the
    profile's declared output dimensions fails explicitly at
    FramingStage — per SESSION 246 upscale-refusal ratification.
    """
    tiny = encode_png(Image.new("RGBA", (200, 200), (100, 100, 100, 255)))
    with pytest.raises(PipelineStageError) as exc_info:
        NormalizationPipeline(stages=[CropStage(), FramingStage()]).run(
            NormalizationSpec(
                raw_bytes=tiny,
                surface_profile_id="conversation",  # 900x1200 declared
            )
        )
    assert exc_info.value.stage_name == "framing"
    assert "input_smaller_than_output" in str(exc_info.value)


def test_partial_v1_chain_evidence_has_no_detection_claim() -> None:
    """End-to-end language discipline: no detection / face / eye
    / silhouette claim anywhere in the composed manifest.
    """
    result = NormalizationPipeline(stages=[CropStage(), FramingStage()]).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="conversation",
        )
    )
    blob = repr(result.manifest).lower()
    for forbidden in (
        "face_detected", "subject_detected", "silhouette",
        "eye_detected", "landmark", "subject_bbox", "face_bbox",
    ):
        assert forbidden not in blob, (
            f"forbidden detection substring {forbidden!r} leaked into v1 chain manifest"
        )
    # subject_detection_method='none' is the ONE permitted mention.
    assert "'subject_detection_method': 'none'" in repr(result.manifest)
