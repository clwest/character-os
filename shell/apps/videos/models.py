"""Video — the unit of work.

Each video is one rendered output (a spokesperson ad, a dialogue
scene, a cinematic clip, etc.). Replaces the legacy OutputRecord
(design doc §4.4). Belongs to a Spokesperson which belongs to a
Workspace; the FK chain is the multi-tenant guarantee.
"""
from __future__ import annotations

import uuid

from django.db import models

from apps.spokespeople.models import Spokesperson


class Video(models.Model):
    """A single rendered media artefact."""

    class Kind(models.TextChoices):
        SPOKESPERSON_AD = "spokesperson_ad", "Spokesperson ad"
        LONG_SPOKESPERSON_AD = "long_spokesperson_ad", "Long spokesperson ad"
        DIALOGUE_SCENE = "dialogue_scene", "Dialogue scene"
        CINEMATIC_VIDEO = "cinematic_video", "Cinematic"
        STORYBOARD = "storyboard", "Storyboard"
        STORYBOARD_VOICED = "storyboard_voiced", "Storyboard (voiced)"
        VOICED_COMMERCIAL = "voiced_commercial", "Voiced commercial"
        SPOKESPERSON_REELS = "spokesperson_reels", "Spokesperson reels"
        DIALOGUE_SCENE_REELS = "dialogue_scene_reels", "Dialogue reels"
        SPOKESPERSON_AD_DUBBED = "spokesperson_ad_dubbed", "Dubbed ad"
        SPOKESPERSON_AD_REMIX = "spokesperson_ad_remix", "Style remix"
        SPOKESPERSON_AD_POLISHED = "spokesperson_ad_polished", "Polished ad"
        SPOKESPERSON_AD_WITH_PIP = "spokesperson_ad_with_pip", "Ad with PiP"
        SPOKESPERSON_AD_WITH_BACKDROP = "spokesperson_ad_with_backdrop", "Ad with backdrop"
        SPOKESPERSON_AD_WITH_COHOST = "spokesperson_ad_with_cohost", "Ad with co-host"
        SPOKESPERSON_AD_WITH_MUSIC = "spokesperson_ad_with_music", "Ad with music"
        SPOKESPERSON_AD_WITH_BROLL = "spokesperson_ad_with_broll", "Ad with B-roll"
        SPOKESPERSON_AD_WITH_ANIMATED_PIP = (
            "spokesperson_ad_with_animated_pip",
            "Ad with animated PiP",
        )

    class Status(models.TextChoices):
        PENDING = "pending", "Pending"
        RENDERING = "rendering", "Rendering"
        READY = "ready", "Ready"
        FAILED = "failed", "Failed"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spokesperson = models.ForeignKey(
        Spokesperson,
        on_delete=models.CASCADE,
        related_name="videos",
    )

    # SESSION 143 / V6 — backwards-compat link. Each Video now
    # rides on a ``talking_head`` Composition (for kind=
    # spokesperson_ad); the legacy SPA surface keeps reading
    # ``output_path``/``status``/etc. but those fields are
    # populated by syncing from the composition's terminal
    # state via ``apps.videos.signals``. Null for in-flight
    # rows on the legacy media-engine path (un-supported
    # kinds) and for rows that pre-date the migration.
    composition = models.ForeignKey(
        "compositions.Composition",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="videos",
        help_text=(
            "Underlying Composition that produces this Video's "
            "output. Populated by perform_create when kind is "
            "supported by a starter composition; null for "
            "legacy / unsupported kinds."
        ),
    )
    title = models.CharField(max_length=200, blank=True, default="")
    brief = models.TextField(
        blank=True,
        help_text=(
            "One-line override of the spokesperson's business_brief for "
            "this specific video (e.g., 'Black Friday sale'). Empty = "
            "use the spokesperson's default brief."
        ),
    )
    kind = models.CharField(
        max_length=40,
        choices=Kind.choices,
        default=Kind.SPOKESPERSON_AD,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.PENDING,
    )
    output_path = models.CharField(max_length=512, blank=True, default="")
    duration_seconds = models.FloatField(null=True, blank=True)
    tags = models.JSONField(
        default=list,
        blank=True,
        help_text="Soft topic tags. Hidden in v1 UI (design doc §4.4).",
    )

    # Media-engine integration placeholder — task id, error text, etc.
    media_engine_task_id = models.CharField(max_length=120, blank=True, default="")
    error_message = models.TextField(blank=True, default="")

    # SESSION 139 / K6 — citation log. Which KnowledgeChunk ids fed
    # the synthesized brief sent to the media-engine. Empty list when
    # no knowledge was visible to the spokesperson at render time
    # (graceful-degradation path; see contract rule 6 in
    # ``docs/design/KNOWLEDGE_LAYER.md``).
    knowledge_chunk_ids = models.JSONField(
        default=list,
        blank=True,
        help_text=(
            "List of KnowledgeChunk UUIDs (as strings) injected into the "
            "render-time prompt synthesis. No UI in v1 — present for "
            "audit + future operator-facing 'why did the spokesperson say "
            "that?' surfaces."
        ),
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["spokesperson", "-created_at"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        label = self.title or self.brief[:40] or str(self.id)[:8]
        return f"{label} [{self.kind} {self.status}]"
