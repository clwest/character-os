"""R7.2 tests — async tool dispatch + render_video.

What this slice ships:

1. ``QUEUED`` status on ``RealtimeToolInvocation.Status``
   + migration ``0003_r7_2_queued_status``.
2. Generic ``execute_tool_invocation`` Celery task in
   ``apps/realtime/tasks.py``. Resolves invocation +
   spec, calls executor, updates row + links
   ``produced_composition`` / ``produced_asset`` from
   the executor's return payload.
3. ``dispatch_tool`` async branch now actually enqueues
   Celery (was a stub in R7.0). ``approve_invocation``
   also enqueues for async tools.
4. ``render_video`` async tool — fires a composition
   starter (default ``talking_head``). $0.08 cost (over
   the $0.05 default approval threshold) so it exercises
   the ``awaiting_approval`` flow end-to-end.

Covered (15 tests):

* Async dispatch: under-threshold async tool → QUEUED →
  SUCCEEDED (eager Celery executes inline).
* Approval flow: over-threshold async → AWAITING_APPROVAL
  → approve → QUEUED → SUCCEEDED.
* Approval flow: reject path unchanged.
* Celery task: executor raises → FAILED row.
* Celery task: tool de-registered → FAILED row.
* Celery task: terminal-state idempotency.
* `render_video`: happy path → composition created +
  linked via produced_composition + audit row SUCCEEDED.
* `render_video`: missing script → FAILED.
* `render_video`: unknown recipe → FAILED.
* `render_video`: tier limit exceeded → FAILED.
* `render_video`: cost is over threshold (verifies the
  flow lands `awaiting_approval` from a fresh dispatch).
* `render_video`: approve completes the render through
  Celery.
* REST integration: dispatch via `/invoke_tool/` returns
  202 awaiting_approval, approve via
  `/realtime_tool_invocations/<id>/approve/` returns
  200 succeeded with composition_id.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.billing.models import Subscription
from apps.compositions.models import Composition
from apps.realtime.dispatch import dispatch_tool
from apps.realtime.models import RealtimeSession, RealtimeToolInvocation
from apps.realtime.tools import clear_registry, register_tool
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _settings():
    """Eager Celery + force-mocks. Eager mode runs Celery
    tasks synchronously so test assertions land without
    polling."""
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
        EMBEDDING_FORCE_MOCK=True,
        RENDER_SCRIPT_FORCE_MOCK=True,
    ):
        yield


@pytest.fixture
def reset_registry():
    """Snapshot + restore the production tool catalog so
    tests can register synthetic tools without polluting."""
    from apps.realtime import tools as _tools_mod
    snapshot = dict(_tools_mod._TOOLS)
    yield
    _tools_mod._TOOLS.clear()
    _tools_mod._TOOLS.update(snapshot)


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _set_tier(ws: Workspace, tier: str) -> None:
    sub, _ = Subscription.objects.get_or_create(
        workspace=ws,
        defaults={"tier": tier, "status": Subscription.Status.ACTIVE},
    )
    sub.tier = tier
    sub.save()


def _make_spokesperson(ws: Workspace, name: str = "Sasha") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id="av_test",
        portrait_path="https://fake/p.png", business_brief="brief",
    )


def _make_session(ws: Workspace, sp: Spokesperson) -> RealtimeSession:
    return RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.READY,
        provider_session_id="rt_x",
    )


# ---- dispatcher async path --------------------------------------


def test_async_under_threshold_executes_via_celery(reset_registry):
    """Async tool under the cost threshold: dispatch enqueues
    Celery, eager mode runs it inline, invocation lands
    SUCCEEDED."""
    @register_tool(
        name="synth_async_cheap",
        description="Test async tool",
        cost_micros=1_000,  # well under $0.05 threshold
        workspace_scoped=True,
        is_async=True,
    )
    def _exec(session, args):
        return {"ran": True, "echo": args.get("payload", "")}

    ws, user = _make_workspace("r72a1@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "synth_async_cheap", {"payload": "hi"}, user=user,
    )
    # Eager mode → final state is SUCCEEDED, not QUEUED.
    assert result.state == "succeeded"
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED
    assert invocation.completed_at is not None


def test_async_over_threshold_awaits_approval(reset_registry):
    """Async tool over threshold: dispatch creates an
    AWAITING_APPROVAL row, does NOT enqueue Celery.
    Approve then enqueues."""
    @register_tool(
        name="synth_async_pricey",
        description="Test async pricey tool",
        cost_micros=100_000,
        workspace_scoped=True,
        is_async=True,
    )
    def _exec(session, args):
        return {"unreachable_before_approval": True}

    ws, user = _make_workspace("r72a2@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "synth_async_pricey", {}, user=user,
    )
    assert result.state == "awaiting_approval"
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    assert invocation.status == RealtimeToolInvocation.Status.AWAITING_APPROVAL
    # Executor NOT called yet.
    assert invocation.completed_at is None


def test_approve_async_invocation_enqueues_celery(reset_registry):
    @register_tool(
        name="synth_approve_async",
        description="Approve cycle for async tool",
        cost_micros=100_000,
        workspace_scoped=True,
        is_async=True,
    )
    def _exec(session, args):
        return {"approved": True, "payload": args.get("val")}

    ws, user = _make_workspace("r72a3@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    dispatched = dispatch_tool(
        session, "synth_approve_async", {"val": 42}, user=user,
    )
    assert dispatched.state == "awaiting_approval"

    from apps.realtime.dispatch import approve_invocation
    invocation = RealtimeToolInvocation.objects.get(
        id=dispatched.invocation_id,
    )
    approved = approve_invocation(invocation)
    assert approved.state == "succeeded"
    invocation.refresh_from_db()
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED


# ---- generic Celery task ----------------------------------------


def test_celery_task_records_failure_on_executor_exception(reset_registry):
    @register_tool(
        name="synth_celery_boom",
        description="Failing async tool",
        cost_micros=1_000,
        workspace_scoped=True,
        is_async=True,
    )
    def _exec(session, args):
        raise RuntimeError("boom inside celery")

    ws, user = _make_workspace("r72ce1@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "synth_celery_boom", {}, user=user,
    )
    # Eager mode → final state reflects the Celery
    # task's recording of the failure.
    assert result.state == "failed"
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    assert invocation.status == RealtimeToolInvocation.Status.FAILED
    assert "boom inside celery" in invocation.error_message


def test_celery_task_handles_tool_deregistered(reset_registry):
    """Celery task runs after the tool was removed from the
    registry (race: dispatch, then registry cleared, then
    Celery picks it up)."""
    # Create the invocation manually in QUEUED state.
    ws, _u = _make_workspace("r72ce2@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    invocation = RealtimeToolInvocation.objects.create(
        session=session,
        tool_name="nonexistent_tool",
        status=RealtimeToolInvocation.Status.QUEUED,
    )
    from apps.realtime.tasks import execute_tool_invocation
    out = execute_tool_invocation(str(invocation.id))
    assert out["status"] == "failed"
    assert out["reason"] == "unknown_tool"
    invocation.refresh_from_db()
    assert invocation.status == RealtimeToolInvocation.Status.FAILED
    assert "no longer registered" in invocation.error_message


def test_celery_task_idempotent_on_terminal_invocation():
    """Already-SUCCEEDED invocation → Celery task no-ops."""
    ws, _u = _make_workspace("r72ce3@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    invocation = RealtimeToolInvocation.objects.create(
        session=session,
        tool_name="show_videos_tab",
        status=RealtimeToolInvocation.Status.SUCCEEDED,
    )
    from apps.realtime.tasks import execute_tool_invocation
    out = execute_tool_invocation(str(invocation.id))
    assert out["status"] == RealtimeToolInvocation.Status.SUCCEEDED
    assert "already terminal" in out.get("note", "")


# ---- render_video tool ------------------------------------------


def test_render_video_happy_path_creates_composition():
    """The full flow: dispatch → over-threshold → approve →
    Celery → composition created + linked to invocation
    row's produced_composition."""
    ws, user = _make_workspace("r72rv1@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    client = APIClient()
    client.force_authenticate(user=user)
    # Step 1 — dispatch. Should land awaiting_approval
    # because render_video's cost ($0.08) > threshold ($0.05).
    response = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "render_video", "args": {"script": "Pitch the spring sale."}},
        format="json",
    )
    assert response.status_code == http.HTTP_202_ACCEPTED
    invocation_id = response.json()["invocation_id"]

    # Step 2 — approve. Celery task fires (eager) and
    # marks the invocation SUCCEEDED with composition
    # linkage.
    response = client.post(
        f"/api/realtime_tool_invocations/{invocation_id}/approve/",
        {}, format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    payload = response.json()
    assert payload["state"] == "succeeded"
    invocation = RealtimeToolInvocation.objects.get(id=invocation_id)
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED
    assert invocation.produced_composition_id is not None
    composition = Composition.objects.get(pk=invocation.produced_composition_id)
    assert composition.workspace == ws
    assert composition.spokesperson == sp
    assert composition.template_kind == "talking_head"


def test_render_video_missing_script_failed():
    ws, user = _make_workspace("r72rv2@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "render_video", {}, user=user,
    )
    # Over-threshold so dispatch returns awaiting_approval
    # WITHOUT calling the executor. Approve to trigger
    # the validation.
    assert result.state == "awaiting_approval"
    from apps.realtime.dispatch import approve_invocation
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    approved = approve_invocation(invocation)
    assert approved.state == "failed"
    invocation.refresh_from_db()
    assert "script is required" in invocation.error_message


def test_render_video_unknown_recipe_failed():
    ws, user = _make_workspace("r72rv3@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "render_video",
        {"script": "test", "recipe": "no_such_recipe"},
        user=user,
    )
    # over-threshold → awaiting_approval
    from apps.realtime.dispatch import approve_invocation
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    approved = approve_invocation(invocation)
    assert approved.state == "failed"
    invocation.refresh_from_db()
    assert "unknown recipe" in invocation.error_message


def test_render_video_tier_limit_exceeded_failed():
    """Starter workspace at its monthly video cap: tool
    invocation lands FAILED with the tier-limit message."""
    from apps.videos.models import Video

    ws, user = _make_workspace("r72rv4@test")
    _set_tier(ws, "starter")  # 10 videos/month cap
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)

    # Seed 10 videos to fill the starter cap.
    for i in range(10):
        Video.objects.create(
            spokesperson=sp,
            brief=f"video {i}",
            status=Video.Status.READY,
        )

    result = dispatch_tool(
        session, "render_video", {"script": "another"}, user=user,
    )
    from apps.realtime.dispatch import approve_invocation
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    approved = approve_invocation(invocation)
    assert approved.state == "failed"
    invocation.refresh_from_db()
    # The TierLimitExceeded message references the cap.
    assert "Starter" in invocation.error_message or "tier" in invocation.error_message.lower()


def test_render_video_cost_is_over_threshold():
    """Confirms render_video is the load-bearing
    threshold-crossing tool — its cost is over $0.05 so
    dispatch must yield awaiting_approval."""
    from apps.realtime.tools import get_tool
    spec = get_tool("render_video")
    assert spec.cost_micros > 50_000
    assert spec.is_async is True


def test_render_video_with_recipe_override():
    """Operator passes a different recipe name."""
    ws, user = _make_workspace("r72rv6@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "render_video",
        {"script": "Pitch with backdrop.", "recipe": "talking_head_polished"},
        user=user,
    )
    from apps.realtime.dispatch import approve_invocation
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    approved = approve_invocation(invocation)
    assert approved.state == "succeeded"
    invocation.refresh_from_db()
    composition = Composition.objects.get(pk=invocation.produced_composition_id)
    assert composition.template_kind == "talking_head_polished"


# ---- REST integration end-to-end --------------------------------


def test_full_rest_flow_dispatch_approve_succeed():
    """End-to-end: SPA POSTs `invoke_tool` → 202 →
    operator approves via `approve` endpoint → 200 with
    composition_id."""
    ws, user = _make_workspace("r72rest@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    client = APIClient()
    client.force_authenticate(user=user)
    # Step 1
    response = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "render_video", "args": {"script": "Hello world."}},
        format="json",
    )
    assert response.status_code == http.HTTP_202_ACCEPTED
    body = response.json()
    assert body["state"] == "awaiting_approval"
    assert body["cost_micros"] == 80_000
    # Step 2
    inv_id = body["invocation_id"]
    response = client.post(
        f"/api/realtime_tool_invocations/{inv_id}/approve/",
        {}, format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    body = response.json()
    assert body["state"] == "succeeded"
    assert "composition_id" in body.get("result", {})


# ---- INVENTORY undercount fix ------------------------------------


def test_inventory_celery_task_count_includes_realtime_tasks():
    """Drift-prevention backlog item 5 — the inventory
    Celery counter previously undercounted because the
    autodiscovery hadn't fired at management-command time.
    After the fix, the count includes
    `realtime.execute_tool_invocation` +
    `realtime.fetch_transcript_for_session` plus the
    embeddings + conversations + compositions tasks."""
    from apps.accounts.management.commands.inventory import (
        _collect_celery_tasks,
    )
    result = _collect_celery_tasks()
    assert result["total"] >= 7, (
        f"expected >=7 registered tasks; got {result['total']}: "
        f"{result['tasks']}"
    )
    assert "realtime.execute_tool_invocation" in result["tasks"]
    assert "realtime.fetch_transcript_for_session" in result["tasks"]
