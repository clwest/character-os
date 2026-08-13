"""Runner-level provider-neutral prompt test.

Operator discipline #2 lock: the same logical cell handed to
two different providers MUST receive byte-identical final
prompts. The prompt-builder unit test proves the function is
provider-neutral by signature; this runner-level test proves
the runner does not add provider-specific prompt patching on
its dispatch path.
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


def _fixture_setup(tmp_path: Path):
    fixtures_root = seed_tmp_fixtures(tmp_path, ["fixture_h1"])
    fixtures = [load_fixture("fixture_h1", fixtures_root=fixtures_root)]
    return fixtures_root, fixtures


def _load_candidate(fixtures_root: Path, cell_result) -> dict:
    return json.loads(
        (fixtures_root / cell_result.candidate_artifact.relative_from_fixtures_root).read_text()
    )


def test_two_providers_receive_byte_identical_prompt_for_same_cell(
    tmp_path: Path,
) -> None:
    """One run, two providers (mock + stability_still). The
    (fixture, direction, purpose) triple is identical across
    the two providers; the runner MUST hand both adapters the
    same final prompt string."""
    fixtures_root, fixtures = _fixture_setup(tmp_path)
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock", "stability_still"),
        surface_profiles=("compact",),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
        provider_factory=large_mock_provider_factory,
    )
    by_provider = {r.cell.provider: r for r in result.cell_results}
    assert set(by_provider) == {"mock", "stability_still"}
    prompt_mock = _load_candidate(fixtures_root, by_provider["mock"])["provider_stage"]["prompt"]
    prompt_stab = _load_candidate(fixtures_root, by_provider["stability_still"])["provider_stage"]["prompt"]
    assert prompt_mock == prompt_stab


def test_provider_neutral_prompt_holds_across_every_ratified_provider(
    tmp_path: Path,
) -> None:
    """Extend across all three ratified providers. Even the
    Runway adapter's mock code path receives the shared prompt.
    """
    fixtures_root, fixtures = _fixture_setup(tmp_path)
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only",),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock", "stability_still", "runway_still_portrait"),
        surface_profiles=("compact",),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
        provider_factory=large_mock_provider_factory,
    )
    prompts = {
        r.cell.provider: _load_candidate(fixtures_root, r)["provider_stage"]["prompt"]
        for r in result.cell_results
    }
    # All three prompts are byte-identical to one canonical value.
    canonical = prompts["mock"]
    for prov, prompt in prompts.items():
        assert prompt == canonical, (
            f"provider {prov!r} received a divergent prompt — cross-"
            f"provider evidence would be invalid"
        )


def test_provider_neutral_prompt_holds_across_different_directions(
    tmp_path: Path,
) -> None:
    """Sanity anchor: while the prompts SHARED across providers
    for the same direction are identical, the prompt DOES change
    when direction changes. Ensures the sharing invariant isn't
    trivial (i.e. all prompts always equal)."""
    fixtures_root, fixtures = _fixture_setup(tmp_path)
    axes = MatrixAxes(
        fixture_ids=("fixture_h1",),
        directions=("identity_only", "cinematic_naturalistic"),
        purposes_by_branch={
            IdentityBranch.HUMAN: ("front",),
            IdentityBranch.NON_HUMAN: (),
        },
        providers=("mock", "stability_still"),
        surface_profiles=("compact",),
    )
    result = run_matrix(
        fixtures=fixtures, axes=axes,
        execution_mode="forced_mock", fixtures_root=fixtures_root,
        provider_factory=large_mock_provider_factory,
    )
    by_key = {
        (r.cell.provider, r.cell.direction): _load_candidate(fixtures_root, r)["provider_stage"]["prompt"]
        for r in result.cell_results
    }
    # Within a direction, providers agree.
    assert by_key[("mock", "identity_only")] == by_key[("stability_still", "identity_only")]
    assert by_key[("mock", "cinematic_naturalistic")] == by_key[("stability_still", "cinematic_naturalistic")]
    # Across directions, prompts differ.
    assert by_key[("mock", "identity_only")] != by_key[("mock", "cinematic_naturalistic")]
