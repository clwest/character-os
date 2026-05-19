"""V9 tests — polish primitives + starters.

Covers all four polish primitives (add_captions /
add_intro_outro / trim_clip / reformat_clip) plus the two
new starter compositions (talking_head_polished, reels_format).
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
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.primitives.polish import (
    AddCaptionsPrimitive,
    AddIntroOutroPrimitive,
    ReformatClipPrimitive,
    TrimClipPrimitive,
)
from apps.compositions.starters import (
    reels_format,
    talking_head_polished,
)
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineError,
    ProcessedClipResult,
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


def _make_spokesperson(ws: Workspace, name: str = "Sp") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name,
        runway_avatar_id="fake",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


def _make_clip(
    ws,
    file_path: str = "/data/_assets/clip.mp4",
    duration_ms: int | None = 5000,
    width: int | None = 1280,
    height: int | None = 720,
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path=file_path, duration_ms=duration_ms,
        width=width, height=height,
        mime_type="video/mp4",
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _fake_processed(output_url: str = "/data/_internal/x.mp4") -> ProcessedClipResult:
    return ProcessedClipResult(
        output_url=output_url, duration_seconds=5.0,
        size_bytes=2048, mock_mode=False,
    )


def _patched_method(method_name: str, return_value):
    """Build a context-manager-style mock for MediaEngineClient
    that returns ``return_value`` from a specific method."""
    fake = MagicMock()
    getattr(fake, method_name).return_value = return_value
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- AddCaptionsPrimitive -----------------------------------------


def test_captions_mock_mode_returns_stub() -> None:
    ws = _make_workspace("v9c1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_captions",
        params={
            "captions": [
                {"start_s": 0, "end_s": 2, "text": "Hello"},
                {"start_s": 2, "end_s": 4, "text": "World"},
            ],
        },
    )
    r = AddCaptionsPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "base", "asset": clip}],
        mock_mode=True,
    )
    assert r.asset_type == AssetType.CLIP
    assert r.extra_source_spec["caption_count"] == 2
    assert r.extra_source_spec["mock"] is True
    assert r.duration_ms == clip.duration_ms  # preserved


def test_captions_empty_list_raises() -> None:
    ws = _make_workspace("v9c2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_captions",
        params={"captions": []},
    )
    with pytest.raises(PrimitiveError):
        AddCaptionsPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=True,
        )


def test_captions_real_mode_calls_media_engine() -> None:
    ws = _make_workspace("v9c3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws, "/data/voice.mp4")
    captions = [{"start_s": 0, "end_s": 2.5, "text": "Hi"}]
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_captions",
        params={"captions": captions},
    )
    cm, fake = _patched_method("add_captions", _fake_processed("/data/captioned.mp4"))
    with patch(
        "apps.compositions.primitives.polish.MediaEngineClient",
        return_value=cm,
    ):
        r = AddCaptionsPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=False,
        )
    fake.add_captions.assert_called_once()
    kwargs = fake.add_captions.call_args.kwargs
    assert kwargs["clip_url"] == "/data/voice.mp4"
    assert kwargs["captions"] == captions
    assert r.file_path == "/data/captioned.mp4"


def test_captions_rejects_non_clip_input() -> None:
    ws = _make_workspace("v9c4@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    audio = Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/a.mp3",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_captions",
        params={"captions": [{"start_s": 0, "end_s": 1, "text": "x"}]},
    )
    with pytest.raises(PrimitiveError):
        AddCaptionsPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": audio}],
            mock_mode=False,
        )


# ---- AddIntroOutroPrimitive ---------------------------------------


def test_intro_outro_mock_mode_extends_duration() -> None:
    ws = _make_workspace("v9io1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws, duration_ms=5000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_intro_outro",
        params={
            "intro": {"text": "Brand", "duration_s": 3},
            "outro": {"text": "CTA", "duration_s": 2},
        },
    )
    r = AddIntroOutroPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "base", "asset": clip}],
        mock_mode=True,
    )
    assert r.duration_ms == 5000 + 3000 + 2000
    assert r.extra_source_spec["has_intro"] is True
    assert r.extra_source_spec["has_outro"] is True


def test_intro_outro_requires_at_least_one() -> None:
    ws = _make_workspace("v9io2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_intro_outro",
        params={},
    )
    with pytest.raises(PrimitiveError):
        AddIntroOutroPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=True,
        )


def test_intro_outro_intro_only() -> None:
    """Operator can ship intro without outro (or vice versa)."""
    ws = _make_workspace("v9io3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws, duration_ms=5000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_intro_outro",
        params={"intro": {"text": "Welcome", "duration_s": 2.5}},
    )
    r = AddIntroOutroPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "base", "asset": clip}],
        mock_mode=True,
    )
    assert r.duration_ms == 5000 + 2500
    assert r.extra_source_spec["has_outro"] is False


def test_intro_outro_real_mode_call_shape() -> None:
    ws = _make_workspace("v9io4@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws, "/data/body.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_intro_outro",
        params={
            "intro": {"text": "Brand", "duration_s": 3, "bg_color": "blue"},
            "outro": {"text": "Thanks", "duration_s": 2},
        },
    )
    cm, fake = _patched_method("add_intro_outro", _fake_processed("/data/wrapped.mp4"))
    with patch(
        "apps.compositions.primitives.polish.MediaEngineClient",
        return_value=cm,
    ):
        AddIntroOutroPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=False,
        )
    kwargs = fake.add_intro_outro.call_args.kwargs
    assert kwargs["clip_url"] == "/data/body.mp4"
    assert kwargs["intro"]["bg_color"] == "blue"
    assert kwargs["outro"]["duration_s"] == 2


# ---- TrimClipPrimitive --------------------------------------------


def test_trim_mock_mode_uses_trimmed_duration() -> None:
    ws = _make_workspace("v9t1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws, duration_ms=10000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="trim_clip",
        params={"start_ms": 2000, "end_ms": 7000},
    )
    r = TrimClipPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "base", "asset": clip}],
        mock_mode=True,
    )
    assert r.duration_ms == 5000
    assert r.extra_source_spec["start_ms"] == 2000
    assert r.extra_source_spec["end_ms"] == 7000


def test_trim_rejects_inverted_range() -> None:
    ws = _make_workspace("v9t2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="trim_clip",
        params={"start_ms": 5000, "end_ms": 3000},
    )
    with pytest.raises(PrimitiveError):
        TrimClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=False,
        )


def test_trim_real_mode_call_shape() -> None:
    ws = _make_workspace("v9t3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws, "/data/full.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="trim_clip",
        params={"start_ms": 1000, "end_ms": 6000},
    )
    cm, fake = _patched_method("trim_clip", _fake_processed("/data/trimmed.mp4"))
    with patch(
        "apps.compositions.primitives.polish.MediaEngineClient",
        return_value=cm,
    ):
        TrimClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=False,
        )
    kwargs = fake.trim_clip.call_args.kwargs
    assert kwargs["start_ms"] == 1000
    assert kwargs["end_ms"] == 6000


# ---- ReformatClipPrimitive ----------------------------------------


def test_reformat_mock_mode_updates_dims() -> None:
    ws = _make_workspace("v9r1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws, width=1280, height=720)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="reformat_clip",
        params={"target_ratio": "720:1280"},
    )
    r = ReformatClipPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "base", "asset": clip}],
        mock_mode=True,
    )
    assert r.width == 720
    assert r.height == 1280
    assert r.duration_ms == clip.duration_ms


def test_reformat_rejects_unknown_ratio() -> None:
    ws = _make_workspace("v9r2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="reformat_clip",
        params={"target_ratio": "1920:1080"},
    )
    with pytest.raises(PrimitiveError):
        ReformatClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=False,
        )


def test_reformat_real_mode_propagates_failure() -> None:
    ws = _make_workspace("v9r3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="reformat_clip",
        params={"target_ratio": "720:1280"},
    )
    fake = MagicMock()
    fake.reformat_clip.side_effect = MediaEngineError(
        "explode", status_code=500,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.polish.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError):
            ReformatClipPrimitive.execute(
                step=step,
                resolved_inputs=[{"slot": "base", "asset": clip}],
                mock_mode=False,
            )


# ---- starter: talking_head_polished -------------------------------


def test_polished_starter_creates_full_three_step_composition() -> None:
    ws = _make_workspace("v9sp1@test")
    sp = _make_spokesperson(ws)
    captions = [
        {"start_s": 0, "end_s": 2, "text": "Hi"},
        {"start_s": 2, "end_s": 4, "text": "World"},
    ]
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Tell viewers about coffee.",
        captions=captions,
        intro={"text": "Brand", "duration_s": 3},
        outro={"text": "CTA", "duration_s": 2},
        mock_mode=True,
    )
    assert c.template_kind == "talking_head_polished"
    steps = list(c.steps.all().order_by("position"))
    assert len(steps) == 3
    assert steps[0].primitive == "generate_avatar_speech"
    assert steps[1].primitive == "add_captions"
    assert steps[2].primitive == "add_intro_outro"

    # Step chains
    assert steps[1].inputs[0]["from_step_position"] == 0
    assert steps[2].inputs[0]["from_step_position"] == 1


def test_polished_starter_skips_captions_when_omitted() -> None:
    ws = _make_workspace("v9sp2@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Hi.",
        # captions omitted
        intro={"text": "Brand"},
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    assert len(steps) == 2
    assert steps[0].primitive == "generate_avatar_speech"
    assert steps[1].primitive == "add_intro_outro"
    # intro_outro chains directly to step 0
    assert steps[1].inputs[0]["from_step_position"] == 0


def test_polished_starter_skips_both_polish_steps_when_neither_supplied() -> None:
    """Operator submitting talking_head_polished with neither
    captions nor intro/outro gets just the speech step. Same
    composition as `talking_head` semantically but
    template_kind=polished for audit clarity."""
    ws = _make_workspace("v9sp3@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Hi.",
        mock_mode=True,
    )
    steps = list(c.steps.all())
    assert len(steps) == 1
    assert steps[0].primitive == "generate_avatar_speech"


def test_polished_starter_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v9sp_e2e@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="The founder's substantive take.",
        captions=[{"start_s": 0, "end_s": 5, "text": "Founder"}],
        intro={"text": "Coffee Co", "duration_s": 2},
        mock_mode=True,
    )
    result = execute_composition.apply(args=[str(c.pk)]).get()
    assert result["status"] == "completed"
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    # Final asset is the last step's output — intro_outro in this case
    assert c.final_asset.source_spec["primitive_kind"] == "add_intro_outro"


def test_polished_starter_rejects_empty_script() -> None:
    ws = _make_workspace("v9sp_empty@test")
    sp = _make_spokesperson(ws)
    with pytest.raises(ValueError):
        talking_head_polished(
            workspace=ws, spokesperson=sp,
            script="  ",
            intro={"text": "Brand"},
            mock_mode=True,
        )


# ---- SESSION 180 — operator-friendly shorthand kwargs -------------


def test_polished_intro_text_kwarg_builds_default_intro_dict() -> None:
    """``intro_text="Brand"`` lands as the intro card without the
    operator having to know the dict shape — the load-bearing
    seam between the SPA form (passes plain strings) and the
    starter (composes the JSON-shaped dict)."""
    ws = _make_workspace("v9sp_introtext@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Hi there.",
        intro_text="Welcome to the show.",
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    assert [s.primitive for s in steps] == [
        "generate_avatar_speech",
        "add_intro_outro",
    ]
    intro_params = steps[1].params["intro"]
    assert intro_params["text"] == "Welcome to the show."
    assert intro_params["duration_s"] == 3.0
    # outro stays absent — the operator only set intro_text.
    assert "outro" not in steps[1].params


def test_polished_outro_text_kwarg_builds_default_outro_dict() -> None:
    ws = _make_workspace("v9sp_outrotext@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Hi there.",
        outro_text="Thanks for watching.",
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    assert [s.primitive for s in steps] == [
        "generate_avatar_speech",
        "add_intro_outro",
    ]
    outro_params = steps[1].params["outro"]
    assert outro_params["text"] == "Thanks for watching."
    assert outro_params["duration_s"] == 3.0
    assert "intro" not in steps[1].params


def test_polished_both_text_kwargs_build_both_cards() -> None:
    ws = _make_workspace("v9sp_bothtext@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Hi there.",
        intro_text="Open.", outro_text="Close.",
        mock_mode=True,
    )
    step = c.steps.get(position=1)
    assert step.primitive == "add_intro_outro"
    assert step.params["intro"]["text"] == "Open."
    assert step.params["outro"]["text"] == "Close."


def test_polished_intro_dict_wins_over_intro_text() -> None:
    """Programmatic dict-form kwarg suppresses the shorthand —
    no surprise override."""
    ws = _make_workspace("v9sp_wins@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Hi.",
        intro={"text": "Programmatic", "duration_s": 5.0,
               "font_size": 72},
        intro_text="Form-Driven",  # ignored
        mock_mode=True,
    )
    intro = c.steps.get(position=1).params["intro"]
    assert intro["text"] == "Programmatic"
    assert intro["duration_s"] == 5.0
    assert intro["font_size"] == 72


def test_polished_burn_captions_chunks_script_into_segments() -> None:
    """Auto-timed captions split on sentence boundaries; per-
    chunk duration tracks character count at the avatar's
    estimated speech rate."""
    ws = _make_workspace("v9sp_burn@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script=(
            "Markets reward conviction. "
            "Everyone I know who built something durable started "
            "by being convinced of one specific thing nobody else "
            "believed yet. "
            "That's the discipline."
        ),
        burn_captions=True,
        mock_mode=True,
    )
    captions_step = c.steps.get(position=1)
    assert captions_step.primitive == "add_captions"
    captions = captions_step.params["captions"]
    # 3 sentences → 3 segments
    assert len(captions) == 3
    # All segments are non-overlapping and monotonic
    for prev, curr in zip(captions, captions[1:]):
        assert prev["end_s"] == curr["start_s"]
    # Each segment has a non-empty text + a positive duration
    for seg in captions:
        assert seg["text"].strip()
        assert seg["end_s"] > seg["start_s"]


def test_polished_explicit_captions_win_over_burn_captions() -> None:
    ws = _make_workspace("v9sp_burnwins@test")
    sp = _make_spokesperson(ws)
    explicit = [
        {"start_s": 0, "end_s": 2, "text": "operator-supplied"},
    ]
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Some script.",
        captions=explicit,
        burn_captions=True,  # ignored — explicit list wins
        mock_mode=True,
    )
    captions = c.steps.get(position=1).params["captions"]
    assert captions == explicit


def test_polished_full_polish_via_shorthand_kwargs() -> None:
    """End-to-end shape: intro_text + outro_text + burn_captions
    all on at once lays down speech → captions → intro_outro
    (the 3-step polish chain the recipe name promises)."""
    ws = _make_workspace("v9sp_fullshort@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Hi. There.",
        intro_text="Open",
        outro_text="Close",
        burn_captions=True,
        mock_mode=True,
    )
    steps = list(c.steps.all().order_by("position"))
    assert [s.primitive for s in steps] == [
        "generate_avatar_speech",
        "add_captions",
        "add_intro_outro",
    ]
    # captions chains off speech, intro_outro chains off captions
    assert steps[1].inputs[0]["from_step_position"] == 0
    assert steps[2].inputs[0]["from_step_position"] == 1


def test_polished_empty_intro_text_kwarg_skips_step() -> None:
    """Whitespace-only intro_text is treated as not-set so the
    intro_outro step still skips. Mirrors how the SPA form
    submits an empty text input."""
    ws = _make_workspace("v9sp_blank@test")
    sp = _make_spokesperson(ws)
    c = talking_head_polished(
        workspace=ws, spokesperson=sp,
        script="Hi.",
        intro_text="   ",
        mock_mode=True,
    )
    primitives = [s.primitive for s in c.steps.all().order_by("position")]
    assert primitives == ["generate_avatar_speech"]


# ---- starter: reels_format ----------------------------------------


def test_reels_format_starter_uses_vertical_ratio() -> None:
    ws = _make_workspace("v9rf1@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws)
    c = reels_format(
        workspace=ws, spokesperson=sp,
        base_clip=clip, mock_mode=True,
    )
    assert c.template_kind == "reels_format"
    step = c.steps.first()
    assert step.primitive == "reformat_clip"
    assert step.params["target_ratio"] == "720:1280"


def test_reels_format_rejects_cross_workspace_clip() -> None:
    ws_a = _make_workspace("v9rfxA@test", "A")
    ws_b = _make_workspace("v9rfxB@test", "B")
    sp_a = _make_spokesperson(ws_a)
    foreign = _make_clip(ws_b)
    with pytest.raises(ValueError):
        reels_format(
            workspace=ws_a, spokesperson=sp_a,
            base_clip=foreign, mock_mode=True,
        )


def test_reels_format_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v9rfe2e@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws, width=1280, height=720, duration_ms=5000)
    c = reels_format(
        workspace=ws, spokesperson=sp,
        base_clip=clip, mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    assert c.final_asset.width == 720
    assert c.final_asset.height == 1280


# ---- cost estimates -----------------------------------------------


def test_polish_primitive_costs_nonzero() -> None:
    """Operator-visible cost forecasts include polish steps."""
    assert AddCaptionsPrimitive.estimate_cost({}) > 0
    assert AddIntroOutroPrimitive.estimate_cost({}) > 0
    assert TrimClipPrimitive.estimate_cost({}) > 0
    assert ReformatClipPrimitive.estimate_cost({}) > 0


def test_trim_is_cheapest_polish_primitive() -> None:
    """Trim is stream-copy only (no re-encode); should cost
    less than re-encoding primitives."""
    trim_cost = TrimClipPrimitive.estimate_cost({})
    captions_cost = AddCaptionsPrimitive.estimate_cost({})
    assert trim_cost < captions_cost
