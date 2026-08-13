"""Tests for ``bootstrap_review_resume_pending_publications`` command.

Covers both recovery cases per Finding 9 + Q11:
* Pending Phase-4 publications (evidence_published_at_utc IS NULL).
* Missed no_candidate_approved supersedes (journal terminal is
  no_candidate but slot still has APPROVED IdentityReference).
"""
from __future__ import annotations

import uuid
from io import StringIO
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.identity.models import IdentityReference, ReferenceState

from apps.bootstrap_review.decisions import record_decision
from apps.bootstrap_review.evidence import FROZEN_EVIDENCE_ROOT
from apps.bootstrap_review.journal import review_dir_for_fixture
from apps.bootstrap_review.models import PromotionAudit
from apps.bootstrap_review.promotion import promote_current_decision

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
FCID_COMPACT = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__front__compact"
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
    return User.objects.create_user(email="resume@example.test", password="x")


def _make_decision(reviewer, **kwargs):
    kw = dict(
        decision_id=str(uuid.uuid4()),
        bootstrap_run_id=FROZEN_RUN_ID,
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
        disposition="selected",
        frozen_candidate_id=FCID_COMPACT,
        supersedes_decision_id=None,
        amendment_reason=None,
        reviewer_user_id=reviewer.id,
        reviewer_email_at_write_time=reviewer.email,
    )
    kw.update(kwargs)
    record, _ = record_decision(**kw)
    return record


# ---------------------------------------------------------------------
# Dry-run
# ---------------------------------------------------------------------


def test_dry_run_reports_nothing_pending_on_clean_state(reviewer):
    _make_decision(reviewer)
    promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    # Everything is already published; dry-run should report 0/0.
    out = StringIO()
    call_command(
        "bootstrap_review_resume_pending_publications",
        "--dry-run",
        stdout=out,
    )
    assert "0 pending publication(s), 0 pending supersede(s)" in out.getvalue()


# ---------------------------------------------------------------------
# Pending Phase-4 publications
# ---------------------------------------------------------------------


def test_completes_pending_publication_after_phase_4_crash(reviewer, monkeypatch):
    _make_decision(reviewer)
    import apps.bootstrap_review.promotion as promo

    original_publish = promo._publish_revision_folder
    call_count = {"n": 0}

    def flaky(audit):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise RuntimeError("simulated Phase 4 crash")
        original_publish(audit)

    monkeypatch.setattr(promo, "_publish_revision_folder", flaky)

    with pytest.raises(RuntimeError):
        promote_current_decision(
            fixture_id="fixture_h1",
            reference_kind="portrait_reference",
            reference_purpose="front",
        )
    audit = PromotionAudit.objects.first()
    assert audit is not None
    assert audit.evidence_published_at_utc is None

    monkeypatch.setattr(promo, "_publish_revision_folder", original_publish)
    out = StringIO()
    call_command("bootstrap_review_resume_pending_publications", stdout=out)
    assert "published" in out.getvalue()

    audit.refresh_from_db()
    assert audit.evidence_published_at_utc is not None
    from apps.bootstrap_review.promotion import _revision_folder

    folder = _revision_folder(
        audit.fixture_id,
        audit.reference_kind,
        audit.reference_purpose,
        audit.slot_revision,
    )
    assert (folder / ".materialization_complete").exists()


def test_resume_is_idempotent(reviewer):
    _make_decision(reviewer)
    promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    for _ in range(3):
        call_command("bootstrap_review_resume_pending_publications")
    assert PromotionAudit.objects.count() == 1


# ---------------------------------------------------------------------
# Missed no_candidate_approved supersede
# ---------------------------------------------------------------------


def test_resume_applies_missed_no_candidate_supersede(reviewer, monkeypatch):
    """Simulate: selected A → promoted; then reviewer amends to
    no_candidate_approved but the promotion service call was never
    invoked. Resume must detect + supersede.
    """
    d1 = _make_decision(reviewer)
    r1 = promote_current_decision(
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
    )
    ref = IdentityReference.objects.get(pk=r1.identity_reference_id)
    assert ref.state == ReferenceState.APPROVED

    # Amend to no_candidate_approved via journal only — do NOT call
    # the promotion service. That's the "missed" case resume repairs.
    _make_decision(
        reviewer,
        disposition="no_candidate_approved",
        frozen_candidate_id=None,
        supersedes_decision_id=d1.decision_id,
        amendment_reason="none acceptable",
    )
    # Reference is still APPROVED — journal reflects new state but
    # substrate has not been updated.
    ref.refresh_from_db()
    assert ref.state == ReferenceState.APPROVED

    out = StringIO()
    call_command("bootstrap_review_resume_pending_publications", stdout=out)
    assert "1 pending supersede(s)" in out.getvalue()

    ref.refresh_from_db()
    assert ref.state == ReferenceState.SUPERSEDED
    # No new PromotionAudit was created for the no_candidate operation.
    assert PromotionAudit.objects.count() == 1
