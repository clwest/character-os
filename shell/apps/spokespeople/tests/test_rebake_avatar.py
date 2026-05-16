"""W11.2 + SESSION 171 — ``POST /api/spokespeople/<id>/rebake-avatar/``.

SESSION 170 shipped the rebake action but landed without test
coverage ("actions live-exercised SESSION 171 pending"). The
operator's first real-Runway dogfood surfaced a bug: the rebake
hardcoded ``template = "coach"`` as the default if the request
body didn't include one. That silently flipped Marcus from the
``mascot`` template (stylized battle unicorn) to ``coach``
(photorealistic human).

Root cause: ``Spokesperson`` didn't persist ``visual_template``,
so the action had nothing to fall back to and used a careless
hardcoded default. SESSION 171 added the field + migration +
backfill + flipped the rebake default to ``spokesperson.visual_template``.

These tests lock the fix so a future refactor can't regress the
"coach" default back in.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    AvatarCreateResult,
    PortraitCreateResult,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_workspace(email: str) -> tuple[Workspace, "User"]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws, user


def _make_spokesperson(
    ws: Workspace,
    *,
    name: str = "Marcus",
    visual_template: str = "mascot",
    visual_subject: str = "battle unicorn in lorica segmentata",
    voice_id: str = "marcus",
    runway_avatar_id: str = "av_old_123",
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws,
        name=name,
        visual_template=visual_template,
        visual_subject=visual_subject,
        voice_id=voice_id,
        runway_avatar_id=runway_avatar_id,
        runway_avatar_status="ready",
    )


def _patched_client(
    portrait_template: str = "mascot",
    avatar_id: str = "av_new_456",
) -> tuple[MagicMock, MagicMock]:
    """Patch ``MediaEngineClient`` used by the rebake action so
    we can assert what template + subject got threaded through to
    media-engine without firing real Runway."""
    fake_client = MagicMock()
    fake_client.create_portrait.return_value = PortraitCreateResult(
        portrait_data_uri="data:image/png;base64,fake",
        template=portrait_template,
        prompt="(mock prompt)",
        mock_mode=True,
    )
    fake_client.create_avatar.return_value = AvatarCreateResult(
        avatar_id=avatar_id,
        status="ready",
        thumbnail_url="https://runway/thumb.png",
        mock_mode=True,
    )
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False
    return cm, fake_client


def test_rebake_without_template_body_uses_spokesperson_visual_template():
    """SESSION 171 fix — when the request body omits ``template``,
    the action MUST use ``spokesperson.visual_template`` (not the
    hardcoded ``"coach"`` from W11.2).

    Marcus's row has ``visual_template="mascot"``. A bodyless rebake
    must thread ``"mascot"`` into ``create_portrait`` so Marcus comes
    back as a battle unicorn, not a photorealistic human.
    """
    ws, user = _make_workspace("rebake1@test")
    sp = _make_spokesperson(ws, visual_template="mascot")
    client = APIClient()
    client.force_authenticate(user)

    cm, fake = _patched_client()
    with patch(
        "apps.spokespeople.views.MediaEngineClient", return_value=cm,
    ):
        resp = client.post(
            f"/api/spokespeople/{sp.id}/rebake-avatar/", data={}, format="json",
        )

    assert resp.status_code == http.HTTP_200_OK, resp.json()
    # The action MUST have called create_portrait with the row's
    # template, not "coach".
    fake.create_portrait.assert_called_once()
    _, kwargs = fake.create_portrait.call_args
    assert kwargs["template"] == "mascot"
    assert kwargs["subject"] == "battle unicorn in lorica segmentata"


def test_rebake_template_body_override_wins_and_persists():
    """Explicit body ``template`` still wins over the row's value,
    and the new choice is persisted back to the row so the next
    rebake defaults to the operator's most recent intent.
    """
    ws, user = _make_workspace("rebake2@test")
    sp = _make_spokesperson(ws, visual_template="mascot")
    client = APIClient()
    client.force_authenticate(user)

    cm, fake = _patched_client(portrait_template="coach")
    with patch(
        "apps.spokespeople.views.MediaEngineClient", return_value=cm,
    ):
        resp = client.post(
            f"/api/spokespeople/{sp.id}/rebake-avatar/",
            data={"template": "coach"},
            format="json",
        )

    assert resp.status_code == http.HTTP_200_OK, resp.json()
    _, kwargs = fake.create_portrait.call_args
    assert kwargs["template"] == "coach"

    sp.refresh_from_db()
    assert sp.visual_template == "coach"


def test_rebake_invalid_template_rejected():
    """Validation belt-and-braces — a body template not in
    ``SUPPORTED_PORTRAIT_TEMPLATES`` raises 400 before any
    media-engine call fires.
    """
    ws, user = _make_workspace("rebake3@test")
    sp = _make_spokesperson(ws, visual_template="mascot")
    client = APIClient()
    client.force_authenticate(user)

    cm, fake = _patched_client()
    with patch(
        "apps.spokespeople.views.MediaEngineClient", return_value=cm,
    ):
        resp = client.post(
            f"/api/spokespeople/{sp.id}/rebake-avatar/",
            data={"template": "bogus_template"},
            format="json",
        )

    assert resp.status_code == http.HTTP_400_BAD_REQUEST
    fake.create_portrait.assert_not_called()


def test_rebake_persists_row_intent_before_media_engine_call():
    """The action persists visual_subject + voice_preset +
    visual_template upfront, so a media-engine failure still
    leaves the row carrying the operator's intent for the next
    rebake attempt.
    """
    ws, user = _make_workspace("rebake4@test")
    sp = _make_spokesperson(ws, visual_template="mascot", voice_id="marcus")
    client = APIClient()
    client.force_authenticate(user)

    cm, fake = _patched_client()
    with patch(
        "apps.spokespeople.views.MediaEngineClient", return_value=cm,
    ):
        resp = client.post(
            f"/api/spokespeople/{sp.id}/rebake-avatar/",
            data={
                "template": "founder",
                "voice_preset": "clara",
                "visual_subject": "donkey in a hoodie",
            },
            format="json",
        )

    assert resp.status_code == http.HTTP_200_OK, resp.json()
    sp.refresh_from_db()
    assert sp.visual_template == "founder"
    assert sp.voice_id == "clara"
    assert sp.visual_subject == "donkey in a hoodie"


def test_create_persists_visual_template_from_payload():
    """Sanity check on the wizard's create payload — the new
    ``visual_template`` field round-trips through the serializer
    onto the row. Pre-SESSION 171 the wizard collected this but
    didn't send it; the serializer didn't expose it.
    """
    ws, user = _make_workspace("create-vt@test")
    client = APIClient()
    client.force_authenticate(user)

    resp = client.post(
        "/api/spokespeople/",
        data={
            "workspace": str(ws.id),
            "name": "Test Mascot",
            "business_brief": "...",
            "visual_subject": "test subject",
            "visual_template": "local_guide",
            "tone_archetype": "expert",
        },
        format="json",
    )
    assert resp.status_code == http.HTTP_201_CREATED, resp.json()
    sp = Spokesperson.objects.get(pk=resp.json()["id"])
    assert sp.visual_template == "local_guide"


def test_create_defaults_visual_template_to_mascot_when_omitted():
    """Omitting ``visual_template`` falls back to the model
    default ``mascot`` — matches the seed cast + Marcus's
    original choice.
    """
    ws, user = _make_workspace("create-vt-default@test")
    client = APIClient()
    client.force_authenticate(user)

    resp = client.post(
        "/api/spokespeople/",
        data={
            "workspace": str(ws.id),
            "name": "Default Template",
            "business_brief": "...",
            "tone_archetype": "expert",
        },
        format="json",
    )
    assert resp.status_code == http.HTTP_201_CREATED, resp.json()
    sp = Spokesperson.objects.get(pk=resp.json()["id"])
    assert sp.visual_template == "mascot"
