"""V13 tests — generate_image primitive + storyboard_ad starter.

Ports the hackathon's storyboard_service.py pattern. The
generate_image primitive is the cinematic-frame building
block; storyboard_ad chains three of them through three
generate_visual_clip steps + one concat_clips for a 15-second
3-shot ad.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.compositions.primitives.generate_image import (
    SUPPORTED_IMAGE_RATIOS,
    GenerateImagePrimitive,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.starters import storyboard_ad
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    GenerateImageResult,
    MediaEngineError,
)

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


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Sp",
        runway_avatar_id="fake",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


def _make_image(
    ws,
    file_path: str = "/data/_internal/images/x.png",
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE,
        file_path=file_path, mime_type="image/png",
        width=1280, height=720,
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _fake_image_result(image_url: str = "/data/_internal/images/x.png") -> GenerateImageResult:
    return GenerateImageResult(
        image_url=image_url, width=1280, height=720,
        seed=None, mock_mode=False,
    )


def _patched_client(method_name: str, return_value):
    fake = MagicMock()
    getattr(fake, method_name).return_value = return_value
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- GenerateImagePrimitive ---------------------------------------


def test_generate_image_mock_mode_returns_stub_image_asset() -> None:
    ws = _make_workspace("v13gi1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={"prompt": "A polished coffee bag on a morning table"},
    )
    r = GenerateImagePrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=True,
    )
    assert r.asset_type == AssetType.IMAGE
    assert r.width == 1280
    assert r.height == 720
    assert r.mime_type == "image/png"
    assert r.extra_source_spec["mock"] is True
    assert r.extra_source_spec["used_reference_image"] is False


def test_generate_image_rejects_short_prompt() -> None:
    ws = _make_workspace("v13gi2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={"prompt": "hi"},
    )
    with pytest.raises(PrimitiveError):
        GenerateImagePrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )


def test_generate_image_rejects_unknown_ratio() -> None:
    ws = _make_workspace("v13gi3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={"prompt": "cinematic alley", "ratio": "1920:1080"},
    )
    with pytest.raises(PrimitiveError):
        GenerateImagePrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )


def test_generate_image_supports_three_ratios() -> None:
    assert SUPPORTED_IMAGE_RATIOS == {"1280:720", "720:1280", "1024:1024"}


def test_generate_image_vertical_ratio_returns_portrait_dims() -> None:
    ws = _make_workspace("v13gi4@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={"prompt": "vertical character portrait", "ratio": "720:1280"},
    )
    r = GenerateImagePrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=True,
    )
    assert r.width == 720
    assert r.height == 1280


def test_generate_image_real_mode_call_shape() -> None:
    ws = _make_workspace("v13gi5@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={
            "prompt": "neon cyberpunk street",
            "ratio": "1024:1024",
            "seed": 42,
        },
    )
    cm, fake = _patched_client("generate_image", _fake_image_result())
    with patch(
        "apps.compositions.primitives.generate_image.MediaEngineClient",
        return_value=cm,
    ):
        r = GenerateImagePrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )
    fake.generate_image.assert_called_once()
    kwargs = fake.generate_image.call_args.kwargs
    assert kwargs["prompt"] == "neon cyberpunk street"
    assert kwargs["ratio"] == "1024:1024"
    assert kwargs["seed"] == 42
    assert kwargs["reference_image_url"] is None
    assert r.asset_type == AssetType.IMAGE


def test_generate_image_uses_explicit_reference_url_from_params() -> None:
    ws = _make_workspace("v13gi6@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={
            "prompt": "remix this brand frame",
            "reference_image_url": "https://brand.test/logo.png",
        },
    )
    cm, fake = _patched_client("generate_image", _fake_image_result())
    with patch(
        "apps.compositions.primitives.generate_image.MediaEngineClient",
        return_value=cm,
    ):
        GenerateImagePrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )
    kwargs = fake.generate_image.call_args.kwargs
    assert kwargs["reference_image_url"] == "https://brand.test/logo.png"


def test_generate_image_uses_reference_slot_input() -> None:
    """``reference_image`` slot pointing at an IMAGE asset
    feeds its file_path as the reference."""
    ws = _make_workspace("v13gi7@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    ref = _make_image(ws, "/data/_internal/images/upstream.png")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={"prompt": "match this style"},
    )
    cm, fake = _patched_client("generate_image", _fake_image_result())
    with patch(
        "apps.compositions.primitives.generate_image.MediaEngineClient",
        return_value=cm,
    ):
        GenerateImagePrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "reference_image", "asset": ref},
            ],
            mock_mode=False,
        )
    kwargs = fake.generate_image.call_args.kwargs
    assert kwargs["reference_image_url"] == "/data/_internal/images/upstream.png"


def test_generate_image_explicit_url_wins_over_slot() -> None:
    ws = _make_workspace("v13gi8@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    ref = _make_image(ws, "/data/_internal/images/slot.png")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={
            "prompt": "explicit override",
            "reference_image_url": "/data/_internal/images/explicit.png",
        },
    )
    cm, fake = _patched_client("generate_image", _fake_image_result())
    with patch(
        "apps.compositions.primitives.generate_image.MediaEngineClient",
        return_value=cm,
    ):
        GenerateImagePrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "reference_image", "asset": ref},
            ],
            mock_mode=False,
        )
    kwargs = fake.generate_image.call_args.kwargs
    assert kwargs["reference_image_url"] == "/data/_internal/images/explicit.png"


def test_generate_image_rejects_non_image_in_reference_slot() -> None:
    ws = _make_workspace("v13gi9@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/clip.mp4",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={"prompt": "won't run"},
    )
    with pytest.raises(PrimitiveError):
        GenerateImagePrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "reference_image", "asset": clip},
            ],
            mock_mode=False,
        )


def test_generate_image_propagates_media_engine_failure() -> None:
    ws = _make_workspace("v13gi10@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={"prompt": "should fail"},
    )
    fake = MagicMock()
    fake.generate_image.side_effect = MediaEngineError(
        "gen4_image rejected", status_code=502,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.generate_image.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError):
            GenerateImagePrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )


def test_generate_image_invalid_seed_raises() -> None:
    ws = _make_workspace("v13gi11@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="generate_image",
        params={"prompt": "valid prompt", "seed": "bogus"},
    )
    with pytest.raises(PrimitiveError):
        GenerateImagePrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )


# ---- storyboard_ad starter ----------------------------------------


def test_storyboard_ad_creates_seven_step_composition() -> None:
    ws = _make_workspace("v13sb1@test")
    sp = _make_spokesperson(ws)
    c = storyboard_ad(
        workspace=ws, spokesperson=sp,
        hook_prompt="Coffee bag glints in morning light",
        action_prompt="Espresso pours into a cup",
        payoff_prompt="Smiling customer leaves the cafe",
        mock_mode=True,
    )
    assert c.template_kind == "storyboard_ad"
    steps = list(c.steps.all().order_by("position"))
    assert len(steps) == 7

    # Steps 0-2: generate_image
    for idx in range(3):
        assert steps[idx].primitive == "generate_image"

    # Steps 3-5: generate_visual_clip with reference_image chain
    for idx in range(3):
        step = steps[3 + idx]
        assert step.primitive == "generate_visual_clip"
        assert step.inputs[0]["slot"] == "reference_image"
        assert step.inputs[0]["from_step_position"] == idx

    # Step 6: concat
    concat = steps[6]
    assert concat.primitive == "concat_clips"
    positions = [e["from_step_position"] for e in concat.inputs]
    assert positions == [3, 4, 5]


def test_storyboard_ad_shot_prompts_carry_through() -> None:
    ws = _make_workspace("v13sb2@test")
    sp = _make_spokesperson(ws)
    c = storyboard_ad(
        workspace=ws, spokesperson=sp,
        hook_prompt="HOOK SHOT",
        action_prompt="ACTION SHOT",
        payoff_prompt="PAYOFF SHOT",
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    # Both image step + visual_clip step share the per-shot prompt
    assert steps[0].params["prompt"] == "HOOK SHOT"
    assert steps[1].params["prompt"] == "ACTION SHOT"
    assert steps[2].params["prompt"] == "PAYOFF SHOT"
    assert steps[3].params["prompt"] == "HOOK SHOT"
    assert steps[4].params["prompt"] == "ACTION SHOT"
    assert steps[5].params["prompt"] == "PAYOFF SHOT"


def test_storyboard_ad_image_seed_propagates_to_all_three_shots() -> None:
    """Same seed across the three image steps keeps visual
    identity coherent across shots."""
    ws = _make_workspace("v13sb3@test")
    sp = _make_spokesperson(ws)
    c = storyboard_ad(
        workspace=ws, spokesperson=sp,
        hook_prompt="HOOK_PROMPT", action_prompt="ACTION_PROMPT", payoff_prompt="PAYOFF_PROMPT",
        image_seed=12345, mock_mode=True,
    )
    image_steps = c.steps.filter(primitive="generate_image").order_by("position")
    for s in image_steps:
        assert s.params["seed"] == 12345


def test_storyboard_ad_clip_duration_propagates() -> None:
    ws = _make_workspace("v13sb4@test")
    sp = _make_spokesperson(ws)
    c = storyboard_ad(
        workspace=ws, spokesperson=sp,
        hook_prompt="HOOK_PROMPT", action_prompt="ACTION_PROMPT", payoff_prompt="PAYOFF_PROMPT",
        clip_duration=5, mock_mode=True,
    )
    clip_steps = c.steps.filter(primitive="generate_visual_clip")
    for s in clip_steps:
        assert s.params["duration"] == 5


def test_storyboard_ad_rejects_empty_prompts() -> None:
    ws = _make_workspace("v13sb5@test")
    sp = _make_spokesperson(ws)
    with pytest.raises(ValueError):
        storyboard_ad(
            workspace=ws, spokesperson=sp,
            hook_prompt="", action_prompt="A", payoff_prompt="P",
            mock_mode=True,
        )
    with pytest.raises(ValueError):
        storyboard_ad(
            workspace=ws, spokesperson=sp,
            hook_prompt="H", action_prompt=" ", payoff_prompt="P",
            mock_mode=True,
        )
    with pytest.raises(ValueError):
        storyboard_ad(
            workspace=ws, spokesperson=sp,
            hook_prompt="H", action_prompt="A", payoff_prompt="",
            mock_mode=True,
        )


def test_storyboard_ad_rejects_cross_workspace_spokesperson() -> None:
    ws_a = _make_workspace("v13sb_xa@test", "A")
    ws_b = _make_workspace("v13sb_xb@test", "B")
    foreign_sp = _make_spokesperson(ws_b)
    with pytest.raises(ValueError):
        storyboard_ad(
            workspace=ws_a, spokesperson=foreign_sp,
            hook_prompt="HOOK_PROMPT", action_prompt="ACTION_PROMPT", payoff_prompt="PAYOFF_PROMPT",
            mock_mode=True,
        )


def test_storyboard_ad_executes_end_to_end_in_mock_mode() -> None:
    """Mock-mode runs all 7 steps. Final asset is the concat
    output."""
    ws = _make_workspace("v13sb_e2e@test")
    sp = _make_spokesperson(ws)
    c = storyboard_ad(
        workspace=ws, spokesperson=sp,
        hook_prompt="Hook visual",
        action_prompt="Action visual",
        payoff_prompt="Payoff visual",
        mock_mode=True,
    )
    result = execute_composition.apply(args=[str(c.pk)]).get()
    assert result["status"] == "completed"
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    # Final asset is the concat output, not any intermediate
    assert c.final_asset.source_spec["primitive_kind"] == "concat_clips"
    assert c.final_asset.source_spec["input_count"] == 3


def test_storyboard_ad_intermediate_assets_persist_with_composition() -> None:
    """All 7 step outputs survive on the Asset table linked to
    the composition. 3 IMAGE + 3 CLIP (visual_clip outputs) +
    1 final CLIP = 7 produced assets."""
    ws = _make_workspace("v13sb_intermediate@test")
    sp = _make_spokesperson(ws)
    c = storyboard_ad(
        workspace=ws, spokesperson=sp,
        hook_prompt="Hook visual frame",
        action_prompt="Action visual frame",
        payoff_prompt="Payoff visual frame",
        mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()
    assert c.produced_assets.count() == 7
    # 3 IMAGE assets + 4 CLIP assets (3 visual + 1 concat)
    images = c.produced_assets.filter(asset_type=AssetType.IMAGE).count()
    clips = c.produced_assets.filter(asset_type=AssetType.CLIP).count()
    assert images == 3
    assert clips == 4


# ---- cost --------------------------------------------------------


def test_generate_image_cost_estimate_is_realistic() -> None:
    """gen4_image is $0.04/image; estimate should sit well
    above the local-ffmpeg-only primitives' floors."""
    assert GenerateImagePrimitive.estimate_cost({}) >= 20_000
