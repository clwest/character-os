"""Personality propagation to Runway (W11.y follow-up).

W11.y split `personality` out of `business_brief` locally but
left the Runway-side avatar personality stale (baked at avatar-
create time). The session-create override (R-arc) covers the
realtime surface; this slice adds a post_save signal +
`sync_personality_to_runway` Celery task so non-session-create
surfaces (recipe renders that call avatar_videos directly,
future polish flows) inherit the same persona without a manual
push.

These tests cover the signal-fires-task wiring and the task's
status branches. They patch `MediaEngineClient` to avoid hitting
real network during the suite.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Spokesperson
from apps.spokespeople.tasks import sync_personality_to_runway
from character_os.clients.media_engine import MediaEngineError

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_workspace(email: str) -> tuple[Workspace, "User"]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, user


def _make_spokesperson(ws: Workspace, *, runway_avatar_id: str = "av_1") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws,
        name="Test Person",
        business_brief="WHAT they do.",
        personality="HOW they sound — original.",
        runway_avatar_id=runway_avatar_id,
    )


# ---- task ----------------------------------------------------------


def test_task_no_avatar_short_circuits() -> None:
    ws, _ = _make_workspace("nosync-noavatar@test")
    sp = Spokesperson.objects.create(
        workspace=ws, name="X", personality="some content",
    )
    result = sync_personality_to_runway.apply(args=[str(sp.pk)]).get()
    assert result["status"] == "no_avatar"


def test_task_empty_personality_short_circuits() -> None:
    ws, _ = _make_workspace("nosync-empty@test")
    sp = _make_spokesperson(ws)
    sp.personality = ""
    sp.save(update_fields=["personality"])
    result = sync_personality_to_runway.apply(args=[str(sp.pk)]).get()
    assert result["status"] == "empty"


def test_task_pushes_to_media_engine() -> None:
    ws, _ = _make_workspace("nosync-push@test")
    sp = _make_spokesperson(ws)
    fake = MagicMock()
    fake.change_avatar_personality.return_value = {
        "avatar_id": sp.runway_avatar_id,
        "status": "applied",
        "error": None,
        "mock_mode": False,
    }
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.spokespeople.tasks.MediaEngineClient", return_value=cm,
    ):
        result = sync_personality_to_runway.apply(args=[str(sp.pk)]).get()
    assert result["status"] == "applied"
    fake.change_avatar_personality.assert_called_once_with(
        avatar_id=sp.runway_avatar_id,
        personality="HOW they sound — original.",
    )


def test_task_upstream_error_surfaces() -> None:
    ws, _ = _make_workspace("nosync-err@test")
    sp = _make_spokesperson(ws)
    fake = MagicMock()
    fake.change_avatar_personality.side_effect = MediaEngineError(
        "PATCH /internal/avatars/av_1/change-personality/ returned 502",
        status_code=502,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.spokespeople.tasks.MediaEngineClient", return_value=cm,
    ):
        result = sync_personality_to_runway.apply(args=[str(sp.pk)]).get()
    assert result["status"] == "upstream_error"
    assert "502" in result["error"]


# ---- signal --------------------------------------------------------


def test_signal_fires_task_on_personality_change() -> None:
    """Editing personality on an existing row with a
    runway_avatar_id schedules a `sync_personality_to_runway`
    task via `transaction.on_commit`. We patch both `on_commit`
    (test wrapping transaction never commits) and the task's
    `.delay` to verify the enqueue chain end-to-end without
    actually running the task body."""
    ws, _ = _make_workspace("signal-fires@test")
    sp = _make_spokesperson(ws)
    captured: list = []
    with patch(
        "apps.spokespeople.signals.transaction.on_commit",
        side_effect=lambda fn: captured.append(fn),
    ), patch(
        "apps.spokespeople.tasks.sync_personality_to_runway.delay",
    ) as delay_mock:
        sp.personality = "HOW they sound — newly edited!"
        sp.save(update_fields=["personality"])
        assert len(captured) == 1, "expected one on_commit callback"
        # Fire the captured callback explicitly — equivalent to a
        # real DB commit firing the registered hook.
        captured[0]()
    delay_mock.assert_called_once_with(str(sp.pk))


def test_signal_skips_when_personality_unchanged() -> None:
    ws, _ = _make_workspace("signal-noop@test")
    sp = _make_spokesperson(ws)
    fake = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.spokespeople.tasks.MediaEngineClient", return_value=cm,
    ):
        # Save without changing personality.
        sp.name = "Renamed"
        sp.save(update_fields=["name"])
    fake.change_avatar_personality.assert_not_called()


def test_signal_skips_when_no_avatar() -> None:
    ws, _ = _make_workspace("signal-no-avatar@test")
    sp = Spokesperson.objects.create(
        workspace=ws, name="No Avatar", personality="something",
    )
    fake = MagicMock()
    cm = MagicMock()
    cm.__enter__.return_value = fake
    cm.__exit__.return_value = False
    with patch(
        "apps.spokespeople.tasks.MediaEngineClient", return_value=cm,
    ):
        sp.personality = "changed"
        sp.save(update_fields=["personality"])
    fake.change_avatar_personality.assert_not_called()
