"""R7.3 tests — attach_memory tool + R6.1 memory-loop closure.

What this slice ships:

1. **R6.1** — `compose_session_memory` no longer filters
   by `status=ENDED`. Any session with a
   `transcript_asset` surfaces, regardless of status. The
   widen is what makes mid-session memory commits visible
   to the next session's R6 projection.

2. **`apps.realtime.tasks.capture_transcript`** — helper
   extracted from R5's Celery task body so both R5
   (session-end) and R7.3 (mid-session) share one
   implementation. R7.3 calls it synchronously; R5
   wraps it in a Celery task with retry logic.

3. **`attach_memory` async tool** — Pro tier, ~$0.001.
   Fires `capture_transcript(session)`, returns
   `{event, asset_id, session_id, status, message}`.
   The generic Celery wrapper picks up `asset_id` and
   links it to the invocation row's `produced_asset`.

The v1 tool catalog is now complete: 6 tools.

Covered (12 tests):

* `attach_memory` happy path → audit row succeeded + asset
  created on session + produced_asset linked.
* `attach_memory` idempotent — running twice replaces the
  prior Asset.
* `attach_memory` empty upstream → status `empty`, no
  asset.
* `attach_memory` upstream error → status `upstream_error`,
  no asset, invocation SUCCEEDED (the FAILED state is
  reserved for executor exceptions, not structured
  failure payloads).
* `attach_memory` on session without provider_session_id
  → status `empty`.
* `attach_memory` is over the approval threshold check:
  $0.001 < $0.05 → executes inline (no AWAITING_APPROVAL).
* `attach_memory` is Pro-tier — Starter workspace blocked.
* End-to-end memory loop: attach_memory on READY session
  → R6 picks it up at the next session-create (mocked).
* `capture_transcript` helper — three direct unit tests
  (success / empty / upstream error) verifying it works
  on non-ENDED sessions.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.billing.models import Subscription
from apps.compositions.models import Asset, AssetType
from apps.realtime.dispatch import dispatch_tool
from apps.realtime.models import RealtimeSession, RealtimeToolInvocation
from apps.realtime.tasks import capture_transcript
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineError,
    RealtimeTranscriptResult,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _settings():
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
        EMBEDDING_FORCE_MOCK=True,
    ):
        yield


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


def _make_session(
    ws: Workspace, sp: Spokesperson,
    *,
    status: str = RealtimeSession.Status.READY,
    provider_session_id: str = "rt_live",
) -> RealtimeSession:
    return RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=status,
        provider_session_id=provider_session_id,
    )


def _patch_capture(
    *, text: str = "Operator: hi. Sasha: hi back.",
    segments: list | None = None,
    mock_mode: bool = True,
    session_id: str = "rt_live",
):
    """Patch MediaEngineClient.realtime_session_fetch_transcript
    so capture_transcript runs without a live media-engine."""
    fake = MagicMock()
    fake.realtime_session_fetch_transcript.return_value = RealtimeTranscriptResult(
        session_id=session_id,
        text=text,
        segments=segments or [
            {"speaker": "operator", "text": "hi", "t": 0},
            {"speaker": "sasha", "text": "hi back", "t": 1},
        ],
        mock_mode=mock_mode,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return patch(
        "apps.realtime.tasks.MediaEngineClient", return_value=cm,
    ), fake


# ---- capture_transcript helper -----------------------------------


def test_capture_transcript_persisted_on_ready_session():
    """The helper works on READY (not just ENDED) sessions —
    that's the load-bearing change for R7.3's mid-session
    use case."""
    ws, _u = _make_workspace("r73c1@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp, status=RealtimeSession.Status.READY)
    patcher, _ = _patch_capture(text="Mid-session content.")
    with patcher:
        result = capture_transcript(session)
    assert result["status"] == "persisted"
    assert result["asset_id"]
    assert result["chars"] > 0
    session.refresh_from_db()
    assert session.transcript_asset_id is not None
    assert session.transcript_asset.inline_content == "Mid-session content."
    # Status didn't flip — still READY.
    assert session.status == RealtimeSession.Status.READY


def test_capture_transcript_empty_upstream_no_asset():
    ws, _u = _make_workspace("r73c2@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    patcher, _ = _patch_capture(text="   ")  # whitespace only
    with patcher:
        result = capture_transcript(session)
    assert result["status"] == "empty"
    assert result["asset_id"] is None
    session.refresh_from_db()
    assert session.transcript_asset_id is None


def test_capture_transcript_upstream_error_no_asset():
    ws, _u = _make_workspace("r73c3@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    fake = MagicMock()
    fake.realtime_session_fetch_transcript.side_effect = MediaEngineError("boom")
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.tasks.MediaEngineClient", return_value=cm):
        result = capture_transcript(session)
    assert result["status"] == "upstream_error"
    assert result["asset_id"] is None


# ---- attach_memory tool ------------------------------------------


def test_attach_memory_happy_path_links_produced_asset():
    """End-to-end: dispatch → Celery (eager) → executor
    calls capture_transcript → Asset persisted + linked
    to invocation row's produced_asset."""
    ws, user = _make_workspace("r73h1@test")
    _set_tier(ws, "pro")  # attach_memory is pro-only
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    patcher, _ = _patch_capture(text="Lots of operator text.")
    with patcher:
        result = dispatch_tool(
            session, "attach_memory", {}, user=user,
        )
    # Eager mode → final state is SUCCEEDED.
    assert result.state == "succeeded"
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED
    assert invocation.produced_asset_id is not None
    asset = Asset.objects.get(pk=invocation.produced_asset_id)
    assert asset.asset_type == AssetType.TRANSCRIPT
    assert asset.workspace == ws
    assert asset.inline_content == "Lots of operator text."
    # Session also got the transcript_asset set.
    session.refresh_from_db()
    assert session.transcript_asset_id == asset.id


def test_attach_memory_idempotent_replaces_stale_asset():
    """Running attach_memory twice replaces the prior
    Asset (last-write-wins, resolves Q-r-8)."""
    ws, user = _make_workspace("r73h2@test")
    _set_tier(ws, "pro")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    # First commit.
    patcher1, _ = _patch_capture(text="First snapshot.")
    with patcher1:
        first = dispatch_tool(session, "attach_memory", {}, user=user)
    first_invocation = RealtimeToolInvocation.objects.get(
        id=first.invocation_id,
    )
    first_asset_id = first_invocation.produced_asset_id
    # Second commit.
    patcher2, _ = _patch_capture(text="Second snapshot, longer.")
    with patcher2:
        second = dispatch_tool(session, "attach_memory", {}, user=user)
    second_invocation = RealtimeToolInvocation.objects.get(
        id=second.invocation_id,
    )
    second_asset_id = second_invocation.produced_asset_id
    assert first_asset_id != second_asset_id
    # Old asset deleted.
    assert not Asset.objects.filter(pk=first_asset_id).exists()
    # New asset has the fresh content.
    new = Asset.objects.get(pk=second_asset_id)
    assert "Second snapshot" in new.inline_content
    # Session now points at the fresh asset.
    session.refresh_from_db()
    assert session.transcript_asset_id == second_asset_id


def test_attach_memory_empty_upstream_succeeded_no_asset():
    """Empty transcript: invocation row is SUCCEEDED (the
    tool ran cleanly; the upstream just didn't have
    content yet) but result.status='empty' + no
    produced_asset linkage."""
    ws, user = _make_workspace("r73h3@test")
    _set_tier(ws, "pro")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    patcher, _ = _patch_capture(text="")
    with patcher:
        result = dispatch_tool(session, "attach_memory", {}, user=user)
    assert result.state == "succeeded"
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED
    assert invocation.produced_asset_id is None


def test_attach_memory_upstream_error_succeeded_no_asset():
    """Upstream MediaEngineError: invocation row stays
    SUCCEEDED (structured failure surfaces in the result
    payload, not as a FAILED row). The SPA can render the
    `upstream_error` status code."""
    ws, user = _make_workspace("r73h4@test")
    _set_tier(ws, "pro")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    fake = MagicMock()
    fake.realtime_session_fetch_transcript.side_effect = MediaEngineError("upstream boom")
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.tasks.MediaEngineClient", return_value=cm):
        result = dispatch_tool(session, "attach_memory", {}, user=user)
    assert result.state == "succeeded"
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED
    assert invocation.produced_asset_id is None


def test_attach_memory_session_without_provider_id_empty():
    """A session that never reached CREATING (no
    provider_session_id) → capture short-circuits with
    status=empty."""
    ws, user = _make_workspace("r73h5@test")
    _set_tier(ws, "pro")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp, provider_session_id="")
    result = dispatch_tool(session, "attach_memory", {}, user=user)
    assert result.state == "succeeded"
    invocation = RealtimeToolInvocation.objects.get(id=result.invocation_id)
    assert invocation.produced_asset_id is None


def test_attach_memory_starter_tier_blocked_with_403():
    """Pro-only tool — Starter workspace gets a 403 via the
    dispatcher's tier defense-in-depth check."""
    from apps.realtime.dispatch import DispatchError
    ws, user = _make_workspace("r73h6@test")
    _set_tier(ws, "starter")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    with pytest.raises(DispatchError) as ctx:
        dispatch_tool(session, "attach_memory", {}, user=user)
    assert ctx.value.http_status == 403


def test_attach_memory_cost_below_threshold():
    """Sanity: attach_memory is under the approval
    threshold so it executes inline (no
    AWAITING_APPROVAL flow)."""
    from apps.realtime.tools import get_tool
    spec = get_tool("attach_memory")
    assert spec.cost_micros < 50_000
    assert spec.is_async is True
    assert spec.tier_required == "pro"


# ---- R6.1 memory loop end-to-end ---------------------------------


def test_memory_loop_attach_memory_surfaces_in_next_session_r6():
    """The full point of R7.3 + R6.1: after attach_memory
    commits a transcript on a READY session, the next
    session's R6 memory projection sees it.

    Mocked: the R6 LLM call is force-mocked so the
    deterministic memory body references the session id.
    """
    from character_os.realtime_memory import compose_session_memory

    ws, user = _make_workspace("r73loop@test")
    _set_tier(ws, "pro")
    sp = _make_spokesperson(ws)
    # First session is READY (still live). attach_memory
    # commits a snapshot.
    live = _make_session(ws, sp)
    patcher, _ = _patch_capture(
        text="Discussed Q4 launch plan + early-bird pricing.",
    )
    with patcher:
        dispatch_tool(live, "attach_memory", {}, user=user)
    # Now simulate: operator opens a new session. R6
    # composes memory based on prior sessions for this
    # spokesperson.
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        memory = compose_session_memory(sp)
    # The READY session's transcript IS included
    # (this is R6.1's load-bearing change).
    assert len(memory.session_ids) == 1
    assert str(live.id) in memory.session_ids
    # Mock body references the count.
    assert "1 prior session" in memory.body


def test_memory_loop_does_not_include_session_without_transcript():
    """The widened R6 filter is still gated on
    transcript_asset__isnull=False. A session that
    never committed memory + never ended doesn't
    surface."""
    from character_os.realtime_memory import compose_session_memory
    ws, _u = _make_workspace("r73nope@test")
    sp = _make_spokesperson(ws)
    _make_session(ws, sp)  # READY, no transcript_asset
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        memory = compose_session_memory(sp)
    assert memory.session_ids == []


# ---- REST integration --------------------------------------------


def test_invoke_attach_memory_via_rest():
    """End-to-end through the dispatcher endpoint, with the
    media-engine mocked."""
    ws, user = _make_workspace("r73rest@test")
    _set_tier(ws, "pro")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    client = APIClient()
    client.force_authenticate(user=user)
    patcher, _ = _patch_capture(text="A bit of conversation.")
    with patcher:
        response = client.post(
            f"/api/realtime_sessions/{session.id}/invoke_tool/",
            {"tool_name": "attach_memory", "args": {}},
            format="json",
        )
    assert response.status_code == http.HTTP_200_OK, response.content
    payload = response.json()
    assert payload["state"] == "succeeded"
    # The generic Celery wrapper snapshotted asset_id into
    # the dispatch result via _maybe_result.
    assert "asset_id" in payload.get("result", {})
