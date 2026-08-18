"""NarrativeMemory — durable story facts promoted by the operator
from an accepted Composition.

SESSION 264 / ``docs/design/EPISODIC_CONTINUITY_CANON_PROMOTION_AUDIT_SESSION_264.md``.

Slice 1: operator-visible promote UX + read/archive/unarchive
surface. Slice 2: embedding + Universe-scoped retrieval lane
consumed by dialogue synthesis.

Load-bearing rules (see audit §8, §9, §13):

1. **Synthesis never writes here.** Every row is created by an
   explicit operator promotion of turns/text from a specific
   accepted ``Composition``. There is no auto-promotion path.
2. **Never mutates KnowledgeDocument.** Narrative memory is a
   separate tier from static Universe canon; the two must not
   flow into one another. Slice 2 wires a *separate* retrieval
   lane — memory chunks never enter ``retrieve_universe_canon``,
   never enter ``retrieve_for_teammate``, never become
   ``KnowledgeChunk`` rows.
3. **Universe-scoped.** Every row denormalizes ``workspace`` and
   ``universe`` (for tenant/scope filtering) but the authoritative
   parent is the ``Episode``. ``source_composition`` records the
   attempt the operator promoted from.
4. **Operator authority is explicit.** Corrections happen via
   supersede chains (mirror ``bootstrap_review`` journal shape);
   deletion is soft (``archived_at``). No hard-delete affordance
   is exposed in Slice 1 or 2.
5. **Embedding is operator-triggered.** ``embedding_vector`` is
   populated inline by ``apps.memory.views.promote_from_composition``
   using the same ``apps.embeddings.embedding_service.embed``
   function that ``KnowledgeChunk`` uses. Archived / superseded
   rows retain their vectors for audit but are excluded from
   retrieval by the ``retrieve_universe_memory`` predicate.
"""
from __future__ import annotations

import uuid

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    EMBEDDING_DIMENSION,
    EMBEDDING_MODEL_DEFAULT,
)


class NarrativeMemoryKind(models.TextChoices):
    """Coarse tag for how the memory row should be treated.

    Purely a hint for future retrieval scoring and operator
    filtering; the row is retrieved by cosine distance in Slice 2
    regardless of ``kind``. Vocabulary matches audit §13.1.
    """

    EVENT = "event", "Event"                       # something happened in-world
    ACTION = "action", "Action"                    # a character did a specific thing
    PROMISE = "promise", "Promise"                 # a character/world committed to a future outcome
    DIALOGUE_CALLBACK = "dialogue_callback", "Dialogue Callback"  # notable line, not necessarily an event
    WORLD_DETAIL = "world_detail", "World Detail"  # a discovered/revealed world fact


class NarrativeMemoryWeight(models.TextChoices):
    """Optional hint for retrieval scoring (Slice 2 will use this)."""

    CENTRAL = "central", "Central"
    PERIPHERAL = "peripheral", "Peripheral"


class NarrativeMemoryStatus(models.TextChoices):
    """Lifecycle state of a memory row.

    * ``REMEMBERED`` — the current, retrievable state.
    * ``SUPERSEDED`` — replaced by a newer row (``supersedes`` FK
      on the new row points here). Retrieval must skip.
    * ``ARCHIVED`` — soft-deleted by the operator. Retrieval must
      skip. ``archived_at`` also carries the timestamp.

    ``REMEMBERED`` is the default on create; state changes go
    through service methods (``supersede()``, ``archive()``,
    ``unarchive()``) rather than direct field writes.
    """

    REMEMBERED = "remembered", "Remembered"
    SUPERSEDED = "superseded", "Superseded"
    ARCHIVED = "archived", "Archived"


class NarrativeMemory(models.Model):
    """A durable narrative fact promoted from an accepted Composition.

    Represents "this happened / was said in the story of this
    Universe" — subordinate to static Universe canon, retrieved
    through its own lane in Slice 2. Never automatically created;
    only via explicit operator promotion (see audit §9).

    Field notes:

    * ``episode``: authoritative narrative parent. RESTRICT on
      delete — attached memories block Episode hard-delete just as
      Compositions do. Operators must archive memories first (or
      archive the Episode, which soft-deletes without cascading).
    * ``source_composition``: the specific render attempt the
      operator promoted from. RESTRICT for the same reason. Also
      participates in Django's shared-CASCADE-parent rule so
      Workspace cascade still works.
    * ``workspace`` / ``universe``: denormalized from Episode for
      Slice 2 retrieval filters (workspace tenant wall + Universe
      scope). ``clean()`` enforces consistency with
      ``episode.universe.workspace_id`` and ``episode.universe_id``.
    * ``witnessed_by``: subset of the Episode's cast. Empty M2M is
      the "whole cast" convention (matches
      ``KnowledgeDocument.spokespeople`` empty-M2M semantics).
      Cross-Universe teammates are rejected by the pre_add signal.
    * ``body``: the compact memory text. Populated by the operator
      at promotion time; may be a verbatim quote from
      ``source_composition.synthesized_brief`` or a paraphrase.
      Frozen after create (Slice 1 does not expose edit UI).
    * ``supersedes``: self-FK to the memory this one replaces.
      Retcon chain is derived by walking backwards; retrieval
      only surfaces the terminal (non-superseded) row per chain.
    * ``archived_at``: soft-delete marker; matches Universe /
      Episode conventions.
    """

    id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False,
    )

    # Narrative parent. RESTRICT — attached memories block Episode
    # hard-delete, matching Composition.episode = RESTRICT.
    episode = models.ForeignKey(
        "universe.Episode",
        on_delete=models.RESTRICT,
        related_name="narrative_memories",
        help_text=(
            "Story this memory belongs to. Attached memories block "
            "Episode hard-delete; archive first to release."
        ),
    )

    # Provenance — the exact Composition the operator promoted from.
    # RESTRICT so a Composition with attached memories can't be
    # deleted from under them without operator action.
    source_composition = models.ForeignKey(
        "compositions.Composition",
        on_delete=models.RESTRICT,
        related_name="promoted_memories",
        help_text=(
            "Render attempt the operator promoted this memory from. "
            "Immutable after create."
        ),
    )

    # Denormalized tenant / scope FKs — populated from Episode at
    # create time by the serializer/service, verified in clean().
    # CASCADE on Workspace and Universe because both are ancestors
    # of Episode too (Django's shared-CASCADE-parent rule keeps
    # deletion consistent).
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="narrative_memories",
        help_text="Tenant anchor. Must match episode.universe.workspace.",
    )
    universe = models.ForeignKey(
        "universe.Universe",
        on_delete=models.CASCADE,
        related_name="narrative_memories",
        help_text="Universe anchor. Must match episode.universe.",
    )

    kind = models.CharField(
        max_length=32,
        choices=NarrativeMemoryKind.choices,
        default=NarrativeMemoryKind.EVENT,
        help_text="Coarse tag for filtering + future retrieval scoring.",
    )

    body = models.TextField(
        help_text=(
            "Compact memory text. May be a verbatim quote from "
            "source_composition.synthesized_brief or an operator "
            "paraphrase. Not edited after create in Slice 1."
        ),
    )

    witnessed_by = models.ManyToManyField(
        "spokespeople.Teammate",
        related_name="witnessed_narrative_memories",
        blank=True,
        help_text=(
            "Subset of the Episode's cast who witnessed this fact. "
            "Empty M2M = whole cast (matches empty-M2M-is-broadcast "
            "convention on KnowledgeDocument.spokespeople)."
        ),
    )

    weight = models.CharField(
        max_length=16,
        choices=NarrativeMemoryWeight.choices,
        default=NarrativeMemoryWeight.PERIPHERAL,
        help_text="Retrieval scoring hint (unused in Slice 1).",
    )

    status = models.CharField(
        max_length=16,
        choices=NarrativeMemoryStatus.choices,
        default=NarrativeMemoryStatus.REMEMBERED,
        help_text=(
            "Lifecycle state. Non-REMEMBERED rows are excluded from "
            "retrieval in Slice 2."
        ),
    )

    # Retcon chain — self-FK to the memory this one replaces. The
    # replaced row's status flips to SUPERSEDED via the archive
    # service; retrieval only surfaces the terminal row per chain.
    supersedes = models.ForeignKey(
        "self",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="superseded_by",
        help_text=(
            "Prior memory this row replaces. Chains form a linked "
            "list of amendments; retrieval only surfaces the "
            "terminal row per chain."
        ),
    )
    superseded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "When this row was superseded by another. Set when the "
            "*replacing* row is created."
        ),
    )
    superseded_reason = models.TextField(
        blank=True,
        default="",
        help_text=(
            "Operator-supplied reason accompanying a supersede. Not "
            "required in Slice 1."
        ),
    )

    archived_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "Soft-delete marker. NULL = active. Non-NULL = archived. "
            "Reversible via unarchive."
        ),
    )

    # Audit / provenance. SET_NULL because we want the row to
    # survive a user's account deletion — the memory is a Universe
    # fact, not a personal artifact.
    promoted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promoted_narrative_memories",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # ---- Slice 2 — embedding ----
    #
    # Reuses ``apps.embeddings.embedding_service.embed`` (same
    # provider ``text-embedding-3-small`` @ 1536 dims that
    # ``KnowledgeChunk`` uses) so retrieval treats memory bodies
    # and canon chunks under the same cosine geometry. Populated
    # inline by ``apps.memory.views.promote_from_composition``
    # right after ``NarrativeMemory.save()`` — the operator loop
    # is short (a couple sentences), sync avoids adding a Celery
    # sweep for a substrate that doesn't have one on the canon
    # side either.
    #
    # ``null=True`` for two reasons:
    #   * Row f25e53af from the SESSION 264 Slice 1 dogfood was
    #     created before this field existed; the migration adds
    #     the column NULL so existing rows survive without an
    #     immediate backfill.
    #   * Embedding failures must not roll back the ``Remember
    #     this`` promotion — the operator's intent lands
    #     regardless. The row is simply excluded from retrieval
    #     until re-embedded (a management command / operator
    #     retry, not modeled in Slice 2).
    embedding_vector = VectorField(
        dimensions=EMBEDDING_DIMENSION,
        null=True,
        blank=True,
    )
    embedding_model = models.CharField(
        max_length=100,
        blank=True,
        default="",
        help_text="Provider model that produced ``embedding_vector``.",
    )
    embedding_dimension = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Dimension of the persisted vector (0 = never embedded)."
        ),
    )
    embedding_cost_micros = models.PositiveIntegerField(
        default=0,
        help_text="Cost in micros (1 USD = 1_000_000 micros).",
    )
    embedded_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text=(
            "When ``embedding_vector`` was last populated. NULL = "
            "never embedded (excluded from retrieval)."
        ),
    )

    class Meta:
        db_table = "memory_narrative_memory"
        ordering = ["-created_at"]
        indexes = [
            models.Index(
                fields=["universe", "status"],
                name="narrmem_universe_status_idx",
            ),
            models.Index(
                fields=["episode", "status"],
                name="narrmem_episode_status_idx",
            ),
            models.Index(
                fields=["source_composition"],
                name="narrmem_source_comp_idx",
            ),
            models.Index(
                fields=["workspace", "-created_at"],
                name="narrmem_workspace_ctime_idx",
            ),
            # pgvector HNSW index mirroring KnowledgeChunk's
            # ``knowchunk_vec_hnsw_idx`` (m=16 / ef_construction=64,
            # cosine ops). Ensures retrieval scales past the first
            # few operator-promoted rows without a re-index event.
            HnswIndex(
                name="narrmem_vec_hnsw_idx",
                fields=["embedding_vector"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]

    def __str__(self) -> str:  # pragma: no cover — admin cosmetics
        return f"{self.kind}: {self.body[:60]}"

    # ---- Invariants ----

    def clean(self) -> None:
        """Enforce Universe / Workspace consistency between
        ``episode``, ``source_composition``, ``workspace``, and
        ``universe``.

        Load-bearing:
          * ``workspace`` matches ``episode.universe.workspace``.
          * ``universe`` matches ``episode.universe``.
          * ``source_composition.workspace`` matches ``workspace``.
          * If ``source_composition`` is Episode-attached, its
            ``source_composition.episode`` matches ``episode``.
          * ``supersedes``, when set, points to a row in the same
            Episode (retcon chains never cross Episodes).

        ``witnessed_by`` M2M consistency is enforced by
        ``pre_add`` signals on the through table because
        ``clean()`` can't inspect an unsaved M2M cleanly.
        """
        super().clean()

        errors: dict[str, str] = {}

        if self.episode_id and self.universe_id:
            episode_uni = self.episode.universe_id
            if episode_uni != self.universe_id:
                errors["universe"] = (
                    f"NarrativeMemory.universe ({self.universe_id}) "
                    f"must match episode.universe ({episode_uni})."
                )

        if self.episode_id and self.workspace_id:
            episode_ws = self.episode.universe.workspace_id
            if episode_ws != self.workspace_id:
                errors["workspace"] = (
                    f"NarrativeMemory.workspace ({self.workspace_id}) "
                    f"must match episode.universe.workspace ({episode_ws})."
                )

        if self.source_composition_id and self.workspace_id:
            comp_ws = self.source_composition.workspace_id
            if comp_ws != self.workspace_id:
                errors["source_composition"] = (
                    f"source_composition.workspace ({comp_ws}) does not "
                    f"match memory.workspace ({self.workspace_id})."
                )

        if self.source_composition_id and self.episode_id:
            comp_ep = self.source_composition.episode_id
            if comp_ep is not None and comp_ep != self.episode_id:
                errors["source_composition"] = (
                    f"source_composition.episode ({comp_ep}) does not "
                    f"match this memory's episode ({self.episode_id})."
                )

        if self.supersedes_id and self.episode_id:
            prior_episode = self.supersedes.episode_id
            if prior_episode != self.episode_id:
                errors["supersedes"] = (
                    "Cannot supersede a memory from a different Episode "
                    "(retcon chains are Episode-scoped)."
                )

        if not (self.body or "").strip():
            errors["body"] = "NarrativeMemory.body cannot be blank."

        if errors:
            raise ValidationError(errors)
