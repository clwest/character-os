"""V14 tests — audio_extract primitive + dialogue_scene starter.

Ports the hackathon's dialogue_service.py pattern. v14 adds
two pieces: audio_extract (unblocks the deferred V13
storyboard_voiced) and dialogue_scene (the N-character skit
recipe with per-line avatar overrides).
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
from apps.compositions.primitives.audio_extract import (
    SUPPORTED_AUDIO_FORMATS,
    AudioExtractPrimitive,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.starters import dialogue_scene
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


def _make_spokesperson(
    ws: Workspace,
    name: str = "Sp",
    avatar_id: str = "fake-avatar",
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=avatar_id,
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


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _fake_processed(output_url: str = "/data/_internal/audio_extracts/x.mp3") -> ProcessedClipResult:
    return ProcessedClipResult(
        output_url=output_url, duration_seconds=5.0,
        size_bytes=50000, mock_mode=False,
    )


# ---- AudioExtractPrimitive ----------------------------------------


def test_audio_extract_supports_three_formats() -> None:
    assert SUPPORTED_AUDIO_FORMATS == {"mp3", "aac", "wav"}


def test_audio_extract_mock_mode_returns_audio_asset() -> None:
    ws = _make_workspace("v14ae1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws, duration_ms=8000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="audio_extract",
    )
    r = AudioExtractPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "base", "asset": clip}],
        mock_mode=True,
    )
    assert r.asset_type == AssetType.AUDIO
    assert r.duration_ms == 8000
    assert r.mime_type == "audio/mpeg"
    assert r.extra_source_spec["mock"] is True
    assert r.extra_source_spec["format"] == "mp3"


def test_audio_extract_supports_format_param() -> None:
    ws = _make_workspace("v14ae2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="audio_extract",
        params={"format": "wav"},
    )
    r = AudioExtractPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "base", "asset": clip}],
        mock_mode=True,
    )
    assert r.extra_source_spec["format"] == "wav"
    assert r.mime_type == "audio/wav"


def test_audio_extract_rejects_unknown_format() -> None:
    ws = _make_workspace("v14ae3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="audio_extract",
        params={"format": "flac"},
    )
    with pytest.raises(PrimitiveError):
        AudioExtractPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=False,
        )


def test_audio_extract_rejects_audio_input() -> None:
    ws = _make_workspace("v14ae4@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    audio = Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/a.mp3",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="audio_extract",
    )
    with pytest.raises(PrimitiveError):
        AudioExtractPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": audio}],
            mock_mode=False,
        )


def test_audio_extract_real_mode_call_shape() -> None:
    ws = _make_workspace("v14ae5@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws, "/data/talking_head.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="audio_extract",
        params={"format": "mp3"},
    )
    fake = MagicMock()
    fake.audio_extract.return_value = _fake_processed("/data/_internal/audio_extracts/extracted.mp3")
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.audio_extract.MediaEngineClient",
        return_value=cm,
    ):
        r = AudioExtractPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "base", "asset": clip}],
            mock_mode=False,
        )
    fake.audio_extract.assert_called_once()
    kwargs = fake.audio_extract.call_args.kwargs
    assert kwargs["clip_url"] == "/data/talking_head.mp4"
    assert kwargs["format"] == "mp3"
    assert r.asset_type == AssetType.AUDIO


def test_audio_extract_propagates_media_engine_failure() -> None:
    ws = _make_workspace("v14ae6@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    clip = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="audio_extract",
    )
    fake = MagicMock()
    fake.audio_extract.side_effect = MediaEngineError("ffmpeg died", status_code=500)
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.audio_extract.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError):
            AudioExtractPrimitive.execute(
                step=step,
                resolved_inputs=[{"slot": "base", "asset": clip}],
                mock_mode=False,
            )


# ---- dialogue_scene starter ---------------------------------------


def test_dialogue_scene_two_character_creates_three_step_composition() -> None:
    """Two lines → 2 speech steps + 1 concat = 3 steps total."""
    ws = _make_workspace("v14ds1@test")
    sp_a = _make_spokesperson(ws, name="Riggs", avatar_id="avatar_riggs")
    sp_b = _make_spokesperson(ws, name="Sasha", avatar_id="avatar_sasha")
    c = dialogue_scene(
        workspace=ws, primary_spokesperson=sp_a,
        lines=[
            {"spokesperson": sp_a, "text": "Welcome to the show."},
            {"spokesperson": sp_b, "text": "Glad to be here."},
        ],
        mock_mode=True,
    )
    assert c.template_kind == "dialogue_scene"
    assert c.spokesperson_id == sp_a.pk  # primary owns the composition
    steps = list(c.steps.all().order_by("position"))
    assert len(steps) == 3
    assert steps[0].primitive == "generate_avatar_speech"
    assert steps[1].primitive == "generate_avatar_speech"
    assert steps[2].primitive == "concat_clips"


def test_dialogue_scene_per_line_avatar_override_uses_each_spokesperson() -> None:
    ws = _make_workspace("v14ds2@test")
    sp_a = _make_spokesperson(ws, name="A", avatar_id="avatar_a")
    sp_b = _make_spokesperson(ws, name="B", avatar_id="avatar_b")
    sp_c = _make_spokesperson(ws, name="C", avatar_id="avatar_c")
    c = dialogue_scene(
        workspace=ws, primary_spokesperson=sp_a,
        lines=[
            {"spokesperson": sp_a, "text": "Line one."},
            {"spokesperson": sp_b, "text": "Line two."},
            {"spokesperson": sp_c, "text": "Line three."},
        ],
        mock_mode=True,
    )
    speech_steps = list(c.steps.filter(primitive="generate_avatar_speech").order_by("position"))
    assert len(speech_steps) == 3
    assert speech_steps[0].params["spokesperson_avatar_id"] == "avatar_a"
    assert speech_steps[0].params["script"] == "Line one."
    assert speech_steps[1].params["spokesperson_avatar_id"] == "avatar_b"
    assert speech_steps[1].params["script"] == "Line two."
    assert speech_steps[2].params["spokesperson_avatar_id"] == "avatar_c"
    assert speech_steps[2].params["script"] == "Line three."


def test_dialogue_scene_concat_step_chains_to_all_speech_outputs() -> None:
    ws = _make_workspace("v14ds3@test")
    sp_a = _make_spokesperson(ws, name="A", avatar_id="avatar_a")
    sp_b = _make_spokesperson(ws, name="B", avatar_id="avatar_b")
    c = dialogue_scene(
        workspace=ws, primary_spokesperson=sp_a,
        lines=[
            {"spokesperson": sp_a, "text": "L1"},
            {"spokesperson": sp_b, "text": "L2"},
            {"spokesperson": sp_a, "text": "L3"},
        ],
        mock_mode=True,
    )
    concat = c.steps.get(primitive="concat_clips")
    positions = [e["from_step_position"] for e in concat.inputs]
    assert positions == [0, 1, 2]


def test_dialogue_scene_single_line_skips_concat() -> None:
    """Degenerate-case optimization — one line means just one
    speech step + no concat (mirrors long_form_ad pattern)."""
    ws = _make_workspace("v14ds4@test")
    sp = _make_spokesperson(ws)
    c = dialogue_scene(
        workspace=ws, primary_spokesperson=sp,
        lines=[{"spokesperson": sp, "text": "Only one line."}],
        mock_mode=True,
    )
    steps = list(c.steps.all())
    assert len(steps) == 1
    assert steps[0].primitive == "generate_avatar_speech"


def test_dialogue_scene_rejects_empty_lines() -> None:
    ws = _make_workspace("v14ds5@test")
    sp = _make_spokesperson(ws)
    with pytest.raises(ValueError):
        dialogue_scene(
            workspace=ws, primary_spokesperson=sp,
            lines=[], mock_mode=True,
        )


def test_dialogue_scene_rejects_line_with_empty_text() -> None:
    ws = _make_workspace("v14ds6@test")
    sp = _make_spokesperson(ws)
    with pytest.raises(ValueError):
        dialogue_scene(
            workspace=ws, primary_spokesperson=sp,
            lines=[{"spokesperson": sp, "text": "  "}],
            mock_mode=True,
        )


def test_dialogue_scene_rejects_cross_workspace_speaker() -> None:
    ws_a = _make_workspace("v14ds_xa@test", "A")
    ws_b = _make_workspace("v14ds_xb@test", "B")
    sp_a = _make_spokesperson(ws_a, name="A_speaker", avatar_id="av_a")
    foreign = _make_spokesperson(ws_b, name="Foreign", avatar_id="av_f")
    with pytest.raises(ValueError):
        dialogue_scene(
            workspace=ws_a, primary_spokesperson=sp_a,
            lines=[
                {"spokesperson": sp_a, "text": "ok"},
                {"spokesperson": foreign, "text": "uh oh"},
            ],
            mock_mode=True,
        )


def test_dialogue_scene_rejects_speaker_with_no_avatar() -> None:
    ws = _make_workspace("v14ds_noava@test")
    sp_with = _make_spokesperson(ws, name="Has", avatar_id="av_x")
    sp_without = Spokesperson.objects.create(
        workspace=ws, name="No Avatar",
        runway_avatar_id="",  # empty
        business_brief="b",
    )
    with pytest.raises(ValueError):
        dialogue_scene(
            workspace=ws, primary_spokesperson=sp_with,
            lines=[
                {"spokesperson": sp_with, "text": "first"},
                {"spokesperson": sp_without, "text": "fails"},
            ],
            mock_mode=True,
        )


def test_dialogue_scene_rejects_primary_outside_workspace() -> None:
    ws_a = _make_workspace("v14ds_paxa@test", "A")
    ws_b = _make_workspace("v14ds_paxb@test", "B")
    foreign_primary = _make_spokesperson(ws_b, name="ForeignPrimary", avatar_id="av")
    with pytest.raises(ValueError):
        dialogue_scene(
            workspace=ws_a, primary_spokesperson=foreign_primary,
            lines=[{"spokesperson": foreign_primary, "text": "x"}],
            mock_mode=True,
        )


def test_dialogue_scene_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v14ds_e2e@test")
    sp_a = _make_spokesperson(ws, name="Sasha", avatar_id="av_sasha")
    sp_b = _make_spokesperson(ws, name="Donny", avatar_id="av_donny")
    c = dialogue_scene(
        workspace=ws, primary_spokesperson=sp_a,
        lines=[
            {"spokesperson": sp_a, "text": "Welcome to our coffee shop."},
            {"spokesperson": sp_b, "text": "Glad to be a customer here."},
            {"spokesperson": sp_a, "text": "Hope to see you again soon."},
        ],
        mock_mode=True,
    )
    result = execute_composition.apply(args=[str(c.pk)]).get()
    assert result["status"] == "completed"
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    # Final asset is the concat output
    assert c.final_asset.source_spec["primitive_kind"] == "concat_clips"
    assert c.final_asset.source_spec["input_count"] == 3


def test_dialogue_scene_intermediate_assets_persist() -> None:
    ws = _make_workspace("v14ds_inter@test")
    sp_a = _make_spokesperson(ws, name="A", avatar_id="av_a")
    sp_b = _make_spokesperson(ws, name="B", avatar_id="av_b")
    c = dialogue_scene(
        workspace=ws, primary_spokesperson=sp_a,
        lines=[
            {"spokesperson": sp_a, "text": "first line"},
            {"spokesperson": sp_b, "text": "second line"},
        ],
        mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()
    # 2 speech outputs + 1 concat output = 3 produced assets
    assert c.produced_assets.count() == 3
    # All are CLIP type
    for asset in c.produced_assets.all():
        assert asset.asset_type == AssetType.CLIP


# ---- cost --------------------------------------------------------


def test_audio_extract_cost_is_cheap() -> None:
    """audio_extract is local ffmpeg only; should sit alongside
    V9's polish primitives, well below provider-billed ones."""
    cost = AudioExtractPrimitive.estimate_cost({})
    assert cost > 0
    assert cost < 5_000  # cheaper than any provider-billed primitive


# ---- SESSION 196 slice 2 — concat_clips result_role override ----


def test_concat_clips_default_role_is_backdrop_unchanged() -> None:
    """Backwards-compat: when no ``result_role`` param is set, the
    primitive emits with ``role=BACKDROP`` — the SESSION 186 A2
    default. V18 backdrop chain + storyboard_voiced step 6 + every
    pre-SESSION-196 caller relies on this."""
    from apps.compositions.primitives.concat_clips import ConcatClipsPrimitive

    ws = _make_workspace("v196concat_default@test")
    sp = _make_spokesperson(ws)
    clip = Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/_assets/a.mp4", duration_ms=5000,
        mime_type="video/mp4",
    )

    from apps.compositions.models import Composition, CompositionStep
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp,
        name="t", template_kind="talking_head_with_backdrop",
        mock_mode=True,
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="concat_clips", inputs=[], params={},
    )
    result = ConcatClipsPrimitive.execute(
        step, [{"slot": "clip", "asset": clip}], mock_mode=True,
    )
    assert result.role == "backdrop"


def test_concat_clips_honors_result_role_override() -> None:
    """When ``result_role`` is set in step.params, the primitive
    stamps that value instead of BACKDROP. Slice 2's mechanism."""
    from apps.compositions.primitives.concat_clips import ConcatClipsPrimitive

    ws = _make_workspace("v196concat_override@test")
    sp = _make_spokesperson(ws)
    clip = Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/_assets/a.mp4", duration_ms=5000,
        mime_type="video/mp4",
    )

    from apps.compositions.models import Composition, CompositionStep
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp,
        name="t", template_kind="dialogue_scene",
        mock_mode=True,
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="concat_clips", inputs=[],
        params={"result_role": "composite_output"},
    )
    result = ConcatClipsPrimitive.execute(
        step, [{"slot": "clip", "asset": clip}], mock_mode=True,
    )
    assert result.role == "composite_output"
    # extra_source_spec records the override so the Asset's audit
    # trail captures which role was stamped + why.
    assert result.extra_source_spec["result_role"] == "composite_output"


def test_concat_clips_rejects_invalid_result_role() -> None:
    """Defense-in-depth: only AssetRole values are accepted. A
    typo in the starter (e.g. result_role="composite") would be
    caught at concat-step execute, not silently stamped."""
    from apps.compositions.primitives.concat_clips import ConcatClipsPrimitive
    from apps.compositions.primitives.mock import PrimitiveError

    ws = _make_workspace("v196concat_bad@test")
    sp = _make_spokesperson(ws)
    clip = Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/_assets/a.mp4", duration_ms=5000,
        mime_type="video/mp4",
    )

    from apps.compositions.models import Composition, CompositionStep
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp,
        name="t", template_kind="dialogue_scene",
        mock_mode=True,
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="concat_clips", inputs=[],
        params={"result_role": "composite_typo"},
    )
    with pytest.raises(PrimitiveError, match="not a valid AssetRole"):
        ConcatClipsPrimitive.execute(
            step, [{"slot": "clip", "asset": clip}], mock_mode=True,
        )


def test_dialogue_scene_starter_passes_composite_output_to_concat() -> None:
    """Slice 2 wiring: the dialogue_scene starter sets
    ``result_role=composite_output`` on its concat step's params
    so the SESSION 195 bug (dialogue final stamped BACKDROP →
    polluting the A7 backdrop_clip_id picker) doesn't recur."""
    ws = _make_workspace("v196ds_role@test")
    sp_a = _make_spokesperson(ws, name="Riggs", avatar_id="avatar_riggs")
    sp_b = _make_spokesperson(ws, name="Sasha", avatar_id="avatar_sasha")
    c = dialogue_scene(
        workspace=ws, primary_spokesperson=sp_a,
        lines=[
            {"spokesperson": sp_a, "text": "L1"},
            {"spokesperson": sp_b, "text": "L2"},
        ],
        mock_mode=True,
    )
    concat = c.steps.get(primitive="concat_clips")
    assert concat.params.get("result_role") == "composite_output"


def test_dialogue_scene_e2e_final_asset_is_composite_output() -> None:
    """End-to-end: a dialogue_scene composition runs to completion
    in mock mode + the final Asset row carries ``role=composite_output``.
    Inverse: the A7 role-filtered backdrop_clip_id picker
    (``role=backdrop``) would not surface this asset."""
    ws = _make_workspace("v196ds_e2e@test")
    sp_a = _make_spokesperson(ws, name="Riggs", avatar_id="avatar_riggs")
    sp_b = _make_spokesperson(ws, name="Sasha", avatar_id="avatar_sasha")
    c = dialogue_scene(
        workspace=ws, primary_spokesperson=sp_a,
        lines=[
            {"spokesperson": sp_a, "text": "L1"},
            {"spokesperson": sp_b, "text": "L2"},
        ],
        mock_mode=True,
    )
    from apps.compositions.tasks import execute_composition
    result = execute_composition.apply(args=[str(c.pk)]).get()
    assert result["status"] == "completed"
    c.refresh_from_db()
    assert c.final_asset is not None
    assert c.final_asset.role == "composite_output"
    # And confirm the negative case: the dialogue final does NOT
    # surface in a role=backdrop filter (which is what the A7
    # picker uses).
    backdrop_only = Asset.objects.filter(workspace=ws, role="backdrop")
    assert c.final_asset not in backdrop_only
