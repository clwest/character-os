"""V10 tests — design_voice + dub_audio primitives + 2 starters.

These primitives port the hackathon's production-tested
audio_client.py (29-language dubbing was used live; voice
design seeded brand voices). V10's job is to restore the
capability under the V0+ composition architecture without
losing the existing Runway anchors.
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
from apps.compositions.primitives.voice import (
    SUPPORTED_DUB_LANGS,
    DesignVoicePrimitive,
    DubAudioPrimitive,
)
from apps.compositions.starters import (
    multi_lang_dub,
    voice_design,
)
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import (
    AudioDubResult,
    MediaEngineError,
    VoiceDesignResult,
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


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _patched_client(method_name: str, return_value):
    fake = MagicMock()
    getattr(fake, method_name).return_value = return_value
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- DesignVoicePrimitive -----------------------------------------


def test_design_voice_mock_mode_returns_voice_asset_with_stub_id() -> None:
    ws = _make_workspace("v10vd1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="design_voice",
        params={"description": "warm conversational founder voice"},
    )
    r = DesignVoicePrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=True,
    )
    assert r.asset_type == AssetType.VOICE
    assert r.mime_type == "audio/mpeg"
    assert r.extra_source_spec["mock"] is True
    assert r.extra_source_spec["voice_id"].startswith("mock_voice_")
    assert r.extra_source_spec["description_chars"] > 0


def test_design_voice_rejects_short_description() -> None:
    ws = _make_workspace("v10vd2@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="design_voice",
        params={"description": "hi"},  # too short
    )
    with pytest.raises(PrimitiveError):
        DesignVoicePrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )


def test_design_voice_real_mode_calls_media_engine() -> None:
    ws = _make_workspace("v10vd3@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="design_voice",
        params={
            "description": "energetic young female British accent",
            "name": "Sasha — sales",
        },
    )
    cm, fake = _patched_client(
        "design_voice",
        VoiceDesignResult(
            voice_id="runway_voice_abc123",
            preview_url="https://runway.test/preview.mp3",
            mock_mode=False,
        ),
    )
    with patch(
        "apps.compositions.primitives.voice.MediaEngineClient",
        return_value=cm,
    ):
        r = DesignVoicePrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    fake.design_voice.assert_called_once()
    kwargs = fake.design_voice.call_args.kwargs
    assert kwargs["description"] == "energetic young female British accent"
    assert kwargs["name"] == "Sasha — sales"

    assert r.asset_type == AssetType.VOICE
    assert r.file_path == "https://runway.test/preview.mp3"
    assert r.extra_source_spec["voice_id"] == "runway_voice_abc123"


def test_design_voice_propagates_media_engine_failure() -> None:
    ws = _make_workspace("v10vd4@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="design_voice",
        params={"description": "soft narrator voice"},
    )
    fake = MagicMock()
    fake.design_voice.side_effect = MediaEngineError(
        "voice design rejected", status_code=502,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.voice.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc:
            DesignVoicePrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )
    assert "design_voice" in str(exc.value)


# ---- DubAudioPrimitive --------------------------------------------


def test_dub_audio_mock_mode_returns_audio_asset() -> None:
    ws = _make_workspace("v10da1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    source = _make_audio(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="dub_audio",
        params={"target_language": "es"},
    )
    r = DubAudioPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "source", "asset": source}],
        mock_mode=True,
    )
    assert r.asset_type == AssetType.AUDIO
    assert r.extra_source_spec["mock"] is True
    assert r.extra_source_spec["target_language"] == "es"
    assert r.duration_ms == source.duration_ms


def test_dub_audio_rejects_unsupported_language() -> None:
    ws = _make_workspace("v10da2@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    source = _make_audio(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="dub_audio",
        params={"target_language": "klingon"},
    )
    with pytest.raises(PrimitiveError) as exc:
        DubAudioPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": source}],
            mock_mode=False,
        )
    assert "klingon" in str(exc.value)


def test_dub_audio_requires_target_language_param() -> None:
    ws = _make_workspace("v10da3@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    source = _make_audio(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="dub_audio",
        params={},
    )
    with pytest.raises(PrimitiveError):
        DubAudioPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": source}],
            mock_mode=False,
        )


def test_dub_audio_rejects_non_audio_input() -> None:
    ws = _make_workspace("v10da4@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    clip = Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/clip.mp4",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="dub_audio",
        params={"target_language": "fr"},
    )
    with pytest.raises(PrimitiveError):
        DubAudioPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": clip}],
            mock_mode=False,
        )


def test_dub_audio_real_mode_call_shape() -> None:
    ws = _make_workspace("v10da5@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    source = _make_audio(ws, "/data/voice.mp3", duration_ms=4000)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="dub_audio",
        params={"target_language": "ja"},
    )
    cm, fake = _patched_client(
        "dub_audio",
        AudioDubResult(
            output_url="/data/_internal/dubs/abc-ja.mp3",
            duration_seconds=4.5,
            size_bytes=50000,
            target_language="ja",
            mock_mode=False,
        ),
    )
    with patch(
        "apps.compositions.primitives.voice.MediaEngineClient",
        return_value=cm,
    ):
        r = DubAudioPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": source}],
            mock_mode=False,
        )
    fake.dub_audio.assert_called_once()
    kwargs = fake.dub_audio.call_args.kwargs
    assert kwargs["audio_url"] == "/data/voice.mp3"
    assert kwargs["target_language"] == "ja"
    assert r.file_path == "/data/_internal/dubs/abc-ja.mp3"
    assert r.duration_ms == 4500


def test_dub_audio_supports_all_29_hackathon_languages() -> None:
    """Sanity check that the SUPPORTED_DUB_LANGS frozenset
    matches the 29 codes the hackathon shipped — operators
    who relied on a specific language in production keep
    using the same code here."""
    expected = {
        "en", "hi", "pt", "zh", "es", "fr", "de", "ja", "ar", "ru",
        "ko", "id", "it", "nl", "tr", "pl", "sv", "fil", "ms", "ro",
        "uk", "el", "cs", "da", "fi", "bg", "hr", "sk", "ta",
    }
    assert SUPPORTED_DUB_LANGS == expected
    assert len(SUPPORTED_DUB_LANGS) == 29


# ---- starter: voice_design ---------------------------------------


def test_voice_design_starter_shape() -> None:
    ws = _make_workspace("v10sp_vd1@test")
    sp = _make_teammate(ws)
    c = voice_design(
        workspace=ws, spokesperson=sp,
        description="confident founder voice with warmth",
        voice_name="Riggs",
        mock_mode=True,
    )
    assert c.template_kind == "voice_design"
    step = c.steps.first()
    assert step.primitive == "design_voice"
    assert step.params["description"] == "confident founder voice with warmth"
    assert step.params["name"] == "Riggs"


def test_voice_design_rejects_short_description() -> None:
    ws = _make_workspace("v10sp_vd2@test")
    sp = _make_teammate(ws)
    with pytest.raises(ValueError):
        voice_design(
            workspace=ws, spokesperson=sp,
            description="hi",
            mock_mode=True,
        )


def test_voice_design_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v10sp_vd_e2e@test")
    sp = _make_teammate(ws)
    c = voice_design(
        workspace=ws, spokesperson=sp,
        description="energetic spokesperson voice for cafe ads",
        mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    assert c.final_asset.asset_type == AssetType.VOICE


# ---- starter: multi_lang_dub --------------------------------------


def test_multi_lang_dub_starter_shape() -> None:
    ws = _make_workspace("v10sp_dub1@test")
    sp = _make_teammate(ws)
    audio = _make_audio(ws)
    c = multi_lang_dub(
        workspace=ws, spokesperson=sp,
        source_audio=audio, target_language="es",
        mock_mode=True,
    )
    assert c.template_kind == "multi_lang_dub"
    step = c.steps.first()
    assert step.primitive == "dub_audio"
    assert step.params["target_language"] == "es"
    assert step.inputs[0]["asset_id"] == str(audio.id)


def test_multi_lang_dub_normalizes_language_to_lowercase() -> None:
    ws = _make_workspace("v10sp_dub_lc@test")
    sp = _make_teammate(ws)
    audio = _make_audio(ws)
    c = multi_lang_dub(
        workspace=ws, spokesperson=sp,
        source_audio=audio, target_language="ES",  # uppercase
        mock_mode=True,
    )
    step = c.steps.first()
    assert step.params["target_language"] == "es"


def test_multi_lang_dub_rejects_clip_input() -> None:
    """v1 only supports AUDIO inputs; CLIP-dubbing waits for
    V12's transcribe primitive."""
    ws = _make_workspace("v10sp_dub_clip@test")
    sp = _make_teammate(ws)
    clip = Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/clip.mp4",
    )
    with pytest.raises(ValueError):
        multi_lang_dub(
            workspace=ws, spokesperson=sp,
            source_audio=clip, target_language="es",
            mock_mode=True,
        )


def test_multi_lang_dub_rejects_cross_workspace_audio() -> None:
    ws_a = _make_workspace("v10sp_dub_xA@test", "A")
    ws_b = _make_workspace("v10sp_dub_xB@test", "B")
    sp_a = _make_teammate(ws_a)
    foreign = _make_audio(ws_b)
    with pytest.raises(ValueError):
        multi_lang_dub(
            workspace=ws_a, spokesperson=sp_a,
            source_audio=foreign, target_language="es",
            mock_mode=True,
        )


def test_multi_lang_dub_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v10sp_dub_e2e@test")
    sp = _make_teammate(ws)
    audio = _make_audio(ws, "/data/voice.mp3", duration_ms=4000)
    c = multi_lang_dub(
        workspace=ws, spokesperson=sp,
        source_audio=audio, target_language="fr",
        mock_mode=True,
    )
    execute_composition.apply(args=[str(c.pk)]).get()
    c.refresh_from_db()
    assert c.status == CompositionStatus.COMPLETED
    assert c.final_asset is not None
    assert c.final_asset.asset_type == AssetType.AUDIO
    assert c.final_asset.source_spec["target_language"] == "fr"


# ---- cost estimates ----------------------------------------------


def test_voice_primitives_have_realistic_cost_estimates() -> None:
    """Voice design + dubbing are real provider-billed
    operations; their estimates should sit well above the
    mock primitives' 100-micro floors."""
    design_cost = DesignVoicePrimitive.estimate_cost({})
    dub_cost = DubAudioPrimitive.estimate_cost({})
    assert design_cost >= 50_000  # ~$0.05+ floor
    assert dub_cost >= 25_000
