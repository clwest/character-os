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

    def episode_count(self) -> int:
        """Number of Episodes currently anchored in this Universe.

        Used by the hard-delete preflight so populated Universes
        report Episode count alongside Teammate + KnowledgeDocument
        counts. Reverse relation ``episodes`` is defined on
        ``Episode.universe`` (EPISODE_SCHEMA_V1). Returns 0
        gracefully before the FK lands.
        """
        try:
            return self.episodes.count()
        except AttributeError:
            return 0


# ============================================================
# EPISODE_SCHEMA_V1 (SESSION 262)
# ============================================================
#
# Universe-scoped narrative primitive. Contract:
# ``docs/design/EPISODE_SCHEMA_V1.md``. Nine fields; no
# denormalized workspace FK (universe.workspace is derivable
# and Universe already exists — see design Q2).
#
# Load-bearing invariants (also enforced at signal + view layer):
#
# 1. ``universe`` is required; Episode is a story inside a world.
# 2. ``operator_topic`` is the story-authoritative creative intent.
#    Distinct from the SESSION 262 per-attempt copy on
#    ``Composition.operator_topic``. Editing this NEVER propagates
#    to attached Compositions (their observability fields are
#    immutable-once-populated per SESSION 262).
# 3. Cast is operator-authoritative; NEVER auto-populated from
#    Composition speakers.
# 4. Cast M2M rows enforce ``teammate.universe_id ==
#    episode.universe_id`` (Universe consistency).
# 5. ``on_delete=RESTRICT`` on ``universe`` mirrors
#    ``Teammate.universe`` and ``KnowledgeDocument.universe``:
#    populated Universes cannot silently orphan their Episodes.
# 6. Hard-delete is gated by attached Compositions
#    (``Composition.episode = PROTECT``). Cast membership alone
#    does NOT block hard-delete (EpisodeCast M2M cascades).


class Episode(models.Model):
    """A Universe-scoped narrative event conceived and named by the
    operator as a story.

    Owns the story's verbatim ``operator_topic``, its title, and
    its cast (a subset of the Universe's Teammates; may be empty
    until first Composition attaches). Referenced by zero or more
    Compositions, each of which is one render attempt or variant
    of the story. Episode's existence is itself the operator saying
    "this is a story." No Episode is ever auto-created around a
    Composition.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # Universe parent. NOT NULL — Episode is Universe-scoped by
    # construction.
    #
    # ``on_delete=CASCADE`` (deviation from EPISODE_SCHEMA_V1 §Q7
    # design draft's RESTRICT). Rationale:
    #
    # Episode has no denormalized workspace FK (Q2 decision).
    # RESTRICT would fire during Workspace cascade-delete because
    # Django's shared-CASCADE-parent rule requires the protecting
    # child to share a cascading ancestor with the RESTRICTed
    # parent. Teammate + KnowledgeDocument both have a workspace
    # FK (predating Universe) so they satisfy the rule; Episode
    # doesn't, so RESTRICT would block workspace deletion entirely.
    #
    # DB-layer safety is preserved by ``Composition.episode =
    # PROTECT`` — populated Episodes still can't hard-delete under
    # direct model.delete() calls. The API-layer preflight on
    # ``UniverseViewSet.destroy`` blocks Universe hard-delete when
    # Episodes exist (400 with ``episode_count`` in ``blocking``).
    # Together this preserves the "populated Universe cannot silently
    # wipe stories" guarantee via operator-facing surfaces + PROTECT
    # backstop on the child linkage.
    universe = models.ForeignKey(
        Universe,
        on_delete=models.CASCADE,
        related_name="episodes",
        help_text=(
            "World this Episode belongs to. Episode.universe is "
            "immutable after create; migrations between Universes "
            "are the crossover primitive (deferred)."
        ),
    )

    # Operator-facing label. Distinct from `operator_topic` prose;
    # `title` is the short identity handle. Per-Universe uniqueness
    # enforced via the meta constraint.
    title = models.CharField(
        max_length=120,
        help_text=(
            "Operator-facing label (e.g. 'AI took over the lab'). "
            "Not globally unique; unique within the parent Universe."
        ),
    )

    # Story-authoritative creative intent. NOT the per-attempt
    # topic — SESSION 262 Composition.operator_topic carries the
    # per-render copy. Editing this field NEVER propagates to
    # attached Compositions.
    operator_topic = models.TextField(
        help_text=(
            "Story-authoritative operator premise. Verbatim. New "
            "Compositions attached to this Episode inherit a COPY "
            "into Composition.operator_topic at create time; the "
            "copy is Composition-immutable per SESSION 262."
        ),
    )

    # Operator-declared cast. M2M through EpisodeCast for a stable
    # (episode, teammate) unique constraint + a natural attach
    # timestamp for future audit surfaces.
    cast = models.ManyToManyField(
        "spokespeople.Teammate",
        through="universe.EpisodeCast",
        related_name="episodes",
        blank=True,
        help_text=(
            "Operator-declared characters participating in this "
            "story. Never auto-populated. Each Teammate must "
            "belong to the same Universe as this Episode."
        ),
    )

    # Soft-delete marker. Mirrors Universe.archived_at exactly.
    archived_at = models.DateTimeField(
        null=True, blank=True,
        help_text=(
            "Soft-delete marker. NULL = active. Non-NULL = archived. "
            "Reversible via unarchive."
        ),
    )

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_episodes",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "universe_episode"
        ordering = ["universe", "-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["universe", "title"],
                name="episode_unique_title_per_universe",
            ),
        ]
        indexes = [
            models.Index(
                fields=["universe", "archived_at"],
                name="episode_universe_archived_idx",
            ),
            models.Index(
                fields=["created_by", "created_at"],
                name="episode_created_by_at_idx",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.title} ({self.universe.name})"

    def clean(self) -> None:
        """Reject blank title / operator_topic. Universe
        immutability check for updates."""
        super().clean()
        if not (self.title or "").strip():
            raise ValidationError({"title": "Episode title cannot be blank."})
        if not (self.operator_topic or "").strip():
            raise ValidationError({
                "operator_topic": "Episode operator_topic cannot be blank.",
            })

    # ---- Introspection helpers used by the API + preflight ----

    def composition_count(self) -> int:
        """Number of Compositions currently attached to this Episode.
        Used by the hard-delete preflight to surface a 409 body."""
        try:
            return self.compositions.count()
        except AttributeError:
            return 0

    def cast_count(self) -> int:
        """Number of Teammates in this Episode's cast."""
        try:
            return self.cast.count()
        except AttributeError:
            return 0


class EpisodeCast(models.Model):
    """Through row for the Episode.cast M2M.

    Explicit through model (rather than the ORM's implicit
    auto-created table) so the ``m2m_changed pre_add`` signal has
    a stable ordering and so future audit surfaces (who added
    whom, when) have a natural attach timestamp without another
    migration. Mirrors ``KnowledgeDocumentSpokesperson`` in
    ``apps/embeddings/models.py``.

    Cascades from either side: deleting an Episode cascades away
    all its cast rows; deleting a Teammate cascades away all its
    Episode-cast rows. This is safe because cast is
    operator-authoritative and stateless — losing a cast row
    doesn't destroy render provenance (that lives on Compositions
    per SESSION 262).
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    episode = models.ForeignKey(
        Episode,
        on_delete=models.CASCADE,
        related_name="cast_rows",
    )
    teammate = models.ForeignKey(
        "spokespeople.Teammate",
        on_delete=models.CASCADE,
        related_name="episode_cast_rows",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "universe_episode_cast"
        constraints = [
            models.UniqueConstraint(
                fields=["episode", "teammate"],
                name="episode_cast_unique_pair",
            ),
        ]
        indexes = [
            models.Index(fields=["episode"], name="episode_cast_episode_idx"),
            models.Index(fields=["teammate"], name="episode_cast_tm_idx"),
        ]

    def __str__(self) -> str:
        return f"{self.episode_id} × {self.teammate_id}"

    def clean(self) -> None:
        """Enforce Universe consistency: cast Teammates must belong
        to the same Universe as the Episode. Legacy
        (teammate.universe=NULL) attachment is REJECTED per
        EPISODE_SCHEMA_V1 §Q6.
        """
        super().clean()
        if self.episode_id and self.teammate_id:
            episode_uni = self.episode.universe_id
            tm_uni = self.teammate.universe_id
            if tm_uni is None:
                raise ValidationError({
                    "teammate": (
                        f"Teammate {self.teammate.name!r} has no Universe "
                        f"(legacy). A Universe-scoped Episode cannot "
                        f"include a legacy Teammate in its cast. Assign "
                        f"the Teammate to Universe {self.episode.universe.name!r} first."
                    ),
                })
            if tm_uni != episode_uni:
                raise ValidationError({
                    "teammate": (
                        f"Teammate {self.teammate.name!r} belongs to "
                        f"Universe {tm_uni}, but this Episode is in "
                        f"Universe {episode_uni}. Cross-Universe cast "
                        f"attachment is forbidden."
                    ),
                })
            # Workspace consistency defense-in-depth.
            if self.teammate.workspace_id != self.episode.universe.workspace_id:
                raise ValidationError({
                    "teammate": (
                        f"Teammate {self.teammate.name!r} belongs to a "
                        f"different Workspace than Episode."
                    ),
                })
