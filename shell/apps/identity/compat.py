"""§19 Step 4.b — Compatibility mirror derivation + synchronization.

**Transitional infrastructure with an explicit deletion horizon.**

This module bridges the canonical identity substrate to the three
legacy ``Teammate`` compatibility fields
(``portrait_path`` / ``voice_id`` / ``runway_avatar_id``) during the
growth window ratified in §17.10.a.

**Deletion horizon: Step 13** of the §19 implementation sequence.
When the growth-window exit conditions all hold and the three
compatibility fields are removed from ``Teammate``, this module is
removed in the same migration. Everything here carries a bounded
lifetime; nothing here becomes permanent architecture.

Boundary discipline held here (§17.10.a Amendment 4 + operator
directive SESSION 243):

1. **Reads canonical state; writes mirror state.** Every function
   in this module either derives a mirror value from the canonical
   substrate (never modifying it) or writes to the three
   ``Teammate`` fields (never to canonical rows).
2. **Provider IDs are read out, never stored back into canonical
   rows.** Extractors below consult
   ``GenerationRecord.prompt_snapshot`` — the ratified provenance
   location. They do not add provider-specific columns to any
   canonical model.
3. **Null semantics quarantined at the compatibility boundary.**
   Derivation returns ``None`` internally to mean "canonical
   absence." Synchronization encodes ``None → ""`` at the
   ``Teammate.*`` write, matching the physical legacy compatibility
   representation (§17.10.a Amendment 4 "Compatibility null
   representation"). Canonical code never sees ``""``.
4. **No reverse synchronization.** Nothing in this module reads
   ``Teammate.portrait_path`` / ``.voice_id`` / ``.runway_avatar_id``
   and writes canonical state. That would recreate the two-authority
   problem §17.10.a exists to eliminate.
5. **No transitional bypass of canonical services.** The
   authoritative transition services
   (``services.approve_bundle`` / ``.approve_reference`` /
   ``.approve_prequalification_version`` etc.) remain the sole
   canonical write path. This module is downstream of them.
"""
from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Optional

from apps.spokespeople.models import Teammate

from .models import (
    MIN_CANONICAL_SPEC_SCHEMA_VERSION,
    ApprovedRepresentationBundle,
    CharacterIdentity,
    CharacterIdentityVersion,
    GenerationProvider,
    GenerationRecord,
    IdentityReference,
    IdentityReferenceKind,
    ImportProvenance,
    PrequalificationProvenance,
    ReferenceState,
)

# ---------------------------------------------------------------------
# Provider-ID extractors — bounded-lifetime compatibility adapters.
#
# §17.10.a Amendment 4 provider-output convention:
#   * LEGACY_IMPORTED records → ``prompt_snapshot["legacy_value"]``
#     (Step 3's landed convention, preserved verbatim).
#   * Any other provider → ``prompt_snapshot["provider_voice_id"]``
#     / ``prompt_snapshot["provider_realtime_id"]`` per the
#     prequalification-authoring service's landed evidence shape.
#
# Extractors return ``None`` for a missing / empty value. The sync
# helper below encodes ``None → ""`` when writing to the
# compatibility field.
# ---------------------------------------------------------------------


def _extract_provider_voice_id(record: GenerationRecord) -> Optional[str]:
    """Read the provider-side voice identifier from a
    ``GenerationRecord``. Bounded-lifetime compatibility helper.
    Recognizes the legacy-imported convention and the
    prequalification-authored convention.
    """
    if record.provider == GenerationProvider.LEGACY_IMPORTED:
        value = record.prompt_snapshot.get("legacy_value")
    else:
        value = record.prompt_snapshot.get("provider_voice_id")
    return _stripped_or_none(value)


def _extract_provider_realtime_id(record: GenerationRecord) -> Optional[str]:
    """Read the provider-side realtime identifier from a
    ``GenerationRecord``. Same shape as ``_extract_provider_voice_id``
    but keyed to ``provider_realtime_id`` for non-legacy records.
    §17.10.a bars any such identifier from permanent canonical
    schema; this compatibility helper is the ratified extraction
    surface.
    """
    if record.provider == GenerationProvider.LEGACY_IMPORTED:
        value = record.prompt_snapshot.get("legacy_value")
    else:
        value = record.prompt_snapshot.get("provider_realtime_id")
    return _stripped_or_none(value)


def _stripped_or_none(value) -> Optional[str]:
    """``None`` or empty-after-strip → ``None``. Otherwise the
    stripped string. Matches the Step 3 convention used by
    ``import_service._stripped`` at the compatibility boundary so
    Step 3-imported and Step 4-authored rows compare consistently.
    """
    if value is None:
        return None
    if not isinstance(value, str):
        return None
    stripped = value.strip()
    return stripped or None


# ---------------------------------------------------------------------
# Canonical → mirror derivation.
#
# Each derive_* function walks the ratified canonical structure and
# returns the mirror value the compatibility field should hold. Any
# break in the walk (no identity, no approved version, no bundle,
# no approved reference in the slot) returns ``None``. The sync
# helper encodes ``None`` as ``""`` at mirror-write time.
# ---------------------------------------------------------------------


def _current_approved_version(
    identity: CharacterIdentity,
) -> Optional[CharacterIdentityVersion]:
    return (
        CharacterIdentityVersion.objects
        .filter(
            identity=identity,
            state=CharacterIdentityVersion.State.APPROVED,
        )
        .first()
    )


def _current_approved_bundle(
    version: CharacterIdentityVersion,
) -> Optional[ApprovedRepresentationBundle]:
    return (
        ApprovedRepresentationBundle.objects
        .filter(
            identity_version=version,
            state=ApprovedRepresentationBundle.State.APPROVED,
        )
        .first()
    )


def _current_front_portrait_reference(
    version: CharacterIdentityVersion,
) -> Optional[IdentityReference]:
    return (
        IdentityReference.objects
        .filter(
            identity_version=version,
            kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
            purpose="front",
            state=ReferenceState.APPROVED,
        )
        .first()
    )


def derive_portrait_path(teammate: Teammate) -> Optional[str]:
    """Return the ``portrait_path`` mirror value derived from
    canonical state, or ``None`` if canonical state is absent along
    the derivation walk.

    Walk: teammate → CharacterIdentity → current approved
    CharacterIdentityVersion → approved
    ``IdentityReference(kind=portrait_reference, purpose='front')``
    → ``Asset.file_path``.
    """
    identity = _teammate_identity(teammate)
    if identity is None:
        return None
    version = _current_approved_version(identity)
    if version is None:
        return None
    portrait_ref = _current_front_portrait_reference(version)
    if portrait_ref is None:
        return None
    return _stripped_or_none(portrait_ref.asset.file_path)


def derive_voice_id(teammate: Teammate) -> Optional[str]:
    """Return the ``voice_id`` mirror value derived from canonical
    state.

    Walk: teammate → CharacterIdentity → current approved
    CharacterIdentityVersion → current approved
    ``ApprovedRepresentationBundle`` → ``approved_voice`` →
    ``CanonicalVoiceReference.generation_record`` → provider-ID
    extractor.
    """
    identity = _teammate_identity(teammate)
    if identity is None:
        return None
    version = _current_approved_version(identity)
    if version is None:
        return None
    bundle = _current_approved_bundle(version)
    if bundle is None or bundle.approved_voice_id is None:
        return None
    return _extract_provider_voice_id(bundle.approved_voice.generation_record)


def derive_runway_avatar_id(teammate: Teammate) -> Optional[str]:
    """Return the ``runway_avatar_id`` mirror value derived from
    canonical state.

    Walk: teammate → CharacterIdentity → current approved
    CharacterIdentityVersion → current approved
    ``ApprovedRepresentationBundle`` → ``approved_realtime`` →
    ``CanonicalRealtimeReference.generation_record`` → provider-ID
    extractor.
    """
    identity = _teammate_identity(teammate)
    if identity is None:
        return None
    version = _current_approved_version(identity)
    if version is None:
        return None
    bundle = _current_approved_bundle(version)
    if bundle is None or bundle.approved_realtime_id is None:
        return None
    return _extract_provider_realtime_id(
        bundle.approved_realtime.generation_record
    )


def _teammate_identity(teammate: Teammate) -> Optional[CharacterIdentity]:
    """The at-most-one ``CharacterIdentity`` FK'd to ``teammate``.

    §19 Step 3 (SESSION 242) added the partial-unique constraint
    ``one_character_identity_per_teammate`` making "at most one"
    a database invariant. Read via ``.filter().first()`` for API
    stability against schema evolution.
    """
    return CharacterIdentity.objects.filter(teammate=teammate).first()


# ---------------------------------------------------------------------
# Canonical → mirror synchronization.
#
# Writes the three compatibility fields on a ``Teammate`` from the
# current canonical state. Called by
# ``services.record_prequalification_representation`` at the end of
# an authoring event (Amendment 4 step I) and, in Step 4.c, by the
# other canonical transition services (approve_bundle,
# supersede_bundle, approve_reference on the front portrait,
# approve_version, supersede_version, and
# approve_prequalification_version).
#
# In Step 4.b (this landing) this is the sole call site. The
# authoritative transition services are NOT yet wired to call
# ``sync_teammate_mirrors``; wiring them is Step 4.c.
# ---------------------------------------------------------------------


#: Fields written by ``sync_teammate_mirrors``. Enumerated for the
#: ``.save(update_fields=...)`` call so unrelated ``Teammate``
#: mutation is impossible on the sync path. Kept as a module constant
#: so the enforcement regression tests can grep for it.
MIRROR_FIELDS = ("portrait_path", "voice_id", "runway_avatar_id")


def sync_teammate_mirrors(teammate: Teammate) -> None:
    """Derive canonical values for the three compatibility mirror
    fields and write them to ``teammate`` inside the caller's
    transaction.

    Encoding: ``None → ""`` at the mirror-write boundary. Canonical
    derivation uses ``None`` to mean "canonical absence." The
    ``Teammate`` field schema stores empty string as the physical
    legacy null representation per §17.10.a Amendment 4.

    **Transactional responsibility is the caller's.** The two
    real callers (``record_prequalification_representation`` in 4.b
    and the wired canonical transition services in 4.c) already own
    a ``transaction.atomic()`` around the canonical writes; this
    helper joins that transaction. Failure here rolls back the
    entire authoring event, keeping the mirrors atomically consistent
    with the canonical state per Amendment 1's authoritative-write
    rule.

    Not idempotent by content in the mutating sense — always issues
    a ``.save(update_fields=MIRROR_FIELDS + ('updated_at',))`` even
    when the derived values match the current mirror values. The
    write is cheap; over-writing is honest ("the mirror sync
    happened at time X"); coalescing to a no-op would add branching
    that the compatibility layer does not need. The verifier that
    §17.10.a Amendment 4 mandates asserts equality, not idempotency
    at the write layer.
    """
    portrait = derive_portrait_path(teammate)
    voice = derive_voice_id(teammate)
    realtime = derive_runway_avatar_id(teammate)

    teammate.portrait_path = portrait if portrait is not None else ""
    teammate.voice_id = voice if voice is not None else ""
    teammate.runway_avatar_id = realtime if realtime is not None else ""
    teammate.save(
        update_fields=[
            *MIRROR_FIELDS,
            # ``updated_at`` is auto-managed but Django respects the
            # explicit list when passed. Including it keeps parity
            # with existing sites that update these fields.
            "updated_at",
        ]
    )


# ---------------------------------------------------------------------
# §19 Step 4.e — Compatibility-consistency verifier (read-only).
#
# Amendment 4 mandates a verifier that asserts, for every ``Teammate``,
# the three compatibility mirror fields equal the values derivable from
# the current canonical approved state. The verifier is strictly
# read-only in Step 4 — detection is not repair — and never mutates
# canonical or mirror state.
#
# The comparison boundary normalizes whitespace exactly once here.
# Canonical derivation returns ``None`` for absence; ``Teammate`` fields
# store ``""`` as the physical legacy null representation during the
# growth window. The verifier compares ``strip()`` -> None on both
# sides and reports outcomes with stable status + reason codes.
#
# All code paths in this section run inside SELECT-only ORM queries.
# No ``.save()``, ``.objects.create``, ``.objects.update``, or
# ``.objects.delete`` calls exist here. Regression tests assert this
# structurally (AST walk) and behaviorally (state snapshots before/
# after verifier calls).
# ---------------------------------------------------------------------


class MirrorStatus:
    """Ratified per-field verifier statuses. Small and explicit per
    operator direction — no repair status, no auto-classification of
    ambiguous drift into ``not_applicable``.
    """

    MATCH = "match"
    DRIFT = "drift"
    NOT_APPLICABLE = "not_applicable"


class MirrorReason:
    """Stable reason codes attached to each per-field verifier result.

    Vocabulary is designed so 4.d callers and future operational
    audits can discriminate the drift class without depending on
    message text.
    """

    #: Both mirror and canonical agree — either both populated with
    #: equal (whitespace-normalized) values, or both absent.
    MATCH = "match"

    #: Teammate has no ``CharacterIdentity``; this field's mirror is
    #: blank. Not drift — the teammate has not been authored into the
    #: canonical substrate yet.
    NO_IDENTITY_AUTHORED = "no_identity_authored"

    #: Teammate has no ``CharacterIdentity`` but this field's mirror
    #: carries a populated value. Operational migration debt exposed
    #: by Step 4.d — the teammate needs
    #: ``python manage.py backfill_identity_substrate`` before
    #: migrated authoring endpoints will accept it. Drift.
    CANONICAL_IDENTITY_REQUIRED = "canonical_identity_required"

    #: CharacterIdentity exists but the canonical derivation for this
    #: field returned ``None`` (no current approved version, or the
    #: approved bundle carries no ``approved_voice`` /
    #: ``approved_realtime``, or no approved front portrait reference
    #: is on the current version), and the mirror carries a populated
    #: value. Drift — canonical wins conceptually; the mirror is
    #: stale.
    STALE_AFTER_CANONICAL_ABSENT = "stale_after_canonical_absent"

    #: Canonical derivation returned a value but the mirror is blank.
    #: Drift.
    MIRROR_BLANK_BUT_CANONICAL_PRESENT = "mirror_blank_but_canonical_present"

    #: Both mirror and canonical are populated with values that differ
    #: after whitespace normalization. Drift.
    VALUE_MISMATCH = "value_mismatch"


class IdentityClass:
    """Per-teammate identity-class classification. Reported alongside
    the three per-field results so operational audits can slice by
    provenance category.
    """

    #: Teammate has no ``CharacterIdentity`` row.
    NO_IDENTITY = "no_identity"

    #: CharacterIdentity exists but no version is currently
    #: ``state='approved'``.
    NO_APPROVED_VERSION = "no_approved_version"

    #: Current approved version was landed by Step 3's one-time legacy
    #: backfill (has ``ImportProvenance``).
    LEGACY_IMPORTED = "legacy_imported"

    #: Current approved version was landed by post-Step-4 canonical
    #: authoring (has ``PrequalificationProvenance``).
    PREQUALIFICATION_AUTHORED = "prequalification_authored"

    #: Current approved version has neither provenance marker and
    #: ``spec_schema_version >= MIN_CANONICAL_SPEC_SCHEMA_VERSION`` —
    #: the future qualified authoring path landing in Steps 5–10.
    QUALIFIED_AUTHORED = "qualified_authored"

    #: Current approved version has ``spec_schema_version = 0`` but
    #: carries neither provenance marker. This shape is not producible
    #: by any ratified write path under Amendment 4 discipline —
    #: surface it explicitly so audit tooling can flag the anomaly
    #: rather than silently classifying.
    ANOMALOUS_NO_PROVENANCE = "anomalous_no_provenance"


@dataclass(frozen=True)
class MirrorFieldResult:
    """Per-field verifier outcome for one of the three ``Teammate``
    compatibility mirrors.

    ``mirror_value`` and ``canonical_value`` are the pre-comparison
    values: mirror is the raw ``Teammate`` field content (``""`` when
    blank, matching the physical schema); canonical is the derivation
    output (``None`` for canonical absence). Whitespace normalization
    happens inside ``_compare_field`` and does not leak into the
    reported values — audit output preserves what was actually
    persisted.
    """

    field_name: str
    mirror_value: str
    canonical_value: Optional[str]
    status: str
    reason: str


@dataclass(frozen=True)
class MirrorVerifyResult:
    """Per-teammate verifier outcome.

    ``identity_class`` slices the teammate by canonical-substrate
    provenance category; per-field results describe the three
    compatibility mirrors independently. ``has_drift`` /
    ``canonical_backfill_required`` are computed convenience flags
    for aggregate reporting.
    """

    teammate_id: uuid.UUID
    workspace_id: uuid.UUID
    identity_class: str
    portrait_path: MirrorFieldResult
    voice_id: MirrorFieldResult
    runway_avatar_id: MirrorFieldResult

    @property
    def fields(self) -> tuple[MirrorFieldResult, ...]:
        return (self.portrait_path, self.voice_id, self.runway_avatar_id)

    @property
    def has_drift(self) -> bool:
        return any(f.status == MirrorStatus.DRIFT for f in self.fields)

    @property
    def canonical_backfill_required(self) -> bool:
        """True iff the teammate has no ``CharacterIdentity`` AND at
        least one mirror field is populated. This is the audit signal
        for "run ``backfill_identity_substrate`` on this row" per the
        Step 4.d operational discipline.
        """
        return (
            self.identity_class == IdentityClass.NO_IDENTITY
            and any(
                f.status == MirrorStatus.DRIFT
                and f.reason == MirrorReason.CANONICAL_IDENTITY_REQUIRED
                for f in self.fields
            )
        )


@dataclass(frozen=True)
class MirrorVerifyReport:
    """Aggregate outcome across a Teammate sweep.

    Detailed per-teammate results live under ``per_teammate``.
    Summary counters flatten the common operational questions:

    * How many teammates are in each identity-class category?
    * How many are cleanly matched vs drifted?
    * How many require ``backfill_identity_substrate`` before
      migrated authoring endpoints will accept them?
    * Where is drift concentrated (by field, by reason)?
    * Where are legitimate not-applicable cases coming from
      (by reason)?
    """

    total_inspected: int
    identity_class_counts: dict[str, int]
    clean_match_count: int
    drift_count: int
    canonical_backfill_required_count: int
    drift_by_field: dict[str, int]
    drift_by_reason: dict[str, int]
    na_by_reason: dict[str, int]
    per_teammate: tuple[MirrorVerifyResult, ...]


def _classify_identity_version(
    version: CharacterIdentityVersion,
) -> str:
    """Classify a currently-approved version by its ratified
    provenance / schema-validation axis.
    """
    if ImportProvenance.objects.filter(identity_version=version).exists():
        return IdentityClass.LEGACY_IMPORTED
    if PrequalificationProvenance.objects.filter(
        identity_version=version,
    ).exists():
        return IdentityClass.PREQUALIFICATION_AUTHORED
    if version.spec_schema_version >= MIN_CANONICAL_SPEC_SCHEMA_VERSION:
        return IdentityClass.QUALIFIED_AUTHORED
    return IdentityClass.ANOMALOUS_NO_PROVENANCE


def _compare_field(
    field_name: str,
    mirror_raw: str,
    canonical_value: Optional[str],
) -> MirrorFieldResult:
    """Produce a per-field verifier result under the ratified
    §5.6.a semantics.

    Whitespace normalization is applied exactly once at the
    comparison boundary (mirroring the Step 3 ``_stripped`` /
    Step 4.b ``_stripped_or_none`` conventions). Canonical values
    reach this function already normalized (``derive_*`` uses the
    same rule internally).
    """
    mirror_norm = _stripped_or_none(mirror_raw)

    if mirror_norm is None and canonical_value is None:
        return MirrorFieldResult(
            field_name=field_name,
            mirror_value=mirror_raw or "",
            canonical_value=None,
            status=MirrorStatus.MATCH,
            reason=MirrorReason.MATCH,
        )
    if mirror_norm is None and canonical_value is not None:
        return MirrorFieldResult(
            field_name=field_name,
            mirror_value=mirror_raw or "",
            canonical_value=canonical_value,
            status=MirrorStatus.DRIFT,
            reason=MirrorReason.MIRROR_BLANK_BUT_CANONICAL_PRESENT,
        )
    if mirror_norm is not None and canonical_value is None:
        return MirrorFieldResult(
            field_name=field_name,
            mirror_value=mirror_raw,
            canonical_value=None,
            status=MirrorStatus.DRIFT,
            reason=MirrorReason.STALE_AFTER_CANONICAL_ABSENT,
        )
    # Both populated.
    if mirror_norm == canonical_value:
        return MirrorFieldResult(
            field_name=field_name,
            mirror_value=mirror_raw,
            canonical_value=canonical_value,
            status=MirrorStatus.MATCH,
            reason=MirrorReason.MATCH,
        )
    return MirrorFieldResult(
        field_name=field_name,
        mirror_value=mirror_raw,
        canonical_value=canonical_value,
        status=MirrorStatus.DRIFT,
        reason=MirrorReason.VALUE_MISMATCH,
    )


def _build_no_identity_result(teammate: Teammate) -> MirrorVerifyResult:
    """Teammate has no ``CharacterIdentity``. Each mirror field is
    either N/A (``no_identity_authored`` if blank) or drift
    (``canonical_identity_required`` if populated).
    """
    field_results: dict[str, MirrorFieldResult] = {}
    for name in MIRROR_FIELDS:
        mirror_raw = getattr(teammate, name) or ""
        mirror_norm = _stripped_or_none(mirror_raw)
        if mirror_norm is None:
            field_results[name] = MirrorFieldResult(
                field_name=name,
                mirror_value=mirror_raw,
                canonical_value=None,
                status=MirrorStatus.NOT_APPLICABLE,
                reason=MirrorReason.NO_IDENTITY_AUTHORED,
            )
        else:
            field_results[name] = MirrorFieldResult(
                field_name=name,
                mirror_value=mirror_raw,
                canonical_value=None,
                status=MirrorStatus.DRIFT,
                reason=MirrorReason.CANONICAL_IDENTITY_REQUIRED,
            )
    return MirrorVerifyResult(
        teammate_id=teammate.id,
        workspace_id=teammate.workspace_id,
        identity_class=IdentityClass.NO_IDENTITY,
        portrait_path=field_results["portrait_path"],
        voice_id=field_results["voice_id"],
        runway_avatar_id=field_results["runway_avatar_id"],
    )


def verify_teammate_mirrors(teammate: Teammate) -> MirrorVerifyResult:
    """Read-only verifier for a single ``Teammate``'s compatibility
    mirrors (§17.10.a Amendment 4 mirror-consistency requirement).

    Compares each of the three mirror fields against the value
    derivable from the current canonical approved state; returns a
    structured result covering status + reason per field plus an
    identity-class classification for the teammate as a whole.

    **Never mutates state.** No ``.save()``, ``.objects.create``,
    ``.objects.update``, or ``.objects.delete`` executes on any code
    path. Callers may run the verifier in a read-only transaction,
    concurrent to normal operation, or over an inspection-only
    replica.
    """
    identity = _teammate_identity(teammate)
    if identity is None:
        return _build_no_identity_result(teammate)

    version = _current_approved_version(identity)
    if version is None:
        identity_class = IdentityClass.NO_APPROVED_VERSION
    else:
        identity_class = _classify_identity_version(version)

    # ``derive_*`` walks canonical structure with SELECT-only queries
    # and returns ``None`` for absence. Whitespace normalization
    # happens inside ``derive_*`` (via ``_stripped_or_none``) so the
    # values returned here are already normalized.
    canonical_portrait = derive_portrait_path(teammate)
    canonical_voice = derive_voice_id(teammate)
    canonical_realtime = derive_runway_avatar_id(teammate)

    return MirrorVerifyResult(
        teammate_id=teammate.id,
        workspace_id=teammate.workspace_id,
        identity_class=identity_class,
        portrait_path=_compare_field(
            "portrait_path", teammate.portrait_path or "", canonical_portrait,
        ),
        voice_id=_compare_field(
            "voice_id", teammate.voice_id or "", canonical_voice,
        ),
        runway_avatar_id=_compare_field(
            "runway_avatar_id", teammate.runway_avatar_id or "",
            canonical_realtime,
        ),
    )


def verify_all_mirrors(
    *,
    workspace_id: Optional[uuid.UUID] = None,
) -> MirrorVerifyReport:
    """Sweep every ``Teammate`` (optionally filtered by workspace)
    through ``verify_teammate_mirrors`` and produce an aggregate
    report.

    Read-only across the sweep. Iterates via
    ``Teammate.objects.all().order_by("workspace_id", "id")`` (or
    the workspace filter) — no writes, no side effects.

    ``workspace_id`` accepts a ``uuid.UUID`` instance; the caller
    (typically the ``verify_identity_mirrors`` management command)
    parses the CLI string into a UUID before invoking.
    """
    qs = Teammate.objects.all().order_by("workspace_id", "id")
    if workspace_id is not None:
        qs = qs.filter(workspace_id=workspace_id)

    per_teammate: list[MirrorVerifyResult] = []
    identity_class_counts: dict[str, int] = {}
    drift_by_field: dict[str, int] = {name: 0 for name in MIRROR_FIELDS}
    drift_by_reason: dict[str, int] = {}
    na_by_reason: dict[str, int] = {}
    clean_match_count = 0
    drift_count = 0
    canonical_backfill_required_count = 0

    for teammate in qs.iterator():
        result = verify_teammate_mirrors(teammate)
        per_teammate.append(result)
        identity_class_counts[result.identity_class] = (
            identity_class_counts.get(result.identity_class, 0) + 1
        )

        teammate_has_drift = False
        all_match = True
        for f in result.fields:
            if f.status == MirrorStatus.DRIFT:
                teammate_has_drift = True
                all_match = False
                drift_by_field[f.field_name] += 1
                drift_by_reason[f.reason] = (
                    drift_by_reason.get(f.reason, 0) + 1
                )
            elif f.status == MirrorStatus.NOT_APPLICABLE:
                all_match = False
                na_by_reason[f.reason] = na_by_reason.get(f.reason, 0) + 1
        if teammate_has_drift:
            drift_count += 1
            if result.canonical_backfill_required:
                canonical_backfill_required_count += 1
        elif all_match:
            clean_match_count += 1

    return MirrorVerifyReport(
        total_inspected=len(per_teammate),
        identity_class_counts=identity_class_counts,
        clean_match_count=clean_match_count,
        drift_count=drift_count,
        canonical_backfill_required_count=canonical_backfill_required_count,
        drift_by_field=drift_by_field,
        drift_by_reason=drift_by_reason,
        na_by_reason=na_by_reason,
        per_teammate=tuple(per_teammate),
    )


__all__ = [
    "IdentityClass",
    "MIRROR_FIELDS",
    "MirrorFieldResult",
    "MirrorReason",
    "MirrorStatus",
    "MirrorVerifyReport",
    "MirrorVerifyResult",
    "derive_portrait_path",
    "derive_runway_avatar_id",
    "derive_voice_id",
    "sync_teammate_mirrors",
    "verify_all_mirrors",
    "verify_teammate_mirrors",
]
