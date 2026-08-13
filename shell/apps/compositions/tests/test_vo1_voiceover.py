"""VO.1 tests — synthesize_voiceover_audio primitive +
voice_spec resolver + Asset role + cost model.

Covers the contract rules from docs/design/VOICEOVER_V1.md:

* Rule 1 — VO audio persists as Asset(AUDIO, VOICEOVER_AUDIO)
  with full provenance in source_spec.
* Rule 2 — workspace-scoped voice_spec resolution. Cross-
  workspace spokesperson refs are rejected.
* Rule 3 — TTS-only path; no avatar pipeline fires. Verified
  indirectly by asserting the role is VOICEOVER_AUDIO + the
  provenance carries 'primitive_kind=synthesize_voiceover_audio'.
* Rule 8 — voice_spec discriminator is exactly-one-of
  {spokesperson_id, voice_id, voice_design}.
"""
from __future__ import annotations

import uuid
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import (
    AssetRole,
    AssetType,
    Composition,
    CompositionStep,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.primitives.voiceover import (
    SynthesizeVoiceoverAudioPrimitive,
    _resolve_voice_spec,
)
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import (
    MediaEngineError,
    TtsResult,
    VoiceDesignResult,
)

User = get_user_model()

pytestmark = [pytest.mark.django_db]


# ---- fixtures / helpers --------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_teammate(ws: Workspace, *, voice_id: str = "voice_abc") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name="Sasha",
        runway_avatar_id="fake_avatar",
        portrait_path="https://fake/p.png",
        business_brief="b",
        voice_id=voice_id,
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="vo-test",
        mock_mode=mock_mode,
    )


def _patched_client(**method_returns):
    """Build a context-manager-shaped MediaEngineClient mock
    that returns the supplied values for each method name."""
    fake = MagicMock()
    for name, value in method_returns.items():
        getattr(fake, name).return_value = value
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- AssetRole enum coverage --------------------------------------


def test_assetrole_voiceover_audio_value_is_voiceover_audio() -> None:
    """Rule 1 — the new role enum lands with the exact wire
    value the scope-lock + migration declare."""
    assert AssetRole.VOICEOVER_AUDIO.value == "voiceover_audio"
    assert AssetRole.VOICEOVER_AUDIO.label == "Voiceover Audio"


def test_assetrole_choices_include_voiceover_audio() -> None:
    """The choices iterable surfaces VOICEOVER_AUDIO so admin +
    serializer surfaces auto-pick it up."""
    values = {value for value, _ in AssetRole.choices}
    assert "voiceover_audio" in values


# ---- Registry wiring ----------------------------------------------


def test_synthesize_voiceover_audio_registered() -> None:
    """VO.1 registry entry — primitive count rises 21 → 22."""
    from apps.compositions.primitives import (
        get_primitive,
        registered_primitives,
    )

    names = registered_primitives()
    assert "synthesize_voiceover_audio" in names
    primitive = get_primitive("synthesize_voiceover_audio")
    assert primitive is SynthesizeVoiceoverAudioPrimitive


# ---- Cost model ---------------------------------------------------


def test_estimate_cost_tts_only_path_is_10k_micros() -> None:
    """voice_id / spokesperson_id paths cost TTS only."""
    assert SynthesizeVoiceoverAudioPrimitive.estimate_cost({}) == 10_000
    assert SynthesizeVoiceoverAudioPrimitive.estimate_cost(
        {"voice_spec": {"voice_id": "x"}}
    ) == 10_000
    assert SynthesizeVoiceoverAudioPrimitive.estimate_cost(
        {"voice_spec": {"spokesperson_id": "x"}}
    ) == 10_000


def test_estimate_cost_voice_design_path_adds_design_cost() -> None:
    """voice_design path triggers a design_voice sub-call, so
    cost is TTS + design."""
    assert SynthesizeVoiceoverAudioPrimitive.estimate_cost(
        {"voice_spec": {"voice_design": "warm conversational founder voice"}}
    ) == 110_000


# ---- voice_spec resolver — happy paths -----------------------------


def test_voice_spec_resolves_voice_id_path() -> None:
    ws = _make_workspace("vo1-vsi@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    voice_id, prov, extra = _resolve_voice_spec(
        {"voice_id": "voice_abc"}, comp,
    )
    assert voice_id == "voice_abc"
    assert prov["voice_spec_discriminator"] == "voice_id"
    assert prov["voice_id"] == "voice_abc"
    assert extra == 0


def test_voice_spec_resolves_spokesperson_path_within_workspace() -> None:
    """Rule 2 happy path — workspace-bound spokesperson resolves."""
    ws = _make_workspace("vo1-sp1@test")
    sp = _make_teammate(ws, voice_id="elev_xyz")
    comp = _comp(ws, sp)
    voice_id, prov, extra = _resolve_voice_spec(
        {"spokesperson_id": str(sp.id)}, comp,
    )
    assert voice_id == "elev_xyz"
    assert prov["voice_spec_discriminator"] == "spokesperson_id"
    assert prov["spokesperson_name"] == "Sasha"
    assert extra == 0


def test_voice_spec_voice_design_calls_design_voice_sub_path() -> None:
    """voice_design fires a design_voice sub-call + persists
    the resulting voice_id + adds the design cost to the
    composition's total."""
    ws = _make_workspace("vo1-vd1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    cm, fake = _patched_client(
        design_voice=VoiceDesignResult(
            voice_id="newly_designed_voice",
            preview_url="https://runway.test/preview.mp3",
            mock_mode=False,
        ),
    )
    with patch(
        "apps.compositions.primitives.voiceover.MediaEngineClient",
        return_value=cm,
    ):
        voice_id, prov, extra = _resolve_voice_spec(
            {"voice_design": "warm gentle female voice"},
            comp,
        )

    fake.design_voice.assert_called_once()
    kwargs = fake.design_voice.call_args.kwargs
    assert kwargs["description"] == "warm gentle female voice"
    assert voice_id == "newly_designed_voice"
    assert prov["voice_spec_discriminator"] == "voice_design"
    assert prov["voice_design_description"] == "warm gentle female voice"
    assert extra == 100_000  # design cost


# ---- voice_spec resolver — error paths ----------------------------


def test_voice_spec_rejects_empty_dict() -> None:
    ws = _make_workspace("vo1-vse1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    with pytest.raises(PrimitiveError) as exc:
        _resolve_voice_spec({}, comp)
    assert "voice_spec" in str(exc.value)


def test_voice_spec_rejects_none() -> None:
    ws = _make_workspace("vo1-vse2@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    with pytest.raises(PrimitiveError):
        _resolve_voice_spec(None, comp)


def test_voice_spec_rejects_multiple_discriminators() -> None:
    """Rule 8 — exactly-one-of. Passing both voice_id AND
    spokesperson_id is a misconfiguration that should fail
    loud rather than pick one silently."""
    ws = _make_workspace("vo1-vse3@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    with pytest.raises(PrimitiveError) as exc:
        _resolve_voice_spec(
            {"voice_id": "abc", "spokesperson_id": str(sp.id)},
            comp,
        )
    assert "exactly one" in str(exc.value)


def test_voice_spec_rejects_cross_workspace_spokesperson_id() -> None:
    """Rule 2 — spokesperson in workspace A is invisible to
    compositions in workspace B."""
    ws_a = _make_workspace("vo1-cw1a@test")
    ws_b = _make_workspace("vo1-cw1b@test")
    sp_a = _make_teammate(ws_a)
    sp_b = _make_teammate(ws_b)
    comp_b = _comp(ws_b, sp_b)

    with pytest.raises(PrimitiveError) as exc:
        _resolve_voice_spec(
            {"spokesperson_id": str(sp_a.id)},
            comp_b,
        )
    msg = str(exc.value)
    assert "not found in workspace" in msg
    assert "rule 2" in msg.lower()


def test_voice_spec_rejects_spokesperson_without_voice_id() -> None:
    """Teammate exists but has no voice — operator must
    either bind a voice or pass voice_id directly."""
    ws = _make_workspace("vo1-novc@test")
    sp = _make_teammate(ws, voice_id="")
    comp = _comp(ws, sp)
    with pytest.raises(PrimitiveError) as exc:
        _resolve_voice_spec({"spokesperson_id": str(sp.id)}, comp)
    assert "voice_id" in str(exc.value)


def test_voice_spec_rejects_invalid_uuid() -> None:
    ws = _make_workspace("vo1-uuid@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    with pytest.raises(PrimitiveError):
        _resolve_voice_spec({"spokesperson_id": "not-a-uuid"}, comp)


def test_voice_spec_rejects_short_voice_design_prompt() -> None:
    ws = _make_workspace("vo1-vds@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    with pytest.raises(PrimitiveError) as exc:
        _resolve_voice_spec({"voice_design": "hi"}, comp)
    assert "at least 4 characters" in str(exc.value)


# ---- Primitive execute — mock mode ---------------------------------


def test_execute_mock_mode_returns_audio_asset_voiceover_role() -> None:
    """Rule 1 — the AUDIO asset carries the new
    VOICEOVER_AUDIO role; provenance fields land in
    source_spec."""
    ws = _make_workspace("vo1-exec1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="synthesize_voiceover_audio",
        params={
            "script": "And now back to you, Jessica.",
            "voice_spec": {"voice_id": "voice_jessica_123"},
        },
    )
    result = SynthesizeVoiceoverAudioPrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=True,
    )
    assert result.asset_type == AssetType.AUDIO
    assert result.role == AssetRole.VOICEOVER_AUDIO.value
    assert result.mime_type == "audio/mpeg"
    assert result.duration_ms is not None
    assert result.duration_ms >= 1_000
    assert result.cost_micros == 10_000
    spec = result.extra_source_spec
    assert spec["primitive_kind"] == "synthesize_voiceover_audio"
    assert spec["mock"] is True
    assert spec["script"] == "And now back to you, Jessica."
    assert spec["script_chars"] == len("And now back to you, Jessica.")
    assert spec["voice_id"] == "voice_jessica_123"
    assert spec["provider"] == "mock"


def test_execute_mock_mode_resolves_spokesperson_voice() -> None:
    ws = _make_workspace("vo1-exec2@test")
    sp = _make_teammate(ws, voice_id="elev_marcus_456")
    comp = _comp(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="synthesize_voiceover_audio",
        params={
            "script": "Friends, Romans, countrymen.",
            "voice_spec": {"spokesperson_id": str(sp.id)},
        },
    )
    result = SynthesizeVoiceoverAudioPrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=True,
    )
    assert result.role == AssetRole.VOICEOVER_AUDIO.value
    spec = result.extra_source_spec
    assert spec["voice_id"] == "elev_marcus_456"
    assert spec["voice_spec_discriminator"] == "spokesperson_id"


def test_execute_mock_mode_voice_design_invokes_design_sub_call() -> None:
    """voice_design path fires the design_voice sub-call even
    in mock-mode (the operator wants the side-effect: a new
    voice_id stored on the AUDIO asset for re-use)."""
    ws = _make_workspace("vo1-exec3@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="synthesize_voiceover_audio",
        params={
            "script": "A different speaker reads this CTA line.",
            "voice_spec": {
                "voice_design": "deep authoritative narrator voice",
            },
        },
    )
    cm, fake = _patched_client(
        design_voice=VoiceDesignResult(
            voice_id="designed_voice_abc",
            preview_url=None,
            mock_mode=True,
        ),
    )
    with patch(
        "apps.compositions.primitives.voiceover.MediaEngineClient",
        return_value=cm,
    ):
        result = SynthesizeVoiceoverAudioPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=True,
        )

    assert result.role == AssetRole.VOICEOVER_AUDIO.value
    spec = result.extra_source_spec
    assert spec["voice_id"] == "designed_voice_abc"
    assert spec["voice_spec_discriminator"] == "voice_design"
    # Total cost = TTS + design.
    assert result.cost_micros == 10_000 + 100_000


def test_execute_blank_script_raises() -> None:
    ws = _make_workspace("vo1-blank@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="synthesize_voiceover_audio",
        params={"script": "   ", "voice_spec": {"voice_id": "x"}},
    )
    with pytest.raises(PrimitiveError) as exc:
        SynthesizeVoiceoverAudioPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=True,
        )
    assert "non-empty script" in str(exc.value)


def test_execute_over_long_script_raises() -> None:
    ws = _make_workspace("vo1-long@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="synthesize_voiceover_audio",
        params={
            "script": "x" * 5001,
            "voice_spec": {"voice_id": "abc"},
        },
    )
    with pytest.raises(PrimitiveError) as exc:
        SynthesizeVoiceoverAudioPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=True,
        )
    assert "5000" in str(exc.value)


# ---- Primitive execute — real mode (MediaEngineClient.tts) ---------


def test_execute_real_mode_calls_media_engine_tts() -> None:
    ws = _make_workspace("vo1-real1@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="synthesize_voiceover_audio",
        params={
            "script": "Hello world from VO.1",
            "voice_spec": {"voice_id": "voice_xyz"},
            "model": "eleven_multilingual_v2",
            "provider": "auto",
        },
    )
    cm, fake = _patched_client(
        tts=TtsResult(
            audio_url="/data/_internal/voiceovers/abc123.mp3",
            voice_id="voice_xyz",
            duration_seconds=2.4,
            size_bytes=12_345,
            model="eleven_multilingual_v2",
            provider="elevenlabs",
            cost_micros=10_000,
            mock_mode=False,
        ),
    )
    with patch(
        "apps.compositions.primitives.voiceover.MediaEngineClient",
        return_value=cm,
    ):
        result = SynthesizeVoiceoverAudioPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    fake.tts.assert_called_once()
    kwargs = fake.tts.call_args.kwargs
    assert kwargs["text"] == "Hello world from VO.1"
    assert kwargs["voice_id"] == "voice_xyz"
    assert kwargs["model"] == "eleven_multilingual_v2"
    assert kwargs["provider"] == "auto"

    assert result.asset_type == AssetType.AUDIO
    assert result.role == AssetRole.VOICEOVER_AUDIO.value
    assert result.file_path == "/data/_internal/voiceovers/abc123.mp3"
    assert result.duration_ms == 2400
    assert result.size_bytes == 12_345
    assert result.extra_source_spec["provider"] == "elevenlabs"
    assert result.extra_source_spec["provider_pref"] == "auto"


def test_execute_real_mode_propagates_media_engine_failure() -> None:
    ws = _make_workspace("vo1-real2@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="synthesize_voiceover_audio",
        params={
            "script": "Test",
            "voice_spec": {"voice_id": "voice_abc"},
        },
    )
    fake = MagicMock()
    fake.tts.side_effect = MediaEngineError(
        "tts provider unavailable", status_code=503,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.voiceover.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc:
            SynthesizeVoiceoverAudioPrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )
    assert "media-engine tts failed" in str(exc.value)


def test_execute_real_mode_duration_falls_back_when_provider_returns_zero() -> None:
    """Provider can return duration_seconds=0 (e.g. Runway TTS
    payload lacked the field). The primitive falls back to the
    char-count estimator so VO.2's offset math stays anchored."""
    ws = _make_workspace("vo1-real3@test")
    sp = _make_teammate(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="synthesize_voiceover_audio",
        params={
            "script": "x" * 110,  # ~10 seconds @ 11 cps
            "voice_spec": {"voice_id": "voice_abc"},
        },
    )
    cm, fake = _patched_client(
        tts=TtsResult(
            audio_url="/data/_internal/voiceovers/foo.mp3",
            voice_id="voice_abc",
            duration_seconds=0.0,
            size_bytes=0,
            model="eleven_multilingual_v2",
            provider="runway",
            cost_micros=10_000,
            mock_mode=False,
        ),
    )
    with patch(
        "apps.compositions.primitives.voiceover.MediaEngineClient",
        return_value=cm,
    ):
        result = SynthesizeVoiceoverAudioPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )
    # 110 chars / 11 cps = 10s = 10_000 ms (within heuristic).
    assert result.duration_ms is not None
    assert 9_000 <= result.duration_ms <= 12_000
