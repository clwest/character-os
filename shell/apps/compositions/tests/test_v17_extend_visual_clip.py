"""V17.1 tests — extend_visual_clip primitive.

SESSION 182 / V17.1. Pins the Django-side contract for the
extend_visual_clip primitive added in this slice.

Covers:

* Registry — primitive resolvable by name; cost estimator
  returns positive value scaling with duration.
* Mock-mode — duration_ms = source + new segment; carries
  source dims; extra_source_spec records both component
  durations.
* Input validation — exactly one CLIP; non-CLIP rejected;
  missing prompt rejected; empty file_path rejected.
* Param validation — non-integer duration / seed rejected.
* Real-mode dispatch — media-engine called with right kwargs;
  output persisted as CLIP Asset with summed duration.
* Failure path — media-engine errors surface as
  PrimitiveError.

V17 contract rule 10 (primitive emits one Asset per call) is
the load-bearing claim; the mock + real-mode tests both verify
the one-asset shape. Recipe-level chaining (V17.5) is the
operator-facing concern and not validated here.
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
from apps.compositions.primitives.extend_visual_clip import (
    ExtendVisualClipPrimitive,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    ExtendClipResult,
    MediaEngineError,
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
    file_path: str = "https://cdn.test/source.mp4",
    duration_ms: int | None = 10000,
    width: int | None = 1280,
    height: int | None = 720,
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
        file_path="/data/m.mp3", duration_ms=10000,
        mime_type="audio/mpeg",
    )


def _comp(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t",
        mock_mode=mock_mode,
    )


def _fake_extend_result(
    *,
    output_url: str = "/data/_internal/extends/abc.mp4",
    source_duration_seconds: float = 10.0,
    new_segment_duration_seconds: float = 5.0,
    task_id: str = "runway_task_abc",
) -> ExtendClipResult:
    return ExtendClipResult(
        output_url=output_url,
        duration_seconds=source_duration_seconds + new_segment_duration_seconds,
        source_duration_seconds=source_duration_seconds,
        new_segment_duration_seconds=new_segment_duration_seconds,
        size_bytes=2_048_000,
        task_id=task_id,
        mock_mode=False,
    )


# ---- registry ------------------------------------------------------


def test_primitive_registered_under_canonical_name() -> None:
    assert "extend_visual_clip" in registered_primitives()
    assert get_primitive("extend_visual_clip") is ExtendVisualClipPrimitive


def test_cost_estimator_returns_positive_micros() -> None:
    assert ExtendVisualClipPrimitive.estimate_cost({}) > 0


def test_cost_estimator_scales_with_duration() -> None:
    """Cost is per-second × new-segment duration. A 10s extend
    must cost more than a 5s extend. Source duration is not in
    the formula — V17 rule 13 + the implementation comment
    say the source isn't re-rendered."""
    five = ExtendVisualClipPrimitive.estimate_cost({"duration": 5})
    ten = ExtendVisualClipPrimitive.estimate_cost({"duration": 10})
    assert ten > five


def test_cost_estimator_floor_for_tiny_durations() -> None:
    """Below the minimum, cost still surfaces a non-trivial
    forecast so operators see SOMETHING before clicking
    render. Even an invalid 1s extend reports the floor."""
    assert ExtendVisualClipPrimitive.estimate_cost({"duration": 1}) >= 250_000


def test_cost_estimator_handles_missing_or_bad_duration() -> None:
    """Defensive: param missing or non-numeric → 5s default →
    floor cost."""
    assert ExtendVisualClipPrimitive.estimate_cost({}) > 0
    assert ExtendVisualClipPrimitive.estimate_cost(
        {"duration": "five"},
    ) > 0


# ---- mock-mode -----------------------------------------------------


def test_mock_mode_sums_source_plus_new_duration() -> None:
    """Mock-mode duration_ms = source duration_ms + new-
    segment duration in ms. V17 rule 13 (cost surfaces) +
    downstream recipe steps that read total duration both
    depend on this being right."""
    ws = _make_workspace("v17_mock_dur@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    src = _make_clip(ws, duration_ms=10000)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "continuing outside", "duration": 5},
    )
    result = ExtendVisualClipPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "source", "asset": src}],
        mock_mode=True,
    )
    assert result.asset_type == AssetType.CLIP
    assert result.duration_ms == 15000  # 10s + 5s
    assert result.width == 1280
    assert result.height == 720
    assert result.mime_type == "video/mp4"
    assert result.extra_source_spec["mock"] is True
    assert result.extra_source_spec["source_duration_ms"] == 10000
    assert result.extra_source_spec["new_segment_duration_ms"] == 5000


def test_mock_mode_carries_source_dimensions() -> None:
    """Output is at the source's ratio (the primitive doesn't
    rescale). Downstream concat / composite steps that probe
    output dims must see the source's, not the schema default."""
    ws = _make_workspace("v17_mock_dims@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    # Runway avatar dims — not the 1280x720 default.
    src = _make_clip(ws, width=1088, height=704)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything"},
    )
    result = ExtendVisualClipPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "source", "asset": src}],
        mock_mode=True,
    )
    assert result.width == 1088
    assert result.height == 704


def test_mock_mode_records_prompt_chars_for_audit() -> None:
    """Audit trails reconstruct what the operator asked for;
    extra_source_spec carries the prompt length."""
    ws = _make_workspace("v17_mock_chars@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp, mock_mode=True)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "the founder walks out of the office"},
    )
    result = ExtendVisualClipPrimitive.execute(
        step=step,
        resolved_inputs=[{"slot": "source", "asset": src}],
        mock_mode=True,
    )
    assert result.extra_source_spec["prompt_chars"] == len(
        "the founder walks out of the office"
    )


# ---- input validation ---------------------------------------------


def test_missing_prompt_rejected() -> None:
    ws = _make_workspace("v17_no_prompt@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip", params={},
    )
    with pytest.raises(PrimitiveError) as exc:
        ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    assert "prompt" in str(exc.value)


def test_whitespace_only_prompt_rejected() -> None:
    """A prompt of spaces is operator error, not a valid call.
    The media-engine would reject it anyway; failing in the
    primitive surfaces a clean error closer to the operator."""
    ws = _make_workspace("v17_ws_prompt@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "   "},
    )
    with pytest.raises(PrimitiveError) as exc:
        ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    assert "prompt" in str(exc.value)


def test_zero_inputs_rejected() -> None:
    ws = _make_workspace("v17_zero@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything"},
    )
    with pytest.raises(PrimitiveError) as exc:
        ExtendVisualClipPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )
    assert "exactly one" in str(exc.value)


def test_two_inputs_rejected() -> None:
    """V17 rule 10 — the primitive consumes ONE source clip.
    Multi-clip chains live at the recipe layer (V17.5)."""
    ws = _make_workspace("v17_two@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    a = _make_clip(ws, file_path="https://cdn.test/a.mp4")
    b = _make_clip(ws, file_path="https://cdn.test/b.mp4")
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything"},
    )
    with pytest.raises(PrimitiveError) as exc:
        ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "a", "asset": a},
                {"slot": "b", "asset": b},
            ],
            mock_mode=False,
        )
    assert "exactly one" in str(exc.value)


def test_non_clip_input_rejected() -> None:
    ws = _make_workspace("v17_nontype@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    audio = _make_audio(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything"},
    )
    with pytest.raises(PrimitiveError) as exc:
        ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": audio}],
            mock_mode=False,
        )
    assert "CLIP" in str(exc.value)


def test_empty_file_path_rejected() -> None:
    """An upstream step that produced no file_path can't be
    extended — surface a clean error instead of letting an
    empty string flow to the media-engine."""
    ws = _make_workspace("v17_nofile@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws, file_path="")
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything"},
    )
    with pytest.raises(PrimitiveError) as exc:
        ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    assert "file_path" in str(exc.value)


def test_non_integer_duration_rejected() -> None:
    ws = _make_workspace("v17_baddur@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything", "duration": "five"},
    )
    with pytest.raises(PrimitiveError) as exc:
        ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    assert "duration" in str(exc.value).lower()


def test_non_integer_seed_rejected() -> None:
    ws = _make_workspace("v17_badseed@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything", "seed": "abc"},
    )
    with pytest.raises(PrimitiveError) as exc:
        ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )
    assert "seed" in str(exc.value)


# ---- real-mode dispatch -------------------------------------------


def test_real_mode_calls_media_engine_with_request_shape() -> None:
    ws = _make_workspace("v17_real@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(
        ws, file_path="https://cdn.test/source.mp4",
        duration_ms=10000, width=1280, height=720,
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={
            "prompt": "continuing outside",
            "duration": 5,
            "ratio": "1280:720",
            "seed": 42,
        },
    )

    fake = MagicMock()
    fake.extend_clip.return_value = _fake_extend_result()
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.extend_visual_clip.MediaEngineClient",
        return_value=cm,
    ):
        result = ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )

    fake.extend_clip.assert_called_once()
    kwargs = fake.extend_clip.call_args.kwargs
    assert kwargs["source_clip_url"] == "https://cdn.test/source.mp4"
    assert kwargs["prompt"] == "continuing outside"
    assert kwargs["duration"] == 5
    assert kwargs["ratio"] == "1280:720"
    assert kwargs["seed"] == 42

    assert result.asset_type == AssetType.CLIP
    assert result.file_path == "/data/_internal/extends/abc.mp4"
    assert result.duration_ms == 15000  # source 10s + new 5s
    assert result.width == 1280
    assert result.height == 720
    assert result.mime_type == "video/mp4"
    assert result.extra_source_spec["task_id"] == "runway_task_abc"
    assert result.extra_source_spec["source_asset_id"] == str(src.id)
    assert result.extra_source_spec["source_duration_ms"] == 10000
    assert result.extra_source_spec["new_segment_duration_ms"] == 5000


def test_real_mode_omits_seed_when_not_supplied() -> None:
    """seed param defaults to None → not forwarded → media-
    engine picks a random one + records it in the cache key."""
    ws = _make_workspace("v17_no_seed@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything"},
    )

    fake = MagicMock()
    fake.extend_clip.return_value = _fake_extend_result()
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.extend_visual_clip.MediaEngineClient",
        return_value=cm,
    ):
        ExtendVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "source", "asset": src}],
            mock_mode=False,
        )

    kwargs = fake.extend_clip.call_args.kwargs
    assert kwargs["seed"] is None


def test_media_engine_failure_propagates_as_primitive_error() -> None:
    ws = _make_workspace("v17_fail@test")
    sp = _make_spokesperson(ws)
    comp = _comp(ws, sp)
    src = _make_clip(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="extend_visual_clip",
        params={"prompt": "anything"},
    )

    fake = MagicMock()
    fake.extend_clip.side_effect = MediaEngineError(
        "explode", status_code=502,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.extend_visual_clip.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc:
            ExtendVisualClipPrimitive.execute(
                step=step,
                resolved_inputs=[{"slot": "source", "asset": src}],
                mock_mode=False,
            )
    assert "media-engine" in str(exc.value).lower()
