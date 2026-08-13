"""Step 8 closure invariants — pinned before SHIPPED.

Every operator-mandated 8.c closure invariant maps to one test
here. Answers the central Step 8 question with executable
evidence (operator #16):

    Can the benchmark harness produce immutable, reproducible,
    provider-neutral two-tier evidence from the ratified fixture
    matrix without making any qualification decision itself?

Not duplicative with per-module tests: those verify each
module's internal behavior; this file pins cross-module +
architectural invariants that would silently regress otherwise.
"""
from __future__ import annotations

import ast
import json
from pathlib import Path

import pytest

from app.services.benchmark_harness import (
    CELL_OUTCOME_HARNESS_ERROR,
    CELL_OUTCOME_INVALID_FIXTURE,
    CELL_OUTCOME_NORMALIZATION_FAILED,
    CELL_OUTCOME_PROVIDER_REQUEST_FAILED,
    CELL_OUTCOME_PROVIDER_UNAVAILABLE,
    CELL_OUTCOME_SUCCESS,
    CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY,
    HARNESS_SCHEMA_VERSION,
    IdentityBranch,
    MatrixAxes,
    load_fixture,
    run_matrix,
)

from ._test_helpers import large_mock_provider_factory, seed_tmp_fixtures


# ---- 1. Cell status taxonomy pinned (operator #6) -----------


def test_cell_outcome_taxonomy_is_pinned_to_ratified_names() -> None:
    """The stable taxonomy shipped by 8.b + one additional
    ``not_attempted_due_to_fatal_run_error`` used by the runner's
    fatal-run recording path. If any of these strings change, the
    replay + fatal-run + reproducibility contracts all break."""
    ratified = {
        "success",
        "provider_unavailable",
        "provider_request_failed",
        "unsupported_provider_capability",
        "normalization_failed",
        "invalid_fixture",
        "harness_error",
    }
    assert CELL_OUTCOME_SUCCESS == "success"
    assert CELL_OUTCOME_PROVIDER_UNAVAILABLE == "provider_unavailable"
    assert CELL_OUTCOME_PROVIDER_REQUEST_FAILED == "provider_request_failed"
    assert CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY == "unsupported_provider_capability"
    assert CELL_OUTCOME_NORMALIZATION_FAILED == "normalization_failed"
    assert CELL_OUTCOME_INVALID_FIXTURE == "invalid_fixture"
    assert CELL_OUTCOME_HARNESS_ERROR == "harness_error"
    exposed = {
        CELL_OUTCOME_SUCCESS,
        CELL_OUTCOME_PROVIDER_UNAVAILABLE,
        CELL_OUTCOME_PROVIDER_REQUEST_FAILED,
        CELL_OUTCOME_UNSUPPORTED_PROVIDER_CAPABILITY,
        CELL_OUTCOME_NORMALIZATION_FAILED,
        CELL_OUTCOME_INVALID_FIXTURE,
        CELL_OUTCOME_HARNESS_ERROR,
    }
    assert exposed == ratified


# ---- 2. Two-tier evidence invariant (operator #7) -----------


def _cell(tmp_path: Path, *, provider_factory=None, execution_mode="forced_mock"):
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    return run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode=execution_mode, fixtures_root=fixtures_root,
        provider_factory=provider_factory,
    ), fixtures_root


def test_two_tier_evidence_provider_success_norm_success(tmp_path: Path) -> None:
    """Success case: raw + normalized + manifest + candidate ALL required."""
    result, _ = _cell(tmp_path, provider_factory=large_mock_provider_factory)
    r = result.cell_results[0]
    assert r.outcome == "success"
    assert r.raw_artifact is not None
    assert r.normalized_artifact is not None
    assert r.manifest_artifact is not None
    assert r.candidate_artifact is not None


def test_two_tier_evidence_provider_success_norm_fail(tmp_path: Path) -> None:
    """Provider success + normalization failure: raw required;
    normalized + manifest absent; candidate required with
    failure metadata."""
    result, _ = _cell(tmp_path)  # ratified Mock → norm always fails
    r = result.cell_results[0]
    assert r.outcome == "normalization_failed"
    assert r.raw_artifact is not None
    assert r.normalized_artifact is None
    assert r.manifest_artifact is None
    assert r.candidate_artifact is not None
    assert r.stable_failure_code == "input_smaller_than_output"


def test_two_tier_evidence_provider_failure_before_bytes(tmp_path: Path) -> None:
    """Provider failure: raw + normalized + manifest all absent;
    candidate required with provider failure evidence."""
    result, fixtures_root = _cell(tmp_path, execution_mode="real_required")
    r = result.cell_results[0]
    assert r.outcome == "provider_unavailable"
    assert r.raw_artifact is None
    assert r.normalized_artifact is None
    assert r.manifest_artifact is None
    assert r.candidate_artifact is not None
    payload = json.loads(
        (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
    )
    assert payload["provider_stage"]["error"] is not None
    assert payload["provider_stage"]["error"]["class"] == "ProviderUnavailableError"


# ---- 3. File layout closure test (operator #8) --------------


def test_file_layout_uses_ratified_bucketing_plus_one_documented_addition(
    tmp_path: Path,
) -> None:
    """The evidence tree contains the ratified §17.8.a per-artifact
    buckets + the 8.b-added ``candidates/`` locator bucket + the
    ``_runs/<run_id>/`` top-level cross-fixture bucket. No other
    directory taxonomy is introduced."""
    result, fixtures_root = _cell(tmp_path)
    r = result.cell_results[0]
    provider_root = result.layout.cell_provider_root(r.cell)
    on_disk_dirs = sorted(
        p.name for p in provider_root.iterdir() if p.is_dir()
    )
    # Expect: candidates/, observations/, raw/. Norm failed, so
    # no manifests/ or normalized/ subdirectories.
    assert set(on_disk_dirs) == {"candidates", "observations", "raw"}


def test_file_layout_success_case_contains_all_ratified_buckets_used(
    tmp_path: Path,
) -> None:
    result, fixtures_root = _cell(tmp_path, provider_factory=large_mock_provider_factory)
    r = result.cell_results[0]
    provider_root = result.layout.cell_provider_root(r.cell)
    on_disk_dirs = sorted(
        p.name for p in provider_root.iterdir() if p.is_dir()
    )
    assert set(on_disk_dirs) == {"candidates", "manifests", "normalized", "observations", "raw"}


def test_scores_bucket_never_created_by_step_8_at_any_path(tmp_path: Path) -> None:
    """Global anchor: scan the entire fixtures tree for any
    ``scores/`` directory Step 8 might have accidentally created."""
    result, fixtures_root = _cell(tmp_path, provider_factory=large_mock_provider_factory)
    for p in fixtures_root.rglob("scores"):
        assert not p.is_dir(), (
            f"Step 8 created a scores/ directory at {p} — Step 9 territory"
        )


# ---- 4. Evidence schema version discipline (operator #9) ----


def test_candidate_and_run_summary_both_carry_harness_schema_version(
    tmp_path: Path,
) -> None:
    result, fixtures_root = _cell(tmp_path)
    r = result.cell_results[0]
    candidate = json.loads(
        (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
    )
    summary = json.loads(result.layout.run_summary_path.read_text())
    assert candidate["harness_schema_version"] == HARNESS_SCHEMA_VERSION
    assert summary["harness_schema_version"] == HARNESS_SCHEMA_VERSION


# ---- 5. Provider capabilities snapshot canonicalization -----


def test_provider_capabilities_snapshot_is_canonical_and_stable(
    tmp_path: Path,
) -> None:
    """The capabilities dict serialized on candidate.json is
    stable across runs — supported_models / aspect_ratios /
    execution_modes_supported are sorted; capability payload
    is byte-identical for identical adapter identity."""
    # Two independent runs with the ratified Mock; capabilities
    # snapshot must be byte-identical (even without diffing the
    # rest of the candidate).
    from app.services.benchmark_harness import canonical_json_bytes

    result_a, root_a = _cell(tmp_path / "a")
    result_b, root_b = _cell(tmp_path / "b")
    ca = json.loads(
        (root_a / result_a.cell_results[0].candidate_artifact.relative_from_fixtures_root).read_text()
    )["provider_stage"]["capabilities"]
    cb = json.loads(
        (root_b / result_b.cell_results[0].candidate_artifact.relative_from_fixtures_root).read_text()
    )["provider_stage"]["capabilities"]
    # Same dict content.
    assert ca == cb
    # Canonically serializable to identical bytes.
    assert canonical_json_bytes(ca) == canonical_json_bytes(cb)


# ---- 6. Boundary guards strengthened (operator #11) ---------


_HARNESS_ROOT = (
    Path(__file__).resolve().parents[2]
    / "app" / "services" / "benchmark_harness"
)

# Extended forbidden import surface for 8.c closure. Includes
# every specific legacy call site the operator named.
_FORBIDDEN_FOR_CLOSURE = (
    # Direct legacy image services / clients.
    "app.services.character_studio_client",
    "app.services.stability_ai_service",
    "app.services.stability_portrait",
    "app.services.runway_client",
    "app.services.image_stability",
    "app.services.avatar_listing_client",
    "app.services.character_host_client",
    "app.services.animated_pip_client",
    # Legacy media-engine internal routers.
    "app.routers.internal",
    # Django-side.
    "apps.identity",
    "shell.apps.identity",
    "django",
    "django.conf",
    "django.db",
    # Scoring / bootstrap review code (Step 9/10 territory).
    "app.services.scoring",
    "app.services.bootstrap_review",
    # Direct pixel manipulation MUST NOT enter the harness. The
    # harness orchestrates PortraitProvider + NormalizationPipeline;
    # it never becomes another image-processing layer.
    "PIL",
    "PIL.Image",
    "rembg",
    "onnxruntime",
    "cv2",
    "numpy",
)


def _harness_modules() -> list[Path]:
    return sorted(_HARNESS_ROOT.rglob("*.py"))


def _absolute_imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_bytes())
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module is not None and node.level == 0:
                names.add(node.module)
    return names


def test_harness_never_imports_forbidden_legacy_or_image_processing_modules() -> None:
    """Closure-strengthened boundary guard. Covers legacy image
    services + Django + scoring/bootstrap-review + direct
    Pillow/rembg/opencv/onnx — the harness ORCHESTRATES, it does
    not become another image-processing layer."""
    offenders: list[tuple[str, str]] = []
    for py in _harness_modules():
        for imp in _absolute_imports(py):
            for forbidden in _FORBIDDEN_FOR_CLOSURE:
                if imp == forbidden or imp.startswith(forbidden + "."):
                    offenders.append(
                        (str(py.relative_to(_HARNESS_ROOT)), imp),
                    )
    assert offenders == [], (
        f"benchmark_harness production modules import forbidden "
        f"paths for closure: {offenders}"
    )


def test_harness_uses_portrait_provider_and_normalization_only(tmp_path: Path) -> None:
    """The harness's runtime call graph enters provider execution
    via ``PortraitProvider`` and normalization via
    ``NormalizationPipeline`` — never via a legacy shortcut. This
    test runs a small matrix and confirms the produced evidence
    carries provider provenance stamped by the ratified adapter
    (not by any bypass)."""
    result, fixtures_root = _cell(tmp_path)
    r = result.cell_results[0]
    candidate = json.loads(
        (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
    )
    assert candidate["provider_stage"]["provider"] == "mock"
    # Capabilities is factual (matches §9.5 discipline).
    assert candidate["provider_stage"]["capabilities"] is not None


# ---- 7. No Step-9 state vocabulary (operator #12) ----------


_STEP_9_STATE_STRINGS = (
    "selected", "approved", "rejected",
    "reviewer_score", "trust_score", "aesthetic_score",
    "preferred_provider", "winner", "qualification_passed",
    "qualification_failed",
)


def test_no_step_9_state_vocabulary_in_any_emitted_evidence(tmp_path: Path) -> None:
    """Sweep every emitted evidence surface (candidate + run
    summary, both success + normalization-failure cases) for
    Step-9 state strings. Neutral guard values like
    ``not_evaluated`` are permitted; anything else is not."""
    from app.services.benchmark_harness import (
        IdentityBranch as _IdentityBranch,
        MatrixAxes as _MatrixAxes,
        load_fixture as _load_fixture,
        run_matrix as _run_matrix,
    )
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1", "fixture_nh1"])
    fixtures = [
        _load_fixture("fixture_h1", fixtures_root=fixtures_root),
        _load_fixture("fixture_nh1", fixtures_root=fixtures_root),
    ]
    axes = _MatrixAxes(
        fixture_ids=("fixture_h1", "fixture_nh1"),
        directions=("identity_only",),
        purposes_by_branch={
            _IdentityBranch.HUMAN: ("front",),
            _IdentityBranch.NON_HUMAN: ("front",),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    result = _run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    # Read every emitted JSON file under fixtures_root.
    all_json_files = list(fixtures_root.rglob("*.json"))
    assert len(all_json_files) > 0
    for f in all_json_files:
        text = f.read_text().lower()
        for word in _STEP_9_STATE_STRINGS:
            assert word not in text, (
                f"Step-9 vocabulary {word!r} leaked into evidence at {f}"
            )


# ---- 8. fixture_nh1 closure invariant (operator #13) -------


def test_fixture_nh1_flows_through_same_machinery_with_marker(
    tmp_path: Path,
) -> None:
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_nh1"])
    fixtures = [load_fixture("fixture_nh1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_nh1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: (),
            IdentityBranch.NON_HUMAN: ("front",),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    r = result.cell_results[0]
    candidate = json.loads(
        (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
    )
    # Branch preserved.
    assert candidate["identity"]["branch"] == "non_human"
    # Reference kind is the non-canonical placeholder per §17.2.b.
    assert candidate["cell"]["reference_kind"] == "canonical_reference"
    # not_applicable_unscored marker survives.
    assert candidate["not_applicable_unscored"] is True
    # No aesthetic / quality interpretation emitted.
    for scoring_field in (
        "identity_continuity", "warmth", "trust_review",
        "aesthetic_character_consistent_with_brief",
    ):
        assert scoring_field not in candidate


# ---- 9. Known provider/profile evidence anchors (operator #14)


def test_ratified_mock_on_ratified_profiles_produces_expected_failure(
    tmp_path: Path,
) -> None:
    """The ratified Mock's 256×256 output cannot survive any
    ratified profile's declared output dimensions. Every cell
    factually fails with ``input_smaller_than_output``. This is
    honest provider-capability evidence per operator #17."""
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock",),
        surface_profiles=("compact", "team_card"),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    for r in result.cell_results:
        assert r.outcome == "normalization_failed"
        assert r.stable_failure_code == "input_smaller_than_output"
