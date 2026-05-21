"""VO.2 tests — overlay_audio_at_offset primitive.

Covers the contract rules from docs/design/VOICEOVER_V1.md:

* Rule 4 — preserves base CLIP's video stream byte-for-byte.
  Asserted indirectly here (the route passes ``-c:v copy``); the
  media-engine companion test ``test_vo2_overlay_audio_endpoint.py``
  carries the real ffprobe byte-identity proof.
* Rule 5 — duck_db default -18; range [-60, 0] enforced
  shell-side.
* Rule 6 — offset + vo_duration > base_duration raises
  PrimitiveError with actionable message. Enforced shell-side
  using persisted Asset.duration_ms (no I/O); media-engine
  re-checks via ffprobe.
* Rule 8 — output Asset role propagates the base CLIP's role
  (TALKING_HEAD stays TALKING_HEAD).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.asset_roles import PRIMITIVE_TO_ROLE
from apps.compositions.models import (
    Asset,
    AssetRole,
    AssetType,
    Composition,
    CompositionStep,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.primitives.overlay_audio import (
    OverlayAudioAtOffsetPrimitive,
    _coerce_duck_db,
    _coerce_offset,
    _expect_base_and_voiceover,
)
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineError,
    ProcessedClipResult,
)

User = get_user_model()
pytestmark = [pytest.mark.django_db]


# ---- fixtures / helpers --------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Sasha",
        runway_avatar_id="fake_avatar",
        portrait_path="https://fake/p.png",
        business_brief="b",
        voice_id="voice_abc",
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="vo2-test",
        mock_mode=mock_mode,
    )


def _make_base_clip(
    comp: Composition,
    *,
    duration_ms: int = 10_000,
    role: str = AssetRole.TALKING_HEAD.value,
    file_path: str = "/data/_internal/avatar_speech/base.mp4",
) -> Asset:
    return Asset.objects.create(
        workspace=comp.workspace,
        composition=comp,
        asset_type=AssetType.CLIP,
        file_path=file_path,
        duration_ms=duration_ms,
        width=1280,
        height=720,
        mime_type="video/mp4",
        size_bytes=1024 * 1024,
        role=role,
        source_spec={"primitive_kind": "generate_avatar_speech"},
    )


def _make_vo_audio(
    comp: Composition,
    *,
    duration_ms: int = 3_000,
    file_path: str = "/data/_internal/voiceovers/vo.mp3",
) -> Asset:
    return Asset.objects.create(
        workspace=comp.workspace,
        composition=comp,
        asset_type=AssetType.AUDIO,
        file_path=file_path,
        duration_ms=duration_ms,
        mime_type="audio/mpeg",
        size_bytes=1024 * 50,
        role=AssetRole.VOICEOVER_AUDIO.value,
        source_spec={"primitive_kind": "synthesize_voiceover_audio"},
    )


def _patched_client(**method_returns):
    fake = MagicMock()
    for name, value in method_returns.items():
        getattr(fake, name).return_value = value
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- Registry + role mapping ---------------------------------------


def test_overlay_audio_at_offset_registered() -> None:
    """VO.2 registry entry — primitive count rises 22 → 23."""
    from apps.compositions.primitives import (
        get_primitive,
        registered_primitives,
    )

    names = registered_primitives()
    assert "overlay_audio_at_offset" in names
    primitive = get_primitive("overlay_audio_at_offset")
    assert primitive is OverlayAudioAtOffsetPrimitive


def test_overlay_audio_at_offset_role_mapping() -> None:
    """Contract rule 20 — every primitive_kind literal has a
    static fallback role. Runtime overrides per VO.0 spec
    (propagate base.role); static value matches mix_audio."""
    assert (
        PRIMITIVE_TO_ROLE["overlay_audio_at_offset"]
        == AssetRole.COMPOSITE_OUTPUT.value
    )


# ---- Cost model ----------------------------------------------------


def test_estimate_cost_is_100_micros() -> None:
    """ffmpeg-only; no provider billing. Matches the scope-lock
    placeholder ($0.0001)."""
    assert OverlayAudioAtOffsetPrimitive.estimate_cost({}) == 100


# ---- _coerce_offset ------------------------------------------------


def test_coerce_offset_accepts_zero() -> None:
    assert _coerce_offset(0) == 0.0
    assert _coerce_offset(0.0) == 0.0


def test_coerce_offset_accepts_positive_float() -> None:
    assert _coerce_offset(5.5) == 5.5


def test_coerce_offset_rejects_none() -> None:
    with pytest.raises(PrimitiveError) as exc:
        _coerce_offset(None)
    assert "requires offset_seconds" in str(exc.value)


def test_coerce_offset_rejects_negative() -> None:
    with pytest.raises(PrimitiveError) as exc:
        _coerce_offset(-1.0)
    assert "≥ 0" in str(exc.value)


def test_coerce_offset_rejects_non_numeric() -> None:
    with pytest.raises(PrimitiveError):
        _coerce_offset("five")


# ---- _coerce_duck_db -----------------------------------------------


def test_coerce_duck_db_defaults_to_minus_18() -> None:
    """Rule 5 default — operator silence ducks to -18 dB."""
    assert _coerce_duck_db(None) == -18.0


def test_coerce_duck_db_accepts_in_range() -> None:
    """Rule 5 range — [-60, 0]."""
    assert _coerce_duck_db(0) == 0.0
    assert _coerce_duck_db(-60) == -60.0
    assert _coerce_duck_db(-20.5) == -20.5


def test_coerce_duck_db_rejects_above_zero() -> None:
    """Boosting base above 0 dB during a duck is incoherent."""
    with pytest.raises(PrimitiveError) as exc:
        _coerce_duck_db(3.0)
    assert "[-60.0, 0.0]" in str(exc.value)


def test_coerce_duck_db_rejects_below_minus_60() -> None:
    with pytest.raises(PrimitiveError):
        _coerce_duck_db(-61.0)


def test_coerce_duck_db_rejects_non_numeric() -> None:
    with pytest.raises(PrimitiveError):
        _coerce_duck_db("loud")


# ---- _expect_base_and_voiceover ------------------------------------


def test_expect_slot_resolution_named_slots() -> None:
    """Named slots resolve correctly regardless of order."""
    ws = _make_workspace("vo2-slot1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_base_clip(comp)
    vo = _make_vo_audio(comp)

    base_out, vo_out = _expect_base_and_voiceover(
        [{"slot": "voiceover", "asset": vo}, {"slot": "base", "asset": base}],
    )
    assert base_out.id == base.id
    assert vo_out.id == vo.id


def test_expect_slot_resolution_unnamed_slots_by_type() -> None:
    """Slot-less entries resolve by asset_type — CLIP → base,
    AUDIO → voiceover."""
    ws = _make_workspace("vo2-slot2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_base_clip(comp)
    vo = _make_vo_audio(comp)

    base_out, vo_out = _expect_base_and_voiceover(
        [{"slot": "", "asset": base}, {"slot": "", "asset": vo}],
    )
    assert base_out.id == base.id
    assert vo_out.id == vo.id


def test_expect_missing_base_raises() -> None:
    ws = _make_workspace("vo2-slot3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    vo = _make_vo_audio(comp)
    with pytest.raises(PrimitiveError) as exc:
        _expect_base_and_voiceover([{"slot": "voiceover", "asset": vo}])
    assert "slot 'base'" in str(exc.value)


def test_expect_missing_voiceover_raises() -> None:
    ws = _make_workspace("vo2-slot4@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_base_clip(comp)
    with pytest.raises(PrimitiveError) as exc:
        _expect_base_and_voiceover([{"slot": "base", "asset": base}])
    assert "slot 'voiceover'" in str(exc.value)


def test_expect_wrong_type_in_base_slot_raises() -> None:
    """An AUDIO in the 'base' slot is operator misconfiguration."""
    ws = _make_workspace("vo2-slot5@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    vo = _make_vo_audio(comp)
    with pytest.raises(PrimitiveError) as exc:
        _expect_base_and_voiceover([{"slot": "base", "asset": vo}])
    assert "expects a CLIP" in str(exc.value)


# ---- Execute — rule 6 (offset + vo > base) -------------------------


def test_rule_6_overflow_raises_with_actionable_message() -> None:
    """Rule 6 — VO that extends past the base raises a clear
    error rather than silently truncating."""
    ws = _make_workspace("vo2-r6a@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_base_clip(comp, duration_ms=5_000)   # 5s base
    vo = _make_vo_audio(comp, duration_ms=3_000)      # 3s VO
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 3.0},               # 3 + 3 > 5
    )
    with pytest.raises(PrimitiveError) as exc:
        OverlayAudioAtOffsetPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": base},
                {"slot": "voiceover", "asset": vo},
            ],
            mock_mode=True,
        )
    msg = str(exc.value)
    assert "past base clip end" in msg
    assert "shorten the VO text" in msg


def test_rule_6_exact_fit_at_end_passes() -> None:
    """offset + vo_duration == base_duration is the canonical
    cta_swap layout — must NOT raise rule 6."""
    ws = _make_workspace("vo2-r6b@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_base_clip(comp, duration_ms=10_000)
    vo = _make_vo_audio(comp, duration_ms=3_000)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 7.0},               # 7 + 3 == 10
    )
    result = OverlayAudioAtOffsetPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": base},
            {"slot": "voiceover", "asset": vo},
        ],
        mock_mode=True,
    )
    assert result.asset_type == AssetType.CLIP


# ---- Execute — mock mode -------------------------------------------


def test_execute_mock_mode_propagates_base_role_talking_head() -> None:
    """VO.0 spec — TALKING_HEAD base → TALKING_HEAD output."""
    ws = _make_workspace("vo2-mock1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_base_clip(comp, role=AssetRole.TALKING_HEAD.value)
    vo = _make_vo_audio(comp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 1.0},
    )
    result = OverlayAudioAtOffsetPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": base},
            {"slot": "voiceover", "asset": vo},
        ],
        mock_mode=True,
    )
    assert result.asset_type == AssetType.CLIP
    assert result.role == AssetRole.TALKING_HEAD.value
    assert result.duration_ms == base.duration_ms
    assert result.width == base.width
    assert result.height == base.height
    assert result.cost_micros == 100

    spec = result.extra_source_spec
    assert spec["primitive_kind"] == "overlay_audio_at_offset"
    assert spec["mock"] is True
    assert spec["base_asset_id"] == str(base.id)
    assert spec["voiceover_asset_id"] == str(vo.id)
    assert spec["offset_seconds"] == 1.0
    assert spec["duck_db"] == -18.0


def test_execute_mock_mode_propagates_base_role_composite() -> None:
    """A composite_output base (e.g. cinematic_visual) keeps its
    role — overlay doesn't change semantic role."""
    ws = _make_workspace("vo2-mock2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_base_clip(comp, role=AssetRole.COMPOSITE_OUTPUT.value)
    vo = _make_vo_audio(comp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 0.0},
    )
    result = OverlayAudioAtOffsetPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": base},
            {"slot": "voiceover", "asset": vo},
        ],
        mock_mode=True,
    )
    assert result.role == AssetRole.COMPOSITE_OUTPUT.value


def test_execute_mock_mode_custom_duck_db() -> None:
    """Operator-supplied duck_db lands in the provenance."""
    ws = _make_workspace("vo2-mock3@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    base = _make_base_clip(comp)
    vo = _make_vo_audio(comp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 2.0, "duck_db": -6.0},
    )
    result = OverlayAudioAtOffsetPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "base", "asset": base},
            {"slot": "voiceover", "asset": vo},
        ],
        mock_mode=True,
    )
    assert result.extra_source_spec["duck_db"] == -6.0


# ---- Execute — real mode (MediaEngineClient.overlay_audio) ---------


def test_execute_real_mode_calls_media_engine_overlay_audio() -> None:
    ws = _make_workspace("vo2-real1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    base = _make_base_clip(comp, duration_ms=10_000)
    vo = _make_vo_audio(comp, duration_ms=3_000)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 6.5, "duck_db": -12.0},
    )
    cm, fake = _patched_client(
        overlay_audio=ProcessedClipResult(
            output_url="/data/_internal/overlays/abc.mp4",
            duration_seconds=10.0,
            size_bytes=2_345_678,
            mock_mode=False,
        ),
    )
    with patch(
        "apps.compositions.primitives.overlay_audio.MediaEngineClient",
        return_value=cm,
    ):
        result = OverlayAudioAtOffsetPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": base},
                {"slot": "voiceover", "asset": vo},
            ],
            mock_mode=False,
        )

    fake.overlay_audio.assert_called_once()
    kwargs = fake.overlay_audio.call_args.kwargs
    assert kwargs["base_url"] == base.file_path
    assert kwargs["vo_url"] == vo.file_path
    assert kwargs["offset_seconds"] == 6.5
    assert kwargs["duck_db"] == -12.0

    assert result.asset_type == AssetType.CLIP
    assert result.role == AssetRole.TALKING_HEAD.value     # propagated
    assert result.file_path == "/data/_internal/overlays/abc.mp4"
    assert result.duration_ms == 10_000
    assert result.size_bytes == 2_345_678
    assert result.cost_micros == 100


def test_execute_real_mode_propagates_media_engine_failure() -> None:
    ws = _make_workspace("vo2-real2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    base = _make_base_clip(comp)
    vo = _make_vo_audio(comp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 1.0},
    )
    fake = MagicMock()
    fake.overlay_audio.side_effect = MediaEngineError(
        "ffmpeg rc=1: invalid filter chain", status_code=500,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.compositions.primitives.overlay_audio.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc:
            OverlayAudioAtOffsetPrimitive.execute(
                step=step,
                resolved_inputs=[
                    {"slot": "base", "asset": base},
                    {"slot": "voiceover", "asset": vo},
                ],
                mock_mode=False,
            )
    assert "media-engine overlay_audio failed" in str(exc.value)


def test_execute_real_mode_rejects_empty_base_file_path() -> None:
    ws = _make_workspace("vo2-empty1@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    base = _make_base_clip(comp, file_path="")
    vo = _make_vo_audio(comp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 1.0},
    )
    with pytest.raises(PrimitiveError) as exc:
        OverlayAudioAtOffsetPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": base},
                {"slot": "voiceover", "asset": vo},
            ],
            mock_mode=False,
        )
    assert "empty file_path" in str(exc.value)


def test_execute_real_mode_rejects_empty_voiceover_file_path() -> None:
    ws = _make_workspace("vo2-empty2@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    base = _make_base_clip(comp)
    vo = _make_vo_audio(comp, file_path="")
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="overlay_audio_at_offset",
        params={"offset_seconds": 1.0},
    )
    with pytest.raises(PrimitiveError) as exc:
        OverlayAudioAtOffsetPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "base", "asset": base},
                {"slot": "voiceover", "asset": vo},
            ],
            mock_mode=False,
        )
    assert "voiceover AUDIO has empty file_path" in str(exc.value)
