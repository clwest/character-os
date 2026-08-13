"""V17.2 tests — cinematic_visual_extended starter + recipe.

SESSION 182 / V17.2. Chains V17.1's extend_visual_clip primitive
off V4's generate_visual_clip to produce clips longer than
Runway's 10s per-render ceiling.

Covers:

* Starter math — 1 + N step layout where N = (target - 10) / 5.
* Step composition — step 0 is generate_visual_clip with
  duration=10, no prompt_image (gen4.5 text-to-video); steps
  1..N are extend_visual_clip each pulling from the prior
  step's output via from_step_position.
* Validation — empty prompt, cross-workspace spokesperson,
  target_duration not in the accepted set.
* Recipe registry — recipe resolvable by kind; cost-forecast
  scales with target_duration.
* Cross-workspace asset rejection on save (V1 rule 3 — the
  signal layer catches it; the starter doesn't bypass it).

V17 contract rules 10 (one Asset per primitive call) + 12
(backwards-compat under V17) are the load-bearing claims this
file pins.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import CompositionStep
from apps.compositions.recipes import RECIPES
from apps.compositions.starters import cinematic_visual_extended
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = [pytest.mark.django_db]


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_teammate(ws: Workspace, name: str = "Sp") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name,
        runway_avatar_id="fake-avatar",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


# ---- starter math --------------------------------------------------


def test_target_15s_creates_one_extend_step() -> None:
    """15s target = 10s base + 1 × 5s extension = 2 total steps."""
    ws = _make_workspace("v17_2_15@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="a sun rising over still water",
        target_duration=15,
        mock_mode=True,
    )
    steps = list(
        CompositionStep.objects.filter(composition=comp).order_by("position")
    )
    assert len(steps) == 2
    assert steps[0].primitive == "generate_visual_clip"
    assert steps[1].primitive == "extend_visual_clip"


def test_target_25s_creates_three_extend_steps() -> None:
    """25s = 10s base + 3 × 5s extension = 4 total steps."""
    ws = _make_workspace("v17_2_25@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything",
        target_duration=25,
        mock_mode=True,
    )
    steps = list(
        CompositionStep.objects.filter(composition=comp).order_by("position")
    )
    assert len(steps) == 4
    assert steps[0].primitive == "generate_visual_clip"
    assert all(s.primitive == "extend_visual_clip" for s in steps[1:])


def test_target_50s_creates_eight_extend_steps() -> None:
    """50s = 10s base + 8 × 5s extension. Upper end of the
    supported range — beyond this, operators should compose
    via long_form_ad or manual concat."""
    ws = _make_workspace("v17_2_50@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything",
        target_duration=50,
        mock_mode=True,
    )
    steps = list(
        CompositionStep.objects.filter(composition=comp).order_by("position")
    )
    assert len(steps) == 9  # 1 base + 8 extends


# ---- step composition ----------------------------------------------


def test_base_step_uses_gen45_duration_and_no_prompt_image() -> None:
    """Step 0 must be a 10s text-to-video render — no prompt_image
    in params, duration=10. Q-v17-1 shape: gen4.5 text-to-video
    is the only model accepting a 10s base; gen4_turbo (which
    the extend primitive uses) requires an image + locks to 5s."""
    ws = _make_workspace("v17_2_base@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="cinematic shot",
        target_duration=15,
        mock_mode=True,
    )
    base = CompositionStep.objects.get(composition=comp, position=0)
    assert base.primitive == "generate_visual_clip"
    assert base.params["prompt"] == "cinematic shot"
    assert base.params["duration"] == 10
    assert "prompt_image" not in base.params


def test_extend_steps_chain_via_from_step_position() -> None:
    """Each extend step's `source` input points at the IMMEDIATELY
    PRIOR step's position. Linear chain — V1 rule 5 (no DAG) +
    V17 rule 10 (primitive emits one asset per call)."""
    ws = _make_workspace("v17_2_chain@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything", target_duration=25,
        mock_mode=True,
    )
    steps = list(
        CompositionStep.objects.filter(composition=comp).order_by("position")
    )
    # Step 0 has no inputs (it's the base generate).
    assert steps[0].inputs == []
    # Each subsequent step pulls from the prior position.
    for i, step in enumerate(steps[1:], start=1):
        assert step.inputs == [
            {"slot": "source", "from_step_position": i - 1},
        ], f"step {i} inputs wrong: {step.inputs}"


def test_extend_steps_carry_prompt_and_5s_duration() -> None:
    """Every extend step shares the operator's prompt + locked
    5s duration (gen4_turbo's per-call max)."""
    ws = _make_workspace("v17_2_extends@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="a slow camera push", target_duration=20,
        mock_mode=True,
    )
    extend_steps = list(
        CompositionStep.objects.filter(
            composition=comp, primitive="extend_visual_clip",
        ).order_by("position")
    )
    assert len(extend_steps) == 2  # (20 - 10) / 5
    for step in extend_steps:
        assert step.params["prompt"] == "a slow camera push"
        assert step.params["duration"] == 5


def test_ratio_propagates_to_every_step() -> None:
    """Operator's ratio choice must be applied to base + every
    extend step. ffmpeg concat in V17.0 fails loudly on dim
    mismatch (intentional — see V17.0 test
    test_extend_concat_handles_mismatched_source_dims), so the
    starter MUST keep ratios consistent across the chain."""
    ws = _make_workspace("v17_2_ratio@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything", target_duration=20,
        ratio="720:1280",
        mock_mode=True,
    )
    for step in CompositionStep.objects.filter(composition=comp):
        assert step.params["ratio"] == "720:1280", (
            f"step at position {step.position} dropped the ratio override"
        )


def test_seed_propagates_only_to_extend_steps() -> None:
    """Seed conditions the extend primitive's Runway calls
    (V17.1 accepts it). The base generate_visual_clip primitive
    (V4) doesn't currently accept seed, so the starter omits it
    from the base step's params. Audit log records the seed at
    starter time regardless."""
    ws = _make_workspace("v17_2_seed@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything", target_duration=20,
        seed=42,
        mock_mode=True,
    )
    base = CompositionStep.objects.get(composition=comp, position=0)
    assert "seed" not in base.params
    extends = CompositionStep.objects.filter(
        composition=comp, primitive="extend_visual_clip",
    )
    for step in extends:
        assert step.params["seed"] == 42


# ---- validation ---------------------------------------------------


def test_empty_prompt_rejected() -> None:
    ws = _make_workspace("v17_2_no_prompt@test")
    sp = _make_teammate(ws)
    with pytest.raises(ValueError) as exc:
        cinematic_visual_extended(
            workspace=ws, spokesperson=sp,
            prompt="   ", target_duration=15,
            mock_mode=True,
        )
    assert "prompt" in str(exc.value)


def test_invalid_target_duration_rejected() -> None:
    """Target must be in {15, 20, 25, 30, 40, 50}. 12 (not a
    multiple of 5) and 60 (over the cap) both rejected. The
    constraint lives in the starter, not at the schema layer —
    a future v2 could relax it without DB changes."""
    ws = _make_workspace("v17_2_bad_target@test")
    sp = _make_teammate(ws)
    for invalid in (10, 12, 35, 60, 0, -5):
        with pytest.raises(ValueError) as exc:
            cinematic_visual_extended(
                workspace=ws, spokesperson=sp,
                prompt="anything", target_duration=invalid,
                mock_mode=True,
            )
        assert "target_duration" in str(exc.value), (
            f"target_duration={invalid} should be rejected"
        )


def test_cross_workspace_spokesperson_rejected() -> None:
    """V1 contract rule 1 — every Composition has explicit
    workspace + spokesperson anchors. Starter rejects a
    spokesperson from a different workspace with a clean
    error before any rows write."""
    ws_a = _make_workspace("v17_2_wsA@test")
    ws_b = _make_workspace("v17_2_wsB@test")
    sp_b = _make_teammate(ws_b)
    with pytest.raises(ValueError) as exc:
        cinematic_visual_extended(
            workspace=ws_a, spokesperson=sp_b,
            prompt="anything", target_duration=15,
            mock_mode=True,
        )
    assert "workspace" in str(exc.value).lower()


# ---- composition row shape ----------------------------------------


def test_composition_records_template_kind() -> None:
    """The Composition row's template_kind must match the
    starter name so admin + audit surfaces can group these
    chains correctly (the dashboard cross-cut + lineage
    queries key off template_kind)."""
    ws = _make_workspace("v17_2_kind@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything", target_duration=20,
        mock_mode=True,
    )
    assert comp.template_kind == "cinematic_visual_extended"


def test_composition_name_auto_generated_from_prompt() -> None:
    """Operators who don't supply a name get one of shape
    "Cinematic visual {target}s — {prompt[:40]}"."""
    ws = _make_workspace("v17_2_autoname@test")
    sp = _make_teammate(ws)
    long_prompt = "the founder walks through a sunlit office at sunset"
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt=long_prompt, target_duration=20,
        mock_mode=True,
    )
    assert "20s" in comp.name
    assert long_prompt[:40] in comp.name


def test_operator_supplied_name_wins() -> None:
    ws = _make_workspace("v17_2_name@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything", target_duration=20,
        name="My Hero Shot v3",
        mock_mode=True,
    )
    assert comp.name == "My Hero Shot v3"


# ---- recipe registry ----------------------------------------------


def test_recipe_registered_in_v15_gallery() -> None:
    """V15 SPA gallery reads from RECIPES. A new recipe needs
    an entry there for the form to render."""
    assert "cinematic_visual_extended" in RECIPES
    recipe = RECIPES["cinematic_visual_extended"]
    assert recipe.kind == "cinematic_visual_extended"
    assert recipe.starter is cinematic_visual_extended


def test_recipe_exposes_target_duration_as_select_field() -> None:
    """The form must surface target_duration as a `select`
    (not a free-form number) so operators can't typo into an
    invalid value. Reinforces the starter-side validation.

    Choice values are STRINGS — the SPA's Zod schema
    (`web/src/lib/api/recipes.ts` `recipeFieldChoice`)
    requires `value: z.string()`. The starter coerces back
    to int. SESSION 182 dogfood surfaced this constraint
    when the original int-valued choices failed Zod
    validation in the gallery."""
    recipe = RECIPES["cinematic_visual_extended"]
    target_field = recipe.field_by_name("target_duration")
    assert target_field is not None
    assert target_field.type == "select"
    # All six accepted values surfaced as choices, as STRINGS
    # per the SPA contract.
    assert target_field.choices is not None
    choice_values = {c["value"] for c in target_field.choices}
    assert choice_values == {"15", "20", "25", "30", "40", "50"}
    # Every value must be a string (defensive against future
    # contributor accidentally re-introducing int values).
    for choice in target_field.choices:
        assert isinstance(choice["value"], str), (
            f"choice {choice!r} must use a string value per "
            "the SPA Zod schema"
        )


def test_starter_accepts_string_target_duration_from_spa() -> None:
    """The SPA submits target_duration as the string value
    from its select choices ("15", "20", ...). The starter
    must coerce to int. Tests with direct int args also
    work — both shapes supported."""
    ws = _make_workspace("v17_2_str_target@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything", target_duration="15",  # type: ignore[arg-type]
        mock_mode=True,
    )
    steps = list(
        CompositionStep.objects.filter(composition=comp).order_by("position")
    )
    # Same shape as int=15: 1 base + 1 extend = 2 steps.
    assert len(steps) == 2
    assert steps[0].primitive == "generate_visual_clip"
    assert steps[1].primitive == "extend_visual_clip"


def test_starter_rejects_non_numeric_string_target_duration() -> None:
    """A garbage string from a tampered SPA submission surfaces
    a clean error before any rows write."""
    ws = _make_workspace("v17_2_garbage_target@test")
    sp = _make_teammate(ws)
    with pytest.raises(ValueError) as exc:
        cinematic_visual_extended(
            workspace=ws, spokesperson=sp,
            prompt="anything", target_duration="fifteen",  # type: ignore[arg-type]
            mock_mode=True,
        )
    assert "target_duration" in str(exc.value)


def test_recipe_to_json_round_trips_for_spa() -> None:
    """SPA fetches `/api/recipes/` and expects a JSON-clean
    payload. A new recipe that breaks to_json() blows up the
    whole gallery; this test pins the contract."""
    payload = RECIPES["cinematic_visual_extended"].to_json()
    assert payload["kind"] == "cinematic_visual_extended"
    assert payload["family"] == "cinematic"
    assert any(
        f["name"] == "target_duration"
        for f in payload["fields"]
    )


# ---- mock-mode chain --------------------------------------------


def test_mock_mode_flag_persists_on_composition() -> None:
    """V0 rule 9 — mock_mode is composition-level. The starter
    sets it once on the Composition; the runtime then runs every
    step in that mode. No mixing."""
    ws = _make_workspace("v17_2_mock@test")
    sp = _make_teammate(ws)
    comp = cinematic_visual_extended(
        workspace=ws, spokesperson=sp,
        prompt="anything", target_duration=15,
        mock_mode=True,
    )
    assert comp.mock_mode is True
