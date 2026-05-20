"""B1.4 — approve / reject REST + render dispatch + completion signal.

Six concerns:

1. **Approve happy path** — PENDING → APPROVED, composition
   created via talking_head_polished recipe, ``produced_composition``
   FK linked, ``execute_composition`` enqueued. The highlight
   ``decided_at`` timestamp is set.
2. **Approve resolves spokesperson via RealtimeSession reverse-FK**
   (Q-b-7). Transcript with no realtime session attached → 400.
3. **Reject happy path** — PENDING → REJECTED, optional
   ``rejection_reason`` captured, ``decided_at`` set.
4. **State-machine guards** — approving/rejecting a row in a
   non-PENDING state is either idempotent (same state) or 400
   (different terminal state).
5. **Cross-workspace approve** — operator A cannot approve
   operator B's highlight (404).
6. **Completion signal** — when the produced composition
   transitions to ``completed``, the linked highlight flips
   APPROVED → RENDERED automatically.

All tests force-mock the LLM helper so mining is deterministic.
``talking_head_polished`` runs in mock_mode=False but the
``execute_composition`` enqueue is patched out so we don't
actually fire Celery during unit tests — the signal test
calls the post-save flow directly.
"""
from __future__ import annotations

from datetime import datetime, timezone as dt_tz
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
)
from apps.realtime.models import RealtimeSession
from apps.spokespeople.models import Spokesperson
from apps.transcripts.models import TranscriptHighlight

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock(settings):
    settings.TRANSCRIPT_MINER_FORCE_MOCK = True
    yield


@pytest.fixture(autouse=True)
def _no_celery_dispatch():
    """Approve fires execute_composition.delay — patch it so
    the test isn't dependent on a running broker. The signal
    test invokes the post-save flow directly so it doesn't
    need a real run."""
    with patch("apps.compositions.tasks.execute_composition.delay") as p:
        yield p


# ---- fixtures ---------------------------------------------------


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Marcus", runway_avatar_id="av_marcus",
        portrait_path="https://fake/p.png",
        business_brief="Roman history guide.",
    )


def _make_transcript_with_session(
    ws: Workspace, sp: Spokesperson,
    body: str = "Assistant: This is a moment worth sharing as a clip.\n",
) -> Asset:
    """Create a transcript Asset PLUS the RealtimeSession that
    R5 would have created for it. The spokesperson reverse-FK
    lookup walks transcript → session → spokesperson."""
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.TRANSCRIPT,
        file_path="",
        inline_content=body,
        source_spec={"primitive_kind": "realtime_transcript"},
        mime_type="text/plain",
        size_bytes=len(body.encode("utf-8")),
    )
    RealtimeSession.objects.create(
        workspace=ws,
        spokesperson=sp,
        status=RealtimeSession.Status.ENDED,
        started_at=datetime(2026, 5, 19, 10, 0, tzinfo=dt_tz.utc),
        ended_at=datetime(2026, 5, 19, 10, 5, tzinfo=dt_tz.utc),
        transcript_asset=asset,
    )
    return asset


def _mine_one(client: APIClient, transcript: Asset) -> TranscriptHighlight:
    """Helper: mine + return the first PENDING row."""
    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript.pk), "target_count": 1},
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    row = TranscriptHighlight.objects.get(pk=response.json()["highlights"][0]["id"])
    assert row.status == TranscriptHighlight.Status.PENDING
    return row


# ---- approve happy path ----------------------------------------


def test_approve_flips_to_approved_and_fires_render(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b14ah@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)

    response = client.post(
        f"/api/transcript_highlights/{highlight.pk}/approve/",
    )
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["status"] == TranscriptHighlight.Status.APPROVED
    assert data["produced_composition_id"] is not None
    assert data["decided_at"] is not None

    # DB matches
    highlight.refresh_from_db()
    assert highlight.status == TranscriptHighlight.Status.APPROVED
    assert highlight.produced_composition is not None
    assert highlight.produced_composition.workspace_id == ws.pk
    assert highlight.produced_composition.spokesperson_id == sp.pk
    assert highlight.produced_composition.template_kind == "talking_head_polished"

    # Celery dispatch was called with the composition id.
    _no_celery_dispatch.assert_called_once_with(
        str(highlight.produced_composition.pk),
    )


def test_approve_passes_highlight_text_as_script(_no_celery_dispatch) -> None:
    """The composition's first step (generate_avatar_speech)
    must carry the highlight text verbatim — that's the whole
    point of B-1."""
    user, ws = _make_user_workspace("b14script@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)

    client.post(f"/api/transcript_highlights/{highlight.pk}/approve/")
    highlight.refresh_from_db()
    comp = highlight.produced_composition
    speech_step = comp.steps.filter(primitive="generate_avatar_speech").first()
    assert speech_step is not None
    assert speech_step.params["script"] == highlight.text


# ---- spokesperson resolution -----------------------------------


def test_approve_fails_when_transcript_has_no_session() -> None:
    """Q-b-7 — operator-uploaded transcripts (no
    RealtimeSession FK) cannot be approved in v1; the
    spokesperson lookup fails loudly."""
    user, ws = _make_user_workspace("b14nosess@test")
    sp = _make_spokesperson(ws)
    # Transcript WITHOUT a RealtimeSession.
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.TRANSCRIPT,
        file_path="",
        inline_content="Assistant: ungrounded line here.\n",
        source_spec={"primitive_kind": "manual_upload"},
        mime_type="text/plain",
        size_bytes=40,
    )
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(asset.pk), "target_count": 1},
        format="json",
    )
    row = TranscriptHighlight.objects.get(
        pk=response.json()["highlights"][0]["id"]
    )

    approve_resp = client.post(
        f"/api/transcript_highlights/{row.pk}/approve/",
    )
    assert approve_resp.status_code == http.HTTP_400_BAD_REQUEST
    assert "realtime session" in str(approve_resp.content).lower()

    # Row is still PENDING — failed approve must not leave a
    # half-flipped state.
    row.refresh_from_db()
    assert row.status == TranscriptHighlight.Status.PENDING
    assert row.produced_composition is None


# ---- reject happy path -----------------------------------------


def test_reject_flips_to_rejected_with_reason() -> None:
    user, ws = _make_user_workspace("b14rej@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)

    response = client.post(
        f"/api/transcript_highlights/{highlight.pk}/reject/",
        {"rejection_reason": "off-brand tone"},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    highlight.refresh_from_db()
    assert highlight.status == TranscriptHighlight.Status.REJECTED
    assert highlight.rejection_reason == "off-brand tone"
    assert highlight.decided_at is not None
    assert highlight.produced_composition is None


def test_reject_without_reason_still_succeeds() -> None:
    user, ws = _make_user_workspace("b14norreason@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)

    response = client.post(
        f"/api/transcript_highlights/{highlight.pk}/reject/",
    )
    assert response.status_code == http.HTTP_200_OK
    highlight.refresh_from_db()
    assert highlight.status == TranscriptHighlight.Status.REJECTED
    assert highlight.rejection_reason == ""


# ---- state-machine guards --------------------------------------


def test_approve_already_approved_is_idempotent(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b14idem@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)

    response_one = client.post(f"/api/transcript_highlights/{highlight.pk}/approve/")
    assert response_one.status_code == http.HTTP_200_OK
    # Second approve — should be a no-op.
    response_two = client.post(f"/api/transcript_highlights/{highlight.pk}/approve/")
    assert response_two.status_code == http.HTTP_200_OK
    # Only fired once.
    assert _no_celery_dispatch.call_count == 1


def test_approve_rejected_row_returns_400() -> None:
    user, ws = _make_user_workspace("b14rejappr@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)

    client.post(f"/api/transcript_highlights/{highlight.pk}/reject/")
    response = client.post(f"/api/transcript_highlights/{highlight.pk}/approve/")
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_reject_approved_row_returns_400(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b14apprrej@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)
    client.post(f"/api/transcript_highlights/{highlight.pk}/approve/")

    response = client.post(f"/api/transcript_highlights/{highlight.pk}/reject/")
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_reject_already_rejected_is_idempotent() -> None:
    user, ws = _make_user_workspace("b14rejrej@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)

    r1 = client.post(f"/api/transcript_highlights/{highlight.pk}/reject/")
    r2 = client.post(f"/api/transcript_highlights/{highlight.pk}/reject/")
    assert r1.status_code == http.HTTP_200_OK
    assert r2.status_code == http.HTTP_200_OK


# ---- cross-workspace -------------------------------------------


def test_approve_cross_workspace_returns_404(_no_celery_dispatch) -> None:
    user_a, _ = _make_user_workspace("b14cwa@test")
    user_b, ws_b = _make_user_workspace("b14cwb@test")
    sp_b = _make_spokesperson(ws_b)
    transcript_b = _make_transcript_with_session(ws_b, sp_b)

    client = APIClient()
    _login(client, user_b)
    highlight = _mine_one(client, transcript_b)

    # Switch to user_a; try to approve user_b's highlight.
    _login(client, user_a)
    response = client.post(
        f"/api/transcript_highlights/{highlight.pk}/approve/",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND

    # State unchanged.
    highlight.refresh_from_db()
    assert highlight.status == TranscriptHighlight.Status.PENDING
    # And no Celery enqueue.
    _no_celery_dispatch.assert_not_called()


# ---- completion signal -----------------------------------------


def test_completion_signal_flips_approved_to_rendered(_no_celery_dispatch) -> None:
    """When the composition reaches status=COMPLETED, the
    transcripts post_save signal flips linked APPROVED rows
    to RENDERED. Validated by manually transitioning the
    composition (the real V2 runtime saves with the same
    update_fields shape)."""
    user, ws = _make_user_workspace("b14sig@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)
    client.post(f"/api/transcript_highlights/{highlight.pk}/approve/")
    highlight.refresh_from_db()

    comp = highlight.produced_composition
    assert comp is not None

    # Simulate V2 runtime's completion save.
    comp.status = CompositionStatus.COMPLETED
    comp.save(update_fields=["status"])

    highlight.refresh_from_db()
    assert highlight.status == TranscriptHighlight.Status.RENDERED


def test_completion_signal_skips_non_completion_saves(
    _no_celery_dispatch,
) -> None:
    """Intermediate composition saves (DRAFT → QUEUED →
    RUNNING) must NOT flip the highlight prematurely.
    Regression guard."""
    user, ws = _make_user_workspace("b14sigint@test")
    sp = _make_spokesperson(ws)
    transcript = _make_transcript_with_session(ws, sp)
    client = APIClient()
    _login(client, user)
    highlight = _mine_one(client, transcript)
    client.post(f"/api/transcript_highlights/{highlight.pk}/approve/")
    highlight.refresh_from_db()
    comp = highlight.produced_composition

    # Walk through intermediate statuses.
    for intermediate in (
        CompositionStatus.PLANNING,
        CompositionStatus.RUNNING,
    ):
        comp.status = intermediate
        comp.save(update_fields=["status"])
        highlight.refresh_from_db()
        assert highlight.status == TranscriptHighlight.Status.APPROVED


def test_completion_signal_ignores_compositions_without_highlight() -> None:
    """A vanilla talking_head_polished composition with no
    highlight FK should not blow up the signal handler."""
    user, ws = _make_user_workspace("b14signohl@test")
    sp = _make_spokesperson(ws)
    comp = Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="standalone",
        template_kind="talking_head_polished",
    )
    # Should not raise.
    comp.status = CompositionStatus.COMPLETED
    comp.save(update_fields=["status"])
