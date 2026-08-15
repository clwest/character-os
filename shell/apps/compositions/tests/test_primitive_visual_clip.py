"""V4 tests — ``generate_visual_clip`` primitive end-to-end.

Covers:

* Mock-mode primitive — deterministic stub asset, no
  media-engine call.
* Real-mode primitive (mocked media-engine) — fires
  ``create_visual_clip``, polls until terminal, returns
  PrimitiveResult with output_url.
* Real-mode with explicit ``prompt_image`` in params — passed
  through to media-engine unchanged.
* Real-mode with ``reference_image`` slot input (IMAGE asset)
  — primitive resolves the asset's file_path as prompt_image.
* Failure paths — empty prompt, media-engine 502, terminal-
  FAILED task, missing output_url on ready, non-IMAGE asset
  in reference_image slot.
* Starter composition — ``cinematic_visual`` factory creates
  the right shape with optional ratio + duration + prompt_image
  params; rejects cross-workspace spokesperson.
* End-to-end — starter → execute_composition → COMPLETED
  composition with final_asset of type CLIP.
* Cost estimation — scales with duration.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.compositions.cost import (
    estimate_composition_cost,
    estimate_step_cost,
)
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.compositions.primitives.mock import PrimitiveError
from apps.compositions.primitives.visual_clip import (
    GenerateVisualClipPrimitive,
)
from apps.compositions.starters import cinematic_visual
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import (
    MediaEngineError,
    VideoCreateResult,
    VideoPollResult,
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
        workspace=ws, name=name, business_brief="A brand.",
    )


def _make_composition(
    ws: Workspace, sp: Teammate, *, mock_mode: bool = False,
) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp, name="vc test",
        mock_mode=mock_mode,
    )


def _create_result(task_id: str = "runway_visual_task", mock_mode: bool = False) -> VideoCreateResult:
    return VideoCreateResult(
        task_id=task_id, status="pending", kind="visual_clip",
        mock_mode=mock_mode,
    )


def _ready(
    task_id: str = "runway_visual_task",
    output_url: str = "/data/_assets/visual-fake.mp4",
    duration: float | None = 5.0,
) -> VideoPollResult:
    return VideoPollResult(
        task_id=task_id, status="ready", progress=1.0,
        output_url=output_url, duration_seconds=duration,
        error=None, failure_code=None, mock_mode=False,
    )


def _patched_client(create_result, poll_results):
    polls = list(poll_results)

    def _poll(_task_id):
        return polls.pop(0) if polls else _ready()

    fake = MagicMock()
    fake.create_visual_clip.return_value = create_result
    fake.poll_task.side_effect = _poll
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- mock-mode primitive -------------------------------------------


def test_mock_mode_returns_deterministic_clip() -> None:
    ws = _make_workspace("v4mock@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, mock_mode=True)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "A sunlit coffee bag.", "duration": 8},
    )

    result = GenerateVisualClipPrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=True,
    )

    assert result.asset_type == AssetType.CLIP
    assert result.file_path.startswith("mock://compositions/")
    assert result.duration_ms == 8000  # honors requested duration
    assert result.cost_micros > 0
    assert result.extra_source_spec["mock"] is True
    assert result.extra_source_spec["primitive_kind"] == "generate_visual_clip"


# ---- real-mode primitive (mocked media-engine) ---------------------


def test_real_mode_fires_create_and_polls_until_ready() -> None:
    ws = _make_workspace("v4real@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "A neon-lit alley.", "ratio": "1280:720", "duration": 5},
    )

    cm, fake = _patched_client(_create_result(), [_ready()])
    with patch(
        "apps.compositions.primitives.visual_clip.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.visual_clip.time.sleep",
    ):
        result = GenerateVisualClipPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    fake.create_visual_clip.assert_called_once()
    call_kwargs = fake.create_visual_clip.call_args.kwargs
    assert call_kwargs["prompt"] == "A neon-lit alley."
    assert call_kwargs["ratio"] == "1280:720"
    assert call_kwargs["duration"] == 5
    assert call_kwargs.get("prompt_image") is None

    assert result.asset_type == AssetType.CLIP
    assert result.file_path == "/data/_assets/visual-fake.mp4"
    assert result.extra_source_spec["used_reference_image"] is False


def test_real_mode_uses_explicit_prompt_image_from_params() -> None:
    ws = _make_workspace("v4pi@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={
            "prompt": "Animate this portrait gently.",
            "prompt_image": "/api/runway/image/abc123",
        },
    )

    cm, fake = _patched_client(_create_result(), [_ready()])
    with patch(
        "apps.compositions.primitives.visual_clip.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.visual_clip.time.sleep",
    ):
        result = GenerateVisualClipPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    sent_kwargs = fake.create_visual_clip.call_args.kwargs
    assert sent_kwargs["prompt_image"] == "/api/runway/image/abc123"
    assert result.extra_source_spec["used_reference_image"] is True


def test_real_mode_resolves_reference_image_from_input_slot() -> None:
    """V13's generate_image step output feeds into this step
    via the ``reference_image`` slot."""
    ws = _make_workspace("v4ref@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    upstream_image = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        file_path="/data/_assets/upstream-portrait.png",
        mime_type="image/png",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "Animate this portrait."},
    )

    cm, fake = _patched_client(_create_result(), [_ready()])
    with patch(
        "apps.compositions.primitives.visual_clip.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.visual_clip.time.sleep",
    ):
        result = GenerateVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[
                {"slot": "reference_image", "asset": upstream_image},
            ],
            mock_mode=False,
        )

    sent_kwargs = fake.create_visual_clip.call_args.kwargs
    assert sent_kwargs["prompt_image"] == "/data/_assets/upstream-portrait.png"
    assert result.extra_source_spec["used_reference_image"] is True


def test_explicit_prompt_image_wins_over_reference_image_slot() -> None:
    ws = _make_workspace("v4override@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    slot_image = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.IMAGE,
        file_path="/data/_assets/from-slot.png",
        mime_type="image/png",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={
            "prompt": "Animate.",
            "prompt_image": "/api/runway/image/explicit",
        },
    )

    cm, fake = _patched_client(_create_result(), [_ready()])
    with patch(
        "apps.compositions.primitives.visual_clip.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.visual_clip.time.sleep",
    ):
        GenerateVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "reference_image", "asset": slot_image}],
            mock_mode=False,
        )

    sent_kwargs = fake.create_visual_clip.call_args.kwargs
    assert sent_kwargs["prompt_image"] == "/api/runway/image/explicit"


# ---- failure paths ------------------------------------------------


def test_empty_prompt_raises_primitive_error() -> None:
    ws = _make_workspace("v4empty@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "   "},
    )

    with pytest.raises(PrimitiveError) as exc_info:
        GenerateVisualClipPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )
    assert "prompt" in str(exc_info.value).lower()


def test_non_image_asset_in_reference_slot_raises() -> None:
    ws = _make_workspace("v4nontype@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    not_an_image = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.AUDIO,
        file_path="/data/_assets/not-an-image.mp3",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "Visualize me."},
    )

    with pytest.raises(PrimitiveError) as exc_info:
        GenerateVisualClipPrimitive.execute(
            step=step,
            resolved_inputs=[{"slot": "reference_image", "asset": not_an_image}],
            mock_mode=False,
        )
    assert "image" in str(exc_info.value).lower()


def test_media_engine_failure_raises_primitive_error() -> None:
    ws = _make_workspace("v4me502@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "Hi."},
    )

    fake = MagicMock()
    fake.create_visual_clip.side_effect = MediaEngineError(
        "upstream 502", status_code=502, response_text="bad gateway",
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    with patch(
        "apps.compositions.primitives.visual_clip.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc_info:
            GenerateVisualClipPrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )
    assert "media-engine" in str(exc_info.value).lower()


def test_terminal_failed_raises_primitive_error() -> None:
    ws = _make_workspace("v4tf@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "Hi."},
    )

    bad_poll = VideoPollResult(
        task_id="x", status="failed", progress=None, output_url=None,
        duration_seconds=None, error="bad output", failure_code=None,
        mock_mode=False,
    )
    cm, _fake = _patched_client(_create_result("x"), [bad_poll])

    with patch(
        "apps.compositions.primitives.visual_clip.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.visual_clip.time.sleep",
    ):
        with pytest.raises(PrimitiveError) as exc_info:
            GenerateVisualClipPrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )
    assert "failed" in str(exc_info.value).lower()


# ---- starter composition ------------------------------------------


def test_cinematic_visual_starter_creates_composition_with_one_step() -> None:
    ws = _make_workspace("v4starter@test.local")
    sp = _make_teammate(ws, name="Sasha")

    comp = cinematic_visual(
        workspace=ws, spokesperson=sp,
        prompt="A bicycle bell glinting in morning light.",
        ratio="1280:720", duration=5, mock_mode=True,
    )

    assert comp.template_kind == "cinematic_visual"
    assert comp.mock_mode is True
    assert comp.status == CompositionStatus.DRAFT

    steps = list(comp.steps.all())
    assert len(steps) == 1
    assert steps[0].primitive == "generate_visual_clip"
    assert steps[0].params["prompt"] == "A bicycle bell glinting in morning light."
    assert steps[0].params["ratio"] == "1280:720"
    assert steps[0].params["duration"] == 5
    assert "prompt_image" not in steps[0].params


def test_cinematic_visual_starter_persists_prompt_image() -> None:
    ws = _make_workspace("v4starpi@test.local")
    sp = _make_teammate(ws)
    comp = cinematic_visual(
        workspace=ws, spokesperson=sp,
        prompt="Animate this.",
        prompt_image="/api/runway/image/seed",
        mock_mode=True,
    )
    step = comp.steps.first()
    assert step.params["prompt_image"] == "/api/runway/image/seed"


def test_cinematic_visual_rejects_cross_workspace_spokesperson() -> None:
    ws_a = _make_workspace("v4xA@test.local", "A")
    ws_b = _make_workspace("v4xB@test.local", "B")
    foreign_sp = _make_teammate(ws_b, name="Foreign")
    with pytest.raises(ValueError):
        cinematic_visual(
            workspace=ws_a, spokesperson=foreign_sp,
            prompt="x", mock_mode=True,
        )


def test_cinematic_visual_executes_end_to_end_in_mock_mode() -> None:
    ws = _make_workspace("v4e2e@test.local")
    sp = _make_teammate(ws, name="Maya")

    comp = cinematic_visual(
        workspace=ws, spokesperson=sp,
        prompt="A study scene with soft window light.",
        duration=8,
        mock_mode=True,
    )

    result = execute_composition.apply(args=[str(comp.pk)]).get()
    assert result["status"] == "completed"

    comp.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    assert comp.final_asset is not None
    assert comp.final_asset.asset_type == AssetType.CLIP
    assert comp.final_asset.duration_ms == 8000
    assert comp.cost_actual_micros > 0
    spec = comp.final_asset.source_spec
    assert spec["primitive_kind"] == "generate_visual_clip"


# ---- cost estimation ----------------------------------------------


def test_cost_estimate_scales_with_duration() -> None:
    short = GenerateVisualClipPrimitive.estimate_cost({"duration": 5})
    long_ = GenerateVisualClipPrimitive.estimate_cost({"duration": 10})
    assert short > 0
    assert long_ >= short


def test_cost_estimate_defaults_when_duration_missing() -> None:
    """Missing duration → 5s minimum, same floor as explicit 5."""
    default_cost = GenerateVisualClipPrimitive.estimate_cost({})
    floor_cost = GenerateVisualClipPrimitive.estimate_cost({"duration": 5})
    assert default_cost == floor_cost
    assert default_cost > 0


def test_gen45_text_to_video_cost_matches_controlled_measurements() -> None:
    """SESSION 253 empirical calibration lock.

    Two controlled real-Runway renders on the operator's
    account measured the gen4.5 text_to_video path (no
    prompt_image) at 12 credits/sec × $0.01/credit = $0.12/sec:

    * 5s consumed 60 credits = $0.60
    * 10s consumed 120 credits = $1.20

    Third row (20s) proves linear scaling continues past
    Runway's per-render ceiling — the estimator is
    duration-generic; recipes that chain/extend are the
    concern of a different primitive.
    """
    assert GenerateVisualClipPrimitive.estimate_cost({"duration": 5}) == 600_000
    assert GenerateVisualClipPrimitive.estimate_cost({"duration": 10}) == 1_200_000
    assert GenerateVisualClipPrimitive.estimate_cost({"duration": 20}) == 2_400_000


def test_gen45_below_minimum_duration_reports_5s_floor() -> None:
    """Duration below Runway's 5s minimum still surfaces the
    real 5s billable floor rather than a misleading smaller
    number."""
    below_min = GenerateVisualClipPrimitive.estimate_cost({"duration": 1})
    floor = GenerateVisualClipPrimitive.estimate_cost({"duration": 5})
    assert below_min == floor == 600_000


def test_gen4_turbo_image_to_video_cost_when_prompt_image_present() -> None:
    """SESSION 253 calibration.

    A truthy prompt_image param routes the estimator to
    gen4_turbo (image_to_video) at 5 credits/sec × $0.01 =
    $0.05/sec. Mirrors media-engine
    ``/internal/clips/visual/`` routing. Rate confirmed
    indirectly by the ``cinematic_visual_extended`` real-Runway
    dogfood (25 credits for 5s of gen4_turbo extend).
    """
    assert GenerateVisualClipPrimitive.estimate_cost(
        {"duration": 5, "prompt_image": "/api/runway/image/abc"},
    ) == 250_000
    assert GenerateVisualClipPrimitive.estimate_cost(
        {"duration": 10, "prompt_image": "/api/runway/image/abc"},
    ) == 500_000


def test_empty_prompt_image_routes_to_gen45_not_gen4turbo() -> None:
    """An empty or whitespace-only prompt_image isn't a valid
    image reference; the estimator treats it as text-only and
    quotes the gen4.5 rate."""
    assert GenerateVisualClipPrimitive.estimate_cost(
        {"duration": 5, "prompt_image": ""},
    ) == 600_000
    assert GenerateVisualClipPrimitive.estimate_cost(
        {"duration": 5, "prompt_image": "   "},
    ) == 600_000


def test_slot_wired_reference_image_routes_to_gen4_turbo() -> None:
    """SESSION 253 storyboard_ad calibration lock.

    Storyboard recipes wire the ``reference_image`` via
    ``CompositionStep.inputs`` (raw JSON with
    ``from_step_position``), NOT via a params-side
    ``prompt_image``. The estimator must accept ``inputs`` and
    treat any ``reference_image`` slot entry as evidence of
    the gen4_turbo image_to_video route ($0.05/sec).

    Baseline storyboard_ad dogfood: each 5s shot billed
    exactly 25 credits = $0.25 (gen4_turbo). The prior
    estimator ignored slot wiring and quoted the gen4.5 rate
    ($0.60), over-quoting by 2.4×.
    """
    inputs = [{"slot": "reference_image", "from_step_position": 0}]
    assert GenerateVisualClipPrimitive.estimate_cost(
        {"duration": 5}, inputs=inputs,
    ) == 250_000
    assert GenerateVisualClipPrimitive.estimate_cost(
        {"duration": 10}, inputs=inputs,
    ) == 500_000


def test_resolved_inputs_reference_image_also_routes_to_gen4_turbo() -> None:
    """At runtime write-back, ``resolved_inputs`` has the shape
    ``[{"slot": ..., "asset": <Asset>}, ...]``. The estimator
    should treat that shape identically to raw wiring — both
    indicate a gen4_turbo image_to_video route."""
    class _FakeAsset:
        pass
    resolved = [{"slot": "reference_image", "asset": _FakeAsset()}]
    assert GenerateVisualClipPrimitive.estimate_cost(
        {"duration": 5}, inputs=resolved,
    ) == 250_000


def test_inputs_without_reference_image_slot_stays_gen45() -> None:
    """Other slot types (backdrop, source, etc.) must not flip
    routing to gen4_turbo — only reference_image does."""
    inputs = [{"slot": "backdrop", "from_step_position": 0}]
    assert GenerateVisualClipPrimitive.estimate_cost(
        {"duration": 5}, inputs=inputs,
    ) == 600_000


def test_composition_cost_estimate_picks_up_visual_clip() -> None:
    ws = _make_workspace("v4estcomp@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "x", "duration": 8},
    )
    step_cost = estimate_step_cost(step)
    comp_cost = estimate_composition_cost(comp)
    assert step_cost > 0
    assert comp_cost == step_cost


# ---- SESSION 253 Stage 3 duration provenance ----------------------


def _ready_with_source(
    duration: float | None,
    duration_source: str | None,
) -> VideoPollResult:
    """Variant that lets tests dial the media-engine's provenance
    marker independently of the raw duration_seconds value."""
    return VideoPollResult(
        task_id="runway_visual_task", status="ready", progress=1.0,
        output_url="/data/_assets/visual-fake.mp4",
        duration_seconds=duration,
        duration_source=duration_source,
        error=None, failure_code=None, mock_mode=False,
    )


def test_real_mode_persists_media_probe_provenance() -> None:
    """SESSION 253 Stage 3 — when the poll response carries a
    measured duration_seconds + duration_source="media_probe",
    the primitive persists them verbatim on the Asset spec."""
    ws = _make_workspace("v4provmeasured@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "A sunset sea.", "duration": 5},
    )

    cm, _fake = _patched_client(
        _create_result(),
        [_ready_with_source(duration=4.87, duration_source="media_probe")],
    )
    with patch(
        "apps.compositions.primitives.visual_clip.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.visual_clip.time.sleep",
    ):
        result = GenerateVisualClipPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    assert result.duration_ms == 4870
    spec = result.extra_source_spec
    assert spec["duration_estimated"] is False
    assert spec["duration_source"] == "media_probe"


def test_real_mode_marks_requested_duration_as_estimated_on_probe_failure() -> None:
    """When the media-engine ffprobe fails and returns
    duration_seconds=None, the primitive falls back to the
    OPERATOR-requested duration and explicitly marks the
    provenance so the audit trail can distinguish measured vs
    fabricated durations."""
    ws = _make_workspace("v4provfallback@test.local")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_visual_clip",
        params={"prompt": "A city street.", "duration": 8},
    )

    cm, _fake = _patched_client(
        _create_result(),
        [_ready_with_source(duration=None, duration_source=None)],
    )
    with patch(
        "apps.compositions.primitives.visual_clip.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.visual_clip.time.sleep",
    ):
        result = GenerateVisualClipPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    # Requested-duration fallback: 8 s * 1000 = 8000 ms.
    assert result.duration_ms == 8000
    spec = result.extra_source_spec
    assert spec["duration_estimated"] is True
    assert spec["duration_source"] == "requested"
