"""V5 — long-form ad arc tests.

Covers:

* ``SplitScriptPrimitive`` — naive + LLM paths, validation,
  cost estimate.
* ``ConcatClipsPrimitive`` — mock-mode + real-mode (mocked
  media-engine client), input validation, failure paths.
* ``long_form_ad`` starter — pre-splits at create time,
  lays down N+1 (or 1) steps with the right shape, rejects
  cross-workspace spokesperson, runs end-to-end via
  ``execute_composition``.
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
from apps.compositions.primitives.concat_clips import (
    ConcatClipsPrimitive,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.primitives.split_script import SplitScriptPrimitive
from apps.compositions.starters import long_form_ad
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    ConcatClipsResult,
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


def _make_spokesperson(
    ws: Workspace,
    name: str = "Sp",
    avatar_id: str = "runway_avatar_fake_v5",
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name,
        runway_avatar_id=avatar_id,
        portrait_path="https://fake.test/portrait.png",
        business_brief="A brand.",
    )


def _make_composition(ws, sp, *, mock_mode: bool = False) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="t", mock_mode=mock_mode,
    )


# ---- SplitScriptPrimitive -----------------------------------------


def test_split_script_primitive_emits_json_array() -> None:
    ws = _make_workspace("v5sp1@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="split_script",
        params={
            "script": "Sentence one. Sentence two. Sentence three.",
            "max_chars": 30,
        },
    )

    result = SplitScriptPrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=False,
    )
    assert result.asset_type == AssetType.TRANSCRIPT
    chunks = json.loads(result.inline_content)
    assert isinstance(chunks, list)
    assert len(chunks) >= 2
    for c in chunks:
        assert len(c) <= 30
    assert result.extra_source_spec["primitive_kind"] == "split_script"
    assert result.extra_source_spec["chunk_count"] == len(chunks)
    assert result.extra_source_spec["split_path"] == "naive"


def test_split_script_primitive_empty_raises() -> None:
    ws = _make_workspace("v5sp2@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="split_script",
        params={"script": "   "},
    )
    with pytest.raises(PrimitiveError):
        SplitScriptPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )


def test_split_script_primitive_use_llm_disabled_in_mock_mode() -> None:
    """When ``mock_mode=True``, the primitive ignores
    ``use_llm`` and uses the naive splitter — keeps tests
    hermetic without forcing the operator to set the env."""
    ws = _make_workspace("v5sp3@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="split_script",
        params={"script": "One. Two. Three.", "use_llm": True},
    )
    result = SplitScriptPrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=True,
    )
    assert result.extra_source_spec["split_path"] == "naive"


def test_split_script_primitive_cost_estimate() -> None:
    naive_cost = SplitScriptPrimitive.estimate_cost({"script": "x"})
    llm_cost = SplitScriptPrimitive.estimate_cost(
        {"script": "x", "use_llm": True}
    )
    assert naive_cost == 0
    assert llm_cost > 0


# ---- ConcatClipsPrimitive -----------------------------------------


def _make_clip_asset(
    ws,
    file_path: str = "/data/_assets/clip.mp4",
    duration_ms: int | None = 5000,
) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.CLIP,
        file_path=file_path,
        duration_ms=duration_ms,
        mime_type="video/mp4",
    )


def test_concat_clips_mock_mode_stubs_output() -> None:
    ws = _make_workspace("v5c1@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, mock_mode=True)
    a = _make_clip_asset(ws, "/data/_assets/a.mp4", 3000)
    b = _make_clip_asset(ws, "/data/_assets/b.mp4", 4000)
    step = CompositionStep.objects.create(
        composition=comp, position=2, primitive="concat_clips",
    )

    result = ConcatClipsPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "clip", "asset": a},
            {"slot": "clip", "asset": b},
        ],
        mock_mode=True,
    )
    assert result.asset_type == AssetType.CLIP
    assert result.file_path.startswith("mock://compositions/")
    assert result.duration_ms == 7000  # 3000 + 4000
    assert result.extra_source_spec["mock"] is True
    assert result.extra_source_spec["input_count"] == 2


def test_concat_clips_real_mode_calls_media_engine() -> None:
    ws = _make_workspace("v5c2@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    a = _make_clip_asset(ws, "/data/_assets/a.mp4", 3000)
    b = _make_clip_asset(ws, "/data/_assets/b.mp4", 4000)
    step = CompositionStep.objects.create(
        composition=comp, position=2, primitive="concat_clips",
        params={"reencode": True},
    )

    fake = MagicMock()
    fake.concat_clips.return_value = ConcatClipsResult(
        output_url="/data/_internal/concats/abc.mp4",
        duration_seconds=7.0,
        size_bytes=2048,
        mock_mode=False,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.concat_clips.MediaEngineClient",
        return_value=cm,
    ):
        result = ConcatClipsPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "clip", "asset": a},
                {"slot": "clip", "asset": b},
            ],
            mock_mode=False,
        )

    fake.concat_clips.assert_called_once()
    call_kwargs = fake.concat_clips.call_args.kwargs
    assert call_kwargs["clip_urls"] == ["/data/_assets/a.mp4", "/data/_assets/b.mp4"]
    assert call_kwargs["reencode"] is True

    assert result.file_path == "/data/_internal/concats/abc.mp4"
    assert result.duration_ms == 7000
    assert result.size_bytes == 2048


def test_concat_clips_mock_mode_crossfade_shortens_duration() -> None:
    """SESSION 200 — crossfade_ms > 0 shortens the mock duration
    by (n-1) * crossfade_ms because each xfade overlaps adjacent
    clips. Three 4s clips with 500ms crossfade = 12000 - 1000 =
    11000ms."""
    ws = _make_workspace("v200xfade1@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, mock_mode=True)
    a = _make_clip_asset(ws, "/data/_assets/a.mp4", 4000)
    b = _make_clip_asset(ws, "/data/_assets/b.mp4", 4000)
    c = _make_clip_asset(ws, "/data/_assets/c.mp4", 4000)
    step = CompositionStep.objects.create(
        composition=comp, position=2, primitive="concat_clips",
        params={"crossfade_ms": 500},
    )

    result = ConcatClipsPrimitive.execute(
        step=step,
        resolved_inputs=[
            {"slot": "clip", "asset": a},
            {"slot": "clip", "asset": b},
            {"slot": "clip", "asset": c},
        ],
        mock_mode=True,
    )
    assert result.duration_ms == 11000
    assert result.extra_source_spec["crossfade_ms"] == 500


def test_concat_clips_real_mode_forwards_crossfade_ms() -> None:
    """SESSION 200 — the primitive passes crossfade_ms through to
    the media-engine client call so the ffmpeg xfade filter chain
    fires server-side."""
    ws = _make_workspace("v200xfade2@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    a = _make_clip_asset(ws, "/data/_assets/a.mp4", 5000)
    b = _make_clip_asset(ws, "/data/_assets/b.mp4", 5000)
    step = CompositionStep.objects.create(
        composition=comp, position=2, primitive="concat_clips",
        params={"crossfade_ms": 750},
    )

    fake = MagicMock()
    fake.concat_clips.return_value = ConcatClipsResult(
        output_url="/data/_internal/concats/xfade.mp4",
        duration_seconds=9.25,
        size_bytes=4096,
        mock_mode=False,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.concat_clips.MediaEngineClient",
        return_value=cm,
    ):
        result = ConcatClipsPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "clip", "asset": a},
                {"slot": "clip", "asset": b},
            ],
            mock_mode=False,
        )

    call_kwargs = fake.concat_clips.call_args.kwargs
    assert call_kwargs["crossfade_ms"] == 750
    assert result.extra_source_spec["crossfade_ms"] == 750


def test_concat_clips_rejects_negative_crossfade_ms() -> None:
    """SESSION 200 — primitive validates crossfade_ms >= 0 before
    calling the media-engine (the endpoint also caps at 5000ms)."""
    ws = _make_workspace("v200xfade3@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, mock_mode=True)
    a = _make_clip_asset(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="concat_clips",
        params={"crossfade_ms": -100},
    )
    with pytest.raises(PrimitiveError) as exc:
        ConcatClipsPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "clip", "asset": a}],
            mock_mode=True,
        )
    assert ">= 0" in str(exc.value)


def test_concat_clips_rejects_non_integer_crossfade_ms() -> None:
    """SESSION 200 — non-numeric crossfade_ms is a config error,
    not a silent default."""
    ws = _make_workspace("v200xfade4@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, mock_mode=True)
    a = _make_clip_asset(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="concat_clips",
        params={"crossfade_ms": "soft"},
    )
    with pytest.raises(PrimitiveError) as exc:
        ConcatClipsPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "clip", "asset": a}],
            mock_mode=True,
        )
    assert "integer" in str(exc.value).lower()


def test_concat_clips_rejects_non_clip_asset() -> None:
    ws = _make_workspace("v5c3@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    audio = Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/audio.mp3",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="concat_clips",
    )
    with pytest.raises(PrimitiveError) as exc:
        ConcatClipsPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "clip", "asset": audio}],
            mock_mode=False,
        )
    assert "CLIP" in str(exc.value)


def test_concat_clips_no_inputs_raises() -> None:
    ws = _make_workspace("v5c4@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="concat_clips",
    )
    with pytest.raises(PrimitiveError) as exc:
        ConcatClipsPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )
    assert "at least one" in str(exc.value).lower()


def test_concat_clips_media_engine_failure_propagates() -> None:
    ws = _make_workspace("v5c5@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    a = _make_clip_asset(ws)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="concat_clips",
    )

    fake = MagicMock()
    fake.concat_clips.side_effect = MediaEngineError(
        "concat exploded", status_code=500,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.concat_clips.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc:
            ConcatClipsPrimitive.execute(
                step=step,
                resolved_inputs=[{"slot": "clip", "asset": a}],
                mock_mode=False,
            )
    assert "media-engine" in str(exc.value).lower()


def test_concat_clips_rejects_clip_with_empty_file_path() -> None:
    ws = _make_workspace("v5c6@test.local")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    bad = Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP, file_path="",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="concat_clips",
    )
    with pytest.raises(PrimitiveError) as exc:
        ConcatClipsPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "clip", "asset": bad}],
            mock_mode=False,
        )
    assert "empty file_path" in str(exc.value)


# ---- long_form_ad starter -----------------------------------------


def test_long_form_ad_short_script_creates_single_step() -> None:
    """Script that fits in one chunk → no concat step. The
    starter optimizes the degenerate case."""
    ws = _make_workspace("v5lf1@test.local")
    sp = _make_spokesperson(ws)
    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script="A short script that fits in one chunk.",
        mock_mode=True,
    )
    assert comp.template_kind == "long_form_ad"
    steps = list(comp.steps.all())
    assert len(steps) == 1
    assert steps[0].primitive == "generate_avatar_speech"


def test_long_form_ad_long_script_creates_n_plus_1_steps() -> None:
    """Multi-chunk script → N speech steps + 1 concat step."""
    ws = _make_workspace("v5lf2@test.local")
    sp = _make_spokesperson(ws)
    long_script = " ".join(f"Sentence number {i}." for i in range(1, 21))

    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script=long_script,
        max_chars=80,
        mock_mode=True,
    )

    steps = list(comp.steps.all())
    assert len(steps) >= 4
    # All but the last are speech steps
    speech_steps = steps[:-1]
    for s in speech_steps:
        assert s.primitive == "generate_avatar_speech"
        assert s.params["script"] != ""
        assert len(s.params["script"]) <= 80
    # Final step is concat
    concat = steps[-1]
    assert concat.primitive == "concat_clips"
    assert concat.position == len(speech_steps)
    # Concat inputs reference every prior position
    input_positions = [
        entry["from_step_position"] for entry in concat.inputs
    ]
    assert input_positions == list(range(len(speech_steps)))


def test_long_form_ad_use_knowledge_propagates_to_steps() -> None:
    ws = _make_workspace("v5lf3@test.local")
    sp = _make_spokesperson(ws)
    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script="Sentence one. Sentence two. " * 10,
        max_chars=60,
        use_knowledge=True,
        mock_mode=True,
    )
    speech_steps = [s for s in comp.steps.all() if s.primitive == "generate_avatar_speech"]
    assert speech_steps
    for s in speech_steps:
        assert s.params["use_knowledge"] is True


def test_long_form_ad_rejects_empty_script() -> None:
    ws = _make_workspace("v5lf4@test.local")
    sp = _make_spokesperson(ws)
    with pytest.raises(ValueError):
        long_form_ad(
            workspace=ws, spokesperson=sp, script="  ",
            mock_mode=True,
        )


def test_long_form_ad_rejects_cross_workspace_spokesperson() -> None:
    ws_a = _make_workspace("v5lfxA@test.local", "A")
    ws_b = _make_workspace("v5lfxB@test.local", "B")
    foreign_sp = _make_spokesperson(ws_b)
    with pytest.raises(ValueError):
        long_form_ad(
            workspace=ws_a, spokesperson=foreign_sp,
            script="hi", mock_mode=True,
        )


def test_long_form_ad_executes_end_to_end_in_mock_mode() -> None:
    """End-to-end: starter creates multi-step composition,
    executor runs split → N speech → concat → COMPLETED."""
    ws = _make_workspace("v5lfe2e@test.local")
    sp = _make_spokesperson(ws, name="Sasha")
    long_script = (
        "Welcome to our coffee shop. We brew the best espresso in town. "
        "Our beans are sourced ethically. The roasters are local artisans. "
        "Come visit us this Saturday. We have a special promotion running."
    )

    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script=long_script,
        max_chars=60,
        mock_mode=True,
    )
    n_steps_before = comp.steps.count()
    assert n_steps_before >= 4  # at least 3 speech + 1 concat

    result = execute_composition.apply(args=[str(comp.pk)]).get()
    assert result["status"] == "completed"

    comp.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    assert comp.final_asset is not None
    assert comp.final_asset.asset_type == AssetType.CLIP
    # Final asset is the concat output, not any individual speech clip
    spec = comp.final_asset.source_spec
    assert spec["primitive_kind"] == "concat_clips"
    assert spec["input_count"] == n_steps_before - 1
    assert comp.cost_actual_micros > 0


def test_long_form_ad_uses_llm_split_when_requested() -> None:
    """``use_llm_split=True`` (non-mock) calls
    ``split_script_with_llm`` instead of the naive path."""
    ws = _make_workspace("v5lfllm@test.local")
    sp = _make_spokesperson(ws)
    fake_chunks = ["First chunk text.", "Second chunk text."]
    with patch(
        "apps.compositions.starters.split_script_with_llm",
        return_value=fake_chunks,
    ) as fake_split, patch(
        "apps.compositions.starters.chunk_script",
    ) as fake_naive:
        comp = long_form_ad(
            workspace=ws, spokesperson=sp,
            script="x" * 1000,
            use_llm_split=True,
            mock_mode=False,
        )
    fake_split.assert_called_once()
    fake_naive.assert_not_called()
    speech_steps = [s for s in comp.steps.all() if s.primitive == "generate_avatar_speech"]
    assert [s.params["script"] for s in speech_steps] == fake_chunks


def test_long_form_ad_uses_naive_split_in_mock_mode_even_with_use_llm() -> None:
    """``mock_mode=True`` forces the naive splitter regardless
    of ``use_llm_split``. Hermetic test pattern."""
    ws = _make_workspace("v5lfmocknaive@test.local")
    sp = _make_spokesperson(ws)
    with patch(
        "apps.compositions.starters.split_script_with_llm"
    ) as fake_llm, patch(
        "apps.compositions.starters.chunk_script",
        wraps=__import__(
            "apps.compositions.script_splitter", fromlist=["chunk_script"]
        ).chunk_script,
    ) as fake_naive:
        long_form_ad(
            workspace=ws, spokesperson=sp,
            script="Long. " * 50,
            max_chars=50,
            use_llm_split=True,
            mock_mode=True,
        )
    fake_llm.assert_not_called()
    fake_naive.assert_called_once()
