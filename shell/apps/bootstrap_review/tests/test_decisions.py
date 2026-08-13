"""§19 Step 9.b.2 decision-service tests (SESSION 249).

Coverage per operator checklist §20:

* selected valid candidate succeeds
* no_candidate_approved succeeds
* selected requires frozen_candidate_id
* no_candidate_approved requires frozen_candidate_id=null
* unsupported candidate cannot be selected
* cross-slot / cross-fixture candidate refused
* unauthorized run refused
* fixture_nh1 refused
* first decision preserved / amendment appends / prior bytes untouched
* amendment reason required
* supersedes chain correct across ≥3 revisions
* idempotency: same UUID same payload → one record
* idempotency: same UUID changed payload → conflict
* stale supersedes → conflict
* tampered artifact prevents selection + no journal entry written
"""
from __future__ import annotations

import uuid
from pathlib import Path

import pytest

from apps.bootstrap_review.decisions import (
    AmendmentReasonRequired,
    CandidateNotReviewable,
    CandidateSlotMismatch,
    DuplicateFirstDecision,
    InvalidCandidate,
    InvalidDisposition,
    StaleSupersedesDecision,
    record_decision,
)
from apps.bootstrap_review.evidence import (
    ArtifactIntegrityError,
    FrozenCandidateId,
    artifact_path,
)
from apps.bootstrap_review.journal import (
    DecisionIdConflict,
    current_decision_per_slot,
    decision_file_path,
    decision_history_for_slot,
    review_dir_for_fixture,
)

FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f"
GOOD_FCID = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__front__compact"
)
GOOD_FCID_OTHER_PURPOSE = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h1__portrait_reference__neutral_rest__compact"
)
GOOD_FCID_OTHER_FIXTURE = (
    f"{FROZEN_RUN_ID}/identity_only/stability_still/"
    "fixture_h2__portrait_reference__front__compact"
)
UNSUPPORTED_FCID = (
    f"{FROZEN_RUN_ID}/identity_only/runway_still_portrait/"
    "fixture_h1__portrait_reference__front__compact"
)


@pytest.fixture(autouse=True)
def clean_review_directories():
    dirs = [
        review_dir_for_fixture(f)
        for f in ("fixture_h1", "fixture_h2", "fixture_h3", "fixture_h4")
    ]
    for d in dirs:
        if d.exists():
            for f in d.iterdir():
                f.unlink()
            d.rmdir()
    yield
    for d in dirs:
        if d.exists():
            for f in d.iterdir():
                f.unlink()
            d.rmdir()


def _call(**overrides):
    kwargs = dict(
        decision_id=str(uuid.uuid4()),
        bootstrap_run_id=FROZEN_RUN_ID,
        fixture_id="fixture_h1",
        reference_kind="portrait_reference",
        reference_purpose="front",
        disposition="no_candidate_approved",
        frozen_candidate_id=None,
        supersedes_decision_id=None,
        amendment_reason=None,
        reviewer_user_id=42,
        reviewer_email_at_write_time="chris@example.test",
    )
    kwargs.update(overrides)
    return record_decision(**kwargs)


# ---------------------------------------------------------------------
# Disposition + candidate-constraint validation
# ---------------------------------------------------------------------


def test_no_candidate_approved_succeeds():
    _, created = _call(disposition="no_candidate_approved")
    assert created is True


def test_no_candidate_approved_refuses_non_null_fcid():
    with pytest.raises(InvalidDisposition):
        _call(disposition="no_candidate_approved", frozen_candidate_id=GOOD_FCID)


def test_selected_requires_frozen_candidate_id():
    with pytest.raises(InvalidDisposition):
        _call(disposition="selected", frozen_candidate_id=None)


def test_selected_valid_candidate_succeeds():
    _, created = _call(
        disposition="selected", frozen_candidate_id=GOOD_FCID
    )
    assert created is True


def test_invalid_disposition_refused():
    with pytest.raises(InvalidDisposition):
        _call(disposition="rejected")


def test_selected_refuses_unsupported_candidate():
    with pytest.raises(CandidateNotReviewable):
        _call(disposition="selected", frozen_candidate_id=UNSUPPORTED_FCID)


def test_selected_refuses_cross_purpose_candidate():
    with pytest.raises(CandidateSlotMismatch):
        _call(
            disposition="selected",
            frozen_candidate_id=GOOD_FCID_OTHER_PURPOSE,
        )


def test_selected_refuses_cross_fixture_candidate():
    with pytest.raises(CandidateSlotMismatch):
        _call(
            disposition="selected",
            frozen_candidate_id=GOOD_FCID_OTHER_FIXTURE,
        )


def test_unauthorized_run_refused():
    with pytest.raises(InvalidCandidate):
        _call(bootstrap_run_id="bootstrap_someone_else")


def test_fixture_nh1_refused():
    with pytest.raises(InvalidCandidate):
        _call(fixture_id="fixture_nh1")


# ---------------------------------------------------------------------
# Append-only + amendment chain
# ---------------------------------------------------------------------


def test_first_decision_persists():
    r, _ = _call(disposition="no_candidate_approved")
    current = current_decision_per_slot(r.fixture_id)
    assert current[(r.reference_kind, r.reference_purpose)]["decision_id"] == r.decision_id


def test_amendment_requires_reason():
    r1, _ = _call()
    with pytest.raises(AmendmentReasonRequired):
        _call(
            disposition="no_candidate_approved",
            supersedes_decision_id=r1.decision_id,
            amendment_reason=None,
        )
    with pytest.raises(AmendmentReasonRequired):
        _call(
            disposition="no_candidate_approved",
            supersedes_decision_id=r1.decision_id,
            amendment_reason="   ",
        )


def test_first_decision_bytes_never_mutated_by_amendment():
    r1, _ = _call()
    r1_path = decision_file_path(r1.fixture_id, r1.decision_id)
    original = r1_path.read_bytes()
    _call(
        disposition="selected",
        frozen_candidate_id=GOOD_FCID,
        supersedes_decision_id=r1.decision_id,
        amendment_reason="second thought",
    )
    assert r1_path.read_bytes() == original


def test_three_revision_chain_terminal_is_correct():
    r1, _ = _call(disposition="no_candidate_approved")
    r2, _ = _call(
        disposition="selected",
        frozen_candidate_id=GOOD_FCID,
        supersedes_decision_id=r1.decision_id,
        amendment_reason="pick compact",
    )
    r3, _ = _call(
        disposition="no_candidate_approved",
        supersedes_decision_id=r2.decision_id,
        amendment_reason="unsure again",
    )
    current = current_decision_per_slot(r1.fixture_id)
    assert current[(r1.reference_kind, r1.reference_purpose)]["decision_id"] == r3.decision_id
    history = decision_history_for_slot(
        r1.fixture_id, r1.reference_kind, r1.reference_purpose
    )
    assert [d["decision_id"] for d in history] == [
        r1.decision_id,
        r2.decision_id,
        r3.decision_id,
    ]


def test_first_decision_blocked_when_terminal_exists():
    _call()
    with pytest.raises(DuplicateFirstDecision):
        # Second first-decision (no supersedes) attempted → must fail.
        _call()


def test_stale_supersedes_rejected():
    r1, _ = _call()
    r2, _ = _call(
        supersedes_decision_id=r1.decision_id,
        amendment_reason="amend",
    )
    # r1 is no longer the terminal; a third attempt superseding r1
    # again is stale.
    with pytest.raises(StaleSupersedesDecision):
        _call(
            supersedes_decision_id=r1.decision_id,
            amendment_reason="also amend from stale ref",
        )


# ---------------------------------------------------------------------
# Idempotency
# ---------------------------------------------------------------------


def test_same_uuid_same_payload_is_idempotent():
    decision_id = str(uuid.uuid4())
    r1, created1 = _call(decision_id=decision_id)
    r2, created2 = _call(decision_id=decision_id)
    assert created1 is True
    assert created2 is False
    assert r1.decision_id == r2.decision_id
    # Only one file exists.
    dir_ = review_dir_for_fixture("fixture_h1")
    assert len(list(dir_.glob("*.jsonl"))) == 1


def test_same_uuid_different_payload_is_conflict():
    decision_id = str(uuid.uuid4())
    _call(decision_id=decision_id, disposition="no_candidate_approved")
    with pytest.raises(DecisionIdConflict):
        _call(
            decision_id=decision_id,
            disposition="selected",
            frozen_candidate_id=GOOD_FCID,
        )


# ---------------------------------------------------------------------
# Integrity re-check at POST time
# ---------------------------------------------------------------------


def test_tampered_raw_bytes_prevent_selection(monkeypatch):
    fcid = FrozenCandidateId.parse(GOOD_FCID)
    real_path = artifact_path(fcid, "raw")
    import apps.bootstrap_review.evidence as evidence

    original_read_bytes = evidence.Path.read_bytes

    def tampered(self, *args, **kwargs):
        if self == real_path:
            return b"tampered"
        return original_read_bytes(self, *args, **kwargs)

    monkeypatch.setattr(evidence.Path, "read_bytes", tampered)
    with pytest.raises(ArtifactIntegrityError):
        _call(disposition="selected", frozen_candidate_id=GOOD_FCID)
    # No journal file created.
    dir_ = review_dir_for_fixture("fixture_h1")
    assert list(dir_.glob("*.jsonl")) == []
