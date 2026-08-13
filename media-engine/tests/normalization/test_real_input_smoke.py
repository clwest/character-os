"""Opt-in real-input normalization smoke (SESSION 246 Step 7 closure).

Runs the ratified v1 chain against a real Runway / Stability
portrait retained locally at ``media-engine/data/_internal/portraits/``
(gitignored per CLAUDE.md). Gated on
``NORMALIZATION_REAL_INPUT_SMOKE=1`` — kept opt-in so CI does
NOT pay rembg's ONNX-load cost on every run against a real-size
1280x720 image, and so the smoke never runs against a missing
directory.

**Purpose is implementation validation, not aesthetic scoring**
per SESSION 246 operator ratification. Verifies:

* the retained real portrait bytes decode as PNG
* rembg matting succeeds on real portrait bytes (not just
  small synthetic RGBA)
* full v1 chain (Crop v2 → Framing → BgReplace) completes
* output is a valid PNG at the profile's declared dimensions
* repeat runs are byte-identical
* manifest has every required §10.6 field
* no synthetic-fixture assumption is hidden by the smoke's
  small-input tests

Does NOT verify:

* whether the crop looks good
* whether the eye-line proxy landed a plausible eye position
* whether the procedural background reads correctly against
  the portrait's own tone
* whether reviewers would score the composite favorably

Those are Step 8 / Step 10 concerns.

Does NOT make any provider API call. The smoke reads bytes
from disk that were produced by earlier authorized real-mode
sessions.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest

from app.services.normalization import (
    NormalizationPipeline,
    NormalizationSpec,
)
from app.services.normalization.png import decode_png
from app.services.normalization.stages.background_replacement import (
    BackgroundReplacementStage,
)
from app.services.normalization.stages.crop import CropStage
from app.services.normalization.stages.framing import FramingStage


REAL_SMOKE_ENV = "NORMALIZATION_REAL_INPUT_SMOKE"


def _retained_portraits_dir() -> Path:
    """Portraits dir per media-engine's storage convention.

    Resolves via ``__file__`` so the smoke works regardless of
    the pytest invocation cwd.
    """
    return (
        Path(__file__).resolve().parents[2]
        / "data"
        / "_internal"
        / "portraits"
    )


def _pick_smoke_portrait() -> Path | None:
    """Return the first available retained portrait, or ``None``
    if none exist locally. Sorted by name so the choice is
    deterministic within a given operator's checkout.
    """
    d = _retained_portraits_dir()
    if not d.is_dir():
        return None
    candidates = sorted(d.glob("*.png"))
    return candidates[0] if candidates else None


_SMOKE_GATED = pytest.mark.skipif(
    os.environ.get(REAL_SMOKE_ENV) != "1",
    reason=(
        f"Opt-in real-input normalization smoke. Set "
        f"{REAL_SMOKE_ENV}=1 with a retained portrait at "
        f"media-engine/data/_internal/portraits/*.png to run."
    ),
)


@_SMOKE_GATED
def test_retained_portrait_exists_before_smoke_runs() -> None:
    """When the smoke is opted in, guard against a false
    positive from an absent local directory. Skip explicitly
    with an actionable message rather than pretending the
    smoke ran.
    """
    if _pick_smoke_portrait() is None:
        pytest.skip(
            "No retained portrait bytes available under "
            f"{_retained_portraits_dir()}. Run a portrait "
            "provider real-mode call in a prior session to "
            "populate this directory, then re-run this smoke."
        )


@_SMOKE_GATED
def test_real_portrait_flows_through_v1_chain_where_geometry_permits() -> None:
    """Run the real portrait against every ratified surface
    profile and record which succeed vs. which fail.

    **Finding surfaced by this smoke (SESSION 246 Step 7 closure):**
    Retained real Runway portraits are 1280x720 (Runway's
    ``gen4_image`` currently only ships this aspect per
    SESSION 244 finding). Under CropStage(v2)'s pixel-exact
    aspect crop, that produces:

    * compact (1:1, 512x512 output) — 720x720 crop, downscale
      OK.
    * team_card (1:1, 384x384 output) — 720x720 crop, downscale
      OK.
    * presence (4:5, 720x900 output) — 576x720 crop, refused
      at Framing (``input_smaller_than_output``).
    * studio (3:4, 900x1200 output) — 540x720 crop, refused.
    * conversation (3:4, 900x1200 output) — 540x720 crop,
      refused.

    This is the pipeline behaving correctly — v1 refuses to
    upscale. It exposes a genuine product-level limitation:
    Runway's current 1280x720-only image output cannot feed
    Character OS's portrait-oriented profiles without either
    (a) a real upscale-policy decision or (b) a wider Runway
    aspect option shipping upstream. Recorded in the SESSION
    246 handoff.

    The smoke asserts the load-bearing invariants:

    * At least the two 1:1-output profiles (compact, team_card)
      succeed end-to-end on real Runway bytes.
    * Every failure is deterministic ``input_smaller_than_output``
      (never a nondeterminism / rembg / decode bug).
    * Successful outputs are valid PNGs at the profile's
      declared dimensions.
    * Manifest is complete on every success.
    """
    portrait_path = _pick_smoke_portrait()
    if portrait_path is None:
        pytest.skip("No retained portrait bytes.")

    raw = portrait_path.read_bytes()
    from app.services.normalization import PipelineStageError, load_surface_profile

    ratified_profiles = ("compact", "presence", "studio", "conversation", "team_card")

    successes: list[str] = []
    failures: dict[str, str] = {}

    for profile_id in ratified_profiles:
        profile = load_surface_profile(profile_id)
        pipeline = NormalizationPipeline(
            stages=[CropStage(), FramingStage(), BackgroundReplacementStage()]
        )
        try:
            result = pipeline.run(
                NormalizationSpec(
                    raw_bytes=raw,
                    surface_profile_id=profile_id,
                )
            )
        except PipelineStageError as exc:
            # Any real-input failure MUST be the ratified
            # upscale-refusal — never a nondeterminism / decode
            # / rembg-provider bug.
            assert exc.stage_name == "framing", (
                f"{profile_id}: unexpected stage failure at "
                f"{exc.stage_name!r}: {exc!s}"
            )
            assert "input_smaller_than_output" in str(exc), (
                f"{profile_id}: unexpected failure reason: {exc!s}"
            )
            failures[profile_id] = str(exc)
            continue

        successes.append(profile_id)
        # Successful output validates every §10.6 invariant.
        decoded = decode_png(result.normalized_bytes)
        assert decoded.size == (
            profile.output.width_px, profile.output.height_px,
        )
        for field in (
            "pipeline_version", "surface_profile_id",
            "surface_profile_version", "background_id",
            "stages_executed", "stages_skipped",
            "eye_line_adjustments", "crop_metadata",
            "execution_duration_ms",
        ):
            assert field in result.manifest
        executed_names = [
            row["stage_name"] for row in result.manifest["stages_executed"]
        ]
        assert executed_names == ["crop", "framing", "background_replacement"]

    # The 1:1-output profiles must succeed on the Runway 1280x720
    # size; if they ever don't, either the profile YAML changed
    # or a stage regressed. The others may or may not — that
    # depends on real provider aspect ratios.
    assert "compact" in successes, (
        f"compact profile failed on real 1280x720 input: "
        f"{failures.get('compact')}"
    )
    assert "team_card" in successes, (
        f"team_card profile failed on real 1280x720 input: "
        f"{failures.get('team_card')}"
    )

    # Report smoke observations as evidence in the test output.
    print(
        f"\n[SESSION 246 Step 7 real-input smoke] "
        f"portrait={portrait_path.name} "
        f"successes={successes} "
        f"upscale-refused={list(failures.keys())}"
    )


@_SMOKE_GATED
def test_real_portrait_v1_chain_is_byte_deterministic_over_repeat_runs() -> None:
    """§10.6 anchor at real-input level. Uses ``compact`` since
    it's the profile that reliably succeeds on real Runway
    1280x720 output.
    """
    portrait_path = _pick_smoke_portrait()
    if portrait_path is None:
        pytest.skip("No retained portrait bytes.")

    raw = portrait_path.read_bytes()
    spec = NormalizationSpec(
        raw_bytes=raw,
        surface_profile_id="compact",
    )
    pipeline = NormalizationPipeline(
        stages=[CropStage(), FramingStage(), BackgroundReplacementStage()]
    )
    a = pipeline.run(spec)
    b = pipeline.run(spec)
    assert a.normalized_bytes == b.normalized_bytes, (
        "real-input v1 chain nondeterministic on repeat runs — "
        "investigate before ratifying Step 7 closed."
    )


@_SMOKE_GATED
def test_real_portrait_raw_bytes_not_mutated() -> None:
    """The pipeline never touches raw input bytes. Uses
    ``compact`` for the same geometry reason as the
    determinism test.
    """
    portrait_path = _pick_smoke_portrait()
    if portrait_path is None:
        pytest.skip("No retained portrait bytes.")

    raw = portrait_path.read_bytes()
    original = bytes(raw)
    NormalizationPipeline(
        stages=[CropStage(), FramingStage(), BackgroundReplacementStage()]
    ).run(
        NormalizationSpec(raw_bytes=raw, surface_profile_id="compact")
    )
    assert raw == original
