"""ConversationThread — realtime chats with a spokesperson.

v1 stub: just the thread metadata. Messages, transcripts, and memory
documents come in their own slice. Threads belong to a Spokesperson;
in the legacy model they belonged to a Campaign, but campaigns are
gone (design doc §4.2).
"""
from __future__ import annotations

import uuid

from django.db import models

from apps.spokespeople.models import Spokesperson


class ConversationThread(models.Model):
    """A realtime conversation thread with a spokesperson."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spokesperson = models.ForeignKey(
        Spokesperson,
        on_delete=models.CASCADE,
        related_name="conversation_threads",
    )
    title = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_activity_at"]
        indexes = [
            models.Index(fields=["spokesperson", "-last_activity_at"]),
        ]

    def __str__(self) -> str:
        label = self.title or f"Thread {str(self.id)[:8]}"
        return f"{label} ({self.spokesperson.name})"
