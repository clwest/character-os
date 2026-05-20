"""B3.5 — forecast + launch endpoint tests + tier-gate
composition logic.

Covers:

* ``forecast`` — happy path, no recipients blocker,
  over-batch-cap blocker, over-month-cap blocker, non-DRAFT
  blocker. Never raises.
* ``launch`` — happy path (recipients flip to QUEUED,
  compositions created, status flips to IN_FLIGHT, Celery
  enqueued); over-batch-cap → 402; over-month-cap → 402;
  no recipients → 400; non-DRAFT → 409; per-recipient render
  failure flips that row to FAILED but others continue
  (rule 8); all-render-fail short-circuits campaign to
  FAILED.
* ``check_personalized_batch`` helper unit-tested for both
  gate dimensions.
* ``estimate_campaign_cost_micros`` helper sanity-checked.

Celery dispatch is patched so tests don't depend on a
running broker.
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.billing.services import TierLimitExceeded
from apps.campaigns.cost import (
    PER_RECIPIENT_COST_MICROS,
    estimate_campaign_cost_micros,
)
from apps.campaigns.models import (
    PersonalizedCampaign,
    PersonalizedRecipient,
)
from apps.campaigns.services import check_personalized_batch
from apps.compositions.models import Composition, CompositionStatus
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- fixtures ---------------------------------------------------


@pytest.fixture(autouse=True)
def _no_celery_dispatch():
    """Launch fires execute_composition.delay — patch so tests
    don't need a broker."""
    with patch("apps.compositions.tasks.execute_composition.delay") as p:
        yield p


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_spokesperson(ws: Workspace, name: str = "Marcus") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test.",
    )


def _make_draft_with_recipients(
    user, ws: Workspace, sp: Spokesperson, recipient_count: int = 3,
) -> PersonalizedCampaign:
    """Build a DRAFT campaign with N PENDING recipients via
    direct ORM (skips the REST round-trip)."""
    campaign = PersonalizedCampaign.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="Q3 outreach",
        template="Hi {first_name}, saw {company}!",
        placeholders=["first_name", "company"],
        created_by=user,
    )
    for idx in range(1, recipient_count + 1):
        PersonalizedRecipient.objects.create(
            campaign=campaign,
            variables={
                "first_name": f"Recipient{idx}",
                "company": f"Co{idx}",
            },
            label=f"Recipient{idx}",
            position=idx,
        )
    return campaign


# ---- estimate_campaign_cost_micros ------------------------------


def test_cost_estimate_scales_linearly() -> None:
    assert estimate_campaign_cost_micros(0) == 0
    assert estimate_campaign_cost_micros(1) == PER_RECIPIENT_COST_MICROS
    assert estimate_campaign_cost_micros(10) == 10 * PER_RECIPIENT_COST_MICROS


def test_cost_estimate_negative_clamps_to_zero() -> None:
    assert estimate_campaign_cost_micros(-5) == 0


# ---- check_personalized_batch (helper unit tests) ---------------


def test_check_personalized_batch_under_cap_passes() -> None:
    """Starter workspace, batch=3, under cap=5 — no raise."""
    _, ws = _make_user_workspace("b35chkok@test")
    # Should not raise.
    check_personalized_batch(ws, 3)


def test_check_personalized_batch_over_batch_cap_raises() -> None:
    """Starter cap=5; asking for 10 → personalized_batch_too_large."""
    _, ws = _make_user_workspace("b35chkbatch@test")
    with pytest.raises(TierLimitExceeded) as exc:
        check_personalized_batch(ws, 10)
    assert exc.value.payload["code"] == "personalized_batch_too_large"
    assert exc.value.payload["batch_cap"] == 5
    assert exc.value.payload["recipient_count"] == 10


def test_check_personalized_batch_under_batch_but_over_month_raises() -> None:
    """Batch=5 fits the per-batch cap but pushes
    videos_used + 5 past the per-month cap → 402.

    SESSION 204 migration: get_usage() now counts Composition
    rows (excluding DRAFT). Seed completed Compositions to
    exercise the per-month gate."""
    _, ws = _make_user_workspace("b35chkmonth@test")
    sp = _make_spokesperson(ws)
    for _ in range(8):
        Composition.objects.create(
            workspace=ws, spokesperson=sp, name="x",
            template_kind="talking_head_polished",
            status=CompositionStatus.COMPLETED,
        )
    with pytest.raises(TierLimitExceeded) as exc:
        check_personalized_batch(ws, 5)
    assert exc.value.payload["code"] == "video_limit_reached"
    assert exc.value.payload["videos_used"] == 8
    assert exc.value.payload["videos_limit"] == 10


def test_check_personalized_batch_zero_recipients_is_noop() -> None:
    """An empty batch never trips the gates; caller (launch
    endpoint) returns 400 separately on the no-recipients
    state."""
    _, ws = _make_user_workspace("b35chk0@test")
    check_personalized_batch(ws, 0)  # no raise


# ---- forecast endpoint ------------------------------------------


def test_forecast_happy_path() -> None:
    user, ws = _make_user_workspace("b35fc@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=3)
    client = APIClient()
    _login(client, user)

    response = client.get(f"/api/campaigns/{campaign.pk}/forecast/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["recipient_count"] == 3
    assert data["batch_cap"] == 5  # Starter default
    assert data["projected_cost_micros"] == 3 * PER_RECIPIENT_COST_MICROS
    assert data["per_recipient_cost_micros"] == PER_RECIPIENT_COST_MICROS
    assert data["ready_to_launch"] is True
    assert data["blocking_reason"] is None


def test_forecast_no_recipients_blocks() -> None:
    user, ws = _make_user_workspace("b35fcempty@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=0)
    client = APIClient()
    _login(client, user)

    response = client.get(f"/api/campaigns/{campaign.pk}/forecast/")
    data = response.json()
    assert data["ready_to_launch"] is False
    assert data["blocking_reason"]["code"] == "no_recipients"
    assert data["recipient_count"] == 0


def test_forecast_over_batch_cap_blocks_without_raising() -> None:
    """Starter cap=5; create 6 PENDING recipients → forecast
    surfaces personalized_batch_too_large as blocking_reason
    (HTTP 200, not 402 — forecast is read-only)."""
    user, ws = _make_user_workspace("b35fcbig@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=6)
    client = APIClient()
    _login(client, user)

    response = client.get(f"/api/campaigns/{campaign.pk}/forecast/")
    assert response.status_code == http.HTTP_200_OK
    data = response.json()
    assert data["ready_to_launch"] is False
    assert data["blocking_reason"]["code"] == "personalized_batch_too_large"


def test_forecast_non_draft_blocks() -> None:
    user, ws = _make_user_workspace("b35fcnd@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=2)
    campaign.status = PersonalizedCampaign.Status.IN_FLIGHT
    campaign.save(update_fields=["status"])
    client = APIClient()
    _login(client, user)

    response = client.get(f"/api/campaigns/{campaign.pk}/forecast/")
    data = response.json()
    assert data["ready_to_launch"] is False
    assert data["blocking_reason"]["code"] == "campaign_not_draft"


# ---- launch endpoint --------------------------------------------


def test_launch_happy_path_creates_compositions_and_enqueues(
    _no_celery_dispatch,
) -> None:
    """End-to-end: campaign DRAFT → LAUNCHING → IN_FLIGHT,
    every recipient gets a Composition + status=QUEUED,
    Celery enqueued once per recipient."""
    user, ws = _make_user_workspace("b35lh@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=3)
    client = APIClient()
    _login(client, user)

    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == http.HTTP_200_OK, response.content
    body = response.json()
    assert body["queued_count"] == 3
    assert body["failed_at_render_count"] == 0
    assert body["campaign"]["status"] == "in_flight"

    # DB state matches.
    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.IN_FLIGHT
    assert campaign.launched_at is not None

    recipients = list(campaign.recipients.order_by("position"))
    assert all(
        r.status == PersonalizedRecipient.Status.QUEUED for r in recipients
    )
    assert all(r.produced_composition_id is not None for r in recipients)
    assert all(
        r.produced_composition.workspace_id == ws.pk for r in recipients
    )
    # Compositions carry the template's substituted script.
    for r in recipients:
        comp = r.produced_composition
        speech_step = comp.steps.filter(
            primitive="generate_avatar_speech",
        ).first()
        assert speech_step is not None
        assert r.variables["first_name"] in speech_step.params["script"]

    # Celery enqueued once per recipient.
    assert _no_celery_dispatch.call_count == 3


def test_launch_composition_name_carries_provenance(_no_celery_dispatch) -> None:
    """Rule 9 — composition.name = `{campaign.name} — {recipient.label}`."""
    user, ws = _make_user_workspace("b35name@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=2)
    client = APIClient()
    _login(client, user)
    client.post(f"/api/campaigns/{campaign.pk}/launch/")

    for r in campaign.recipients.all():
        assert r.produced_composition.name.startswith(
            f"{campaign.name} — {r.label}"
        )


def test_launch_per_recipient_render_failure_flips_row_others_continue(
    _no_celery_dispatch,
) -> None:
    """Rule 8: one recipient missing a required variable
    flips JUST that row to FAILED; the others ship."""
    user, ws = _make_user_workspace("b35failrow@test")
    sp = _make_spokesperson(ws)
    campaign = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp, name="x",
        template="Hi {first_name}, saw {company}!",
        placeholders=["first_name", "company"],
        created_by=user,
    )
    # Row 1: valid. Row 2: missing 'company'. Row 3: valid.
    for idx, vars_ in enumerate(
        [
            {"first_name": "Bob", "company": "Acme"},
            {"first_name": "Carol"},  # missing company
            {"first_name": "Dave", "company": "Globex"},
        ],
        start=1,
    ):
        PersonalizedRecipient.objects.create(
            campaign=campaign, variables=vars_,
            label=vars_["first_name"], position=idx,
        )

    client = APIClient()
    _login(client, user)
    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == http.HTTP_200_OK
    body = response.json()
    assert body["queued_count"] == 2
    assert body["failed_at_render_count"] == 1

    rows = list(campaign.recipients.order_by("position"))
    assert rows[0].status == PersonalizedRecipient.Status.QUEUED
    assert rows[1].status == PersonalizedRecipient.Status.FAILED
    assert "company" in rows[1].error_message
    assert rows[2].status == PersonalizedRecipient.Status.QUEUED

    # Campaign still IN_FLIGHT (at least one succeeded).
    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.IN_FLIGHT

    # Celery fired twice (only the two QUEUED rows).
    assert _no_celery_dispatch.call_count == 2


def test_launch_all_render_failures_short_circuits_to_failed(
    _no_celery_dispatch,
) -> None:
    user, ws = _make_user_workspace("b35allfail@test")
    sp = _make_spokesperson(ws)
    campaign = PersonalizedCampaign.objects.create(
        workspace=ws, spokesperson=sp, name="x",
        template="Hi {first_name}, saw {company}!",
        placeholders=["first_name", "company"],
        created_by=user,
    )
    # All rows missing 'company'.
    for idx in range(1, 4):
        PersonalizedRecipient.objects.create(
            campaign=campaign,
            variables={"first_name": f"Recipient{idx}"},
            label=f"Recipient{idx}", position=idx,
        )
    client = APIClient()
    _login(client, user)

    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == http.HTTP_200_OK
    body = response.json()
    assert body["queued_count"] == 0
    assert body["failed_at_render_count"] == 3
    assert body["campaign"]["status"] == "failed"

    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.FAILED
    assert campaign.completed_at is not None
    _no_celery_dispatch.assert_not_called()


def test_launch_over_batch_cap_returns_402(_no_celery_dispatch) -> None:
    """Starter cap=5; 10 recipients trips
    personalized_batch_too_large."""
    user, ws = _make_user_workspace("b35lhbig@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=10)
    client = APIClient()
    _login(client, user)

    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == 402, response.content
    assert response.json()["code"] == "personalized_batch_too_large"

    # State unchanged — campaign stayed in DRAFT.
    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.DRAFT
    _no_celery_dispatch.assert_not_called()


def test_launch_over_month_cap_returns_402(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b35lhmonth@test")
    sp = _make_spokesperson(ws)
    # SESSION 204 — get_usage() now counts Compositions
    # (excluding DRAFT). Seed 8 completed Compositions to
    # leave 2 of 10 Starter videos remaining; launching 5
    # would exceed.
    for _ in range(8):
        Composition.objects.create(
            workspace=ws, spokesperson=sp, name="x",
            template_kind="talking_head_polished",
            status=CompositionStatus.COMPLETED,
        )
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=5)
    client = APIClient()
    _login(client, user)

    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == 402
    assert response.json()["code"] == "video_limit_reached"

    campaign.refresh_from_db()
    assert campaign.status == PersonalizedCampaign.Status.DRAFT
    _no_celery_dispatch.assert_not_called()


def test_launch_no_recipients_returns_400(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b35lhnore@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=0)
    client = APIClient()
    _login(client, user)

    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    _no_celery_dispatch.assert_not_called()


def test_launch_non_draft_returns_409(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b35lhnd@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=2)
    campaign.status = PersonalizedCampaign.Status.IN_FLIGHT
    campaign.save(update_fields=["status"])
    client = APIClient()
    _login(client, user)

    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == http.HTTP_409_CONFLICT
    _no_celery_dispatch.assert_not_called()


def test_launch_cross_workspace_returns_404(_no_celery_dispatch) -> None:
    user_a, _ = _make_user_workspace("b35lha@test")
    user_b, ws_b = _make_user_workspace("b35lhb@test")
    sp_b = _make_spokesperson(ws_b)
    campaign = _make_draft_with_recipients(user_b, ws_b, sp_b, recipient_count=2)

    client = APIClient()
    _login(client, user_a)
    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == http.HTTP_404_NOT_FOUND
    _no_celery_dispatch.assert_not_called()


# ---- BC3 — source_script lineage propagation -------------------


def test_launch_with_source_script_propagates_lineage_per_recipient(
    _no_celery_dispatch,
) -> None:
    """BC3 / BC0 rules 4 + 5 + 8 — when source_script is set,
    every per-recipient Composition inherits the Script's
    knowledge_chunk_ids + verification fields, and the
    synthesized_brief = the per-recipient rendered template.

    This is the load-bearing composition-arc test. F-arc brief-
    mode panel on each per-recipient Asset detail page depends
    on Composition.knowledge_chunk_ids being populated."""
    from apps.scripts.models import Script

    user, ws = _make_user_workspace("bc3launch@test")
    sp = _make_spokesperson(ws)

    # Create a READY Script with knowledge + warnings.
    script = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="Five Good Emperors",
        prompt="explain the five good emperors",
        draft_text="Today we're tackling the Five Good Emperors.",
        knowledge_chunk_ids=[
            "chunk-a", "chunk-b", "chunk-c", "chunk-d", "chunk-e",
        ],
        verification_status="verified",
        verification_warnings=[
            {"kind": "multi_word", "claim": "Machiavelli and Gibbon",
             "position": 436},
        ],
        status="ready",
    )

    # Build a campaign with the source_script + 2 recipients.
    campaign = PersonalizedCampaign.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="Outreach",
        template="Hi {first_name}, today we tackle the Five Good Emperors.",
        placeholders=["first_name"],
        source_script=script,
        created_by=user,
    )
    for idx, name in enumerate(["Bob", "Carol"], start=1):
        PersonalizedRecipient.objects.create(
            campaign=campaign,
            variables={"first_name": name},
            label=name,
            position=idx,
        )

    client = APIClient()
    _login(client, user)
    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == http.HTTP_200_OK, response.content
    assert response.json()["queued_count"] == 2

    # Every per-recipient Composition inherits the Script's
    # lineage (rule 4) + verification flags (rule 8).
    recipients = list(campaign.recipients.order_by("position"))
    for r in recipients:
        comp = r.produced_composition
        assert comp is not None
        # Rule 4 — chunk_ids match.
        assert comp.knowledge_chunk_ids == [
            "chunk-a", "chunk-b", "chunk-c", "chunk-d", "chunk-e",
        ]
        # Rule 8 — verification flags carry unchanged.
        assert comp.verification_status == "verified"
        assert len(comp.verification_warnings) == 1
        assert comp.verification_warnings[0]["claim"] == (
            "Machiavelli and Gibbon"
        )
        # Rule 5 — synthesized_brief is the per-recipient
        # rendered template, NOT the Script's draft_text.
        assert r.variables["first_name"] in comp.synthesized_brief
        assert comp.synthesized_brief == r.rendered_script


def test_launch_without_source_script_leaves_lineage_empty(
    _no_celery_dispatch,
) -> None:
    """BC3 back-compat — Campaign without source_script
    produces vanilla per-recipient Compositions (lineage fields
    empty). Existing C-arc behavior preserved."""
    user, ws = _make_user_workspace("bc3lbc@test")
    sp = _make_spokesperson(ws)
    campaign = _make_draft_with_recipients(user, ws, sp, recipient_count=2)
    # source_script is None by default.
    assert campaign.source_script is None

    client = APIClient()
    _login(client, user)
    response = client.post(f"/api/campaigns/{campaign.pk}/launch/")
    assert response.status_code == http.HTTP_200_OK

    for r in campaign.recipients.all():
        comp = r.produced_composition
        assert comp is not None
        # No lineage carried.
        assert comp.knowledge_chunk_ids == []
        assert comp.synthesized_brief == ""
        assert comp.verification_status == ""
        assert comp.verification_warnings == []
