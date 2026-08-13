"""V7 tests — composite + mix_audio primitives + 5 starters.

Covers:

* CompositeVideoPrimitive mock-mode + real-mode (mocked
  media-engine), all four layout kinds (pip / backdrop /
  cohost / broll), input validation, failure paths.
* MixAudioPrimitive mock-mode + real-mode, CLIP+AUDIO input
  shape, multi-track forwards-compat, failure paths.
* Five starters: pip_layout, backdrop_layout, cohost_layout,
  broll_splice, music_bed_pass. Each builds a single-step
  composition with the right primitive + spec; rejects
  cross-workspace assets; runs end-to-end via
  execute_composition in mock-mode.
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
from apps.compositions.primitives.composite_video import (
    CompositeVideoPrimitive,
)
from apps.compositions.primitives.mix_audio import MixAudioPrimitive
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.starters import (
    backdrop_layout,
    broll_splice,
    cohost_layout,
    music_bed_pass,
    pip_layout,
)
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import (
    AudioMixResult,
    CompositeResult,
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


def _make_teammate(ws: Workspace, name: str = "Sp") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name,
        runway_avatar_id="fake",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


def _make_clip(
    ws,
    file_path: str = "/data/_assets/clip.mp4",
    duration_ms: int | None = 5000,
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path=file_path, duration_ms=duration_ms,
        mime_type="video/mp4",
    )


def _make_audio(
    ws,
    file_path: str = "/data/_assets/music.mp3",
    duration_ms: int | None = 30000,
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path=file_path, duration_ms=duration_ms,
        mime_type="audio/mpeg",
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _fake_composite(output_url: str = "/data/_internal/composites/x.mp4") -> CompositeResult:
    return CompositeResult(
        output_url=output_url, duration_seconds=5.0,
        size_bytes=2048, mock_mode=False,
    )


def _fake_mix(output_url: str = "/data/_internal/mixes/x.mp4") -> AudioMixResult:
    return AudioMixResult(
        output_url=output_url, duration_seconds=5.0,
        size_bytes=2048, mock_mode=False,
    )


# ---- CompositeVideoPrimitive ---------------------------------------


def test_composite_mock_mode_returns_stub() -> None:
    ws = _make_workspace("v7c1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    a = _make_clip(ws, "/data/a.mp4", 3000)
    b = _make_clip(ws, "/data/b.mp4", 4000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="composite_video",
        params={"layout_spec": {"kind": "pip", "options": {}}},
    )
    result = CompositeVideoPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": a},
            {"slot": "pip", "asset": b},
        ],
        mock_mode=True,
    )
    assert result.asset_type == AssetType.CLIP
    assert result.extra_source_spec["layout_kind"] == "pip"
    assert result.extra_source_spec["mock"] is True
    assert result.duration_ms is not None


def test_composite_rejects_unknown_layout_kind() -> None:
    ws = _make_workspace("v7c_unk@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    a = _make_clip(ws, "/data/a.mp4")
    b = _make_clip(ws, "/data/b.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="composite_video",
        params={"layout_spec": {"kind": "fake_kind", "options": {}}},
    )
    with pytest.raises(PrimitiveError) as exc:
        CompositeVideoPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": a},
                {"slot": "pip", "asset": b},
            ],
            mock_mode=False,
        )
    assert "kind" in str(exc.value).lower()


def test_composite_requires_two_clip_inputs() -> None:
    ws = _make_workspace("v7c_min@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    a = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="composite_video",
        params={"layout_spec": {"kind": "pip", "options": {}}},
    )
    with pytest.raises(PrimitiveError) as exc:
        CompositeVideoPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": a}],
            mock_mode=False,
        )
    assert "two CLIP inputs" in str(exc.value)


def test_composite_rejects_null_duration_input() -> None:
    """SESSION 184 polish — composite_video errors loudly when any
    CLIP input has duration_ms=None instead of silently letting the
    media-engine pick the base clip's length as the trim target.
    Regression guard against the SESSION 183 Sunset 2 finding: when
    generate_avatar_speech produced a null-duration speech asset
    over an over-provisioned backdrop, the composite picked the
    backdrop length and left a trailing silent tail on the output.
    The right shape is to refuse the dispatch and surface the
    upstream primitive that didn't persist duration."""
    ws = _make_workspace("v7c_nodur@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    # Backdrop has duration, speech doesn't (the bug shape).
    backdrop = _make_clip(ws, "/data/backdrop.mp4", duration_ms=15_000)
    speech = _make_clip(ws, "/data/speech.mp4", duration_ms=None)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="composite_video",
        params={
            "layout_spec": {
                "kind": "backdrop",
                "options": {},
            },
        },
    )
    with pytest.raises(PrimitiveError) as exc:
        CompositeVideoPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": backdrop},
                {"slot": "overlay", "asset": speech},
            ],
            mock_mode=False,
        )
    message = str(exc.value).lower()
    assert "duration_ms" in message
    assert str(speech.id) in str(exc.value)
    # Verbatim phrasing of the actionable hint.
    assert "upstream primitive" in message


def test_composite_rejects_null_duration_input_in_mock_mode_too() -> None:
    """The null-duration check fires in mock mode as well — the
    contract is symmetric across mock + real paths so unit tests
    catch the break before real-mode dogfood."""
    ws = _make_workspace("v7c_nodur_mock@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    backdrop = _make_clip(ws, "/data/backdrop.mp4", duration_ms=15_000)
    speech = _make_clip(ws, "/data/speech.mp4", duration_ms=None)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="composite_video",
        params={"layout_spec": {"kind": "backdrop", "options": {}}},
    )
    with pytest.raises(PrimitiveError):
        CompositeVideoPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": backdrop},
                {"slot": "overlay", "asset": speech},
            ],
            mock_mode=True,
        )


def test_composite_rejects_non_clip_input() -> None:
    ws = _make_workspace("v7c_nontype@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    audio = _make_audio(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="composite_video",
        params={"layout_spec": {"kind": "pip", "options": {}}},
    )
    with pytest.raises(PrimitiveError):
        CompositeVideoPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": clip},
                {"slot": "pip", "asset": audio},
            ],
            mock_mode=False,
        )


def test_composite_real_mode_calls_media_engine_with_layout_spec() -> None:
    ws = _make_workspace("v7c_real@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    a = _make_clip(ws, "/data/bg.mp4", 5000)
    b = _make_clip(ws, "/data/fg.mp4", 5000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="composite_video",
        params={
            "layout_spec": {
                "kind": "backdrop",
                "options": {"fg_width": 280, "margin_x": 30},
            },
        },
    )

    fake = MagicMock()
    fake.create_composite.return_value = _fake_composite(
        "/data/_internal/composites/backdrop-x.mp4",
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.composite_video.MediaEngineClient",
        return_value=cm,
    ):
        result = CompositeVideoPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "background", "asset": a},
                {"slot": "foreground", "asset": b},
            ],
            mock_mode=False,
        )

    fake.create_composite.assert_called_once()
    kwargs = fake.create_composite.call_args.kwargs
    assert kwargs["clip_urls"] == ["/data/bg.mp4", "/data/fg.mp4"]
    assert kwargs["layout_spec"]["kind"] == "backdrop"
    assert kwargs["layout_spec"]["options"]["fg_width"] == 280

    assert result.file_path == "/data/_internal/composites/backdrop-x.mp4"
    assert result.extra_source_spec["layout_kind"] == "backdrop"
    assert result.extra_source_spec["input_count"] == 2


def test_composite_media_engine_failure_propagates() -> None:
    ws = _make_workspace("v7c_fail@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    a = _make_clip(ws)
    b = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="composite_video",
        params={"layout_spec": {"kind": "pip", "options": {}}},
    )

    fake = MagicMock()
    fake.create_composite.side_effect = MediaEngineError(
        "explode", status_code=500,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.composite_video.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc:
            CompositeVideoPrimitive.execute(
                step=step,
                resolved_inputs=[
                    {"slot": "base", "asset": a},
                    {"slot": "pip", "asset": b},
                ],
                mock_mode=False,
            )
    assert "media-engine" in str(exc.value).lower()


# ---- MixAudioPrimitive --------------------------------------------


def test_mix_audio_mock_mode_returns_stub() -> None:
    ws = _make_workspace("v7m1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_clip(ws, "/data/voice.mp4", 5000)
    music = _make_audio(ws, "/data/music.mp3", 60000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="mix_audio",
        params={"mix_spec": {"music_gain_db": -15}},
    )
    result = MixAudioPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": base},
            {"slot": "music", "asset": music},
        ],
        mock_mode=True,
    )
    assert result.asset_type == AssetType.CLIP
    assert result.duration_ms == base.duration_ms
    assert result.extra_source_spec["mock"] is True
    assert result.extra_source_spec["mix_spec"]["music_gain_db"] == -15


def test_mix_audio_requires_one_clip_and_one_audio() -> None:
    ws = _make_workspace("v7m_min@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    base = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="mix_audio",
    )
    # No audio at all
    with pytest.raises(PrimitiveError) as exc:
        MixAudioPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": base}],
            mock_mode=False,
        )
    assert "AUDIO" in str(exc.value)


def test_mix_audio_rejects_second_clip() -> None:
    ws = _make_workspace("v7m_two_clips@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    a = _make_clip(ws, "/data/a.mp4")
    b = _make_clip(ws, "/data/b.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="mix_audio",
    )
    with pytest.raises(PrimitiveError) as exc:
        MixAudioPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": a},
                {"slot": "second_base", "asset": b},
            ],
            mock_mode=False,
        )
    assert "one CLIP" in str(exc.value)


def test_mix_audio_real_mode_calls_media_engine() -> None:
    ws = _make_workspace("v7m_real@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    base = _make_clip(ws, "/data/voice.mp4", 5000)
    music = _make_audio(ws, "/data/music.mp3", 60000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="mix_audio",
        params={"mix_spec": {"music_gain_db": -20, "fade_in_ms": 500}},
    )

    fake = MagicMock()
    fake.mix_audio.return_value = _fake_mix("/data/_internal/mixes/x.mp4")
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.mix_audio.MediaEngineClient",
        return_value=cm,
    ):
        result = MixAudioPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": base},
                {"slot": "music", "asset": music},
            ],
            mock_mode=False,
        )

    fake.mix_audio.assert_called_once()
    kwargs = fake.mix_audio.call_args.kwargs
    assert kwargs["base_clip_url"] == "/data/voice.mp4"
    assert kwargs["audio_urls"] == ["/data/music.mp3"]
    assert kwargs["mix_spec"]["music_gain_db"] == -20

    assert result.file_path == "/data/_internal/mixes/x.mp4"


# ---- starters: pip_layout -----------------------------------------


def test_pip_layout_starter_creates_one_step_composition() -> None:
    ws = _make_workspace("v7sp_pip@test")
    sp = _make_teammate(ws)
    base = _make_clip(ws, "/data/base.mp4")
    pip = _make_clip(ws, "/data/pip.mp4")
    c = pip_layout(
        workspace=ws, spokesperson=sp,
        base_clip=base, pip_clip=pip,
        mock_mode=True,
    )
    assert c.template_kind == "pip_layout"
    step = c.steps.first()
    assert step.primitive == "composite_video"
    assert step.params["layout_spec"]["kind"] == "pip"
    asset_ids = {e["asset_id"] for e in step.inputs}
    assert asset_ids == {str(base.id), str(pip.id)}


def test_pip_layout_rejects_cross_workspace_assets() -> None:
    ws_a = _make_workspace("v7px_a@test", "A")
    ws_b = _make_workspace("v7px_b@test", "B")
    sp_a = _make_teammate(ws_a)
    base = _make_clip(ws_a)
    foreign = _make_clip(ws_b)
    with pytest.raises(ValueError):
        pip_layout(
            workspace=ws_a, spokesperson=sp_a,
            base_clip=base, pip_clip=foreign,
            mock_mode=True,
        )


def test_pip_layout_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v7p_e2e@test")
    sp = _make_teammate(ws)
    base = _make_clip(ws, "/data/base.mp4", 5000)
    pip = _make_clip(ws, "/data/pip.mp4", 5000)
    c = pip_layout(
        workspace=ws, spokesperson=sp,
        base_clip=base, pip_clip=pip,
        mock_mode=True,
    )
    result = execute_composition.apply(args=[str(c.pk)]).get()
    assert result["status"] == "completed"
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    assert c.final_asset.source_spec["layout_kind"] == "pip"


# ---- starters: backdrop_layout (V8 building block) ----------------


def test_backdrop_layout_creates_composition_with_backdrop_kind() -> None:
    ws = _make_workspace("v7sp_bd@test")
    sp = _make_teammate(ws)
    bg = _make_clip(ws, "/data/cinematic.mp4")
    fg = _make_clip(ws, "/data/avatar.mp4")
    c = backdrop_layout(
        workspace=ws, spokesperson=sp,
        background_clip=bg, foreground_clip=fg,
        fg_width=280, mock_mode=True,
    )
    assert c.template_kind == "backdrop_layout"
    step = c.steps.first()
    assert step.params["layout_spec"]["kind"] == "backdrop"
    assert step.params["layout_spec"]["options"]["fg_width"] == 280
    # Input order: [0] = background, [1] = foreground
    assert step.inputs[0]["slot"] == "background"
    assert step.inputs[0]["asset_id"] == str(bg.id)
    assert step.inputs[1]["slot"] == "foreground"
    assert step.inputs[1]["asset_id"] == str(fg.id)


def test_backdrop_layout_executes_end_to_end() -> None:
    ws = _make_workspace("v7bd_e2e@test")
    sp = _make_teammate(ws)
    bg = _make_clip(ws, "/data/bg.mp4")
    fg = _make_clip(ws, "/data/fg.mp4")
    c = backdrop_layout(
        workspace=ws, spokesperson=sp,
        background_clip=bg, foreground_clip=fg,
        mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED


# ---- starters: cohost_layout --------------------------------------


def test_cohost_layout_creates_composition() -> None:
    ws = _make_workspace("v7sp_co@test")
    sp = _make_teammate(ws)
    main = _make_clip(ws, "/data/main.mp4")
    cohost = _make_clip(ws, "/data/cohost.mp4")
    c = cohost_layout(
        workspace=ws, spokesperson=sp,
        main_clip=main, cohost_clip=cohost,
        cohost_width=200, mock_mode=True,
    )
    assert c.template_kind == "cohost_layout"
    step = c.steps.first()
    assert step.params["layout_spec"]["kind"] == "cohost"
    assert step.params["layout_spec"]["options"]["cohost_width"] == 200


# ---- starters: broll_splice ---------------------------------------


def test_broll_splice_creates_composition_with_cutaway_window() -> None:
    ws = _make_workspace("v7sp_br@test")
    sp = _make_teammate(ws)
    base = _make_clip(ws, "/data/avatar.mp4", 10000)
    broll = _make_clip(ws, "/data/cinematic.mp4", 5000)
    c = broll_splice(
        workspace=ws, spokesperson=sp,
        base_clip=base, broll_clip=broll,
        cutaway_start_s=3.0, cutaway_end_s=6.5,
        mock_mode=True,
    )
    assert c.template_kind == "broll_splice"
    step = c.steps.first()
    spec = step.params["layout_spec"]
    assert spec["kind"] == "broll"
    assert spec["options"]["cutaway_start_s"] == 3.0
    assert spec["options"]["cutaway_end_s"] == 6.5


def test_broll_splice_rejects_invalid_window() -> None:
    ws = _make_workspace("v7br_bad@test")
    sp = _make_teammate(ws)
    base = _make_clip(ws)
    broll = _make_clip(ws)
    with pytest.raises(ValueError):
        broll_splice(
            workspace=ws, spokesperson=sp,
            base_clip=base, broll_clip=broll,
            cutaway_start_s=5.0, cutaway_end_s=3.0,  # inverted
            mock_mode=True,
        )


# ---- starters: music_bed_pass -------------------------------------


def test_music_bed_pass_creates_composition() -> None:
    ws = _make_workspace("v7sp_mb@test")
    sp = _make_teammate(ws)
    base = _make_clip(ws, "/data/voice.mp4")
    music = _make_audio(ws, "/data/music.mp3")
    c = music_bed_pass(
        workspace=ws, spokesperson=sp,
        base_clip=base, music_asset=music,
        music_gain_db=-20, fade_in_ms=500,
        mock_mode=True,
    )
    assert c.template_kind == "music_bed_pass"
    step = c.steps.first()
    assert step.primitive == "mix_audio"
    spec = step.params["mix_spec"]
    assert spec["music_gain_db"] == -20.0
    assert spec["fade_in_ms"] == 500


def test_music_bed_pass_executes_end_to_end() -> None:
    ws = _make_workspace("v7mb_e2e@test")
    sp = _make_teammate(ws)
    base = _make_clip(ws, "/data/voice.mp4", 5000)
    music = _make_audio(ws)
    c = music_bed_pass(
        workspace=ws, spokesperson=sp,
        base_clip=base, music_asset=music,
        mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    assert c.final_asset.source_spec["primitive_kind"] == "mix_audio"


# ---- cost estimation ---------------------------------------------


def test_composite_cost_estimate_is_nonzero() -> None:
    assert CompositeVideoPrimitive.estimate_cost({}) > 0


def test_mix_audio_cost_estimate_is_nonzero() -> None:
    assert MixAudioPrimitive.estimate_cost({}) > 0


def test_mix_audio_cheaper_than_composite() -> None:
    """Sanity check: audio mix doesn't re-encode video, so it
    should cost less than composite. Both are bounded
    constants; this asserts the ordering."""
    assert MixAudioPrimitive.estimate_cost({}) < CompositeVideoPrimitive.estimate_cost({})
