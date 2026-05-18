"""V16 tests — remove_avatar_background primitive.

Covers:

* Mock-mode returns a stub CLIP that carries the source's
  duration / dimensions through (the matter doesn't change shape).
* Real-mode dispatches to media-engine with the source clip URL +
  model, persists output_url as ``file_path``.
* Input validation: exactly one CLIP input required; non-CLIP
  rejected; empty file_path rejected.
* Model validation: only registered models accepted.
* Failure path: media-engine errors surface as PrimitiveError.
* Registry: primitive resolvable by name; cost estimator returns
  positive value.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStep,
)
from apps.compositions.primitives import (
    get_primitive,
    registered_primitives,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.primitives.remove_avatar_background import (
    RemoveAvatarBackgroundPrimitive,
)
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineError,
    ProcessedClipResult,
)

User = get_user_model()

pytestmark = [pytest.mark.django_db]


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Sp",
        runway_avatar_id="fake-avatar",
        portrait_path="https://fake/p.png",
        business_brief="b",
    )


def _make_clip(
    ws: Workspace,
    file_path: str = "/data/_internal/avatar/clip.mp4",
    duration_ms: int | None = 22000,
    width: int | None = 1088,
    height: int | None = 704,
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path=file_path, duration_ms=duration_ms,
        width=width, height=height,
        mime_type="video/mp4",
    )


def _make_audio(ws: Workspace) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/m.mp3", duration_ms=22000,
        mime_type="audio/mpeg",
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _fake_processed(
    output_url: str = "/data/_internal/matted/abc.webm",
    duration_seconds: float | None = 22.0,
) -> ProcessedClipResult:
    return ProcessedClipResult(
        output_url=output_url,
        duration_seconds=duration_seconds,
        size_bytes=512_000,
        mock_mode=False,
    )


# ---- registry ------------------------------------------------------


def test_primitive_registered_under_canonical_name() -> None:
    assert "remove_avatar_background" in registered_primitives()
    assert get_primitive("remove_avatar_background") is (
        RemoveAvatarBackgroundPrimitive
    )


def test_cost_estimator_returns_positive_micros() -> None:
    assert RemoveAvatarBackgroundPrimitive.estimate_cost({}) > 0


# ---- mock-mode -----------------------------------------------------


def test_mock_mode_carries_source_shape_through() -> None:
    """Matter doesn't change dimensions or duration. Mock-mode
    stub must reflect that so downstream steps that read
    duration / dims (e.g. composite trim) see consistent
    numbers."""
    ws = _make_workspace("v16_mock@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    src = _make_clip(ws, duration_ms=22000, width=1088, height=704)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="remove_avatar_background",
        params={},
    )
    result = RemoveAvatarBackgroundPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "clip", "asset": src}],
        mock_mode=True,
    )
    assert result.asset_type == AssetType.CLIP
    assert result.duration_ms == 22000
    assert result.width == 1088
    assert result.height == 704
    assert result.mime_type == "video/webm"
    assert result.extra_source_spec["mock"] is True
    assert result.extra_source_spec["model"] == "u2net_human_seg"


# ---- input validation ---------------------------------------------


def test_zero_inputs_rejected() -> None:
    ws = _make_workspace("v16_zero@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="remove_avatar_background", params={},
    )
    with pytest.raises(PrimitiveError) as exc:
        RemoveAvatarBackgroundPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )
    assert "exactly one" in str(exc.value)


def test_two_inputs_rejected() -> None:
    """Chained matting is an anti-pattern — guard against the
    starter accidentally wiring multiple clips in."""
    ws = _make_workspace("v16_two@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    a = _make_clip(ws, "/data/a.mp4")
    b = _make_clip(ws, "/data/b.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="remove_avatar_background", params={},
    )
    with pytest.raises(PrimitiveError) as exc:
        RemoveAvatarBackgroundPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "a", "asset": a},
                {"slot": "b", "asset": b},
            ],
            mock_mode=False,
        )
    assert "exactly one" in str(exc.value)


def test_non_clip_input_rejected() -> None:
    ws = _make_workspace("v16_nontype@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    audio = _make_audio(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="remove_avatar_background", params={},
    )
    with pytest.raises(PrimitiveError) as exc:
        RemoveAvatarBackgroundPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "clip", "asset": audio}],
            mock_mode=False,
        )
    assert "CLIP" in str(exc.value)


def test_unknown_model_rejected() -> None:
    ws = _make_workspace("v16_unkmodel@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="remove_avatar_background",
        params={"model": "fancy-future-model"},
    )
    with pytest.raises(PrimitiveError) as exc:
        RemoveAvatarBackgroundPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "clip", "asset": src}],
            mock_mode=False,
        )
    assert "model" in str(exc.value).lower()


def test_empty_file_path_rejected() -> None:
    """An upstream step that produced no file_path can't be
    matted — surface a clean error instead of letting an empty
    string flow to the media-engine."""
    ws = _make_workspace("v16_nofile@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws, file_path="")
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="remove_avatar_background", params={},
    )
    with pytest.raises(PrimitiveError) as exc:
        RemoveAvatarBackgroundPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "clip", "asset": src}],
            mock_mode=False,
        )
    assert "file_path" in str(exc.value)


# ---- real-mode dispatch -------------------------------------------


def test_real_mode_calls_media_engine_with_source_url_and_model() -> None:
    ws = _make_workspace("v16_real@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(
        ws, file_path="https://cdn.test/avatar-x.mp4",
        duration_ms=22000, width=1088, height=704,
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="remove_avatar_background",
        params={"model": "u2net_human_seg"},
    )

    fake = MagicMock()
    fake.remove_avatar_background.return_value = _fake_processed(
        "/data/_internal/matted/x.webm",
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.remove_avatar_background.MediaEngineClient",
        return_value=cm,
    ):
        result = RemoveAvatarBackgroundPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "clip", "asset": src}],
            mock_mode=False,
        )

    fake.remove_avatar_background.assert_called_once()
    kwargs = fake.remove_avatar_background.call_args.kwargs
    assert kwargs["clip_url"] == "https://cdn.test/avatar-x.mp4"
    assert kwargs["model"] == "u2net_human_seg"

    assert result.file_path == "/data/_internal/matted/x.webm"
    assert result.mime_type == "video/webm"
    assert result.duration_ms == 22000
    assert result.width == 1088
    assert result.height == 704
    assert result.extra_source_spec["model"] == "u2net_human_seg"
    assert result.extra_source_spec["source_asset_id"] == str(src.id)


def test_media_engine_failure_propagates_as_primitive_error() -> None:
    ws = _make_workspace("v16_fail@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws, file_path="https://cdn.test/a.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="remove_avatar_background", params={},
    )

    fake = MagicMock()
    fake.remove_avatar_background.side_effect = MediaEngineError(
        "explode", status_code=500,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.remove_avatar_background.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc:
            RemoveAvatarBackgroundPrimitive.execute(
                step=step,
                resolved_inputs=[{"slot": "clip", "asset": src}],
                mock_mode=False,
            )
    assert "media-engine" in str(exc.value).lower()
