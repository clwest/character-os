"""``Script`` — B-2 / E-arc persistence.

Slice B2.1 (SESSION 206). Per
``docs/design/AUTO_SCRIPTING_V1.md`` — lifts K6's in-primitive
script synthesis (``character_os.script_synthesis.build_render_brief``)
into a first-class persistent artifact with explicit operator
approval before render spend.

Mirrors the apps.publish / apps.campaigns shape — workspace FK,
status state machine, JSONField provenance, cross-workspace
guards at clean() + pre_save signal.

State machine (rule 10 — forward-only transitions):

* ``DRAFT`` — created or regenerated; operator can edit /
  regenerate / approve.
* ``READY`` — operator approved the draft. ``approved_at``
  set. Edits and regenerates refused (rule 10). Renders
  can fire.
* ``RENDERED`` — at least one ``auto_script`` Composition
  has been launched against this Script. Immutable.
* ``ARCHIVED`` — operator hid the Script from list views.
  Soft-delete equivalent; cascade-safe.

The model is permissive at the DB layer — state-machine
enforcement lives at the ``ScriptViewSet`` layer (B2.3). This
mirrors how apps.publish.PublishBundle leaves status open in
the model and the viewset gates the transitions.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models

from apps.accounts.models import Workspace
from apps.spokespeople.models import Spokesperson


class Script(models.Model):
    """A K6-drafted script grounded in K2 knowledge, persisted
    pre-render so the operator can review citations + verifier
    flags before spending Runway credit.

    See ``docs/design/AUTO_SCRIPTING_V1.md`` for the 10 contract
    rules. Load-bearing rules at the model layer:

    * Rule 1 — spokesperson + workspace required; clean() +
      pre_save signal reject cross-workspace combos.
    * Rule 3 — ``knowledge_chunk_ids`` persists citations.
    * Rule 4 — ``verification_status`` + ``verification_warnings``
      surface K6.4 results.
    * Rule 10 — state-machine enforcement at the viewset, not
      the model; ``approved_at`` set on DRAFT → READY.
    """

    class Status(models.TextChoices):
        DRAFT = "draft", "Draft"
        READY = "ready", "Ready"
        RENDERED = "rendered", "Rendered"
        ARCHIVED = "archived", "Archived"

    class VerificationStatus(models.TextChoices):
        """K6.4 verifier outcomes — mirrors
        ``Composition.VerificationStatus`` semantics but
        decoupled (B-2 may diverge from K6 later)."""

        VERIFIED = "verified", "Verified"
        WARNED = "warned", "Warned"
        SKIPPED = "skipped", "Skipped"
        BLOCKED = "blocked", "Blocked"
        # Empty string is also accepted — set when no LLM call
        # happened yet (initial row before draft_script runs).
        TRUSTED_PASSTHROUGH = "trusted_passthrough", "Trusted passthrough"

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )

    # Rule 1 + rule 6 — workspace anchor.
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="scripts",
    )

    # Rule 1 — spokesperson required; clean() enforces that
    # spokesperson.workspace == script.workspace.
    spokesperson = models.ForeignKey(
        Spokesperson,
        on_delete=models.CASCADE,
        related_name="scripts",
        help_text=(
            "Whose voice this script is drafted for. K6's system "
            "prompt is heavily spokesperson-anchored (tone_archetype "
            "+ personality + business_brief); cross-spokesperson "
            "reuse is structurally rejected — clone-to-edit for a "
            "different voice."
        ),
    )

    name = models.CharField(max_length=120)

    # Operator's input — doubles as the RAG query and the topic
    # for the LLM. Same role as ``operator_prompt`` in K6's
    # ``build_render_brief``.
    prompt = models.TextField()

    # K6.6 opener pin. Optional; verbatim first sentence when set.
    opener = models.CharField(max_length=280, blank=True, default="")

    # Rule 3 — first-class draft text + citations. ``draft_text``
    # is the source of truth for the voiceover; the
    # ``generate_avatar_speech`` primitive reads it verbatim and
    # skips in-primitive K6 synthesis (rule 7).
    draft_text = models.TextField(blank=True, default="")
    knowledge_chunk_ids = models.JSONField(default=list, blank=True)

    # Provenance for audit + cost surfacing.
    model = models.CharField(max_length=40, blank=True, default="")
    tokens_input = models.PositiveIntegerField(default=0)
    tokens_output = models.PositiveIntegerField(default=0)

    # Rule 4 — K6.4 verifier outcomes. ``verifier_mode`` is the
    # per-script override of ``settings.K6_CLAIM_VERIFIER_MODE``.
    verification_status = models.CharField(
        max_length=30,
        choices=VerificationStatus.choices,
        blank=True,
        default="",
    )
    verification_warnings = models.JSONField(default=list, blank=True)
    verifier_mode = models.CharField(
        max_length=10,
        blank=True,
        default="",
        help_text=(
            "Optional per-script override of "
            "settings.K6_CLAIM_VERIFIER_MODE. One of 'strict' / "
            "'warn' / 'off' / blank (inherit default)."
        ),
    )

    # Rule 10 — audit trail. Snapshot-on-regenerate; never
    # mutated. The live draft_text / knowledge_chunk_ids fields
    # always reflect the most recent successful draft.
    revision_history = models.JSONField(default=list, blank=True)

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
        related_name="created_scripts",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    # Set on DRAFT → READY transition (rule 10).
    approved_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=["workspace", "status"]),
            models.Index(fields=["spokesperson", "status"]),
            models.Index(fields=["verification_status"]),
            models.Index(fields=["workspace", "-created_at"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return (
            f"script {str(self.id)[:8]} [{self.status}] "
            f"{self.name!r}"
        )

    def clean(self) -> None:
        """Rule 1 — spokesperson must belong to the same
        workspace as the script."""
        super().clean()
        if self.spokesperson_id and self.workspace_id:
            sp_ws_id = (
                Spokesperson.objects.filter(pk=self.spokesperson_id)
                .values_list("workspace_id", flat=True)
                .first()
            )
            if sp_ws_id is not None and sp_ws_id != self.workspace_id:
                raise ValidationError({
                    "spokesperson": (
                        "spokesperson belongs to a different workspace "
                        "than this script."
                    ),
                })
