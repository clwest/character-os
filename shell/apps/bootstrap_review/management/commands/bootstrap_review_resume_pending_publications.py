"""SESSION 249 §19 Step 9.b.3a resume command.

Idempotent recovery pass for two failure classes:

1. PromotionAudit rows with ``evidence_published_at_utc IS NULL`` —
   DB committed but filesystem revision folder never published.
2. Fixture slots whose current journal decision is
   ``no_candidate_approved`` but the prior APPROVED IdentityReference
   at that slot is still APPROVED (missed supersede transition).

Both operations are journal- and DB-driven. The command never
regenerates provider evidence, never re-runs normalization, and
never creates duplicate DB rows.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.accounts.models import Workspace
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    IdentityReference,
    ReferenceState,
)
from apps.identity import services as identity_services

from apps.bootstrap_review.evidence import AUTHORIZED_FIXTURE_IDS
from apps.bootstrap_review.journal import current_decision_per_slot
from apps.bootstrap_review.models import PromotionAudit
from apps.bootstrap_review.promotion import _publish_revision_folder
from apps.bootstrap_review.workspace import BOOTSTRAP_WORKSPACE_SLUG


class Command(BaseCommand):
    help = (
        "Resume incomplete bootstrap-review promotion publications + "
        "apply missed no_candidate_approved supersedes. Idempotent."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report actions without applying them.",
        )

    def handle(self, *args, **options):
        dry_run: bool = options.get("dry_run", False)

        pending_publications = list(
            PromotionAudit.objects.filter(evidence_published_at_utc__isnull=True)
        )
        pending_supersedes = _find_pending_supersedes()

        self.stdout.write(
            f"bootstrap_review_resume: "
            f"{len(pending_publications)} pending publication(s), "
            f"{len(pending_supersedes)} pending supersede(s)"
        )

        if dry_run:
            for audit in pending_publications:
                self.stdout.write(
                    f"  [dry-run] would publish {audit.fixture_id}/"
                    f"{audit.reference_kind}/{audit.reference_purpose}"
                    f"@rev{audit.slot_revision}"
                )
            for ref in pending_supersedes:
                self.stdout.write(
                    f"  [dry-run] would supersede reference {ref.id} "
                    f"({ref.kind}/{ref.purpose})"
                )
            return

        for audit in pending_publications:
            _publish_revision_folder(audit)
            self.stdout.write(
                f"  ✓ published {audit.fixture_id}/{audit.reference_kind}/"
                f"{audit.reference_purpose}@rev{audit.slot_revision}"
            )

        for ref in pending_supersedes:
            identity_services.supersede_reference_at_slot(
                ref.identity_version,
                kind=ref.kind,
                purpose=ref.purpose,
                reason=(
                    "resume: journal shows no_candidate_approved for slot "
                    "but reference was still APPROVED"
                ),
            )
            self.stdout.write(
                f"  ✓ superseded reference {ref.id} "
                f"({ref.kind}/{ref.purpose})"
            )

        self.stdout.write(self.style.SUCCESS("bootstrap_review_resume: done"))


def _find_pending_supersedes() -> list[IdentityReference]:
    """Locate APPROVED IdentityReferences whose slot's current journal
    decision is ``no_candidate_approved``.
    """
    workspace = Workspace.objects.filter(slug=BOOTSTRAP_WORKSPACE_SLUG).first()
    if workspace is None:
        return []
    pending: list[IdentityReference] = []
    for fixture_id in AUTHORIZED_FIXTURE_IDS:
        current = current_decision_per_slot(fixture_id)
        if not current:
            continue
        identity = CharacterIdentity.objects.filter(
            workspace=workspace, name=fixture_id
        ).first()
        if identity is None:
            continue
        version = (
            CharacterIdentityVersion.objects.filter(identity=identity)
            .order_by("-revision")
            .first()
        )
        if version is None:
            continue
        for (kind, purpose), decision in current.items():
            if decision["disposition"] != "no_candidate_approved":
                continue
            ref = IdentityReference.objects.filter(
                identity_version=version,
                kind=kind,
                purpose=purpose,
                state=ReferenceState.APPROVED,
            ).first()
            if ref is not None:
                pending.append(ref)
    return pending
