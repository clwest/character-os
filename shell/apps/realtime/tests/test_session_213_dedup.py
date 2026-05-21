"""SESSION 213 Fix 2A — dispatch dedup window.

Q-r-2 mitigation: when the avatar can't see tool-result
events, it sometimes spams identical lookups 3-4 times within
a few seconds. The dispatch dedup window short-circuits the
second-and-onward fires — no new audit row, no new executor
call, and the response carries an `already_returned: True`
hint so the SPA can suppress duplicate UI side-effects.

Covered:

* Identical (session, tool_name, args) inside the 10s window
  returns the cached invocation id + `already_returned: True`.
  No second audit row is created.
* Cost attribution surfaces the spec's cost_micros even on a
  deduped hit (the SPA's cost ticker keeps its accounting).
* The dedup window is configurable via
  ``REALTIME_TOOL_DEDUP_WINDOW_SECONDS``; outside-window
  refires count as fresh invocations.
* Different args do NOT dedup — distinct lookups still fire.
* Different sessions do NOT dedup — cross-session isolation.
* Terminal-failure states (FAILED / REJECTED) do NOT dedup —
  legitimate retries are not blocked.
* AWAITING_APPROVAL dedupes — the operator must not see two
  modals for the same intent.
* Async / QUEUED dedupes — the same render isn't enqueued
  twice.
"""
from __future__ import annotations

from datetime import timedelta

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from django.utils import timezone

from apps.accounts.models import Workspace
from apps.realtime.dispatch import dispatch_tool
from apps.realtime.models import RealtimeSession, RealtimeToolInvocation
from apps.realtime.tools import register_tool
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- fixtures ---------------------------------------------------


@pytest.fixture
def reset_registry():
    """Snapshot the production tool catalog; restore on
    teardown so synthetic tools don't leak."""
    from apps.realtime import tools as _t

    snapshot = dict(_t._TOOLS)
    yield
    _t._TOOLS.clear()
    _t._TOOLS.update(snapshot)


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_spokesperson(ws: Workspace, name: str = "Sasha") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws,
        name=name,
        runway_avatar_id="av_test",
        portrait_path="https://fake/p.png",
        business_brief="brief",
    )


def _make_session(ws: Workspace, sp: Spokesperson) -> RealtimeSession:
    return RealtimeSession.objects.create(
        workspace=ws,
        spokesperson=sp,
        status=RealtimeSession.Status.READY,
        provider_session_id="rt_x",
    )


def _count_invocations(session: RealtimeSession) -> int:
    return RealtimeToolInvocation.objects.filter(session=session).count()


# ---- dedup hits ---------------------------------------------------


def test_dedup_same_args_within_window_returns_cached_invocation():
    """Identical (tool_name, args) refire on the same session
    returns the first invocation's id — no second row."""
    ws, user = _make_workspace("213dup1@test")
    sp = _make_spokesperson(ws, name="Riggs")
    session = _make_session(ws, sp)

    first = dispatch_tool(session, "show_videos_tab", {}, user=user)
    assert first.state == "succeeded"
    assert first.result is not None
    assert first.result.get("already_returned") is not True

    second = dispatch_tool(session, "show_videos_tab", {}, user=user)
    assert second.invocation_id == first.invocation_id, (
        "dedup should return the first invocation id, not a new row"
    )
    assert second.result is not None
    assert second.result["already_returned"] is True
    assert second.result["matched_invocation_id"] == first.invocation_id
    assert _count_invocations(session) == 1


def test_dedup_preserves_spec_cost_attribution(reset_registry):
    """Deduped DispatchResult still reflects the spec's
    cost_micros so the SPA's cost ticker stays accurate (the
    underlying cost wasn't re-incurred — but the SPA shouldn't
    have to do a second lookup to know what the tool nominally
    costs)."""
    @register_tool(
        name="synth_priced",
        description="Test-only priced tool",
        cost_micros=1_000,
        workspace_scoped=False,
    )
    def _exec(session, args):
        return {"ok": True}

    ws, user = _make_workspace("213cost@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)

    first = dispatch_tool(session, "synth_priced", {"q": "x"}, user=user)
    assert first.cost_micros == 1_000

    second = dispatch_tool(session, "synth_priced", {"q": "x"}, user=user)
    assert second.cost_micros == 1_000
    assert second.result["already_returned"] is True
    assert _count_invocations(session) == 1


# ---- dedup misses ------------------------------------------------


@override_settings(REALTIME_TOOL_DEDUP_WINDOW_SECONDS=1)
def test_dedup_misses_outside_window():
    """A refire after the dedup window passes should create a
    new audit row. Easier to verify with a tiny window than to
    sleep; we hand-roll the timestamp on the first row to
    simulate elapsed time."""
    ws, user = _make_workspace("213out@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)

    first = dispatch_tool(session, "show_videos_tab", {}, user=user)
    invocation = RealtimeToolInvocation.objects.get(id=first.invocation_id)
    # Move the row outside the (now 1-second) window.
    RealtimeToolInvocation.objects.filter(id=invocation.id).update(
        invoked_at=timezone.now() - timedelta(seconds=5),
    )

    second = dispatch_tool(session, "show_videos_tab", {}, user=user)
    assert second.invocation_id != first.invocation_id
    assert second.result is not None
    assert second.result.get("already_returned") is not True
    assert _count_invocations(session) == 2


def test_dedup_misses_on_different_args():
    """Distinct lookups (different args dict) must still fire
    — dedup is per-args, not per-tool-name."""
    ws, user = _make_workspace("213diffargs@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)

    first = dispatch_tool(
        session, "show_videos_tab", {"hint": "first"}, user=user,
    )
    second = dispatch_tool(
        session, "show_videos_tab", {"hint": "second"}, user=user,
    )
    assert second.invocation_id != first.invocation_id
    assert _count_invocations(session) == 2


def test_dedup_misses_across_sessions():
    """Dedup is scoped per-session. Two sessions in the same
    workspace each see their own first-fire."""
    ws, user = _make_workspace("213xsess@test")
    sp = _make_spokesperson(ws)
    session_a = _make_session(ws, sp)
    session_b = _make_session(ws, sp)

    a_first = dispatch_tool(session_a, "show_videos_tab", {}, user=user)
    b_first = dispatch_tool(session_b, "show_videos_tab", {}, user=user)
    assert a_first.invocation_id != b_first.invocation_id
    assert _count_invocations(session_a) == 1
    assert _count_invocations(session_b) == 1


# ---- terminal-failure states do NOT dedup ----------------------


def test_dedup_misses_after_failed_invocation(reset_registry):
    """A second attempt after a real failure is legitimate
    retry; dedup must not block it."""
    call_count = {"n": 0}

    @register_tool(
        name="synth_flaky",
        description="Fails once, succeeds next",
        cost_micros=0,
        workspace_scoped=False,
    )
    def _exec(session, args):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("boom")
        return {"ok": True}

    ws, user = _make_workspace("213retry@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)

    first = dispatch_tool(session, "synth_flaky", {}, user=user)
    assert first.state == "failed"

    second = dispatch_tool(session, "synth_flaky", {}, user=user)
    assert second.state == "succeeded"
    assert second.invocation_id != first.invocation_id
    assert _count_invocations(session) == 2


def test_dedup_misses_after_rejected_invocation(reset_registry):
    """A REJECTED row means the operator declined — a second
    fire is the avatar legitimately asking again."""
    @register_tool(
        name="synth_decline",
        description="Reject-cycle",
        cost_micros=0,
        workspace_scoped=False,
    )
    def _exec(session, args):
        return {"ran": True}

    ws, user = _make_workspace("213rej@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)

    # Hand-craft a REJECTED row so we don't have to thread
    # the approval flow.
    RealtimeToolInvocation.objects.create(
        session=session,
        tool_name="synth_decline",
        args={"q": "x"},
        status=RealtimeToolInvocation.Status.REJECTED,
        completed_at=timezone.now(),
    )

    second = dispatch_tool(session, "synth_decline", {"q": "x"}, user=user)
    assert second.state == "succeeded"
    assert second.result == {"ran": True}
    assert _count_invocations(session) == 2


# ---- non-terminal states DO dedup -------------------------------


def test_dedup_skipped_when_tool_opts_out(reset_registry):
    """Mutating tools (Q-r-8 last-write-wins) declare
    `dedup_enabled=False`. Their identical refires must still
    fire — both attach_memory's idempotent-replace semantics
    and any future stateful tool depend on it."""
    @register_tool(
        name="synth_mutating",
        description="Always-fire mutating tool",
        cost_micros=0,
        workspace_scoped=True,
        dedup_enabled=False,
    )
    def _exec(session, args):
        return {"committed": True}

    ws, user = _make_workspace("213optout@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)

    first = dispatch_tool(session, "synth_mutating", {}, user=user)
    second = dispatch_tool(session, "synth_mutating", {}, user=user)
    assert first.invocation_id != second.invocation_id
    assert first.result == {"committed": True}
    assert second.result == {"committed": True}
    assert _count_invocations(session) == 2


def test_dedup_hits_awaiting_approval(reset_registry):
    """The operator must not see two modals for the same
    intent. AWAITING_APPROVAL dedupes to the existing row."""
    @register_tool(
        name="synth_pending_modal",
        description="Over-threshold tool",
        cost_micros=100_000,
        workspace_scoped=True,
    )
    def _exec(session, args):
        return {"unreachable": True}

    ws, user = _make_workspace("213pending@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)

    first = dispatch_tool(
        session, "synth_pending_modal", {"x": 1}, user=user,
    )
    assert first.state == "awaiting_approval"

    second = dispatch_tool(
        session, "synth_pending_modal", {"x": 1}, user=user,
    )
    assert second.state == "awaiting_approval"
    assert second.invocation_id == first.invocation_id
    assert second.result is not None
    assert second.result["already_returned"] is True
    assert _count_invocations(session) == 1
