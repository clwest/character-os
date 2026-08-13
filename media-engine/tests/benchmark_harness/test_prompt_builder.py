"""Prompt-builder discipline tests.

The prompt builder is now part of reproducibility (operator
discipline #1). Its output shape must be:

* deterministic — same inputs, same bytes
* provider-neutral — no provider argument, no provider-branching
* versioned — the emitted prompt carries the builder version stamp
* free of aesthetic optimization — no adjectives added, no
  provider-specific tuning
"""
from __future__ import annotations

import inspect

import pytest

from app.services.benchmark_harness import (
    HumanPortraitReferencePurpose,
    IdentityBranch,
    NonHumanCanonicalReferencePurpose,
    PROMPT_BUILDER_VERSION,
    PromptBuilderError,
    RenderingDirectionHypothesis,
    build_prompt,
    load_ratified_fixtures,
)


# ---- Determinism ------------------------------------------------


def test_build_prompt_is_byte_deterministic_across_repeat_calls() -> None:
    fixtures = load_ratified_fixtures()
    h1 = fixtures[0]
    a = build_prompt(h1, "cinematic_naturalistic", "front")
    b = build_prompt(h1, "cinematic_naturalistic", "front")
    assert a == b


def test_build_prompt_output_changes_with_direction() -> None:
    fixtures = load_ratified_fixtures()
    h1 = fixtures[0]
    a = build_prompt(h1, "identity_only", "front")
    b = build_prompt(h1, "cinematic_naturalistic", "front")
    assert a != b
    assert "identity_only" in a
    assert "cinematic_naturalistic" in b


def test_build_prompt_output_changes_with_purpose() -> None:
    fixtures = load_ratified_fixtures()
    h1 = fixtures[0]
    a = build_prompt(h1, "identity_only", "front")
    b = build_prompt(h1, "identity_only", "neutral_rest")
    assert a != b
    assert "front (category: view)" in a
    assert "neutral_rest (category: expression)" in b


def test_build_prompt_output_changes_with_fixture() -> None:
    fixtures = {f.fixture_id: f for f in load_ratified_fixtures()}
    a = build_prompt(fixtures["fixture_h1"], "identity_only", "front")
    b = build_prompt(fixtures["fixture_h2"], "identity_only", "front")
    assert a != b
    assert "fixture_h1" in a
    assert "fixture_h2" in b


# ---- Provider-neutrality (operator discipline #2) ---------------


def test_build_prompt_signature_has_no_provider_parameter() -> None:
    """Cross-provider evidence discipline requires that the same
    logical candidate produces the same prompt across all
    providers. The strongest possible enforcement is that
    ``build_prompt`` cannot even accept a provider argument."""
    params = list(inspect.signature(build_prompt).parameters.keys())
    assert params == ["fixture", "direction", "purpose"]


def test_build_prompt_contains_no_provider_name_ever() -> None:
    """Sweep every ratified cell for a human fixture and assert
    that no prompt mentions any ratified provider name. If a
    future prompt encoding accidentally leaks a provider-branch
    hint, this test catches it."""
    from app.services.benchmark_harness import RATIFIED_PROVIDERS

    fixtures = load_ratified_fixtures()
    h1 = fixtures[0]
    for direction in RenderingDirectionHypothesis:
        for purpose in HumanPortraitReferencePurpose:
            prompt = build_prompt(h1, direction.value, purpose.value)
            for provider in RATIFIED_PROVIDERS:
                assert provider not in prompt, (
                    f"prompt for direction={direction.value}, "
                    f"purpose={purpose.value} leaked provider "
                    f"name {provider!r}"
                )


# ---- Version stamp discipline (operator discipline #1) ----------


def test_prompt_carries_builder_version_stamp() -> None:
    fixtures = load_ratified_fixtures()
    h1 = fixtures[0]
    prompt = build_prompt(h1, "identity_only", "front")
    assert f"prompt builder v{PROMPT_BUILDER_VERSION}" in prompt


def test_prompt_builder_version_is_v1_at_step_8a() -> None:
    """Locks the version at 8.a landing. Bumping requires a
    deliberate version-bump commit that also updates prior-run
    replay behavior."""
    assert PROMPT_BUILDER_VERSION == "1"


# ---- Axis validation --------------------------------------------


def test_unknown_direction_raises() -> None:
    fixtures = load_ratified_fixtures()
    h1 = fixtures[0]
    with pytest.raises(PromptBuilderError, match="unknown rendering direction"):
        build_prompt(h1, "not_a_direction", "front")


def test_purpose_off_branch_for_human_raises() -> None:
    """A non-human purpose passed against a human fixture is a
    contract violation the builder must catch."""
    fixtures = {f.fixture_id: f for f in load_ratified_fixtures()}
    with pytest.raises(PromptBuilderError, match="not ratified for branch"):
        build_prompt(fixtures["fixture_h1"], "identity_only", "listening_never_authored")


def test_non_human_fixture_can_only_use_non_human_purposes() -> None:
    """Symmetric check for the non-human branch."""
    fixtures = {f.fixture_id: f for f in load_ratified_fixtures()}
    nh1 = fixtures["fixture_nh1"]
    # 'listening' is a valid HUMAN purpose but not non-human — fails.
    with pytest.raises(PromptBuilderError, match="not ratified for branch"):
        build_prompt(nh1, "identity_only", "listening")
    # 'front' is the sole ratified non-human purpose — succeeds.
    prompt = build_prompt(nh1, "identity_only", "front")
    assert "branch=non_human" in prompt


# ---- Aesthetic-language / detection-language guard -------------


_FORBIDDEN_AESTHETIC_SUBSTRINGS = (
    "beautiful", "attractive", "flattering", "pleasing",
    "excellent", "poor", "quality", "ugly",
)

_FORBIDDEN_DETECTION_SUBSTRINGS = (
    "subject_bbox", "face_bbox", "face_detected",
    "eye_detected", "landmark", "silhouette",
)


def test_prompt_carries_no_aesthetic_or_detection_language() -> None:
    """The builder MUST NOT inject aesthetic or detection-outcome
    phrasing. Mirrors the same discipline applied to the
    normalization pipeline's manifest evidence
    (test_step7_closure)."""
    fixtures = load_ratified_fixtures()
    h1 = fixtures[0]
    # Sweep a representative slice — every direction × the
    # ratified 7 purposes for the human branch.
    for direction in RenderingDirectionHypothesis:
        for purpose in HumanPortraitReferencePurpose:
            prompt = build_prompt(
                h1, direction.value, purpose.value,
            ).lower()
            for forbidden in _FORBIDDEN_AESTHETIC_SUBSTRINGS:
                assert forbidden not in prompt, (
                    f"prompt injected aesthetic word {forbidden!r} "
                    f"at direction={direction.value}, purpose={purpose.value}"
                )
            for forbidden in _FORBIDDEN_DETECTION_SUBSTRINGS:
                assert forbidden not in prompt


# ---- Provider-agnostic content: same call from two provider
# ----   contexts produces one prompt -----------------------------


def test_two_provider_contexts_yield_the_same_prompt() -> None:
    """Simulate two provider call-sites building a prompt for
    the same cell. The strings must be byte-identical — no
    context-dependent divergence."""
    fixtures = load_ratified_fixtures()
    h1 = fixtures[0]

    # Provider A context.
    def provider_a_dispatch() -> str:
        return build_prompt(h1, "cinematic_naturalistic", "front")

    # Provider B context (deliberately different call frame).
    def provider_b_dispatch() -> str:
        # Pretend this is inside an adapter — the adapter never
        # gets to modify the prompt.
        prompt = build_prompt(h1, "cinematic_naturalistic", "front")
        return prompt

    assert provider_a_dispatch() == provider_b_dispatch()
