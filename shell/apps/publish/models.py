"""``PublishBundle`` + ``PublishVariant`` — D-arc / B-14
persistence.

Slice B14.2 (SESSION 205). Per
``docs/design/PUBLISH_BUNDLE_V1.md`` — one source CLIP + N
platforms = N ``publish_variant`` compositions, each producing
a platform-ready Asset.

Mirrors the C-arc (`PersonalizedCampaign` +
`PersonalizedRecipient`) shape closely — both are
"parent-bundle + N independent children, each producing one
Composition" patterns. The differences are:

* Source: PublishBundle takes ONE Asset(CLIP) as input
  (rule 1); PersonalizedCampaign takes one template + CSV.
* Children: PublishVariant carries platform-specific render
  config (target_ratio + max_duration_ms snapshotted from the
  catalog); PersonalizedRecipient carries per-row substitution
  variables.
* Tier gates: variants are free (rule 5); recipients cost
  $0.25/clip.

Cross-workspace guards (rule 2): clean() + pre_save signal.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType, Composition


class PublishBundle(models.Model):
    """A batch publish operation — one source CLIP → N
    platform-ready variants.

    Created in DRAFT status with N PublishVariant rows
    snapshotted from the catalog at create time. Operator
    reviews + launches.

    State machine (rule 6 — launch is operator-explicit):

    * ``DRAFT`` — created; variants exist but nothing has
      rendered.
    * ``LAUNCHING`` — operator hit launch; fan-out
      transaction is mid-flight.
    * ``IN_FLIGHT`` — all variant Compositions enqueued;
      some / all still running.
    * ``COMPLETED`` — every variant COMPLETED.
    * ``PARTIAL`` — some COMPLETED, others FAILED. Operator
      can retry failed variants individually (B14.3).
    * ``FAILED`` — every variant FAILED.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        LAUNCHING = "launching", "Launching"
        IN_FLIGHT = "in_flight", "In flight"
        COMPLETED = "completed", "Completed"
        PARTIAL = "partial", "Partial"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="publish_bundles",
    )

    # Rule 1 — single CLIP source per bundle. Constraint is
    # enforced at clean() (asset_type=CLIP + same workspace).
    source_clip = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="publish_bundles",
        help_text=(
            "The Asset(asset_type=CLIP) being packaged. Must "
            "live in the same workspace as the bundle. "
            "clean() + pre_save signal both guard."
        ),
    )

    name = models.CharField(max_length=120)

    # Rule 7 — snapshot the operator's platform selections at
    # create time. The catalog itself is closed in v1
    # (apps.compositions.platform_catalog), but persisting the
    # selected keys here means a future catalog change can't
    # silently retro-edit an old bundle's intent.
    selected_platforms = models.JSONField(default=list)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_publish_bundles",
    )

    launched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"publish-bundle {str(self.id)[:8]} [{self.status}] "
            f"{self.name!r}"
        )

    def clean(self) -> None:
        """Rule 1 — source must be a CLIP. Rule 2 — workspace
        isolation."""
        super().clean()
        if self.source_clip_id:
            asset_row = Asset.objects.filter(pk=self.source_clip_id).values(
                "asset_type", "workspace_id",
            ).first()
            if asset_row is not None:
                if asset_row["asset_type"] != AssetType.CLIP:
                    raise ValidationError({
                        "source_clip": (
                            f"source_clip must be asset_type=CLIP; "
                            f"got {asset_row['asset_type']!r}"
                        ),
                    })
                if (
                    self.workspace_id is not None
                    and asset_row["workspace_id"] != self.workspace_id
                ):
                    raise ValidationError({
                        "source_clip": (
                            "source_clip belongs to a different "
                            "workspace than this bundle."
                        ),
                    })


class PublishVariant(models.Model):
    """One row per ``(bundle, platform)`` pair.

    Workspace scoping inherits from ``bundle.workspace`` —
    no separate FK. The cross-workspace concern is
    ``produced_composition`` pointing at another workspace's
    Composition, which clean() + signal reject.

    State machine (rule 3 — per-variant failures don't
    block the bundle):

    * ``PENDING`` — created from the bundle's platform
      selection; not enqueued.
    * ``QUEUED`` — bundle launched; this variant's
      Composition has been enqueued.
    * ``RUNNING`` — V-arc runner picked it up.
    * ``COMPLETED`` — Composition reached COMPLETED;
      produced_composition + final asset are set.
    * ``FAILED`` — Composition reached FAILED / PARTIAL;
      error_message holds the cause.

    The platform parameters (target_ratio + max_duration_ms)
    are SNAPSHOTTED at create time (rule 7) so an old bundle
    renders at the original specs even if the catalog evolves.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    bundle = models.ForeignKey(
        PublishBundle,
        on_delete=models.CASCADE,
        related_name="variants",
    )

    # The catalog key. Stays stable as a string even if the
    # display label or other attributes evolve later.
    platform_key = models.CharField(max_length=40)

    # Snapshotted at create time per rule 7.
    target_ratio = models.CharField(max_length=20)
    max_duration_ms = models.PositiveIntegerField()

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    produced_composition = models.ForeignKey(
        Composition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_publish_variants",
    )

    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Progress query: list variants by status in a bundle.
            models.Index(fields=["bundle", "status"]),
            # Completion-signal reverse lookup: composition → variant.
            models.Index(fields=["produced_composition"]),
        ]
        ordering = ["bundle", "platform_key"]
        constraints = [
            # One variant per (bundle, platform) — operator
            # can't accidentally create two TikTok rows for the
            # same bundle.
            models.UniqueConstraint(
                fields=["bundle", "platform_key"],
                name="publish_variant_unique_bundle_platform",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"variant {str(self.id)[:8]} [{self.status}] "
            f"{self.platform_key!r}"
        )

    @property
    def workspace(self):
        """Surface bundle.workspace as a direct attribute for
        the shared ``IsWorkspaceMember`` permission resolver.
        Same shape as ``PersonalizedRecipient.workspace`` +
        ``RealtimeToolInvocation.workspace``."""
        return self.bundle.workspace

    def clean(self) -> None:
        """Rule 2 — produced_composition (when set) must live
        in the same workspace as the bundle."""
        super().clean()
        if self.bundle_id and self.produced_composition_id:
            bundle_ws_id = (
                PublishBundle.objects.filter(pk=self.bundle_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            comp_ws_id = (
                Composition.objects.filter(pk=self.produced_composition_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            if (
                bundle_ws_id is not None
                and comp_ws_id is not None
                and bundle_ws_id != comp_ws_id
            ):
                raise ValidationError({
                    "produced_composition": (
                        "produced_composition belongs to a different "
                        "workspace than this variant's bundle."
                    ),
                })
