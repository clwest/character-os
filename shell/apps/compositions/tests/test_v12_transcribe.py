"""V12 tests — transcribe primitive + add_captions auto mode +
recut_teaser starter.

First net-new capability beyond what the hackathon shipped.
OpenAI Whisper transcription, plus the composition pattern
("take a rendered ad, recut it as a vertical teaser") that
unlocks teaser generation as a first-class operator surface.
"""
from __future__ import annotations

import json
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
from apps.compositions.primitives.polish import AddCaptionsPrimitive
from apps.compositions.primitives.transcribe import TranscribePrimitive
from apps.compositions.starters import recut_teaser
from apps.compositions.tasks import execute_composition
from apps.compositions.transcription import (
    Segment,
    pick_strongest_segment,
)
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import (
    MediaEngineError,
    TranscribeResult,
    TranscriptSegment,
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


def _make_teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name="Sp",
        runway_avatar_id="fake",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


def _make_clip(
    ws,
    file_path: str = "/data/_assets/clip.mp4",
    duration_ms: int | None = 10000,
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path=file_path, duration_ms=duration_ms,
        mime_type="video/mp4",
    )


def _make_audio(
    ws,
    file_path: str = "/data/_assets/audio.mp3",
    duration_ms: int | None = 5000,
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path=file_path, duration_ms=duration_ms,
        mime_type="audio/mpeg",
    )


def _make_transcript(
    ws,
    segments: list[dict] | None = None,
) -> Asset:
    """Create a TRANSCRIPT asset with V12-shaped inline_content."""
    payload = {
        "segments": segments or [
            {"start_s": 0.0, "end_s": 2.5, "text": "Hello there."},
            {"start_s": 2.5, "end_s": 5.0, "text": "Welcome aboard."},
        ],
        "duration_seconds": 5.0,
        "language": "en",
        "full_text": "Hello there. Welcome aboard.",
    }
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.TRANSCRIPT,
        inline_content=json.dumps(payload),
        mime_type="application/json",
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _fake_transcribe_result(
    segments: list[tuple[float, float, str]] | None = None,
) -> TranscribeResult:
    segs = segments or [
        (0.0, 2.5, "Hello world."),
        (2.5, 5.0, "This is a test."),
    ]
    return TranscribeResult(
        segments=[
            TranscriptSegment(start_s=s, end_s=e, text=t)
            for s, e, t in segs
        ],
        duration_seconds=segs[-1][1],
        language="en",
        full_text=" ".join(t for _, _, t in segs),
        mock_mode=False,
    )


def _patched_client(method_name: str, return_value, *, target_module: str):
    fake = MagicMock()
    getattr(fake, method_name).return_value = return_value
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- TranscribePrimitive ------------------------------------------


def test_transcribe_mock_mode_returns_deterministic_transcript() -> None:
    ws = _make_workspace("v12t1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="transcribe",
    )
    r = TranscribePrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "source", "asset": clip}],
        mock_mode=True,
    )
    assert r.asset_type == AssetType.TRANSCRIPT
    assert r.mime_type == "application/json"
    payload = json.loads(r.inline_content)
    assert isinstance(payload["segments"], list)
    assert len(payload["segments"]) >= 1
    assert r.extra_source_spec["mock"] is True
    assert r.extra_source_spec["segment_count"] >= 1


def test_transcribe_accepts_audio_input() -> None:
    ws = _make_workspace("v12t2@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    audio = _make_audio(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="transcribe",
    )
    r = TranscribePrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "source", "asset": audio}],
        mock_mode=True,
    )
    assert r.asset_type == AssetType.TRANSCRIPT
    assert r.extra_source_spec["source_asset_type"] == AssetType.AUDIO


def test_transcribe_rejects_image_input() -> None:
    ws = _make_workspace("v12t3@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    img = Asset.objects.create(
        workspace=ws, asset_type=AssetType.IMAGE,
        file_path="/data/img.png",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="transcribe",
    )
    with pytest.raises(PrimitiveError):
        TranscribePrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": img}],
            mock_mode=False,
        )


def test_transcribe_real_mode_call_shape() -> None:
    ws = _make_workspace("v12t4@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws, "/data/talking_head.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="transcribe",
    )
    cm, fake = _patched_client(
        "transcribe", _fake_transcribe_result(),
        target_module="apps.compositions.primitives.transcribe",
    )
    with patch(
        "apps.compositions.primitives.transcribe.MediaEngineClient",
        return_value=cm,
    ):
        r = TranscribePrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": clip}],
            mock_mode=False,
        )
    fake.transcribe.assert_called_once()
    kwargs = fake.transcribe.call_args.kwargs
    assert kwargs["source_url"] == "/data/talking_head.mp4"
    assert kwargs["extract_audio"] is True  # auto: CLIP → True

    payload = json.loads(r.inline_content)
    assert len(payload["segments"]) == 2
    assert payload["segments"][0]["text"] == "Hello world."
    assert payload["language"] == "en"


def test_transcribe_audio_input_skips_extraction_by_default() -> None:
    ws = _make_workspace("v12t5@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    audio = _make_audio(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="transcribe",
    )
    cm, fake = _patched_client(
        "transcribe", _fake_transcribe_result(),
        target_module="apps.compositions.primitives.transcribe",
    )
    with patch(
        "apps.compositions.primitives.transcribe.MediaEngineClient",
        return_value=cm,
    ):
        TranscribePrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": audio}],
            mock_mode=False,
        )
    kwargs = fake.transcribe.call_args.kwargs
    # AUDIO input → extract_audio default False
    assert kwargs["extract_audio"] is False


def test_transcribe_propagates_media_engine_failure() -> None:
    ws = _make_workspace("v12t6@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="transcribe",
    )
    fake = MagicMock()
    fake.transcribe.side_effect = MediaEngineError("whisper down", status_code=502)
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.transcribe.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError):
            TranscribePrimitive.execute(
                step=step,
                resolved_inputs=[{"slot": "source", "asset": clip}],
                mock_mode=False,
            )


# ---- add_captions auto mode (V9 extension) ------------------------


def test_add_captions_auto_mode_reads_transcript_input() -> None:
    """V12: when params['captions'] is empty AND a TRANSCRIPT
    input is supplied, the primitive derives captions from
    the transcript's segments."""
    ws = _make_workspace("v12ac1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws)
    transcript = _make_transcript(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_captions",
        params={},  # no captions list — should fall back to transcript
    )
    r = AddCaptionsPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": clip},
            {"slot": "transcript", "asset": transcript},
        ],
        mock_mode=True,
    )
    assert r.asset_type == AssetType.CLIP
    # Auto-mode set caption_count from the transcript's segments
    assert r.extra_source_spec["caption_count"] == 2


def test_add_captions_manual_overrides_auto() -> None:
    """When both params['captions'] AND a TRANSCRIPT input are
    supplied, the operator-supplied list wins (explicit beats
    inferred)."""
    ws = _make_workspace("v12ac2@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws)
    transcript = _make_transcript(ws)  # 2 segments
    manual = [
        {"start_s": 0, "end_s": 1, "text": "Manual A"},
        {"start_s": 1, "end_s": 2, "text": "Manual B"},
        {"start_s": 2, "end_s": 3, "text": "Manual C"},
    ]
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_captions",
        params={"captions": manual},
    )
    r = AddCaptionsPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": clip},
            {"slot": "transcript", "asset": transcript},
        ],
        mock_mode=True,
    )
    assert r.extra_source_spec["caption_count"] == 3  # manual list


def test_add_captions_auto_mode_handles_bare_array_transcript() -> None:
    """Some upstream transcripts may store a bare array instead
    of the {segments: [...]} wrapper. Auto-mode tolerates
    both shapes."""
    ws = _make_workspace("v12ac3@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws)
    bare = Asset.objects.create(
        workspace=ws, asset_type=AssetType.TRANSCRIPT,
        inline_content=json.dumps([
            {"start_s": 0.0, "end_s": 2.0, "text": "Bare A"},
            {"start_s": 2.0, "end_s": 4.0, "text": "Bare B"},
        ]),
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_captions",
        params={},
    )
    r = AddCaptionsPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": clip},
            {"slot": "transcript", "asset": bare},
        ],
        mock_mode=True,
    )
    assert r.extra_source_spec["caption_count"] == 2


def test_add_captions_still_rejects_no_source_at_all() -> None:
    """No captions + no transcript = error. The auto-mode
    fallback only triggers when a TRANSCRIPT is present."""
    ws = _make_workspace("v12ac4@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="add_captions",
        params={},
    )
    with pytest.raises(PrimitiveError):
        AddCaptionsPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=False,
        )


# ---- pick_strongest_segment helper --------------------------------


def test_pick_strongest_segment_first_criterion() -> None:
    segs = [
        Segment(0.0, 2.0, "A"),
        Segment(2.0, 6.0, "B"),
    ]
    picked = pick_strongest_segment(segs, criterion="first")
    assert picked.text == "A"


def test_pick_strongest_segment_last_criterion() -> None:
    segs = [
        Segment(0.0, 2.0, "A"),
        Segment(2.0, 6.0, "B"),
    ]
    picked = pick_strongest_segment(segs, criterion="last")
    assert picked.text == "B"


def test_pick_strongest_segment_longest_criterion() -> None:
    segs = [
        Segment(0.0, 1.0, "Short"),
        Segment(1.0, 10.0, "Long"),
        Segment(10.0, 12.0, "Medium"),
    ]
    picked = pick_strongest_segment(segs, criterion="longest")
    assert picked.text == "Long"


def test_pick_strongest_segment_hook_falls_back_when_no_api_key() -> None:
    """Missing OPENAI_API_KEY → falls back to longest. Same
    graceful degradation pattern as script_synthesis."""
    segs = [
        Segment(0.0, 1.0, "Short"),
        Segment(1.0, 8.0, "Long hook"),
    ]
    with patch.dict("os.environ", {}, clear=False), patch(
        "apps.compositions.transcription._is_force_mock",
        return_value=False,
    ):
        import os as _os
        _os.environ.pop("OPENAI_API_KEY", None)
        picked = pick_strongest_segment(segs, criterion="hook")
    assert picked.text == "Long hook"


def test_pick_strongest_segment_empty_raises() -> None:
    with pytest.raises(ValueError):
        pick_strongest_segment([], criterion="hook")


# ---- recut_teaser starter -----------------------------------------


def test_recut_teaser_creates_two_step_composition() -> None:
    ws = _make_workspace("v12rt1@test")
    sp = _make_teammate(ws)
    src = _make_clip(ws, duration_ms=30000)
    c = recut_teaser(
        workspace=ws, spokesperson=sp,
        source_clip=src, mock_mode=True,
    )
    assert c.template_kind == "recut_teaser"
    steps = list(c.steps.all().order_by("position"))
    assert len(steps) == 2
    assert steps[0].primitive == "trim_clip"
    assert steps[1].primitive == "reformat_clip"


def test_recut_teaser_trim_window_matches_picked_segment() -> None:
    """Mock-mode picks 'longest' from the stub segments. The
    stub's middle segment is 2.5–6.0s, which is the longest."""
    ws = _make_workspace("v12rt2@test")
    sp = _make_teammate(ws)
    src = _make_clip(ws)
    c = recut_teaser(
        workspace=ws, spokesperson=sp,
        source_clip=src, mock_mode=True,
    )
    trim_step = c.steps.get(position=0)
    # Stub segment 2.5-6.0s (longest of the three stub segments)
    assert trim_step.params["start_ms"] == 2500
    assert trim_step.params["end_ms"] == 6000


def test_recut_teaser_reformat_step_chains_to_trim_output() -> None:
    ws = _make_workspace("v12rt3@test")
    sp = _make_teammate(ws)
    src = _make_clip(ws)
    c = recut_teaser(
        workspace=ws, spokesperson=sp,
        source_clip=src, mock_mode=True,
    )
    reformat = c.steps.get(position=1)
    assert reformat.inputs[0]["from_step_position"] == 0
    assert reformat.params["target_ratio"] == "720:1280"


def test_recut_teaser_accepts_operator_supplied_transcript() -> None:
    """When the operator passes ``transcript=...``, the starter
    skips the synchronous Whisper call. Useful for chained
    compositions or test setups."""
    ws = _make_workspace("v12rt4@test")
    sp = _make_teammate(ws)
    src = _make_clip(ws)
    custom_transcript = [
        {"start_s": 1.0, "end_s": 4.5, "text": "Quick line."},
        {"start_s": 4.5, "end_s": 12.0, "text": "Much longer winning hook."},
    ]
    c = recut_teaser(
        workspace=ws, spokesperson=sp,
        source_clip=src, transcript=custom_transcript,
        mock_mode=True,
    )
    trim_step = c.steps.get(position=0)
    # mock_mode forces "longest" → the 4.5-12.0s segment wins
    assert trim_step.params["start_ms"] == 4500
    assert trim_step.params["end_ms"] == 12000


def test_recut_teaser_respects_target_ratio_param() -> None:
    ws = _make_workspace("v12rt5@test")
    sp = _make_teammate(ws)
    src = _make_clip(ws)
    c = recut_teaser(
        workspace=ws, spokesperson=sp,
        source_clip=src, target_ratio="960:960",
        mock_mode=True,
    )
    reformat = c.steps.get(position=1)
    assert reformat.params["target_ratio"] == "960:960"


def test_recut_teaser_rejects_non_clip_source() -> None:
    ws = _make_workspace("v12rt6@test")
    sp = _make_teammate(ws)
    audio = _make_audio(ws)
    with pytest.raises(ValueError):
        recut_teaser(
            workspace=ws, spokesperson=sp,
            source_clip=audio, mock_mode=True,
        )


def test_recut_teaser_rejects_cross_workspace_clip() -> None:
    ws_a = _make_workspace("v12rt_x_a@test", "A")
    ws_b = _make_workspace("v12rt_x_b@test", "B")
    sp_a = _make_teammate(ws_a)
    foreign = _make_clip(ws_b)
    with pytest.raises(ValueError):
        recut_teaser(
            workspace=ws_a, spokesperson=sp_a,
            source_clip=foreign, mock_mode=True,
        )


def test_recut_teaser_rejects_empty_supplied_transcript() -> None:
    ws = _make_workspace("v12rt_empty@test")
    sp = _make_teammate(ws)
    src = _make_clip(ws)
    with pytest.raises(ValueError):
        recut_teaser(
            workspace=ws, spokesperson=sp,
            source_clip=src, transcript=[],
            mock_mode=True,
        )


def test_recut_teaser_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v12rt_e2e@test")
    sp = _make_teammate(ws)
    src = _make_clip(ws, duration_ms=30000)
    c = recut_teaser(
        workspace=ws, spokesperson=sp,
        source_clip=src, mock_mode=True,
    )
    result = execute_composition.apply(args=[str(c.pk)]).get()
    assert result["status"] == "completed"
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    # Final asset is the reformat output (the recut teaser MP4)
    assert c.final_asset.source_spec["primitive_kind"] == "reformat_clip"
    assert c.final_asset.source_spec["target_ratio"] == "720:1280"


# ---- cost --------------------------------------------------------


def test_transcribe_cost_estimate_is_realistic() -> None:
    assert TranscribePrimitive.estimate_cost({}) >= 25_000
