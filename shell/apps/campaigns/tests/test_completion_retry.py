"""B3.6 — completion signal + per-recipient retry.

Two surfaces:

* ``flip_recipient_on_composition_completion`` (post_save
  signal on Composition) — terminal composition status flips
  the linked recipient + rolls up the campaign.
* ``POST /api/campaigns/<id>/retry_recipient/`` — operator
  retries a FAILED recipient; creates a new Composition,
  enqueues Celery, flips campaign back to IN_FLIGHT if it
  was terminal.

Tests cover the state-machine transitions, idempotency, and
the cross-app rollup logic.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.campaigns.models import (
    PersonalizedCampaign,
    PersonalizedRecipient,
)
from apps.campaigns.services import rollup_campaign_status
from apps.compositions.models import Composition, CompositionStatus
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_celery_dispatch():
    with patch("apps.compositions.tasks.execute_composition.delay") as p:
        yield p


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name="Marcus", runway_avatar_id="av_marcus",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test.",
    )


def _make_launched_campaign(
    user, ws: Workspace, sp: Teammate, recipient_count: int = 3,
) -> PersonalizedCampaign:
    """Build an IN_FLIGHT campaign by simulating launch:
    each recipient is QUEUED with a fresh Composition row."""
    campaign = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp, name="Q3",
        template="Hi {first_name}, saw {company}!",
        placeholders=["first_name", "company"],
        status=PersonalizedCampaign.Status.IN_FLIGHT,
        created_by=user,
    )
    for idx in range(1, recipient_count + 1):
        comp = Composition.objects.create(
            workspace=ws, spokesperson=sp,
            name=f"Q3 — Recipient{idx}",
            template_kind="talking_head_polished",
            status=CompositionStatus.RUNNING,
        )
        PersonalizedRecipient.objects.create(
            campaign=campaign,
            variables={"first_name": f"Recipient{idx}", "company": f"Co{idx}"},
            label=f"Recipient{idx}",
            position=idx,
            rendered_script=f"Hi Recipient{idx}, saw Co{idx}!",
            status=PersonalizedRecipient.Status.QUEUED,
            produced_composition=comp,
        )
    return campaign


# ---- completion signal ------------------------------------------


def test_composition_completed_flips_recipient_to_completed() -> None:
    user, ws = _make_user_workspace("b36c@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=3)
    recipient = campaign.recipients.order_by("position").first()
    comp = recipient.produced_composition

    comp.status = CompositionStatus.COMPLETED
    comp.save(update_fields=["status"])

    recipient.refresh_from_db()
    assert recipient.status == PersonalizedRecipient.Status.COMPLETED
    assert recipient.error_message == ""


def test_composition_failed_flips_recipient_to_failed_with_error() -> None:
    user, ws = _make_user_workspace("b36f@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=2)
    recipient = campaign.recipients.first()
    comp = recipient.produced_composition

    comp.status = CompositionStatus.FAILED
    comp.error_message = "step 0 generate_avatar_speech: 500 from Runway"
    comp.save(update_fields=["status", "error_message"])

    recipient.refresh_from_db()
    assert recipient.status == PersonalizedRecipient.Status.FAILED
    assert "Runway" in recipient.error_message


def test_composition_partial_treated_as_failure() -> None:
    """PARTIAL means some steps succeeded but the whole
    pipeline didn't deliver a usable asset — treat as
    FAILED at the recipient level."""
    user, ws = _make_user_workspace("b36p@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=1)
    recipient = campaign.recipients.first()
    comp = recipient.produced_composition

    comp.status = CompositionStatus.PARTIAL
    comp.error_message = "step 1 add_captions: timeout"
    comp.save(update_fields=["status", "error_message"])

    recipient.refresh_from_db()
    assert recipient.status == PersonalizedRecipient.Status.FAILED


def test_signal_idempotent_on_already_terminal_recipient() -> None:
    """If a recipient is already FAILED (e.g. from launch-time
    render error), a later composition completion saves don't
    re-flip them."""
    user, ws = _make_user_workspace("b36idem@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=1)
    recipient = campaign.recipients.first()
    recipient.status = PersonalizedRecipient.Status.FAILED
    recipient.error_message = "render-time"
    recipient.save(update_fields=["status", "error_message"])

    comp = recipient.produced_composition
    comp.status = CompositionStatus.COMPLETED
    comp.save(update_fields=["status"])

    recipient.refresh_from_db()
    # Stays FAILED — already terminal, signal skips.
    assert recipient.status == PersonalizedRecipient.Status.FAILED
    assert recipient.error_message == "render-time"


def test_signal_skips_intermediate_composition_states() -> None:
    """Composition transitioning DRAFT → PLANNING → RUNNING
    leaves the recipient alone."""
    user, ws = _make_user_workspace("b36int@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=1)
    recipient = campaign.recipients.first()
    comp = recipient.produced_composition

    for intermediate in (
        CompositionStatus.PLANNING, CompositionStatus.RUNNING,
    ):
        comp.status = intermediate
        comp.save(update_fields=["status"])
        recipient.refresh_from_db()
        assert recipient.status == PersonalizedRecipient.Status.QUEUED


# ---- campaign rollup --------------------------------------------


def test_rollup_all_completed_flips_campaign_to_completed() -> None:
    user, ws = _make_user_workspace("b36rcomp@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=3)

    for r in campaign.recipients.all():
        comp = r.produced_composition
        comp.status = CompositionStatus.COMPLETED
        comp.save(update_fields=["status"])

    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.COMPLETED
    assert campaign.completed_at is not None


def test_rollup_mixed_flips_campaign_to_partial() -> None:
    user, ws = _make_user_workspace("b36rpart@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=3)

    recipients = list(campaign.recipients.order_by("position"))
    # 2 succeed, 1 fails.
    recipients[0].produced_composition.status = CompositionStatus.COMPLETED
    recipients[0].produced_composition.save(update_fields=["status"])
    recipients[1].produced_composition.status = CompositionStatus.COMPLETED
    recipients[1].produced_composition.save(update_fields=["status"])
    recipients[2].produced_composition.status = CompositionStatus.FAILED
    recipients[2].produced_composition.save(update_fields=["status"])

    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.PARTIAL


def test_rollup_all_failed_flips_campaign_to_failed() -> None:
    user, ws = _make_user_workspace("b36rfail@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=2)

    for r in campaign.recipients.all():
        comp = r.produced_composition
        comp.status = CompositionStatus.FAILED
        comp.save(update_fields=["status"])

    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.FAILED


def test_rollup_does_not_flip_while_recipients_pending() -> None:
    user, ws = _make_user_workspace("b36rwait@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=3)

    # Only 1 of 3 completes.
    first = campaign.recipients.first()
    first.produced_composition.status = CompositionStatus.COMPLETED
    first.produced_composition.save(update_fields=["status"])

    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.IN_FLIGHT


def test_rollup_helper_returns_false_when_no_change() -> None:
    """Idempotency: calling rollup on a stable campaign
    doesn't write."""
    user, ws = _make_user_workspace("b36rstable@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=2)

    # Nothing has completed yet.
    assert rollup_campaign_status(campaign) is False


# ---- retry endpoint ---------------------------------------------


def test_retry_failed_recipient_creates_new_composition(
    _no_celery_dispatch,
) -> None:
    user, ws = _make_user_workspace("b36retry@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=1)
    recipient = campaign.recipients.first()
    failed_comp = recipient.produced_composition
    failed_comp.status = CompositionStatus.FAILED
    failed_comp.error_message = "transient"
    failed_comp.save(update_fields=["status", "error_message"])
    recipient.refresh_from_db()
    assert recipient.status == PersonalizedRecipient.Status.FAILED

    client = APIClient()
    _login(client, user)

    response = client.post(
        f"/api/campaigns/{campaign.pk}/retry_recipient/",
        {"recipient_id": str(recipient.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content

    recipient.refresh_from_db()
    assert recipient.status == PersonalizedRecipient.Status.QUEUED
    assert recipient.error_message == ""
    # New composition, not the failed one.
    assert recipient.produced_composition_id != failed_comp.pk
    assert recipient.produced_composition.status != CompositionStatus.FAILED
    # Failed composition stays for audit (Q-c-6).
    assert Composition.objects.filter(pk=failed_comp.pk).exists()
    # Celery enqueued.
    _no_celery_dispatch.assert_called_once_with(
        str(recipient.produced_composition.pk),
    )


def test_retry_flips_terminal_campaign_back_to_in_flight(
    _no_celery_dispatch,
) -> None:
    """If the campaign was COMPLETED / PARTIAL / FAILED and
    the operator retries a recipient, the campaign goes back
    to IN_FLIGHT and completed_at clears."""
    user, ws = _make_user_workspace("b36retrycamp@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=2)

    # Flip everything to terminal: 1 success, 1 fail → PARTIAL.
    rs = list(campaign.recipients.order_by("position"))
    rs[0].produced_composition.status = CompositionStatus.COMPLETED
    rs[0].produced_composition.save(update_fields=["status"])
    rs[1].produced_composition.status = CompositionStatus.FAILED
    rs[1].produced_composition.save(update_fields=["status"])
    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.PARTIAL
    assert campaign.completed_at is not None

    client = APIClient()
    _login(client, user)
    rs[1].refresh_from_db()
    response = client.post(
        f"/api/campaigns/{campaign.pk}/retry_recipient/",
        {"recipient_id": str(rs[1].pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK

    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.IN_FLIGHT
    assert campaign.completed_at is None


def test_retry_non_failed_recipient_returns_400(
    _no_celery_dispatch,
) -> None:
    """PENDING / QUEUED / RUNNING / COMPLETED are all
    non-retryable — only FAILED."""
    user, ws = _make_user_workspace("b36nofail@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=1)
    recipient = campaign.recipients.first()
    # Recipient is QUEUED — not retryable.
    assert recipient.status == PersonalizedRecipient.Status.QUEUED

    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/campaigns/{campaign.pk}/retry_recipient/",
        {"recipient_id": str(recipient.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    _no_celery_dispatch.assert_not_called()


def test_retry_missing_recipient_id_returns_400(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b36noid@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=1)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/campaigns/{campaign.pk}/retry_recipient/",
        {},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_retry_unknown_recipient_returns_404(_no_celery_dispatch) -> None:
    import uuid
    user, ws = _make_user_workspace("b36unk@test")
    sp = _make_teammate(ws)
    campaign = _make_launched_campaign(user, ws, sp, recipient_count=1)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/campaigns/{campaign.pk}/retry_recipient/",
        {"recipient_id": str(uuid.uuid4())},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_retry_cross_workspace_returns_404(_no_celery_dispatch) -> None:
    user_a, _ = _make_user_workspace("b36cwa@test")
    user_b, ws_b = _make_user_workspace("b36cwb@test")
    sp_b = _make_teammate(ws_b)
    campaign = _make_launched_campaign(user_b, ws_b, sp_b, recipient_count=1)
    recipient = campaign.recipients.first()
    recipient.produced_composition.status = CompositionStatus.FAILED
    recipient.produced_composition.save(update_fields=["status"])

    client = APIClient()
    _login(client, user_a)
    response = client.post(
        f"/api/campaigns/{campaign.pk}/retry_recipient/",
        {"recipient_id": str(recipient.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND
    _no_celery_dispatch.assert_not_called()
