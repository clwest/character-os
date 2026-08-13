"""§19 Step 9.b.2 decision service — validation + integrity re-check
+ append (SESSION 249).

Sits between the HTTP view and the append-only journal. Enforces:

* disposition vocabulary — exactly ``selected`` or
  ``no_candidate_approved``;
* candidate constraint — ``selected`` requires a
  ``frozen_candidate_id`` that belongs to the SAME slot, has provider
  outcome ``success``, was produced via ``actual_execution_mode='real'``,
  and passes SHA-256 integrity re-verification at POST time (§Q16);
* amendment reason required + non-blank on any amendment (§Q4);
* stale-supersedes protection — the reviewer must be amending the
  current terminal decision, not a historical one (§Q11);
* client-generated ``decision_id`` idempotency (§Q22, §L10).

No substrate writes. No provider calls. No ``bootstrap/references/``
materialization. All of those are 9.b.3 territory.
"""
from __future__ import annotations

from datetime import datetime, timezone

from apps.identity.schema_loader import get_branch_schema

from .evidence import (
    AUTHORIZED_FIXTURE_IDS,
    AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES,
    AUTHORIZED_REFERENCE_KINDS,
    AUTHORIZED_RUN_IDS,
    CandidateJsonMissing,
    EvidenceError,
    FrozenCandidateId,
    load_candidate_json,
    read_artifact_bytes,
)
from .journal import (
    AUTHORIZED_DISPOSITIONS,
    DecisionIdConflict,
    DecisionRecord,
    _parse_decision_record,
    _validate_decision_id_shape,
    append_decision,
    current_decision_per_slot,
    decision_file_path,
    derive_fixture_progress,
)


# ---------------------------------------------------------------------
# Exceptions — stable domain vocabulary
# ---------------------------------------------------------------------


class DecisionError(Exception):
    code: str = "decision_error"


class InvalidDisposition(DecisionError):
    code = "invalid_disposition"


class CandidateSlotMismatch(DecisionError):
    code = "candidate_slot_mismatch"


class CandidateNotReviewable(DecisionError):
    code = "candidate_not_reviewable"


class InvalidCandidate(DecisionError):
    code = "invalid_candidate"


class AmendmentReasonRequired(DecisionError):
    code = "amendment_reason_required"


class StaleSupersedesDecision(DecisionError):
    code = "stale_supersedes_decision"


class DuplicateFirstDecision(DecisionError):
    """Raised when a first decision (``supersedes_decision_id=None``)
    is submitted for a slot that already has a terminal decision.
    Amendments must supply ``supersedes_decision_id``.
    """

    code = "supersedes_decision_required"


# ---------------------------------------------------------------------
# Public service
# ---------------------------------------------------------------------


def record_decision(
    *,
    decision_id: str,
    bootstrap_run_id: str,
    fixture_id: str,
    reference_kind: str,
    reference_purpose: str,
    disposition: str,
    frozen_candidate_id: str | None,
    supersedes_decision_id: str | None,
    amendment_reason: str | None,
    reviewer_user_id: int,
    reviewer_email_at_write_time: str,
    now: datetime | None = None,
) -> tuple[DecisionRecord, bool]:
    """Validate + integrity-check + append a reviewer decision.

    Returns ``(record, created)`` — ``created=False`` for idempotent
    replay of the same ``decision_id`` with the same payload.

    Raises a specific :class:`DecisionError` subclass on validation
    failure; raises :class:`~apps.bootstrap_review.evidence.ArtifactIntegrityError`
    on SHA-256 mismatch during the pre-write integrity re-check
    (§Q16). Raises :class:`~apps.bootstrap_review.journal.DecisionIdConflict`
    on same-UUID / different-payload replay.
    """
    # --- Vocabulary / shape validation ---------------------------------
    _validate_decision_id_shape(decision_id)
    if bootstrap_run_id not in AUTHORIZED_RUN_IDS:
        raise InvalidCandidate(
            f"bootstrap_run_id={bootstrap_run_id!r} not authorized"
        )
    if fixture_id not in AUTHORIZED_FIXTURE_IDS:
        raise InvalidCandidate(
            f"fixture_id={fixture_id!r} not authorized for 9.b.2"
        )
    if reference_kind not in AUTHORIZED_REFERENCE_KINDS:
        raise InvalidCandidate(
            f"reference_kind={reference_kind!r} not authorized"
        )
    if reference_purpose not in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        raise InvalidCandidate(
            f"reference_purpose={reference_purpose!r} not authorized"
        )
    if disposition not in AUTHORIZED_DISPOSITIONS:
        raise InvalidDisposition(
            f"disposition={disposition!r} must be one of "
            f"{sorted(AUTHORIZED_DISPOSITIONS)}"
        )

    # --- Disposition / candidate constraint (§Q2 + §Q3) ---------------
    if disposition == "selected":
        if not frozen_candidate_id:
            raise InvalidDisposition(
                "selected requires a non-null frozen_candidate_id"
            )
        _validate_selected_candidate(
            frozen_candidate_id=frozen_candidate_id,
            expected_run_id=bootstrap_run_id,
            expected_fixture_id=fixture_id,
            expected_reference_kind=reference_kind,
            expected_reference_purpose=reference_purpose,
        )
    else:  # no_candidate_approved
        if frozen_candidate_id is not None:
            raise InvalidDisposition(
                "no_candidate_approved requires frozen_candidate_id=null"
            )

    # --- Idempotency check (§Q22, §L10) ------------------------------
    # Before doing the amendment/currency check, look for a pre-existing
    # file with the same decision_id. If one exists AND the client-
    # supplied fields match, return it verbatim (no write, no side
    # effect). If it exists with different client fields, conflict.
    # This must run BEFORE the stale-supersedes check because a replay
    # of an old first-decision is legitimate even after amendments
    # have moved the terminal marker onward.
    existing_path = decision_file_path(fixture_id, decision_id)
    if existing_path.exists():
        existing = _parse_decision_record(existing_path)
        client_now = {
            "bootstrap_run_id": bootstrap_run_id,
            "fixture_id": fixture_id,
            "reference_kind": reference_kind,
            "reference_purpose": reference_purpose,
            "disposition": disposition,
            "frozen_candidate_id": frozen_candidate_id,
            "supersedes_decision_id": supersedes_decision_id,
            "amendment_reason": amendment_reason,
            "reviewer_user_id": reviewer_user_id,
        }
        client_stored = {k: existing.get(k) for k in client_now}
        if client_stored == client_now:
            return (
                DecisionRecord(
                    decision_id=existing["decision_id"],
                    review_run_id=existing["review_run_id"],
                    bootstrap_run_id=existing["bootstrap_run_id"],
                    fixture_id=existing["fixture_id"],
                    reference_kind=existing["reference_kind"],
                    reference_purpose=existing["reference_purpose"],
                    disposition=existing["disposition"],  # type: ignore[arg-type]
                    frozen_candidate_id=existing.get("frozen_candidate_id"),
                    supersedes_decision_id=existing.get(
                        "supersedes_decision_id"
                    ),
                    amendment_reason=existing.get("amendment_reason"),
                    reviewer_user_id=existing["reviewer_user_id"],
                    reviewer_email_at_write_time=existing.get(
                        "reviewer_email_at_write_time", ""
                    ),
                    decided_at_utc=existing["decided_at_utc"],
                ),
                False,
            )
        raise DecisionIdConflict(
            f"decision_id={decision_id!r} already exists with different "
            "client-supplied payload"
        )

    # --- Amendment / supersedes protection (§Q9 + §Q11) ---------------
    if supersedes_decision_id is not None:
        if not amendment_reason or not amendment_reason.strip():
            raise AmendmentReasonRequired(
                "amendment_reason is required and must be non-blank "
                "when supersedes_decision_id is set"
            )
    current = current_decision_per_slot(fixture_id).get(
        (reference_kind, reference_purpose)
    )
    if supersedes_decision_id is None:
        # First decision path. Refuse if a terminal decision already
        # exists — the client must explicitly supersede it.
        if current is not None and current["decision_id"] != decision_id:
            raise DuplicateFirstDecision(
                f"slot already has a terminal decision "
                f"(decision_id={current['decision_id']!r}); "
                "provide supersedes_decision_id to amend it"
            )
    else:
        # Amendment path. The referenced decision must be the current
        # terminal decision for this slot — otherwise the amendment
        # is stale (someone else's decision landed in between).
        if current is None:
            raise StaleSupersedesDecision(
                f"cannot supersede decision_id={supersedes_decision_id!r} — "
                "the slot has no current decision"
            )
        if current["decision_id"] != supersedes_decision_id:
            raise StaleSupersedesDecision(
                f"cannot supersede decision_id={supersedes_decision_id!r} — "
                f"current terminal decision is "
                f"{current['decision_id']!r}. Re-load the slot and amend "
                "against the current decision."
            )

    # --- Build immutable record + append ------------------------------
    if now is None:
        now = datetime.now(timezone.utc)
    # In 9.b.2 one file = one session = one decision, so review_run_id
    # collapses onto decision_id. This is what makes replay idempotent:
    # a retry with the same decision_id must produce byte-identical
    # file contents. 9.b.3+ may widen review_run_id to group multiple
    # records (promotion_committed etc.) under one session — that's
    # a later concern; 9.b.2 stays honest by making the grouping
    # trivially deterministic.
    review_run_id = decision_id
    record = DecisionRecord(
        decision_id=decision_id,
        review_run_id=review_run_id,
        bootstrap_run_id=bootstrap_run_id,
        fixture_id=fixture_id,
        reference_kind=reference_kind,
        reference_purpose=reference_purpose,
        disposition=disposition,  # type: ignore[arg-type]
        frozen_candidate_id=frozen_candidate_id,
        supersedes_decision_id=supersedes_decision_id,
        amendment_reason=amendment_reason,
        reviewer_user_id=reviewer_user_id,
        reviewer_email_at_write_time=reviewer_email_at_write_time,
        decided_at_utc=now.strftime("%Y-%m-%dT%H:%M:%S.%f+00:00"),
    )
    return append_decision(record)


def _validate_selected_candidate(
    *,
    frozen_candidate_id: str,
    expected_run_id: str,
    expected_fixture_id: str,
    expected_reference_kind: str,
    expected_reference_purpose: str,
) -> None:
    """Validate that ``frozen_candidate_id`` points at a reviewable
    Stability real-mode success in the SAME slot, then re-verify
    every artifact's SHA-256 (§Q16).
    """
    try:
        fcid = FrozenCandidateId.parse(frozen_candidate_id)
    except EvidenceError as exc:
        raise InvalidCandidate(str(exc)) from exc

    if fcid.run_id != expected_run_id:
        raise CandidateSlotMismatch(
            f"frozen_candidate_id belongs to run={fcid.run_id!r}, "
            f"not the expected run={expected_run_id!r}"
        )
    if fcid.fixture_id != expected_fixture_id:
        raise CandidateSlotMismatch(
            f"frozen_candidate_id belongs to fixture={fcid.fixture_id!r}, "
            f"not the slot's fixture={expected_fixture_id!r}"
        )
    if fcid.reference_kind != expected_reference_kind:
        raise CandidateSlotMismatch(
            f"frozen_candidate_id belongs to reference_kind="
            f"{fcid.reference_kind!r}, not {expected_reference_kind!r}"
        )
    if fcid.reference_purpose != expected_reference_purpose:
        raise CandidateSlotMismatch(
            f"frozen_candidate_id belongs to reference_purpose="
            f"{fcid.reference_purpose!r}, not {expected_reference_purpose!r}"
        )

    try:
        candidate = load_candidate_json(fcid)
    except CandidateJsonMissing as exc:
        raise InvalidCandidate(str(exc)) from exc

    if candidate.get("outcome") != "success":
        raise CandidateNotReviewable(
            f"candidate outcome={candidate.get('outcome')!r} is not 'success'"
        )
    provider_stage = candidate.get("provider_stage") or {}
    if provider_stage.get("actual_execution_mode") != "real":
        raise CandidateNotReviewable(
            "candidate must have actual_execution_mode='real'; got "
            f"{provider_stage.get('actual_execution_mode')!r}"
        )
    norm_stage = candidate.get("normalization_stage") or {}
    if norm_stage.get("outcome") != "success":
        raise CandidateNotReviewable(
            "candidate must have normalization_stage.outcome='success'; got "
            f"{norm_stage.get('outcome')!r}"
        )

    # §Q16 integrity re-check at POST time. Re-hash every artifact.
    # ArtifactIntegrityError + ArtifactAbsent propagate to the view
    # unchanged so the SPA renders the stable codes.
    for kind in ("raw", "normalized", "manifest"):
        # read_artifact_bytes raises ArtifactIntegrityError on
        # mismatch and ArtifactAbsent if the file is missing. Both
        # are the correct responses to a selection attempt against
        # altered evidence.
        read_artifact_bytes(fcid, kind)


# ---------------------------------------------------------------------
# Progress helper — thin wrapper that supplies the branch schema
# ---------------------------------------------------------------------


def fixture_progress(fixture_id: str):
    """Return :class:`~apps.bootstrap_review.journal.FixtureProgress`
    for ``fixture_id``. Loads the human branch schema so
    ``required_for_identity`` comes from the ratified YAML rather
    than being hardcoded in Python (§Q9 discipline).
    """
    schema = get_branch_schema("human")
    return derive_fixture_progress(
        fixture_id=fixture_id,
        required_for_identity=list(schema.required_for_identity),
    )
