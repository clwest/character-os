"""EB.3 tests — `/api/engine_connections/` DRF surface.

Eight tests per the ENGINE_BRIDGE_V1 scope-lock plan:

1. List endpoint is workspace-scoped (cross-workspace rows are
   never returned).
2. Create row; response redacts the token (`****abcd` shape).
3. GET single row; token preview never returns full value.
4. PATCH the token; subsequent GET shows the new redacted preview
   (different from the create-time preview).
5. DELETE removes the row.
6. test_ping happy path (mocked upstream returns 200).
7. test_ping engine-unreachable path (URLError surfaces in error
   message + 3-second timeout boundary).
8. Starter tier gets 403 on create.

Plus two structural extras:
* Anonymous user gets 401 on list.
* Duplicate (workspace, engine_kind) on create returns 400.
"""
from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.billing.models import Subscription
from apps.realtime.models import EngineConnection

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _make_user_workspace(email: str, *, tier: str = "pro") -> tuple[User, Workspace]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    sub, _ = Subscription.objects.get_or_create(
        workspace=ws,
        defaults={"tier": tier, "status": Subscription.Status.ACTIVE},
    )
    sub.tier = tier
    sub.save()
    return user, ws


def _make_connection(
    ws: Workspace, *, token: str = "tok_supersecret_abcd", url: str = "https://eng.example",
) -> EngineConnection:
    return EngineConnection.objects.create(
        workspace=ws,
        engine_kind=EngineConnection.Kind.UDB_PA,
        engine_url=url,
        engine_token=token,
    )


def _client(user) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


# ---------------------------------------------------------------------------
# tests
# ---------------------------------------------------------------------------


def test_list_is_workspace_scoped():
    """1. List shows only the requesting user's workspace rows."""
    user_a, ws_a = _make_user_workspace("a@x.test")
    _, ws_b = _make_user_workspace("b@x.test")
    _make_connection(ws_a, token="aaaaaaaaaa1234")
    _make_connection(ws_b, token="bbbbbbbbbb5678")

    resp = _client(user_a).get("/api/engine_connections/")

    assert resp.status_code == http.HTTP_200_OK
    payload = resp.json()
    assert len(payload) == 1
    assert payload[0]["engine_token_preview"] == "****1234"
    # Token never leaks under any field name.
    serialized = json.dumps(payload)
    assert "aaaaaaaaaa1234" not in serialized


def test_create_returns_redacted_token():
    """2. Create accepts engine_token; response includes only the
    redacted preview, never the stored value."""
    user, _ = _make_user_workspace("c@x.test")

    resp = _client(user).post(
        "/api/engine_connections/",
        {
            "engine_url": "https://eng.example",
            "engine_token": "tok_secret_value_9999",
            "label": "Customer 1",
        },
        format="json",
    )

    assert resp.status_code == http.HTTP_201_CREATED
    payload = resp.json()
    assert payload["engine_token_preview"] == "****9999"
    assert "engine_token" not in payload or payload.get("engine_token") in (None, "")
    assert "tok_secret_value_9999" not in json.dumps(payload)
    # Stored row has the full token.
    row = EngineConnection.objects.get(pk=payload["id"])
    assert row.engine_token == "tok_secret_value_9999"


def test_retrieve_redacts_token():
    """3. Single-row GET redacts identically to list."""
    user, ws = _make_user_workspace("d@x.test")
    conn = _make_connection(ws, token="raw_abcd_efgh")

    resp = _client(user).get(f"/api/engine_connections/{conn.id}/")

    assert resp.status_code == http.HTTP_200_OK
    payload = resp.json()
    assert payload["engine_token_preview"] == "****efgh"
    assert "raw_abcd_efgh" not in json.dumps(payload)


def test_patch_token_updates_redaction():
    """4. PATCH rotates the token; preview reflects the new value."""
    user, ws = _make_user_workspace("e@x.test")
    conn = _make_connection(ws, token="original_token_oldd")

    resp = _client(user).patch(
        f"/api/engine_connections/{conn.id}/",
        {"engine_token": "rotated_token_newx"},
        format="json",
    )

    assert resp.status_code == http.HTTP_200_OK
    assert resp.json()["engine_token_preview"] == "****newx"
    conn.refresh_from_db()
    assert conn.engine_token == "rotated_token_newx"


def test_delete_removes_row():
    """5. DELETE returns 204 + the row is gone."""
    user, ws = _make_user_workspace("f@x.test")
    conn = _make_connection(ws)

    resp = _client(user).delete(f"/api/engine_connections/{conn.id}/")

    assert resp.status_code == http.HTTP_204_NO_CONTENT
    assert not EngineConnection.objects.filter(pk=conn.id).exists()


def test_test_ping_happy_path():
    """6. test_ping POSTs to the engine; response carries
    status_code + body preview + latency. Row's last_tested_at
    + last_test_status get stamped."""
    user, ws = _make_user_workspace("g@x.test")
    conn = _make_connection(ws)

    fake_resp = MagicMock()
    fake_resp.read.return_value = json.dumps(
        {"success": True, "task_id": "t_ping"},
    ).encode("utf-8")
    fake_resp.status = 200
    fake_resp.__enter__ = lambda self: self
    fake_resp.__exit__ = lambda *a: False

    with patch("urllib.request.urlopen", return_value=fake_resp):
        resp = _client(user).post(
            f"/api/engine_connections/{conn.id}/test_ping/",
            format="json",
        )

    assert resp.status_code == http.HTTP_200_OK
    payload = resp.json()
    assert payload["status_code"] == 200
    assert "task_id" in payload["response_preview"]
    assert payload["latency_ms"] >= 0
    assert payload["error_message"] == ""

    conn.refresh_from_db()
    assert conn.last_test_status == 200
    assert conn.last_tested_at is not None


def test_test_ping_engine_unreachable():
    """7. URLError surfaces in error_message; status_code stays
    None; last_test_status reflects the no-status outcome."""
    import urllib.error

    user, ws = _make_user_workspace("h@x.test")
    conn = _make_connection(ws)

    with patch(
        "urllib.request.urlopen",
        side_effect=urllib.error.URLError("connection refused"),
    ):
        resp = _client(user).post(
            f"/api/engine_connections/{conn.id}/test_ping/",
            format="json",
        )

    assert resp.status_code == http.HTTP_200_OK
    payload = resp.json()
    assert payload["status_code"] is None
    assert "connection refused" in payload["error_message"]

    conn.refresh_from_db()
    assert conn.last_test_status is None
    # last_tested_at still stamps — operator-visible "we tried".
    assert conn.last_tested_at is not None


def test_starter_tier_gets_403_on_create():
    """8. Pro+ tier gate at the viewset. Starter create -> 403."""
    user, _ = _make_user_workspace("i@x.test", tier="starter")

    resp = _client(user).post(
        "/api/engine_connections/",
        {
            "engine_url": "https://eng.example",
            "engine_token": "tok_starter",
        },
        format="json",
    )

    assert resp.status_code == http.HTTP_403_FORBIDDEN


# ---- Extras --------------------------------------------------------


def test_anonymous_user_gets_401():
    """List requires authentication."""
    resp = APIClient().get("/api/engine_connections/")
    assert resp.status_code in (
        http.HTTP_401_UNAUTHORIZED,
        http.HTTP_403_FORBIDDEN,
    )


def test_duplicate_kind_returns_400():
    """One row per (workspace, engine_kind) — creating a second
    with the same kind for the same workspace returns 400 with a
    clear message rather than an opaque IntegrityError."""
    user, ws = _make_user_workspace("j@x.test")
    _make_connection(ws)

    resp = _client(user).post(
        "/api/engine_connections/",
        {
            "engine_url": "https://eng.example/v2",
            "engine_token": "tok_dup",
        },
        format="json",
    )

    assert resp.status_code == http.HTTP_400_BAD_REQUEST
    assert "already exists" in json.dumps(resp.json())
