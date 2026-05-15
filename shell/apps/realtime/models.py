"""Realtime avatar arc models — R1 schema slice.

SESSION 146 / R1. Mirrors V1's pattern:

* Every row has a required ``workspace`` FK + a
  ``spokesperson`` FK (contract rules 1 + 2).
* Cross-workspace references on session-create and on tool
  invocations are rejected structurally — at the ORM level
  via ``clean()`` + a pre_save signal as defense in depth.
* Provider abstraction (contract rule 8) — ``provider`` field
  on the session so a future second provider drops in without
  a schema migration.
* Transcript reference (contract rule 4) — ``transcript_asset``
  reuses V1's Asset shape rather than forking a new
  "RealtimeTranscript" table. Realtime sessions and recorded
  videos share the persistence surface.

Scope-lock: ``docs/design/REALTIME_AVATAR_V1.md`` §"Data
model" — 10 contract rules. R1 ships schema only; broker
(R3), provider integration (R2), and the SPA (R8) come
later.
"""
from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, Composition
from apps.conversations.models import ConversationThread
from apps.spokespeople.models import Spokesperson


class RealtimeSession(models.Model):
    """A live two-way WebRTC session with a spokesperson.

    Workspace + spokesperson anchors mirror V1's
    ``Composition`` shape. The ``thread`` FK ties the session
    to a K8 ``ConversationThread`` so the same logical
    conversation can span text chat (K9) + realtime audio (R+
    arc). Null in v1 because the SPA can spin up a standalone
    session before binding it to a thread; R3 broker logic
    enforces "if non-null, must be in the same workspace."

    ``provider_session_key`` carries the JWT-shaped token the
    SDK uses to connect. Never logged. v1 stores plaintext;
    v2 hardening can encrypt at rest.
    """

    class Provider(models.TextChoices):
        RUNWAY = "runway", "Runway"

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        CREATING = "creating", "Creating"
        NOT_READY = "not_ready", "Not Ready"
        READY = "ready", "Ready (live)"
        ENDED = "ended", "Ended"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Privacy + provenance anchors (contract rules 1 + 2)
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="realtime_sessions",
    )
    spokesperson = models.ForeignKey(
        Spokesperson,
        on_delete=models.PROTECT,
        related_name="realtime_sessions",
    )
    thread = models.ForeignKey(
        ConversationThread,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="realtime_sessions",
    )

    # Provider abstraction (contract rule 8)
    provider = models.CharField(
        max_length=20,
        choices=Provider.choices,
        default=Provider.RUNWAY,
    )
    provider_session_id = models.CharField(max_length=200, blank=True, default="")
    # NEVER LOG — SDK connect token.
    provider_session_key = models.TextField(blank=True, default="")
    provider_document_id = models.CharField(max_length=200, blank=True, default="")

    # K-arc bridge — chunk ids the session's document was
    # composed from. Same shape as
    # ``Composition.knowledge_chunk_ids`` (V-arc) so the F6
    # citations panel can reuse its resolver for realtime
    # sessions when the SPA surface lands (R8).
    knowledge_chunk_ids = models.JSONField(default=list, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.DRAFT,
    )
    error_message = models.TextField(blank=True, default="")

    # Lifecycle timestamps
    started_at = models.DateTimeField(null=True, blank=True)
    ready_at = models.DateTimeField(null=True, blank=True)
    ended_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField(null=True, blank=True)

    # Cost governance (contract rule 7)
    cost_estimate_micros = models.PositiveIntegerField(default=0)
    cost_actual_micros = models.PositiveIntegerField(default=0)
    duration_seconds = models.PositiveIntegerField(default=0)

    # Mock-mode (contract rule 9) — set at session-create
    # from env / settings, never mixed mid-session.
    mock_mode = models.BooleanField(default=False)

    # Transcript Asset reference (contract rule 4). Null
    # until the post-session transcript fetch + persist
    # completes (R5).
    transcript_asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_realtime_sessions",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["spokesperson", "created_at"]),
            models.Index(fields=["thread"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"realtime:{self.id} ({self.spokesperson.name})"

    def clean(self) -> None:
        """Cross-workspace validation. Spokesperson + thread
        + transcript_asset must all belong to the session's
        workspace.

        The pre_save signal catches direct ``.save()`` paths
        that bypass ``clean()``. Together = defense in depth.
        """
        super().clean()
        ws_id = self.workspace_id
        if ws_id is None:
            return

        if self.spokesperson_id and self.spokesperson.workspace_id != ws_id:
            raise ValidationError(
                f"RealtimeSession.spokesperson must be in the same workspace. "
                f"Session workspace: {ws_id}. "
                f"Spokesperson workspace: {self.spokesperson.workspace_id}."
            )

        if self.thread_id and self.thread.spokesperson.workspace_id != ws_id:
            raise ValidationError(
                f"RealtimeSession.thread must be in the same workspace. "
                f"Session workspace: {ws_id}. "
                f"Thread spokesperson workspace: "
                f"{self.thread.spokesperson.workspace_id}."
            )

        if self.transcript_asset_id and self.transcript_asset.workspace_id != ws_id:
            raise ValidationError(
                f"RealtimeSession.transcript_asset must be in the same "
                f"workspace. Session workspace: {ws_id}. "
                f"Asset workspace: {self.transcript_asset.workspace_id}."
            )


class RealtimeToolInvocation(models.Model):
    """Audit trail for every tool the avatar invoked.

    Lets operators replay "what did the avatar do?" + gives
    admins the cost-attribution surface. A tool that triggers
    a long video render burns Runway credits; we record the
    linkage to the produced Asset / Composition.

    Workspace scoping flows through ``session.workspace`` —
    no separate FK on this row. The cross-workspace concern
    is ``produced_asset`` / ``produced_composition`` pointing
    at another workspace's resources, which ``clean()`` +
    the signal reject.
    """

    class Status(models.TextChoices):
        INVOKED = "invoked", "Invoked"
        AWAITING_APPROVAL = "awaiting_approval", "Awaiting Approval"
        SUCCEEDED = "succeeded", "Succeeded"
        FAILED = "failed", "Failed"
        REJECTED = "rejected", "Rejected"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    session = models.ForeignKey(
        RealtimeSession,
        on_delete=models.CASCADE,
        related_name="tool_invocations",
    )

    tool_name = models.CharField(max_length=80)
    args = models.JSONField(default=dict, blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.INVOKED,
    )
    error_message = models.TextField(blank=True, default="")

    # If the invocation triggered an Asset / Composition,
    # link it for audit + cost attribution. Both nullable —
    # most tools (recall_knowledge, search_docs) don't
    # produce assets; only the render-y ones
    # (render_video, capture_clip) do.
    produced_asset = models.ForeignKey(
        Asset,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )
    produced_composition = models.ForeignKey(
        Composition,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="+",
    )

    invoked_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["session", "invoked_at"]),
            models.Index(fields=["tool_name"]),
        ]
        ordering = ["session", "invoked_at"]

    def __str__(self) -> str:
        return f"{self.tool_name}@{self.session_id}:{self.status}"

    @property
    def workspace(self):
        """Surface the session's workspace as a direct
        attribute so shared workspace-scoped permission
        resolvers (``character_os.permissions._workspace_of``)
        find it without traversing an extra FK. R7 introduces
        this when the invocation viewset starts using
        ``IsWorkspaceMember``.
        """
        return self.session.workspace

    def clean(self) -> None:
        """Reject produced_asset / produced_composition refs
        that belong to another workspace."""
        super().clean()
        if not self.session_id:
            return
        session_ws_id = (
            RealtimeSession.objects.filter(pk=self.session_id)
            .values_list("workspace_id", flat=True)
            .first()
        )
        if session_ws_id is None:
            return

        if (
            self.produced_asset_id
            and self.produced_asset.workspace_id != session_ws_id
        ):
            raise ValidationError(
                f"RealtimeToolInvocation.produced_asset must be in the "
                f"session's workspace. Session workspace: {session_ws_id}. "
                f"Asset workspace: {self.produced_asset.workspace_id}."
            )

        if (
            self.produced_composition_id
            and self.produced_composition.workspace_id != session_ws_id
        ):
            raise ValidationError(
                f"RealtimeToolInvocation.produced_composition must be in "
                f"the session's workspace. Session workspace: "
                f"{session_ws_id}. Composition workspace: "
                f"{self.produced_composition.workspace_id}."
            )
