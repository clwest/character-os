"""Spokesperson — the unit of brand identity.

Holds the business brief, voice + portrait references, and the
media-engine identifiers that link to Runway-side artefacts. Videos
and ConversationThreads FK here. Replaces the legacy `Character`
model from runway-hackathon (design doc §4.3).
"""
from __future__ import annotations

import uuid

from django.db import models

from apps.accounts.models import Workspace


class Spokesperson(models.Model):
    """A named on-camera identity inside a workspace."""

    class Status(models.TextChoices):
        SETUP_NEEDED = "setup_needed", "Setup needed"
        READY = "ready", "Ready"
        ARCHIVED = "archived", "Archived"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="spokespeople",
    )
    name = models.CharField(max_length=120)
    business_brief = models.TextField(
        blank=True,
        help_text=(
            "One-paragraph description of the business this spokesperson "
            "represents. Promoted up from the legacy per-campaign "
            "brief_prompt (design doc §4.3)."
        ),
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SETUP_NEEDED,
    )

    # Media-engine integration — placeholders, populated by the
    # Django→FastAPI client when the avatar pipeline runs. Nullable
    # until the avatar is created.
    runway_avatar_id = models.CharField(max_length=120, blank=True, default="")
    runway_avatar_status = models.CharField(max_length=40, blank=True, default="")
    portrait_path = models.CharField(max_length=512, blank=True, default="")
    voice_id = models.CharField(max_length=120, blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "name"],
                name="spokesperson_unique_name_per_workspace",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.workspace.name})"
