"""``PersonalizedCampaign`` + ``PersonalizedRecipient`` —
C-arc / B-3 persistence.

Slice B3.2 (SESSION 203). Per
``docs/design/PERSONALIZED_VIDEO_V1.md`` — one template + N
recipients = N talking_head_polished compositions.

Two models:

* **PersonalizedCampaign** — the batch container. Holds the
  template, the operator-supplied name, the parsed
  placeholder list (the CSV header contract per rule 1),
  and a state machine that walks DRAFT → LAUNCHING → IN_FLIGHT
  → COMPLETED / PARTIAL / FAILED.
* **PersonalizedRecipient** — one row per recipient. Holds
  the variables dict (one CSV row), the rendered_script
  after template-render, and a per-recipient state machine
  PENDING → QUEUED → RUNNING → COMPLETED / FAILED. Each
  recipient gets its own Composition row (rule 2).

Cross-workspace guards (rule 3): clean() + pre_save signal.
Mirrors the B-1 / R-arc patterns.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Workspace
from apps.compositions.models import Composition
from apps.scripts.models import Script
from apps.spokespeople.models import Spokesperson


# Rule 1: campaign.template + campaign.placeholders are the
# CSV-header contract. Template can be long; placeholders is
# a small list.
MAX_TEMPLATE_CHARS = 4000


class PersonalizedCampaign(models.Model):
    """A batched personalized-video send.

    Created in DRAFT status; operator pastes CSV (creates
    PersonalizedRecipient rows); reviews; launches.

    State machine (rule 6 — launch is operator-explicit):

    * ``DRAFT`` — created; recipients may be empty or
      partially populated; nothing has rendered.
    * ``LAUNCHING`` — operator hit launch; the fan-out
      transaction is mid-flight (rows being created /
      Celery being enqueued).
    * ``IN_FLIGHT`` — all per-recipient Compositions are
      enqueued; some / all are still running.
    * ``COMPLETED`` — every recipient is COMPLETED.
    * ``PARTIAL`` — some recipients are COMPLETED, others
      FAILED. Operator can retry failed rows individually.
    * ``FAILED`` — every recipient is FAILED (rare; usually
      a tier-gate or external-API hiccup that hit
      everyone).
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
        related_name="personalized_campaigns",
    )

    # Rule 9 — composition name = `{campaign.name} — {recipient.label}`.
    # Length caps line up with Composition.name's TextField.
    spokesperson = models.ForeignKey(
        Spokesperson,
        on_delete=models.CASCADE,
        related_name="personalized_campaigns",
        help_text=(
            "The on-camera identity used for every recipient's "
            "talking_head_polished re-bake. Cross-workspace "
            "references rejected at clean()."
        ),
    )

    name = models.CharField(max_length=120)
    template = models.TextField(
        max_length=MAX_TEMPLATE_CHARS,
        help_text=(
            "Script template with {placeholder} variables. "
            "Doubled braces {{like-this}} escape (rule 7). "
            "Parsed at create time; placeholders field holds "
            "the resulting variable list."
        ),
    )
    placeholders = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "Parsed placeholder names from template. The CSV "
            "header MUST be a strict superset (rule 1)."
        ),
    )

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
        related_name="created_personalized_campaigns",
    )

    launched_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # BC1 — optional derivation pointer per B2_B3_COMPOSITION_V1
    # rule 1 (Script → Campaign is one-direction; back-reference
    # lives on this side only) + rule 9 (on_delete=PROTECT
    # prevents silent lineage orphaning). Workspace isolation
    # (rule 3) enforced via clean() + pre_save signal.
    source_script = models.ForeignKey(
        Script,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="derived_campaigns",
        help_text=(
            "Optional source Script row this Campaign derives "
            "from. When set, the launch path propagates the "
            "Script's knowledge_chunk_ids + synthesized_brief "
            "(substituted per recipient) + verification flags "
            "onto every per-recipient Composition (BC0 rule 4)."
        ),
    )

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["workspace", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"campaign {str(self.id)[:8]} [{self.status}] {self.name!r}"

    def clean(self) -> None:
        """Rule 3 — workspace isolation. spokesperson AND
        source_script (when set) must be in the same workspace
        as the campaign."""
        super().clean()
        if self.workspace_id and self.spokesperson_id:
            sp_ws_id = (
                Spokesperson.objects.filter(pk=self.spokesperson_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            if sp_ws_id is not None and sp_ws_id != self.workspace_id:
                raise ValidationError({
                    "spokesperson": (
                        "spokesperson belongs to a different "
                        "workspace than this campaign."
                    ),
                })
        # BC1 / BC0 rule 3 — source_script workspace check.
        if self.workspace_id and self.source_script_id:
            script_ws_id = (
                Script.objects.filter(pk=self.source_script_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            if (
                script_ws_id is not None
                and script_ws_id != self.workspace_id
            ):
                raise ValidationError({
                    "source_script": (
                        "source_script belongs to a different "
                        "workspace than this campaign."
                    ),
                })


class PersonalizedRecipient(models.Model):
    """One row per recipient. Holds the substituted variables +
    per-recipient state.

    Workspace scoping inherits from ``campaign.workspace`` —
    no separate FK. Cross-workspace concerns are
    ``produced_composition`` pointing at another workspace's
    row, which ``clean()`` + signal reject.

    State machine (rule 8 — per-recipient failures don't
    block the batch):

    * ``PENDING`` — created from a CSV row; rendered_script
      populated.
    * ``QUEUED`` — campaign launched; this recipient's
      composition has been enqueued via Celery.
    * ``RUNNING`` — V-arc runner picked it up.
    * ``COMPLETED`` — composition reached status=COMPLETED;
      produced_composition + (transitively) final asset
      are set.
    * ``FAILED`` — composition reached status=FAILED OR
      template-render raised TemplateError(kind="missing")
      at launch time. error_message holds the cause.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        QUEUED = "queued", "Queued"
        RUNNING = "running", "Running"
        COMPLETED = "completed", "Completed"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    campaign = models.ForeignKey(
        PersonalizedCampaign,
        on_delete=models.CASCADE,
        related_name="recipients",
    )

    # Rule 5 — PII storage is opt-in via the variables dict.
    # Operator's CSV header drives the keys; we never special-
    # case email / phone / name.
    variables = models.JSONField(
        default=dict,
        help_text=(
            "One CSV row's values keyed by header column. Keys "
            "MUST be a superset of campaign.placeholders."
        ),
    )

    # Rule 9 — derived display label. first_name | email |
    # 'recipient #N'. Stored (not computed) so the SPA grid
    # doesn't have to re-derive on every render.
    label = models.CharField(max_length=200)

    # Rule 2 — substituted script. Computed at launch time;
    # persisted so operator can audit what the avatar said
    # without re-running template-render.
    rendered_script = models.TextField(blank=True, default="")

    # Rule 9 — stable row order for SPA grid display.
    position = models.PositiveIntegerField(default=0)

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
        related_name="source_recipients",
    )

    error_message = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            # Progress query: list recipients by status in a
            # campaign.
            models.Index(fields=["campaign", "status"]),
            # Completion-signal reverse lookup: from a
            # composition find its recipient row.
            models.Index(fields=["produced_composition"]),
        ]
        ordering = ["campaign", "position"]

    def __str__(self) -> str:
        return (
            f"recipient {str(self.id)[:8]} [{self.status}] "
            f"{self.label!r}"
        )

    @property
    def workspace(self):
        """Expose campaign.workspace as a direct attribute for
        the shared ``IsWorkspaceMember`` permission resolver.
        Same shape as ``RealtimeToolInvocation.workspace``."""
        return self.campaign.workspace

    def clean(self) -> None:
        """Rule 3 — workspace isolation. produced_composition
        (when set) must belong to the same workspace as
        campaign.workspace."""
        super().clean()
        if self.campaign_id and self.produced_composition_id:
            campaign_ws_id = (
                PersonalizedCampaign.objects.filter(pk=self.campaign_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            comp_ws_id = (
                Composition.objects.filter(pk=self.produced_composition_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            if (
                campaign_ws_id is not None
                and comp_ws_id is not None
                and campaign_ws_id != comp_ws_id
            ):
                raise ValidationError({
                    "produced_composition": (
                        "produced_composition belongs to a different "
                        "workspace than this recipient's campaign."
                    ),
                })
