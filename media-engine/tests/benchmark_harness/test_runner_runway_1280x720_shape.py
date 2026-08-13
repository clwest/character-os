"""Runway-1280x720 → portrait-profile normalization-failure shape.

Operator discipline #10 + #12 lock: the Runway 1280×720
constraint (portrait-oriented profiles refuse via
``input_smaller_than_output`` at FramingStage) emerges from the
generic normalization runner without any Runway special-casing.

This test uses a stub provider that returns Runway-sized bytes
(1280×720) and confirms:

* Raw provider evidence is written even when normalization fails.
* Normalized artifact and manifest are absent for the failing
  cells.
* stable_failure_code is ``input_smaller_than_output``.
* 1:1 profiles (compact, team_card) succeed end-to-end on the
  same 1280×720 input.

The same generic machinery handles ANY provider whose output
geometry is incompatible with a profile — not just Runway.
"""
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any

from PIL import Image

from app.services.benchmark_harness import (
    IdentityBranch,
    MatrixAxes,
    load_fixture,
    run_matrix,
)
from app.services.normalization.png import encode_png
from app.services.portrait_provider import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProviderName,
    PortraitResult,
    PortraitSpec,
    ProviderCapabilities,
    ProviderUnavailableError,
)

from ._test_helpers import seed_tmp_fixtures


class Runway1280x720Stub:
    """Stub that returns a 1280×720 RGBA PNG regardless of the
    requested aspect ratio — simulating Runway's real
    ``gen4_image`` behavior (1280×720-only per SESSION 244
    finding). Deterministic bytes per prompt."""

    def generate_still_portrait(self, spec: PortraitSpec) -> PortraitResult:
        if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
            raise ProviderUnavailableError("stub does not implement REAL_REQUIRED")
        seed = hashlib.sha256(spec.prompt.encode("utf-8")).digest()
        color = (seed[0], seed[1], seed[2], 255)
        img = Image.new("RGBA", (1280, 720), color)
        raw = encode_png(img)
        start = time.monotonic()
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return PortraitResult(
            image_bytes=raw,
            provider=PortraitProviderName.RUNWAY_STILL_PORTRAIT,
            provider_model=spec.provider_model or "gen4_image_stub",
            execution_mode_actual=ExecutionModeActual.MOCK,
            prompt_snapshot={
                "prompt": spec.prompt,
                "aspect_ratio": spec.aspect_ratio,
                "deterministic_seed": spec.deterministic_seed,
                "requested_execution_mode": spec.execution_mode.value,
            },
            elapsed_ms=elapsed_ms,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=PortraitProviderName.RUNWAY_STILL_PORTRAIT,
            provider_model="gen4_image_stub",
            supported_models=("gen4_image_stub",),
            # Deliberately broad so the harness can request 1:1
            # etc. — the stub always returns 1280×720 anyway.
            supported_aspect_ratios=(
                "1:1", "3:4", "4:5", "4:3", "9:16", "16:9", "1280:720",
            ),
            max_prompt_length=None,
            is_deterministic=True,
            execution_modes_supported=frozenset(
                {ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO},
            ),
        )

    def provider_name(self) -> PortraitProviderName:
        return PortraitProviderName.RUNWAY_STILL_PORTRAIT


def _stub_factory(name: str, settings: Any) -> Runway1280x720Stub:
    return Runway1280x720Stub()


def test_1280x720_input_produces_expected_shape_per_profile(tmp_path: Path) -> None:
    """Reproduce the SESSION 246 real-input smoke shape:
    compact + team_card succeed (1:1 crop, 720×720 downscales
    into declared dims); presence + studio + conversation fail
    at FramingStage with ``input_smaller_than_output``."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("runway_still_portrait",),
        surface_profiles=("compact", "team_card", "presence", "studio", "conversation"),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
        provider_factory=_stub_factory,
    )
    by_profile = {r.cell.surface_profile: r for r in result.cell_results}

    # Expected: 1:1 profiles succeed end-to-end on 1280×720.
    for good_profile in ("compact", "team_card"):
        r = by_profile[good_profile]
        assert r.outcome == "success", (
            f"{good_profile} should succeed on 1280×720; got "
            f"{r.outcome} — reason={r.stable_failure_code!r}"
        )
        assert r.normalized_artifact is not None
        assert r.manifest_artifact is not None

    # Expected: portrait-oriented profiles fail deterministically.
    for bad_profile in ("presence", "studio", "conversation"):
        r = by_profile[bad_profile]
        assert r.outcome == "normalization_failed", (
            f"{bad_profile} should have deterministic normalization "
            f"failure on 1280×720; got {r.outcome}"
        )
        assert r.stable_failure_code == "input_smaller_than_output"
        # Raw evidence preserved even though normalization failed.
        assert r.raw_artifact is not None
        # Normalized artifact absent — no fake artifact created.
        assert r.normalized_artifact is None
        assert r.manifest_artifact is None


def test_failing_cell_raw_evidence_survives_and_is_hashed(tmp_path: Path) -> None:
    """The raw provider output for a 1280×720 → portrait-profile
    failing cell is preserved and its SHA-256 recorded on
    candidate.json. Step 9 promotion path can still inspect the
    exact bytes Runway produced."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("runway_still_portrait",),
        surface_profiles=("presence",),  # portrait-oriented; will fail
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
        provider_factory=_stub_factory,
    )
    r = result.cell_results[0]
    assert r.outcome == "normalization_failed"
    assert r.stable_failure_code == "input_smaller_than_output"

    raw_path = fixtures_root / r.raw_artifact.relative_from_fixtures_root
    assert raw_path.exists()
    # Bytes on disk are the exact bytes the stub produced.
    on_disk_hash = hashlib.sha256(raw_path.read_bytes()).hexdigest()
    assert on_disk_hash == r.raw_artifact.sha256_hex

    # Candidate JSON records the same hash.
    payload = json.loads(
        (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
    )
    assert payload["raw_artifact"]["sha256_hex"] == on_disk_hash
    assert payload["normalization_stage"]["outcome"] == "failed"
    assert payload["normalization_stage"]["normalized_artifact"] is None


def test_no_runway_special_case_in_harness_code() -> None:
    """The harness code (production modules only) contains no
    Runway-specific branching in the runner or dispatcher.
    Enforced via source-text scan — a future ``if provider ==
    'runway'`` branch trips this test."""
    import pathlib
    harness_root = (
        pathlib.Path(__file__).resolve().parents[2]
        / "app" / "services" / "benchmark_harness"
    )
    banned_substrings = (
        # If a runner ever starts branching on provider name for
        # Runway-specific behavior, it is a scope regression.
        'if provider == "runway',
        "if provider == 'runway",
        "elif provider == 'runway",
        'elif provider == "runway',
        "== 'runway_still_portrait'",
        '== "runway_still_portrait"',
    )
    offenders: list[tuple[str, str]] = []
    for py in harness_root.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        for phrase in banned_substrings:
            if phrase in text:
                offenders.append((py.name, phrase))
    assert offenders == [], (
        f"benchmark_harness contains Runway-specific special-casing: "
        f"{offenders} — violates operator discipline #12"
    )
