"""``TranscriptHighlight`` — operator-approved highlight rows.

B-arc slice B1.2 (SESSION 202). Persistence layer for the
transcript miner. Each row is one LLM pick from
``select_transcript_highlights``; the operator reviews via the
SPA, approves picks they want as standalone clips, and rejects
the rest.

State machine:

    PENDING ──approve──▶ APPROVED ──composition_completed──▶ RENDERED
       │
       └──reject──▶ REJECTED

Contract rules in play (``TRANSCRIPT_MINER_V1.md``):

* Rule 2 — workspace-scoped. ``workspace`` FK +
  ``source_transcript`` FK; ``clean()`` rejects cross-workspace
  refs; signal in ``signals.py`` catches the raw ``.save()``
  path.
* Rule 3 — auditable. ``text`` + ``char_start`` + ``char_end``
  + ``llm_reasoning`` persisted from B1.1's helper output.
* Rule 5 — approval gate. ``status`` defaults to PENDING.
  APPROVED transition enqueues a composition (B1.4 handler).
* Rule 8 — 280-char cap. Enforced at the parser level in B1.1;
  ``clean()`` re-asserts here as defense in depth.
"""
from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType, Composition


# Mirrors the helper's MAX_HIGHLIGHT_CHARS (rule 8). Repeated
# here so the model layer can validate without importing the
# helper (which imports settings + OpenAI client lazily).
MAX_HIGHLIGHT_CHARS = 280


class TranscriptHighlight(models.Model):
    """One LLM-mined highlight from a transcript Asset.

    Workspace scoping rules:
    * ``workspace`` is the source of truth — every cross-FK
      (source_transcript, produced_composition) must match.
    * Cross-workspace refs raise ``ValidationError`` at
      ``clean()`` and again at ``pre_save`` via the signal
      receiver. Same defense-in-depth shape as the R-arc.

    State transitions (rule 5):
    * ``PENDING`` — fresh from the LLM. Operator hasn't
      decided.
    * ``APPROVED`` — operator approved; B1.4 handler
      enqueues a ``talking_head_polished`` composition;
      ``produced_composition`` FK gets set.
    * ``REJECTED`` — operator rejected. ``rejection_reason``
      optional. Row stays in DB for audit (Q-b-2 resolution).
    * ``RENDERED`` — produced_composition finished; signal
      from compositions arc flips the status.
    """

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        APPROVED = "approved", "Approved (rendering)"
        REJECTED = "rejected", "Rejected"
        RENDERED = "rendered", "Rendered"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="transcript_highlights",
    )

    source_transcript = models.ForeignKey(
        Asset,
        on_delete=models.CASCADE,
        related_name="mined_highlights",
        help_text=(
            "The Asset(asset_type=TRANSCRIPT) the LLM mined. "
            "Cross-workspace refs are rejected at clean()."
        ),
    )

    text = models.TextField(
        help_text=(
            "The highlight substring of the transcript body. "
            "Must satisfy source_transcript.inline_content"
            "[char_start:char_end] == text (rule 3)."
        ),
    )
    char_start = models.PositiveIntegerField()
    char_end = models.PositiveIntegerField()

    llm_reasoning = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Rationale string from the LLM for audit. Blank "
            "for mock-mode rows (defaults to a stub string in "
            "the miner)."
        ),
    )

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )

    # Per Q-b-4: approving auto-enqueues a
    # ``talking_head_polished`` composition. The FK is set
    # synchronously in the approve handler so the SPA can
    # show "rendering" + link to the composition immediately.
    produced_composition = models.ForeignKey(
        Composition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="source_highlights",
    )

    rejection_reason = models.TextField(blank=True, default="")

    mined_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)

    # LLM telemetry — per Q-b-5: first row in a mining call
    # holds the full call cost + token totals; subsequent rows
    # hold 0 / "". Keeps per-call accounting accurate without
    # introducing a separate MiningCall table.
    llm_model_id = models.CharField(max_length=80, blank=True, default="")
    llm_cost_micros = models.PositiveIntegerField(default=0)
    llm_tokens_input = models.PositiveIntegerField(default=0)
    llm_tokens_output = models.PositiveIntegerField(default=0)

    class Meta:
        indexes = [
            # Approval-queue read pattern: list PENDING in a
            # workspace.
            models.Index(fields=["workspace", "status"]),
            # "What did this transcript produce?"
            models.Index(fields=["source_transcript"]),
        ]
        ordering = ["-mined_at"]
        constraints = [
            models.CheckConstraint(
                check=models.Q(char_end__gt=models.F("char_start")),
                name="transcript_highlight_char_end_gt_start",
            ),
            models.CheckConstraint(
                check=models.Q(text__isnull=False),
                name="transcript_highlight_text_not_null",
            ),
        ]

    def __str__(self) -> str:
        return (
            f"highlight {str(self.id)[:8]} "
            f"[{self.status}] {self.text[:40]!r}"
        )

    def clean(self) -> None:
        """Enforce contract rules at form / explicit
        full_clean() time. ``signals.py`` catches the raw
        ``.save()`` path."""
        super().clean()

        # Rule 1 — source_transcript must be a TRANSCRIPT.
        if self.source_transcript_id:
            asset_type = (
                Asset.objects.filter(pk=self.source_transcript_id)
                .values_list("asset_type", flat=True)
                .first()
            )
            if asset_type is not None and asset_type != AssetType.TRANSCRIPT:
                raise ValidationError({
                    "source_transcript": (
                        f"source_transcript must be asset_type=TRANSCRIPT; "
                        f"got {asset_type!r}"
                    ),
                })

        # Rule 2 — workspace isolation.
        if self.workspace_id and self.source_transcript_id:
            source_ws = (
                Asset.objects.filter(pk=self.source_transcript_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            if source_ws is not None and source_ws != self.workspace_id:
                raise ValidationError({
                    "source_transcript": (
                        "source_transcript belongs to a different "
                        "workspace than this highlight."
                    ),
                })

        if self.workspace_id and self.produced_composition_id:
            comp_ws = (
                Composition.objects.filter(pk=self.produced_composition_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            if comp_ws is not None and comp_ws != self.workspace_id:
                raise ValidationError({
                    "produced_composition": (
                        "produced_composition belongs to a different "
                        "workspace than this highlight."
                    ),
                })

        # Rule 3 — char_end > char_start enforced at DB layer
        # via CheckConstraint; restate as a friendly error.
        if self.char_end <= self.char_start:
            raise ValidationError({
                "char_end": (
                    f"char_end ({self.char_end}) must be greater than "
                    f"char_start ({self.char_start})."
                ),
            })

        # Rule 8 — 280-char cap. Defense in depth; the parser
        # already trims, but a hand-constructed row could
        # bypass.
        if len(self.text or "") > MAX_HIGHLIGHT_CHARS:
            raise ValidationError({
                "text": (
                    f"text length ({len(self.text)}) exceeds the "
                    f"per-highlight cap ({MAX_HIGHLIGHT_CHARS} chars)."
                ),
            })
