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
from apps.spokespeople.models import Teammate
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


def _make_teammate(
    ws: Workspace,
    name: str = "Sp",
    avatar_id: str = "runway_avatar_fake_v5",
) -> Teammate:
    return Teammate.objects.create(
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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


# ---- SESSION 257 AI-D5 cleanup — concat duration provenance -----
#
# Concat asset now carries the same duration_source /
# duration_estimated shape that talking-head speech steps have
# (SESSION 253 Stage 2 ffprobe plumbing). Prior to this cleanup the
# concat asset had duration_ms populated but source unstamped;
# downstream analytics couldn't tell whether the number was
# ffprobed (measured) or summed (derived).


def test_concat_real_mode_measured_stamps_media_probe() -> None:
    """When media-engine returns a real ffprobe duration (real
    mode, mock_mode=False on the response), the concat asset's
    duration_source must be 'media_probe' and duration_estimated
    must be False."""
    ws = _make_workspace("aid5cprobe@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    a = _make_clip_asset(ws, "/data/_assets/a.mp4", 3000)
    b = _make_clip_asset(ws, "/data/_assets/b.mp4", 4000)
    step = CompositionStep.objects.create(
        composition=comp, position=2, primitive="concat_clips",
    )
    fake = MagicMock()
    fake.concat_clips.return_value = ConcatClipsResult(
        output_url="/data/_internal/concats/abc.mp4",
        duration_seconds=7.02,
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
    assert result.extra_source_spec["duration_source"] == "media_probe"
    assert result.extra_source_spec["duration_estimated"] is False


def test_concat_real_mode_missing_duration_falls_back_to_derived() -> None:
    """When media-engine returned no duration_seconds (ffprobe
    failed, network issue, etc), the primitive falls back to
    summing input durations. That fallback is DERIVED, not
    measured — stamp truthfully."""
    ws = _make_workspace("aid5cderiv@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    a = _make_clip_asset(ws, "/data/_assets/a.mp4", 3000)
    b = _make_clip_asset(ws, "/data/_assets/b.mp4", 4000)
    step = CompositionStep.objects.create(
        composition=comp, position=2, primitive="concat_clips",
    )
    fake = MagicMock()
    fake.concat_clips.return_value = ConcatClipsResult(
        output_url="/data/_internal/concats/no_dur.mp4",
        duration_seconds=None,  # media-engine couldn't probe
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
    assert result.duration_ms == 7000  # summed from inputs
    assert result.extra_source_spec["duration_source"] == "derived_from_inputs"
    assert result.extra_source_spec["duration_estimated"] is True


def test_concat_media_engine_mock_stamps_derived_not_measured() -> None:
    """A media-engine mock response returns a fabricated
    duration_seconds (based on inputs). Not a real ffprobe —
    stamp as derived, NOT media_probe. Prevents downstream
    analytics from treating mock-mode figures as measurements."""
    ws = _make_workspace("aid5cmemock@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    a = _make_clip_asset(ws, "/data/_assets/a.mp4", 3000)
    b = _make_clip_asset(ws, "/data/_assets/b.mp4", 4000)
    step = CompositionStep.objects.create(
        composition=comp, position=2, primitive="concat_clips",
    )
    fake = MagicMock()
    fake.concat_clips.return_value = ConcatClipsResult(
        output_url="/data/_internal/concats/me_mock.mp4",
        duration_seconds=7.0,  # media-engine mock populates this
        size_bytes=2048,
        mock_mode=True,  # but flags itself as mock
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
    assert result.extra_source_spec["duration_source"] == "derived_from_inputs"
    assert result.extra_source_spec["duration_estimated"] is True


def test_concat_shell_mock_stamps_estimated_not_measured() -> None:
    """Shell mock branch never touches media-engine at all.
    Duration is fabricated from summed inputs. Mark it explicitly
    non-measured so mock rows don't contaminate real analytics."""
    ws = _make_workspace("aid5cshellmock@test.local")
    sp = _make_teammate(ws)
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
    assert result.extra_source_spec["mock"] is True
    assert result.extra_source_spec["duration_source"] == "estimated"
    assert result.extra_source_spec["duration_estimated"] is True


def test_concat_clips_rejects_non_clip_asset() -> None:
    ws = _make_workspace("v5c3@test.local")
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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


def test_long_form_ad_use_knowledge_synthesizes_once_not_per_chunk() -> None:
    """SESSION 251 knowledge-ordering fix. Pre-SESSION 251 this test
    asserted the opposite direction — that ``use_knowledge=True``
    propagated onto every per-chunk speech step. That produced "9
    mini-ads back to back" because K6 has no cross-chunk awareness
    and re-synthesized a full standalone script per chunk. The fix
    lifts K6 to fire ONCE up front over the whole brief, then forces
    ``use_knowledge=False`` on every downstream speech step so the
    chunks render the already-synthesized text verbatim."""
    ws = _make_workspace("v5lf3@test.local")
    sp = _make_teammate(ws)
    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script="Sentence one. Sentence two. " * 10,
        max_chars=60,
        use_knowledge=True,
        mock_mode=True,
        # SESSION 251 — long-form knowledge mode is duration-driven;
        # mock_mode short-circuits the tolerance check so the value
        # is informational here (K10 canned mock brief is ~55s).
        target_duration_seconds=60,
    )
    speech_steps = [s for s in comp.steps.all() if s.primitive == "generate_avatar_speech"]
    assert speech_steps
    for s in speech_steps:
        # Per-chunk steps must NOT re-invoke K6 — the composition-
        # level upfront synthesis is the single source of truth.
        assert s.params["use_knowledge"] is False
    # And the upfront synthesis metadata is persisted on the
    # composition (not per-step) so the operator can trace it.
    assert comp.synthesized_brief


def test_long_form_ad_rejects_empty_script() -> None:
    ws = _make_workspace("v5lf4@test.local")
    sp = _make_teammate(ws)
    with pytest.raises(ValueError):
        long_form_ad(
            workspace=ws, spokesperson=sp, script="  ",
            mock_mode=True,
        )


def test_long_form_ad_rejects_cross_workspace_spokesperson() -> None:
    ws_a = _make_workspace("v5lfxA@test.local", "A")
    ws_b = _make_workspace("v5lfxB@test.local", "B")
    foreign_sp = _make_teammate(ws_b)
    with pytest.raises(ValueError):
        long_form_ad(
            workspace=ws_a, spokesperson=foreign_sp,
            script="hi", mock_mode=True,
        )


def test_long_form_ad_executes_end_to_end_in_mock_mode() -> None:
    """End-to-end: starter creates multi-step composition,
    executor runs split → N speech → concat → COMPLETED."""
    ws = _make_workspace("v5lfe2e@test.local")
    sp = _make_teammate(ws, name="Sasha")
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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


# ---- SESSION 253 long-form recap calibration -----------------------
#
# Character OS previously split long-form scripts at ~280 chars per
# chunk because Runway's per-call ceiling was assumed to be around
# 300. SESSION 253 dogfooded seven controlled Runway
# ``/v1/avatar_videos`` calls from ~25s to ~180s and found each one
# billed at exactly 2 credits regardless of duration — making the
# per-call fixed cost the dominant term. Long-form's operating cap
# was raised to LONG_FORM_CHUNK_MAX_CHARS = 1900 (≈ 172s at the
# platform's 11 chars/sec estimator), leaving a 100-char safety
# margin below media-engine's 2000-char Pydantic ceiling. The
# short-form DEFAULT_CHUNK_MAX_CHARS (280) is preserved for other
# recipes (SplitScriptPrimitive, recut_teaser).


def _make_script_of_length(target_chars: int) -> str:
    """Build a script close to ``target_chars`` from repeated
    fixed-length sentences, snapping down to the nearest complete
    sentence. The resulting length lands within one sentence's
    worth of the target — good enough for structural chunker
    tests where the meaningful bound is the LONG_FORM cap, not
    the exact input size."""
    sentence = "This is a well-formed sentence built for reliable packing. "
    n = max(1, target_chars // len(sentence))
    return (sentence * n).rstrip()


def test_long_form_ad_uses_1900_char_default_cap() -> None:
    """Default per-chunk cap on long_form_ad is now
    ``LONG_FORM_CHUNK_MAX_CHARS = 1900`` (was 280). Pin the
    value so future accidental changes light up as an explicit
    test failure."""
    from apps.compositions.script_splitter import LONG_FORM_CHUNK_MAX_CHARS
    assert LONG_FORM_CHUNK_MAX_CHARS == 1900


def test_default_chunk_max_chars_unchanged_at_280() -> None:
    """``DEFAULT_CHUNK_MAX_CHARS`` remains 280 for SplitScriptPrimitive
    and other recipes that depend on the historical short-chunk
    shape. SESSION 253 only raised the long-form recipe's default,
    not the platform-wide constant."""
    from apps.compositions.script_splitter import DEFAULT_CHUNK_MAX_CHARS
    assert DEFAULT_CHUNK_MAX_CHARS == 280


def test_split_script_primitive_default_still_uses_280() -> None:
    """SplitScriptPrimitive's docstring-declared default is 280.
    Callers who don't pass ``max_chars`` must still get the
    short-form cap, unaffected by long_form_ad's calibration."""
    from apps.compositions.primitives.split_script import (
        SplitScriptPrimitive as _SP,
    )
    import inspect
    src = inspect.getsource(_SP.execute)
    # The primitive delegates to the splitter helpers using the
    # module-level default; confirm the default resolves to 280.
    from apps.compositions.script_splitter import DEFAULT_CHUNK_MAX_CHARS
    assert DEFAULT_CHUNK_MAX_CHARS == 280
    assert "DEFAULT_CHUNK_MAX_CHARS" in src


def test_long_form_ad_90s_script_produces_one_avatar_call() -> None:
    """~90s script (~990 chars at 11 cps) fits under the 1900-char
    long-form cap → single ``generate_avatar_speech`` step, no
    concat. Was ~4 chunks under the old 280-char cap."""
    ws = _make_workspace("v5lf_s253_90s@test.local")
    sp = _make_teammate(ws)
    script = _make_script_of_length(990)

    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script=script, mock_mode=True,
    )
    steps = list(comp.steps.all())
    speech = [s for s in steps if s.primitive == "generate_avatar_speech"]
    concat = [s for s in steps if s.primitive == "concat_clips"]
    assert len(speech) == 1
    assert len(concat) == 0
    assert speech[0].params["script"] == script


def test_long_form_ad_120s_script_produces_one_avatar_call() -> None:
    """~120s script (~1320 chars) still fits under the 1900-char
    cap. Was ~5 chunks under 280-char."""
    ws = _make_workspace("v5lf_s253_120s@test.local")
    sp = _make_teammate(ws)
    script = _make_script_of_length(1320)

    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script=script, mock_mode=True,
    )
    speech = [s for s in comp.steps.all() if s.primitive == "generate_avatar_speech"]
    concat = [s for s in comp.steps.all() if s.primitive == "concat_clips"]
    assert len(speech) == 1
    assert len(concat) == 0


def test_long_form_ad_180s_script_at_safe_budget_produces_one_call() -> None:
    """~180s script sized right at the safe 1900-char budget →
    single call. Historically 7-8 chunks at 280."""
    ws = _make_workspace("v5lf_s253_180s@test.local")
    sp = _make_teammate(ws)
    script = _make_script_of_length(1860)  # comfortably < 1900
    assert len(script) <= 1900

    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script=script, mock_mode=True,
    )
    speech = [s for s in comp.steps.all() if s.primitive == "generate_avatar_speech"]
    concat = [s for s in comp.steps.all() if s.primitive == "concat_clips"]
    assert len(speech) == 1
    assert len(concat) == 0
    # And no chunk exceeds the safe budget.
    for s in speech:
        assert len(s.params["script"]) <= 1900


def test_long_form_ad_5min_script_produces_approximately_two_calls() -> None:
    """~5-min script (~3300 chars) exceeds one segment → 2 calls
    plus one concat step. Historical: ~12 chunks at 280 chars."""
    from apps.compositions.script_splitter import LONG_FORM_CHUNK_MAX_CHARS

    ws = _make_workspace("v5lf_s253_5min@test.local")
    sp = _make_teammate(ws)
    script = _make_script_of_length(3300)

    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script=script, mock_mode=True,
    )
    speech = [s for s in comp.steps.all() if s.primitive == "generate_avatar_speech"]
    concat = [s for s in comp.steps.all() if s.primitive == "concat_clips"]
    # Subject to sentence-boundary alignment: 3300 / 1900 = 1.7 →
    # the greedy packer always emits exactly 2 chunks for scripts
    # in the (max_chars, 2 * max_chars] range when every sentence
    # fits inside a chunk. Assert that specific value.
    assert len(speech) == 2, f"expected 2 speech steps, got {len(speech)}"
    assert len(concat) == 1
    for s in speech:
        assert len(s.params["script"]) <= LONG_FORM_CHUNK_MAX_CHARS


def test_long_form_ad_preserves_wording_across_chunks() -> None:
    """Concatenating every chunk's script (whitespace-normalized)
    reproduces the input verbatim. The chunker splits at sentence
    boundaries but must not rewrite, reorder, or drop content."""
    ws = _make_workspace("v5lf_s253_wording@test.local")
    sp = _make_teammate(ws)
    script = _make_script_of_length(3300)  # forces 2 chunks

    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script=script, mock_mode=True,
    )
    speech = [s for s in comp.steps.all() if s.primitive == "generate_avatar_speech"]
    reassembled = " ".join(s.params["script"] for s in speech)
    # Whitespace at chunk boundaries can collapse — normalize both
    # sides before comparison so we're asserting content parity, not
    # exact byte equality.
    normalize = lambda t: " ".join(t.split())
    assert normalize(reassembled) == normalize(script)


def test_long_form_ad_no_chunk_exceeds_safe_budget() -> None:
    """Structural invariant: for any script the chunker sends to
    generate_avatar_speech, every step's script length is bounded
    by the effective ``max_chars``. Guards against a future
    regression that lets an oversize chunk through and gets 422'd
    at the media-engine."""
    from apps.compositions.script_splitter import LONG_FORM_CHUNK_MAX_CHARS

    ws = _make_workspace("v5lf_s253_bounded@test.local")
    sp = _make_teammate(ws)
    # Try a range of sizes: safely-under-cap, right-at-cap, and
    # multi-chunk. The bound holds in every case.
    for target in (990, 1860, 3300, 4900):
        script = _make_script_of_length(target)
        comp = long_form_ad(
            workspace=ws, spokesperson=sp,
            script=script, mock_mode=True,
            name=f"bounded-{target}",
        )
        for s in comp.steps.all():
            if s.primitive != "generate_avatar_speech":
                continue
            assert len(s.params["script"]) <= LONG_FORM_CHUNK_MAX_CHARS, (
                f"chunk exceeded {LONG_FORM_CHUNK_MAX_CHARS} for "
                f"target={target}: {len(s.params['script'])} chars"
            )


def test_long_form_ad_rejects_max_chars_above_hard_ceiling() -> None:
    """Explicit override above 2000 (media-engine's Pydantic cap)
    is rejected at starter time — any chunk that size would 422
    at the media-engine, so refusing to lay down guaranteed-to-fail
    speech steps is the safer default."""
    ws = _make_workspace("v5lf_s253_ceiling@test.local")
    sp = _make_teammate(ws)
    with pytest.raises(ValueError, match="exceeds Runway"):
        long_form_ad(
            workspace=ws, spokesperson=sp,
            script="A short script.", max_chars=2500,
            mock_mode=True,
        )


def test_long_form_ad_accepts_explicit_smaller_max_chars() -> None:
    """Callers who explicitly want the old short-chunk shape (e.g.
    to reproduce a pre-SESSION 253 render) can still pass
    ``max_chars=280`` and get the historical multi-chunk plan."""
    ws = _make_workspace("v5lf_s253_smaller@test.local")
    sp = _make_teammate(ws)
    script = _make_script_of_length(990)  # would be 1 chunk at 1900
    comp = long_form_ad(
        workspace=ws, spokesperson=sp,
        script=script, max_chars=280,
        mock_mode=True,
    )
    speech = [s for s in comp.steps.all() if s.primitive == "generate_avatar_speech"]
    # 990 chars at 280-char cap must produce multiple chunks.
    assert len(speech) >= 3
