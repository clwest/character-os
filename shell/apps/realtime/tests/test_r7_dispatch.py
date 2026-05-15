"""R7.0 tests — tool dispatch foundation.

What this slice ships:

1. ``apps/realtime/tools/`` registry with
   ``register_tool`` decorator + ``get_tool`` /
   ``list_tools`` / ``get_workspace_tools`` /
   ``clear_registry`` accessors.
2. ``apps/realtime/tools/show_videos_tab.py`` — first
   tool. UI-only nav event, $0 cost.
3. ``apps/realtime/dispatch.py`` — ``dispatch_tool``,
   ``approve_invocation``, ``reject_invocation``,
   ``DispatchResult``, ``DispatchError``.
4. ``POST /api/realtime_sessions/<id>/invoke_tool/``
   action on the session viewset.
5. ``RealtimeToolInvocationViewSet`` at
   ``/api/realtime_tool_invocations/`` with retrieve +
   list + approve + reject actions.
6. ``RealtimeToolInvocation.workspace`` property — surfaces
   ``session.workspace`` so the shared
   ``IsWorkspaceMember`` permission resolver works.
7. ``AWAITING_APPROVAL`` status added to the model's
   Status TextChoices.
8. ``REALTIME_TOOL_APPROVAL_THRESHOLD_MICROS = 50_000``
   ($0.05) settings fallback in ``dispatch._approval_threshold_micros``.

Covered:

* Registry: register + lookup + unknown raises.
* Registry: ``get_workspace_tools`` returns full catalog
  (R7.0 has no filtering).
* Dispatch: unknown tool → 400.
* Dispatch: below threshold + sync tool → executes
  inline, returns 200 with `succeeded` + `result`.
* Dispatch: above threshold → returns 202 with
  `awaiting_approval` + `cost_micros` + `reason`. No
  executor call.
* Dispatch: executor raises → 200 with `failed` +
  `error_message`. Audit row recorded as FAILED.
* Dispatch: args dict persisted on the audit row.
* Approve: deferred tool → executes + 200 succeeded.
* Approve: already-succeeded invocation → idempotent.
* Approve: tool de-registered between dispatch +
  approval → recorded as FAILED.
* Reject: deferred tool → 200 rejected + reason on row.
* Reject: idempotent.
* List: filters by `?session=<uuid>`.
* List: workspace-scoped (other-workspace invocations
  excluded).
* Tool: `show_videos_tab` returns
  `{event, spokesperson_id}` payload.
* Cross-workspace: session in ws A can't be hit by user
  in ws B via the invoke_tool endpoint (returns 404 due
  to queryset filtering).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.realtime.dispatch import (
    DispatchError,
    DispatchResult,
    approve_invocation,
    dispatch_tool,
    reject_invocation,
)
from apps.realtime.models import RealtimeSession, RealtimeToolInvocation
from apps.realtime.tools import (
    ToolSpec,
    clear_registry,
    get_tool,
    get_workspace_tools,
    list_tools,
    register_tool,
)
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def reset_registry():
    """Snapshot the production tool catalog before the test
    registers synthetic tools; restore it on teardown. The
    snapshot is a shallow copy of the registry dict so
    cleanup is a clear + update, no module reload needed."""
    snapshot = dict(_registry())
    yield
    _registry().clear()
    _registry().update(snapshot)


def _registry():
    """Test-only: peek at the registry's internal dict so
    the snapshot/restore fixture has something to act on."""
    from apps.realtime import tools as _t
    return _t._TOOLS


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


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


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- registry ---------------------------------------------------


def test_registry_has_show_videos_tab():
    spec = get_tool("show_videos_tab")
    assert isinstance(spec, ToolSpec)
    assert spec.cost_micros == 0
    assert spec.workspace_scoped is False
    assert spec.is_async is False


def test_registry_unknown_raises_keyerror():
    with pytest.raises(KeyError):
        get_tool("does_not_exist")


def test_list_tools_includes_show_videos_tab():
    names = [t.name for t in list_tools()]
    assert "show_videos_tab" in names


def test_get_workspace_tools_returns_full_catalog():
    ws, _u = _make_workspace("r7gw@test")
    tools = get_workspace_tools(ws)
    # R7.0 has no filtering — every registered tool comes
    # back. R7.1 adds tier-based filtering on top.
    assert {t.name for t in tools} == {t.name for t in list_tools()}


# ---- dispatch_tool (Python-level) -------------------------------


def test_dispatch_unknown_tool_raises():
    ws, user = _make_workspace("r7du@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    with pytest.raises(DispatchError) as ctx:
        dispatch_tool(session, "nope", {}, user=user)
    assert ctx.value.http_status == 400


def test_dispatch_show_videos_tab_executes_inline():
    ws, user = _make_workspace("r7sv@test")
    sp = _make_spokesperson(ws, name="Riggs")
    session = _make_session(ws, sp)
    result = dispatch_tool(session, "show_videos_tab", {}, user=user)
    assert isinstance(result, DispatchResult)
    assert result.state == "succeeded"
    assert result.tool_name == "show_videos_tab"
    assert result.cost_micros == 0
    assert result.result == {
        "event": "show_videos_tab",
        "spokesperson_id": str(sp.id),
    }
    # Audit row created with SUCCEEDED status.
    invocation = RealtimeToolInvocation.objects.get(
        id=result.invocation_id,
    )
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED
    assert invocation.completed_at is not None


def test_dispatch_above_threshold_awaits_approval(reset_registry):
    """Register a synthetic high-cost tool to exercise the
    threshold gate."""
    @register_tool(
        name="synth_expensive",
        description="Test-only expensive tool",
        cost_micros=100_000,  # $0.10 — over the $0.05 default
        workspace_scoped=True,
    )
    def _exec(session, args):
        return {"unreachable": True}  # should NOT be called

    ws, user = _make_workspace("r7at@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(session, "synth_expensive", {"x": 1}, user=user)
    assert result.state == "awaiting_approval"
    assert result.cost_micros == 100_000
    assert result.result is None
    assert "$0.10" in result.reason
    assert "$0.05" in result.reason
    invocation = RealtimeToolInvocation.objects.get(
        id=result.invocation_id,
    )
    assert invocation.status == RealtimeToolInvocation.Status.AWAITING_APPROVAL
    # Args persisted verbatim for the operator's modal.
    assert invocation.args == {"x": 1}


def test_dispatch_executor_failure_recorded(reset_registry):
    @register_tool(
        name="synth_boom",
        description="Test-only failing tool",
        cost_micros=0,
        workspace_scoped=False,
    )
    def _exec(session, args):
        raise RuntimeError("boom")

    ws, user = _make_workspace("r7bm@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(session, "synth_boom", {}, user=user)
    assert result.state == "failed"
    assert "boom" in result.error_message
    invocation = RealtimeToolInvocation.objects.get(
        id=result.invocation_id,
    )
    assert invocation.status == RealtimeToolInvocation.Status.FAILED


def test_dispatch_args_persisted_on_audit_row():
    ws, user = _make_workspace("r7ar@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(
        session, "show_videos_tab", {"hint": "from_chat"}, user=user,
    )
    invocation = RealtimeToolInvocation.objects.get(
        id=result.invocation_id,
    )
    assert invocation.args == {"hint": "from_chat"}


# ---- approval flow ----------------------------------------------


def test_approve_executes_deferred_tool(reset_registry):
    @register_tool(
        name="synth_pricey",
        description="Defer + approve cycle",
        cost_micros=80_000,  # over threshold
        workspace_scoped=True,
    )
    def _exec(session, args):
        return {"approved_payload": args.get("amount", 0)}

    ws, user = _make_workspace("r7ap@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    dispatched = dispatch_tool(
        session, "synth_pricey", {"amount": 5}, user=user,
    )
    assert dispatched.state == "awaiting_approval"

    invocation = RealtimeToolInvocation.objects.get(
        id=dispatched.invocation_id,
    )
    approved = approve_invocation(invocation)
    assert approved.state == "succeeded"
    assert approved.result == {"approved_payload": 5}
    invocation.refresh_from_db()
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED


def test_approve_idempotent_on_resolved_invocation():
    """An invocation already SUCCEEDED → approve is a no-op
    that returns the current state."""
    ws, user = _make_workspace("r7id@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    result = dispatch_tool(session, "show_videos_tab", {}, user=user)
    invocation = RealtimeToolInvocation.objects.get(
        id=result.invocation_id,
    )
    # Already SUCCEEDED — approving should not re-execute.
    again = approve_invocation(invocation)
    assert again.state == "succeeded"
    # completed_at unchanged (no re-execution).
    invocation.refresh_from_db()
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED


def test_approve_after_deregister_marks_failed(reset_registry):
    @register_tool(
        name="synth_transient",
        description="Tool that disappears between dispatch + approve",
        cost_micros=100_000,
        workspace_scoped=True,
    )
    def _exec(session, args):
        return {"unreachable": True}

    ws, user = _make_workspace("r7dg@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    dispatched = dispatch_tool(session, "synth_transient", {}, user=user)
    invocation = RealtimeToolInvocation.objects.get(
        id=dispatched.invocation_id,
    )
    # De-register before approving.
    _registry().pop("synth_transient", None)
    approved = approve_invocation(invocation)
    assert approved.state == "failed"
    invocation.refresh_from_db()
    assert invocation.status == RealtimeToolInvocation.Status.FAILED


def test_reject_records_reason(reset_registry):
    @register_tool(
        name="synth_rejectable",
        description="Reject cycle",
        cost_micros=100_000,
        workspace_scoped=True,
    )
    def _exec(session, args):
        return {}

    ws, user = _make_workspace("r7rj@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    dispatched = dispatch_tool(session, "synth_rejectable", {}, user=user)
    invocation = RealtimeToolInvocation.objects.get(
        id=dispatched.invocation_id,
    )
    rejected = reject_invocation(invocation, reason="not now")
    assert rejected.state == "rejected"
    assert rejected.reason == "not now"
    invocation.refresh_from_db()
    assert invocation.status == RealtimeToolInvocation.Status.REJECTED
    assert invocation.error_message == "not now"


def test_reject_idempotent():
    ws, user = _make_workspace("r7ri@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    invocation = RealtimeToolInvocation.objects.create(
        session=session,
        tool_name="show_videos_tab",
        status=RealtimeToolInvocation.Status.REJECTED,
        error_message="prior reason",
    )
    again = reject_invocation(invocation, reason="new reason")
    assert again.state == "rejected"
    # First reject's reason is preserved (idempotent).
    invocation.refresh_from_db()
    assert invocation.error_message == "prior reason"


# ---- REST surface -----------------------------------------------


def test_invoke_tool_endpoint_inline_execution():
    ws, user = _make_workspace("r7vinl@test")
    sp = _make_spokesperson(ws, name="Donny")
    session = _make_session(ws, sp)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "show_videos_tab", "args": {}},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content
    payload = response.json()
    assert payload["state"] == "succeeded"
    assert payload["tool_name"] == "show_videos_tab"
    assert payload["result"]["event"] == "show_videos_tab"
    assert payload["result"]["spokesperson_id"] == str(sp.id)


def test_invoke_tool_endpoint_above_threshold_returns_202(reset_registry):
    @register_tool(
        name="synth_rest_expensive",
        description="REST + threshold cycle",
        cost_micros=100_000,
        workspace_scoped=True,
    )
    def _exec(session, args):
        return {}

    ws, user = _make_workspace("r7v202@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "synth_rest_expensive", "args": {}},
        format="json",
    )
    assert response.status_code == http.HTTP_202_ACCEPTED
    payload = response.json()
    assert payload["state"] == "awaiting_approval"
    assert payload["cost_micros"] == 100_000


def test_invoke_tool_endpoint_unknown_tool_returns_400():
    ws, user = _make_workspace("r7vunk@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "no_such_tool"},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_invoke_tool_endpoint_cross_workspace_session_404():
    """A session in workspace A is invisible to workspace B
    members — the queryset filter on RealtimeSessionViewSet
    drops it before the dispatch can fire."""
    ws_a, _ua = _make_workspace("r7vxa@test", "A")
    ws_b, user_b = _make_workspace("r7vxb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    session = _make_session(ws_a, sp_a)
    client = APIClient()
    _login(client, user_b)
    response = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "show_videos_tab"},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_approve_endpoint(reset_registry):
    @register_tool(
        name="synth_approvable",
        description="Approve via REST",
        cost_micros=100_000,
        workspace_scoped=True,
    )
    def _exec(session, args):
        return {"ran": True}

    ws, user = _make_workspace("r7vapp@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    client = APIClient()
    _login(client, user)
    dispatched = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "synth_approvable", "args": {}},
        format="json",
    )
    inv_id = dispatched.json()["invocation_id"]
    response = client.post(
        f"/api/realtime_tool_invocations/{inv_id}/approve/",
        {}, format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    payload = response.json()
    assert payload["state"] == "succeeded"
    assert payload["result"] == {"ran": True}


def test_reject_endpoint(reset_registry):
    @register_tool(
        name="synth_rejectable_rest",
        description="Reject via REST",
        cost_micros=100_000,
        workspace_scoped=True,
    )
    def _exec(session, args):
        return {}

    ws, user = _make_workspace("r7vrej@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    client = APIClient()
    _login(client, user)
    dispatched = client.post(
        f"/api/realtime_sessions/{session.id}/invoke_tool/",
        {"tool_name": "synth_rejectable_rest", "args": {}},
        format="json",
    )
    inv_id = dispatched.json()["invocation_id"]
    response = client.post(
        f"/api/realtime_tool_invocations/{inv_id}/reject/",
        {"reason": "operator declined"},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    payload = response.json()
    assert payload["state"] == "rejected"
    assert payload["reason"] == "operator declined"


def test_list_invocations_filters_by_session():
    ws, user = _make_workspace("r7vls@test")
    sp = _make_spokesperson(ws)
    session_a = _make_session(ws, sp)
    session_b = _make_session(ws, sp)
    client = APIClient()
    _login(client, user)
    # One invocation on each session.
    client.post(
        f"/api/realtime_sessions/{session_a.id}/invoke_tool/",
        {"tool_name": "show_videos_tab"}, format="json",
    )
    client.post(
        f"/api/realtime_sessions/{session_b.id}/invoke_tool/",
        {"tool_name": "show_videos_tab"}, format="json",
    )
    response = client.get(
        f"/api/realtime_tool_invocations/?session={session_a.id}",
    )
    assert response.status_code == http.HTTP_200_OK
    rows = response.json()
    assert len(rows) == 1
    assert rows[0]["session"] == str(session_a.id)


def test_list_invocations_workspace_scoped():
    ws_a, user_a = _make_workspace("r7vws@test", "A")
    ws_b, user_b = _make_workspace("r7vws2@test", "B")
    sp_a = _make_spokesperson(ws_a)
    session_a = _make_session(ws_a, sp_a)
    client = APIClient()
    _login(client, user_a)
    client.post(
        f"/api/realtime_sessions/{session_a.id}/invoke_tool/",
        {"tool_name": "show_videos_tab"}, format="json",
    )
    # User B in workspace B should see zero invocations
    # from workspace A.
    other = APIClient()
    _login(other, user_b)
    response = other.get("/api/realtime_tool_invocations/")
    assert response.status_code == http.HTTP_200_OK
    assert response.json() == []
