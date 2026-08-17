"""SESSION 258 / P2.H — parallel-execution runtime tests.

Covers the P2 parallel dispatch stack that runs alongside the
sequential V2 runner:

* ``execute_step`` — the per-step Celery task. Idempotency
  guards, no-raise contract, DB-side input resolution, cost
  provenance, step-level failure without composition side
  effects.
* ``execute_composition_layer_coordinator`` — the chord
  callback that runs after every step in a dispatched layer
  reaches terminal state. Failure vs. success vs. dispatch
  branches, malformed-DAG defense, no-op on already-
  finalized composition.
* Feature-flag gates — ``COMPOSITION_PARALLEL_EXECUTION_ENABLED``
  master switch and ``COMPOSITION_PARALLEL_EXECUTION_KINDS``
  allow-list, both consulted by ``execute_composition``.
* End-to-end runs of dialogue_scene-shaped step graphs under
  the parallel path with eager Celery — verifies chord/group
  wiring, cost aggregation, final_asset wiring, and the
  successful-siblings-survive failure economics.

Uses the V2 mock primitives (``mock_passthrough`` /
``mock_failure``) so no provider/HTTP surface is exercised.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    Composition,
    CompositionStatus,
    CompositionStep,
    StepStatus,
)
from apps.compositions.tasks import (
    WorkspaceMismatchError,
    _dispatch_composition_parallel,
    _resolve_inputs_from_db,
    _should_use_parallel_execution,
    execute_composition,
    execute_composition_layer_coordinator,
    execute_step,
)
from apps.spokespeople.models import Teammate

User = get_user_model()


pytestmark = [
    pytest.mark.django_db,
    pytest.mark.usefixtures("_celery_eager"),
]


@pytest.fixture
def _celery_eager():
    """Every Celery signature (``.apply_async`` / ``.delay`` /
    chord dispatch) resolves inline — necessary so the P2 chord
    chain terminates within the test."""
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


# ---- helpers --------------------------------------------------


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_teammate(ws: Workspace, name: str = "Sp") -> Teammate:
    return Teammate.objects.create(workspace=ws, name=name)


def _make_composition(
    ws: Workspace,
    sp: Teammate,
    *,
    name: str = "parallel comp",
    mock_mode: bool = True,
    template_kind: str = "dialogue_scene",
) -> Composition:
    return Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name=name,
        mock_mode=mock_mode,
        template_kind=template_kind,
    )


def _add_step(
    composition: Composition,
    position: int,
    *,
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


def _run_step(step: CompositionStep) -> dict:
    return execute_step.apply(args=[str(step.pk)]).get()


def _run_composition(composition: Composition) -> dict:
    return execute_composition.apply(args=[str(composition.pk)]).get()


# ---- execute_step: idempotency + no-raise contract -----------


def test_execute_step_happy_path_persists_asset_and_marks_succeeded() -> None:
    """The parallel step task runs the primitive, atomically
    persists the output Asset + step transition, and returns a
    success status dict. No composition-status write from here —
    that's the coordinator's job."""
    ws = _make_workspace("pes_ok@test.local", "pes ok")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0)

    result = _run_step(step)

    assert result["status"] == "succeeded"
    assert result["position"] == 0
    assert result["cost_actual_micros"] == 100

    step.refresh_from_db()
    comp.refresh_from_db()
    assert step.status == StepStatus.SUCCEEDED
    assert step.output_asset_id is not None
    assert step.cost_actual_micros == 100
    # execute_step never advances the composition state — only
    # cost_actual is refreshed via the SQL aggregator.
    assert comp.status == CompositionStatus.DRAFT
    assert comp.cost_actual_micros == 100


def test_execute_step_already_succeeded_is_noop() -> None:
    """Resume dispatch fires the task for a step that already
    ran — must not re-execute (no double-cost, no new Asset)."""
    ws = _make_workspace("pes_dupe@test.local", "pes dupe")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0)

    first = _run_step(step)
    assert first["status"] == "succeeded"
    step.refresh_from_db()
    first_asset_id = step.output_asset_id
    assets_before = Asset.objects.filter(composition=comp).count()

    second = _run_step(step)
    assert second["status"] == "already_succeeded"

    step.refresh_from_db()
    assert step.output_asset_id == first_asset_id
    assert Asset.objects.filter(composition=comp).count() == assets_before


def test_execute_step_already_failed_is_noop() -> None:
    """A coordinator resume must not silently retry a FAILED
    step — that's operator-owned via retry_step."""
    ws = _make_workspace("pes_prev_fail@test.local", "pes prev fail")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0, primitive="mock_failure")

    _run_step(step)
    step.refresh_from_db()
    assert step.status == StepStatus.FAILED
    first_error = step.error_message

    result = _run_step(step)
    assert result["status"] == "already_failed"

    step.refresh_from_db()
    assert step.status == StepStatus.FAILED
    assert step.error_message == first_error


def test_execute_step_primitive_failure_marks_step_failed_only() -> None:
    """A primitive raising PrimitiveError must NOT propagate —
    step goes to FAILED, composition remains untouched (chord
    callback decides the composition state after fan-in)."""
    ws = _make_workspace("pes_pfail@test.local", "pes pfail")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    step = _add_step(comp, position=0, primitive="mock_failure")

    result = _run_step(step)

    assert result["status"] == "failed"
    assert result["error_kind"] == "primitive_failure"

    step.refresh_from_db()
    comp.refresh_from_db()
    assert step.status == StepStatus.FAILED
    assert "PrimitiveError" in step.error_message
    # Composition-level status untouched by a single step failure.
    assert comp.status == CompositionStatus.DRAFT
    assert comp.error_message == ""


def test_execute_step_input_resolution_failure_marks_step_failed_with_kind() -> None:
    """DB-side input resolver raising ``InputResolutionError``
    still funnels through the no-raise return contract — the
    step lands FAILED with error_kind=input_resolution."""
    ws = _make_workspace("pes_ires@test.local", "pes ires")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    _add_step(comp, position=0)  # never runs; not upstream of s1
    s1 = _add_step(
        comp, position=1,
        inputs=[{"slot": "source", "from_step_position": 0}],
    )

    # Fire step 1 directly — step 0 is still PENDING, so DB
    # resolution can't find a succeeded upstream.
    result = _run_step(s1)

    assert result["status"] == "failed"
    assert result["error_kind"] == "input_resolution"
    s1.refresh_from_db()
    assert s1.status == StepStatus.FAILED
    assert "upstream step 0" in s1.error_message


# ---- DB-side input resolver ----------------------------------


def test_resolve_inputs_from_db_reads_upstream_output_asset() -> None:
    """After a successful upstream run, the DB resolver hands
    the upstream's output_asset to the downstream step."""
    ws = _make_workspace("res_ok@test.local", "res ok")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    s0 = _add_step(comp, position=0)
    s1 = _add_step(
        comp, position=1,
        inputs=[{"slot": "source", "from_step_position": 0}],
    )

    _run_step(s0)
    s0.refresh_from_db()

    resolved = _resolve_inputs_from_db(s1)
    assert len(resolved) == 1
    assert resolved[0]["slot"] == "source"
    assert resolved[0]["asset"].pk == s0.output_asset_id


def test_resolve_inputs_from_db_rejects_non_succeeded_upstream() -> None:
    """PENDING / RUNNING / FAILED upstreams must raise
    InputResolutionError rather than silently pass the missing
    slot to the primitive."""
    from apps.compositions.tasks import InputResolutionError

    ws = _make_workspace("res_bad@test.local", "res bad")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)
    _add_step(comp, position=0, primitive="mock_failure")
    s1 = _add_step(
        comp, position=1,
        inputs=[{"slot": "source", "from_step_position": 0}],
    )

    with pytest.raises(InputResolutionError) as exc:
        _resolve_inputs_from_db(s1)
    assert "expected SUCCEEDED" in str(exc.value)


def test_resolve_inputs_from_db_workspace_mismatch_raises() -> None:
    """Defense-in-depth: an asset_id pointing at another
    workspace's asset must raise WorkspaceMismatchError even
    though the V1 signal already rejected it at save time.

    We use `Asset.objects.create` directly + push the input dict
    onto the step without triggering `full_clean` so this test
    exercises the runtime check specifically, not the signal.
    """
    ws1 = _make_workspace("res_ws1@test.local", "res ws1")
    ws2 = _make_workspace("res_ws2@test.local", "res ws2")
    sp1 = _make_teammate(ws1)
    from apps.compositions.models import AssetType
    foreign_asset = Asset.objects.create(
        workspace=ws2, asset_type=AssetType.CLIP, file_path="mock://x.mp4",
    )
    comp = _make_composition(ws1, sp1)
    step = _add_step(comp, position=0)
    # Bypass clean() / signal — write directly at the ORM layer.
    step.inputs = [{"slot": "clip", "asset_id": str(foreign_asset.pk)}]
    CompositionStep.objects.filter(pk=step.pk).update(inputs=step.inputs)
    step.refresh_from_db()

    with pytest.raises(WorkspaceMismatchError):
        _resolve_inputs_from_db(step)


# ---- Feature-flag branching ----------------------------------


@override_settings(COMPOSITION_PARALLEL_EXECUTION_ENABLED=False)
def test_should_use_parallel_execution_returns_false_when_flag_off() -> None:
    """Explicit flag-off short-circuits before the kind check —
    every composition routes to sequential regardless of
    template_kind. Uses `override_settings` so this test doesn't
    depend on the live default (which may be flipped True for
    real-provider dogfood while `dialogue_scene` is opted in)."""
    ws = _make_workspace("flag_off@test.local", "flag off")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp)  # template_kind="dialogue_scene"
    assert _should_use_parallel_execution(comp) is False


@override_settings(COMPOSITION_PARALLEL_EXECUTION_ENABLED=True)
def test_should_use_parallel_execution_requires_kind_in_allow_list() -> None:
    """Even with the master switch on, only kinds on the
    allow-list route to parallel dispatch."""
    ws = _make_workspace("flag_on_notallowed@test.local", "flag on notallow")
    sp = _make_teammate(ws)
    comp = _make_composition(
        ws, sp, template_kind="talking_head",  # not in default allow-list
    )
    assert _should_use_parallel_execution(comp) is False


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_execute_composition_dispatches_parallel_when_flag_and_kind_match() -> None:
    """Flag on + kind in allow-list → parallel path takes over.
    With eager Celery, the chord chain runs to completion inline."""
    ws = _make_workspace("flag_par@test.local", "flag par")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")
    # Two independent roots + concat — the classic dialogue_scene shape.
    _add_step(comp, position=0)
    _add_step(comp, position=1)
    _add_step(
        comp, position=2,
        inputs=[
            {"slot": "clip", "from_step_position": 0},
            {"slot": "clip", "from_step_position": 1},
        ],
    )

    _run_composition(comp)

    comp.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    steps = list(comp.steps.all().order_by("position"))
    assert all(s.status == StepStatus.SUCCEEDED for s in steps)
    assert comp.final_asset_id == steps[-1].output_asset_id
    assert comp.cost_actual_micros == 300


# ---- Layer coordinator branches ------------------------------


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_coordinator_finalizes_completed_and_aggregates_provenance() -> None:
    """Full happy-path dialogue_scene shape (2 turns + concat):
    coordinator finalizes COMPLETED, wires final_asset, refreshes
    cost, and (had any speech step written knowledge_chunk_ids to
    its Asset.source_spec) would aggregate them onto the
    composition.

    Uses mock_passthrough so no chunk_ids exist to aggregate,
    but exercises the aggregate-helper call path.
    """
    ws = _make_workspace("coord_ok@test.local", "coord ok")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")
    _add_step(comp, position=0)
    _add_step(comp, position=1)
    _add_step(
        comp, position=2,
        inputs=[
            {"slot": "clip", "from_step_position": 0},
            {"slot": "clip", "from_step_position": 1},
        ],
    )

    _run_composition(comp)
    comp.refresh_from_db()

    assert comp.status == CompositionStatus.COMPLETED
    assert comp.final_asset_id is not None
    assert comp.cost_actual_micros == 300
    # Aggregate helper ran (no chunks to add for mock primitives,
    # but no exception is a signal it fired).
    assert comp.knowledge_chunk_ids in ([], None)


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_coordinator_finalizes_partial_when_sibling_fails_survives_success() -> None:
    """Scope-lock failure economics: one sibling in the parallel
    layer fails, another succeeds. Composition is PARTIAL — the
    successful sibling's Asset is preserved on its step row so a
    later retry_step run can resume only the failed branch."""
    ws = _make_workspace("coord_par@test.local", "coord par")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")
    s0 = _add_step(comp, position=0)  # succeeds
    s1 = _add_step(comp, position=1, primitive="mock_failure")
    # Concat depends on both; it never runs because s1 fails.
    _add_step(
        comp, position=2,
        inputs=[
            {"slot": "clip", "from_step_position": 0},
            {"slot": "clip", "from_step_position": 1},
        ],
    )

    _run_composition(comp)
    comp.refresh_from_db(); s0.refresh_from_db(); s1.refresh_from_db()

    assert comp.status == CompositionStatus.PARTIAL
    assert s0.status == StepStatus.SUCCEEDED
    assert s0.output_asset_id is not None  # sibling survived
    assert s1.status == StepStatus.FAILED
    # Concat never dispatched — layer 1 was skipped due to failure.
    concat = comp.steps.get(position=2)
    assert concat.status == StepStatus.PENDING
    # Composition cost reflects the succeeded sibling only.
    assert comp.cost_actual_micros == 100
    assert comp.final_asset_id is None


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_coordinator_finalizes_failed_when_every_layer0_step_fails() -> None:
    """All layer-0 siblings fail → no succeeded steps anywhere →
    composition is FAILED, not PARTIAL."""
    ws = _make_workspace("coord_all_fail@test.local", "coord all fail")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")
    s0 = _add_step(comp, position=0, primitive="mock_failure")
    s1 = _add_step(comp, position=1, primitive="mock_failure")

    _run_composition(comp)
    comp.refresh_from_db(); s0.refresh_from_db(); s1.refresh_from_db()

    assert comp.status == CompositionStatus.FAILED
    assert s0.status == StepStatus.FAILED
    assert s1.status == StepStatus.FAILED
    assert comp.final_asset_id is None


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_coordinator_noops_on_already_finalized_composition() -> None:
    """Duplicate coordinator invocation (e.g., double dispatch)
    on a composition already in a terminal state → no state
    changes, ``already_finalized`` return."""
    ws = _make_workspace("coord_dup@test.local", "coord dup")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")
    _add_step(comp, position=0)

    _run_composition(comp)
    comp.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    completed_asset_id = comp.final_asset_id

    # Manually re-invoke the coordinator — should no-op.
    result = execute_composition_layer_coordinator.apply(
        args=[[], str(comp.pk), 99],
    ).get()
    assert result["status"] == "already_finalized"

    comp.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    assert comp.final_asset_id == completed_asset_id


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_parallel_dispatch_finalizes_failed_on_malformed_dag() -> None:
    """A cycle / forward reference / self-reference must land
    the composition in FAILED via the parallel entry point's
    DAG-validation catch — no chord dispatched."""
    ws = _make_workspace("coord_dag@test.local", "coord dag")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")
    # Self-reference at step 0 — the P2.A builder rejects it.
    _add_step(
        comp, position=0,
        inputs=[{"slot": "self", "from_step_position": 0}],
    )

    _run_composition(comp)
    comp.refresh_from_db()

    assert comp.status == CompositionStatus.FAILED
    assert "DAG validation" in comp.error_message
    assert "self-reference" in comp.error_message


# ---- Empty + resume paths -------------------------------------


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_parallel_dispatch_finalizes_empty_composition_as_completed() -> None:
    """No steps → the parallel entry point finalizes COMPLETED
    immediately (matches sequential path's `steps_succeeded=0`
    semantics) without dispatching a chord."""
    ws = _make_workspace("coord_empty@test.local", "coord empty")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")

    result = _run_composition(comp)
    assert result["status"] == "completed"
    assert result["steps_succeeded"] == 0

    comp.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    assert comp.cost_actual_micros == 0


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_parallel_dispatch_from_all_succeeded_state_finalizes_without_redispatch() -> None:
    """Resume-after-crash scenario: every step already SUCCEEDED
    but composition is not terminal (crash between last step
    persist and finalize). Parallel entry point finalizes
    COMPLETED without re-executing any step."""
    ws = _make_workspace("coord_resume@test.local", "coord resume")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")
    s0 = _add_step(comp, position=0)
    s1 = _add_step(comp, position=1)
    _run_step(s0)
    _run_step(s1)

    # Composition status still DRAFT because the coordinator
    # never ran. Force the resume path.
    comp.refresh_from_db()
    assert comp.status == CompositionStatus.DRAFT

    result = _dispatch_composition_parallel(comp)
    assert result["status"] == CompositionStatus.COMPLETED
    assert result["steps_succeeded"] == 2

    comp.refresh_from_db()
    assert comp.status == CompositionStatus.COMPLETED
    assert comp.cost_actual_micros == 200


# ---- Cost aggregation across siblings -------------------------


@override_settings(
    COMPOSITION_PARALLEL_EXECUTION_ENABLED=True,
    COMPOSITION_PARALLEL_EXECUTION_KINDS={"dialogue_scene"},
)
def test_parallel_run_aggregates_cost_actual_micros_across_layers() -> None:
    """P1 SQL-aggregator invariant on the parallel path: three
    parallel siblings + fan-in = 4 steps × 100 = 400 micros on
    the composition after finalize. No race, no lost update."""
    ws = _make_workspace("cost_ok@test.local", "cost ok")
    sp = _make_teammate(ws)
    comp = _make_composition(ws, sp, template_kind="dialogue_scene")
    _add_step(comp, position=0)
    _add_step(comp, position=1)
    _add_step(comp, position=2)
    _add_step(
        comp, position=3,
        inputs=[
            {"slot": "clip", "from_step_position": 0},
            {"slot": "clip", "from_step_position": 1},
            {"slot": "clip", "from_step_position": 2},
        ],
    )

    _run_composition(comp)
    comp.refresh_from_db()

    assert comp.status == CompositionStatus.COMPLETED
    assert comp.cost_actual_micros == 400
