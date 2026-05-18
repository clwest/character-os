"""R5 tests — transcript capture (post-session fetch +
persist as Asset(TRANSCRIPT)).

Covered:

* Task fetches from media-engine + creates
  Asset(asset_type=TRANSCRIPT) in the session's workspace.
* Asset is wired to ``RealtimeSession.transcript_asset``.
* Empty upstream transcript (404 / not recorded yet) returns
  empty status — no Asset created.
* Idempotent: re-running on a session that already has a
  transcript_asset replaces the stale Asset with a fresh
  one.
* Upstream MediaEngineError returns ``upstream_error``
  status without crashing.
* Task safely no-ops when the session row is missing /
  has no provider_session_id.
* Segments are preserved on the Asset's ``source_spec``.
* Broker's end flow enqueues the task in eager celery
  mode → Asset gets created automatically.
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
from apps.compositions.models import Asset, AssetType
from apps.realtime.models import RealtimeSession
from apps.realtime.tasks import fetch_transcript_for_session
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineError,
    RealtimeTranscriptResult,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _eager_celery():
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


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Sasha", runway_avatar_id="av_test",
        portrait_path="https://fake/p.png", business_brief="b",
    )


def _make_session(ws: Workspace, sp: Spokesperson, **kwargs) -> RealtimeSession:
    defaults = dict(
        workspace=ws,
        spokesperson=sp,
        provider_session_id="rt_session_xyz",
        provider_session_key="key",
        status=RealtimeSession.Status.READY,
    )
    defaults.update(kwargs)
    return RealtimeSession.objects.create(**defaults)


def _patch_fetch(text: str = "User: Hi.\nSasha: Hello!", segments=None):
    """Patch the broker's MediaEngineClient.realtime_session_fetch_transcript
    to return the given content. Returns (patcher_ctx, fake_client)."""
    fake = MagicMock()
    fake.realtime_session_fetch_transcript.return_value = RealtimeTranscriptResult(
        session_id="rt_session_xyz",
        text=text,
        segments=segments if segments is not None else [
            {"role": "user", "text": "Hi.", "ts": "2026-05-15T00:00:00Z"},
            {"role": "spokesperson", "text": "Hello!", "ts": "2026-05-15T00:00:01Z"},
        ],
        mock_mode=True,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    return patch(
        "apps.realtime.tasks.MediaEngineClient", return_value=cm,
    ), fake


# ---- task happy path -------------------------------------------


def test_task_persists_transcript_as_asset() -> None:
    ws, _user = _make_workspace("r5persist@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    patcher, _ = _patch_fetch(text="User: Hi.\nSasha: Hello!")
    with patcher:
        result = fetch_transcript_for_session.apply(args=[str(session.id)]).get()
    assert result["status"] == "persisted"
    assert result["chars"] > 0
    asset_id = result["asset_id"]
    assert asset_id is not None
    asset = Asset.objects.get(pk=asset_id)
    assert asset.asset_type == AssetType.TRANSCRIPT
    assert asset.workspace_id == ws.pk
    assert "Hi." in asset.inline_content
    assert "Hello!" in asset.inline_content
    # Session is wired.
    session.refresh_from_db()
    assert session.transcript_asset_id == asset.pk


def test_task_preserves_segments_in_source_spec() -> None:
    ws, _user = _make_workspace("r5segs@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    custom_segments = [
        {"role": "user", "text": "Q1", "ts": "t1"},
        {"role": "spokesperson", "text": "A1", "ts": "t2"},
        {"role": "user", "text": "Q2", "ts": "t3"},
    ]
    patcher, _ = _patch_fetch(text="conversation body", segments=custom_segments)
    with patcher:
        fetch_transcript_for_session.apply(args=[str(session.id)]).get()
    session.refresh_from_db()
    asset = session.transcript_asset
    assert asset is not None
    assert asset.source_spec["primitive_kind"] == "realtime_transcript"
    assert asset.source_spec["segments"] == custom_segments
    assert asset.source_spec["session_id"] == str(session.id)


def test_task_empty_transcript_creates_no_asset() -> None:
    """Runway 404 (not recorded yet) returns empty text →
    task no-ops, no Asset row, session.transcript_asset
    stays null."""
    ws, _user = _make_workspace("r5empty@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    patcher, _ = _patch_fetch(text="", segments=[])
    with patcher:
        result = fetch_transcript_for_session.apply(args=[str(session.id)]).get()
    assert result["status"] == "empty"
    assert result["asset_id"] is None
    assert Asset.objects.filter(workspace=ws).count() == 0
    session.refresh_from_db()
    assert session.transcript_asset_id is None


def test_task_idempotent_replaces_stale_asset() -> None:
    """Re-running on a session that already has a
    transcript_asset replaces the old asset with a fresh
    one (keeps transcript current if Runway updated)."""
    ws, _user = _make_workspace("r5idem@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    patcher, _ = _patch_fetch(text="First version.")
    with patcher:
        first_run = fetch_transcript_for_session.apply(args=[str(session.id)]).get()
    first_asset_id = first_run["asset_id"]
    patcher2, _ = _patch_fetch(text="Second, fresher version.")
    with patcher2:
        second_run = fetch_transcript_for_session.apply(args=[str(session.id)]).get()
    second_asset_id = second_run["asset_id"]
    assert first_asset_id != second_asset_id
    # First asset is gone.
    assert not Asset.objects.filter(pk=first_asset_id).exists()
    session.refresh_from_db()
    fresh_asset = session.transcript_asset
    assert fresh_asset is not None
    assert "Second, fresher" in fresh_asset.inline_content


def test_task_upstream_failure_returns_error_status() -> None:
    ws, _user = _make_workspace("r5fail@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    fake = MagicMock()
    fake.realtime_session_fetch_transcript.side_effect = MediaEngineError(
        "runway 500", status_code=500,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.tasks.MediaEngineClient", return_value=cm):
        result = fetch_transcript_for_session.apply(args=[str(session.id)]).get()
    assert result["status"] == "upstream_error"
    session.refresh_from_db()
    assert session.transcript_asset_id is None


def test_task_unknown_session_no_ops() -> None:
    result = fetch_transcript_for_session.apply(
        args=["11111111-1111-1111-1111-111111111111"],
    ).get()
    assert result["status"] == "not_found"


def test_task_upstream_failed_flips_session_to_failed() -> None:
    """Runway's session-level ``status: "failed"`` is permanent —
    the provider raises with the ``runway session marked failed``
    marker, the broker flips ``RealtimeSession.status = FAILED``
    and persists the upstream body so the SPA can show the real
    failureCode instead of an open-ended 'transcript pending'."""
    from apps.realtime.models import RealtimeSession

    ws, _user = _make_workspace("r5upstreamfailed@test")
    sp = _make_spokesperson(ws)
    session = _make_session(ws, sp)
    upstream_body = (
        '{"error":"runway session marked failed [code=UNKNOWN]: '
        'Unknown error","code":"upstream_runway_error"}'
    )
    fake = MagicMock()
    fake.realtime_session_fetch_transcript.side_effect = MediaEngineError(
        "GET /internal/realtime_sessions/abc/transcript/ returned 502",
        status_code=502,
        response_text=upstream_body,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch("apps.realtime.tasks.MediaEngineClient", return_value=cm):
        result = fetch_transcript_for_session.apply(args=[str(session.id)]).get()
    assert result["status"] == "upstream_failed"
    session.refresh_from_db()
    assert session.status == RealtimeSession.Status.FAILED
    # Persisted error is the upstream body (actionable for triage),
    # not the MediaEngineClient wrapper ("returned 502").
    assert "runway session marked failed" in session.error_message
    assert "code=UNKNOWN" in session.error_message
    assert session.transcript_asset_id is None


def test_task_session_without_provider_id_skips() -> None:
    ws, _user = _make_workspace("r5nopid@test")
    sp = _make_spokesperson(ws)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp,
        provider_session_id="",  # never went upstream
        status=RealtimeSession.Status.FAILED,
    )
    result = fetch_transcript_for_session.apply(args=[str(session.id)]).get()
    assert result["status"] == "empty"


# ---- broker integration ------------------------------------------


def test_broker_end_enqueues_transcript_fetch() -> None:
    """Ending a session via the DELETE endpoint should
    enqueue fetch_transcript_for_session in eager celery
    → Asset gets created in the same request."""
    ws, user = _make_workspace("r5broker@test")
    sp = _make_spokesperson(ws)
    session = _make_session(
        ws, sp,
        started_at=datetime.now(tz=timezone.utc) - timedelta(seconds=42),
    )
    client = APIClient()
    client.force_authenticate(user=user)
    # Stub the broker's MediaEngineClient (called for
    # `realtime_session_end`) AND the task's
    # MediaEngineClient (called for
    # `realtime_session_fetch_transcript`).
    fake_broker = MagicMock()
    cm_broker = MagicMock()
    cm_broker.__enter__.return_value = fake_broker
    cm_broker.__exit__.return_value = False
    task_patcher, _ = _patch_fetch(text="End-flow transcript content.")
    with patch(
        "apps.realtime.views.MediaEngineClient", return_value=cm_broker,
    ), task_patcher:
        response = client.delete(f"/api/realtime_sessions/{session.id}/")
    assert response.status_code == http.HTTP_200_OK
    session.refresh_from_db()
    assert session.status == RealtimeSession.Status.ENDED
    assert session.transcript_asset_id is not None
    transcript = session.transcript_asset
    assert "End-flow transcript content." in transcript.inline_content
    assert transcript.workspace_id == ws.pk


def test_broker_end_handles_transcript_enqueue_failure_gracefully() -> None:
    """If Celery enqueue raises, the end response should
    still succeed — transcript capture is best-effort."""
    ws, user = _make_workspace("r5brokerfail@test")
    sp = _make_spokesperson(ws)
    session = _make_session(
        ws, sp,
        started_at=datetime.now(tz=timezone.utc) - timedelta(seconds=5),
    )
    client = APIClient()
    client.force_authenticate(user=user)
    fake_broker = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake_broker
    cm.__exit__.return_value = False
    with patch(
        "apps.realtime.views.MediaEngineClient", return_value=cm,
    ), patch(
        "apps.realtime.tasks.fetch_transcript_for_session.delay",
        side_effect=RuntimeError("broker down"),
    ):
        response = client.delete(f"/api/realtime_sessions/{session.id}/")
    assert response.status_code == http.HTTP_200_OK
    session.refresh_from_db()
    assert session.status == RealtimeSession.Status.ENDED
    # Transcript wasn't captured (enqueue failed), but
    # session is properly ended.
    assert session.transcript_asset_id is None
