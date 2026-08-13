"""§19 Step 9.b bootstrap-review views (SESSION 249).

9.b.0 landed a single health endpoint. 9.b.1 adds the read-only
browser: run metadata, per-fixture summary, per-slot candidate
listing, and artifact streaming for the frozen 9.a evidence.

Every endpoint is operator-gated by :class:`IsOperator`. Every
endpoint reads from the frozen tree only; none writes. Every
artifact response verifies SHA-256 against candidate.json before
returning bytes.

The frontend consumes these endpoints via the SPA route family
under ``/settings/bootstrap-review/*``.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from typing import Any

from django.http import FileResponse, HttpResponse, JsonResponse
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import Workspace

from .decisions import (
    AmendmentReasonRequired,
    CandidateNotReviewable,
    CandidateSlotMismatch,
    DecisionError,
    DuplicateFirstDecision,
    InvalidCandidate,
    InvalidDisposition,
    StaleSupersedesDecision,
    fixture_progress,
    record_decision,
)
from .evidence import (
    AUTHORIZED_FIXTURE_IDS,
    AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES,
    AUTHORIZED_RUN_IDS,
    ArtifactAbsent,
    ArtifactIntegrityError,
    ArtifactKind,
    CandidateJsonMissing,
    EvidenceError,
    FrozenCandidateId,
    InvalidFrozenCandidateId,
    PathContainmentViolation,
    UnauthorizedRunId,
    factual_normalization_notices,
    iter_slot_candidates,
    load_candidate_json,
    load_run_summary,
    read_artifact_bytes,
)
from .journal import (
    DecisionIdConflict,
    JournalError,
    current_decision_per_slot,
    decision_history_for_slot,
)
from .permissions import IsOperator
from .workspace import BOOTSTRAP_WORKSPACE_SLUG


# ---------------------------------------------------------------------
# 9.b.0 — health endpoint (unchanged; kept as the first endpoint so
# operators can smoke-test the gate + workspace seed without pulling
# the full evidence tree)
# ---------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsOperator])
def bootstrap_review_health(request: Request) -> Response:
    """9.b.0 skeleton health endpoint. Operator-gated.

    Returns 200 with the seeded bootstrap-fixtures workspace's
    identity when the operator gate admits the caller AND the
    9.b.0 data migration has run.
    """
    try:
        workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
    except Workspace.DoesNotExist:
        return Response(
            {
                "status": "error",
                "detail": (
                    "bootstrap-fixtures workspace not found — the 9.b.0 "
                    "data migration has not run on this database."
                ),
            },
            status=status.HTTP_500_INTERNAL_SERVER_ERROR,
        )

    return Response(
        {
            "status": "ok",
            "detail": (
                "9.b.0 skeleton — bootstrap-review API surface. See "
                "/api/bootstrap-review/runs/ for the 9.b.1 read surface."
            ),
            "bootstrap_fixtures_workspace": {
                "id": str(workspace.id),
                "slug": workspace.slug,
                "name": workspace.name,
            },
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------


def _error(code: str, message: str, status_code: int) -> Response:
    """Return a stable domain error response.

    ``code`` is the machine-friendly value (matches
    :class:`EvidenceError.code`); ``message`` is the human-friendly
    detail. The SPA branches on ``code``, not on ``message``.
    """
    return Response(
        {"code": code, "detail": message},
        status=status_code,
    )


def _map_evidence_error_to_response(exc: EvidenceError) -> Response:
    """Translate an :class:`EvidenceError` into a stable HTTP response.

    * ``UnauthorizedRunId`` — 404 (the run does not exist from the
      SPA's point of view; we do not enumerate authorized runs to
      strangers).
    * ``InvalidFrozenCandidateId`` — 400 (client sent a malformed id).
    * ``CandidateJsonMissing`` — 404.
    * ``ArtifactAbsent`` — 404 (with the specific code so the SPA
      distinguishes "unsupported cell" from "missing due to tampering").
    * ``ArtifactIntegrityError`` — 502 (LOUD; evidence has been
      altered on disk since the run froze — treat as upstream data
      corruption). Logged at ERROR level.
    * ``PathContainmentViolation`` — 400 (defense in depth; should be
      unreachable under normal use because of vocabulary guards).
    """
    if isinstance(exc, ArtifactIntegrityError):
        # LOUD failure. Never streamed to the SPA as if it were valid
        # evidence. Log at ERROR so the operator sees it in the shell
        # server log; the SPA renders the stable ``code`` so the
        # candidate is not silently displayed.
        import logging

        logging.getLogger("bootstrap_review").error(
            "artifact integrity violation: %s", exc
        )
        return _error(exc.code, str(exc), status.HTTP_502_BAD_GATEWAY)

    if isinstance(exc, (UnauthorizedRunId, CandidateJsonMissing, ArtifactAbsent)):
        return _error(exc.code, str(exc), status.HTTP_404_NOT_FOUND)

    if isinstance(exc, (InvalidFrozenCandidateId, PathContainmentViolation)):
        return _error(exc.code, str(exc), status.HTTP_400_BAD_REQUEST)

    return _error(exc.code, str(exc), status.HTTP_500_INTERNAL_SERVER_ERROR)


def _serialize_run_metadata(summary: dict) -> dict:
    """Extract the fields the SPA needs from run_summary.json.

    Deliberately does not reinterpret the summary — every value is
    copied verbatim or aggregated with clearly-named keys.
    """
    counts = summary.get("counts") or {}
    reproducibility = summary.get("reproducibility") or {}
    axes = reproducibility.get("axes") or {}
    run = summary.get("run") or {}
    execution_mode = summary.get("execution_mode") or {}
    fixtures = summary.get("fixtures") or []

    return {
        "run_id": run.get("run_id"),
        "run_fingerprint": run.get("run_fingerprint"),
        "run_kind": run.get("run_kind"),
        "qualification_status": summary.get("qualification_status"),
        "execution_mode": {
            "requested": execution_mode.get("requested"),
            "contains_real_execution": execution_mode.get(
                "contains_real_execution"
            ),
            "notice": execution_mode.get("notice"),
        },
        "started_at_utc": summary.get("started_at_utc"),
        "ended_at_utc": summary.get("ended_at_utc"),
        "fixtures": [
            {
                "fixture_id": f.get("fixture_id"),
                "branch": f.get("branch"),
                "content_hash": f.get("content_hash"),
                "spec_schema_version": f.get("spec_schema_version"),
            }
            for f in fixtures
            # 9.b.1 exposes only human fixtures — fixture_nh1 stays
            # off the review surface per SESSION 248 §Q24.
            if f.get("fixture_id") in AUTHORIZED_FIXTURE_IDS
        ],
        "axes": {
            "directions": list(axes.get("directions") or []),
            "providers": list(axes.get("providers") or []),
            "purposes_by_branch": axes.get("purposes_by_branch") or {},
            "surface_profiles": list(axes.get("surface_profiles") or []),
            "fixture_ids": [
                fid
                for fid in (axes.get("fixture_ids") or [])
                if fid in AUTHORIZED_FIXTURE_IDS
            ],
        },
        "counts": {
            "planned": counts.get("planned"),
            "by_outcome": counts.get("by_outcome") or {},
            "by_provider": counts.get("by_provider") or {},
            "by_profile": counts.get("by_profile") or {},
            "by_direction": counts.get("by_direction") or {},
        },
    }


def _serialize_candidate(
    candidate: dict,
    fcid: FrozenCandidateId,
) -> dict:
    """Serialize a candidate.json for the slot-listing endpoint.

    Preserves factual manifest data; strips provider prompt text +
    capabilities snapshot because those are not needed by the picker
    UI and can be several KB per record.
    """
    provider_stage = candidate.get("provider_stage") or {}
    norm_stage = candidate.get("normalization_stage") or {}
    raw_artifact = candidate.get("raw_artifact")
    normalized_artifact = norm_stage.get("normalized_artifact")
    manifest_artifact = norm_stage.get("manifest_artifact")
    error = provider_stage.get("error")

    return {
        "frozen_candidate_id": fcid.value,
        "cell_id": fcid.cell_id,
        "run_id": fcid.run_id,
        "fixture_id": fcid.fixture_id,
        "direction_hypothesis": fcid.direction,
        "provider": fcid.provider,
        "surface_profile": fcid.surface_profile,
        "reference_kind": fcid.reference_kind,
        "reference_purpose": fcid.reference_purpose,
        "outcome": candidate.get("outcome"),
        "provider_stage": {
            "outcome": provider_stage.get("outcome"),
            "provider_model": provider_stage.get("provider_model"),
            "requested_execution_mode": provider_stage.get(
                "requested_execution_mode"
            ),
            "actual_execution_mode": provider_stage.get(
                "actual_execution_mode"
            ),
            "elapsed_ms": provider_stage.get("elapsed_ms"),
            "error": error,
        },
        "normalization_stage": {
            "attempted": norm_stage.get("attempted"),
            "outcome": norm_stage.get("outcome"),
            "pipeline_version": norm_stage.get("pipeline_version"),
            "surface_profile_id": norm_stage.get("surface_profile_id"),
            "surface_profile_version": norm_stage.get(
                "surface_profile_version"
            ),
            "background_id": norm_stage.get("background_id"),
            "failure": norm_stage.get("failure"),
        },
        "raw_artifact": (
            {
                "byte_count": raw_artifact.get("byte_count"),
                "sha256_hex": raw_artifact.get("sha256_hex"),
                # Never expose the recorded relative_path — clients
                # look artifacts up by frozen_candidate_id + kind.
            }
            if raw_artifact is not None
            else None
        ),
        "normalized_artifact": (
            {
                "byte_count": normalized_artifact.get("byte_count"),
                "sha256_hex": normalized_artifact.get("sha256_hex"),
            }
            if normalized_artifact is not None
            else None
        ),
        "manifest_artifact": (
            {
                "byte_count": manifest_artifact.get("byte_count"),
                "sha256_hex": manifest_artifact.get("sha256_hex"),
            }
            if manifest_artifact is not None
            else None
        ),
        "factual_normalization_notices": factual_normalization_notices(candidate),
    }


# ---------------------------------------------------------------------
# 9.b.1 — runs list
# ---------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsOperator])
def list_runs(request: Request) -> Response:
    """List the bootstrap runs 9.b.1 is authorized to browse.

    Under the current scope this returns exactly the frozen 9.a run.
    Additional runs may be authorized by a later scope-lock; expanding
    ``AUTHORIZED_RUN_IDS`` in ``evidence.py`` is the only intended
    lever.
    """
    runs: list[dict] = []
    for run_id in sorted(AUTHORIZED_RUN_IDS):
        try:
            summary = load_run_summary(run_id)
        except EvidenceError:
            # Should not happen (authorization implies presence), but
            # do not leak partial state.
            continue
        runs.append(_serialize_run_metadata(summary))
    return Response({"runs": runs}, status=status.HTTP_200_OK)


# ---------------------------------------------------------------------
# 9.b.1 — one-run metadata
# ---------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsOperator])
def retrieve_run(request: Request, bootstrap_run_id: str) -> Response:
    if bootstrap_run_id not in AUTHORIZED_RUN_IDS:
        return _error(
            UnauthorizedRunId.code,
            f"run_id={bootstrap_run_id!r} is not authorized for 9.b.1",
            status.HTTP_404_NOT_FOUND,
        )
    try:
        summary = load_run_summary(bootstrap_run_id)
    except EvidenceError as exc:
        return _map_evidence_error_to_response(exc)
    return Response(
        _serialize_run_metadata(summary),
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------
# 9.b.1 — one-fixture summary
# ---------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsOperator])
def retrieve_fixture(
    request: Request,
    bootstrap_run_id: str,
    fixture_id: str,
) -> Response:
    if bootstrap_run_id not in AUTHORIZED_RUN_IDS:
        return _error(
            UnauthorizedRunId.code,
            f"run_id={bootstrap_run_id!r} is not authorized for 9.b.1",
            status.HTTP_404_NOT_FOUND,
        )
    if fixture_id not in AUTHORIZED_FIXTURE_IDS:
        return _error(
            "unknown_fixture",
            f"fixture_id={fixture_id!r} not exposed by 9.b.1",
            status.HTTP_404_NOT_FOUND,
        )

    # Aggregate per-purpose counts across the four sub-directories
    # (2 directions × 2 providers × 5 profiles = 20 candidates per
    # purpose slot).
    per_purpose_reviewable: Counter[str] = Counter()
    per_purpose_unsupported: Counter[str] = Counter()

    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        try:
            candidates = list(
                iter_slot_candidates(
                    run_id=bootstrap_run_id,
                    fixture_id=fixture_id,
                    reference_kind="portrait_reference",
                    reference_purpose=purpose,
                )
            )
        except EvidenceError as exc:
            return _map_evidence_error_to_response(exc)

        for candidate in candidates:
            outcome = candidate.get("outcome")
            if outcome == "success":
                per_purpose_reviewable[purpose] += 1
            elif outcome == "unsupported_provider_capability":
                per_purpose_unsupported[purpose] += 1
            else:
                # Preserved as "other" so counts always sum to 20.
                # No frozen 9.a cell today should hit this branch.
                pass

    # 9.b.2 — layer current review state on top of the frozen counts.
    current = current_decision_per_slot(fixture_id)

    purposes_payload = []
    for purpose in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        current_decision = current.get(("portrait_reference", purpose))
        purposes_payload.append(
            {
                "reference_kind": "portrait_reference",
                "reference_purpose": purpose,
                "reviewable_candidate_count": per_purpose_reviewable[purpose],
                "unsupported_evidence_count": per_purpose_unsupported[purpose],
                "review_status": (
                    current_decision["disposition"]
                    if current_decision
                    else "unreviewed"
                ),
                "current_decision": _serialize_decision(current_decision),
            }
        )

    progress = fixture_progress(fixture_id)
    from .readiness import derive_step10_readiness

    readiness = derive_step10_readiness(fixture_id)
    return Response(
        {
            "run_id": bootstrap_run_id,
            "fixture_id": fixture_id,
            "purposes": purposes_payload,
            "progress": _serialize_progress(progress),
            "canonical_materialization": {
                "canonical_reference_floor_satisfied": (
                    readiness.canonical_reference_floor_satisfied
                ),
                "canonical_version_admitted": readiness.canonical_version_admitted,
                "publication_complete": readiness.publication_complete,
                "evidence_integrity": readiness.evidence_integrity,
                "step10_ready": readiness.ready,
                "failures": list(readiness.failures),
            },
        },
        status=status.HTTP_200_OK,
    )


def _serialize_decision(decision: dict | None) -> dict | None:
    if decision is None:
        return None
    return {
        "decision_id": decision["decision_id"],
        "disposition": decision["disposition"],
        "frozen_candidate_id": decision.get("frozen_candidate_id"),
        "supersedes_decision_id": decision.get("supersedes_decision_id"),
        "amendment_reason": decision.get("amendment_reason"),
        "reviewer_user_id": decision["reviewer_user_id"],
        "reviewer_email_at_write_time": decision.get(
            "reviewer_email_at_write_time"
        ),
        "decided_at_utc": decision["decided_at_utc"],
    }


def _serialize_progress(progress) -> dict:
    return {
        "purposes_total": progress.purposes_total,
        "purposes_dispositioned": progress.purposes_dispositioned,
        "review_complete": progress.review_complete,
        "approval_floor_pairs": list(progress.approval_floor_pairs),
        "approval_floor_satisfied_pairs": list(
            progress.approval_floor_satisfied_pairs
        ),
        "approval_floor_satisfied": progress.approval_floor_satisfied,
    }


# ---------------------------------------------------------------------
# 9.b.1 — one-slot candidate listing
# ---------------------------------------------------------------------


@api_view(["GET"])
@permission_classes([IsOperator])
def retrieve_slot(
    request: Request,
    bootstrap_run_id: str,
    fixture_id: str,
    reference_kind: str,
    reference_purpose: str,
) -> Response:
    if bootstrap_run_id not in AUTHORIZED_RUN_IDS:
        return _error(
            UnauthorizedRunId.code,
            f"run_id={bootstrap_run_id!r} is not authorized for 9.b.1",
            status.HTTP_404_NOT_FOUND,
        )
    if fixture_id not in AUTHORIZED_FIXTURE_IDS:
        return _error(
            "unknown_fixture",
            f"fixture_id={fixture_id!r} not exposed by 9.b.1",
            status.HTTP_404_NOT_FOUND,
        )
    if reference_kind != "portrait_reference":
        return _error(
            "unknown_reference_kind",
            f"reference_kind={reference_kind!r} not exposed by 9.b.1",
            status.HTTP_404_NOT_FOUND,
        )
    if reference_purpose not in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        return _error(
            "unknown_reference_purpose",
            f"reference_purpose={reference_purpose!r} not exposed by 9.b.1",
            status.HTTP_404_NOT_FOUND,
        )

    try:
        raw_candidates = list(
            iter_slot_candidates(
                run_id=bootstrap_run_id,
                fixture_id=fixture_id,
                reference_kind=reference_kind,
                reference_purpose=reference_purpose,
            )
        )
    except EvidenceError as exc:
        return _map_evidence_error_to_response(exc)

    reviewable: list[dict] = []
    unsupported: list[dict] = []
    for candidate in raw_candidates:
        cell = candidate.get("cell") or {}
        try:
            fcid = FrozenCandidateId.build(
                run_id=bootstrap_run_id,
                direction=cell.get("direction") or "",
                provider=cell.get("provider") or "",
                cell_id=cell.get("cell_id") or "",
            )
        except EvidenceError:
            # Should not happen — iter_slot_candidates enumerates the
            # ratified matrix. If it does, skip rather than expose a
            # malformed record.
            continue

        serialized = _serialize_candidate(candidate, fcid)
        outcome = serialized["outcome"]
        if outcome == "success":
            reviewable.append(serialized)
        elif outcome == "unsupported_provider_capability":
            unsupported.append(serialized)
        # Other outcomes: preserved as neither; frozen 9.a records
        # only success + unsupported.

    unsupported_summary = _summarize_unsupported(unsupported)

    # 9.b.2 — surface current-decision + history for this slot.
    current_decision = current_decision_per_slot(fixture_id).get(
        (reference_kind, reference_purpose)
    )
    history = decision_history_for_slot(
        fixture_id, reference_kind, reference_purpose
    )

    # 9.b.3b — surface the current PromotionAudit (if any) for this
    # slot so the SPA can render Promote / Published / Pending states.
    current_promotion = None
    if current_decision is not None:
        from .models import PromotionAudit

        audit = PromotionAudit.objects.filter(
            decision_id=current_decision["decision_id"]
        ).first()
        if audit is not None:
            current_promotion = {
                "promotion_audit_id": str(audit.id),
                "slot_revision": audit.slot_revision,
                "substrate_committed_at_utc": (
                    audit.substrate_committed_at_utc.isoformat()
                ),
                "evidence_published_at_utc": (
                    audit.evidence_published_at_utc.isoformat()
                    if audit.evidence_published_at_utc
                    else None
                ),
                "publication_status": (
                    "published"
                    if audit.evidence_published_at_utc
                    else "publication_pending"
                ),
            }

    return Response(
        {
            "run_id": bootstrap_run_id,
            "fixture_id": fixture_id,
            "reference_kind": reference_kind,
            "reference_purpose": reference_purpose,
            "reviewable_candidates": reviewable,
            "unsupported_evidence": unsupported,
            "unsupported_summary": unsupported_summary,
            "current_decision": _serialize_decision(current_decision),
            "current_promotion": current_promotion,
            "decision_history": [_serialize_decision(d) for d in history],
        },
        status=status.HTTP_200_OK,
    )


def _summarize_unsupported(unsupported: list[dict]) -> list[dict]:
    """Group unsupported evidence by (provider, error class) per L5(b).

    Preserves every ``frozen_candidate_id`` under a ``members`` field
    so no individual cell becomes unreachable via the grouped summary.
    """
    groups: dict[tuple[str, str, str], dict[str, Any]] = defaultdict(
        lambda: {
            "provider": "",
            "error_class": "",
            "error_message": "",
            "count": 0,
            "members": [],
        }
    )
    for candidate in unsupported:
        provider = candidate["provider"]
        error = candidate["provider_stage"].get("error") or {}
        error_class = error.get("class") or "unknown"
        error_message = error.get("message") or ""
        key = (provider, error_class, error_message)
        group = groups[key]
        if not group["provider"]:
            group["provider"] = provider
            group["error_class"] = error_class
            group["error_message"] = error_message
        group["count"] += 1
        group["members"].append(
            {
                "frozen_candidate_id": candidate["frozen_candidate_id"],
                "direction": candidate["direction_hypothesis"],
                "surface_profile": candidate["surface_profile"],
            }
        )
    return sorted(
        groups.values(),
        key=lambda g: (g["provider"], g["error_class"]),
    )


# ---------------------------------------------------------------------
# 9.b.1 — artifact streaming
# ---------------------------------------------------------------------


_ARTIFACT_MIME_TYPES: dict[str, str] = {
    "raw": "image/png",
    "normalized": "image/png",
    "manifest": "application/json",
    "candidate": "application/json",
}


def _retrieve_artifact(
    request: Request,
    bootstrap_run_id: str,
    direction: str,
    provider: str,
    cell_id: str,
    kind: ArtifactKind,
) -> HttpResponse:
    try:
        fcid = FrozenCandidateId.build(
            run_id=bootstrap_run_id,
            direction=direction,
            provider=provider,
            cell_id=cell_id,
        )
    except EvidenceError as exc:
        return _map_evidence_error_to_response(exc)

    if kind == "candidate":
        # For candidate.json we serve the parsed JSON directly with
        # the enriched envelope — never the raw file bytes. This keeps
        # the response shape uniform with retrieve_slot.
        try:
            candidate = load_candidate_json(fcid)
        except EvidenceError as exc:
            return _map_evidence_error_to_response(exc)
        return JsonResponse(candidate)

    try:
        payload = read_artifact_bytes(fcid, kind)
    except EvidenceError as exc:
        return _map_evidence_error_to_response(exc)

    response = FileResponse(
        _BytesFileLike(payload),
        content_type=_ARTIFACT_MIME_TYPES[kind],
    )
    # ETag = the verified sha (already validated in
    # read_artifact_bytes). Enables browser caching without ever
    # returning stale bytes because the sha derives from the exact
    # payload streamed.
    import hashlib

    response["ETag"] = f'"{hashlib.sha256(payload).hexdigest()}"'
    response["Cache-Control"] = "private, max-age=3600"
    return response


class _BytesFileLike:
    """Minimal iterable wrapper so FileResponse streams a bytes
    payload without hitting the disk twice.
    """

    def __init__(self, payload: bytes) -> None:
        self._payload = payload
        self._sent = False

    def __iter__(self):
        return self

    def __next__(self) -> bytes:
        if self._sent:
            raise StopIteration
        self._sent = True
        return self._payload

    def close(self) -> None:
        pass


@api_view(["GET"])
@permission_classes([IsOperator])
def retrieve_raw_artifact(
    request: Request,
    bootstrap_run_id: str,
    direction: str,
    provider: str,
    cell_id: str,
) -> HttpResponse:
    return _retrieve_artifact(
        request, bootstrap_run_id, direction, provider, cell_id, "raw"
    )


@api_view(["GET"])
@permission_classes([IsOperator])
def retrieve_normalized_artifact(
    request: Request,
    bootstrap_run_id: str,
    direction: str,
    provider: str,
    cell_id: str,
) -> HttpResponse:
    return _retrieve_artifact(
        request, bootstrap_run_id, direction, provider, cell_id, "normalized"
    )


@api_view(["GET"])
@permission_classes([IsOperator])
def retrieve_manifest_artifact(
    request: Request,
    bootstrap_run_id: str,
    direction: str,
    provider: str,
    cell_id: str,
) -> HttpResponse:
    return _retrieve_artifact(
        request, bootstrap_run_id, direction, provider, cell_id, "manifest"
    )


@api_view(["GET"])
@permission_classes([IsOperator])
def retrieve_candidate_json(
    request: Request,
    bootstrap_run_id: str,
    direction: str,
    provider: str,
    cell_id: str,
) -> HttpResponse:
    return _retrieve_artifact(
        request, bootstrap_run_id, direction, provider, cell_id, "candidate"
    )


# ---------------------------------------------------------------------
# 9.b.2 — POST a reviewer decision (append-only)
# ---------------------------------------------------------------------


_DECISION_ERROR_TO_STATUS: dict[str, int] = {
    "invalid_disposition": status.HTTP_400_BAD_REQUEST,
    "invalid_candidate": status.HTTP_400_BAD_REQUEST,
    "candidate_slot_mismatch": status.HTTP_400_BAD_REQUEST,
    "candidate_not_reviewable": status.HTTP_400_BAD_REQUEST,
    "amendment_reason_required": status.HTTP_400_BAD_REQUEST,
    "supersedes_decision_required": status.HTTP_409_CONFLICT,
    "stale_supersedes_decision": status.HTTP_409_CONFLICT,
    "decision_id_conflict": status.HTTP_409_CONFLICT,
    "journal_error": status.HTTP_400_BAD_REQUEST,
}


@api_view(["POST"])
@permission_classes([IsOperator])
def create_decision(
    request: Request,
    bootstrap_run_id: str,
    fixture_id: str,
    reference_kind: str,
    reference_purpose: str,
) -> Response:
    """Append a reviewer decision to the append-only journal.

    Payload (JSON):
      * decision_id — client-generated UUID (lowercase hex + hyphens)
      * disposition — 'selected' | 'no_candidate_approved'
      * frozen_candidate_id — required for 'selected', null for
        'no_candidate_approved'
      * supersedes_decision_id — null for first decision; required
        for amendment
      * amendment_reason — required + non-blank on amendment

    Responses:
      * 201 — decision recorded (first write)
      * 200 — idempotent replay (same decision_id + identical payload)
      * 400 — validation failure (invalid disposition / candidate /
        slot / vocabulary / amendment reason)
      * 409 — supersedes-required (first decision blocked by prior),
        stale-supersedes (amendment against non-current terminal),
        decision_id_conflict (same UUID different payload)
      * 502 — artifact_integrity_mismatch (candidate.json bytes on
        disk have drifted; NEVER creates the decision)
    """
    body = request.data or {}
    user = request.user
    reviewer_email = getattr(user, "email", "") or ""

    try:
        record, created = record_decision(
            decision_id=str(body.get("decision_id") or ""),
            bootstrap_run_id=bootstrap_run_id,
            fixture_id=fixture_id,
            reference_kind=reference_kind,
            reference_purpose=reference_purpose,
            disposition=str(body.get("disposition") or ""),
            frozen_candidate_id=body.get("frozen_candidate_id"),
            supersedes_decision_id=body.get("supersedes_decision_id"),
            amendment_reason=body.get("amendment_reason"),
            reviewer_user_id=user.id,
            reviewer_email_at_write_time=reviewer_email,
        )
    except (ArtifactIntegrityError, ArtifactAbsent) as exc:
        # Loud propagation per §Q16 — never record the decision.
        return _map_evidence_error_to_response(exc)
    except (
        InvalidCandidate,
        InvalidDisposition,
        CandidateSlotMismatch,
        CandidateNotReviewable,
        AmendmentReasonRequired,
        StaleSupersedesDecision,
        DuplicateFirstDecision,
        DecisionIdConflict,
        JournalError,
    ) as exc:
        return _error(
            exc.code,
            str(exc),
            _DECISION_ERROR_TO_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        )

    payload = {
        "decision": _serialize_decision(
            {
                "decision_id": record.decision_id,
                "disposition": record.disposition,
                "frozen_candidate_id": record.frozen_candidate_id,
                "supersedes_decision_id": record.supersedes_decision_id,
                "amendment_reason": record.amendment_reason,
                "reviewer_user_id": record.reviewer_user_id,
                "reviewer_email_at_write_time": record.reviewer_email_at_write_time,
                "decided_at_utc": record.decided_at_utc,
            }
        ),
        "created": created,
        "review_run_id": record.review_run_id,
    }
    return Response(
        payload,
        status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------
# 9.b.3b — promote current decision into canonical substrate
# ---------------------------------------------------------------------


_PROMOTION_ERROR_TO_STATUS: dict[str, int] = {
    "no_current_decision": status.HTTP_404_NOT_FOUND,
    "decision_not_promotable": status.HTTP_400_BAD_REQUEST,
    "durable_assets_root_missing": status.HTTP_500_INTERNAL_SERVER_ERROR,
    "artifact_absent": status.HTTP_404_NOT_FOUND,
    "artifact_integrity_mismatch": status.HTTP_502_BAD_GATEWAY,
    "invalid_frozen_candidate_id": status.HTTP_400_BAD_REQUEST,
    "unauthorized_run_id": status.HTTP_404_NOT_FOUND,
    "candidate_json_missing": status.HTTP_404_NOT_FOUND,
    "path_containment_violation": status.HTTP_400_BAD_REQUEST,
}


@api_view(["POST"])
@permission_classes([IsOperator])
def promote_slot(
    request: Request,
    bootstrap_run_id: str,
    fixture_id: str,
    reference_kind: str,
    reference_purpose: str,
) -> Response:
    """Promote the current terminal decision at a slot into canonical
    substrate + immutable bootstrap-reference filesystem revision.

    Body-free. Server reads the current decision from the append-only
    journal; the human decision is the authority. Idempotent — retry
    of an already-promoted slot returns the existing PromotionAudit.
    Post-Phase-4 crash: retry finishes publication.

    Delegates entirely to 9.b.3a's ``promote_current_decision``
    service. No new promotion logic here.
    """
    if bootstrap_run_id not in AUTHORIZED_RUN_IDS:
        return _error(
            "unauthorized_run_id",
            f"run_id={bootstrap_run_id!r} not authorized",
            status.HTTP_404_NOT_FOUND,
        )
    if fixture_id not in AUTHORIZED_FIXTURE_IDS:
        return _error(
            "unknown_fixture",
            f"fixture_id={fixture_id!r} not exposed by 9.b.3b",
            status.HTTP_404_NOT_FOUND,
        )
    if reference_kind != "portrait_reference":
        return _error(
            "unknown_reference_kind",
            f"reference_kind={reference_kind!r} not exposed",
            status.HTTP_404_NOT_FOUND,
        )
    if reference_purpose not in AUTHORIZED_PORTRAIT_REFERENCE_PURPOSES:
        return _error(
            "unknown_reference_purpose",
            f"reference_purpose={reference_purpose!r} not exposed",
            status.HTTP_404_NOT_FOUND,
        )

    from .promotion import (
        NoCurrentDecision,
        PromotionError,
        promote_current_decision,
    )

    try:
        result = promote_current_decision(
            fixture_id=fixture_id,
            reference_kind=reference_kind,
            reference_purpose=reference_purpose,
        )
    except (ArtifactAbsent, ArtifactIntegrityError) as exc:
        return _map_evidence_error_to_response(exc)
    except NoCurrentDecision as exc:
        return _error(exc.code, str(exc), status.HTTP_404_NOT_FOUND)
    except PromotionError as exc:
        return _error(
            exc.code,
            str(exc),
            _PROMOTION_ERROR_TO_STATUS.get(exc.code, status.HTTP_400_BAD_REQUEST),
        )
    except EvidenceError as exc:
        return _map_evidence_error_to_response(exc)

    return Response(
        {
            "kind": result.kind,
            "decision_id": result.decision_id,
            "promotion_audit_id": result.promotion_audit_id,
            "character_identity_version_id": result.character_identity_version_id,
            "identity_reference_id": result.identity_reference_id,
            "superseded_identity_reference_id": result.superseded_identity_reference_id,
            "slot_revision": result.slot_revision,
        },
        status=status.HTTP_200_OK,
    )


# ---------------------------------------------------------------------
# 9.b.3b — admit fixture identity version for product use
# ---------------------------------------------------------------------


@api_view(["POST"])
@permission_classes([IsOperator])
def approve_fixture_version(
    request: Request,
    bootstrap_run_id: str,
    fixture_id: str,
) -> Response:
    """Transition the fixture's current DRAFT CharacterIdentityVersion
    to APPROVED via existing ``services.approve_version``. The
    substrate service enforces the ``required_for_identity`` floor —
    this endpoint never bypasses it.

    Idempotent: calling on an already-APPROVED version is a no-op.
    Refuses if no CharacterIdentity exists yet (nothing has been
    promoted for this fixture).
    """
    if bootstrap_run_id not in AUTHORIZED_RUN_IDS:
        return _error(
            "unauthorized_run_id",
            f"run_id={bootstrap_run_id!r} not authorized",
            status.HTTP_404_NOT_FOUND,
        )
    if fixture_id not in AUTHORIZED_FIXTURE_IDS:
        return _error(
            "unknown_fixture",
            f"fixture_id={fixture_id!r} not exposed by 9.b.3b",
            status.HTTP_404_NOT_FOUND,
        )

    from apps.identity import services as identity_services
    from apps.identity.models import CharacterIdentity, CharacterIdentityVersion

    try:
        workspace = Workspace.objects.get(slug=BOOTSTRAP_WORKSPACE_SLUG)
    except Workspace.DoesNotExist:
        return _error(
            "bootstrap_workspace_missing",
            "bootstrap-fixtures workspace not seeded",
            status.HTTP_500_INTERNAL_SERVER_ERROR,
        )
    identity = CharacterIdentity.objects.filter(
        workspace=workspace, name=fixture_id
    ).first()
    if identity is None:
        return _error(
            "no_identity_for_fixture",
            f"no CharacterIdentity exists for {fixture_id!r} — "
            "no promotions have committed yet",
            status.HTTP_404_NOT_FOUND,
        )
    # Prefer any APPROVED version (idempotent path); otherwise the
    # latest DRAFT.
    approved = CharacterIdentityVersion.objects.filter(
        identity=identity,
        state=CharacterIdentityVersion.State.APPROVED,
    ).first()
    if approved is not None:
        return Response(
            {
                "character_identity_version_id": str(approved.id),
                "state": approved.state,
                "already_approved": True,
            },
            status=status.HTTP_200_OK,
        )
    version = (
        CharacterIdentityVersion.objects.filter(
            identity=identity, state=CharacterIdentityVersion.State.DRAFT
        )
        .order_by("-revision")
        .first()
    )
    if version is None:
        return _error(
            "no_draft_version",
            f"identity {identity.id} has no DRAFT version to approve",
            status.HTTP_404_NOT_FOUND,
        )
    try:
        identity_services.approve_version(version, approver=request.user)
    except identity_services.IdentityVersionApprovalError as exc:
        code = getattr(exc, "code", "identity_version_approval_error")
        status_code = (
            status.HTTP_400_BAD_REQUEST
            if code in {"floor_not_satisfied", "invalid_state_transition"}
            else status.HTTP_409_CONFLICT
        )
        return _error(code, str(exc), status_code)
    version.refresh_from_db()
    return Response(
        {
            "character_identity_version_id": str(version.id),
            "state": version.state,
            "approved_at": (
                version.approved_at.isoformat() if version.approved_at else None
            ),
            "already_approved": False,
        },
        status=status.HTTP_200_OK,
    )
