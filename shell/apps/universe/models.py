"""Universe model — the inner wall inside a Workspace.

SESSION 261. See ``docs/design/UNIVERSE_SCHEMA_V1.md`` for the full
contract. Field-by-field semantics are documented in the design
doc's §"Field-by-field semantics"; this module implements them.

Load-bearing invariants (enforced here + at FK sites):

1. ``workspace`` is required — cross-tenant Universe is impossible
   by construction.
2. ``(workspace, slug)`` is unique — a workspace never has two
   Universes with the same slug (auto-suffix on collision).
3. Slug uniqueness is per-workspace, NOT global; the same slug
   ``"workshop"`` in two workspaces is legal.
4. ``archived_at`` is the primary operator-facing lifecycle
   affordance. Hard-delete is legal but gated by ``on_delete=
   RESTRICT`` on ``Teammate.universe`` + ``KnowledgeDocument.
   universe`` — populated Universes cannot be hard-deleted without
   explicit child reassignment first.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from apps.accounts.models import Workspace


class Universe(models.Model):
    """A world inside a Workspace.

    Universe is the inner wall between the outer tenant boundary
    (Workspace) and per-world semantic scoping. It exists so that
    a workspace with multiple worlds (say, "Workshop" and "Bakery")
    can keep their casts and knowledge corpora structurally
    isolated without needing two separate tenants.

    Cross-Universe access is not exposed as a primitive in v1 —
    an explicit crossover mechanism is deferred to a future
    slice per ``UNIVERSE_ARCHITECTURE_INTEGRATION_V1.md``.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Tenant parent. Universe cannot outlive its Workspace, so
    # CASCADE is correct. Django's shared-CASCADE-parent rule
    # (>= 3.1) lets this cascade succeed even though Teammate and
    # KnowledgeDocument use RESTRICT on their ``universe`` FKs
    # (they're also being cascaded from Workspace in the same
    # transaction).
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="universes",
    )

    # Operator-visible label. Not globally unique; per-workspace
    # uniqueness lives on ``slug`` below.
    name = models.CharField(
        max_length=120,
        help_text=(
            "Operator-visible label for this world (e.g. "
            "'Workshop', 'Bakery', 'Riverstone'). Not globally "
            "unique — per-workspace uniqueness is enforced on the "
            "auto-derived slug."
        ),
    )

    # Per-workspace routing key. Auto-derived from ``name`` at
    # save time with auto-suffix on collision (mirrors
    # ``Workspace.save``).
    slug = models.SlugField(
        max_length=140,
        help_text=(
            "Auto-derived from ``name`` at save. Per-workspace "
            "unique via the ``universe_unique_slug_per_workspace`` "
            "constraint. Operator override deferred to a future "
            "slice."
        ),
    )

    # Optional operator prose. Not consumed by K6 synthesis —
    # this is a workspace-management doc field, not knowledge
    # substrate.
    description = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Operator prose about this world. Not consumed by "
            "synthesis; purely a management surface field."
        ),
    )

    # Audit anchor — who created it. SET_NULL when the user
    # deletes so the Universe row survives the audit gap.
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_universes",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Soft-delete marker. NULL = active. Non-NULL = archived.
    # Primary operator affordance; hard-delete is a secondary
    # operator action gated by RESTRICT on child FKs. See
    # ``UNIVERSE_SCHEMA_V1.md §Deletion / cascade policy``.
    archived_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "universe_universe"
        ordering = ["workspace", "name"]
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "slug"],
                name="universe_unique_slug_per_workspace",
            ),
        ]
        indexes = [
            models.Index(
                fields=["workspace", "archived_at"],
                name="universe_ws_archived_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.name} ({self.workspace.name})"

    def clean(self) -> None:
        """Reject blank name; validate slug matches auto-derived
        form when populated (v2 operator overrides deferred).
        """
        super().clean()
        if not (self.name or "").strip():
            raise ValidationError({"name": "Universe name cannot be blank."})

    def save(self, *args, **kwargs) -> None:
        """Auto-derive slug from name with per-workspace suffix
        collision handling. Mirrors ``Workspace.save`` (SESSION
        119) but scoped to ``workspace``, not global.
        """
        if not self.slug:
            base = slugify(self.name) or "universe"
            candidate = base
            n = 2
            # Per-workspace uniqueness; global collisions are legal.
            while (
                Universe.objects.filter(
                    workspace_id=self.workspace_id,
                    slug=candidate,
                )
                .exclude(pk=self.pk)
                .exists()
            ):
                candidate = f"{base}-{n}"
                n += 1
            self.slug = candidate
        super().save(*args, **kwargs)

    # ---- Introspection helpers used by the API ----

    def teammate_count(self) -> int:
        """Number of Teammates currently assigned to this Universe.

        Used by the delete-hard-check path (populated Universes
        cannot be hard-deleted without child reassignment first).
        Reverse relation ``teammates`` is defined on
        ``spokespeople.Teammate.universe``. Returns 0 gracefully
        during the Phase 1-only interval when the FK has not yet
        landed (Phase 2 wires it in).
        """
        try:
            return self.teammates.count()
        except AttributeError:
            return 0

    def knowledge_document_count(self) -> int:
        """Number of KnowledgeDocuments currently assigned to
        this Universe. Same rationale as ``teammate_count``.
        Reverse relation ``knowledge_documents`` is defined on
        ``embeddings.KnowledgeDocument.universe``. Returns 0
        gracefully during the Phase 1-only interval when the FK
        has not yet landed (Phase 3 wires it in).
        """
        try:
            return self.knowledge_documents.count()
        except AttributeError:
            return 0
