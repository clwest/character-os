"""§19 Step 9.b.3a Step-10 readiness derivation (SESSION 249).

Backend derivation function ONLY — the operator-visible CLI command
lands at 9.b.3b. This module provides the pure predicate that other
9.b.3a code (tests, promotion service, later 9.b.3b command) can call
without side effects.

Predicate composition per operator §Q + revised architecture Q25:

1. fixture_id in {fixture_h1..h4} (fixture_nh1 excluded).
2. review_complete — 7 human purposes all terminally dispositioned.
3. approval_floor_satisfied (review side) — required purposes have
   'selected' terminal decision.
4. canonical_reference_floor_satisfied — required purposes have
   APPROVED IdentityReference on the current identity version.
5. canonical_version_admitted — CharacterIdentityVersion.state ==
   APPROVED.
6. publication_complete — every APPROVED IdentityReference's
   PromotionAudit has evidence_published_at_utc NOT NULL, and its
   revision folder exists on disk with the .materialization_complete
   sentinel.
7. evidence_integrity — durable Asset file SHA-256 matches the
   value recorded in PromotionAudit at DB time (belt-and-suspenders
   drift check).

Readiness is expressed as an aggregate + individual booleans so the
9.b.3b CLI can emit structured JSON per failure gate.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    IdentityReference,
    ReferenceState,
)
from apps.identity.schema_loader import get_branch_schema

from apps.accounts.models import Workspace

from .evidence import AUTHORIZED_FIXTURE_IDS
from .journal import derive_fixture_progress
from .models import PromotionAudit
from .workspace import BOOTSTRAP_WORKSPACE_SLUG


@dataclass(frozen=True)
class FixtureReadiness:
    fixture_id: str
    fixture_authorized: bool
    review_complete: bool
    approval_floor_satisfied: bool
    canonical_reference_floor_satisfied: bool
    canonical_version_admitted: bool
    publication_complete: bool
    evidence_integrity: bool
    failures: tuple[str, ...]

    @property
    def ready(self) -> bool:
        return (
            self.fixture_authorized
            and self.review_complete
            and self.approval_floor_satisfied
            and self.canonical_reference_floor_satisfied
            and self.canonical_version_admitted
            and self.publication_complete
            and self.evidence_integrity
        )


def derive_step10_readiness(fixture_id: str) -> FixtureReadiness:
    """Pure predicate — no DB writes, no FS writes.

    Returns a :class:`FixtureReadiness` with each gate's boolean plus
    a ``failures`` tuple naming which gates blocked readiness (or
    empty if the fixture is ready).
    """
    fixture_authorized = fixture_id in AUTHORIZED_FIXTURE_IDS
    if not fixture_authorized:
        return FixtureReadiness(
            fixture_id=fixture_id,
            fixture_authorized=False,
            review_complete=False,
            approval_floor_satisfied=False,
            canonical_reference_floor_satisfied=False,
            canonical_version_admitted=False,
            publication_complete=False,
            evidence_integrity=False,
            failures=("fixture_not_authorized",),
        )

    schema = get_branch_schema("human")
    required = list(schema.required_for_identity)
    progress = derive_fixture_progress(fixture_id, required)

    review_complete = progress.review_complete
    approval_floor_satisfied = progress.approval_floor_satisfied

    # Canonical substrate side.
    workspace = Workspace.objects.filter(slug=BOOTSTRAP_WORKSPACE_SLUG).first()
    identity = None
    version = None
    if workspace is not None:
        identity = CharacterIdentity.objects.filter(
            workspace=workspace, name=fixture_id
        ).first()
        if identity is not None:
            version = (
                CharacterIdentityVersion.objects.filter(
                    identity=identity,
                    state=CharacterIdentityVersion.State.APPROVED,
                )
                .first()
            )

    canonical_version_admitted = version is not None

    canonical_reference_floor_satisfied = False
    approved_refs: list[IdentityReference] = []
    if version is not None:
        approved_refs = list(
            IdentityReference.objects.filter(
                identity_version=version,
                state=ReferenceState.APPROVED,
            )
        )
        approved_pairs = {
            f"{ref.kind}/{ref.purpose}" for ref in approved_refs
        }
        canonical_reference_floor_satisfied = all(
            pair in approved_pairs for pair in required
        )

    # Publication + integrity.
    publication_complete = True
    evidence_integrity = True
    if approved_refs:
        for ref in approved_refs:
            audit = PromotionAudit.objects.filter(
                identity_reference=ref
            ).first()
            if audit is None or audit.evidence_published_at_utc is None:
                publication_complete = False
                continue
            # Filesystem sentinel check.
            from .promotion import _revision_folder

            revision_folder = _revision_folder(
                audit.fixture_id,
                audit.reference_kind,
                audit.reference_purpose,
                audit.slot_revision,
            )
            if not (revision_folder / ".materialization_complete").exists():
                publication_complete = False
                continue
            # Evidence integrity: file bytes still match recorded sha.
            raw_path = Path(audit.raw_asset.file_path)
            if not raw_path.exists():
                evidence_integrity = False
                continue
            recorded_sha = (audit.raw_asset.source_spec or {}).get("sha256")
            actual_sha = hashlib.sha256(raw_path.read_bytes()).hexdigest()
            if recorded_sha != actual_sha:
                evidence_integrity = False
    else:
        # No approved references means publication/integrity are
        # trivially "not blocked" for the readiness gate — the earlier
        # canonical_reference_floor_satisfied gate catches it.
        publication_complete = True
        evidence_integrity = True

    failures: list[str] = []
    if not review_complete:
        failures.append("review_incomplete")
    if not approval_floor_satisfied:
        failures.append("approval_floor_unsatisfied")
    if not canonical_reference_floor_satisfied:
        failures.append("canonical_reference_floor_unsatisfied")
    if not canonical_version_admitted:
        failures.append("canonical_version_not_admitted")
    if not publication_complete:
        failures.append("publication_pending")
    if not evidence_integrity:
        failures.append("evidence_integrity_drift")

    return FixtureReadiness(
        fixture_id=fixture_id,
        fixture_authorized=fixture_authorized,
        review_complete=review_complete,
        approval_floor_satisfied=approval_floor_satisfied,
        canonical_reference_floor_satisfied=canonical_reference_floor_satisfied,
        canonical_version_admitted=canonical_version_admitted,
        publication_complete=publication_complete,
        evidence_integrity=evidence_integrity,
        failures=tuple(failures),
    )
