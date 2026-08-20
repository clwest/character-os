"""SESSION 269 §15 — solo_scene writing contract tests.

Deterministic contract-shape tests for the SESSION 269 §15 slice.
Every assert is a plain string / hash check against the return of
``WritingContract.for_shape("solo_scene", ...)``; no DB, no LLM,
no fixtures beyond module-level constants.

Coverage matches the §14 acceptance list:

1. `WritingContract.for_shape("solo_scene", ...)` returns a string
   containing every scene-physics invariant from §14.8:
   SINGLE ACTIVE CHARACTER, SINGLE PRESENT MOMENT, PLANS REMAIN
   PLANS, MEMORY AS BACKGROUND, END ON A MOMENT, PRESERVE
   CREATIVE FREEDOM.
2. Concrete demonstration pairs survive (GOOD / BAD line examples
   the §14 doc + §11 findings require the LLM to see literally).
3. Solo-scene narrative-shape menu present + does NOT include the
   long-form shapes that caused §11 temporal compression
   (story → realization / mistake → lesson / experiment →
   outcome).
4. Length + shape blocks handle both budgeted and unbudgeted
   invocations.
5. WRITING_CONTRACT_VERSION == 6 (recorded by version stamp on
   every §15 Composition; bumped from 5 in SESSION 271 §187 when
   the universal AUDIENCE-AWARE COMMUNICATION invariant landed).
6. long_form + standalone + dialogue_scene byte-stability is
   proven in ``test_writing_contract_v3.py`` — this module does
   not duplicate those SHA snapshots but references them by
   xfailing on regression (delegated to the v3 suite).
"""
from __future__ import annotations

import pytest

from character_os.writing_contract import (
    WRITING_CONTRACT_VERSION,
    WritingContract,
)


@pytest.fixture(scope="module")
def solo_text() -> str:
    """Bare invocation — matches how avatar_speech's non-duration
    path or a caller without a budget would receive the shape."""
    return WritingContract.for_shape("solo_scene")


@pytest.fixture(scope="module")
def solo_text_budgeted() -> str:
    """Budgeted invocation — matches how
    ``synthesize_with_duration_gate`` passes shape + budget on
    Episode-attached talking_head renders."""
    return WritingContract.for_shape(
        "solo_scene",
        target_duration_seconds=90,
        char_budget=(1200, 900, 1500),
        word_budget=(200, 150, 250),
    )


# ---- 1. Scene-physics invariants -------------------------------


def test_solo_contract_names_single_active_character(solo_text: str) -> None:
    """Direct fix for §11 finding — 'I call for Rivet' / 'we line
    up a reprint' turns a Patch-only Episode into an off-screen
    two-hander. The contract must forbid this explicitly."""
    assert "SINGLE ACTIVE CHARACTER" in solo_text
    # The reference distinction from §14.8: history / relationships
    # / future intentions are OK; active participation is not.
    assert "HISTORY" in solo_text
    assert "RELATIONSHIPS" in solo_text
    assert "FUTURE INTENTIONS" in solo_text
    # Concrete example pair — both sides load-bearing so the LLM
    # sees exactly what fails.
    assert "if this gets weird, I'll call Rivet" in solo_text  # GOOD
    assert "I call for Rivet" in solo_text  # BAD
    assert "we line up a reprint" in solo_text  # BAD continuation
    # The failure mode named plainly.
    assert "off-screen two-hander" in solo_text


def test_solo_contract_bounds_scene_to_single_present_moment(
    solo_text: str,
) -> None:
    """§11 temporal-compression fix — the current scene depicts one
    bounded moment; multi-phase compression is forbidden."""
    assert "SINGLE PRESENT MOMENT" in solo_text
    # The specific compression sequence §11.5 flagged must be
    # named so the LLM sees the shape that fails.
    for phase in [
        "discovery",
        "running an experiment",
        "reaching a conclusion",
    ]:
        assert phase in solo_text, f"missing compression phase: {phase!r}"
    # The defer instruction.
    assert "Later outcomes belong in later Episodes" in solo_text


def test_solo_contract_plans_remain_plans(solo_text: str) -> None:
    """Establishing intent is legitimate; simulating outcomes
    inside the same script is not."""
    assert "PLANS REMAIN PLANS" in solo_text
    # Both concrete phrases from the §14.8 spec.
    assert "halfway through" in solo_text
    assert "we run it and it works" in solo_text


def test_solo_contract_treats_memory_as_background(solo_text: str) -> None:
    """Retrieved NarrativeMemory rows are context, NOT commands
    to reenact past events on-camera."""
    assert "MEMORY AS BACKGROUND, NOT COMMANDS" in solo_text
    assert "already knows happened" in solo_text
    assert "not a recap of the memory" in solo_text
    # Legitimate ways to reference memory (per §14.8) — the
    # 'recognize a pattern' + 'lingering state' examples must
    # survive.
    assert "recognize a pattern" in solo_text
    assert "lingering state" in solo_text


def test_solo_contract_ends_on_a_moment(solo_text: str) -> None:
    """Same END ON A MOMENT rule dialogue_scene has — no lesson
    summary, no philosophical conclusion, no retrospective wrap."""
    assert "END ON A MOMENT, NOT A SUMMARY" in solo_text
    for ending in [
        "decision",
        "reaction",
        "revealed hook",
        "unresolved question",
        "small win",
        "small loss",
    ]:
        assert ending in solo_text, f"missing ending option: {ending!r}"
    # The prohibition side.
    assert "lesson learned" in solo_text
    assert "retrospective conclusion" in solo_text


def test_solo_contract_preserves_creative_freedom(solo_text: str) -> None:
    """The five invariants above are about SCENE PHYSICS, not
    tone. Character voice / humor / opinions all remain."""
    assert "PRESERVE CREATIVE FREEDOM" in solo_text
    assert "SCENE PHYSICS" in solo_text
    assert "not about tone" in solo_text


# ---- 3. Narrative-shape menu -----------------------------------


def test_solo_contract_offers_scene_oriented_shape_menu(
    solo_text: str,
) -> None:
    """Solo-scene menu is scene-oriented (moment → reaction /
    discovery → intent / observation → resolve-or-defer /
    internal turn → decision / present dilemma → next step) —
    stays inside a single bounded moment."""
    for shape in [
        "moment → reaction",
        "discovery → intent",
        "observation → resolve-or-defer",
        "internal turn → decision",
        "present dilemma → next step",
    ]:
        assert shape in solo_text, f"missing scene-oriented shape: {shape!r}"


def test_solo_contract_does_not_include_long_form_arc_shapes(
    solo_text: str,
) -> None:
    """The long-form menu's story→realization / mistake→lesson /
    experiment→outcome shapes are the DIRECT CAUSE of §11
    temporal compression per §11.6. They MUST NOT appear in the
    solo_scene contract."""
    for forbidden in [
        "story → realization",
        "mistake → lesson",
        "experiment → outcome",
        "question → exploration → answer",
    ]:
        assert forbidden not in solo_text, (
            f"solo_scene must NOT include the long-form shape "
            f"{forbidden!r} — direct §11 compression risk"
        )


# ---- 4. Length + shape handling --------------------------------


def test_solo_contract_bare_invocation_has_no_length_numerics(
    solo_text: str,
) -> None:
    """Without budget kwargs, the LENGTH block delegates to the
    caller's system-prompt-supplied budget."""
    assert "LENGTH" in solo_text
    assert "Follow the character / word budget" in solo_text


def test_solo_contract_budgeted_invocation_carries_char_budget(
    solo_text_budgeted: str,
) -> None:
    """With budget kwargs, the LENGTH block interpolates the
    numbers so K6 sees the same accept/reject bounds the
    duration_contract enforces."""
    assert "approximately 90 seconds" in solo_text_budgeted
    assert "~1200 characters" in solo_text_budgeted
    assert "between 900 and 1500" in solo_text_budgeted
    assert "~200 words" in solo_text_budgeted


# ---- 5. Version stamp ------------------------------------------


def test_writing_contract_version_6() -> None:
    """§15 bumped the version 4 → 5. SESSION 271 §187 bumped 5 → 6
    to add the universal AUDIENCE-AWARE COMMUNICATION invariant to
    ``_solo_scene_contract`` (character-agnostic, retrieval-
    independent). Composition.writing_contract_version stamp records
    which contract shaped each render — audits can trace whether a
    given Composition ran under v4 (pre-§15), v5 (Episode-solo
    aware), or v6 (universal audience-aware)."""
    assert WRITING_CONTRACT_VERSION == 6


# ---- 5b. Universal AUDIENCE-AWARE COMMUNICATION invariant -------


def test_solo_contract_contains_universal_audience_aware_block(
    solo_text: str,
) -> None:
    """SESSION 271 §187 / v6 — the universal audience-aware
    invariant lives inside ``_solo_scene_contract`` as a
    character-agnostic block that fires on every solo_scene render.
    Retrieval-independent (no dependency on any KnowledgeDocument
    chunk being retrieved) and cast-independent (does not name
    Patch, Rivet, or any specific character).

    The wording was ratified clause-by-clause in Slice 9 §179.4
    against fox-baker / bear-coffee-shop / Patch / Rivet /
    unrelated-domain thought experiments. Any wording change is
    a v6 → v7 bump that must be a deliberate slice with fresh
    thought-experiment validation."""
    assert "AUDIENCE-AWARE COMMUNICATION" in solo_text
    # The framing clause — must call out "universal — applies to
    # every render" so the LLM understands it's not opt-in.
    assert "universal — applies to every render" in solo_text
    # The seven-dimension identity guard (§179.4 § 7-dim inventory).
    # These are the axes that MUST NOT vary with audience.
    for dimension in [
        "identity",
        "intelligence",
        "expertise",
        "humor",
        "personality",
        "factual grounding",
        "confidence",
    ]:
        assert dimension in solo_text, (
            f"universal audience-aware block missing identity "
            f"dimension: {dimension!r}"
        )
    # The four adaptation levers (§179.4) — technical depth,
    # vocabulary, examples, analogies. These ARE allowed to vary
    # with audience.
    for lever in ["technical depth", "vocabulary", "examples", "analogies"]:
        assert lever in solo_text, (
            f"universal audience-aware block missing adaptation "
            f"lever: {lever!r}"
        )
    # The listener-background anchor — the LLM must match to the
    # listener's likely background knowledge.
    assert "background knowledge" in solo_text


def test_solo_contract_audience_block_precedes_shape_menu(
    solo_text: str,
) -> None:
    """§187 placement — the universal audience-aware block sits
    between ``_SOLO_SCENE_INVARIANTS_BLOCK`` and
    ``_SOLO_SCENE_SHAPES_BLOCK`` so the LLM reads it as a
    top-of-contract gate alongside the other invariants, not as
    a downstream soft-guidance suggestion."""
    audience_idx = solo_text.find("AUDIENCE-AWARE COMMUNICATION")
    shapes_idx = solo_text.find("NARRATIVE SHAPES")
    invariants_idx = solo_text.find("INVARIANTS")
    assert audience_idx != -1, "audience-aware block missing"
    assert shapes_idx != -1, "shape menu missing"
    assert invariants_idx != -1, "invariants block missing"
    # Order: INVARIANTS → AUDIENCE-AWARE → SHAPES.
    assert invariants_idx < audience_idx < shapes_idx, (
        f"expected INVARIANTS < AUDIENCE-AWARE < SHAPES, got "
        f"invariants={invariants_idx} audience={audience_idx} "
        f"shapes={shapes_idx}"
    )


# ---- 6. Shape dispatch -----------------------------------------


def test_for_shape_dispatches_solo_scene_distinctly() -> None:
    """solo_scene must be a distinct branch from long_form and
    standalone — the same call site with the same duration must
    produce different text for each shape."""
    solo = WritingContract.for_shape(
        "solo_scene", target_duration_seconds=60,
        char_budget=(800, 600, 1000), word_budget=(132, 100, 165),
    )
    long_form = WritingContract.for_shape(
        "long_form", target_duration_seconds=60,
        char_budget=(800, 600, 1000), word_budget=(132, 100, 165),
    )
    standalone = WritingContract.for_shape("standalone")
    assert solo != long_form
    assert solo != standalone
    assert "SINGLE ACTIVE CHARACTER" in solo
    assert "SINGLE ACTIVE CHARACTER" not in long_form
    assert "SINGLE ACTIVE CHARACTER" not in standalone


# ---- 7. Regression: build_render_brief whitelist (§15 hotfix) ----


def test_build_render_brief_accepts_solo_scene_shape_with_duration() -> None:
    """SESSION 269 §15 hotfix regression — the pre-§15
    ``build_render_brief`` validation whitelisted only
    ``"standalone"`` and ``"long_form"``. Composition 04b95526
    failed at render time with ``ValueError: target_shape must
    be 'standalone' or 'long_form', got 'solo_scene'`` because
    the primitive correctly routed to solo_scene but the caller's
    input-guard rejected the shape. This test locks in the
    whitelist extension so a future refactor cannot silently
    revert it."""
    from unittest.mock import patch as mock_patch
    from character_os.script_synthesis import build_render_brief

    # Force-mock short-circuits the LLM + retrieval path so we
    # only exercise the whitelist branch. The test asserts that
    # calling build_render_brief with target_shape="solo_scene"
    # does NOT raise ValueError — before the hotfix it did.
    class _FakeTeammate:
        pk = 1
        id = 1
        name = "Patch"
        business_brief = "Workshop inventor."
        workspace = None
        universe = None
        universe_id = None
    tm = _FakeTeammate()

    with mock_patch(
        "character_os.script_synthesis._is_force_mock",
        return_value=True,
    ), mock_patch(
        "character_os.script_synthesis.retrieve_for_teammate",
        return_value=[],
    ):
        # Both duration-driven AND non-duration invocations must
        # succeed — the primitive's non-duration branch also
        # routes Episode-attached talking_head to solo_scene.
        result_with_duration = build_render_brief(
            tm, "topic", target_shape="solo_scene",
            target_duration_seconds=90,
        )
        assert result_with_duration.brief != ""
        result_no_duration = build_render_brief(
            tm, "topic", target_shape="solo_scene",
        )
        assert result_no_duration.brief != ""


def test_build_render_brief_rejects_unknown_target_shape() -> None:
    """The whitelist must still reject genuinely unknown shapes —
    the §15 hotfix expanded the allowed set to {standalone,
    long_form, solo_scene} but did NOT open it wide."""
    import pytest as _pytest
    from character_os.script_synthesis import build_render_brief

    class _FakeTeammate:
        pk = 1
        id = 1
        name = "x"
        business_brief = ""
    with _pytest.raises(ValueError, match="target_shape must be"):
        build_render_brief(_FakeTeammate(), "topic", target_shape="bogus")
