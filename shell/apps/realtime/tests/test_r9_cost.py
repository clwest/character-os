"""R9 tests — cost governance backend.

What this slice ships:

1. ``apps/realtime/cost.py`` — `cost_per_minute_micros`,
   `estimate_session_cost_micros`,
   `actual_session_cost_micros`, `PROVIDER_MAX_SESSION_MINUTES`.
2. ``TIER_LIMITS['<tier>']['realtime_minutes_per_month']``
   — 30 / 120 / None per starter / pro / agency.
3. ``check_realtime_minutes_budget(workspace,
   requested_minutes)`` in billing/services.
4. ``Usage`` shape gains `realtime_minutes_used` +
   `realtime_minutes_limit`.
5. Broker create stamps `cost_estimate_micros` post-
   media-engine; broker `_end_session` stamps
   `cost_actual_micros` from `duration_seconds`.
6. ``GET /api/realtime_sessions/cost_estimate/`` returns
   the SPA-facing cost shape.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.billing.models import Subscription
from apps.billing.services import (
    TierLimitExceeded,
    check_realtime_minutes_budget,
    get_usage,
)
from apps.realtime.cost import (
    PROVIDER_MAX_SESSION_MINUTES,
    actual_session_cost_micros,
    cost_per_minute_micros,
    estimate_session_cost_micros,
)
from apps.realtime.models import RealtimeSession
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    RealtimeDocumentResult,
    RealtimeSessionResult,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mocks():
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
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


def _set_tier(ws: Workspace, tier: str) -> None:
    sub, _ = Subscription.objects.get_or_create(
        workspace=ws,
        defaults={"tier": tier, "status": Subscription.Status.ACTIVE},
    )
    sub.tier = tier
    sub.save()


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Sasha", runway_avatar_id="av_test",
        portrait_path="https://fake/p.png", business_brief="brief",
    )


# ---- cost estimator -----------------------------------------------


def test_cost_per_minute_micros_runway():
    assert cost_per_minute_micros("runway") == 80_000


def test_cost_per_minute_micros_unknown_falls_back():
    # Defensive — unknown providers don't free-tier
    # accidentally.
    assert cost_per_minute_micros("synthesia") == 80_000


def test_estimate_session_cost_micros_default_cap():
    # Default uses PROVIDER_MAX_SESSION_MINUTES (5).
    assert estimate_session_cost_micros("runway") == 400_000


def test_estimate_session_cost_micros_partial_minutes():
    assert estimate_session_cost_micros("runway", minutes=2.5) == 200_000


def test_actual_session_cost_zero_duration():
    """Sessions that flip to FAILED before going live have
    duration_seconds=0 — the helper returns 0 rather than
    a NaN-ish micros value."""
    ws, _u = _make_workspace("r9c0@test")
    sp = _make_spokesperson(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.FAILED,
        duration_seconds=0,
    )
    assert actual_session_cost_micros(session) == 0


def test_actual_session_cost_from_duration():
    ws, _u = _make_workspace("r9c1@test")
    sp = _make_spokesperson(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.ENDED,
        duration_seconds=180,  # 3 minutes
    )
    # 3 min × 80_000 micros/min = 240_000 micros
    assert actual_session_cost_micros(session) == 240_000


# ---- minutes budget gate ------------------------------------------


def test_minutes_budget_passes_under_cap():
    ws, _u = _make_workspace("r9b1@test")
    _set_tier(ws, "starter")  # 30-min cap
    # No prior sessions — budget free. Should not raise.
    check_realtime_minutes_budget(ws, requested_minutes=5)


def test_minutes_budget_raises_at_cap():
    ws, _u = _make_workspace("r9b2@test")
    _set_tier(ws, "starter")
    sp = _make_spokesperson(ws)
    # Seed sessions totaling 28 minutes (just under cap).
    # Default cap = 30; requesting 5 min more pushes
    # projected to 33, over.
    RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.ENDED,
        duration_seconds=28 * 60,
    )
    with pytest.raises(TierLimitExceeded) as ctx:
        check_realtime_minutes_budget(ws, requested_minutes=5)
    payload = ctx.value.payload
    assert payload["code"] == "realtime_minutes_limit_reached"
    assert payload["realtime_minutes_limit"] == 30
    assert payload["suggested_tier"] == "pro"


def test_minutes_budget_unlimited_for_agency():
    ws, _u = _make_workspace("r9b3@test")
    _set_tier(ws, "agency")
    sp = _make_spokesperson(ws)
    # Seed an absurd amount of usage — agency has no cap.
    RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.ENDED,
        duration_seconds=10_000 * 60,
    )
    # Should not raise.
    check_realtime_minutes_budget(ws, requested_minutes=5)


# ---- Usage shape --------------------------------------------------


def test_usage_includes_realtime_minutes_fields():
    ws, _u = _make_workspace("r9u1@test")
    _set_tier(ws, "starter")
    sp = _make_spokesperson(ws)
    # Seed 7 minutes of usage in the period.
    RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.ENDED,
        duration_seconds=7 * 60,
    )
    usage = get_usage(ws)
    assert usage.realtime_minutes_used == 7
    assert usage.realtime_minutes_limit == 30
    # Dict shape too.
    d = usage.to_dict()
    assert d["realtime_minutes_used"] == 7
    assert d["realtime_minutes_limit"] == 30


def test_usage_rounds_up_partial_minutes():
    """A 90-second session counts as 2 minutes, not 1.
    Operator-facing meters round UP so partial-minute
    usage is visible against the cap."""
    ws, _u = _make_workspace("r9u2@test")
    _set_tier(ws, "starter")
    sp = _make_spokesperson(ws)
    RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.ENDED,
        duration_seconds=90,
    )
    usage = get_usage(ws)
    assert usage.realtime_minutes_used == 2


# ---- broker stamps ------------------------------------------------


def _patch_broker_clients(*, mock_mode: bool = True):
    fake = MagicMock()
    fake.realtime_document_create.return_value = RealtimeDocumentResult(
        document_id="doc_x", mock_mode=mock_mode,
    )
    fake.realtime_session_create.return_value = RealtimeSessionResult(
        session_id="rt_sess_x",
        session_key="eyJ.k.t",
        status="ready",
        expires_at=None,
        avatar_id="av_test",
        mock_mode=mock_mode,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return patch(
        "apps.realtime.views.MediaEngineClient", return_value=cm,
    ), fake


def test_broker_create_stamps_cost_estimate():
    ws, user = _make_workspace("r9bk1@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    client.force_authenticate(user=user)
    patcher, _ = _patch_broker_clients()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id)},
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    session = RealtimeSession.objects.get(id=response.json()["id"])
    # Full session cap × runway rate = $0.40
    assert session.cost_estimate_micros == 400_000


def test_broker_end_stamps_cost_actual():
    """End a session that's been live for 3 minutes; the
    `_end_session` flow should stamp
    `cost_actual_micros = 240_000` ($0.24)."""
    ws, user = _make_workspace("r9bk2@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    client.force_authenticate(user=user)
    patcher, _ = _patch_broker_clients()
    with patcher:
        create = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id)},
            format="json",
        )
        session_id = create.json()["id"]
        # Backdate started_at so the duration calculation
        # at end yields ~180s without sleeping the test.
        session = RealtimeSession.objects.get(id=session_id)
        session.started_at = datetime.now(timezone.utc) - timedelta(seconds=180)
        session.save(update_fields=["started_at"])
        end = client.post(
            f"/api/realtime_sessions/{session_id}/end/",
            {}, format="json",
        )
    assert end.status_code == http.HTTP_200_OK
    session.refresh_from_db()
    assert session.duration_seconds >= 179
    # Allow a 1-second floor for clock skew between the
    # backdate + the broker's `now`. The cost is
    # duration × rate / 60.
    expected = (session.duration_seconds / 60) * 80_000
    assert abs(session.cost_actual_micros - expected) < 100


def test_broker_create_blocks_at_minutes_cap():
    ws, user = _make_workspace("r9bk3@test")
    _set_tier(ws, "starter")  # 30 min cap
    sp = _make_spokesperson(ws)
    # Burn the full budget already.
    RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        status=RealtimeSession.Status.ENDED,
        duration_seconds=30 * 60,
    )
    client = APIClient()
    client.force_authenticate(user=user)
    patcher, _ = _patch_broker_clients()
    with patcher:
        response = client.post(
            "/api/realtime_sessions/",
            {"spokesperson": str(sp.id)},
            format="json",
        )
    # 402 Payment Required from the minutes-budget gate.
    assert response.status_code == 402
    payload = response.json()
    assert payload["code"] == "realtime_minutes_limit_reached"


# ---- cost_estimate REST endpoint ---------------------------------


def test_cost_estimate_endpoint_returns_workspace_shape():
    ws, user = _make_workspace("r9rest1@test")
    _set_tier(ws, "pro")  # 120-min cap
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/realtime_sessions/cost_estimate/")
    assert response.status_code == http.HTTP_200_OK, response.content
    payload = response.json()
    assert payload["provider"] == "runway"
    assert payload["cost_per_minute_micros"] == 80_000
    assert payload["max_session_minutes"] == PROVIDER_MAX_SESSION_MINUTES
    assert payload["monthly_minutes_used"] == 0
    assert payload["monthly_minutes_limit"] == 120
    assert payload["monthly_minutes_remaining"] == 120
    assert payload["tier"] == "pro"


def test_cost_estimate_endpoint_unlimited_tier():
    ws, user = _make_workspace("r9rest2@test")
    _set_tier(ws, "agency")
    client = APIClient()
    client.force_authenticate(user=user)
    response = client.get("/api/realtime_sessions/cost_estimate/")
    assert response.status_code == http.HTTP_200_OK
    payload = response.json()
    assert payload["monthly_minutes_limit"] is None
    assert payload["monthly_minutes_remaining"] is None


def test_cost_estimate_endpoint_requires_auth():
    client = APIClient()
    response = client.get("/api/realtime_sessions/cost_estimate/")
    assert response.status_code in (
        http.HTTP_401_UNAUTHORIZED,
        http.HTTP_403_FORBIDDEN,
    )


def test_cost_estimate_endpoint_cross_workspace_rejected():
    ws_a, _ua = _make_workspace("r9rest3a@test", "A")
    ws_b, user_b = _make_workspace("r9rest3b@test", "B")
    client = APIClient()
    client.force_authenticate(user=user_b)
    response = client.get(
        f"/api/realtime_sessions/cost_estimate/?workspace={ws_a.id}",
    )
    # Not a member of A → 404 (avoid leaking existence
    # of other workspaces).
    assert response.status_code == http.HTTP_404_NOT_FOUND
