"""§19 Step 9.b.3b promote + approve-version endpoint tests.

Backend HTTP surface only. SPA tests live under web/src.
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    IdentityReference,
    ReferenceState,
)

from apps.bootstrap_review.decisions import record_decision
from apps.bootstrap_review.evidence import (
    AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES,
    FROZEN_EVIDENCE_ROOT,
)
from apps.bootstrap_review.journal import review_dir_for_fixture
from apps.bootstrap_review.models import PromotionAudit
from apps.bootstrap_review.workspace import BOOTSTRAP_WORKSPACE_SLUG

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
FCID_FRONT = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__front__compact"
)
FCID_NEUTRAL = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__neutral_rest__compact"
)

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def clean_state(tmp_path, settings):
    settings.BOOTSTRAP_DURABLE_ASSETS_ROOT = str(tmp_path / "assets")
    fixtures = ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4")
    for fixture in fixtures:
        for sub in ("review", "references"):
            d = FROZEN_EVIDENCE_ROOT / fixture / "bootstrap" / sub
            if d.exists():
                import shutil
                shutil.rmtree(d)
    yield
    for fixture in fixtures:
        for sub in ("review", "references"):
            d = FROZEN_EVIDENCE_ROOT / fixture / "bootstrap" / sub
            if d.exists():
                import shutil
                shutil.rmtree(d)


@pytest.fixture()
def staff_user(db):
    User = get_user_model()
    user = User.objects.create_user(email="staff-p@example.test", password="x")
    user.is_staff = True
    user.save(update_fields=["is_staff"])
    return user


@pytest.fixture()
def ordinary_user(db):
    User = get_user_model()
    return User.objects.create_user(email="ord-p@example.test", password="x")


@pytest.fixture()
def staff_client(staff_user):
    c = APIClient()
    c.force_authenticate(user=staff_user)
    return c


def _decide(reviewer, purpose, disposition="selected", fcid=FCID_FRONT):
    decision_id = str(uuid.uuid4())
    record_decision(
        decision_id=decision_id,
        bootstrap_run_id=FROZEN_RUN_ID,
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose=purpose,
        disposition=disposition,
        frozen_candidate_id=fcid if disposition == "selected" else None,
        supersedes_decision_id=None,
        amendment_reason=None,
        reviewer_user_id=reviewer.id,
        reviewer_email_at_write_time=reviewer.email,
    )


def _decide_and_return(reviewer, purpose, disposition="selected", fcid=FCID_FRONT):
    decision_id = str(uuid.uuid4())
    record_decision(
        decision_id=decision_id,
        bootstrap_run_id=FROZEN_RUN_ID,
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose=purpose,
        disposition=disposition,
        frozen_candidate_id=fcid if disposition == "selected" else None,
        supersedes_decision_id=None,
        amendment_reason=None,
        reviewer_user_id=reviewer.id,
        reviewer_email_at_write_time=reviewer.email,
    )
    return {"decision_id": decision_id}


def _promote_url(purpose="front", fixture_id="fixture_h1"):
    return reverse(
        "bootstrap-review-slot-promote",
        args=[FROZEN_RUN_ID, fixture_id, "portrait_reference", purpose],
    )


def _approve_url(fixture_id="fixture_h1"):
    return reverse(
        "bootstrap-review-fixture-approve-version",
        args=[FROZEN_RUN_ID, fixture_id],
    )


# ---------------------------------------------------------------------
# Promote endpoint
# ---------------------------------------------------------------------


def test_promote_happy_path_returns_selected_kind(staff_user, staff_client):
    _decide(staff_user, "front", fcid=FCID_FRONT)
    r = staff_client.post(_promote_url())
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["kind"] == "selected"
    assert body["slot_revision"] == 1
    assert PromotionAudit.objects.count() == 1


def test_promote_idempotent_retry(staff_user, staff_client):
    _decide(staff_user, "front", fcid=FCID_FRONT)
    r1 = staff_client.post(_promote_url()).json()
    r2 = staff_client.post(_promote_url()).json()
    assert r1["promotion_audit_id"] == r2["promotion_audit_id"]
    assert PromotionAudit.objects.count() == 1


def test_promote_no_current_decision_returns_404(staff_client):
    r = staff_client.post(_promote_url())
    assert r.status_code == status.HTTP_404_NOT_FOUND
    assert r.json()["code"] == "no_current_decision"


def test_promote_no_candidate_on_empty_slot_is_noop(staff_user, staff_client):
    """First-ever decision on a slot is no_candidate_approved — no prior
    APPROVED reference to supersede + no CharacterIdentity yet.
    Promotion returns a stable noop marker + creates no rows.
    """
    _decide(staff_user, "front", disposition="no_candidate_approved", fcid=None)
    r = staff_client.post(_promote_url())
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["kind"] == "noop_current_decision_matches_prior_state"
    assert PromotionAudit.objects.count() == 0


def test_promote_no_candidate_after_selected_supersedes_prior(staff_user, staff_client):
    """selected → no_candidate: prior APPROVED IdentityReference
    transitions to SUPERSEDED; no new PromotionAudit row.
    """
    d1_ids = _decide_and_return(staff_user, "front", fcid=FCID_FRONT)
    r1 = staff_client.post(_promote_url()).json()

    from apps.bootstrap_review.decisions import record_decision as rd
    rd(
        decision_id=str(uuid.uuid4()),
        bootstrap_run_id=FROZEN_RUN_ID,
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
        disposition="no_candidate_approved",
        frozen_candidate_id=None,
        supersedes_decision_id=d1_ids["decision_id"],
        amendment_reason="reconsidered",
        reviewer_user_id=staff_user.id,
        reviewer_email_at_write_time=staff_user.email,
    )
    r = staff_client.post(_promote_url())
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["kind"] == "no_candidate_approved"
    # Still exactly one PromotionAudit row (the original select).
    assert PromotionAudit.objects.count() == 1
    a_ref = IdentityReference.objects.get(pk=r1["identity_reference_id"])
    assert a_ref.state == ReferenceState.SUPERSEDED


def test_promote_ordinary_user_forbidden(ordinary_user):
    c = APIClient()
    c.force_authenticate(user=ordinary_user)
    r = c.post(_promote_url())
    assert r.status_code == status.HTTP_403_FORBIDDEN


def test_promote_unauthorized_run_id_refused(staff_client):
    url = reverse(
        "bootstrap-review-slot-promote",
        args=["bootstrap_other", "fixture_h1", "portrait_reference", "front"],
    )
    r = staff_client.post(url)
    assert r.status_code == status.HTTP_404_NOT_FOUND


def test_promote_integrity_failure_creates_nothing(staff_user, staff_client, monkeypatch):
    _decide(staff_user, "front", fcid=FCID_FRONT)
    import apps.bootstrap_review.evidence as evidence
    from apps.bootstrap_review.evidence import FrozenCandidateId, artifact_path

    fcid = FrozenCandidateId.parse(FCID_FRONT)
    real_path = artifact_path(fcid, "raw")
    original = evidence.Path.read_bytes

    def tampered(self, *args, **kwargs):
        if self == real_path:
            return b"tampered"
        return original(self, *args, **kwargs)

    monkeypatch.setattr(evidence.Path, "read_bytes", tampered)
    r = staff_client.post(_promote_url())
    assert r.status_code == status.HTTP_502_BAD_GATEWAY
    assert r.json()["code"] == "artifact_integrity_mismatch"
    assert PromotionAudit.objects.count() == 0


def test_promote_duplicate_selected_amendment(staff_user, staff_client):
    """A→B amendment: two promotions succeed; B becomes APPROVED,
    A becomes SUPERSEDED.
    """
    _decide(staff_user, "front", fcid=FCID_FRONT)
    r1 = staff_client.post(_promote_url()).json()

    fcid_teamcard = (
        f"{FROZEN_RUN_ID}/identity_only/stability_still/"
        "fixture_h1__portrait_reference__front__team_card"
    )
    # Amend to team_card
    from apps.bootstrap_review.decisions import record_decision as rd
    rd(
        decision_id=str(uuid.uuid4()),
        bootstrap_run_id=FROZEN_RUN_ID,
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
        disposition="selected",
        frozen_candidate_id=fcid_teamcard,
        supersedes_decision_id=r1["decision_id"],
        amendment_reason="switch to team_card",
        reviewer_user_id=staff_user.id,
        reviewer_email_at_write_time=staff_user.email,
    )
    r2 = staff_client.post(_promote_url()).json()
    assert r2["slot_revision"] == 2
    assert PromotionAudit.objects.count() == 2

    a_ref = IdentityReference.objects.get(pk=r1["identity_reference_id"])
    assert a_ref.state == ReferenceState.SUPERSEDED
    b_ref = IdentityReference.objects.get(pk=r2["identity_reference_id"])
    assert b_ref.state == ReferenceState.APPROVED


# ---------------------------------------------------------------------
# Approve-version endpoint
# ---------------------------------------------------------------------


def test_approve_version_happy_path(staff_user, staff_client):
    _decide(staff_user, "front", fcid=FCID_FRONT)
    staff_client.post(_promote_url("front"))
    _decide(staff_user, "neutral_rest", fcid=FCID_NEUTRAL)
    staff_client.post(_promote_url("neutral_rest"))

    r = staff_client.post(_approve_url())
    assert r.status_code == status.HTTP_200_OK
    body = r.json()
    assert body["state"] == "approved"
    assert body["already_approved"] is False


def test_approve_version_idempotent(staff_user, staff_client):
    _decide(staff_user, "front", fcid=FCID_FRONT)
    staff_client.post(_promote_url("front"))
    _decide(staff_user, "neutral_rest", fcid=FCID_NEUTRAL)
    staff_client.post(_promote_url("neutral_rest"))
    staff_client.post(_approve_url())

    r = staff_client.post(_approve_url())
    assert r.status_code == status.HTTP_200_OK
    assert r.json()["already_approved"] is True


def test_approve_version_refuses_when_floor_unsatisfied(staff_user, staff_client):
    """Only front promoted, missing neutral_rest — approve must refuse."""
    _decide(staff_user, "front", fcid=FCID_FRONT)
    staff_client.post(_promote_url("front"))

    r = staff_client.post(_approve_url())
    assert r.status_code == status.HTTP_400_BAD_REQUEST
    assert r.json()["code"] == "floor_not_satisfied"


def test_approve_version_no_identity_returns_404(staff_client):
    r = staff_client.post(_approve_url())
    assert r.status_code == status.HTTP_404_NOT_FOUND
    assert r.json()["code"] == "no_identity_for_fixture"


def test_approve_version_ordinary_user_forbidden(ordinary_user):
    c = APIClient()
    c.force_authenticate(user=ordinary_user)
    r = c.post(_approve_url())
    assert r.status_code == status.HTTP_403_FORBIDDEN


# ---------------------------------------------------------------------
# Enriched GET surface — current_promotion + canonical_materialization
# ---------------------------------------------------------------------


def test_slot_get_includes_current_promotion_after_promote(staff_user, staff_client):
    _decide(staff_user, "front", fcid=FCID_FRONT)
    staff_client.post(_promote_url("front"))

    slot = staff_client.get(
        reverse(
            "bootstrap-review-slot-detail",
            args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
        )
    ).json()
    assert slot["current_promotion"] is not None
    assert slot["current_promotion"]["publication_status"] == "published"
    assert slot["current_promotion"]["slot_revision"] == 1


def test_slot_get_current_promotion_none_before_promote(staff_user, staff_client):
    _decide(staff_user, "front", fcid=FCID_FRONT)
    slot = staff_client.get(
        reverse(
            "bootstrap-review-slot-detail",
            args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
        )
    ).json()
    assert slot["current_promotion"] is None


def test_fixture_get_includes_canonical_materialization(staff_user, staff_client):
    fixture = staff_client.get(
        reverse(
            "bootstrap-review-fixture-detail",
            args=[FROZEN_RUN_ID, "fixture_h1"],
        )
    ).json()
    assert "canonical_materialization" in fixture
    cm = fixture["canonical_materialization"]
    assert cm["canonical_reference_floor_satisfied"] is False
    assert cm["step10_ready"] is False


def test_slot_get_publication_pending_state(staff_user, monkeypatch):
    """A Phase 4 crash leaves the DB committed with PromotionAudit
    but evidence_published_at_utc IS NULL. The slot GET must
    surface ``publication_status='publication_pending'`` so the SPA
    can render the recovery notice.
    """
    _decide(staff_user, "front", fcid=FCID_FRONT)
    import apps.bootstrap_review.promotion as promo

    original = promo._publish_revision_folder

    def flaky(audit):
        raise RuntimeError("simulated Phase 4 crash")

    monkeypatch.setattr(promo, "_publish_revision_folder", flaky)

    # APIClient with raise_request_exception=False so we get a real
    # 500 response object instead of a re-raised exception.
    c = APIClient(raise_request_exception=False)
    c.force_authenticate(user=staff_user)
    r = c.post(_promote_url())
    assert r.status_code == status.HTTP_500_INTERNAL_SERVER_ERROR
    audit = PromotionAudit.objects.first()
    assert audit is not None
    assert audit.evidence_published_at_utc is None

    monkeypatch.setattr(promo, "_publish_revision_folder", original)
    slot = c.get(
        reverse(
            "bootstrap-review-slot-detail",
            args=[FROZEN_RUN_ID, "fixture_h1", "portrait_reference", "front"],
        )
    ).json()
    assert slot["current_promotion"]["publication_status"] == "publication_pending"
