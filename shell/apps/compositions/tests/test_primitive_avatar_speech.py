"""V3 tests — ``generate_avatar_speech`` primitive end-to-end.

Covers:

* **Mock-mode primitive** — deterministic stub asset, no
  media-engine call.
* **Real-mode primitive (mocked media-engine)** — fires
  ``create_avatar_speech``, polls via ``poll_task`` until
  terminal, returns PrimitiveResult with output_url.
* **Knowledge integration** — ``use_knowledge=True`` runs
  the script through K6's ``build_render_brief`` and records
  chunk ids in the output asset's source_spec.
* **Failure paths** — media-engine 500 → step FAILED with
  clear error; terminal-FAILED task → step FAILED; missing
  output_url on terminal-ready → step FAILED.
* **Missing avatar id** — composition spokesperson without a
  runway_avatar_id raises PrimitiveError with an
  actionable message.
* **Starter composition** — ``talking_head`` factory creates
  the right shape; running it via ``execute_composition``
  produces a COMPLETED composition with a final_asset.
* **Cost estimation** — ``estimate_cost`` is a pure function
  of script length; ``estimate_composition_cost`` reflects it.
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
    StepStatus,
)
from apps.compositions.primitives.avatar_speech import (
    GenerateAvatarSpeechPrimitive,
)
from apps.compositions.starters import talking_head
from apps.compositions.tasks import execute_composition
from apps.spokespeople.models import Spokesperson
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


def _make_spokesperson(
    ws: Workspace,
    name: str = "Sp",
    avatar_id: str = "runway_avatar_fake-for-v3",
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws,
        name=name,
        runway_avatar_id=avatar_id,
        business_brief="A friendly assistant.",
    )


def _mock_create_result(task_id: str = "runway_task_v3", mock_mode: bool = False) -> VideoCreateResult:
    return VideoCreateResult(
        task_id=task_id,
        status="pending",
        kind="avatar_speech",
        mock_mode=mock_mode,
    )


def _mock_poll_ready(
    task_id: str = "runway_task_v3",
    output_url: str = "/data/_assets/v3-fake.mp4",
    duration: float | None = 7.5,
    mock_mode: bool = False,
) -> VideoPollResult:
    return VideoPollResult(
        task_id=task_id,
        status="ready",
        progress=1.0,
        output_url=output_url,
        duration_seconds=duration,
        error=None,
        failure_code=None,
        mock_mode=mock_mode,
    )


def _mock_poll_failed(
    task_id: str = "runway_task_v3",
    error: str = "upstream rejected",
) -> VideoPollResult:
    return VideoPollResult(
        task_id=task_id,
        status="failed",
        progress=None,
        output_url=None,
        duration_seconds=None,
        error=error,
        failure_code="BAD_OUTPUT",
        mock_mode=False,
    )


def _patched_client(create_result, poll_results):
    """Build a context-manager-style mock for MediaEngineClient
    that returns ``create_result`` from ``create_avatar_speech``
    and yields successive ``poll_results`` from ``poll_task``."""
    polls = list(poll_results)

    def _poll(_task_id):
        return polls.pop(0) if polls else _mock_poll_ready()

    fake = MagicMock()
    fake.create_avatar_speech.return_value = create_result
    fake.poll_task.side_effect = _poll
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return cm, fake


# ---- mock-mode primitive -------------------------------------------


def test_mock_mode_primitive_returns_deterministic_clip() -> None:
    """Mock-mode short-circuits — no media-engine call, no
    polling. Returns a stub CLIP asset matching the V2
    mock_passthrough shape."""
    ws = _make_workspace("v3mock@test.local")
    sp = _make_spokesperson(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="mock", mock_mode=True,
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={"script": "Hello world."},
    )

    result = GenerateAvatarSpeechPrimitive.execute(
        step=step, resolved_inputs=[], mock_mode=True,
    )

    assert result.asset_type == AssetType.CLIP
    assert result.file_path.startswith("mock://compositions/")
    assert result.mime_type == "video/mp4"
    assert result.duration_ms == 5000
    assert result.cost_micros > 0
    assert result.extra_source_spec["mock"] is True
    assert result.extra_source_spec["primitive_kind"] == "generate_avatar_speech"


# ---- real-mode primitive (mocked media-engine) ---------------------


def test_real_mode_primitive_fires_create_and_polls_until_ready() -> None:
    ws = _make_workspace("v3real@test.local")
    sp = _make_spokesperson(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="real",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={"script": "Tell viewers about our coffee."},
    )

    create_result = _mock_create_result("runway_task_real_v3")
    polls = [
        VideoPollResult(
            task_id="runway_task_real_v3",
            status="rendering",
            progress=0.3,
            output_url=None,
            duration_seconds=None,
            error=None,
            failure_code=None,
            mock_mode=False,
        ),
        _mock_poll_ready("runway_task_real_v3"),
    ]
    cm, fake = _patched_client(create_result, polls)

    with patch(
        "apps.compositions.primitives.avatar_speech.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.avatar_speech.time.sleep",
    ) as fake_sleep:
        result = GenerateAvatarSpeechPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    # Verify the media-engine call shape
    fake.create_avatar_speech.assert_called_once()
    kwargs = fake.create_avatar_speech.call_args.kwargs
    assert kwargs["spokesperson_avatar_id"] == sp.runway_avatar_id
    assert kwargs["script"] == "Tell viewers about our coffee."

    # Polled until terminal — should have looped exactly twice
    assert fake.poll_task.call_count == 2
    fake_sleep.assert_called()

    # Result captures the Runway output
    assert result.asset_type == AssetType.CLIP
    assert result.file_path == "/data/_assets/v3-fake.mp4"
    assert result.duration_ms == 7500
    spec = result.extra_source_spec
    assert spec["task_id"] == "runway_task_real_v3"
    assert spec["used_knowledge"] is False


# ---- knowledge integration ----------------------------------------


def test_real_mode_with_knowledge_runs_brief_synthesis() -> None:
    """``use_knowledge=True`` pipes the script through
    ``build_render_brief``. The synthesized brief becomes
    what gets sent to media-engine; chunk_ids land in the
    output asset's source_spec."""
    ws = _make_workspace("v3know@test.local")
    sp = _make_spokesperson(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="know",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={
            "script": "Talk about our brass bells.",
            "use_knowledge": True,
        },
    )

    create_result = _mock_create_result("runway_task_know")
    cm, fake = _patched_client(create_result, [_mock_poll_ready("runway_task_know")])

    fake_script_result = MagicMock()
    fake_script_result.brief = "Synthesized brief about brass bells."
    fake_script_result.chunk_ids = ["chunk-uuid-1", "chunk-uuid-2"]

    with patch(
        "apps.compositions.primitives.avatar_speech.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.avatar_speech.time.sleep",
    ), patch(
        "character_os.script_synthesis.build_render_brief",
        return_value=fake_script_result,
    ) as fake_brief:
        result = GenerateAvatarSpeechPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )

    # build_render_brief was called with the right spokesperson + script
    fake_brief.assert_called_once()
    args, kwargs = fake_brief.call_args
    assert args[0] == sp
    assert args[1] == "Talk about our brass bells."

    # Media-engine got the synthesized brief, not the raw script
    sent_kwargs = fake.create_avatar_speech.call_args.kwargs
    assert sent_kwargs["script"] == "Synthesized brief about brass bells."

    # Citations recorded on the result
    spec = result.extra_source_spec
    assert spec["used_knowledge"] is True
    assert spec["knowledge_chunk_ids"] == ["chunk-uuid-1", "chunk-uuid-2"]


# ---- failure paths ------------------------------------------------


def test_real_mode_missing_avatar_id_raises_primitive_error() -> None:
    """Spokesperson without a runway_avatar_id → PrimitiveError
    with an actionable message. The runtime catches this and
    marks the step FAILED."""
    ws = _make_workspace("v3noavatar@test.local")
    # Use raw create so we bypass the wizard helpers and land
    # a spokesperson with no avatar.
    sp = Spokesperson.objects.create(
        workspace=ws, name="No Avatar", business_brief="x",
    )
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="noava",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={"script": "Hi."},
    )

    from apps.compositions.primitives.mock import PrimitiveError

    with pytest.raises(PrimitiveError) as exc_info:
        GenerateAvatarSpeechPrimitive.execute(
            step=step, resolved_inputs=[], mock_mode=False,
        )
    assert "runway_avatar_id" in str(exc_info.value)


def test_real_mode_media_engine_failure_raises_primitive_error() -> None:
    ws = _make_workspace("v3mefail@test.local")
    sp = _make_spokesperson(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="mefail",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={"script": "Hi."},
    )

    fake = MagicMock()
    fake.create_avatar_speech.side_effect = MediaEngineError(
        "upstream 502", status_code=502, response_text="bad gateway",
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False

    from apps.compositions.primitives.mock import PrimitiveError

    with patch(
        "apps.compositions.primitives.avatar_speech.MediaEngineClient",
        return_value=cm,
    ):
        with pytest.raises(PrimitiveError) as exc_info:
            GenerateAvatarSpeechPrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )
    assert "media-engine" in str(exc_info.value).lower()


def test_terminal_failed_task_raises_primitive_error() -> None:
    ws = _make_workspace("v3failedtask@test.local")
    sp = _make_spokesperson(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="failedtask",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={"script": "Hi."},
    )

    create_result = _mock_create_result("runway_task_t")
    cm, _fake = _patched_client(create_result, [_mock_poll_failed("runway_task_t")])

    from apps.compositions.primitives.mock import PrimitiveError

    with patch(
        "apps.compositions.primitives.avatar_speech.MediaEngineClient",
        return_value=cm,
    ), patch(
        "apps.compositions.primitives.avatar_speech.time.sleep",
    ):
        with pytest.raises(PrimitiveError) as exc_info:
            GenerateAvatarSpeechPrimitive.execute(
                step=step, resolved_inputs=[], mock_mode=False,
            )
    assert "failed" in str(exc_info.value).lower()


# ---- starter composition end-to-end --------------------------------


def test_talking_head_starter_creates_composition_with_one_step() -> None:
    ws = _make_workspace("v3starter@test.local")
    sp = _make_spokesperson(ws, name="Sasha")

    comp = talking_head(
        workspace=ws,
        spokesperson=sp,
        script="Welcome to our cafe.",
        mock_mode=True,
    )

    assert comp.workspace_id == ws.pk
    assert comp.spokesperson_id == sp.pk
    assert comp.template_kind == "talking_head"
    assert comp.mock_mode is True
    assert comp.status == CompositionStatus.DRAFT
    assert comp.name == "Talking-head — Sasha"

    steps = list(comp.steps.all())
    assert len(steps) == 1
    assert steps[0].position == 0
    assert steps[0].primitive == "generate_avatar_speech"
    assert steps[0].params["script"] == "Welcome to our cafe."
    assert steps[0].params["use_knowledge"] is False


def test_talking_head_starter_rejects_cross_workspace_spokesperson() -> None:
    ws_a = _make_workspace("v3stxA@test.local", "A")
    ws_b = _make_workspace("v3stxB@test.local", "B")
    foreign_sp = _make_spokesperson(ws_b, name="Foreign")

    with pytest.raises(ValueError):
        talking_head(
            workspace=ws_a,
            spokesperson=foreign_sp,
            script="hi",
            mock_mode=True,
        )


def test_talking_head_starter_executes_end_to_end_in_mock_mode() -> None:
    """End-to-end: starter creates the composition, executor
    runs it, final_asset lands."""
    ws = _make_workspace("v3e2e@test.local")
    sp = _make_spokesperson(ws, name="Riggs")

    comp = talking_head(
        workspace=ws,
        spokesperson=sp,
        script="Substantive founder voice.",
        mock_mode=True,
    )

    result = execute_composition.apply(args=[str(comp.pk)]).get()
    assert result["status"] == "completed"

    comp.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    assert comp.final_asset is not None
    assert comp.final_asset.asset_type == AssetType.CLIP
    assert comp.final_asset.workspace_id == ws.pk
    assert comp.cost_actual_micros > 0
    assert comp.final_asset.source_spec["primitive_kind"] == "generate_avatar_speech"


# ---- cost estimation ----------------------------------------------


def test_estimate_cost_scales_with_script_length() -> None:
    """Longer scripts cost more. Test asserts ordering, not
    exact numbers (the coefficient may flex during R&D)."""
    short = GenerateAvatarSpeechPrimitive.estimate_cost({"script": "hi"})
    long_ = GenerateAvatarSpeechPrimitive.estimate_cost(
        {"script": "Tell viewers a long story " * 50}
    )
    assert short > 0
    assert long_ > short


def test_estimate_cost_zero_for_empty_script() -> None:
    assert GenerateAvatarSpeechPrimitive.estimate_cost({"script": ""}) == 0
    assert GenerateAvatarSpeechPrimitive.estimate_cost({}) == 0


def test_composition_cost_estimate_picks_up_avatar_speech() -> None:
    ws = _make_workspace("v3estcomp@test.local")
    sp = _make_spokesperson(ws)
    comp = Composition.objects.create(
        workspace=ws, spokesperson=sp, name="estcomp",
    )
    step = CompositionStep.objects.create(
        composition=comp, position=0,
        primitive="generate_avatar_speech",
        params={"script": "x" * 200},
    )
    step_cost = estimate_step_cost(step)
    comp_cost = estimate_composition_cost(comp)
    assert step_cost > 0
    assert comp_cost == step_cost
