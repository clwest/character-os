"""Tests for the Step-10 readiness derivation function.

Backend-only per §R — the CLI command lands at 9.b.3b. This suite
exercises the pure predicate directly.
"""
from __future__ import annotations

import hashlib
import uuid
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model

from apps.identity import services as identity_services
from apps.identity.models import CharacterIdentityVersion

from apps.bootstrap_review.decisions import record_decision
from apps.bootstrap_review.evidence import (
    AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES,
    FROZEN_EVIDENCE_ROOT,
)
from apps.bootstrap_review.models import PromotionAudit
from apps.bootstrap_review.promotion import promote_current_decision
from apps.bootstrap_review.readiness import derive_step10_readiness

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
def clean_review_and_references(tmp_path, settings):
    settings.BOOTSTRAP_DURABLE_ASSETS_ROOT = str(tmp_path / "assets")
    fixtures = ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4")
    for fixture in fixtures:
        for sub in ("review", "references"):
            d = FROZEN_EVIDENCE_ROOT / fixture / "bootstrap" / sub
            if d.exists():
                _rmtree(d)
    yield
    for fixture in fixtures:
        for sub in ("review", "references"):
            d = FROZEN_EVIDENCE_ROOT / fixture / "bootstrap" / sub
            if d.exists():
                _rmtree(d)


def _rmtree(path: Path) -> None:
    import shutil
    shutil.rmtree(path)


@pytest.fixture()
def reviewer():
    User = get_user_model()
    return User.objects.create_user(email="readiness@example.test", password="x")


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
    return decision_id


def test_fixture_nh1_never_ready():
    result = derive_step10_readiness("fixture_nh1")
    assert result.fixture_authorized is False
    assert result.ready is False
    assert "fixture_not_authorized" in result.failures


def test_no_decisions_not_ready():
    result = derive_step10_readiness("fixture_h1")
    assert result.ready is False
    assert result.review_complete is False
    assert result.approval_floor_satisfied is False
    assert result.canonical_reference_floor_satisfied is False
    assert result.canonical_version_admitted is False
    assert "review_incomplete" in result.failures
    assert "approval_floor_unsatisfied" in result.failures


def test_review_incomplete_not_ready(reviewer):
    _decide(reviewer, purpose="front", fcid=FCID_FRONT)
    promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    result = derive_step10_readiness("fixture_h1")
    assert result.ready is False
    assert result.review_complete is False
    assert "review_incomplete" in result.failures


def test_review_complete_but_floor_unsatisfied_not_ready(reviewer):
    """7/7 dispositioned but front + neutral_rest = no_candidate_approved."""
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        _decide(reviewer, purpose=purpose, disposition="no_candidate_approved")
    result = derive_step10_readiness("fixture_h1")
    assert result.ready is False
    assert result.review_complete is True
    assert result.approval_floor_satisfied is False
    assert "approval_floor_unsatisfied" in result.failures


def test_canonical_floor_unsatisfied_not_ready(reviewer):
    """All 7 purposes dispositioned, required selected, but promotions
    never invoked — canonical references don't exist yet.
    """
    _decide(reviewer, purpose="front", fcid=FCID_FRONT)
    _decide(reviewer, purpose="neutral_rest", fcid=FCID_NEUTRAL)
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        if purpose in ("front", "neutral_rest"):
            continue
        _decide(reviewer, purpose=purpose, disposition="no_candidate_approved")
    result = derive_step10_readiness("fixture_h1")
    assert result.review_complete is True
    assert result.approval_floor_satisfied is True  # journal side
    assert result.canonical_reference_floor_satisfied is False
    assert result.canonical_version_admitted is False
    assert result.ready is False


def test_promoted_but_version_still_draft_not_ready(reviewer):
    """Both required references promoted + published, but version has
    not been approve_version'd yet (that's an explicit operator action
    in 9.b.3b).
    """
    _decide(reviewer, purpose="front", fcid=FCID_FRONT)
    promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    _decide(reviewer, purpose="neutral_rest", fcid=FCID_NEUTRAL)
    promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="neutral_rest",
    )
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        if purpose in ("front", "neutral_rest"):
            continue
        _decide(reviewer, purpose=purpose, disposition="no_candidate_approved")
    result = derive_step10_readiness("fixture_h1")
    assert result.review_complete is True
    assert result.approval_floor_satisfied is True
    # canonical_reference_floor_satisfied checks APPROVED versions only,
    # so a DRAFT version reports canonical floor as unsatisfied.
    assert result.canonical_version_admitted is False
    assert result.ready is False


def test_all_conditions_satisfied_is_ready(reviewer):
    """Full happy path: 7 decisions + 2 promotions + version approved."""
    _decide(reviewer, purpose="front", fcid=FCID_FRONT)
    r1 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    _decide(reviewer, purpose="neutral_rest", fcid=FCID_NEUTRAL)
    promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="neutral_rest",
    )
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        if purpose in ("front", "neutral_rest"):
            continue
        _decide(reviewer, purpose=purpose, disposition="no_candidate_approved")
    # Explicit version approval (9.b.3b will expose this via API).
    version = CharacterIdentityVersion.objects.get(pk=r1.character_identity_version_id)
    identity_services.approve_version(version, approver=reviewer)

    result = derive_step10_readiness("fixture_h1")
    assert result.ready is True
    assert result.failures == ()


def test_evidence_integrity_drift_blocks_readiness(reviewer):
    """Simulate durable-Asset file tamper after promotion: readiness
    reports evidence_integrity=False.
    """
    _decide(reviewer, purpose="front", fcid=FCID_FRONT)
    r1 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    _decide(reviewer, purpose="neutral_rest", fcid=FCID_NEUTRAL)
    promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="neutral_rest",
    )
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        if purpose in ("front", "neutral_rest"):
            continue
        _decide(reviewer, purpose=purpose, disposition="no_candidate_approved")
    version = CharacterIdentityVersion.objects.get(pk=r1.character_identity_version_id)
    identity_services.approve_version(version, approver=reviewer)

    # Tamper: overwrite a durable Asset file.
    audit = PromotionAudit.objects.first()
    Path(audit.raw_asset.file_path).write_bytes(b"TAMPERED")

    result = derive_step10_readiness("fixture_h1")
    assert result.evidence_integrity is False
    assert "evidence_integrity_drift" in result.failures
    assert result.ready is False
