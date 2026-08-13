"""R3 tests — Django broker for the realtime arc.

Workspace auth + tier-limit gate + session state machine.

Covered:

* Auth gate (401/403 unauthenticated).
* Cross-workspace caller → 400/404.
* Teammate without `runway_avatar_id` rejected (400).
* Happy path POST create — calls media-engine, persists
  session_id + session_key + expires_at, flips status.
* CREATE response INCLUDES session_key (the SPA needs it
  for the SDK).
* RETRIEVE response EXCLUDES session_key (contract rule 9).
* Tier-limit gate fires when monthly cap reached → 402.
* Retrieve polls upstream when status is CREATING /
  NOT_READY, leaves cached for terminal states.
* DELETE / end calls upstream + marks ENDED with
  duration_seconds.
* Upstream end failure still marks ENDED locally.
* Teammate filter on list view.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Membership, Workspace
from apps.billing.models import Subscription
from apps.realtime.models import RealtimeSession
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import (
    MediaEngineError,
    RealtimeSessionPollResult,
    RealtimeSessionResult,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mocks():
    with override_settings(
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_teammate(
    ws: Workspace,
    *,
    name: str = "Sasha",
    avatar_id: str = "av_test",
) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name, runway_avatar_id=avatar_id,
        portrait_path="https://fake/p.png",
        business_brief="Sells artisan bicycle bells.",
    )


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _mock_create_result() -> RealtimeSessionResult:
    return RealtimeSessionResult(
        session_id="rt_session_abc",
        session_key="eyJ.opaque.jwt.sdk.token",
        status="ready",
        expires_at=(
            datetime.now(tz=timezone.utc) + timedelta(seconds=600)
        ).isoformat(),
        avatar_id="av_test",
        mock_mode=True,
    )


def _patch_create(result: RealtimeSessionResult | None = None):
    """Patch the broker's MediaEngineClient usage so we
    don't hit a real media-engine. Returns the patcher
    context manager.

    R4 — broker also calls `realtime_document_create` before
    `realtime_session_create`; both must be stubbed."""
    from character_os.clients.media_engine import RealtimeDocumentResult

    fake_client = MagicMock()
    fake_client.realtime_document_create.return_value = RealtimeDocumentResult(
        document_id="doc_test", mock_mode=True,
    )
    fake_client.realtime_session_create.return_value = result or _mock_create_result()
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False
    return patch(
        "apps.realtime.views.MediaEngineClient",
        return_value=cm,
    ), fake_client


# ---- auth + workspace scoping -----------------------------------


def test_create_requires_auth() -> None:
    client = APIClient()
    response = client.post("/api/realtime_sessions/", {}, format="json")
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }


def test_create_rejects_cross_workspace_spokesperson() -> None:
    ws_a, _u_a = _make_workspace("r3xa@test", "A")
    _ws_b, user_b = _make_workspace("r3xb@test", "B")
    sp_a = _make_teammate(ws_a)
    client = APIClient()
    _login(client, user_b)
    patcher, _ = _patch_create()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp_a.id)},
            format="json",
        )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_rejects_spokesperson_without_avatar() -> None:
    ws, user = _make_workspace("r3noav@test")
    sp = Teammate.objects.create(
        workspace=ws, name="NoAvatar", runway_avatar_id="",
        portrait_path="", business_brief="b",
    )
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/realtime_sessions/",
        {"spokesperson": str(sp.id)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()["spokesperson"]
    # DRF wraps single-string field errors as either a bare
    # string or a list[str] depending on how raised; tolerate
    # both.
    msg = body[0] if isinstance(body, list) else body
    assert "avatar" in msg.lower()


def test_create_rejects_unknown_spokesperson() -> None:
    _ws, user = _make_workspace("r3unk@test")
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/realtime_sessions/",
        {"spokesperson": "11111111-1111-1111-1111-111111111111"},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


# ---- create happy path ------------------------------------------


def test_create_returns_session_with_key() -> None:
    """CREATE response includes provider_session_key so the
    SPA can connect to the SDK."""
    ws, user = _make_workspace("r3happy@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)
    patcher, fake = _patch_create()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "personality": "warm", "real_mode": True},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["provider_session_id"] == "rt_session_abc"
    assert data["provider_session_key"] == "eyJ.opaque.jwt.sdk.token"
    assert data["status"] == "ready"
    assert data["mock_mode"] is True
    fake.realtime_session_create.assert_called_once()
    kwargs = fake.realtime_session_create.call_args.kwargs
    assert kwargs["avatar_id"] == "av_test"
    assert kwargs["personality"] == "warm"


def test_create_persists_session_state_machine() -> None:
    ws, user = _make_workspace("r3state@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)
    patcher, _ = _patch_create()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    session_id = response.json()["id"]
    session = RealtimeSession.objects.get(id=session_id)
    assert session.provider_session_id == "rt_session_abc"
    assert session.provider_session_key == "eyJ.opaque.jwt.sdk.token"
    assert session.status == RealtimeSession.Status.READY
    assert session.started_at is not None
    assert session.ready_at is not None


def test_create_upstream_failure_marks_session_failed() -> None:
    ws, user = _make_workspace("r3upfail@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)
    fake = MagicMock()
    fake.realtime_session_create.side_effect = MediaEngineError(
        "upstream sneezed", status_code=502,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.realtime.views.MediaEngineClient", return_value=cm,
    ):
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    assert response.status_code == 502
    # A failed row should still be persisted for audit.
    session = RealtimeSession.objects.filter(
        spokesperson=sp,
    ).order_by("-created_at").first()
    assert session is not None
    assert session.status == RealtimeSession.Status.FAILED
    assert "upstream sneezed" in session.error_message


# ---- C5 F-09 fix — draft_only body flag -------------------------
#
# `POST /api/realtime_sessions/` used to unconditionally call the
# media-engine (realtime_document_create + realtime_session_create),
# so C5.1's "DRAFT-only container" contract (BRIDGE_TOOLS_UI_V1.md
# rule 2) was architecturally impossible: every SPA form submit at
# /workspace/tools started a real Runway session and burned spend.
# The `draft_only=true` body flag skips both media-engine calls,
# leaves the row in DRAFT with empty provider_* fields, and skips
# the Runway-cost tier gates (session count + minutes budget).
# Dispatch (R7) still runs against the DRAFT session via
# `_execute_inline`; that path is independently tested and
# unchanged.


def test_create_draft_only_skips_media_engine_and_stays_draft() -> None:
    """F-09 fix — draft_only=true creates the Django row but
    never touches Runway. Response is 201 with empty provider_*
    fields; row status stays DRAFT; no session_key issued."""
    ws, user = _make_workspace("f09draft@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)
    patcher, fake = _patch_create()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "draft_only": True},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    # Contract rule 2 — no Runway session, no session key, no
    # document push. All the fields the SDK would need to connect
    # a live avatar stay empty.
    assert data["provider_session_id"] == ""
    assert data["provider_session_key"] == ""
    assert data["provider_document_id"] == ""
    assert data["status"] == "draft"
    fake.realtime_document_create.assert_not_called()
    fake.realtime_session_create.assert_not_called()
    # Persisted row mirrors the response.
    session = RealtimeSession.objects.get(id=data["id"])
    assert session.status == RealtimeSession.Status.DRAFT
    assert session.provider_session_id == ""
    assert session.provider_session_key == ""
    assert session.cost_estimate_micros == 0
    assert session.ready_at is None


def test_create_draft_only_bypasses_tier_gates() -> None:
    """F-09 fix — the Runway session-count + minutes-budget
    gates are Runway-cost gates. Draft-only containers exercise
    neither, so they must not count against those caps. Bridge
    tool dispatch still gates at the EB resolver (tier check
    lives there)."""
    ws, user = _make_workspace("f09gate@test")
    sp = _make_teammate(ws)
    sub = Subscription.objects.get(workspace=ws)
    sub.tier = Subscription.Tier.STARTER
    sub.save(update_fields=["tier"])
    # Pre-fill the Starter cap. A regular create would 402 here.
    for _ in range(5):
        RealtimeSession.objects.create(
            workspace=ws,
            spokesperson=sp,
            status=RealtimeSession.Status.ENDED,
        )
    client = APIClient()
    _login(client, user)
    # No media-engine patch needed — draft_only should never call it.
    response = client.post(
        "/api/realtime_sessions/",
        {"spokesperson": str(sp.id), "draft_only": True},
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["status"] == "draft"


# ---- P1 2.8-b (F-12 fix) — server default is DRAFT --------------
#
# Pre-P1-2.8-b, the create endpoint defaulted to real-mode: any POST
# without `draft_only=true` provisioned a paid Runway session. F-12
# (SESSION 226) showed this failed silently when the running Django
# process was stale — a client that thought it was sending
# `draft_only=true` (because the SPA HEAD had the flag) still got
# a real session when the runserver held pre-F-09-A code in memory.
#
# The fix (SESSION 227) inverts the default: `real_mode=true` is the
# only way to get a paid session. `draft_only=true` is retained for
# C5's SPA to keep sending it as an explicit-intent marker. The two
# flags are contradictory when both are True → 400.


def test_create_no_flag_defaults_to_draft_after_p1_2_8_b() -> None:
    """P1 2.8-b — server default flipped from real-mode → draft.
    A POST with no `real_mode` and no `draft_only` now lands in
    DRAFT with empty provider_* fields and no media-engine calls.
    Any regression here reopens the F-12 recurrence window (a
    stale runserver + missing SPA flag would silently start a
    paid Runway session)."""
    ws, user = _make_workspace("p128b_default@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)
    patcher, fake = _patch_create()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id)},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED
    fake.realtime_document_create.assert_not_called()
    fake.realtime_session_create.assert_not_called()
    data = response.json()
    assert data["status"] == "draft"
    assert data["provider_session_id"] == ""
    assert data["provider_session_key"] == ""
    assert data["provider_document_id"] == ""


def test_create_real_mode_true_pushes_document_and_creates_session() -> None:
    """P1 2.8-b — R8's realtime avatar path opts in with
    `real_mode=true`. This is the ONLY code path that provisions
    a paid Runway session; any regression here breaks the R8
    surface."""
    ws, user = _make_workspace("p128b_realmode@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)
    patcher, fake = _patch_create()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED
    fake.realtime_document_create.assert_called_once()
    fake.realtime_session_create.assert_called_once()
    data = response.json()
    assert data["provider_session_id"] == "rt_session_abc"
    assert data["status"] == "ready"


def test_create_real_mode_and_draft_only_contradictory_returns_400() -> None:
    """P1 2.8-b — sending both `real_mode=true` AND
    `draft_only=true` is nonsense (a session cannot be both live
    and draft). The endpoint rejects it with 400 rather than
    picking one arbitrarily; forces the caller to fix their
    payload."""
    ws, user = _make_workspace("p128b_conflict@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)
    # No media-engine patch — validation fails before any
    # upstream call.
    response = client.post(
        "/api/realtime_sessions/",
        {
            "spokesperson": str(sp.id),
            "real_mode": True,
            "draft_only": True,
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    body = response.json()
    assert "real_mode" in body


# ---- retrieve does NOT leak session_key -------------------------


def test_retrieve_does_not_return_session_key() -> None:
    """Contract rule 9 — retrieve must NEVER include
    provider_session_key. The SDK already has it from the
    create response; subsequent retrieves are just status
    polling."""
    ws, user = _make_workspace("r3leak@test")
    sp = _make_teammate(ws)
    client = APIClient()
    _login(client, user)
    patcher, _ = _patch_create()
    with patcher:
        create = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    session_id = create.json()["id"]
    response = client.get(f"/api/realtime_sessions/{session_id}/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert "provider_session_key" not in data
    # Sanity check provider_session_id IS in retrieve (it's
    # not the secret — just the upstream id).
    assert data["provider_session_id"] == "rt_session_abc"


# ---- tier-limit gate --------------------------------------------


def test_create_rejected_at_tier_limit() -> None:
    """Starter tier caps at 5 realtime sessions/month. Going
    past it raises 402 with the structured payload."""
    ws, user = _make_workspace("r3tier@test")
    sp = _make_teammate(ws)
    sub = Subscription.objects.get(workspace=ws)
    sub.tier = Subscription.Tier.STARTER
    sub.save(update_fields=["tier"])
    # Pre-fill 5 sessions in the current period. Use ENDED so they
    # count against the tier cap — get_usage now excludes DRAFT /
    # FAILED rows because they never consumed Runway quota.
    for _ in range(5):
        RealtimeSession.objects.create(
            workspace=ws,
            spokesperson=sp,
            status=RealtimeSession.Status.ENDED,
        )
    client = APIClient()
    _login(client, user)
    patcher, _ = _patch_create()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    assert response.status_code == 402
    payload = response.json()
    assert payload["code"] == "realtime_session_limit_reached"
    assert payload["realtime_sessions_used"] == 5
    assert payload["realtime_sessions_limit"] == 5
    assert payload["suggested_tier"] == "pro"


def test_agency_tier_has_unlimited_sessions() -> None:
    ws, user = _make_workspace("r3agency@test")
    sp = _make_teammate(ws)
    sub = Subscription.objects.get(workspace=ws)
    sub.tier = Subscription.Tier.AGENCY
    sub.save(update_fields=["tier"])
    # Pre-fill far past the starter cap. Use ENDED so the rows count;
    # get_usage excludes DRAFT / FAILED.
    for _ in range(50):
        RealtimeSession.objects.create(
            workspace=ws,
            spokesperson=sp,
            status=RealtimeSession.Status.ENDED,
        )
    client = APIClient()
    _login(client, user)
    patcher, _ = _patch_create()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id), "real_mode": True},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED


# ---- retrieve poll ------------------------------------------------


def test_retrieve_polls_upstream_when_creating() -> None:
    ws, user = _make_workspace("r3poll@test")
    sp = _make_teammate(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        provider_session_id="rt_xyz",
        provider_session_key="key",
        status=RealtimeSession.Status.CREATING,
    )
    client = APIClient()
    _login(client, user)
    fake = MagicMock()
    fake.realtime_session_poll.return_value = RealtimeSessionPollResult(
        session_id="rt_xyz", status="ready",
        expires_at=None, error_message="", mock_mode=True,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.views.MediaEngineClient", return_value=cm):
        response = client.get(f"/api/realtime_sessions/{session.id}/")
    assert response.status_code == http.HTTP_200_OK
    session.refresh_from_db()
    assert session.status == RealtimeSession.Status.READY
    assert session.ready_at is not None


def test_retrieve_does_not_poll_for_terminal_states() -> None:
    ws, user = _make_workspace("r3nopoll@test")
    sp = _make_teammate(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        provider_session_id="rt_done",
        status=RealtimeSession.Status.READY,
    )
    client = APIClient()
    _login(client, user)
    fake = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.views.MediaEngineClient", return_value=cm):
        response = client.get(f"/api/realtime_sessions/{session.id}/")
    assert response.status_code == http.HTTP_200_OK
    fake.realtime_session_poll.assert_not_called()


# ---- end ---------------------------------------------------------


def test_destroy_marks_ended_without_upstream_delete() -> None:
    """DELETE /api/realtime_sessions/<id>/ flips the local DB
    row to ENDED but deliberately does NOT call upstream
    DELETE on /v1/realtime_sessions/<id>. Verified against
    the live Runway dev API (May 2026): the DELETE marks the
    underlying conversation as `failed` with no transcript.
    The SDK's LiveKit room close (triggered when AvatarCall
    unmounts in the SPA) is the natural-end signal; Runway
    flips the realtime_session to COMPLETED and populates
    the avatar_conversations transcript on its own."""
    ws, user = _make_workspace("r3end@test")
    sp = _make_teammate(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        provider_session_id="rt_end",
        provider_session_key="key",
        status=RealtimeSession.Status.READY,
        started_at=datetime.now(tz=timezone.utc) - timedelta(seconds=42),
    )
    client = APIClient()
    _login(client, user)
    fake = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.views.MediaEngineClient", return_value=cm):
        response = client.delete(f"/api/realtime_sessions/{session.id}/")
    assert response.status_code == http.HTTP_200_OK
    fake.realtime_session_end.assert_not_called()
    session.refresh_from_db()
    assert session.status == RealtimeSession.Status.ENDED
    assert session.ended_at is not None
    assert session.duration_seconds >= 40


def test_end_action_endpoint_alternative_to_delete() -> None:
    """POST /api/realtime_sessions/<id>/end/ is the
    alternate end path for proxies that strip DELETE."""
    ws, user = _make_workspace("r3endact@test")
    sp = _make_teammate(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        provider_session_id="rt_alt",
        status=RealtimeSession.Status.READY,
        started_at=datetime.now(tz=timezone.utc) - timedelta(seconds=10),
    )
    client = APIClient()
    _login(client, user)
    fake = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.views.MediaEngineClient", return_value=cm):
        response = client.post(f"/api/realtime_sessions/{session.id}/end/")
    assert response.status_code == http.HTTP_200_OK
    session.refresh_from_db()
    assert session.status == RealtimeSession.Status.ENDED


def test_end_marks_ended_even_when_upstream_fails() -> None:
    """Upstream teardown failure shouldn't block the local
    state — the Django row is our source of truth post-end."""
    ws, user = _make_workspace("r3endfail@test")
    sp = _make_teammate(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        provider_session_id="rt_stuck",
        status=RealtimeSession.Status.READY,
        started_at=datetime.now(tz=timezone.utc) - timedelta(seconds=5),
    )
    client = APIClient()
    _login(client, user)
    fake = MagicMock()
    fake.realtime_session_end.side_effect = MediaEngineError(
        "upstream timeout", status_code=504,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.views.MediaEngineClient", return_value=cm):
        response = client.delete(f"/api/realtime_sessions/{session.id}/")
    assert response.status_code == http.HTTP_200_OK
    session.refresh_from_db()
    assert session.status == RealtimeSession.Status.ENDED


def test_end_is_idempotent() -> None:
    ws, user = _make_workspace("r3endidem@test")
    sp = _make_teammate(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        provider_session_id="rt_done",
        status=RealtimeSession.Status.ENDED,
        ended_at=datetime.now(tz=timezone.utc),
        duration_seconds=120,
    )
    client = APIClient()
    _login(client, user)
    fake = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.views.MediaEngineClient", return_value=cm):
        response = client.delete(f"/api/realtime_sessions/{session.id}/")
    assert response.status_code == http.HTTP_200_OK
    fake.realtime_session_end.assert_not_called()
    session.refresh_from_db()
    # Duration must NOT be re-computed (idempotent).
    assert session.duration_seconds == 120


# ---- list filters ------------------------------------------------


def test_list_filters_by_spokesperson() -> None:
    ws, user = _make_workspace("r3lsp@test")
    sp_1 = _make_teammate(ws, name="Teammate A", avatar_id="av_a")
    sp_2 = _make_teammate(ws, name="Teammate B", avatar_id="av_b")
    RealtimeSession.objects.create(workspace=ws, spokesperson=sp_1)
    RealtimeSession.objects.create(workspace=ws, spokesperson=sp_2)
    RealtimeSession.objects.create(workspace=ws, spokesperson=sp_1)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/realtime_sessions/?spokesperson={sp_1.id}")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert len(data) == 2
    assert all(d["spokesperson"] == str(sp_1.id) for d in data)


def test_list_scopes_to_caller_workspaces() -> None:
    ws_a, user_a = _make_workspace("r3lsa@test", "A")
    ws_b, _user_b = _make_workspace("r3lsb@test", "B")
    sp_a = _make_teammate(ws_a)
    sp_b = _make_teammate(ws_b)
    RealtimeSession.objects.create(workspace=ws_a, spokesperson=sp_a)
    RealtimeSession.objects.create(workspace=ws_b, spokesperson=sp_b)
    RealtimeSession.objects.create(workspace=ws_b, spokesperson=sp_b)
    client = APIClient()
    _login(client, user_a)
    response = client.get("/api/realtime_sessions/")
    data = response.json()
    assert len(data) == 1
    assert data[0]["workspace"] == str(ws_a.id)
