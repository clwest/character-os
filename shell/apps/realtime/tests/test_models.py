"""R1 schema tests — RealtimeSession + RealtimeToolInvocation.

Mirrors V1's `test_models.py` shape. Covers:

* Happy-path session create with the workspace anchor.
* Cross-workspace spokesperson on session → ValidationError
  via `clean()` AND via the pre_save signal (defense in
  depth — both paths fire).
* Cross-workspace thread → ValidationError.
* Cross-workspace transcript_asset → ValidationError.
* Tool invocation cross-workspace produced_asset / composition
  → ValidationError.
* State-only updates (status / cost / timestamps) don't re-
  trigger the cross-workspace check — the V1 pattern of
  `update_fields`-based skipping carries over.
* PROTECT semantics on `spokesperson`: deleting a
  spokesperson with active sessions raises ProtectedError.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.models import ProtectedError
from django.utils import timezone

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType, Composition, CompositionStatus
from apps.conversations.models import ConversationThread
from apps.realtime.models import (
    RealtimeSession,
    RealtimeToolInvocation,
)
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- helpers -----------------------------------------------------


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_spokesperson(ws: Workspace, name: str = "Sp") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id="av",
        portrait_path="https://fake/p.png", business_brief="b",
    )


def _make_asset(ws: Workspace, asset_type: str = AssetType.CLIP) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=asset_type,
        file_path="/data/x.mp4", duration_ms=5000,
    )


# ---- happy path -------------------------------------------------


def test_create_session_minimal() -> None:
    ws, _u = _make_workspace("r1min@test")
    sp = _make_spokesperson(ws)
    session = RealtimeSession.objects.create(workspace=ws, spokesperson=sp)
    assert session.status == RealtimeSession.Status.DRAFT
    assert session.provider == RealtimeSession.Provider.RUNWAY
    assert session.knowledge_chunk_ids == []
    assert session.mock_mode is False


def test_session_links_to_conversation_thread() -> None:
    ws, _u = _make_workspace("r1thread@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    session = RealtimeSession.objects.create(
        workspace=ws, spokesperson=sp, thread=thread,
    )
    assert session.thread_id == thread.pk


# ---- cross-workspace rejection: spokesperson ---------------------


def test_clean_rejects_cross_workspace_spokesperson() -> None:
    ws_a, _u = _make_workspace("r1xspa@test", "A")
    ws_b, _u2 = _make_workspace("r1xspb@test", "B")
    foreign_sp = _make_spokesperson(ws_b)
    session = RealtimeSession(workspace=ws_a, spokesperson=foreign_sp)
    with pytest.raises(ValidationError, match="spokesperson"):
        session.full_clean()


def test_signal_rejects_cross_workspace_spokesperson_on_raw_save() -> None:
    """The pre_save signal must catch the cross-workspace case
    even when `clean()` isn't called explicitly (the raw
    `.save()` path)."""
    ws_a, _u = _make_workspace("r1xsps@test", "A")
    ws_b, _u2 = _make_workspace("r1xsps2@test", "B")
    foreign_sp = _make_spokesperson(ws_b)
    with pytest.raises(ValidationError, match="spokesperson"):
        RealtimeSession.objects.create(
            workspace=ws_a, spokesperson=foreign_sp,
        )


# ---- cross-workspace rejection: thread --------------------------


def test_clean_rejects_cross_workspace_thread() -> None:
    ws_a, _u = _make_workspace("r1xth@test", "A")
    ws_b, _u2 = _make_workspace("r1xthb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    foreign_sp = _make_spokesperson(ws_b)
    foreign_thread = ConversationThread.objects.create(spokesperson=foreign_sp)
    session = RealtimeSession(
        workspace=ws_a, spokesperson=sp_a, thread=foreign_thread,
    )
    with pytest.raises(ValidationError, match="thread"):
        session.full_clean()


def test_signal_rejects_cross_workspace_thread_on_raw_save() -> None:
    ws_a, _u = _make_workspace("r1xths@test", "A")
    ws_b, _u2 = _make_workspace("r1xthsb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    foreign_sp = _make_spokesperson(ws_b)
    foreign_thread = ConversationThread.objects.create(spokesperson=foreign_sp)
    with pytest.raises(ValidationError, match="thread"):
        RealtimeSession.objects.create(
            workspace=ws_a, spokesperson=sp_a, thread=foreign_thread,
        )


# ---- cross-workspace rejection: transcript_asset ---------------


def test_clean_rejects_cross_workspace_transcript_asset() -> None:
    ws_a, _u = _make_workspace("r1xta@test", "A")
    ws_b, _u2 = _make_workspace("r1xtab@test", "B")
    sp_a = _make_spokesperson(ws_a)
    foreign_asset = _make_asset(ws_b, asset_type=AssetType.TRANSCRIPT)
    session = RealtimeSession(
        workspace=ws_a, spokesperson=sp_a, transcript_asset=foreign_asset,
    )
    with pytest.raises(ValidationError, match="transcript_asset"):
        session.full_clean()


def test_signal_rejects_cross_workspace_transcript_on_raw_save() -> None:
    ws_a, _u = _make_workspace("r1xts@test", "A")
    ws_b, _u2 = _make_workspace("r1xtsb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    foreign_asset = _make_asset(ws_b, asset_type=AssetType.TRANSCRIPT)
    with pytest.raises(ValidationError, match="transcript_asset"):
        RealtimeSession.objects.create(
            workspace=ws_a, spokesperson=sp_a, transcript_asset=foreign_asset,
        )


# ---- state-only updates don't re-trigger validation ------------


def test_state_only_update_does_not_re_validate() -> None:
    """The V1 pattern of `update_fields`-based skipping carries
    over. Status / timestamp / cost updates should NOT re-fire
    the cross-workspace check — they leave the FK shape
    unchanged."""
    ws, _u = _make_workspace("r1state@test")
    sp = _make_spokesperson(ws)
    session = RealtimeSession.objects.create(workspace=ws, spokesperson=sp)

    # Bump status + a couple of timestamps + cost. This is the
    # shape the R3 broker will use repeatedly during a live
    # session. None of these touch a FK field, so the signal
    # short-circuits.
    session.status = RealtimeSession.Status.READY
    session.ready_at = timezone.now()
    session.cost_actual_micros = 12_345
    session.save(update_fields=[
        "status", "ready_at", "cost_actual_micros", "updated_at",
    ])
    session.refresh_from_db()
    assert session.status == RealtimeSession.Status.READY
    assert session.cost_actual_micros == 12_345


# ---- PROTECT semantics ------------------------------------------


def test_spokesperson_protected_while_sessions_exist() -> None:
    """Deleting a spokesperson with active sessions must raise
    ProtectedError — same shape as Composition.spokesperson."""
    ws, _u = _make_workspace("r1prot@test")
    sp = _make_spokesperson(ws)
    RealtimeSession.objects.create(workspace=ws, spokesperson=sp)
    with pytest.raises(ProtectedError):
        sp.delete()


# ---- tool invocation cross-workspace -----------------------------


def test_tool_invocation_clean_rejects_cross_workspace_asset() -> None:
    ws_a, _u = _make_workspace("r1toolxa@test", "A")
    ws_b, _u2 = _make_workspace("r1toolxb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    session = RealtimeSession.objects.create(workspace=ws_a, spokesperson=sp_a)
    foreign_asset = _make_asset(ws_b)
    invocation = RealtimeToolInvocation(
        session=session,
        tool_name="render_video",
        produced_asset=foreign_asset,
    )
    with pytest.raises(ValidationError, match="produced_asset"):
        invocation.full_clean()


def test_tool_invocation_signal_rejects_cross_workspace_composition() -> None:
    ws_a, _u = _make_workspace("r1toolxc@test", "A")
    ws_b, _u2 = _make_workspace("r1toolxd@test", "B")
    sp_a = _make_spokesperson(ws_a)
    sp_b = _make_spokesperson(ws_b)
    session = RealtimeSession.objects.create(workspace=ws_a, spokesperson=sp_a)
    foreign_comp = Composition.objects.create(
        workspace=ws_b, spokesperson=sp_b, name="t",
        template_kind="talking_head", status=CompositionStatus.COMPLETED,
    )
    with pytest.raises(ValidationError, match="produced_composition"):
        RealtimeToolInvocation.objects.create(
            session=session,
            tool_name="render_video",
            produced_composition=foreign_comp,
        )


def test_tool_invocation_same_workspace_asset_ok() -> None:
    ws, _u = _make_workspace("r1toolok@test")
    sp = _make_spokesperson(ws)
    session = RealtimeSession.objects.create(workspace=ws, spokesperson=sp)
    asset = _make_asset(ws)
    invocation = RealtimeToolInvocation.objects.create(
        session=session,
        tool_name="render_video",
        produced_asset=asset,
        status=RealtimeToolInvocation.Status.SUCCEEDED,
    )
    assert invocation.status == RealtimeToolInvocation.Status.SUCCEEDED
