"""SESSION 259 — Writing Contract v4 continuity-slice tests.

Deterministic contract-shape tests for the SESSION 259 continuity slice.
Every assert is a plain string / hash check against the return of
``WritingContract.for_shape(...)``; no DB, no LLM, no fixtures beyond
module-level constants.

Coverage matches the operator's 19-point checklist from the continuity
slice brief:

1.  ``WRITING_CONTRACT_VERSION == 4``.
2.  dialogue_scene contract includes the causal-chain invariant.
3.  contract explicitly says topic relevance alone is insufficient.
4.  the movable-line writer-test heuristic is present.
5.  new concrete objects/scenarios require prior setup, unresolved need,
    causal consequence, or explicit pivot.
6.  explicit pivots remain legal.
7.  collaboration/agreement remain legal.
8.  jokes/riffs remain legal when causally connected.
9.  strict alternation is still NOT required.
10. disagreement is NOT required.
11. fixed turn count is NOT introduced.
12. minimum line length is NOT introduced.
13. v3 framework-recitation protection remains intact.
14. v3 role-summary protection remains intact.
15. v3 mutual-synthesis-ending protection remains intact.
16. v3 end-on-a-moment rule remains intact.
17. v3 short-reaction allowance remains intact.
18. standalone contract text remains byte-stable (SHA-256 snapshot).
19. long_form contract text remains byte-stable (SHA-256 snapshot).

The v3 test suite (``test_writing_contract_v3.py``) is preserved because
every v3 assertion remains true under v4 — v4 is strictly additive on
``_DIALOGUE_INVARIANTS_BLOCK``. That file's version assertion has been
updated to expect 4 in the same commit as this file.
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
# Captured at v4 commit. Identical to the v3 snapshots because the
# v4 slice only touches ``_DIALOGUE_INVARIANTS_BLOCK``. If either
# hash changes, the slice widened beyond its scope.

_STANDALONE_SHA256 = (
    "a82955c6a34c20300c79ea695a05744b464f5cebcb5f09be964f3eda4fd6891f"
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


def test_writing_contract_version_current() -> None:
    """SESSION 259 continuity slice bumped 3 → 4; SESSION 269
    §15 bumped 4 → 5 (solo_scene shape); SESSION 271 §187 bumped
    5 → 6 (universal audience-aware invariant on solo_scene only).
    The dialogue-scene contract text this test file exercises
    remains byte-stable across every bump — see the SHA-snapshot
    suite in ``test_writing_contract_v3.py``."""
    assert WRITING_CONTRACT_VERSION == 6
    assert isinstance(WRITING_CONTRACT_VERSION, int)


# ---- 2. Causal-chain invariant present -------------------------


def test_dialogue_contract_contains_causal_chain_invariant(
    dialogue_text: str,
) -> None:
    """The load-bearing v4 addition. Must sit inside the invariants
    block (top-of-contract gates) — not merely in a soft-guidance
    block downstream."""
    # Rule title is present.
    assert "Causal chain" in dialogue_text
    # Core semantic: turns arise from what the last speaker did, not
    # from being topic-adjacent.
    assert "arise from the conversational state" in dialogue_text
    # Sits inside the invariants block, before watchability and
    # anti-patterns (LLM reads top-down; invariants are gates).
    invariants_idx = dialogue_text.index("DIALOGUE INVARIANTS")
    watchability_idx = dialogue_text.index("DIALOGUE WATCHABILITY")
    causal_idx = dialogue_text.index("Causal chain")
    assert invariants_idx < causal_idx < watchability_idx, (
        "Causal-chain invariant must sit inside the invariants block, "
        "before the watchability block (structural precedence)"
    )
    # Rule menu of legitimate response mechanisms is present so the
    # LLM can see the range without narrowing to just answer/challenge.
    for mechanism in [
        "answer a question",
        "challenge a claim",
        "correct something",
        "build on what was said",
        "reframe it",
        "escalate it",
        "react to a consequence",
        "call back to something",
    ]:
        assert mechanism in dialogue_text, (
            f"causal-chain mechanism missing: {mechanism!r}"
        )


# ---- 3. Topic relevance alone is not enough --------------------


def test_causal_chain_says_topic_relevance_alone_insufficient(
    dialogue_text: str,
) -> None:
    """Distinction between TOPIC relevance and CONVERSATIONAL response
    is the key semantic. Without this clause, the rule reads as
    "stay on topic" which is already implicit in every existing rule."""
    assert "overall TOPIC is not enough" in dialogue_text
    # And the label for what topic relevance actually is.
    assert "topic adjacency" in dialogue_text
    assert "not conversational response" in dialogue_text


# ---- 4. Movable-line writer-side test --------------------------


def test_causal_chain_carries_movable_line_writer_test(
    dialogue_text: str,
) -> None:
    """The heuristic that gives writers (and the LLM) a self-check.
    Without a heuristic the rule is aspirational; with it, the LLM
    has an operational filter to apply per line."""
    # Test name marker.
    assert "Writer-side test" in dialogue_text
    # The mechanic — moveability implies looseness.
    assert "moved after several different earlier turns" in dialogue_text
    # The conclusion the test yields.
    assert "not responding to the scene" in dialogue_text


# ---- 5. New concrete objects need setup / need / consequence / pivot


def test_causal_chain_requires_new_objects_to_be_earned(
    dialogue_text: str,
) -> None:
    """The specific b75a9dba failure mode: turn 6 introduced 'a tiny
    agent to sort parts' with zero prior setup. v4 must forbid the
    unmarked jump."""
    # The class of things governed.
    assert "New concrete objects, experiments, examples, scenarios" in dialogue_text
    # All four legitimate justifications.
    assert "grow naturally from something already established" in dialogue_text
    assert "answer an unresolved need or question" in dialogue_text
    assert "follow from an action or decision already taken" in dialogue_text
    assert "explicitly acknowledge that the conversation is changing direction" in dialogue_text
    # The core rule shorthand.
    assert "A pivot is allowed; an unmarked jump is not" in dialogue_text


# ---- 6. Explicit pivots remain legal ----------------------------


def test_explicit_pivots_remain_legal(dialogue_text: str) -> None:
    """v4 must not read as 'never change subject'. Explicit pivots
    (topic changes that are named as such) are always allowed."""
    # The permission clause is present.
    assert "A pivot is allowed" in dialogue_text
    # Escape mechanism: explicit acknowledgment legitimizes any pivot.
    assert "explicitly acknowledge that the conversation is changing direction" in dialogue_text


# ---- 7. Collaboration and agreement remain legal ---------------


def test_collaboration_and_agreement_remain_legal(
    dialogue_text: str,
) -> None:
    """The v4 rule must not read as 'characters must clash to be
    causally connected'. Collaboration / agreement / jokes / riffs
    are legal when caused by the scene state."""
    # v4's explicit non-requirement of hostility (in the causal-chain
    # rule itself).
    assert "does NOT require disagreement, hostility" in dialogue_text
    # v4's explicit affirmation that agreement / collaboration remain
    # valid when arising from scene state.
    assert (
        "agreement, collaboration, jokes, riffs, interruptions, "
        "and short reactions remain valid when they arise from the "
        "scene state"
    ) in dialogue_text
    # v3 watchability rule 1 said collaboration is a valid stance —
    # that must still be present (unchanged from v3).
    assert (
        "collaboration is a valid stance"
        in dialogue_text.lower()
        or "collaboration is valid" in dialogue_text
    )


# ---- 8. Jokes / riffs allowed when causally connected -----------


def test_jokes_and_riffs_allowed_when_causally_connected(
    dialogue_text: str,
) -> None:
    """v3's 'humor emerges from interaction' rule remains, plus v4
    explicitly names jokes and riffs as valid response mechanisms."""
    # v3's humor rule intact.
    assert "Humor emerges from interaction" in dialogue_text
    assert "Do not force jokes" in dialogue_text
    # v4 names them as legitimate response shapes.
    assert "jokes, riffs" in dialogue_text


# ---- 9. Strict alternation not required (v4 does not tighten) ---


def test_causal_chain_does_not_introduce_forced_alternation(
    dialogue_text: str,
) -> None:
    """v4 must preserve the existing A→B→B→A latitude. The rule
    must explicitly disclaim alternation as a requirement, and
    must not accidentally introduce alternation language."""
    # v4 explicit disclaimer.
    assert "strict alternation" in dialogue_text
    # v3 rule preserved.
    assert "strict A→B→A→B alternation" in dialogue_text
    assert "Consecutive turns by the same speaker are legal" in dialogue_text
    # No accidental alternation requirement introduced anywhere.
    forbidden_patterns = [
        r"\bmust\s+alternate\b",
        r"\brequire\s+alternation\b",
        r"\balways\s+alternate\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, dialogue_text, re.IGNORECASE) is None, (
            f"v4 accidentally introduced forced alternation: "
            f"pattern {pattern!r} matched"
        )


# ---- 10. Disagreement not required ------------------------------


def test_causal_chain_does_not_require_disagreement(
    dialogue_text: str,
) -> None:
    """v4 explicit disclaimer: causation ≠ conflict. Agreement can
    still be causally continuous."""
    assert "does NOT require disagreement, hostility" in dialogue_text
    # v3 watchability rule 1 disclaimer preserved.
    assert "does NOT mean every scene requires hostility" in dialogue_text
    # v3 invariant 5 preserved (disagreement is permitted, not required).
    assert "Disagreement and correction are allowed" in dialogue_text
    # No accidental "must disagree" language.
    forbidden_patterns = [
        r"\bmust\s+disagree\b",
        r"\brequires?\s+conflict\b",
        r"\bevery\s+turn\s+must\s+challenge\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, dialogue_text, re.IGNORECASE) is None, (
            f"v4 accidentally introduced mandatory disagreement: "
            f"pattern {pattern!r} matched"
        )


# ---- 11. No fixed turn count introduced -------------------------


def test_causal_chain_does_not_introduce_fixed_turn_count(
    dialogue_text: str,
) -> None:
    """v4 must preserve v2/v3's 'turn count is a pacing decision'
    rule. No count-prescriptive language added."""
    assert "fixed turn counts" in dialogue_text  # v4 disclaimer
    assert "Turn count is a pacing decision" in dialogue_text  # v2 rule
    forbidden_patterns = [
        r"\bexactly\s+\d+\s+turns?\b",
        r"\bproduce\s+\d+\s+turns?\b",
        r"\bmust\s+have\s+\d+\s+turns?\b",
        r"\bgenerate\s+exactly\s+\d+\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, dialogue_text, re.IGNORECASE) is None, (
            f"v4 accidentally introduced fixed turn count: "
            f"pattern {pattern!r} matched"
        )


# ---- 12. No minimum line length introduced ----------------------


def test_causal_chain_does_not_introduce_line_length_floor(
    dialogue_text: str,
) -> None:
    """v4 must preserve v2/v3's short-reactions-are-legitimate
    rule. Explicitly disclaimed inside the causal-chain rule too."""
    # v4 explicit non-requirement.
    assert "every turn being long" in dialogue_text
    # v3 rule preserved.
    assert "Short turns are as valuable as long ones" in dialogue_text
    # No accidental length floor.
    forbidden_patterns = [
        r"\bminimum\s+\d+\s+(chars?|characters|words?)\b",
        r"\bat\s+least\s+\d+\s+(chars?|characters|words?)\s+per\s+turn\b",
        r"\bno\s+turn\s+shorter\s+than\b",
    ]
    for pattern in forbidden_patterns:
        assert re.search(pattern, dialogue_text, re.IGNORECASE) is None, (
            f"v4 accidentally introduced minimum line length: "
            f"pattern {pattern!r} matched"
        )


# ---- 13. v3 framework-recitation protection intact --------------


def test_v3_framework_recitation_protection_intact(
    dialogue_text: str,
) -> None:
    """v3's (framework recitation) anti-pattern must remain word-for-
    word — v4 is additive on invariants only."""
    assert "framework recitation" in dialogue_text
    assert "belongs in your knowledge, not in your mouth" in dialogue_text
    assert "demonstrates step 3" in dialogue_text
    assert "EXPLICITLY asks the characters to teach or explain" in dialogue_text


# ---- 14. v3 role-summary protection intact ----------------------


def test_v3_role_summary_protection_intact(dialogue_text: str) -> None:
    """v3's (role summary) anti-pattern must remain word-for-word."""
    assert "role summary" in dialogue_text
    assert "You bring momentum" in dialogue_text
    assert "I bring the checklist" in dialogue_text
    assert "Together we get answers" in dialogue_text
    assert "self-description dressed as dialogue" in dialogue_text


# ---- 15. v3 mutual-synthesis ending protection intact -----------


def test_v3_mutual_synthesis_ending_protection_intact(
    dialogue_text: str,
) -> None:
    """v3's (mutual-synthesis ending) anti-pattern must remain word-
    for-word."""
    assert "mutual-synthesis ending" in dialogue_text
    assert "restates the lesson" in dialogue_text
    assert "ending stub" in dialogue_text
    assert (
        "Let the scene finish while something is still happening"
        in dialogue_text
    )


# ---- 16. v3 end-on-a-moment rule intact -------------------------


def test_v3_end_on_a_moment_rule_intact(dialogue_text: str) -> None:
    """v3 watchability rule 5 must remain word-for-word."""
    assert "END ON A MOMENT, NOT A SUMMARY" in dialogue_text
    for ending in [
        "reaction",
        "decision",
        "reveal",
        "callback",
        "escalation",
        "unresolved hook",
    ]:
        assert ending in dialogue_text, f"missing ending option: {ending!r}"


# ---- 17. v3 short-reaction allowance intact ---------------------


def test_v3_short_reaction_allowance_intact(dialogue_text: str) -> None:
    """v2 rhythm rule 7 (short reactions are valid) must remain."""
    assert "Short reactions" in dialogue_text
    assert "Short turns are as valuable as long ones" in dialogue_text


# ---- 18. standalone contract text byte-stable -------------------


def test_standalone_contract_text_byte_stable_under_v4() -> None:
    """v4 must NOT change standalone contract text. If this hash
    fails, the slice widened beyond its dialogue_scene scope."""
    text = WritingContract.for_shape("standalone")
    actual = _sha256(text)
    assert actual == _STANDALONE_SHA256, (
        f"standalone contract SHA-256 changed under v4 bump: "
        f"{actual!r} vs pinned {_STANDALONE_SHA256!r}. v4 was "
        f"supposed to touch _DIALOGUE_INVARIANTS_BLOCK only."
    )


# ---- 19. long_form contract text byte-stable --------------------


def test_long_form_contract_text_byte_stable_under_v4() -> None:
    """v4 must NOT change the long_form contract text (bare-call
    shape). If this hash fails, the slice widened beyond its
    dialogue_scene scope."""
    text = WritingContract.for_shape("long_form")
    actual = _sha256(text)
    assert actual == _LONG_FORM_BARE_SHA256, (
        f"long_form (bare) contract SHA-256 changed under v4 bump: "
        f"{actual!r} vs pinned {_LONG_FORM_BARE_SHA256!r}. v4 was "
        f"supposed to touch _DIALOGUE_INVARIANTS_BLOCK only."
    )
