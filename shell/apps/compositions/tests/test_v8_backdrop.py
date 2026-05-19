"""V8 tests — talking_head_with_backdrop starter.

First multi-step starter composition. Combines V3
(generate_avatar_speech), V4 (generate_visual_clip), and V7
(composite_video kind=backdrop). No new primitives; the slice
ships entirely as a starter factory + tests.

Covers:

* Starter builds 3 steps with the right primitives, params,
  and from_step_position chaining.
* Validation: empty script / backdrop_prompt rejected;
  cross-workspace spokesperson rejected.
* end-to-end in mock-mode → COMPLETED composition whose
  final asset is the composite output (not any intermediate).
* use_knowledge propagates to the speech step.
* Cost estimation sums all three primitives.
* Backdrop sizing options propagate into the composite
  layout_spec.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.compositions.cost import (
    estimate_composition_cost,
)
from apps.compositions.models import (
    AssetType,
    CompositionStatus,
)
from apps.compositions.starters import (
    _EXTEND_BASE_DURATION_SECONDS,
    _EXTEND_SEGMENT_DURATION_SECONDS,
    _MAX_BACKDROP_CHAIN_LENGTH,
    _compute_backdrop_chain_length,
    _compute_extend_backdrop_chain_length,
    _estimate_avatar_speech_seconds,
    talking_head_with_backdrop,
)
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("_celery_eager"),
]


@pytest.fixture
def _celery_eager():
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str, name: str = "WS") -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_spokesperson(
    ws: Workspace,
    name: str = "Sp",
    avatar_id: str = "fake-avatar-for-v8",
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=avatar_id,
        portrait_path="https://fake.test/portrait.png",
        business_brief="A brand.",
    )


# ---- starter shape ------------------------------------------------


def test_starter_creates_three_steps_with_correct_primitives() -> None:
    ws = _make_workspace("v8shape@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="Hello from the backdrop.",
        backdrop_prompt="A neon-lit alley at night.",
        mock_mode=True,
    )
    assert c.template_kind == "talking_head_with_backdrop"
    steps = list(c.steps.all().order_by("position"))
    assert len(steps) == 3
    assert steps[0].primitive == "generate_visual_clip"
    assert steps[1].primitive == "generate_avatar_speech"
    assert steps[2].primitive == "composite_video"


def test_starter_step_params_carry_through() -> None:
    ws = _make_workspace("v8params@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="Tell viewers about coffee.",
        backdrop_prompt="A misty morning cafe terrace.",
        backdrop_ratio="1280:720",
        backdrop_duration=10,
        fg_width=280,
        margin_x=30, margin_y=50,
        use_knowledge=True,
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))

    # Backdrop step
    assert steps[0].params["prompt"] == "A misty morning cafe terrace."
    assert steps[0].params["ratio"] == "1280:720"
    assert steps[0].params["duration"] == 10

    # Speech step
    assert steps[1].params["script"] == "Tell viewers about coffee."
    assert steps[1].params["use_knowledge"] is True

    # Composite step
    spec = steps[2].params["layout_spec"]
    assert spec["kind"] == "backdrop"
    assert spec["options"]["fg_width"] == 280
    assert spec["options"]["margin_x"] == 30
    assert spec["options"]["margin_y"] == 50


def test_starter_composite_step_chains_to_earlier_outputs() -> None:
    """Step 2's inputs use from_step_position so the runtime
    resolves them at execute time. Background = step 0
    output; foreground = step 1 output."""
    ws = _make_workspace("v8chain@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="hi.", backdrop_prompt="alley.",
        mock_mode=True,
    )
    composite = c.steps.get(position=2)
    bg = composite.inputs[0]
    fg = composite.inputs[1]
    assert bg["slot"] == "background"
    assert bg["from_step_position"] == 0
    assert fg["slot"] == "foreground"
    assert fg["from_step_position"] == 1


def test_use_knowledge_default_is_false() -> None:
    ws = _make_workspace("v8know_default@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="hi.", backdrop_prompt="alley.",
        mock_mode=True,
    )
    speech = c.steps.get(position=1)
    assert speech.params["use_knowledge"] is False


def test_starter_omits_optional_backdrop_ratio_when_unset() -> None:
    """``ratio`` only lands in params when the operator passed
    it — media-engine's server-side default takes over otherwise.
    ``duration`` is always set explicitly (SESSION 179) so the
    backdrop chain length math has a known per-clip ceiling."""
    ws = _make_workspace("v8optional@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="hi.", backdrop_prompt="alley.",
        mock_mode=True,
    )
    backdrop_step = c.steps.get(position=0)
    assert "ratio" not in backdrop_step.params
    # SESSION 179 — duration is always present + defaults to 10
    # (gen4.5 max) so single-backdrop renders get the longest
    # possible per-clip motion before any chain math runs.
    assert backdrop_step.params["duration"] == 10


# ---- validation paths --------------------------------------------


def test_starter_rejects_empty_script() -> None:
    ws = _make_workspace("v8s_empty@test")
    sp = _make_spokesperson(ws)
    with pytest.raises(ValueError):
        talking_head_with_backdrop(
            workspace=ws, spokesperson=sp,
            script="   ", backdrop_prompt="alley.",
            mock_mode=True,
        )


def test_starter_rejects_empty_backdrop_prompt() -> None:
    ws = _make_workspace("v8b_empty@test")
    sp = _make_spokesperson(ws)
    with pytest.raises(ValueError):
        talking_head_with_backdrop(
            workspace=ws, spokesperson=sp,
            script="hi.", backdrop_prompt="   ",
            mock_mode=True,
        )


def test_starter_rejects_cross_workspace_spokesperson() -> None:
    ws_a = _make_workspace("v8xA@test", "A")
    ws_b = _make_workspace("v8xB@test", "B")
    foreign = _make_spokesperson(ws_b)
    with pytest.raises(ValueError):
        talking_head_with_backdrop(
            workspace=ws_a, spokesperson=foreign,
            script="hi.", backdrop_prompt="alley.",
            mock_mode=True,
        )


# ---- end-to-end mock-mode -----------------------------------------


def test_starter_executes_end_to_end_in_mock_mode() -> None:
    """The full three-step path runs through V2's runtime in
    mock-mode. Final asset is the composite output (not the
    intermediate clips)."""
    ws = _make_workspace("v8e2e@test")
    sp = _make_spokesperson(ws, name="Riggs")

    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="The founder's substantive take on coffee.",
        backdrop_prompt="A warm morning cafe with sunlight streaming through windows.",
        mock_mode=True,
    )

    result = execute_composition.apply(args=[str(c.pk)]).get()
    assert result["status"] == "completed"

    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    assert c.final_asset.asset_type == AssetType.CLIP

    # Final asset's source_spec identifies the composite primitive
    spec = c.final_asset.source_spec
    assert spec["primitive_kind"] == "composite_video"
    assert spec["layout_kind"] == "backdrop"
    # Composite consumed both upstream step outputs
    assert spec["input_count"] == 2


def test_starter_intermediate_assets_persist_with_composition_link() -> None:
    """All 3 step outputs survive on the Asset table linked to
    the composition — the V0 audit trail (intermediate assets
    are reusable + inspectable)."""
    ws = _make_workspace("v8intermediate@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="hi.", backdrop_prompt="alley.",
        mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()

    # 3 produced assets total
    assert c.produced_assets.count() == 3
    # All are CLIP type
    for asset in c.produced_assets.all():
        assert asset.asset_type == AssetType.CLIP
        assert asset.workspace_id == ws.pk


# ---- cost estimation ----------------------------------------------


def test_cost_estimate_sums_all_three_primitives() -> None:
    """Composition cost = sum of (visual_clip + avatar_speech
    + composite_video) cost estimates."""
    ws = _make_workspace("v8cost@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 200,
        backdrop_prompt="A cinematic backdrop.",
        backdrop_duration=5,
        mock_mode=True,
    )
    total = estimate_composition_cost(c)
    # Each primitive contributes a positive cost (see V3/V4/V7
    # estimators); the sum should exceed any individual primitive.
    assert total > 0
    # Sanity bound: the three estimates are all bounded constants
    # or scaled costs — confirm total exceeds the most expensive
    # individual primitive (generate_avatar_speech at >250k micros).
    assert total >= 250_000


# ---- multi-backdrop chain (SESSION 179) ---------------------------


def test_estimate_avatar_speech_seconds_helper() -> None:
    """Speech estimator: 11 chars/sec + 2s buffer, floor at 5s.

    Empty / tiny scripts clamp to the 5s floor so the chain math
    never produces a zero-backdrop composition. Long scripts grow
    linearly with character count."""
    # Floor: empty + tiny scripts both land at 5s.
    assert _estimate_avatar_speech_seconds(0) == 5
    assert _estimate_avatar_speech_seconds(20) == 5
    # 110 chars = 10s of speech + 2s buffer = 12s.
    assert _estimate_avatar_speech_seconds(110) == 12
    # 500 chars = ~45.4s of speech, int() = 45 + 2 buffer = 47s.
    assert _estimate_avatar_speech_seconds(500) == 47


def test_compute_backdrop_chain_length_helper() -> None:
    """Chain length: ceil(speech / backdrop) clamped to
    ``_MAX_BACKDROP_CHAIN_LENGTH``."""
    # Short script + default 10s backdrop = single backdrop.
    assert _compute_backdrop_chain_length(20, 10) == 1
    # 500-char script needs 47s of speech / 10s per backdrop = 5.
    assert _compute_backdrop_chain_length(500, 10) == 5
    # Pathological script: 11_000 chars = 1002s of speech;
    # divided by 10s = 101 backdrops; clamped to MAX.
    assert (
        _compute_backdrop_chain_length(11_000, 10)
        == _MAX_BACKDROP_CHAIN_LENGTH
    )


def test_short_script_stays_single_backdrop_three_steps() -> None:
    """Short scripts get the legacy 3-step shape (backdrop +
    speech + composite); no concat step is laid down so existing
    consumers of the 3-step layout keep working."""
    ws = _make_workspace("v8short_chain@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="Hi there.", backdrop_prompt="A quiet park bench.",
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    assert len(steps) == 3
    assert [s.primitive for s in steps] == [
        "generate_visual_clip",
        "generate_avatar_speech",
        "composite_video",
    ]
    # Composite background points at the single backdrop (step 0).
    composite = steps[2]
    bg = composite.inputs[0]
    assert bg["slot"] == "background"
    assert bg["from_step_position"] == 0


def test_long_script_generates_n_backdrops_with_concat() -> None:
    """500-char script triggers a 5-backdrop chain. Step layout:
    5 backdrops + 1 speech + 1 concat + 1 composite = 8 steps."""
    ws = _make_workspace("v8long_chain@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 500,
        backdrop_prompt="A bustling night market.",
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    assert len(steps) == 8
    # First five = backdrops.
    for i in range(5):
        assert steps[i].primitive == "generate_visual_clip"
        assert steps[i].params["prompt"] == "A bustling night market."
        assert steps[i].params["duration"] == 10
    # Step 5 = speech.
    assert steps[5].primitive == "generate_avatar_speech"
    # Step 6 = concat with one input per backdrop in order.
    assert steps[6].primitive == "concat_clips"
    concat_inputs = steps[6].inputs
    assert len(concat_inputs) == 5
    for i, inp in enumerate(concat_inputs):
        assert inp["slot"] == "clip"
        assert inp["from_step_position"] == i
    # Step 7 = composite with background = concat step (6),
    # foreground = speech step (5).
    composite = steps[7]
    assert composite.primitive == "composite_video"
    bg, fg = composite.inputs
    assert bg["slot"] == "background"
    assert bg["from_step_position"] == 6
    assert fg["slot"] == "foreground"
    assert fg["from_step_position"] == 5


def test_chain_length_clamps_to_max_for_pathological_scripts() -> None:
    """A wildly oversized script can't spin up runaway Runway
    calls — the chain length caps at ``_MAX_BACKDROP_CHAIN_LENGTH``
    backdrops + concat + composite + speech."""
    ws = _make_workspace("v8clamp_chain@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="word " * 5_000,  # ~25_000 chars
        backdrop_prompt="An endless library.",
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    n = _MAX_BACKDROP_CHAIN_LENGTH
    # n backdrops + 1 speech + 1 concat + 1 composite
    assert len(steps) == n + 3
    backdrop_count = sum(
        1 for s in steps if s.primitive == "generate_visual_clip"
    )
    assert backdrop_count == n


def test_custom_backdrop_duration_changes_chain_length() -> None:
    """A shorter per-clip backdrop forces more clips for the same
    speech. Demonstrates the operator-tunable knob."""
    ws = _make_workspace("v8duration_chain@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 220,  # ~22s of speech
        backdrop_prompt="A glowing aquarium.",
        backdrop_duration=5,  # 5s per backdrop → ceil(22/5) = 5
        mock_mode=True,
    )
    backdrop_steps = [
        s for s in c.steps.all() if s.primitive == "generate_visual_clip"
    ]
    assert len(backdrop_steps) == 5
    for s in backdrop_steps:
        assert s.params["duration"] == 5


# ---- V16 matting opt-in (SESSION 179) -----------------------------


def test_remove_avatar_bg_default_omits_matting_step() -> None:
    """Default behaviour: no remove_avatar_background step. The
    3-step shape (single-backdrop) survives — load-bearing for
    every existing V8 test above."""
    ws = _make_workspace("v16_default@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="Hi there.", backdrop_prompt="A quiet bench.",
        mock_mode=True,
    )
    primitives = [s.primitive for s in c.steps.all().order_by("position")]
    assert "remove_avatar_background" not in primitives
    assert primitives == [
        "generate_visual_clip",
        "generate_avatar_speech",
        "composite_video",
    ]


def test_remove_avatar_bg_flag_inserts_matting_before_composite() -> None:
    """With the flag on, matting lands between speech and
    composite. The composite's foreground slot is rewired to
    consume the matted clip instead of the raw avatar speech —
    that's the whole point of the matting pass."""
    ws = _make_workspace("v16_single@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="Hi.", backdrop_prompt="alley.",
        remove_avatar_bg=True,
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    # Single-backdrop + matting = 4 steps total
    assert [s.primitive for s in steps] == [
        "generate_visual_clip",
        "generate_avatar_speech",
        "remove_avatar_background",
        "composite_video",
    ]
    matte = steps[2]
    assert matte.inputs == [
        {"slot": "clip", "from_step_position": 1},
    ]
    composite = steps[3]
    bg, fg = composite.inputs
    assert bg["slot"] == "background"
    assert bg["from_step_position"] == 0  # backdrop
    assert fg["slot"] == "foreground"
    assert fg["from_step_position"] == 2  # matted, not raw speech


def test_remove_avatar_bg_flag_inserts_matting_after_concat() -> None:
    """Multi-backdrop chain + matting. Step layout:
    N backdrops + speech + concat + matte + composite. The
    composite's background = concat, foreground = matte."""
    ws = _make_workspace("v16_chain@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 500,  # 5-backdrop chain
        backdrop_prompt="A busy market.",
        remove_avatar_bg=True,
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    # 5 backdrops + speech + concat + matte + composite = 9
    assert len(steps) == 9
    assert [s.primitive for s in steps] == [
        "generate_visual_clip",  # 0
        "generate_visual_clip",  # 1
        "generate_visual_clip",  # 2
        "generate_visual_clip",  # 3
        "generate_visual_clip",  # 4
        "generate_avatar_speech",  # 5
        "concat_clips",  # 6
        "remove_avatar_background",  # 7
        "composite_video",  # 8
    ]
    # Matte feeds from speech (position 5).
    assert steps[7].inputs == [
        {"slot": "clip", "from_step_position": 5},
    ]
    # Composite: bg=concat(6), fg=matte(7).
    bg, fg = steps[8].inputs
    assert bg["from_step_position"] == 6
    assert fg["from_step_position"] == 7


# ---- V17.5 extend-chain opt-in (SESSION 183) ----------------------


def test_compute_extend_backdrop_chain_length_helper() -> None:
    """Extend chain: ceil((speech - 10) / 5), floored at 0, capped
    at ``_MAX_BACKDROP_CHAIN_LENGTH - 1`` so total chain length
    (base + extends) stays bounded by the same safety cap as the
    concat path."""
    # Speech ≤ 10s → 0 extends (just the base 10s generate).
    assert _compute_extend_backdrop_chain_length(0) == 0
    assert _compute_extend_backdrop_chain_length(20) == 0  # 5s floor
    assert _compute_extend_backdrop_chain_length(88) == 0  # 8s + 2 buffer = 10s
    # Speech > 10s → ceil((speech - 10) / 5).
    # 110 chars = 10s + 2 buffer = 12s → (12-10)/5 → ceil → 1 extend.
    assert _compute_extend_backdrop_chain_length(110) == 1
    # 220 chars = 20s + 2 buffer = 22s → (22-10)/5 → ceil → 3 extends.
    assert _compute_extend_backdrop_chain_length(220) == 3
    # 500 chars = 45s + 2 buffer = 47s → (47-10)/5 = 7.4 → ceil → 8;
    # clamped to _MAX_BACKDROP_CHAIN_LENGTH - 1 = 5.
    assert (
        _compute_extend_backdrop_chain_length(500)
        == _MAX_BACKDROP_CHAIN_LENGTH - 1
    )


def test_extend_short_script_lays_down_single_generate_no_extends() -> None:
    """Short script (≤10s of speech) — single generate_visual_clip
    + speech + composite. No extend steps because the base 10s
    already covers the speech length."""
    ws = _make_workspace("v17_5_short@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="Hi there.",
        backdrop_prompt="A quiet park bench.",
        use_extend_for_backdrop=True,
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    primitives = [s.primitive for s in steps]
    assert primitives == [
        "generate_visual_clip",
        "generate_avatar_speech",
        "composite_video",
    ]
    # Base generate is locked to the 10s gen4.5 ceiling.
    assert steps[0].params["duration"] == _EXTEND_BASE_DURATION_SECONDS
    # Composite background = base generate (step 0); foreground =
    # speech (step 1).
    bg, fg = steps[2].inputs
    assert bg["from_step_position"] == 0
    assert fg["from_step_position"] == 1


def test_extend_22s_script_lays_down_one_generate_three_extends() -> None:
    """The motivating SESSION 179 case: 22s of speech. Concat path
    needs 3 backdrops + concat (visible 10s seams). Extend path:
    1 generate (10s) + 3 extends (5s each = 15s) = 25s total
    backdrop, no seam, composite trims to speech."""
    ws = _make_workspace("v17_5_22s@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 220,  # ~22s speech estimate
        backdrop_prompt="A neon-lit alley.",
        use_extend_for_backdrop=True,
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    # 1 generate + 3 extends + speech + composite = 6 steps; no
    # concat step on the extend path.
    primitives = [s.primitive for s in steps]
    assert primitives == [
        "generate_visual_clip",   # 0 — base 10s
        "extend_visual_clip",     # 1 — +5s
        "extend_visual_clip",     # 2 — +5s
        "extend_visual_clip",     # 3 — +5s
        "generate_avatar_speech", # 4
        "composite_video",        # 5
    ]
    # Each extend chains to the prior segment's output (last-frame
    # conditioning is the whole point — V17 contract rule 10).
    for i in range(1, 4):
        step = steps[i]
        assert step.params["duration"] == _EXTEND_SEGMENT_DURATION_SECONDS
        assert step.params["prompt"] == "A neon-lit alley."
        assert step.inputs == [
            {"slot": "source", "from_step_position": i - 1},
        ]
    # Composite background = last extend (step 3); foreground =
    # speech (step 4). No concat step in between.
    bg, fg = steps[5].inputs
    assert bg["slot"] == "background"
    assert bg["from_step_position"] == 3
    assert fg["slot"] == "foreground"
    assert fg["from_step_position"] == 4


def test_extend_chain_clamps_to_max_for_pathological_scripts() -> None:
    """Long scripts can't spin up runaway Runway calls — extends
    clamp to ``_MAX_BACKDROP_CHAIN_LENGTH - 1`` (one slot reserved
    for the base generate). The total chain length matches the
    concat path's safety cap."""
    ws = _make_workspace("v17_5_clamp@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="word " * 5_000,  # ~25_000 chars
        backdrop_prompt="An endless library.",
        use_extend_for_backdrop=True,
        mock_mode=True,
    )
    primitives = [
        s.primitive for s in c.steps.all().order_by("position")
    ]
    n_generate = sum(1 for p in primitives if p == "generate_visual_clip")
    n_extend = sum(1 for p in primitives if p == "extend_visual_clip")
    assert n_generate == 1
    assert n_extend == _MAX_BACKDROP_CHAIN_LENGTH - 1


def test_extend_ratio_propagates_to_base_and_all_extends() -> None:
    """``backdrop_ratio`` must land on every clip in the chain so
    the final concat doesn't get dim-mismatched halfway through.
    Same shape contract as the concat path's per-clip params."""
    ws = _make_workspace("v17_5_ratio@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 220,
        backdrop_prompt="A skyline at dawn.",
        backdrop_ratio="720:1280",
        use_extend_for_backdrop=True,
        mock_mode=True,
    )
    for step in c.steps.all().order_by("position"):
        if step.primitive in ("generate_visual_clip", "extend_visual_clip"):
            assert step.params["ratio"] == "720:1280"


def test_extend_path_ignores_backdrop_duration_kwarg() -> None:
    """``backdrop_duration`` is meaningless on the extend path —
    gen4_turbo extends are fixed at 5s per call and the base is
    fixed at 10s (gen4.5 ceiling). The kwarg is accepted (so
    operators flipping the flag don't get a TypeError) but the
    chain math ignores it."""
    ws = _make_workspace("v17_5_duration@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 220,
        backdrop_prompt="A cinematic backdrop.",
        backdrop_duration=5,  # would force 5-backdrop concat on False path
        use_extend_for_backdrop=True,
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    assert steps[0].primitive == "generate_visual_clip"
    assert steps[0].params["duration"] == _EXTEND_BASE_DURATION_SECONDS
    for step in steps[1:]:
        if step.primitive == "extend_visual_clip":
            assert step.params["duration"] == _EXTEND_SEGMENT_DURATION_SECONDS


def test_extend_path_remove_avatar_bg_matting_lands_before_composite() -> None:
    """V16 matting still wires up correctly when both flags are
    set. Matte source = avatar speech (position N+1 where N is the
    last extend); composite foreground = matte; composite
    background = last extend output. No concat step on this path."""
    ws = _make_workspace("v17_5_matte@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 220,  # 3-extend chain
        backdrop_prompt="A busy night market.",
        use_extend_for_backdrop=True,
        remove_avatar_bg=True,
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    # 1 generate + 3 extends + speech + matte + composite = 7
    assert [s.primitive for s in steps] == [
        "generate_visual_clip",       # 0 — base
        "extend_visual_clip",         # 1
        "extend_visual_clip",         # 2
        "extend_visual_clip",         # 3 — final backdrop segment
        "generate_avatar_speech",     # 4
        "remove_avatar_background",   # 5 — mattes the speech
        "composite_video",            # 6
    ]
    # Matte consumes the speech clip (position 4).
    assert steps[5].inputs == [
        {"slot": "clip", "from_step_position": 4},
    ]
    # Composite: bg = last extend (3); fg = matte (5).
    bg, fg = steps[6].inputs
    assert bg["from_step_position"] == 3
    assert fg["from_step_position"] == 5


def test_extend_path_executes_end_to_end_in_mock_mode() -> None:
    """V2 runtime carries the extend chain through to COMPLETED.
    Mock-mode extends short-circuit to deterministic stub assets;
    the composite final asset is recognisable downstream."""
    ws = _make_workspace("v17_5_e2e@test")
    sp = _make_spokesperson(ws, name="Riggs")

    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="The founder's substantive take on coffee, " * 4,
        backdrop_prompt="A warm cafe terrace at golden hour.",
        use_extend_for_backdrop=True,
        mock_mode=True,
    )

    result = execute_composition.apply(args=[str(c.pk)]).get()
    assert result["status"] == "completed"

    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    assert c.final_asset.asset_type == AssetType.CLIP
    spec = c.final_asset.source_spec
    assert spec["primitive_kind"] == "composite_video"
    assert spec["layout_kind"] == "backdrop"


def test_extend_default_is_false_concat_path_unchanged() -> None:
    """V17 contract rule 12 (V8 keeps current behaviour). Without
    ``use_extend_for_backdrop``, no extend_visual_clip step
    appears anywhere in the composition — even on long scripts.
    Load-bearing for backwards-compat across every existing V8
    test above."""
    ws = _make_workspace("v17_5_default@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="x" * 500,
        backdrop_prompt="A bustling market.",
        mock_mode=True,
    )
    primitives = [
        s.primitive for s in c.steps.all().order_by("position")
    ]
    assert "extend_visual_clip" not in primitives
