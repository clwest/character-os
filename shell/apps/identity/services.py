"""Canonical Identity substrate — authoritative write path.

This module is the ratified write-path stack from §17.3.a: typed
schema validation, then a dedicated identity-version service that
owns all create / mutate transitions on identity versions. The
model layer carries defensive validation (``full_clean()``,
cross-workspace signals, append-only guards) as a belt-and-braces
layer beneath this service — never as the primary funnel.

Guardrails held here:

* ``approve_version`` is transactional and concurrency-safe. It
  locks the parent ``CharacterIdentity`` with
  ``select_for_update()``, reads the current-state view, then
  performs supersede + approve inside one ``transaction.atomic()``
  block (§17.3.b). Two legitimate service-level approvals of
  different versions serialize safely: both complete, exactly one
  version ends approved.
* Idempotent re-approval of the already-approved version is a
  no-op (§17.3.b).
* ``bulk_update()`` is deliberately never used for approval
  transitions.
* Approval floor is enforced against the branch schema's
  declarative ``required_for_identity`` — no hardcoded floor in
  this module (§17.5.b, Correction 5 to SESSION 241 plan).
* Constraint violations are converted into a stable domain
  exception (``IdentityVersionApprovalError``) with a
  discriminating ``.code`` (§17.3.b).
"""
from __future__ import annotations

from typing import Any

from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, models, transaction
from django.utils import timezone

from apps.compositions.models import Asset

from .models import (
    LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION,
    MIN_CANONICAL_SPEC_SCHEMA_VERSION,
    PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
    ApprovedRepresentationBundle,
    CanonicalRealtimeReference,
    CanonicalVoiceReference,
    CharacterIdentity,
    CharacterIdentityVersion,
    DirectionHypothesis,
    GenerationRecord,
    IdentityReference,
    IdentityReferenceKind,
    ImportProvenance,
    NormalizationManifest,
    PrequalificationProvenance,
    ReferenceState,
)
from .prequalification import (
    PortraitRepresentation,
    RealtimeRepresentation,
    VoiceRepresentation,
)
from .schema_loader import BranchSchema, get_branch_schema

User = get_user_model()


# ---------------------------------------------------------------------
# Domain exceptions
# ---------------------------------------------------------------------


class IdentityVersionError(Exception):
    """Base class for write-path errors. Carries a stable
    ``.code`` string so callers can branch on error class without
    depending on message text.
    """

    code: str = "unknown"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class IdentityVersionSpecInvalid(IdentityVersionError):
    """Raised when a spec payload fails branch-schema validation
    (§17.3.a authoritative write path, step 1).
    """

    code = "spec_invalid"


class IdentityReferenceError(IdentityVersionError):
    """Raised when an ``IdentityReference`` cannot be attached —
    unknown branch, invalid (kind, purpose) pair, or
    cross-workspace asset.
    """

    code = "reference_invalid"


class IdentityVersionApprovalError(IdentityVersionError):
    """Raised by ``approve_version`` when the transition cannot
    proceed. ``code`` is one of:

    * ``floor_not_satisfied`` — the branch schema's
      ``required_for_identity`` is not met at ``state='approved'``
      on this version.
    * ``invalid_state_transition`` — the current state is not one
      the transition allows (e.g. approving a superseded /
      rejected version).
    * ``constraint_violation`` — the Postgres partial unique
      constraint fired. Should be rare when the service is used
      correctly; the database is the final defense against bypass
      or implementation defect.
    """

    code = "unknown"


class BundleApprovalError(IdentityVersionError):
    """Raised by ``approve_bundle`` / ``supersede_bundle`` when the
    transition cannot proceed (§17.10.a Amendment 4). ``code`` is
    one of:

    * ``invalid_state_transition`` — the current state does not
      allow the requested transition (e.g. approving an already-
      superseded bundle).
    * ``cross_identity_mismatch`` — a bundle FK (``approved_voice``
      / ``approved_realtime``) belongs to a different identity
      version than the bundle's own ``identity_version``.
    * ``missing_front_portrait`` — bundle approval requires an
      ``IdentityReference`` at ``(kind=portrait_reference,
      purpose='front', state='approved')`` on the bundle's version.
      This precondition is enforced here per Amendment 4 and is not
      hardcoded elsewhere; branch-schema declarative bundle
      requirements land in Steps 5+.
    * ``constraint_violation`` — the Postgres partial unique
      constraint on ``ApprovedRepresentationBundle
      (identity_version_id) WHERE state='approved'`` fired.
    """

    code = "unknown"


class ReferenceApprovalError(IdentityVersionError):
    """Raised by ``approve_reference`` when the transition cannot
    proceed (§17.10.a Amendment 4). ``code`` is one of:

    * ``invalid_state_transition`` — the current state does not
      allow approval (only RAW / NORMALIZED / PROVISIONAL / APPROVED
      transition into APPROVED; already-SUPERSEDED / REJECTED
      references cannot be re-approved).
    * ``constraint_violation`` — the Postgres partial unique
      constraint on ``IdentityReference (identity_version_id, kind,
      purpose) WHERE state='approved'`` fired.
    """

    code = "unknown"


class PrequalificationVersionApprovalError(IdentityVersionApprovalError):
    """Raised by ``approve_prequalification_version`` when the
    transition cannot proceed (§17.10.a Amendment 4). Inherits
    ``code`` values from ``IdentityVersionApprovalError`` plus:

    * ``missing_prequalification_provenance`` — the version has
      neither ``PrequalificationProvenance`` nor ``ImportProvenance``.
      The branch-schema floor bypass is not authorized for such a
      version; the caller should use ``services.approve_version``
      instead (the qualified path).
    """

    code = "unknown"


# ---------------------------------------------------------------------
# Draft authoring
# ---------------------------------------------------------------------


def _peek_next_revision(identity: CharacterIdentity) -> int:
    """Compute the next revision number for a locked identity.
    Caller must already hold ``select_for_update`` on ``identity``.
    """
    latest = (
        CharacterIdentityVersion.objects
        .filter(identity=identity)
        .order_by("-revision")
        .values_list("revision", flat=True)
        .first()
    )
    return (latest or 0) + 1


def create_draft_version(
    identity: CharacterIdentity,
    spec: dict,
    *,
    spec_schema_version: int,
) -> CharacterIdentityVersion:
    """Create a new draft version for ``identity``.

    Validates ``spec`` against the branch schema before persistence.
    Assigns the next monotonic revision inside a
    ``select_for_update`` window so concurrent draft creation
    against the same identity cannot double-assign a revision.

    Rejects ``spec_schema_version`` values below
    ``MIN_CANONICAL_SPEC_SCHEMA_VERSION`` (1). Value ``0`` is the
    reserved ``legacy_unvalidated`` sentinel and is writable
    exclusively by the Step 3 legacy-import service — the normal
    authoring write path must never accept it (§19 Step 3
    discipline, SESSION 242).
    """
    if spec_schema_version < MIN_CANONICAL_SPEC_SCHEMA_VERSION:
        raise IdentityVersionSpecInvalid(
            (
                f"spec_schema_version={spec_schema_version} is below the "
                f"minimum canonical value ({MIN_CANONICAL_SPEC_SCHEMA_VERSION}). "
                "Value 0 is the ``legacy_unvalidated`` sentinel and is "
                "writable only by the Step 3 legacy-import service."
            ),
            code="spec_invalid",
        )
    schema = get_branch_schema(identity.kind)
    try:
        schema.validate_spec(spec)
    except Exception as exc:
        raise IdentityVersionSpecInvalid(str(exc), code="spec_invalid") from exc

    with transaction.atomic():
        locked = (
            CharacterIdentity.objects.select_for_update().get(pk=identity.pk)
        )
        revision = _peek_next_revision(locked)
        return CharacterIdentityVersion.objects.create(
            identity=locked,
            revision=revision,
            state=CharacterIdentityVersion.State.DRAFT,
            spec=spec,
            spec_schema_version=spec_schema_version,
        )


def update_draft_spec(
    version: CharacterIdentityVersion,
    spec: dict,
    *,
    spec_schema_version: int,
) -> CharacterIdentityVersion:
    """Rewrite the spec on a draft version. Rejects any non-draft
    version. Re-validates against the branch schema.
    """
    if version.state != CharacterIdentityVersion.State.DRAFT:
        raise IdentityVersionError(
            f"Cannot update spec on version in state {version.state!r}; "
            "only draft versions accept spec edits.",
            code="invalid_state_transition",
        )
    if spec_schema_version < MIN_CANONICAL_SPEC_SCHEMA_VERSION:
        raise IdentityVersionSpecInvalid(
            (
                f"spec_schema_version={spec_schema_version} is below the "
                f"minimum canonical value ({MIN_CANONICAL_SPEC_SCHEMA_VERSION}); "
                "value 0 is reserved for the legacy-import service."
            ),
            code="spec_invalid",
        )
    schema = get_branch_schema(version.identity.kind)
    try:
        schema.validate_spec(spec)
    except Exception as exc:
        raise IdentityVersionSpecInvalid(str(exc), code="spec_invalid") from exc

    with transaction.atomic():
        version.spec = spec
        version.spec_schema_version = spec_schema_version
        version.save(update_fields=["spec", "spec_schema_version"])
    return version


# ---------------------------------------------------------------------
# Reference attachment
# ---------------------------------------------------------------------


def attach_reference(
    version: CharacterIdentityVersion,
    *,
    asset: Asset,
    kind: str,
    purpose: str,
    state: str = ReferenceState.RAW,
    generation_record: GenerationRecord | None = None,
) -> IdentityReference:
    """Attach an ``Asset`` to a version as a typed reference.

    Validates:

    * ``kind`` is a known artifact class enum value.
    * ``(kind, purpose)`` is enumerated in the branch's purpose
      schema (§17.5.a). Invalid pairs raise
      ``IdentityReferenceError(code='reference_invalid')``.
    * The asset shares a workspace with the identity (§7.5) —
      enforced via ``full_clean()`` on the reference.
    """
    valid_kinds = {choice.value for choice in IdentityReferenceKind}
    if kind not in valid_kinds:
        raise IdentityReferenceError(
            f"Unknown reference kind {kind!r}. Valid kinds: {sorted(valid_kinds)}.",
            code="reference_invalid",
        )

    schema = get_branch_schema(version.identity.kind)
    if not schema.validate_purpose(kind, purpose):
        raise IdentityReferenceError(
            f"Purpose {purpose!r} is not enumerated in the "
            f"{version.identity.kind!r} branch's purpose schema for "
            f"kind {kind!r}.",
            code="reference_invalid",
        )

    reference = IdentityReference(
        identity_version=version,
        asset=asset,
        kind=kind,
        purpose=purpose,
        state=state,
        generation_record=generation_record,
    )
    try:
        reference.full_clean()
    except ValidationError as exc:
        raise IdentityReferenceError(str(exc), code="reference_invalid") from exc
    reference.save()
    return reference


# ---------------------------------------------------------------------
# Generation + normalization records (immutable evidence)
# ---------------------------------------------------------------------


def record_generation(
    version: CharacterIdentityVersion,
    **fields: Any,
) -> GenerationRecord:
    """Record a provider generation attempt. Runs
    ``full_clean()`` so cross-workspace asset FKs are refused
    (§7.5). Immutability is guarded at the model layer along the
    supported ORM path.
    """
    record = GenerationRecord(identity_version=version, **fields)
    try:
        record.full_clean()
    except ValidationError as exc:
        raise IdentityVersionError(str(exc), code="generation_invalid") from exc
    record.save()
    return record


def record_normalization_manifest(
    generation_record: GenerationRecord,
    **fields: Any,
) -> NormalizationManifest:
    """Record the manifest describing a normalization pass over
    ``generation_record``.
    """
    manifest = NormalizationManifest(
        generation_record=generation_record, **fields
    )
    try:
        manifest.full_clean()
    except ValidationError as exc:
        raise IdentityVersionError(str(exc), code="manifest_invalid") from exc
    manifest.save()
    return manifest


# ---------------------------------------------------------------------
# Approval / supersede / reject
# ---------------------------------------------------------------------


def _floor_satisfied(
    version: CharacterIdentityVersion,
    schema: BranchSchema,
) -> tuple[bool, list[str]]:
    """Evaluate the ratified declarative approval floor
    (§17.5.b) against the version's currently-approved reference
    set. Returns ``(satisfied, missing)`` where ``missing`` is
    the authored ``<kind>/<purpose>`` strings that have no
    approved ``IdentityReference`` on the version.

    The floor is consumed as authored — no flattening or
    Python-side lowering.
    """
    approved_pairs = set(
        version.references
        .filter(state=ReferenceState.APPROVED)
        .values_list("kind", "purpose")
    )
    approved_str = {f"{kind}/{purpose}" for kind, purpose in approved_pairs}
    missing = [
        pair for pair in schema.required_for_identity
        if pair not in approved_str
    ]
    return (not missing, missing)


def approve_version(
    version: CharacterIdentityVersion,
    *,
    approver: models.Model | None,
) -> CharacterIdentityVersion:
    """Promote ``version`` to ``approved``. Supersedes the
    currently-approved version of the same identity, if any,
    inside one ``transaction.atomic()`` block.

    Concurrency semantics (§17.3.b):
      * ``CharacterIdentity`` row is locked with
        ``select_for_update()`` for the duration of the
        transition. Legitimate concurrent approvals of different
        versions serialize safely; the later caller sees the
        earlier winner as the currently-approved version and
        supersedes it.
      * Idempotent re-approval of the already-approved version is
        a no-op.
      * A partial-unique constraint violation is converted into
        ``IdentityVersionApprovalError(code='constraint_violation')``
        — that path indicates a bypass or implementation defect,
        not the expected outcome of correctly serialized service
        calls.

    ``bulk_update()`` is deliberately never used for approval
    transitions (§17.3.b).
    """
    with transaction.atomic():
        # Lock the parent identity for the duration of the
        # transition. All state reads that inform the decision
        # happen after this lock is acquired.
        locked_identity = (
            CharacterIdentity.objects.select_for_update().get(pk=version.identity_id)
        )

        # Refresh the version from DB under the lock — the caller
        # may have handed us a stale in-memory instance.
        try:
            fresh_version = CharacterIdentityVersion.objects.get(pk=version.pk)
        except CharacterIdentityVersion.DoesNotExist as exc:
            raise IdentityVersionApprovalError(
                "Version no longer exists.",
                code="invalid_state_transition",
            ) from exc

        if fresh_version.identity_id != locked_identity.pk:
            raise IdentityVersionApprovalError(
                "Version does not belong to the locked identity.",
                code="cross_identity_mismatch",
            )

        # Idempotent re-approval.
        if fresh_version.state == CharacterIdentityVersion.State.APPROVED:
            return fresh_version

        if fresh_version.state != CharacterIdentityVersion.State.DRAFT:
            raise IdentityVersionApprovalError(
                f"Cannot approve version in state {fresh_version.state!r}; "
                "only draft versions transition to approved.",
                code="invalid_state_transition",
            )

        # Declarative approval floor per §17.5.b — read from the
        # branch schema, not from hardcoded transition logic.
        schema = get_branch_schema(locked_identity.kind)
        ok, missing = _floor_satisfied(fresh_version, schema)
        if not ok:
            raise IdentityVersionApprovalError(
                (
                    "Approval floor not satisfied. Missing approved "
                    f"references: {missing}."
                ),
                code="floor_not_satisfied",
            )

        # Supersede the currently-approved version (if any) then
        # promote this one. Both writes live in the same
        # transaction and must succeed or roll back together. The
        # §5.6.a cascade of the prior version's APPROVED children
        # rides the shared helper — 4.c correction ensuring
        # approve_version and approve_prequalification_version and
        # supersede_version cannot drift on cascade shape.
        now = timezone.now()
        current = (
            CharacterIdentityVersion.objects
            .select_for_update()
            .filter(
                identity=locked_identity,
                state=CharacterIdentityVersion.State.APPROVED,
            )
            .first()
        )
        try:
            if current is not None and current.pk != fresh_version.pk:
                _supersede_version_and_cascade_children(current, now=now)

            fresh_version.state = CharacterIdentityVersion.State.APPROVED
            fresh_version.approved_at = now
            fresh_version.approved_by = approver
            fresh_version.save(
                update_fields=["state", "approved_at", "approved_by"]
            )
        except IntegrityError as exc:
            raise IdentityVersionApprovalError(
                "Partial unique constraint fired during approval; "
                "state was not modified.",
                code="constraint_violation",
            ) from exc

        # §19 Step 4.c — compatibility mirror synchronization inside
        # the same transaction. Same discipline as
        # approve_prequalification_version.
        _sync_teammate_mirrors_if_present(locked_identity)

    return fresh_version


def supersede_version(
    version: CharacterIdentityVersion,
    *,
    reason: str = "",
) -> CharacterIdentityVersion:
    """Move an approved version to ``superseded`` explicitly. The
    normal supersede-plus-approve path is inside ``approve_version``;
    this is the operator-directed hand of an approved version out
    of use without an incoming replacement.

    §19 Step 4.c: cascades the version's ``APPROVED`` children
    (bundle, references, canonical voice, canonical realtime) to
    ``SUPERSEDED`` via the shared helper so the substrate invariant
    "APPROVED children on a SUPERSEDED version is forbidden per
    §5.6.a" holds regardless of which service performed the
    transition. Also synchronizes the compatibility mirrors inside
    the same transaction — the operator-directed removal of the
    current-approved version leaves mirrors ``""``.
    """
    if version.state != CharacterIdentityVersion.State.APPROVED:
        raise IdentityVersionError(
            f"Cannot supersede version in state {version.state!r}; "
            "only approved versions transition to superseded.",
            code="invalid_state_transition",
        )
    with transaction.atomic():
        locked_identity = (
            CharacterIdentity.objects
            .select_for_update()
            .get(pk=version.identity_id)
        )
        now = timezone.now()
        # Fold the reviewer-notes update into the shared cascade
        # helper's version save by staging it on the instance first.
        # The helper writes ``state`` + ``superseded_at`` via
        # update_fields; ``reviewer_notes`` needs a follow-up save
        # here so the cascade helper's contract stays uniform across
        # its three callers.
        _supersede_version_and_cascade_children(version, now=now)
        if reason:
            existing = version.reviewer_notes or ""
            version.reviewer_notes = (existing + f"\nsuperseded: {reason}").strip()
            version.save(update_fields=["reviewer_notes"])

        # §19 Step 4.c — compatibility mirror synchronization inside
        # the same transaction. Since ``supersede_version`` removes
        # the current-approved version without a replacement, sync
        # clears the three mirrors to ``""``.
        _sync_teammate_mirrors_if_present(locked_identity)
    return version


def reject_version(
    version: CharacterIdentityVersion,
    *,
    reason: str = "",
) -> CharacterIdentityVersion:
    """Reject a draft version. Only draft versions are eligible.
    """
    if version.state != CharacterIdentityVersion.State.DRAFT:
        raise IdentityVersionError(
            f"Cannot reject version in state {version.state!r}; "
            "only draft versions transition to rejected.",
            code="invalid_state_transition",
        )
    with transaction.atomic():
        CharacterIdentity.objects.select_for_update().get(pk=version.identity_id)
        version.state = CharacterIdentityVersion.State.REJECTED
        if reason:
            existing = version.reviewer_notes or ""
            version.reviewer_notes = (existing + f"\nrejected: {reason}").strip()
        version.save(update_fields=["state", "reviewer_notes"])
    return version


# ---------------------------------------------------------------------
# Bundle assembly helpers (thin — the substrate carries the shape)
# ---------------------------------------------------------------------


def create_draft_bundle(
    version: CharacterIdentityVersion,
    *,
    approved_voice: CanonicalVoiceReference | None = None,
    approved_realtime: CanonicalRealtimeReference | None = None,
) -> ApprovedRepresentationBundle:
    """Create a draft bundle bound to ``version``. The bundle's
    domain contract exposes canonical approved representations
    only (§17.4.a); no provider identifiers cross this boundary.
    """
    if approved_voice is not None and approved_voice.identity_version_id != version.pk:
        raise IdentityVersionError(
            "approved_voice belongs to a different identity version.",
            code="cross_identity_mismatch",
        )
    if approved_realtime is not None and approved_realtime.identity_version_id != version.pk:
        raise IdentityVersionError(
            "approved_realtime belongs to a different identity version.",
            code="cross_identity_mismatch",
        )
    return ApprovedRepresentationBundle.objects.create(
        identity_version=version,
        approved_voice=approved_voice,
        approved_realtime=approved_realtime,
        state=ApprovedRepresentationBundle.State.DRAFT,
    )


# ---------------------------------------------------------------------
# 4.a — Reference approval with SUPERSEDED slot replacement
#       (§17.10.a Amendment 4).
# ---------------------------------------------------------------------


def approve_reference(
    reference: IdentityReference,
    *,
    approver: models.Model | None = None,
) -> IdentityReference:
    """Promote an ``IdentityReference`` to ``state='approved'``.

    Transactionally supersedes any prior ``APPROVED`` reference
    occupying the same ``(identity_version, kind, purpose)`` slot on
    this version, moving it to ``SUPERSEDED`` (never ``REJECTED``).
    Distinct histories: ``REJECTED`` = candidate never admitted;
    ``SUPERSEDED`` = was ``APPROVED`` and a newer authoring event
    admitted a replacement into the same slot (§17.10.a Amendment 4,
    ratified 2026-08-07).

    Concurrency semantics:

    * ``CharacterIdentity`` locked with ``select_for_update()`` for
      the duration of the transition. Concurrent approvals of
      different references at the same slot serialize; the later
      caller sees the earlier winner as the currently-approved
      occupant and supersedes it.
    * Idempotent re-approval of an already-``APPROVED`` reference is
      a no-op.
    * The Postgres partial unique constraint on
      ``IdentityReference (identity_version_id, kind, purpose) WHERE
      state='approved'`` is the final race guard; a constraint
      violation surfaces as
      ``ReferenceApprovalError(code='constraint_violation')``.

    ``approver`` is accepted for signature symmetry with other
    approval services but is not currently persisted on
    ``IdentityReference`` (§7 model shape has no approver field).
    Reserved for future use.
    """
    with transaction.atomic():
        locked_identity = (
            CharacterIdentity.objects
            .select_for_update()
            .get(pk=reference.identity_version.identity_id)
        )

        try:
            fresh = IdentityReference.objects.get(pk=reference.pk)
        except IdentityReference.DoesNotExist as exc:
            raise ReferenceApprovalError(
                "Reference no longer exists.",
                code="invalid_state_transition",
            ) from exc

        if fresh.identity_version.identity_id != locked_identity.pk:
            raise ReferenceApprovalError(
                "Reference does not belong to the locked identity.",
                code="cross_identity_mismatch",
            )

        # Idempotent re-approval — legal at any parent-version state
        # because it is a no-op. Only actual transitions require the
        # parent-DRAFT guard below.
        if fresh.state == ReferenceState.APPROVED:
            return fresh

        # §19 Step 4.c — §5.4 immutability guard. Approving a new
        # reference into an APPROVED / SUPERSEDED / REJECTED version's
        # slot would mutate its approved reference view set (§5.4:
        # "Any change to the approved reference view set" requires a
        # new version). Refuse with a stable domain error telling the
        # caller to author a new version.
        parent_state = fresh.identity_version.state
        if parent_state != CharacterIdentityVersion.State.DRAFT:
            raise ReferenceApprovalError(
                (
                    "Cannot approve a reference on a version in state "
                    f"{parent_state!r}; §5.4 makes approved identity "
                    "versions immutable with respect to their approved "
                    "reference view set. Author a new CharacterIdentity"
                    "Version (draft) and attach the replacement "
                    "reference there."
                ),
                code="parent_version_not_draft",
            )

        allowed_from = {
            ReferenceState.RAW,
            ReferenceState.NORMALIZED,
            ReferenceState.PROVISIONAL,
        }
        if fresh.state not in allowed_from:
            raise ReferenceApprovalError(
                (
                    f"Cannot approve reference in state {fresh.state!r}; "
                    "only RAW / NORMALIZED / PROVISIONAL transition to "
                    "APPROVED. SUPERSEDED and REJECTED are terminal."
                ),
                code="invalid_state_transition",
            )

        # Supersede any prior APPROVED occupant of the same slot.
        prior = (
            IdentityReference.objects
            .select_for_update()
            .filter(
                identity_version=fresh.identity_version,
                kind=fresh.kind,
                purpose=fresh.purpose,
                state=ReferenceState.APPROVED,
            )
            .exclude(pk=fresh.pk)
            .first()
        )
        try:
            if prior is not None:
                prior.state = ReferenceState.SUPERSEDED
                prior.save(update_fields=["state"])

            fresh.state = ReferenceState.APPROVED
            fresh.save(update_fields=["state"])
        except IntegrityError as exc:
            raise ReferenceApprovalError(
                (
                    "Partial unique constraint fired during reference "
                    "approval; state was not modified."
                ),
                code="constraint_violation",
            ) from exc

    # §19 Step 4.c — approve_reference is an assembly-time service.
    # Its parent version is (by the guard above) DRAFT, so it cannot
    # affect the mirror-derivation walk (which visits APPROVED
    # versions only). No compatibility-mirror synchronization needed.
    # Mirrors update when the version is promoted via
    # ``approve_version`` / ``approve_prequalification_version``.
    return fresh


def supersede_reference_at_slot(
    version: CharacterIdentityVersion,
    *,
    kind: str,
    purpose: str,
    reason: str = "",
) -> IdentityReference | None:
    """Transition the current APPROVED ``IdentityReference`` at the
    ``(version, kind, purpose)`` slot to ``SUPERSEDED`` without
    admitting a replacement.

    Substrate-generic (§19 Step 9.b.3a caller: bootstrap-review's
    ``selected → no_candidate_approved`` amendment materialization).
    Mirrors the existing ``supersede_version`` + ``supersede_bundle``
    patterns.

    Semantics:

    * Idempotent when no APPROVED occupant exists — returns ``None``
      without raising. The caller (typically an amendment resume
      pass) is safe to invoke it against any slot without a
      pre-check.
    * Transactional. Locks ``CharacterIdentity`` with
      ``select_for_update`` for the duration of the transition —
      concurrent supersede attempts at the same slot serialize
      safely.
    * Refuses to operate on a non-DRAFT parent version — §5.4 makes
      approved identity versions immutable with respect to their
      approved reference view set.
    * Does not create any replacement row.
    * Does not touch evidence rows (``GenerationRecord``,
      ``NormalizationManifest``, or ``Asset``) — those remain the
      immutable per-provider-call evidence of the (now superseded)
      admission.
    * ``reason`` is appended to the reference's ``reviewer_notes``
      when supplied.
    """
    with transaction.atomic():
        locked_identity = (
            CharacterIdentity.objects
            .select_for_update()
            .get(pk=version.identity_id)
        )

        # §5.4 immutability guard — same as approve_reference.
        try:
            fresh_version = CharacterIdentityVersion.objects.get(pk=version.pk)
        except CharacterIdentityVersion.DoesNotExist as exc:
            raise IdentityReferenceError(
                "Version no longer exists.",
                code="invalid_state_transition",
            ) from exc

        if fresh_version.identity_id != locked_identity.pk:
            raise IdentityReferenceError(
                "Version does not belong to the locked identity.",
                code="cross_identity_mismatch",
            )

        if fresh_version.state != CharacterIdentityVersion.State.DRAFT:
            raise IdentityReferenceError(
                (
                    "Cannot supersede a reference on a version in state "
                    f"{fresh_version.state!r}; §5.4 makes approved identity "
                    "versions immutable with respect to their approved "
                    "reference view set."
                ),
                code="parent_version_not_draft",
            )

        current = (
            IdentityReference.objects
            .select_for_update()
            .filter(
                identity_version=fresh_version,
                kind=kind,
                purpose=purpose,
                state=ReferenceState.APPROVED,
            )
            .first()
        )
        if current is None:
            # Idempotent no-op — no occupant to supersede.
            return None

        current.state = ReferenceState.SUPERSEDED
        update_fields = ["state"]
        if reason:
            existing = current.reviewer_notes or ""
            current.reviewer_notes = (
                existing + f"\nsuperseded: {reason}"
            ).strip()
            update_fields.append("reviewer_notes")
        current.save(update_fields=update_fields)
    return current


# ---------------------------------------------------------------------
# 4.a — Bundle approval / supersede (§17.10.a Amendment 4).
# ---------------------------------------------------------------------


def _bundle_has_front_portrait_reference(
    version: CharacterIdentityVersion,
) -> bool:
    """Return True iff ``version`` has an ``IdentityReference`` at
    ``(kind=portrait_reference, purpose='front', state='approved')``.
    Amendment 4 bundle-approval precondition; kept as a local helper
    (not on the model) because the branch-schema declarative
    bundle-requirement discipline lands in Steps 5+.
    """
    return (
        IdentityReference.objects.filter(
            identity_version=version,
            kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
            purpose="front",
            state=ReferenceState.APPROVED,
        )
        .exists()
    )


def approve_bundle(
    bundle: ApprovedRepresentationBundle,
    *,
    approver: models.Model | None = None,
) -> ApprovedRepresentationBundle:
    """Promote an ``ApprovedRepresentationBundle`` from ``DRAFT`` to
    ``APPROVED`` (§17.10.a Amendment 4).

    Preconditions:

    * The bundle's version has a ``portrait_reference/front`` at
      ``state='approved'``. Amendment 4's bundle-approval invariant.
      Consumed here; not hardcoded elsewhere. When the branch schema
      declares bundle requirements declaratively (Steps 5+), this
      check migrates to the declarative form.
    * If ``approved_voice`` is set, it belongs to the same version.
    * If ``approved_realtime`` is set, it belongs to the same
      version.

    Concurrency semantics:

    * ``CharacterIdentity`` locked with ``select_for_update()`` for
      the duration of the transition.
    * Any prior ``APPROVED`` bundle on the same version is
      superseded transactionally before the new bundle is approved.
      The Postgres partial unique constraint on
      ``ApprovedRepresentationBundle (identity_version_id) WHERE
      state='approved'`` is the final race guard.
    * Idempotent re-approval of the already-``APPROVED`` bundle is
      a no-op.

    ``approver`` is persisted on the bundle's ``approved_by`` field.
    """
    with transaction.atomic():
        locked_identity = (
            CharacterIdentity.objects
            .select_for_update()
            .get(pk=bundle.identity_version.identity_id)
        )

        try:
            fresh = ApprovedRepresentationBundle.objects.get(pk=bundle.pk)
        except ApprovedRepresentationBundle.DoesNotExist as exc:
            raise BundleApprovalError(
                "Bundle no longer exists.",
                code="invalid_state_transition",
            ) from exc

        if fresh.identity_version.identity_id != locked_identity.pk:
            raise BundleApprovalError(
                "Bundle does not belong to the locked identity.",
                code="cross_identity_mismatch",
            )

        # Idempotent re-approval — legal at any parent-version state
        # because it is a no-op. Only actual transitions require the
        # parent-DRAFT guard below.
        if fresh.state == ApprovedRepresentationBundle.State.APPROVED:
            return fresh

        # §19 Step 4.c — §5.4 immutability guard. Approving a bundle
        # on an APPROVED / SUPERSEDED / REJECTED version would mutate
        # its approved voice binding and approved realtime
        # representation — §5.4: "Any change to the approved voice
        # binding" and "Any change to the approved realtime
        # representation" require a new version. Refuse with a stable
        # domain error.
        parent_state = fresh.identity_version.state
        if parent_state != CharacterIdentityVersion.State.DRAFT:
            raise BundleApprovalError(
                (
                    "Cannot approve a bundle on a version in state "
                    f"{parent_state!r}; §5.4 makes approved identity "
                    "versions immutable with respect to their approved "
                    "voice and realtime bindings. Author a new "
                    "CharacterIdentityVersion (draft) and assemble the "
                    "bundle there."
                ),
                code="parent_version_not_draft",
            )

        if fresh.state != ApprovedRepresentationBundle.State.DRAFT:
            raise BundleApprovalError(
                (
                    f"Cannot approve bundle in state {fresh.state!r}; "
                    "only DRAFT transitions to APPROVED."
                ),
                code="invalid_state_transition",
            )

        # Cross-identity FK checks (belt on top of create_draft_bundle
        # braces because bundles may have been created outside that
        # helper in future callers).
        if (
            fresh.approved_voice_id is not None
            and fresh.approved_voice.identity_version_id != fresh.identity_version_id
        ):
            raise BundleApprovalError(
                "approved_voice belongs to a different identity version.",
                code="cross_identity_mismatch",
            )
        if (
            fresh.approved_realtime_id is not None
            and fresh.approved_realtime.identity_version_id != fresh.identity_version_id
        ):
            raise BundleApprovalError(
                "approved_realtime belongs to a different identity version.",
                code="cross_identity_mismatch",
            )

        # Amendment 4 bundle-approval precondition: front portrait
        # reference approved on this version. Enforced locally per
        # the amendment; branch-schema-declarative form lands in
        # Steps 5+.
        if not _bundle_has_front_portrait_reference(fresh.identity_version):
            raise BundleApprovalError(
                (
                    "Bundle approval requires an approved "
                    "portrait_reference/front on the bundle's version "
                    "(§17.10.a Amendment 4)."
                ),
                code="missing_front_portrait",
            )

        # Supersede any prior APPROVED bundle on the same version.
        prior = (
            ApprovedRepresentationBundle.objects
            .select_for_update()
            .filter(
                identity_version=fresh.identity_version,
                state=ApprovedRepresentationBundle.State.APPROVED,
            )
            .exclude(pk=fresh.pk)
            .first()
        )
        now = timezone.now()
        try:
            if prior is not None:
                prior.state = ApprovedRepresentationBundle.State.SUPERSEDED
                prior.save(update_fields=["state"])

            fresh.state = ApprovedRepresentationBundle.State.APPROVED
            fresh.approved_at = now
            fresh.approved_by = approver
            fresh.save(update_fields=["state", "approved_at", "approved_by"])
        except IntegrityError as exc:
            raise BundleApprovalError(
                (
                    "Partial unique constraint fired during bundle "
                    "approval; state was not modified."
                ),
                code="constraint_violation",
            ) from exc

    # §19 Step 4.c — approve_bundle is an assembly-time service. Its
    # parent version is (by the guard above) DRAFT, so it cannot
    # affect the mirror-derivation walk. No compatibility-mirror
    # synchronization needed. Mirrors update at version promotion.
    return fresh


def supersede_bundle(
    bundle: ApprovedRepresentationBundle,
    *,
    reason: str = "",
) -> ApprovedRepresentationBundle:
    """Move an ``APPROVED`` bundle to ``SUPERSEDED`` explicitly. The
    normal supersede-plus-approve path is inside ``approve_bundle``;
    this is the operator-directed hand of an approved bundle out of
    use without an incoming replacement (§17.10.a Amendment 4).

    Sets no ``superseded_at`` timestamp because the bundle model does
    not carry one. Reason is folded into ``reviewer_notes`` when
    supplied.
    """
    if bundle.state != ApprovedRepresentationBundle.State.APPROVED:
        raise BundleApprovalError(
            (
                f"Cannot supersede bundle in state {bundle.state!r}; "
                "only APPROVED transitions to SUPERSEDED."
            ),
            code="invalid_state_transition",
        )
    with transaction.atomic():
        CharacterIdentity.objects.select_for_update().get(
            pk=bundle.identity_version.identity_id
        )

        # §19 Step 4.c — §5.4 immutability guard. Superseding the
        # approved bundle of an APPROVED / SUPERSEDED / REJECTED
        # version would remove the approved voice / realtime
        # bindings; §5.4 makes that a change requiring a new version.
        # Legitimate standalone supersede_bundle is only "abandon a
        # bundle that was approved during assembly, before the parent
        # version was promoted" — i.e. parent version still DRAFT.
        parent_state = bundle.identity_version.state
        if parent_state != CharacterIdentityVersion.State.DRAFT:
            raise BundleApprovalError(
                (
                    "Cannot supersede a bundle on a version in state "
                    f"{parent_state!r}; §5.4 makes approved identity "
                    "versions immutable with respect to their approved "
                    "voice and realtime bindings. Removing the current-"
                    "approved bundle without replacing the version is "
                    "forbidden. Author a new CharacterIdentityVersion "
                    "and supersede the version to remove the trio."
                ),
                code="parent_version_not_draft",
            )

        bundle.state = ApprovedRepresentationBundle.State.SUPERSEDED
        update_fields = ["state"]
        if reason:
            existing = bundle.reviewer_notes or ""
            bundle.reviewer_notes = (
                existing + f"\nsuperseded: {reason}"
            ).strip()
            update_fields.append("reviewer_notes")
        bundle.save(update_fields=update_fields)
    # §19 Step 4.c — supersede_bundle is an assembly-time service. Its
    # parent version is (by the guard above) DRAFT, so mirror
    # derivation is unaffected. No compatibility-mirror sync needed.
    return bundle


# ---------------------------------------------------------------------
# 4.a — Prequalification version approval + state cascade
#       (§17.10.a Amendment 4).
# ---------------------------------------------------------------------


def _supersede_version_and_cascade_children(
    version: CharacterIdentityVersion,
    *,
    now,
) -> None:
    """Transition ``version`` from ``APPROVED`` to ``SUPERSEDED`` and
    cascade its ``APPROVED`` child rows (bundle, references,
    canonical voice, canonical realtime) to ``SUPERSEDED`` in one
    atomic step (§5.6.a + §17.10.a Amendment 4).

    Rationale: ``state='approved'`` on a child row of a superseded
    version would violate §5.6.a's "currently admitted for product
    use" invariant. Once a version is no longer currently admitted,
    its APPROVED children cannot be either.

    Shared by all three version-level transition services
    (``approve_version``, ``approve_prequalification_version``,
    ``supersede_version``) so the cascade shape cannot drift across
    callers.

    Uses ``.update()`` (single SQL statement) for the cascade
    because these are pure state transitions on rows that share the
    same identity — no cross-workspace validation needed on this
    axis. ``.update()`` is materially different from Django's
    ``bulk_update`` helper (which §17.3.b bars from approval
    transitions on the version itself); the cascade below does not
    apply to version-approval transitions.

    Caller must hold ``select_for_update`` on the parent identity
    and be operating inside a ``transaction.atomic()`` block.
    """
    version.state = CharacterIdentityVersion.State.SUPERSEDED
    version.superseded_at = now
    version.save(update_fields=["state", "superseded_at"])

    ApprovedRepresentationBundle.objects.filter(
        identity_version=version,
        state=ApprovedRepresentationBundle.State.APPROVED,
    ).update(state=ApprovedRepresentationBundle.State.SUPERSEDED)

    IdentityReference.objects.filter(
        identity_version=version,
        state=ReferenceState.APPROVED,
    ).update(state=ReferenceState.SUPERSEDED)

    CanonicalVoiceReference.objects.filter(
        identity_version=version,
        state=ReferenceState.APPROVED,
    ).update(state=ReferenceState.SUPERSEDED)

    CanonicalRealtimeReference.objects.filter(
        identity_version=version,
        state=ReferenceState.APPROVED,
    ).update(state=ReferenceState.SUPERSEDED)


def _sync_teammate_mirrors_if_present(
    identity: CharacterIdentity,
) -> None:
    """§19 Step 4.c — trigger compatibility-mirror synchronization for
    the teammate that owns ``identity``, when one exists.

    Called by the three version-level transition services
    (``approve_version``, ``supersede_version``,
    ``approve_prequalification_version``) at the tail of their
    ``with transaction.atomic():`` block, after the canonical state
    transition has been written into the transaction and before the
    block commits. Django reads-its-own-writes inside a transaction,
    so the derivation walk sees the post-transition state.

    Bootstrap fixture identities carry ``teammate=NULL`` per §15.1
    (benchmark fixtures land as identities without an owning
    Teammate). Sync is a no-op for those — there is no compatibility
    mirror to write.

    Sync failure raises out of this helper. The caller's
    ``with transaction.atomic():`` block catches the propagation and
    rolls back the entire canonical transition. Amendment 1's
    authoritative-write rule ("A canonical approval must not commit
    successfully while leaving mirrors inconsistent") is enforced
    structurally: sync and canonical state transition commit or roll
    back together.

    The compat helper reads canonical state; it does not write to any
    canonical row. Provider-neutrality per §17.4.a is preserved
    end-to-end. compat.py itself carries a Step 13 deletion horizon.
    """
    if identity.teammate_id is None:
        return
    # Local import keeps this module free of a compat.py dependency at
    # import time. compat.py imports from ``.models``; services.py
    # importing compat.py at module load would create a circular graph
    # via the shared model imports. The runtime local import is safe
    # because sync only fires from services that also hold a Postgres
    # row lock — no import-time work happens on the hot path.
    from apps.identity import compat  # noqa: PLC0415

    compat.sync_teammate_mirrors(identity.teammate)


def approve_prequalification_version(
    version: CharacterIdentityVersion,
    *,
    approver: models.Model | None = None,
) -> CharacterIdentityVersion:
    """Promote a prequalification-authored (or legacy-imported)
    version to ``APPROVED``, bypassing the branch schema's
    ``required_for_identity`` floor (§17.10.a Amendment 4).

    **Distinct from ``approve_version``.** The qualified
    ``approve_version`` reads and enforces the branch-schema
    approval floor per §17.5.b; this service is the discrete
    ratified bypass path. It **refuses** any version that does not
    carry ``PrequalificationProvenance`` (or ``ImportProvenance``,
    the other explicitly-ratified bypass provenance case per
    Amendment 2). Callers wanting the qualified path use
    ``approve_version``.

    Concurrency semantics mirror ``approve_version``:

    * ``CharacterIdentity`` locked with ``select_for_update()`` for
      the transition.
    * Any prior ``APPROVED`` version on the same identity is
      superseded transactionally, and its ``APPROVED`` child rows
      (bundle, references, canonical voice, canonical realtime)
      cascade to ``SUPERSEDED`` per §5.6.a semantics (a superseded
      version cannot carry currently-admitted children).
    * Idempotent re-approval of the already-``APPROVED`` version is
      a no-op.
    * A partial-unique constraint violation surfaces as
      ``PrequalificationVersionApprovalError(code='constraint_violation')``.

    ``bulk_update()`` is deliberately never used for the version's
    own approval transition (§17.3.b). The cascade to child rows
    uses ``.update()`` (single SQL statement, distinct from
    ``bulk_update()``) because those are pure state moves on
    same-identity children.
    """
    with transaction.atomic():
        locked_identity = (
            CharacterIdentity.objects
            .select_for_update()
            .get(pk=version.identity_id)
        )

        try:
            fresh_version = CharacterIdentityVersion.objects.get(pk=version.pk)
        except CharacterIdentityVersion.DoesNotExist as exc:
            raise PrequalificationVersionApprovalError(
                "Version no longer exists.",
                code="invalid_state_transition",
            ) from exc

        if fresh_version.identity_id != locked_identity.pk:
            raise PrequalificationVersionApprovalError(
                "Version does not belong to the locked identity.",
                code="cross_identity_mismatch",
            )

        # Bypass-authorization gate: version must carry an explicitly-
        # ratified bypass provenance. Otherwise the caller should use
        # ``approve_version`` (the qualified path). Never a mode-flag
        # on the qualified service.
        has_prequal = PrequalificationProvenance.objects.filter(
            identity_version=fresh_version,
        ).exists()
        has_import = ImportProvenance.objects.filter(
            identity_version=fresh_version,
        ).exists()
        if not (has_prequal or has_import):
            raise PrequalificationVersionApprovalError(
                (
                    "Version carries neither PrequalificationProvenance "
                    "nor ImportProvenance; the branch-schema approval "
                    "floor bypass is not authorized. Use "
                    "services.approve_version (the qualified path) "
                    "instead (§17.10.a Amendment 4)."
                ),
                code="missing_prequalification_provenance",
            )

        # Idempotent re-approval.
        if fresh_version.state == CharacterIdentityVersion.State.APPROVED:
            return fresh_version

        if fresh_version.state != CharacterIdentityVersion.State.DRAFT:
            raise PrequalificationVersionApprovalError(
                (
                    f"Cannot approve version in state "
                    f"{fresh_version.state!r}; only DRAFT transitions to "
                    "APPROVED."
                ),
                code="invalid_state_transition",
            )

        # Supersede the current approved version (if any) + cascade
        # its APPROVED children to SUPERSEDED, then promote this
        # version. All inside the same transaction.
        now = timezone.now()
        current = (
            CharacterIdentityVersion.objects
            .select_for_update()
            .filter(
                identity=locked_identity,
                state=CharacterIdentityVersion.State.APPROVED,
            )
            .first()
        )
        try:
            if current is not None and current.pk != fresh_version.pk:
                _supersede_version_and_cascade_children(current, now=now)

            fresh_version.state = CharacterIdentityVersion.State.APPROVED
            fresh_version.approved_at = now
            fresh_version.approved_by = approver
            fresh_version.save(
                update_fields=["state", "approved_at", "approved_by"]
            )
        except IntegrityError as exc:
            raise PrequalificationVersionApprovalError(
                (
                    "Partial unique constraint fired during version "
                    "approval; state was not modified."
                ),
                code="constraint_violation",
            ) from exc

        # §19 Step 4.c — compatibility mirror synchronization inside
        # the same transaction as the canonical state change. Sync
        # failure raises here, out of this ``with`` block, rolling
        # back the version approval + cascade + any orchestrating
        # outer transaction as one atomic step.
        _sync_teammate_mirrors_if_present(locked_identity)

    return fresh_version


# ---------------------------------------------------------------------
# 4.b — Prequalification-authoring orchestration
#       (§17.10.a Amendment 4).
# ---------------------------------------------------------------------


class PrequalificationAuthoringError(IdentityVersionError):
    """Raised by ``record_prequalification_representation`` when the
    orchestration cannot proceed. ``code`` is one of:

    * ``empty_authoring_event`` — caller supplied no representation
      inputs at all (portrait, voice, and realtime all None).
    * ``teammate_workspace_missing`` — teammate has no workspace FK
      to anchor the new ``CharacterIdentity`` on. Not expected in
      production; guarded here so a defect surfaces as a domain
      error rather than a raw AttributeError.
    """

    code = "unknown"


def _build_prequalification_snapshot(
    portrait: PortraitRepresentation | None,
    voice: VoiceRepresentation | None,
    realtime: RealtimeRepresentation | None,
    *,
    carry_forward_from_version_id: object,
) -> dict:
    """Compact evidence summary written to
    ``PrequalificationProvenance.provider_response_snapshot`` per
    §17.10.a Amendment 4's "scope-limited" discipline (mirrors the
    Step 3 provenance-snapshot rule).

    Detailed raw provider response is preserved on each paired
    ``GenerationRecord.prompt_snapshot['provider_response']`` — the
    primary evidence location. This summary carries only which
    representations were touched vs carried forward + factual
    identifiers that are useful without joining GenerationRecord.
    """
    snapshot: dict = {}
    if portrait is not None:
        snapshot["portrait"] = {
            "supplied": True,
            "provider": portrait.provider,
            "portrait_uri": portrait.portrait_uri,
            "mock_mode": portrait.mock_mode,
        }
    else:
        snapshot["portrait"] = {
            "supplied": False,
            "carry_forward_from_version_id": (
                str(carry_forward_from_version_id)
                if carry_forward_from_version_id
                else None
            ),
        }
    if voice is not None:
        snapshot["voice"] = {
            "supplied": True,
            "provider": voice.provider,
            "provider_voice_id": voice.provider_voice_id,
            "voice_kind": voice.voice_kind,
            "mock_mode": voice.mock_mode,
        }
    else:
        snapshot["voice"] = {
            "supplied": False,
            "carry_forward_from_version_id": (
                str(carry_forward_from_version_id)
                if carry_forward_from_version_id
                else None
            ),
        }
    if realtime is not None:
        snapshot["realtime"] = {
            "supplied": True,
            "provider": realtime.provider,
            "provider_realtime_id": realtime.provider_realtime_id,
            "mock_mode": realtime.mock_mode,
        }
    else:
        snapshot["realtime"] = {
            "supplied": False,
            "carry_forward_from_version_id": (
                str(carry_forward_from_version_id)
                if carry_forward_from_version_id
                else None
            ),
        }
    return snapshot


def _make_portrait_generation_record(
    version: CharacterIdentityVersion,
    portrait: PortraitRepresentation,
) -> GenerationRecord:
    """Real (non-legacy) generation record for a portrait input.
    Amendment 3 pairing invariant: non-LEGACY provider ⇒ both
    execution fields non-NULL. ``prompt_snapshot`` carries the
    provider-response evidence for audit; the mirror portrait_path
    derives from ``Asset.file_path``, not from a snapshot key.
    """
    return GenerationRecord.objects.create(
        identity_version=version,
        provider=portrait.provider,
        provider_model=portrait.provider_model,
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={
            "kind": "portrait",
            "portrait_uri": portrait.portrait_uri,
            "provider_response": portrait.provider_response,
        },
        seed_or_reproduction_data=None,
        execution_mode=portrait.execution_mode,
        execution_mode_actual=portrait.execution_mode_actual,
    )


def _make_voice_generation_record(
    version: CharacterIdentityVersion,
    voice: VoiceRepresentation,
) -> GenerationRecord:
    """Real generation record for a voice input. The provider-side
    identifier lands under ``prompt_snapshot['provider_voice_id']``
    per §17.10.a Amendment 4 provider-output convention; the
    compatibility adapter reads this key to derive the
    ``voice_id`` mirror.
    """
    return GenerationRecord.objects.create(
        identity_version=version,
        provider=voice.provider,
        provider_model=voice.provider_model,
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={
            "kind": "voice",
            "provider_voice_id": voice.provider_voice_id,
            "voice_kind": voice.voice_kind,
            "provider_response": voice.provider_response,
        },
        seed_or_reproduction_data=None,
        execution_mode=voice.execution_mode,
        execution_mode_actual=voice.execution_mode_actual,
    )


def _make_realtime_generation_record(
    version: CharacterIdentityVersion,
    realtime: RealtimeRepresentation,
) -> GenerationRecord:
    """Real generation record for a realtime input. The
    provider-side realtime identifier lands under
    ``prompt_snapshot['provider_realtime_id']``. §17.10.a bars this
    identifier from permanent canonical schema; the compatibility
    adapter reads the snapshot key for the growth-window mirror
    derivation only.
    """
    return GenerationRecord.objects.create(
        identity_version=version,
        provider=realtime.provider,
        provider_model=realtime.provider_model,
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={
            "kind": "realtime",
            "provider_realtime_id": realtime.provider_realtime_id,
            "provider_response": realtime.provider_response,
        },
        seed_or_reproduction_data=None,
        execution_mode=realtime.execution_mode,
        execution_mode_actual=realtime.execution_mode_actual,
    )


def _land_portrait_reference_from_input(
    version: CharacterIdentityVersion,
    workspace,
    portrait: PortraitRepresentation,
    *,
    approver,
) -> IdentityReference:
    """Materialize a portrait input into a canonical portrait
    reference. Creates a synthetic ``Asset`` anchored on the
    teammate's workspace, a paired ``GenerationRecord``, and an
    ``IdentityReference(kind=portrait_reference, purpose='front')``
    approved through the ratified service.
    """
    from apps.compositions.models import Asset, AssetRole, AssetType

    asset = Asset.objects.create(
        workspace=workspace,
        asset_type=AssetType.IMAGE,
        role=AssetRole.REFERENCE_IMAGE,
        file_path=portrait.portrait_uri,
        source_spec={
            "prequalification_authored": True,
            "provider": portrait.provider,
            "mock_mode": portrait.mock_mode,
        },
    )
    record = _make_portrait_generation_record(version, portrait)
    ref = IdentityReference.objects.create(
        identity_version=version,
        asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.RAW,
        generation_record=record,
    )
    return approve_reference(ref, approver=approver)


def _land_voice_reference_from_input(
    version: CharacterIdentityVersion,
    voice: VoiceRepresentation,
) -> CanonicalVoiceReference:
    """Materialize a voice input into a
    ``CanonicalVoiceReference(state=APPROVED)`` paired with a
    ``GenerationRecord`` that carries the provider identifier.
    """
    record = _make_voice_generation_record(version, voice)
    return CanonicalVoiceReference.objects.create(
        identity_version=version,
        generation_record=record,
        state=ReferenceState.APPROVED,
        approved_at=timezone.now(),
    )


def _land_realtime_reference_from_input(
    version: CharacterIdentityVersion,
    realtime: RealtimeRepresentation,
) -> CanonicalRealtimeReference:
    """Materialize a realtime input into a
    ``CanonicalRealtimeReference(state=APPROVED)`` paired with a
    ``GenerationRecord`` that carries the provider identifier.
    """
    record = _make_realtime_generation_record(version, realtime)
    return CanonicalRealtimeReference.objects.create(
        identity_version=version,
        generation_record=record,
        state=ReferenceState.APPROVED,
        approved_at=timezone.now(),
    )


def _carry_forward_portrait_reference(
    new_version: CharacterIdentityVersion,
    current_version: CharacterIdentityVersion,
    *,
    approver,
) -> IdentityReference | None:
    """Carry the current version's approved
    ``portrait_reference/front`` forward to the new version. Creates
    a new ``IdentityReference`` anchor row on the new version
    pointing at the **same** ``Asset`` and ``GenerationRecord`` —
    evidence is immutable and shared across versions; anchor rows
    are per-version and cheap per §5.4 / §5.5.

    Returns ``None`` when the current version has no approved
    ``portrait_reference/front``. The bundle-approval invariant on
    the new version will refuse in that case, which is the
    correct failure mode for a "voice-only update against a
    teammate that never had a portrait."
    """
    current_ref = (
        IdentityReference.objects
        .filter(
            identity_version=current_version,
            kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
            purpose="front",
            state=ReferenceState.APPROVED,
        )
        .first()
    )
    if current_ref is None:
        return None

    new_ref = IdentityReference.objects.create(
        identity_version=new_version,
        asset=current_ref.asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose="front",
        state=ReferenceState.RAW,
        generation_record=current_ref.generation_record,
    )
    return approve_reference(new_ref, approver=approver)


def _carry_forward_voice_reference(
    new_version: CharacterIdentityVersion,
    current_version: CharacterIdentityVersion,
) -> CanonicalVoiceReference | None:
    """Carry the current version's approved
    ``CanonicalVoiceReference`` forward to the new version. Creates
    a new anchor row pointing at the same ``GenerationRecord``.

    Reads the approved-bundle's ``approved_voice`` so carry-forward
    matches what was *bundled*, not merely the most recent voice
    reference on the version.
    """
    current_bundle = (
        ApprovedRepresentationBundle.objects
        .filter(
            identity_version=current_version,
            state=ApprovedRepresentationBundle.State.APPROVED,
        )
        .first()
    )
    if current_bundle is None or current_bundle.approved_voice_id is None:
        return None

    source = current_bundle.approved_voice
    return CanonicalVoiceReference.objects.create(
        identity_version=new_version,
        generation_record=source.generation_record,
        state=ReferenceState.APPROVED,
        approved_at=timezone.now(),
    )


def _carry_forward_realtime_reference(
    new_version: CharacterIdentityVersion,
    current_version: CharacterIdentityVersion,
) -> CanonicalRealtimeReference | None:
    """Carry the current version's approved realtime canonical
    reference forward. Same shape as the voice carry-forward.
    """
    current_bundle = (
        ApprovedRepresentationBundle.objects
        .filter(
            identity_version=current_version,
            state=ApprovedRepresentationBundle.State.APPROVED,
        )
        .first()
    )
    if current_bundle is None or current_bundle.approved_realtime_id is None:
        return None

    source = current_bundle.approved_realtime
    return CanonicalRealtimeReference.objects.create(
        identity_version=new_version,
        generation_record=source.generation_record,
        state=ReferenceState.APPROVED,
        approved_at=timezone.now(),
    )


def _get_or_create_identity_for_teammate(teammate) -> CharacterIdentity:
    """Amendment 4 step A: ensure the teammate has a
    ``CharacterIdentity``. Human is the only branch existing
    production authoring supports today; non-human is out of Step 4
    scope.
    """
    existing = CharacterIdentity.objects.filter(teammate=teammate).first()
    if existing is not None:
        return existing
    workspace = getattr(teammate, "workspace", None)
    if workspace is None:
        raise PrequalificationAuthoringError(
            "Teammate has no workspace; cannot anchor a CharacterIdentity.",
            code="teammate_workspace_missing",
        )
    return CharacterIdentity.objects.create(
        workspace=workspace,
        teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN,
        name=teammate.name,
    )


def record_prequalification_representation(
    teammate,
    *,
    source_call: str,
    author: models.Model | None = None,
    portrait: PortraitRepresentation | None = None,
    voice: VoiceRepresentation | None = None,
    realtime: RealtimeRepresentation | None = None,
) -> CharacterIdentityVersion:
    """Prequalification-authoring orchestration per §17.10.a
    Amendment 4 (SESSION 243).

    Records a live production authoring event (wizard create /
    rebake, change_voice, refresh_portrait, batch commands, smoke
    instrumentation) as a new ``CharacterIdentityVersion`` and
    synchronizes the three ``Teammate`` compatibility mirrors in
    one transaction.

    Semantics (Amendment 4 steps A–I, run inside one
    ``transaction.atomic()``):

    A. Ensure the teammate has a ``CharacterIdentity`` (create if
       needed; human branch only in Step 4 scope).
    B. Create a new draft ``CharacterIdentityVersion`` with
       ``spec={}`` and ``spec_schema_version=0``. Provider-neutral;
       carries no invented human-spec facts.
    C. Land ``PrequalificationProvenance`` on the new version with
       a scope-limited response snapshot summarizing which
       representations were supplied vs carried forward.
    D–G. For each of ``portrait`` / ``voice`` / ``realtime``: if the
       caller supplied a representation, land it (new
       ``GenerationRecord`` with the real provider enum + non-NULL
       execution fields; new anchor row on the new version). If the
       caller supplied ``None``, carry the current-approved
       version's canonical state forward by creating a new anchor
       row on the new version pointing at the same underlying
       evidence (``Asset`` + ``GenerationRecord``). §5.4 requires a
       new version for every representation change; §5.5 keeps
       evidence anchored to its producing version; new anchor rows
       are the honest expression of both.
    H. Assemble a draft ``ApprovedRepresentationBundle`` referencing
       whichever voice + realtime canonical references landed. Then
       ``approve_bundle`` promotes it to APPROVED (enforces the
       front-portrait invariant).
    I. ``approve_prequalification_version`` promotes the new version
       to APPROVED, cascading the prior version's approved children
       to SUPERSEDED.
    J. ``compat.sync_teammate_mirrors`` writes the three Teammate
       compatibility fields from the newly-approved canonical
       state. Failure at any step rolls back the entire authoring
       event; the mirrors are never inconsistent with canonical
       state after commit.

    Refuses an "empty authoring event" (all three inputs None) with
    ``PrequalificationAuthoringError(code='empty_authoring_event')``.
    A no-op authoring event has no honest canonical
    representation.

    Not idempotent by content — the caller controls when an
    authoring event fires; identical inputs on two consecutive
    calls produce two versions, only the newer of which is
    currently approved (Amendment 4 versioning consequences).
    """
    if portrait is None and voice is None and realtime is None:
        raise PrequalificationAuthoringError(
            "record_prequalification_representation requires at least "
            "one representation input; got no portrait / voice / "
            "realtime.",
            code="empty_authoring_event",
        )

    with transaction.atomic():
        # A. Ensure CharacterIdentity exists.
        identity = _get_or_create_identity_for_teammate(teammate)

        # Read the current approved version BEFORE creating the new
        # draft. Carry-forward is against whatever was approved at
        # entry to this authoring event.
        current_version = (
            CharacterIdentityVersion.objects
            .filter(
                identity=identity,
                state=CharacterIdentityVersion.State.APPROVED,
            )
            .first()
        )
        current_version_id = current_version.id if current_version else None

        # B. Create the new draft version. Locked identity for
        # revision assignment.
        locked = CharacterIdentity.objects.select_for_update().get(pk=identity.pk)
        revision = _peek_next_revision(locked)
        new_version = CharacterIdentityVersion.objects.create(
            identity=locked,
            revision=revision,
            state=CharacterIdentityVersion.State.DRAFT,
            spec={},
            spec_schema_version=LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION,
        )

        # C. Land PrequalificationProvenance.
        PrequalificationProvenance.objects.create(
            identity_version=new_version,
            source_call=source_call,
            author=author,
            snapshot_schema_version=(
                PREQUALIFICATION_PROVENANCE_SNAPSHOT_SCHEMA_VERSION
            ),
            provider_response_snapshot=_build_prequalification_snapshot(
                portrait, voice, realtime,
                carry_forward_from_version_id=current_version_id,
            ),
        )

        # D–G. Materialize each representation. Explicit branching
        # so carry-forward is provenance-honest per Amendment 4:
        # slots the caller didn't touch anchor at the same evidence,
        # slots the caller supplied land a fresh GenerationRecord
        # with the real provider return.
        if portrait is not None:
            _land_portrait_reference_from_input(
                new_version, teammate.workspace, portrait, approver=author,
            )
        elif current_version is not None:
            _carry_forward_portrait_reference(
                new_version, current_version, approver=author,
            )

        if voice is not None:
            _land_voice_reference_from_input(new_version, voice)
        elif current_version is not None:
            _carry_forward_voice_reference(new_version, current_version)

        if realtime is not None:
            _land_realtime_reference_from_input(new_version, realtime)
        elif current_version is not None:
            _carry_forward_realtime_reference(new_version, current_version)

        # H. Assemble and approve the bundle. approve_bundle
        # enforces the front-portrait invariant; a voice-only
        # authoring event against a teammate with no prior portrait
        # (and no carry-forward possible) fails here.
        voice_ref = (
            CanonicalVoiceReference.objects
            .filter(
                identity_version=new_version,
                state=ReferenceState.APPROVED,
            )
            .order_by("-approved_at")
            .first()
        )
        realtime_ref = (
            CanonicalRealtimeReference.objects
            .filter(
                identity_version=new_version,
                state=ReferenceState.APPROVED,
            )
            .order_by("-approved_at")
            .first()
        )
        bundle = ApprovedRepresentationBundle.objects.create(
            identity_version=new_version,
            approved_voice=voice_ref,
            approved_realtime=realtime_ref,
            state=ApprovedRepresentationBundle.State.DRAFT,
        )
        approve_bundle(bundle, approver=author)

        # I. Approve the new version. This service:
        #    * cascades the prior version's APPROVED children to
        #      SUPERSEDED per §5.6.a (via the shared cascade helper),
        #    * synchronizes the compatibility mirrors inside its own
        #      ``transaction.atomic()`` block via
        #      ``_sync_teammate_mirrors_if_present`` (§19 Step 4.c
        #      wiring).
        #    A prior explicit ``compat.sync_teammate_mirrors(teammate)``
        #    call lived at this point in 4.b; 4.c makes it redundant
        #    because approve_prequalification_version is the last
        #    transactional step of the orchestration and now owns the
        #    sync. Amendment 4's step-I discipline ("write mirrors from
        #    the newly-approved canonical state") is discharged inside
        #    the version-approval transaction itself. Sync failure
        #    still rolls back the entire authoring event via the outer
        #    atomic wrapping this orchestration.
        approve_prequalification_version(new_version, approver=author)

        # Refresh so the returned instance reflects the post-approval
        # state (state=APPROVED, approved_at, approved_by) — the
        # in-memory ``new_version`` was left at DRAFT because
        # ``approve_prequalification_version`` mutates a re-fetched
        # instance under its own lock.
        new_version.refresh_from_db()
        return new_version


__all__ = [
    "BundleApprovalError",
    "IdentityReferenceError",
    "IdentityVersionApprovalError",
    "IdentityVersionError",
    "IdentityVersionSpecInvalid",
    "PrequalificationAuthoringError",
    "PrequalificationVersionApprovalError",
    "ReferenceApprovalError",
    "approve_bundle",
    "approve_prequalification_version",
    "approve_reference",
    "approve_version",
    "attach_reference",
    "create_draft_bundle",
    "create_draft_version",
    "record_generation",
    "record_normalization_manifest",
    "record_prequalification_representation",
    "reject_version",
    "supersede_bundle",
    "supersede_reference_at_slot",
    "supersede_version",
    "update_draft_spec",
]
