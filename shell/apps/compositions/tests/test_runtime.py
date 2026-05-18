"""V2 composition runtime tests.

Named in ``docs/design/VIDEO_COMPOSITION_V1.md`` §"Composition
execution" + the user-supplied V2 brief. Covers:

* Successful mock composition end-to-end (single + multi-step).
* Failed step → composition status=FAILED when step 0 fails.
* Failed step → composition status=PARTIAL when a later step
  fails and earlier ones succeeded.
* ``retry_step`` task resumes from the failed step; prior
  outputs are preserved.
* Workspace mismatch in input resolution is rejected at the
  runtime layer (defense in depth on top of the V1 signal).
* Output Asset rows are created with proper provenance
  (``source_spec``, cost_micros, composition FK, workspace).
* ``from_step_position`` chaining resolves correctly between
  steps.
* Idempotency — re-running on a COMPLETED composition is a
  no-op; re-running on a PARTIAL composition resumes.
* Cost aggregation across successful steps.
* Mock-mode flag propagates from composition to primitives.
* Unknown primitive name → step FAILED, composition state
  set correctly (FAILED if step 0, PARTIAL otherwise).
"""
from __future__ import annotations

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
from apps.compositions.tasks import execute_composition, retry_step
from apps.spokespeople.models import Spokesperson

User = get_user_model()


# Run every Celery task inline so retry_step's .delay() resolves
# synchronously without hitting the broker. Matches the K6 pattern
# in apps/videos/tests/test_render_with_knowledge.py.
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


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_spokesperson(ws: Workspace, name: str = "Sp") -> Spokesperson:
    return Spokesperson.objects.create(workspace=ws, name=name)


def _make_composition(
    ws: Workspace,
    sp: Spokesperson,
    name: str = "test comp",
    mock_mode: bool = True,
) -> Composition:
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name=name,
        mock_mode=mock_mode,
    )


def _add_step(
    composition: Composition,
    position: int,
    primitive: str = "mock_passthrough",
    inputs: list | None = None,
    params: dict | None = None,
) -> CompositionStep:
    return CompositionStep.objects.create(
        composition=composition,
        position=position,
        primitive=primitive,
        inputs=inputs or [],
        params=params or {},
    )


def _run(composition: Composition) -> dict:
    return execute_composition.apply(args=[str(composition.pk)]).get()


# ---- happy path ----------------------------------------------------


@pytest.mark.django_db
def test_single_step_composition_completes() -> None:
    """The trivial happy path — one mock_passthrough step,
    composition reaches COMPLETED with a final_asset."""
    ws = _make_workspace("v2single@test.local", "V2 single")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0)

    result = _run(comp)

    assert result["status"] == "completed"
    assert result["steps_succeeded"] == 1

    comp.refresh_from_db()
    step.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    assert step.status == StepStatus.SUCCEEDED
    assert comp.final_asset_id == step.output_asset_id
    assert comp.final_asset is not None
    assert comp.final_asset.composition_id == comp.pk
    assert comp.cost_actual_micros == 100  # mock_passthrough fixed cost


@pytest.mark.django_db
def test_multi_step_composition_completes_in_order() -> None:
    """Three mock steps run in position order; final_asset is
    the last step's output."""
    ws = _make_workspace("v2multi@test.local", "V2 multi")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    s0 = _add_step(comp, position=0)
    s1 = _add_step(comp, position=1)
    s2 = _add_step(comp, position=2)

    result = _run(comp)
    assert result["status"] == "completed"
    assert result["steps_succeeded"] == 3

    comp.refresh_from_db()
    s0.refresh_from_db(); s1.refresh_from_db(); s2.refresh_from_db()
    assert all(s.status == StepStatus.SUCCEEDED for s in (s0, s1, s2))
    assert comp.final_asset_id == s2.output_asset_id
    assert comp.cost_actual_micros == 300  # 3 × 100


@pytest.mark.django_db
def test_output_asset_inherits_title_from_composition_name() -> None:
    """W11.6.5.3 — every Asset persisted by the runtime
    auto-titles from the parent composition's name. This is
    what makes the asset_picker dropdowns readable instead
    of showing CDN URL tails for clips."""
    ws = _make_workspace("v2title@test.local", "V2 title")
    sp = _make_spokesperson(ws)
    comp = _make_composition(
        ws, sp, name="Talking-head — Marcus", mock_mode=True,
    )
    _add_step(comp, position=0)
    _run(comp)
    comp.refresh_from_db()
    assert comp.final_asset is not None
    assert comp.final_asset.title == "Talking-head — Marcus"


def test_output_asset_title_truncates_long_composition_name() -> None:
    """W11.6.5.3 — Asset.title is CharField(max_length=120).
    Long composition names truncate cleanly without raising
    on save."""
    ws = _make_workspace("v2titlelong@test.local", "V2 title long")
    sp = _make_spokesperson(ws)
    long_name = "A" * 200
    comp = _make_composition(ws, sp, name=long_name, mock_mode=True)
    _add_step(comp, position=0)
    _run(comp)
    comp.refresh_from_db()
    assert comp.final_asset is not None
    assert len(comp.final_asset.title) == 120
    assert comp.final_asset.title == "A" * 120


@pytest.mark.django_db
def test_multi_step_assets_disambiguate_titles() -> None:
    """SESSION 177 — when a composition has more than one step,
    each step's output Asset gets a `— step N/M (<primitive>)`
    suffix so the SPA asset_picker can tell intermediate +
    final outputs apart. Single-step compositions stay
    unchanged (W11.6.5.3 behavior preserved by
    test_output_asset_inherits_title_from_composition_name)."""
    from apps.compositions.models import Asset

    ws = _make_workspace("v2multititle@test.local", "V2 multi title")
    sp = _make_spokesperson(ws)
    comp = _make_composition(
        ws, sp, name="Long-form Ad — Marcus", mock_mode=True,
    )
    _add_step(comp, position=0)
    _add_step(comp, position=1)
    _add_step(comp, position=2)
    _run(comp)
    comp.refresh_from_db()
    assets = list(
        Asset.objects.filter(composition=comp).order_by("created_at")
    )
    assert len(assets) == 3
    assert assets[0].title == "Long-form Ad — Marcus — step 1/3 (mock_passthrough)"
    assert assets[1].title == "Long-form Ad — Marcus — step 2/3 (mock_passthrough)"
    assert assets[2].title == "Long-form Ad — Marcus — step 3/3 (mock_passthrough)"


@pytest.mark.django_db
def test_multi_step_title_respects_120_char_cap() -> None:
    """When the composition name + step suffix would exceed
    `Asset.title`'s 120-char ceiling, the base name truncates
    first so the suffix stays intact (the suffix is what makes
    the title disambiguatable)."""
    from apps.compositions.models import Asset

    ws = _make_workspace("v2multilong@test.local", "V2 multi long")
    sp = _make_spokesperson(ws)
    long_name = "A" * 200
    comp = _make_composition(ws, sp, name=long_name, mock_mode=True)
    _add_step(comp, position=0)
    _add_step(comp, position=1)
    _run(comp)
    comp.refresh_from_db()
    assets = list(
        Asset.objects.filter(composition=comp).order_by("created_at")
    )
    for a in assets:
        assert len(a.title) <= 120
        # Suffix must survive even when base is truncated.
        assert "— step " in a.title
        assert "(mock_passthrough)" in a.title


def test_output_asset_records_provenance() -> None:
    """The Asset created by a step records primitive name,
    step position, composition id, params + mock_mode in
    its source_spec."""
    ws = _make_workspace("v2prov@test.local", "V2 prov")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp, mock_mode=True)
    step = _add_step(comp, position=0, params={"foo": "bar"})

    _run(comp)
    step.refresh_from_db()
    asset = step.output_asset
    assert asset is not None

    spec = asset.source_spec
    assert spec["primitive"] == "mock_passthrough"
    assert spec["step_position"] == 0
    assert spec["step_id"] == str(step.id)
    assert spec["composition_id"] == str(comp.id)
    assert spec["params"] == {"foo": "bar"}
    assert spec["mock_mode"] is True
    # The mock primitive injects extras via extra_source_spec
    assert spec["mock"] is True
    assert spec["resolved_input_slots"] == []

    # Type-specific metadata persisted
    assert asset.asset_type == AssetType.CLIP
    assert asset.duration_ms == 5000
    assert asset.width == 1280
    assert asset.height == 720
    assert asset.mime_type == "video/mp4"
    assert asset.cost_micros == 100
    assert asset.workspace_id == ws.pk
    assert asset.composition_id == comp.pk


# ---- step chaining --------------------------------------------------


@pytest.mark.django_db
def test_step_chaining_via_from_step_position() -> None:
    """Step 1 takes step 0's output as input; runtime resolves
    the upstream asset and primitive sees it in resolved_inputs."""
    ws = _make_workspace("v2chain@test.local", "V2 chain")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _add_step(comp, position=0)
    s1 = _add_step(
        comp, position=1,
        inputs=[{"slot": "source", "from_step_position": 0}],
    )

    _run(comp)
    s1.refresh_from_db()
    assert s1.status == StepStatus.SUCCEEDED
    # The mock primitive records resolved slots in source_spec
    spec = s1.output_asset.source_spec
    assert spec["resolved_input_slots"] == ["source"]


@pytest.mark.django_db
def test_step_chaining_to_missing_upstream_fails_input_resolution() -> None:
    """``from_step_position`` referencing a step that hasn't
    run yet (out-of-order chain) raises InputResolutionError
    → step FAILED. Composition is FAILED since the broken
    chain is step 0."""
    ws = _make_workspace("v2chainfail@test.local", "V2 chainfail")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    s0 = _add_step(
        comp, position=0,
        inputs=[{"slot": "source", "from_step_position": 5}],  # nonexistent
    )

    result = _run(comp)
    assert result["status"] == CompositionStatus.FAILED
    assert result["error_kind"] == "input_resolution"
    s0.refresh_from_db()
    assert s0.status == StepStatus.FAILED
    assert "from_step_position 5" in s0.error_message


# ---- failure paths --------------------------------------------------


@pytest.mark.django_db
def test_step_zero_failure_marks_composition_failed() -> None:
    """First-step failure → composition FAILED (not PARTIAL,
    because no earlier step succeeded)."""
    ws = _make_workspace("v2fail0@test.local", "V2 fail0")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0, primitive="mock_failure")

    result = _run(comp)
    assert result["status"] == CompositionStatus.FAILED
    assert result["error_kind"] == "primitive_failure"

    comp.refresh_from_db(); step.refresh_from_db()
    assert comp.status == CompositionStatus.FAILED
    assert step.status == StepStatus.FAILED
    assert "PrimitiveError" in step.error_message
    assert comp.final_asset is None


@pytest.mark.django_db
def test_step_failure_after_success_marks_composition_partial() -> None:
    """Step 0 succeeds, step 1 fails → composition PARTIAL.
    Step 0's output_asset is preserved for resume."""
    ws = _make_workspace("v2partial@test.local", "V2 partial")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    s0 = _add_step(comp, position=0)
    s1 = _add_step(comp, position=1, primitive="mock_failure")

    result = _run(comp)
    assert result["status"] == CompositionStatus.PARTIAL

    comp.refresh_from_db(); s0.refresh_from_db(); s1.refresh_from_db()
    assert comp.status == CompositionStatus.PARTIAL
    assert s0.status == StepStatus.SUCCEEDED
    assert s0.output_asset_id is not None  # preserved
    assert s1.status == StepStatus.FAILED
    # Composition cost reflects only what succeeded
    assert comp.cost_actual_micros == 100


@pytest.mark.django_db
def test_unknown_primitive_fails_step_with_clear_error() -> None:
    """A primitive name not in the registry → step FAILED
    with error_kind=unknown_primitive."""
    ws = _make_workspace("v2unkn@test.local", "V2 unkn")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0, primitive="does_not_exist")

    result = _run(comp)
    assert result["error_kind"] == "unknown_primitive"
    step.refresh_from_db()
    assert step.status == StepStatus.FAILED
    assert "UnknownPrimitiveError" in step.error_message
    assert "does_not_exist" in step.error_message


# ---- retry / resume -------------------------------------------------


@pytest.mark.django_db
def test_retry_step_resumes_from_failed_position() -> None:
    """After a PARTIAL run, retry_step on the failed step
    flips it back to PENDING + re-enqueues the composition.
    The runtime skips the already-SUCCEEDED step and
    completes the rest."""
    ws = _make_workspace("v2retry@test.local", "V2 retry")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    s0 = _add_step(comp, position=0)
    s1 = _add_step(comp, position=1, primitive="mock_failure")

    # First run — fails at step 1.
    _run(comp)
    comp.refresh_from_db(); s0.refresh_from_db(); s1.refresh_from_db()
    assert comp.status == CompositionStatus.PARTIAL
    s0_asset_id = s0.output_asset_id
    assert s0_asset_id is not None

    # Flip step 1's primitive to a success so retry can win.
    s1.primitive = "mock_passthrough"
    s1.save(update_fields=["primitive"])

    # Retry the failed step.
    retry_result = retry_step.apply(args=[str(s1.pk)]).get()
    assert retry_result["status"] == "retried"

    # Composition should now be COMPLETED. retry_step
    # enqueues execute_composition via .delay() which runs
    # inline under CELERY_TASK_ALWAYS_EAGER (set via
    # pyproject.toml's test config — verify with a refresh).
    comp.refresh_from_db(); s0.refresh_from_db(); s1.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    # Step 0's output was preserved across retry.
    assert s0.output_asset_id == s0_asset_id
    assert s1.status == StepStatus.SUCCEEDED


@pytest.mark.django_db
def test_retry_step_on_non_failed_step_is_noop() -> None:
    ws = _make_workspace("v2retrynoop@test.local", "V2 retry noop")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0)

    _run(comp)
    step.refresh_from_db()
    assert step.status == StepStatus.SUCCEEDED

    out = retry_step.apply(args=[str(step.pk)]).get()
    assert out["status"] == "not_failed"


# ---- idempotency ----------------------------------------------------


@pytest.mark.django_db
def test_running_completed_composition_is_noop() -> None:
    """execute_composition on a COMPLETED composition is a
    no-op (idempotent re-runs are safe)."""
    ws = _make_workspace("v2idem@test.local", "V2 idem")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _add_step(comp, position=0)
    _run(comp)
    comp.refresh_from_db()
    asset_count_before = Asset.objects.filter(composition=comp).count()

    out = _run(comp)
    assert out["status"] == "already_completed"
    asset_count_after = Asset.objects.filter(composition=comp).count()
    assert asset_count_before == asset_count_after, "no duplicate Assets on re-run"


@pytest.mark.django_db
def test_running_failed_composition_with_no_retry_is_noop() -> None:
    """A composition that's terminal-FAILED (no PENDING steps
    to retry) should no-op on re-run rather than re-attempting."""
    ws = _make_workspace("v2failidem@test.local", "V2 fail idem")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _add_step(comp, position=0, primitive="mock_failure")
    _run(comp)
    comp.refresh_from_db()
    assert comp.status == CompositionStatus.FAILED

    out = _run(comp)
    assert out["status"] == "already_failed_no_retry"


# ---- workspace isolation -------------------------------------------


@pytest.mark.django_db
def test_runtime_rejects_cross_workspace_asset_input() -> None:
    """The V1 signal already rejects cross-workspace
    asset_id at save time. The runtime additionally rejects
    in input resolution — defense in depth. This test
    bypasses the signal by raw SQL to verify the runtime's
    defense holds even if a row somehow lands.

    In practice the signal catches everything; this test
    exists so that if a future refactor accidentally drops
    the signal, the runtime still rejects.
    """
    from django.db import connection

    ws_a = _make_workspace("v2isoA@test.local", "V2 iso A")
    ws_b = _make_workspace("v2isoB@test.local", "V2 iso B")
    sp_a = _make_spokesperson(ws_a)

    # Asset in workspace B
    foreign_asset = Asset.objects.create(
        workspace=ws_b,
        asset_type=AssetType.TRANSCRIPT,
        inline_content="hello",
    )
    comp_a = _make_composition(ws_a, sp_a)

    # Bypass the signal by creating the step with no inputs,
    # then patching inputs via raw SQL.
    step = CompositionStep.objects.create(
        composition=comp_a, position=0, primitive="mock_passthrough",
    )
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE compositions_compositionstep SET inputs = %s WHERE id = %s",
            [
                f'[{{"slot": "src", "asset_id": "{foreign_asset.pk}"}}]',
                str(step.pk),
            ],
        )

    result = _run(comp_a)
    assert result["error_kind"] == "workspace_mismatch"

    step.refresh_from_db()
    assert step.status == StepStatus.FAILED
    assert "workspace" in step.error_message.lower()


@pytest.mark.django_db
def test_runtime_handles_missing_asset_id_gracefully() -> None:
    """A step input referencing a non-existent asset_id →
    InputResolutionError → step FAILED with clear message
    (not a 500)."""
    import uuid

    from django.db import connection

    ws = _make_workspace("v2miss@test.local", "V2 miss")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = CompositionStep.objects.create(
        composition=comp, position=0, primitive="mock_passthrough",
    )
    # Bypass the validator — the signal would otherwise raise on save.
    missing_id = uuid.uuid4()
    with connection.cursor() as cursor:
        cursor.execute(
            "UPDATE compositions_compositionstep SET inputs = %s WHERE id = %s",
            [
                f'[{{"slot": "src", "asset_id": "{missing_id}"}}]',
                str(step.pk),
            ],
        )

    result = _run(comp)
    assert result["error_kind"] == "input_resolution"
    step.refresh_from_db()
    assert step.status == StepStatus.FAILED
    assert "not found" in step.error_message.lower()


# ---- cost estimation ------------------------------------------------


@pytest.mark.django_db
def test_estimate_composition_cost_sums_step_estimates() -> None:
    """``estimate_composition_cost`` sums per-primitive
    estimates. mock_passthrough = 100; mock_failure = 100;
    mock_slow = 50."""
    ws = _make_workspace("v2est@test.local", "V2 est")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _add_step(comp, position=0, primitive="mock_passthrough")
    _add_step(comp, position=1, primitive="mock_failure")
    _add_step(comp, position=2, primitive="mock_slow")
    _add_step(comp, position=3, primitive="does_not_exist")  # unknown → 0

    assert estimate_composition_cost(comp) == 100 + 100 + 50 + 0


@pytest.mark.django_db
def test_cost_actual_aggregates_after_success() -> None:
    ws = _make_workspace("v2costact@test.local", "V2 cost act")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    _add_step(comp, position=0)
    _add_step(comp, position=1, primitive="mock_slow")

    _run(comp)
    comp.refresh_from_db()
    assert comp.cost_actual_micros == 150  # 100 + 50


# ---- mock-mode propagation -----------------------------------------


@pytest.mark.django_db
def test_mock_mode_flag_records_in_source_spec() -> None:
    """``composition.mock_mode`` propagates into each asset's
    source_spec so audit trails distinguish demo runs from
    real ones."""
    ws = _make_workspace("v2mock@test.local", "V2 mock")
    sp = _make_spokesperson(ws)
    comp_real = _make_composition(ws, sp, name="real", mock_mode=False)
    comp_mock = _make_composition(ws, sp, name="mock", mock_mode=True)
    _add_step(comp_real, position=0)
    _add_step(comp_mock, position=0)

    _run(comp_real)
    _run(comp_mock)

    real_step = comp_real.steps.first()
    mock_step = comp_mock.steps.first()
    assert real_step.output_asset.source_spec["mock_mode"] is False
    assert mock_step.output_asset.source_spec["mock_mode"] is True


# ---- small smoke tests on the helpers -------------------------------


@pytest.mark.django_db
def test_estimate_step_cost_handles_unknown_primitive() -> None:
    """Unknown primitive in the estimator returns 0 (no
    crash) — the step will fail at execute time with a
    clearer error."""
    ws = _make_workspace("v2estu@test.local", "V2 est unk")
    sp = _make_spokesperson(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0, primitive="not_real")
    assert estimate_step_cost(step) == 0
