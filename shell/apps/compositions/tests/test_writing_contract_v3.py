"""SESSION 258 — Dialogue watchability contract v3 tests.

Deterministic contract-shape tests for the SESSION 258 dialogue
watchability slice. Every assert is a plain string / hash check
against the return of ``WritingContract.for_shape(...)``; no DB, no
LLM, no fixtures beyond module-level constants.

Coverage matches the operator's 11-point checklist from the
watchability slice brief:

1.  ``WRITING_CONTRACT_VERSION == 3``.
2.  dialogue_scene contract includes the five new watchability
    invariants (in-scene stance / meaningful change / action over
    philosophy / knowledge-influences-not-recitation / end on a
    moment).
3.  framework-recitation anti-pattern present.
4.  role-summary anti-pattern present.
5.  mutual-synthesis ending anti-pattern present.
6.  short reactions still explicitly allowed (v2 rhythm rule
    preserved).
7.  no fixed turn count introduced.
8.  no forced alternation introduced.
9.  no mandatory conflict / comedy / sitcom skeleton introduced.
10. standalone contract text unchanged (byte-stable SHA-256 snapshot).
11. long_form contract text unchanged (byte-stable SHA-256 snapshot).
"""
from __future__ import annotations

import hashlib
import re

import pytest

from character_os.writing_contract import (
    WRITING_CONTRACT_VERSION,
    WritingContract,
)


# ---- Byte-stability snapshots ----------------------------------
#
# Captured at v3 commit. If any change to ``writing_contract.py``
# alters the standalone or long_form output, one of these hashes
# fails — forcing an explicit version bump conversation.
#
# The v3 slice's contract is: dialogue_scene text CAN change;
# standalone + long_form text MUST NOT. Regression here means the
# slice quietly widened.

_STANDALONE_SHA256 = (
    "a82955c6a34c20300c79ea695a05744b464f5cebcb5f09be964f3eda4fd6891f"
)
_LONG_FORM_60_500_SHA256 = (
    "b0c0aaed82dad8d593ac929840c09c7f480958809f427987d36fde4cb441b602"
)
_LONG_FORM_BARE_SHA256 = (
    "c0e7f76f45d5ab5da2eb104396ed82f7f5a62e793b249c965f2d5f59145e60c9"
)


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode()).hexdigest()


@pytest.fixture(scope="module")
def dialogue_text() -> str:
    return WritingContract.for_shape("dialogue_scene")


# ---- 1. Version stamp ------------------------------------------


def test_writing_contract_version_reflects_current_slice() -> None:
    """SESSION 269 §15 bumped the version 4 → 5 to add the
    ``solo_scene`` shape (Episode-attached talking_head story mode).
    Standalone + long_form + dialogue_scene contract text remain
    byte-stable across every bump — the snapshots below prove it.
    Every bump forces a deliberate version-stamp conversation."""
    assert WRITING_CONTRACT_VERSION == 5
    assert isinstance(WRITING_CONTRACT_VERSION, int)


# ---- 2. Five new watchability invariants -----------------------


def test_dialogue_contract_contains_in_scene_stance_invariant(
    dialogue_text: str,
) -> None:
    """Invariant 1 — characters enter the scene wanting something."""
    assert "ENTER WITH AN IN-SCENE STANCE" in dialogue_text
    assert "immediate purpose" in dialogue_text
    # Concrete purpose menu — proves the operator's list survived.
    for want in [
        "wants approval",
        "wants an answer",
        "wants to correct",
        "wants to persuade",
        "wants to understand",
    ]:
        assert want in dialogue_text, f"missing example purpose: {want!r}"


def test_dialogue_contract_contains_something_changes_invariant(
    dialogue_text: str,
) -> None:
    """Invariant 2 — a meaningful change occurs; the scene does not
    end in the same conversational state it began in."""
    assert "SOMETHING CHANGES" in dialogue_text
    assert "meaningful change" in dialogue_text
    # Change menu — at least these tokens present.
    for token in [
        "new information",
        "correction",
        "decision",
        "concession",
        "reveal",
        "escalation",
        "earned agreement",
    ]:
        assert token in dialogue_text, f"missing change token: {token!r}"


def test_dialogue_contract_prefers_action_over_philosophy(
    dialogue_text: str,
) -> None:
    """Invariant 3 — characters talk about what's happening, not
    about their methodology."""
    assert "PREFER SPECIFIC ACTION" in dialogue_text
    # The BOTH sides of the contrast pair are load-bearing — pulling
    # either would collapse the guidance to a vague preference.
    assert "Run it again" in dialogue_text
    assert "Our methodology emphasizes repeatability" in dialogue_text
    assert "What did you change?" in dialogue_text
    assert (
        "We should separate variables during experimentation"
        in dialogue_text
    )


def test_dialogue_contract_says_knowledge_influences_not_quoted(
    dialogue_text: str,
) -> None:
    """Invariant 4 — retrieved chunks shape behavior; do not become
    dialogue verbatim."""
    assert "KNOWLEDGE INFLUENCES" in dialogue_text
    assert "IT DOES NOT NEED TO BE QUOTED" in dialogue_text
    # Concrete demonstration pair must survive so the LLM sees both
    # the DO and the DON'T.
    assert "Did you try it twice?" in dialogue_text
    assert "Our framework requires repeatable validation" in dialogue_text


def test_dialogue_contract_ends_on_a_moment_not_summary(
    dialogue_text: str,
) -> None:
    """Invariant 5 — no synthesis endings; scene finishes while
    something is still happening."""
    assert "END ON A MOMENT, NOT A SUMMARY" in dialogue_text
    for ending in [
        "reaction",
        "decision",
        "reveal",
        "callback",
        "escalation",
        "challenge",
        "refusal",
        "concession",
        "unresolved hook",
    ]:
        assert ending in dialogue_text, f"missing ending option: {ending!r}"
    # The prohibition side.
    assert "shared lesson" in dialogue_text


# ---- 3, 4, 5. New anti-patterns --------------------------------


def test_dialogue_contract_prohibits_framework_recitation(
    dialogue_text: str,
) -> None:
    """Anti-pattern A — do NOT turn retrieved lists / frameworks
    into dialogue verbatim."""
    assert "framework recitation" in dialogue_text
    # The core prohibition wording.
    assert "belongs in your knowledge, not in your mouth" in dialogue_text
    # The concrete demonstration that closes the loop.
    assert "demonstrates step 3" in dialogue_text
    # Escape hatch — explicit teach/explain topics are still valid.
    assert "EXPLICITLY asks the characters to teach or explain" in dialogue_text


def test_dialogue_contract_prohibits_role_summary(
    dialogue_text: str,
) -> None:
    """Anti-pattern B — do NOT summarize your own role, the
    relationship, or the workflow."""
    assert "role summary" in dialogue_text
    # The specific example line that made the problem obvious in
    # the P2 dogfood (`9e4601c7`) must be quoted so the model sees
    # exactly what fails.
    assert "You bring momentum" in dialogue_text
    assert "I bring the checklist" in dialogue_text
    assert "Together we get answers" in dialogue_text
    assert "self-description dressed as dialogue" in dialogue_text


def test_dialogue_contract_prohibits_mutual_synthesis_ending(
    dialogue_text: str,
) -> None:
    """Anti-pattern C — do NOT end on A summarizes → B agrees +
    restates. That's an ending stub the model reaches for when no
    reveal was set up."""
    assert "mutual-synthesis ending" in dialogue_text
    assert "restates the lesson" in dialogue_text
    assert "ending stub" in dialogue_text
    assert (
        "Let the scene finish while something is still happening"
        in dialogue_text
    )


# ---- 6-9. Preserve v2 strengths --------------------------------


def test_short_reactions_still_explicitly_allowed(
    dialogue_text: str,
) -> None:
    """v2 rhythm rule 7 preserved — short reactions are legitimate
    and load-bearing."""
    # v2 invariant #7 unchanged.
    assert "Short reactions" in dialogue_text or "Short reactions " in dialogue_text
    assert "Short turns are as valuable as long ones" in dialogue_text


def test_no_fixed_turn_count_introduced(dialogue_text: str) -> None:
    """v2 rule "Turn count is a pacing decision" must persist and
    v3 must not have added any prescriptive turn-count language."""
    # v2 anti-pattern present.
    assert "Turn count is a pacing decision" in dialogue_text
    # v3 introduced no counter-language.
    forbidden_patterns = [
        r"\bexactly\s+\d+\s+turns?\b",
        r"\bproduce\s+\d+\s+turns?\b",
        r"\bmust\s+have\s+\d+\s+turns?\b",
        r"\bgenerate\s+exactly\s+\d+\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, dialogue_text, re.IGNORECASE) is None, (
            f"contract accidentally introduced fixed turn count: "
            f"pattern {pattern!r} matched"
        )


def test_no_forced_alternation_introduced(dialogue_text: str) -> None:
    """v2 rule preserving A→B→B→A latitude must persist and v3
    must not have introduced any alternation requirement."""
    # v2 rule intact.
    assert "strict A→B→A→B alternation" in dialogue_text
    assert "Consecutive turns by the same speaker are legal" in dialogue_text
    # v3 introduced no counter-language.
    forbidden_patterns = [
        r"\bmust\s+alternate\b",
        r"\brequire\s+alternation\b",
        r"\balways\s+alternate\b",
        r"\bstrict\s+A[→\-]?B[→\-]?A\s+alternation\s+is\s+(required|mandatory)\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, dialogue_text, re.IGNORECASE) is None, (
            f"contract accidentally introduced forced alternation: "
            f"pattern {pattern!r} matched"
        )


def test_no_mandatory_conflict_or_comedy_skeleton_introduced(
    dialogue_text: str,
) -> None:
    """v3 must remain general-purpose. Collaboration is valid;
    humor is not required; no sitcom skeleton required."""
    # v2 rule "humor emerges" unchanged.
    assert "Humor emerges from interaction" in dialogue_text
    assert "Do not force jokes" in dialogue_text
    # v3 explicitly names collaboration as valid.
    assert "collaboration is a valid stance" in dialogue_text.lower() or \
        "collaboration is valid" in dialogue_text
    # v3 explicitly disclaims required argument/hostility.
    assert "does NOT mean every scene requires hostility" in dialogue_text
    # No new mandatory-shape language introduced.
    forbidden_patterns = [
        r"\bmust\s+contain\s+a\s+joke\b",
        r"\bmust\s+contain\s+conflict\b",
        r"\bevery\s+scene\s+must\s+be\s+funny\b",
        r"\bsetup\s*[-→]+\s*conflict\s*[-→]+\s*punchline\b.*\brequired\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, dialogue_text, re.IGNORECASE) is None, (
            f"contract accidentally introduced mandatory sitcom "
            f"skeleton: pattern {pattern!r} matched"
        )
    # v2's narrative-shape menu is still presented as "pick whichever
    # fits" — never as a required skeleton.
    assert "NARRATIVE SHAPES" in dialogue_text
    assert "no mandatory skeleton" in dialogue_text


# ---- 10, 11. Standalone + long_form byte-stability ------------


def test_standalone_contract_is_byte_stable() -> None:
    """v3 must NOT change standalone contract text. If this hash
    fails, the slice widened beyond its scope — bump/split the
    change instead of updating the snapshot silently."""
    text = WritingContract.for_shape("standalone")
    assert _sha256(text) == _STANDALONE_SHA256, (
        f"standalone contract SHA-256 changed: {_sha256(text)!r} "
        f"vs pinned {_STANDALONE_SHA256!r}. If this is intentional, "
        f"bump WRITING_CONTRACT_VERSION and update the snapshot in "
        f"this test in the same commit."
    )


def test_long_form_contract_with_budgets_is_byte_stable() -> None:
    """v3 must NOT change the long_form contract text. Pin the
    hash for the canonical (target_duration=60, budgets set) call
    shape used across the arc."""
    text = WritingContract.for_shape(
        "long_form",
        target_duration_seconds=60,
        char_budget=(500, 400, 600),
        word_budget=(90, 70, 110),
    )
    assert _sha256(text) == _LONG_FORM_60_500_SHA256, (
        f"long_form (60s, budgeted) contract SHA-256 changed: "
        f"{_sha256(text)!r} vs pinned {_LONG_FORM_60_500_SHA256!r}."
    )


def test_long_form_contract_bare_is_byte_stable() -> None:
    """No-budget call shape (used when caller supplies budgets in
    the outer prompt instead of the contract block itself) is also
    pinned so future callers exercising this branch don't drift."""
    text = WritingContract.for_shape("long_form")
    assert _sha256(text) == _LONG_FORM_BARE_SHA256, (
        f"long_form (bare) contract SHA-256 changed: "
        f"{_sha256(text)!r} vs pinned {_LONG_FORM_BARE_SHA256!r}."
    )


# ---- Companion sanity checks (not on the checklist but cheap) --


def test_dialogue_contract_still_carries_v2_invariants(
    dialogue_text: str,
) -> None:
    """The v3 slice is additive — every v2 invariant must survive
    verbatim so per-invariant snapshot regressions still fire."""
    for marker in [
        "Each character remains recognizably themselves",
        "Characters respond to each other",
        "Every turn advances the interaction",
        "Avoid repetitive agreement",
        "Disagreement and correction are allowed",
        "Humor emerges from interaction",
        "One coherent arc",
        "Deliberate ending",
    ]:
        assert marker in dialogue_text, f"v2 invariant lost: {marker!r}"


def test_dialogue_watchability_block_appears_after_invariants(
    dialogue_text: str,
) -> None:
    """Section order matters — invariants come first (the "must
    hold" gates), then the watchability paragraph guidance, then
    the anti-patterns. LLM reads top-down; putting watchability
    between the gates and the prohibitions gives it the framing
    context before the anti-patterns land."""
    invariants_idx = dialogue_text.index("DIALOGUE INVARIANTS")
    watchability_idx = dialogue_text.index("DIALOGUE WATCHABILITY")
    anti_patterns_idx = dialogue_text.index("DIALOGUE ANTI-PATTERNS")
    assert invariants_idx < watchability_idx < anti_patterns_idx
