"""§19 Step 9.b.3a substrate models (SESSION 249).

Two small models:

* :class:`BootstrapEvidenceIndex` — race-safe evidence dedup surface
  keyed by ``frozen_candidate_id``. First promotion for a fcid creates
  Assets/GR/NM + one index row; subsequent promotions of the same fcid
  (e.g. amend A→B→A) reuse the linked rows. Unique constraint on
  ``frozen_candidate_id`` is the DB-level race guard (Finding 8).

* :class:`PromotionAudit` — per-promotion materialization + recovery
  index. Unique on ``decision_id`` for retry idempotency; also unique
  on ``(character_identity_version, reference_kind, reference_purpose,
  slot_revision)`` for defense-in-depth. ``frozen_candidate_id`` is
  indexed but not unique (Finding 7). Populated only for
  ``selected`` decisions — ``no_candidate_approved`` supersedes are
  journal-driven per Finding 9.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.db import models

from apps.compositions.models import Asset
from apps.identity.models import (
    CharacterIdentityVersion,
    GenerationRecord,
    IdentityReference,
    NormalizationManifest,
)


class BootstrapEvidenceIndex(models.Model):
    """Race-safe evidence dedup surface, keyed by
    ``frozen_candidate_id``.

    One row per unique frozen candidate that has been promoted at
    least once. Later promotions of the same fcid reuse the
    referenced evidence rows — Assets, GenerationRecord, and
    NormalizationManifest are per-provider-call evidence and stable
    across amendments. Only :class:`IdentityReference` and
    :class:`PromotionAudit` are decision-revision-specific.

    Unique constraint on ``frozen_candidate_id`` guarantees dedup
    under concurrent retries — the second writer's insert raises
    ``IntegrityError`` and the transaction rolls back for a clean
    retry.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    frozen_candidate_id = models.TextField(
        unique=True,
        help_text=(
            "Canonical ``<run_id>/<direction>/<provider>/<cell_id>`` "
            "identifier per SESSION 249 Finding 1. The DB uniqueness "
            "constraint is the race-safe dedup guarantee per Finding 8."
        ),
    )
    raw_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="bootstrap_evidence_raw",
    )
    normalized_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="bootstrap_evidence_normalized",
    )
    generation_record = models.ForeignKey(
        GenerationRecord,
        on_delete=models.PROTECT,
        related_name="bootstrap_evidence",
    )
    normalization_manifest = models.ForeignKey(
        NormalizationManifest,
        on_delete=models.PROTECT,
        related_name="bootstrap_evidence",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]

    def __str__(self) -> str:
        return f"evidence[{self.frozen_candidate_id}]"


class PromotionAudit(models.Model):
    """Per-promotion materialization + recovery index.

    One row per ``selected`` reviewer decision that has been (or is
    being) materialized to canonical substrate + filesystem revision.
    ``no_candidate_approved`` amendments create no row here — they
    are journal-driven per Finding 9.

    Load-bearing invariants:

    * ``unique(decision_id)`` — retry idempotency key (Finding 7).
      Same client-supplied decision_id returns the stored row without
      side effects.
    * ``unique(character_identity_version_id, reference_kind,
      reference_purpose, slot_revision)`` — defense-in-depth against
      slot-revision collisions.
    * ``frozen_candidate_id`` is indexed but NOT unique — the same
      fcid may legitimately appear in multiple rows tied to different
      decisions (amend A → B → back to A).
    * ``evidence_published_at_utc`` is nullable — NULL means the DB
      transaction committed but the filesystem revision folder has
      not yet been published. Resume via
      ``bootstrap_review_resume_pending_publications``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    decision_id = models.UUIDField(
        unique=True,
        help_text=(
            "The reviewer's client-generated decision_id UUID (from the "
            "9.b.2 journal). Retry idempotency key."
        ),
    )
    frozen_candidate_id = models.TextField(
        db_index=True,
        help_text=(
            "Canonical fcid per Finding 1. Indexed but not unique — "
            "amendments may re-select the same fcid in a later revision."
        ),
    )
    bootstrap_run_id = models.TextField()
    fixture_id = models.TextField()
    direction = models.TextField()
    provider = models.TextField()
    cell_id = models.TextField()
    reference_kind = models.TextField()
    reference_purpose = models.TextField()
    surface_profile = models.TextField()
    slot_revision = models.PositiveIntegerField(
        help_text=(
            "Monotonically increasing within the slot; matches the "
            "filesystem revision folder ``bootstrap/references/"
            "<kind>/<purpose>/<slot_revision>/``."
        ),
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    raw_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="bootstrap_promotion_raw",
    )
    normalized_asset = models.ForeignKey(
        Asset,
        on_delete=models.PROTECT,
        related_name="bootstrap_promotion_normalized",
    )
    generation_record = models.ForeignKey(
        GenerationRecord,
        on_delete=models.PROTECT,
        related_name="bootstrap_promotions",
    )
    normalization_manifest = models.ForeignKey(
        NormalizationManifest,
        on_delete=models.PROTECT,
        related_name="bootstrap_promotions",
    )
    identity_reference = models.ForeignKey(
        IdentityReference,
        on_delete=models.PROTECT,
        related_name="bootstrap_promotions",
    )
    character_identity_version = models.ForeignKey(
        CharacterIdentityVersion,
        on_delete=models.PROTECT,
        related_name="bootstrap_promotions",
    )
    substrate_committed_at_utc = models.DateTimeField()
    evidence_published_at_utc = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=[
                    "character_identity_version",
                    "reference_kind",
                    "reference_purpose",
                    "slot_revision",
                ],
                name="bootstrap_promotion_unique_slot_revision",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"promotion[{self.decision_id}] "
            f"{self.fixture_id}/{self.reference_kind}/{self.reference_purpose}"
            f"@rev{self.slot_revision}"
        )
