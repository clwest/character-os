"""No-qualification-vocabulary guard on emitted evidence.

Operator discipline #10 + #12: Step 8 emits factual operational
outcomes only. Words like 'best,' 'preferred,' 'beautiful,'
'quality,' 'trust,' 'winner,' 'approved,' 'selected,'
'benchmark-qualified,' etc. MUST NEVER appear in candidate.json,
run_summary.json, or the normalization manifest payload embedded
on candidate records.

Operational terms like ``provider_request_failed`` or
``normalization_failed`` are fine — they describe what happened,
not a judgment.
"""
from __future__ import annotations

import json
from pathlib import Path

from app.services.benchmark_harness import (
    IdentityBranch,
    MatrixAxes,
    load_fixture,
    run_matrix,
)

from ._test_helpers import large_mock_provider_factory, seed_tmp_fixtures


_FORBIDDEN_QUALIFICATION_WORDS: tuple[str, ...] = (
    # Aesthetic/quality judgments.
    "beautiful", "attractive", "flattering", "pleasing",
    "ugly", "excellent", "high_quality", "low_quality",
    "natural_looking", "cinematic_grading_quality",
    "quality_score", "quality_rating",
    # Trust / winner rhetoric.
    "trust_score", "trust_review_verdict", "winner",
    "candidate_winner", "top_pick", "best_candidate",
    "worst_candidate",
    # "preferred" as a verdict — compound-form only to avoid
    # false-positives on legitimate schema field names like
    # ``preferred_default_framing``.
    "preferred_provider", "preferred_candidate",
    "reviewer_preferred", "preferred_by_reviewer",
    # Selection / approval that Step 9 owns.
    "selected_by_reviewer", "reviewer_selected",
    "approval_state", "approved_by",
    "candidate_approved", "candidate_selected",
    "recommended_candidate",
    # Qualification verdicts.
    "qualified", "unqualified", "benchmark_qualified",
    "pass_verdict", "fail_verdict",
    "qualification_pass", "qualification_fail",
)

# Operational strings that legitimately overlap forbidden
# substrings but are NOT qualification vocabulary. Extend as new
# evidence-emission surfaces land.
_ALLOWED_EXACT_SUBSTRINGS: tuple[str, ...] = (
    "provider_request_failed",
    "normalization_failed",
    "background_replacement_failed",
    "not_attempted_due_to_fatal_run_error",
    "input_smaller_than_output",
)


def _sanitize_for_scan(text: str) -> str:
    """Replace allowed operational substrings with placeholders so
    the forbidden-word scan does not false-positive on them."""
    for allowed in _ALLOWED_EXACT_SUBSTRINGS:
        text = text.replace(allowed, "___OPERATIONAL_STRING___")
    return text


def _every_word_absent(payload_text: str) -> list[str]:
    sanitized = _sanitize_for_scan(payload_text.lower())
    offenders: list[str] = []
    for word in _FORBIDDEN_QUALIFICATION_WORDS:
        if word in sanitized:
            offenders.append(word)
    return offenders


def _small_setup(tmp_path: Path):
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1", "fixture_nh1"])
    fixtures = [
        load_fixture("fixture_h1", fixtures_root=fixtures_root),
        load_fixture("fixture_nh1", fixtures_root=fixtures_root),
    ]
    axes = MatrixAxes(
        fixture_ids=("fixture_h1", "fixture_nh1"),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: ("front",),
        },
        providers=("mock",),
        surface_profiles=("compact",),
    )
    return fixtures_root, fixtures, axes


def test_candidate_json_carries_no_qualification_vocabulary(tmp_path: Path) -> None:
    fixtures_root, fixtures, axes = _small_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    for r in result.cell_results:
        text = (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
        offenders = _every_word_absent(text)
        assert offenders == [], (
            f"candidate.json for cell {r.cell} leaked qualification "
            f"vocabulary: {offenders}"
        )


def test_success_candidate_json_carries_no_qualification_vocabulary(
    tmp_path: Path,
) -> None:
    """The SUCCESS path (via large-mock stub) emits an embedded
    manifest_payload — check it too."""
    fixtures_root, fixtures, axes = _small_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
        provider_factory=large_mock_provider_factory,
    )
    for r in result.cell_results:
        text = (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
        offenders = _every_word_absent(text)
        assert offenders == [], (
            f"success candidate for cell {r.cell} leaked qualification "
            f"vocabulary: {offenders}"
        )


def test_run_summary_carries_no_qualification_vocabulary(tmp_path: Path) -> None:
    fixtures_root, fixtures, axes = _small_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    text = result.layout.run_summary_path.read_text()
    offenders = _every_word_absent(text)
    assert offenders == [], (
        f"run_summary.json leaked qualification vocabulary: {offenders}"
    )


def test_qualification_status_field_uses_only_neutral_value(
    tmp_path: Path,
) -> None:
    """The run_summary's ``qualification_status`` field exists as
    the factual guard against invented scoring. Its ONLY
    permitted value at Step 8 is ``not_evaluated``. If any other
    value ever lands there, this test fires."""
    fixtures_root, fixtures, axes = _small_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    payload = json.loads(result.layout.run_summary_path.read_text())
    assert payload["qualification_status"] == "not_evaluated"


def test_no_scoring_related_fields_on_candidate(tmp_path: Path) -> None:
    """Candidate JSON must not carry any score, rating, verdict,
    selected marker, or approval state."""
    fixtures_root, fixtures, axes = _small_setup(tmp_path)
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
    )
    for r in result.cell_results:
        payload = json.loads(
            (fixtures_root / r.candidate_artifact.relative_from_fixtures_root).read_text()
        )
        forbidden_keys = {
            "score", "rating", "verdict", "approval_state",
            "selected", "approved_by", "reviewer_notes",
            "identity_continuity", "warmth", "trust_review",
        }
        # Recursively scan for forbidden keys.
        stack = [payload]
        found: list[str] = []
        while stack:
            node = stack.pop()
            if isinstance(node, dict):
                for k, v in node.items():
                    if k in forbidden_keys:
                        found.append(k)
                    stack.append(v)
            elif isinstance(node, list):
                stack.extend(node)
        assert found == [], (
            f"cell {r.cell} candidate carries forbidden scoring keys: {found}"
        )
