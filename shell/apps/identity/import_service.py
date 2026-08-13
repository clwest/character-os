"""§19 Step 3 — Legacy Teammate → Canonical Identity substrate
one-time historical backfill.

**This module is Step 3's exclusive write path** for the
``legacy_imported`` provenance category (§17.10.a Amendment 2).
Kept as a dedicated module — separate from
``apps.identity.services`` — so the fact that it bypasses the
Step 2 authoritative write path (``services.approve_version`` and
the branch-schema approval floor) is obvious to future readers and
covered by explicit tests.

Ratified boundaries (SESSION 242):

* **Historical import only.** Never invents provider facts. When
  a legacy value is unknown or malformed, the classifier flags it
  as ``failed_incompatible`` — the row is preserved as incompatible
  legacy evidence, not guessed into a canonical representation
  (Amendment G).
* **One ``GenerationRecord`` per imported representation class.**
  Portrait, voice, and realtime each land as their own bootstrap
  record so the historical chain from legacy field → substrate
  row remains inspectable (Amendment B).
* **Bundle only when at least one bundle-relevant representation
  lands.** Bundle binds voice + realtime; portrait-only imports
  ship references without a bundle (Amendment C).
* **Empty teammates skipped.** A Teammate carrying none of
  ``portrait_path`` / ``voice_id`` / ``runway_avatar_id`` reports
  ``nothing_to_import`` and writes zero substrate rows. Identity-
  page text alone does not trigger an import (Amendment A).
* **Per-teammate atomic transaction.** Any failure during one
  Teammate's import rolls back that Teammate entirely; already-
  committed teammates remain done. Idempotency's
  ``skipped_authored`` classification relies on this
  atomicity — the shape "identity exists without provenance" is
  never a partial-import leftover (Amendment D).
* **Provenance snapshot scope-limited.** Snapshots only the three
  legacy identity fields plus the identity-page text that
  describes how the operator authored the teammate. The whole
  Teammate row is not dumped (Amendment E).
* **Append-only.** No delete / purge command in Step 3
  (Amendment H).
"""
from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from typing import Literal

from django.db import transaction
from django.utils import timezone

from apps.compositions.models import Asset, AssetRole, AssetType
from apps.identity.models import (
    IMPORT_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
    LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION,
    ApprovedRepresentationBundle,
    CanonicalRealtimeReference,
    CanonicalVoiceReference,
    CharacterIdentity,
    CharacterIdentityVersion,
    DirectionHypothesis,
    GenerationProvider,
    GenerationRecord,
    IdentityReference,
    IdentityReferenceKind,
    ImportProvenance,
    ReferenceState,
)
from apps.spokespeople.models import Teammate

logger = logging.getLogger(__name__)


#: Migration string persisted on every ImportProvenance row. Bumps
#: manually if a future substrate migration meaningfully changes
#: the shape of imported rows.
CURRENT_IMPORT_MIGRATION_VERSION = "identity.0002_step3_legacy_provenance"

#: Purpose value used on the synthetic IdentityReference for a
#: legacy portrait. `front` is enumerated in the human purpose
#: schema so the reference is representable under existing
#: substrate validation; when Step 5+ authors real portrait
#: references the reviewer may re-classify.
LEGACY_PORTRAIT_PURPOSE = "front"

#: Identity-page fields snapshotted for provenance context.
#: Explicitly enumerated so the snapshot never accidentally dumps
#: unrelated Teammate columns (Amendment E).
_IDENTITY_PAGE_FIELDS = (
    "business_brief",
    "personality",
    "visual_subject",
    "visual_template",
    "tone_archetype",
    "who_you_help",
    "what_you_sell",
    "always_emphasize",
    "never_say",
    "desired_feeling",
)


ImportAction = Literal[
    "imported",
    "already_imported",
    "skipped_authored",
    "nothing_to_import",
    "failed_incompatible",
    "failed",
]


@dataclass(frozen=True)
class ImportResult:
    """One-teammate outcome, returned by both the classifier and
    the actual importer so ``--dry-run`` reports match real-run
    classification exactly (Amendment F).
    """

    teammate_id: uuid.UUID
    action: ImportAction
    identity_id: uuid.UUID | None = None
    version_id: uuid.UUID | None = None
    provenance_id: uuid.UUID | None = None
    detail: str = ""


# ---------------------------------------------------------------------
# Classification (Amendment F — dry-run must run the same logic)
# ---------------------------------------------------------------------


def _stripped(value: str | None) -> str:
    """Trivial whitespace normalization. Anything else — malformed
    URIs, unsupported shapes — is refused as incompatible legacy
    evidence rather than silently fixed (Amendment G).
    """
    return (value or "").strip()


def _portrait_looks_like_asset_ref(value: str) -> bool:
    """A legacy ``portrait_path`` must be either an HTTP(S) URL
    or a data URI to be importable as an Asset.file_path (see
    ``apps.compositions.models.Asset.file_path`` docstring which
    accepts both).
    """
    if not value:
        return False
    return value.startswith(("http://", "https://", "data:"))


def classify_teammate(teammate: Teammate) -> ImportResult:
    """Return what would happen if ``teammate`` were passed to
    ``import_legacy_teammate`` right now. Runs no writes.

    Order matters — the classifier returns the first applicable
    action from top to bottom:

    1. ``already_imported`` — an identity exists AND at least one
       of its versions carries ImportProvenance.
    2. ``skipped_authored`` — an identity exists WITHOUT any
       ImportProvenance. Per Amendment D this shape is only
       reachable via genuine canonical authoring because Step 3
       imports are per-teammate atomic (see
       ``test_import_service_atomicity``).
    3. ``nothing_to_import`` — Teammate has none of the three
       legacy identity fields set (Amendment A).
    4. ``failed_incompatible`` — the ``portrait_path`` is present
       but does not match the expected URL / data-URI shape
       (Amendment G).
    5. ``imported`` — normal case; a real import would write the
       substrate rows.
    """
    existing = CharacterIdentity.objects.filter(teammate=teammate).first()
    if existing is not None:
        has_provenance = ImportProvenance.objects.filter(
            identity_version__identity=existing,
        ).exists()
        if has_provenance:
            return ImportResult(
                teammate_id=teammate.id,
                action="already_imported",
                identity_id=existing.id,
                detail="identity already carries ImportProvenance",
            )
        return ImportResult(
            teammate_id=teammate.id,
            action="skipped_authored",
            identity_id=existing.id,
            detail=(
                "identity exists without ImportProvenance; treated "
                "as authored (Amendment D — Step 3 cannot leave this "
                "shape behind due to per-teammate atomicity)"
            ),
        )

    portrait_path = _stripped(teammate.portrait_path)
    voice_id = _stripped(teammate.voice_id)
    runway_avatar_id = _stripped(teammate.runway_avatar_id)

    if not any([portrait_path, voice_id, runway_avatar_id]):
        return ImportResult(
            teammate_id=teammate.id,
            action="nothing_to_import",
            detail="no legacy identity fields set",
        )

    if portrait_path and not _portrait_looks_like_asset_ref(portrait_path):
        return ImportResult(
            teammate_id=teammate.id,
            action="failed_incompatible",
            detail=(
                f"portrait_path shape unsupported (expected HTTP(S) URL "
                f"or data URI): {portrait_path[:80]!r}"
            ),
        )

    return ImportResult(
        teammate_id=teammate.id,
        action="imported",
    )


# ---------------------------------------------------------------------
# Import (Amendments A, B, C, D, E, G, H)
# ---------------------------------------------------------------------


def import_legacy_teammate(
    teammate: Teammate,
    *,
    run_id: uuid.UUID,
    dry_run: bool = False,
) -> ImportResult:
    """One-shot per teammate. Classifies first; if the
    classification says ``imported`` and this is a real run,
    performs the full import inside one ``transaction.atomic()``.

    Never calls ``services.approve_version`` — legacy imports are
    outside that gated write path by design (§17.10.a Amendment 2
    point 5 + operator ratification 4).
    """
    classification = classify_teammate(teammate)
    if classification.action != "imported":
        return classification
    if dry_run:
        return classification

    try:
        with transaction.atomic():
            identity = _create_bootstrap_identity(teammate)
            version = _create_bootstrap_version(identity)

            portrait_path = _stripped(teammate.portrait_path)
            voice_id = _stripped(teammate.voice_id)
            runway_avatar_id = _stripped(teammate.runway_avatar_id)

            portrait_ref: IdentityReference | None = None
            voice_ref: CanonicalVoiceReference | None = None
            realtime_ref: CanonicalRealtimeReference | None = None

            if portrait_path:
                portrait_ref = _import_legacy_portrait(
                    version, teammate, portrait_path,
                )
            if voice_id:
                voice_ref = _import_legacy_voice(version, voice_id)
            if runway_avatar_id:
                realtime_ref = _import_legacy_realtime(
                    version, runway_avatar_id,
                )

            # Bundle only when at least one bundle-relevant
            # canonical reference landed (Amendment C). Portrait-
            # only imports live as IdentityReference on the
            # version without a bundle, matching the Step 2
            # bundle model shape (§15.3).
            if voice_ref is not None or realtime_ref is not None:
                _create_bootstrap_bundle(
                    version, voice_ref=voice_ref, realtime_ref=realtime_ref,
                )

            provenance = _record_provenance(version, teammate, run_id)

            return ImportResult(
                teammate_id=teammate.id,
                action="imported",
                identity_id=identity.id,
                version_id=version.id,
                provenance_id=provenance.id,
                detail=(
                    f"portrait={'yes' if portrait_ref else 'no'} "
                    f"voice={'yes' if voice_ref else 'no'} "
                    f"realtime={'yes' if realtime_ref else 'no'}"
                ),
            )
    except Exception as exc:
        logger.exception(
            "legacy import failed for teammate %s", teammate.id,
        )
        return ImportResult(
            teammate_id=teammate.id,
            action="failed",
            detail=f"{type(exc).__name__}: {exc}",
        )


# ---------------------------------------------------------------------
# Bootstrap helpers (private; only import_legacy_teammate uses these)
# ---------------------------------------------------------------------


def _create_bootstrap_identity(teammate: Teammate) -> CharacterIdentity:
    """Land a new CharacterIdentity bound to ``teammate``.
    Round-one imports are all human branch — non-human legacy is
    not in scope. Name mirrors the Teammate's display name.
    """
    return CharacterIdentity.objects.create(
        workspace=teammate.workspace,
        teammate=teammate,
        kind=CharacterIdentity.Kind.HUMAN,
        name=teammate.name,
    )


def _create_bootstrap_version(
    identity: CharacterIdentity,
) -> CharacterIdentityVersion:
    """Land the version at ``state='approved'``,
    ``spec_schema_version=0`` (the legacy_unvalidated sentinel),
    ``spec={}``. Skips ``services.approve_version`` deliberately —
    the branch-schema approval floor does not apply to legacy
    imports (§17.10.a Amendment 2 + operator ratification 4).
    """
    now = timezone.now()
    return CharacterIdentityVersion.objects.create(
        identity=identity,
        revision=1,
        state=CharacterIdentityVersion.State.APPROVED,
        spec={},
        spec_schema_version=LEGACY_UNVALIDATED_SPEC_SCHEMA_VERSION,
        approved_at=now,
        approved_by=None,
        reviewer_notes=(
            "legacy_imported: bootstrap version created by the Step 3 "
            "backfill service. state=approved marks currently admitted "
            "for product use only; does not imply schema validation, "
            "Portrait Language compliance, or benchmark qualification."
        ),
    )


def _legacy_generation_record(
    version: CharacterIdentityVersion,
    *,
    kind: str,
    legacy_field_name: str,
    legacy_value: str,
) -> GenerationRecord:
    """One bootstrap GenerationRecord per imported representation
    class (Amendment B). Provider details left blank — unknown
    means unknown. Execution fields are omitted (default NULL):
    no adapter ran through the execution framework, so the
    honest label is the absence of an execution decision
    (§17.10.a Amendment 3). The paired-null pairing invariant
    on ``GenerationRecord`` enforces that this NULL/NULL shape
    is what ``provider = LEGACY_IMPORTED`` requires.
    """
    return GenerationRecord.objects.create(
        identity_version=version,
        provider=GenerationProvider.LEGACY_IMPORTED,
        provider_model="",  # unknown; Amendment G — do not invent
        direction_hypothesis=DirectionHypothesis.IDENTITY_ONLY,
        prompt_snapshot={
            "legacy_kind": kind,
            "legacy_field": legacy_field_name,
            "legacy_value": legacy_value,
            "note": (
                "Historical ingestion — no provider was called to "
                "produce this artifact. Value predates the substrate."
            ),
        },
        seed_or_reproduction_data=None,
        # execution_mode + execution_mode_actual intentionally omitted →
        # both default to NULL, which is the ratified label for "no
        # execution framework decision ever applied to this row"
        # (§17.10.a Amendment 3).
        elapsed_ms=None,
        failure_reason="",
    )


def _import_legacy_portrait(
    version: CharacterIdentityVersion,
    teammate: Teammate,
    portrait_path: str,
) -> IdentityReference:
    """Land the legacy portrait as: synthetic Asset (workspace-
    anchored, role=REFERENCE_IMAGE, file_path=portrait_path with
    no byte copy or transformation) + bootstrap GenerationRecord
    + IdentityReference(state=APPROVED, purpose=front).
    """
    asset = Asset.objects.create(
        workspace=teammate.workspace,
        asset_type=AssetType.IMAGE,
        role=AssetRole.REFERENCE_IMAGE,
        file_path=portrait_path,
        source_spec={
            "legacy_imported": True,
            "source_teammate_id": str(teammate.id),
            "source_field": "portrait_path",
        },
    )
    record = _legacy_generation_record(
        version,
        kind="portrait",
        legacy_field_name="portrait_path",
        legacy_value=portrait_path,
    )
    return IdentityReference.objects.create(
        identity_version=version,
        asset=asset,
        kind=IdentityReferenceKind.PORTRAIT_REFERENCE,
        purpose=LEGACY_PORTRAIT_PURPOSE,
        state=ReferenceState.APPROVED,
        generation_record=record,
        reviewer_notes=(
            "legacy_imported: synthesized IdentityReference from "
            "Teammate.portrait_path. Purpose=front is the substrate-"
            "representable label; a future reviewer may re-classify."
        ),
    )


def _import_legacy_voice(
    version: CharacterIdentityVersion,
    voice_id: str,
) -> CanonicalVoiceReference:
    """Land the legacy voice as: bootstrap GenerationRecord (which
    carries the provider-side voice_id inside its prompt_snapshot
    per §17.4.a — provider details live under the reference, not
    on it) + CanonicalVoiceReference(state=APPROVED).
    """
    record = _legacy_generation_record(
        version,
        kind="voice",
        legacy_field_name="voice_id",
        legacy_value=voice_id,
    )
    return CanonicalVoiceReference.objects.create(
        identity_version=version,
        generation_record=record,
        state=ReferenceState.APPROVED,
        approved_at=timezone.now(),
        reviewer_notes=(
            "legacy_imported: canonical voice reference synthesized "
            "from Teammate.voice_id. Provider-side identifier lives "
            "in the generation record's prompt_snapshot per §17.4.a."
        ),
    )


def _import_legacy_realtime(
    version: CharacterIdentityVersion,
    runway_avatar_id: str,
) -> CanonicalRealtimeReference:
    """Land the legacy realtime avatar as: bootstrap
    GenerationRecord + CanonicalRealtimeReference(state=APPROVED).
    The Runway-specific identifier stays inside the generation
    record's prompt_snapshot per §17.10.a's explicit prohibition
    on encoding ``runway_avatar_id`` into the permanent
    canonical schema.
    """
    record = _legacy_generation_record(
        version,
        kind="realtime",
        legacy_field_name="runway_avatar_id",
        legacy_value=runway_avatar_id,
    )
    return CanonicalRealtimeReference.objects.create(
        identity_version=version,
        generation_record=record,
        state=ReferenceState.APPROVED,
        approved_at=timezone.now(),
        reviewer_notes=(
            "legacy_imported: canonical realtime reference synthesized "
            "from Teammate.runway_avatar_id. Runway-specific identifier "
            "stays in the generation record's prompt_snapshot per "
            "§17.10.a — never encoded into the permanent schema."
        ),
    )


def _create_bootstrap_bundle(
    version: CharacterIdentityVersion,
    *,
    voice_ref: CanonicalVoiceReference | None,
    realtime_ref: CanonicalRealtimeReference | None,
) -> ApprovedRepresentationBundle:
    """Create the bundle ONLY when at least one of the two
    bundle-relevant references landed (Amendment C). Bundle state
    is APPROVED so Step 4's mirror discipline treats it as the
    current admitted representation.
    """
    if voice_ref is None and realtime_ref is None:
        raise ValueError("_create_bootstrap_bundle called with no refs")
    return ApprovedRepresentationBundle.objects.create(
        identity_version=version,
        approved_voice=voice_ref,
        approved_realtime=realtime_ref,
        state=ApprovedRepresentationBundle.State.APPROVED,
        approved_at=timezone.now(),
        approved_by=None,
        reviewer_notes=(
            "legacy_imported: bootstrap bundle binding the imported "
            "canonical references. state=approved marks currently "
            "admitted for product use — does not imply reviewer "
            "sign-off or benchmark qualification."
        ),
    )


def _record_provenance(
    version: CharacterIdentityVersion,
    teammate: Teammate,
    run_id: uuid.UUID,
) -> ImportProvenance:
    """Land the ImportProvenance row with a scope-limited snapshot
    (Amendment E). Snapshot captures the three legacy identity
    fields plus the identity-page text describing how the operator
    was authoring the teammate. The whole Teammate row is not
    dumped.
    """
    identity_page_snapshot = {
        field: getattr(teammate, field, "")
        for field in _IDENTITY_PAGE_FIELDS
    }
    snapshot = {
        "runway_avatar_id": _stripped(teammate.runway_avatar_id),
        "portrait_path": _stripped(teammate.portrait_path),
        "voice_id": _stripped(teammate.voice_id),
        "identity_page_fields": identity_page_snapshot,
    }
    return ImportProvenance.objects.create(
        identity_version=version,
        source_teammate_id=teammate.id,
        import_run_id=run_id,
        migration_version=CURRENT_IMPORT_MIGRATION_VERSION,
        snapshot_schema_version=IMPORT_PROVENANCE_SNAPSHOT_SCHEMA_VERSION,
        legacy_snapshot=snapshot,
    )


__all__ = [
    "ImportAction",
    "ImportResult",
    "classify_teammate",
    "import_legacy_teammate",
]
