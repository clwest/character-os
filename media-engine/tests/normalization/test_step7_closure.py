"""Step 7 closure — cross-stage invariants pinned before SHIPPED.

This module answers the SESSION 246 closure question:

    Is normalization now a deterministic, provider-independent
    transformation from raw portrait bytes + declarative surface
    /background configuration into normalized bytes +
    reproducible factual evidence?

with **executable invariants** rather than architecture prose.
Every operator-ratified closure invariant from SESSION 246 item
5 maps to one test here. Anything a future refactor might
weaken silently trips this file first.

Not duplicative with per-stage tests: those verify each stage's
internal behavior; this file pins the **default v1 production
chain** as a whole and the boundaries around it.
"""
from __future__ import annotations

import pytest
from PIL import Image

from app.services.normalization import (
    NormalizationPipeline,
    NormalizationSpec,
    PipelineInputError,
    PipelineStageError,
    load_background_family,
    load_surface_profile,
)
from app.services.normalization.png import decode_png, encode_png
from app.services.normalization.stages import _registered_stage_names, get_stage
from app.services.normalization.stages.background_replacement import (
    BackgroundReplacementStage,
)
from app.services.normalization.stages.crop import CropStage
from app.services.normalization.stages.framing import FramingStage
from app.services.normalization.stages.noop import NoOpStage


RATIFIED_PROFILE_IDS = ("compact", "presence", "studio", "conversation", "team_card")
RATIFIED_BG_IDS = (
    "neutral_warm_studio",
    "neutral_cool_studio",
    "warm_material_surround",
    "soft_environmental_depth",
    "conversational_darker_surround",
)


def _v1_chain() -> list:
    """The ratified default v1 chain per SESSION 246 7.c close.
    Kept as one function so if the chain ever changes, every
    closure invariant test picks up the new composition.
    """
    return [CropStage(), FramingStage(), BackgroundReplacementStage()]


def _large_rgba_png() -> bytes:
    return encode_png(Image.new("RGBA", (2400, 2400), (200, 130, 60, 255)))


# ---- Chain composition invariants -------------------------------


def test_default_v1_chain_is_exactly_crop_framing_background_in_order() -> None:
    """The default v1 chain contains exactly three stages, in
    the ratified order.
    """
    chain = _v1_chain()
    names = [s.stage_name for s in chain]
    assert names == ["crop", "framing", "background_replacement"]
    versions = [s.stage_version for s in chain]
    assert versions == [2, 1, 1]


def test_noop_stage_is_registered_but_not_in_default_v1_chain() -> None:
    """NoOp remains available as a harness exerciser (via
    ``get_stage('noop')``) but MUST NOT appear in the default
    production chain — SESSION 246 discipline: "Do not let
    NoOp survive accidentally."
    """
    assert "noop" in _registered_stage_names()
    default_names = {s.stage_name for s in _v1_chain()}
    assert "noop" not in default_names
    # And NoOp itself is not somehow silently one of the chain's
    # concrete classes.
    for stage in _v1_chain():
        assert not isinstance(stage, NoOpStage)


def test_no_standalone_eye_line_stage_registered() -> None:
    """Per SESSION 246 7.c architectural correction: eye-line
    positioning is folded into CropStage(v2). There must be no
    standalone ``eye_line`` stage — its presence would either
    duplicate CropStage's evidence or reintroduce the
    zero-headroom decorative-stage anti-pattern this session
    corrected.
    """
    assert "eye_line" not in _registered_stage_names()


@pytest.mark.parametrize("name", ("crop", "framing", "background_replacement"))
def test_every_production_stage_has_stable_name_and_version(name: str) -> None:
    """Every stage in the v1 chain exposes ``stage_name`` +
    ``stage_version`` as class-level constants so
    ``pipeline_version`` composition can enumerate them without
    instantiating.
    """
    stage = get_stage(name)
    cls = type(stage)
    assert isinstance(cls.stage_name, str) and cls.stage_name == name
    assert isinstance(cls.stage_version, int) and cls.stage_version >= 1


# ---- pipeline_version reactivity --------------------------------


def test_pipeline_version_changes_when_stage_order_changes() -> None:
    """A different stage order produces a different
    pipeline_version — proves the composition string reflects
    the ordered stage set, not just the stage set.
    """
    a = NormalizationPipeline(stages=[CropStage(), FramingStage()])
    b = NormalizationPipeline(stages=[FramingStage(), CropStage()])
    spec = NormalizationSpec(
        raw_bytes=_large_rgba_png(),
        surface_profile_id="presence",
    )
    va = a.pipeline_version(load_surface_profile("presence"), load_background_family())
    vb = b.pipeline_version(load_surface_profile("presence"), load_background_family())
    assert va != vb


def test_pipeline_version_includes_surface_profile_version_and_background_family_hash() -> None:
    """The manifest's ``pipeline_version`` records both the
    surface-profile version AND the background-family schema
    identity via short hash prefix — so a schema edit that
    forgets to bump ``version`` still leaves a signal.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    version = result.manifest["pipeline_version"]
    profile = load_surface_profile("presence")
    family = load_background_family()
    assert f"profile:presence@{profile.version}:" in version
    assert f":{profile.schema_hash[:12]}" in version
    assert f"bg_family:v{family.schema_version}:{family.schema_hash[:12]}" in version


# ---- §10.6 manifest completeness --------------------------------


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


def test_every_10_6_manifest_field_populated_or_explicitly_empty() -> None:
    """Every §10.6 field lands on every run — either populated
    with real evidence or with an explicit empty/not-computed
    representation. No field silently missing.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    assert set(result.manifest) == REQUIRED_MANIFEST_FIELDS
    # Every field has a value (dict / list / str / int); none are
    # None.
    for k, v in result.manifest.items():
        assert v is not None, f"manifest field {k!r} is None"


# ---- Stage evidence: factual-only ------------------------------


_FORBIDDEN_AESTHETIC = (
    "excellent", "poor", "quality", "beautiful", "attractive",
    "flattering", "pleasing", "ugly",
)

_FORBIDDEN_DETECTION = (
    "face_detected", "subject_detected", "silhouette",
    "eye_detected", "landmark", "subject_bbox", "face_bbox",
    "gaze_detected", "pupil_detected",
)


def test_composed_manifest_carries_no_aesthetic_or_detection_claim() -> None:
    """Full-chain manifest scanned for any forbidden aesthetic
    OR detection substring. Load-bearing language discipline
    for reviewer-facing evidence.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="conversation",
        )
    )
    blob = repr(result.manifest).lower()
    for forbidden in _FORBIDDEN_AESTHETIC + _FORBIDDEN_DETECTION:
        assert forbidden not in blob, (
            f"forbidden substring {forbidden!r} in composed v1-chain manifest"
        )


# ---- Raw-input preservation invariant --------------------------


def test_pipeline_never_mutates_raw_input_bytes() -> None:
    """The pipeline's raw-canonical-evidence invariant (§10.3):
    the spec's ``raw_bytes`` is byte-for-byte equal after
    ``run`` completes. Load-bearing for Step 8/10 evidence
    reproducibility.
    """
    raw = _large_rgba_png()
    original = bytes(raw)  # defensive copy for comparison
    NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(raw_bytes=raw, surface_profile_id="presence")
    )
    assert raw == original


# ---- Failure honesty ------------------------------------------


def test_unknown_surface_profile_fails_loudly_at_pipeline_boundary() -> None:
    with pytest.raises(PipelineInputError, match="surface profile"):
        NormalizationPipeline(stages=_v1_chain()).run(
            NormalizationSpec(
                raw_bytes=_large_rgba_png(),
                surface_profile_id="not_a_real_profile",
            )
        )


def test_unknown_background_id_fails_loudly_at_pipeline_boundary() -> None:
    with pytest.raises(PipelineInputError, match="background_id"):
        NormalizationPipeline(stages=_v1_chain()).run(
            NormalizationSpec(
                raw_bytes=_large_rgba_png(),
                surface_profile_id="presence",
                background_id_override="not_a_real_background",
            )
        )


def test_upscale_refusal_holds_end_to_end() -> None:
    """A tiny input that would require upscale to reach any
    ratified profile's declared dimensions raises
    ``input_smaller_than_output`` at FramingStage — never
    silently enlarged.
    """
    tiny = encode_png(Image.new("RGBA", (200, 200), (100, 100, 100, 255)))
    with pytest.raises(PipelineStageError) as exc_info:
        NormalizationPipeline(stages=_v1_chain()).run(
            NormalizationSpec(
                raw_bytes=tiny,
                surface_profile_id="conversation",
            )
        )
    assert exc_info.value.stage_name == "framing"
    assert "input_smaller_than_output" in str(exc_info.value)


def test_background_replacement_failure_does_not_silently_pass_through() -> None:
    """If BackgroundReplacementStage fails, the pipeline raises
    ``PipelineStageError`` — never returns the framed image
    while claiming background replacement executed.
    """
    from app.services.normalization import StageContext, StageError, StageOutput

    class _FailingBg:
        stage_name = "background_replacement"
        stage_version = 1

        def apply(self, ctx: StageContext) -> StageOutput:
            raise StageError("background_replacement_failed: simulated matte failure")

    with pytest.raises(PipelineStageError) as exc_info:
        NormalizationPipeline(
            stages=[CropStage(), FramingStage(), _FailingBg()],
        ).run(
            NormalizationSpec(
                raw_bytes=_large_rgba_png(),
                surface_profile_id="presence",
            )
        )
    assert exc_info.value.stage_name == "background_replacement"
    assert "simulated" in str(exc_info.value)


# ---- No padding / stretch / letterbox behavior -----------------


def test_composed_manifest_records_no_letterbox_padding_stretch() -> None:
    """FramingStage's factual False flags are visible in the
    composed manifest via the ``stages_executed`` row for
    framing. Proves an end-to-end reader can verify no padding
    without inspecting bytes.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    framing_row = next(
        row for row in result.manifest["stages_executed"]
        if row["stage_name"] == "framing"
    )
    d = framing_row["details"]
    assert d["upscale_applied"] is False
    assert d["letterboxing_applied"] is False
    assert d["pillarboxing_applied"] is False
    assert d["stretch_applied"] is False


# ---- rembg shared-cache invariant ------------------------------


def test_rembg_session_cache_is_shared_with_v16() -> None:
    """SESSION 246 7.c.a extraction produced ONE cache used by
    both V16 (video composite) and Step 7 (portrait
    normalization). The BackgroundReplacementStage MUST resolve
    the same session object V16 would resolve for the same
    model — proves the extraction did not fork the cache.
    """
    from app.routers.internal import _get_rembg_session as v16_get_session
    from app.services.rembg_session import get_rembg_session

    shared = get_rembg_session("u2net_human_seg")
    from_v16 = v16_get_session("u2net_human_seg")
    assert shared is from_v16


# ---- Determinism at closure level -----------------------------


def test_every_profile_x_background_yields_byte_identical_output_across_two_runs() -> None:
    """Closure-level determinism: 25 combinations (5 profiles ×
    5 backgrounds) all produce byte-identical output on repeat
    runs. Load-bearing for Step 8/10 reviewer scoring
    reproducibility.
    """
    from app.services.normalization import load_surface_profile

    raw = _large_rgba_png()
    for profile_id in RATIFIED_PROFILE_IDS:
        for bg_id in RATIFIED_BG_IDS:
            spec = NormalizationSpec(
                raw_bytes=raw,
                surface_profile_id=profile_id,
                background_id_override=bg_id,
            )
            a = NormalizationPipeline(stages=_v1_chain()).run(spec)
            b = NormalizationPipeline(stages=_v1_chain()).run(spec)
            assert a.normalized_bytes == b.normalized_bytes, (
                f"{profile_id} × {bg_id}: not byte-identical across runs"
            )
            # Also confirm output dimensions match the profile.
            profile = load_surface_profile(profile_id)
            decoded = decode_png(a.normalized_bytes)
            assert decoded.size == (
                profile.output.width_px, profile.output.height_px,
            )


# ---- Provider-independence invariant --------------------------


def test_pipeline_boundary_names_no_provider() -> None:
    """The normalization package must not import from any
    provider-specific module (portrait_provider, voice_provider,
    or any adapter). Enforced via AST scan so a future refactor
    that accidentally adds a provider import trips CI.
    """
    import ast
    import pathlib

    pkg_root = (
        pathlib.Path(__file__).resolve().parents[2]
        / "app"
        / "services"
        / "normalization"
    )
    forbidden_prefixes = (
        "app.services.portrait_provider",
        "app.services.voice_provider",
        "app.services.tts_provider",
        "app.services.realtime_provider",
        "app.services.character_studio_client",
        "app.services.stability_ai_service",
        "app.services.stability_portrait",
        "app.services.runway_client",
    )
    offenders: list[tuple[str, str]] = []
    for py in pkg_root.rglob("*.py"):
        tree = ast.parse(py.read_bytes())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if any(alias.name.startswith(p) for p in forbidden_prefixes):
                        offenders.append((str(py), alias.name))
            elif isinstance(node, ast.ImportFrom):
                mod = node.module or ""
                if any(mod.startswith(p.replace("app.", "").replace(".", ".")) for p in forbidden_prefixes):
                    offenders.append((str(py), mod))
    assert offenders == [], (
        f"normalization package imports provider-specific modules — "
        f"contradicts §17.6.a provider-independence invariant: {offenders}"
    )


# ---- Compat-mirror expectation with §15.6 substrate ----------


def test_manifest_field_names_match_django_normalization_manifest_kwargs() -> None:
    """The returned manifest dict is shaped for direct kwargs
    into ``shell/apps/identity/services.py::record_normalization_manifest``.
    If either side renames a field, this test catches the
    divergence at CI time before any consumer breaks.
    """
    result = NormalizationPipeline(stages=_v1_chain()).run(
        NormalizationSpec(
            raw_bytes=_large_rgba_png(),
            surface_profile_id="presence",
        )
    )
    # The set matches the ``NormalizationManifest`` model's
    # non-auto fields in ``shell/apps/identity/models.py``.
    # (Excludes id, generation_record, raw_output_asset,
    # normalized_output_asset — those are the caller's
    # responsibility to supply alongside the manifest kwargs.)
    assert set(result.manifest) == {
        "pipeline_version",
        "surface_profile_id",
        "surface_profile_version",
        "background_id",
        "stages_executed",
        "stages_skipped",
        "eye_line_adjustments",
        "crop_metadata",
        "execution_duration_ms",
    }
