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
from apps.compositions.starters import talking_head_with_backdrop
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


def test_starter_omits_optional_backdrop_params_when_unset() -> None:
    """``ratio`` and ``duration`` only land in params when the
    operator passed them — server-side defaults take over
    otherwise."""
    ws = _make_workspace("v8optional@test")
    sp = _make_spokesperson(ws)
    c = talking_head_with_backdrop(
        workspace=ws, spokesperson=sp,
        script="hi.", backdrop_prompt="alley.",
        mock_mode=True,
    )
    backdrop_step = c.steps.get(position=0)
    assert "ratio" not in backdrop_step.params
    assert "duration" not in backdrop_step.params


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
