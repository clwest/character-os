"""Knowledge-layer models.

SESSION 138 / K2 — the data backbone of the knowledge arc.
Locked in ``docs/design/KNOWLEDGE_LAYER.md`` §"Data model".

Scope rules carried forward from the scope lock:

* Every ``KnowledgeDocument`` has a required ``workspace`` FK —
  it is the load-bearing anchor for the privacy contract
  (contract rule 1).
* ``content_hash`` is SHA-256 of the processed content;
  ``(workspace, content_hash)`` is unique so dedup is per-
  workspace and re-ingestion is idempotent (contract rule 5).
* ``spokespeople`` M2M is the visibility filter — empty M2M
  means "visible to all spokespeople in the workspace."
* Cross-workspace validation runs on ``clean()`` and on the
  M2M change signal; see ``signals.py`` for the latter.

``KnowledgeChunk`` holds the per-chunk embedding vector via
``pgvector.django.VectorField`` (1536 dims, matching
``text-embedding-3-small``). An HNSW index on the vector
column makes cosine-distance search O(log n)-ish.

The retrieval surface for these models lives in
``apps.embeddings.retrieval`` — that module is the only
sanctioned consumer of ``KnowledgeChunk.objects`` per
contract rule 2 (enforced by a repo-level grep test in K2's
test suite).
"""
from __future__ import annotations

import uuid

from django.core.exceptions import ValidationError
from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate


class DocumentType(models.TextChoices):
    TEXT = "text", "Plain Text"
    MARKDOWN = "markdown", "Markdown"
    PDF = "pdf", "PDF"
    URL = "url", "Web Page"


class IngestedVia(models.TextChoices):
    PASTE = "paste", "Paste"
    UPLOAD = "upload", "Upload"
    SERPER = "serper", "Serper Discovery"
    SEED = "seed", "Onboarding Seed"


class DocumentStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PROCESSING = "processing", "Processing"
    PROCESSED = "processed", "Processed"
    FAILED = "failed", "Failed"


class DeactivationReason(models.TextChoices):
    """SESSION 275 — reason a KD's ``is_active`` flipped False.

    Empty string is the active/default state. Populated only when
    ``is_active=False``. Distinguishes operator-initiated soft-delete
    from system-initiated orphan-archive so audit + safe-revival
    paths can act on the difference. Read-only via the API.
    """
    OPERATOR_DELETE = (
        "operator_delete",
        "Operator deleted",
    )
    ORPHANED_BY_TEAMMATE_DELETE = (
        "orphaned_by_teammate_delete",
        "Orphaned by teammate delete",
    )


class AudienceScope(models.TextChoices):
    """SESSION 276 Slice 5 / Delta Stage 1 — first-class audience marker.

    Replaces the negative-shape-derived audience semantics
    (empty-M2M-broadcast) documented in
    ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md``
    §31, §46-§71. The full four-state model is Slice 4 §50 and
    §51.

    Stage 1 posture: the field is nullable, unpopulated on every
    existing row, and NOT consulted by retrieval or any mutation
    path. Retrieval keeps the empty-M2M-broadcast semantics at
    ``apps/embeddings/retrieval.py:216-220`` unchanged. Later
    stages populate rows deterministically, extend mutation
    surfaces to set the field, and only then switch retrieval to
    key on the field positively.

    NULL is a MIGRATION-ONLY state — post-Delta the field will be
    NOT NULL. NULL does NOT mean WORKSPACE; it means "audience
    not yet classified under Delta."
    """
    CHARACTER = ("character", "Character-specific")
    UNIVERSE = ("universe", "Universe-shared")
    WORKSPACE = ("workspace", "Workspace-shared")
    NONE = ("none", "None — fail-closed")


# Embedding model is locked to text-embedding-3-small for v1
# (scope lock §"Out of scope" — multi-model is a re-embed-all
# event we defer). 1536 is the dimension that model emits.
EMBEDDING_MODEL_DEFAULT = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


class KnowledgeDocumentSpokesperson(models.Model):
    """Explicit through model for the ``KnowledgeDocument`` ↔
    ``Teammate`` M2M.

    SESSION 240 renamed the ``Spokesperson`` class to ``Teammate``
    but per CLAUDE.md §"Naming note" every persistence identifier
    (DB table, DB constraint, DB column) stays ``spokesperson_*``.
    Django's implicit M2M through recomputes the join-table
    column name from ``Teammate._meta.model_name`` at query time
    and emits SQL against ``teammate_id`` — a column that does
    not exist. Every knowledge/teammate M2M traversal 500s with
    ``UndefinedColumn``.

    Pinning ``db_column="spokesperson_id"`` on ``teammate`` here
    restores the ORM ↔ physical-schema contract without touching
    the table. Do not remove this class; do not rename either
    ``db_column``. The column contract is asserted by
    ``tests/test_m2m_through_column_contract.py``.
    """

    knowledgedocument = models.ForeignKey(
        "embeddings.KnowledgeDocument",
        on_delete=models.CASCADE,
        db_column="knowledgedocument_id",
    )
    teammate = models.ForeignKey(
        "spokespeople.Teammate",
        on_delete=models.CASCADE,
        db_column="spokesperson_id",
    )

    class Meta:
        db_table = "embeddings_knowledgedocument_spokespeople"
        constraints = [
            models.UniqueConstraint(
                fields=["knowledgedocument", "teammate"],
                name="embeddings_knowledgedocu_knowledgedocument_id_spo_e80c5133_uniq",
            ),
        ]


class KnowledgeDocument(models.Model):
    """A piece of workspace-scoped knowledge a spokesperson can
    draw on at render time or in conversation. One physical
    artifact (an uploaded PDF, a pasted markdown block, a
    fetched URL snapshot) maps to one ``KnowledgeDocument``;
    the document's text is split into many ``KnowledgeChunk``
    rows, each carrying its own embedding vector.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)

    # The load-bearing anchor — required, never null. See
    # `docs/design/KNOWLEDGE_LAYER.md` §"Contract rules" 1 + 3.
    workspace = models.ForeignKey(
        Workspace,
        on_delete=models.CASCADE,
        related_name="knowledge_documents",
    )

    # SESSION 261 — Universe substrate (opt-in, prospective). NULL
    # means "legacy workspace-wide doc; visible only to legacy
    # (universe=NULL) teammates via the empty-M2M fallback." Non-
    # NULL scopes the doc to a specific Universe within its
    # Workspace. ``on_delete=RESTRICT`` structurally prevents the
    # knowledge-bleed hazard where hard-delete of a populated
    # Universe would silently demote an empty-M2M canon doc to
    # universe=NULL and expose it to unrelated legacy characters
    # (correction 75d17f5). See UNIVERSE_SCHEMA_V1.md §"Deletion
    # policy" for the load-bearing rationale.
    universe = models.ForeignKey(
        "universe.Universe",
        on_delete=models.RESTRICT,
        null=True,
        blank=True,
        related_name="knowledge_documents",
        help_text=(
            "World this doc scopes to. NULL = legacy workspace-wide "
            "(visible only to legacy universe=NULL teammates)."
        ),
    )

    # Visibility filter — empty M2M = visible to all
    # spokespeople in the workspace. Cross-workspace attaches
    # are blocked by `clean()` + the m2m_changed signal in
    # `signals.py`. `through=KnowledgeDocumentSpokesperson` is
    # load-bearing: see that class's docstring.
    spokespeople = models.ManyToManyField(
        Teammate,
        related_name="knowledge_documents",
        blank=True,
        through="embeddings.KnowledgeDocumentSpokesperson",
    )

    # Identity
    title = models.CharField(max_length=500)
    document_type = models.CharField(
        max_length=20,
        choices=DocumentType.choices,
    )

    # Content
    raw_content = models.TextField(
        blank=True,
        help_text="Original content as ingested (before normalisation).",
    )
    processed_content = models.TextField(
        help_text=(
            "Normalised text that gets chunked + embedded. "
            "``content_hash`` is the SHA-256 of this field."
        ),
    )
    content_hash = models.CharField(
        max_length=64,
        db_index=True,
        help_text="SHA-256 of ``processed_content`` — drives dedup.",
    )

    # Ingestion provenance
    source_url = models.URLField(
        blank=True,
        max_length=2000,
        help_text="Populated when ``document_type='url'``.",
    )
    source_metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text=(
            "Free-form: serper search query, PDF page count, "
            "trafilatura extraction stats, etc."
        ),
    )
    ingested_via = models.CharField(
        max_length=20,
        choices=IngestedVia.choices,
    )

    # Lifecycle
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.PENDING,
    )
    error_message = models.TextField(
        blank=True,
        help_text="Populated when ``status='failed'``.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text=(
            "Soft delete. ``retrieve_for_teammate`` filters "
            "``is_active=True``; admins can audit deleted docs."
        ),
    )

    # SESSION 275 — audit-invariant support. Populated only when
    # ``is_active=False``. Empty string on active rows (and on legacy
    # pre-SESSION 275 soft-deletes, which the migration backfills to
    # blank). Distinguishes operator-initiated soft delete
    # (``OPERATOR_DELETE``, set by ``KnowledgeDocumentViewSet.destroy``)
    # from system-initiated orphan-archive (``ORPHANED_BY_TEAMMATE_DELETE``,
    # set by the ``pre_delete`` signal on ``Teammate`` when this KD's
    # sole remaining spokesperson is being deleted). The safe-revival
    # branch in ``ingestion._persist`` uses this field to reject
    # revivals that would silently broaden an orphaned KD's audience.
    # See ``docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md``.
    deactivated_reason = models.CharField(
        max_length=40,
        blank=True,
        default="",
        choices=DeactivationReason.choices,
        help_text=(
            "Populated when ``is_active=False``. Blank when active. "
            "Distinguishes operator soft-delete from system orphan-archive."
        ),
    )

    # SESSION 276 Slice 5 / Delta Stage 1 — first-class audience
    # marker. NULL on every existing row after this migration;
    # retrieval + mutation paths do NOT yet consult this field.
    # Empty-M2M-broadcast semantics at
    # ``apps/embeddings/retrieval.py:216-220`` remain authoritative
    # during Stage 1. Later stages populate rows deterministically
    # and switch retrieval to key on this field positively.
    # See ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md``
    # §46-§71 for the full Delta design and staged rollout plan.
    audience_scope = models.CharField(
        max_length=20,
        choices=AudienceScope.choices,
        null=True,
        blank=True,
        default=None,
        help_text=(
            "Delta Stage 1 first-class audience marker. NULL is a "
            "MIGRATION-ONLY state during Delta rollout; NULL does NOT "
            "mean WORKSPACE. Retrieval currently does not consult this "
            "field. See SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md."
        ),
    )

    # Audit
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_knowledge_documents",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["workspace", "content_hash"],
                name="knowledge_unique_workspace_content",
            ),
        ]
        indexes = [
            models.Index(fields=["workspace", "is_active"]),
            models.Index(fields=["workspace", "document_type"]),
        ]
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.title} ({self.workspace.name})"

    def clean(self) -> None:
        """Reject cross-workspace spokesperson attachments at
        save time. The m2m_changed signal in
        ``apps.embeddings.signals`` handles the post-save
        attachment path; this catches model-form validation in
        the Django admin and any direct ``full_clean()`` call.

        SESSION 261 — extends with two Universe invariants:

        1. Universe-workspace consistency (the outer wall must
           agree with the inner wall: ``universe.workspace_id
           == workspace_id``).
        2. Universe-M2M consistency (every attached spokesperson
           must belong to the same Universe as this doc — enforced
           post-save; the m2m_changed signal in ``signals.py``
           catches the ``doc.spokespeople.add(sp)`` path).
        """
        super().clean()
        if self.pk and self.workspace_id:
            bad = self.spokespeople.exclude(workspace_id=self.workspace_id)
            if bad.exists():
                names = ", ".join(sp.name for sp in bad[:3])
                raise ValidationError(
                    f"Spokespeople must belong to this document's "
                    f"workspace. Bad: {names}"
                )

        # SESSION 261 — Universe consistency invariant (#2 in
        # UNIVERSE_SCHEMA_V1.md §"Invariants").
        if self.universe_id is not None and self.workspace_id is not None:
            if self.universe.workspace_id != self.workspace_id:
                raise ValidationError({
                    "universe": (
                        f"Universe belongs to workspace "
                        f"{self.universe.workspace_id}, but this document "
                        f"is in workspace {self.workspace_id}."
                    ),
                })

        # SESSION 261 — Universe-M2M consistency invariant (#4
        # in UNIVERSE_SCHEMA_V1.md). Only meaningful post-save
        # (M2M rows require both sides to exist).
        if self.pk and self.universe_id is not None:
            bad = self.spokespeople.exclude(universe_id=self.universe_id)
            if bad.exists():
                names = ", ".join(sp.name for sp in bad[:3])
                raise ValidationError({
                    "spokespeople": (
                        f"Spokespeople must belong to this document's "
                        f"Universe. Bad: {names}"
                    ),
                })


class KnowledgeChunk(models.Model):
    """One embedded chunk of a ``KnowledgeDocument``.

    A document of N characters becomes ``ceil(N / chunk_size)``
    chunks (give or take overlap). The embedding vector is what
    cosine-distance retrieval ranks against.

    *No code outside ``apps.embeddings.retrieval`` should
    import this model* — that's contract rule 2 and is
    enforced by the repo-level grep test.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    document = models.ForeignKey(
        KnowledgeDocument,
        on_delete=models.CASCADE,
        related_name="chunks",
    )

    chunk_index = models.PositiveIntegerField()
    chunk_text = models.TextField()
    chunk_size = models.PositiveIntegerField(
        help_text="Length of ``chunk_text`` in characters.",
    )
    overlap_size = models.PositiveIntegerField(
        default=0,
        help_text="Overlap with the previous chunk, in characters.",
    )

    # pgvector vector column. 1536 dims for text-embedding-3-small.
    embedding_vector = VectorField(dimensions=EMBEDDING_DIMENSION)
    embedding_model = models.CharField(
        max_length=100,
        default=EMBEDDING_MODEL_DEFAULT,
    )
    embedding_dimension = models.PositiveIntegerField(
        default=EMBEDDING_DIMENSION,
    )

    # Cost tracking (per-chunk; admin can sum).
    embedding_cost_micros = models.PositiveIntegerField(
        default=0,
        help_text=(
            "Cost in micros (1 USD = 1_000_000 micros). "
            "Stored per-chunk so cleanup math is easy."
        ),
    )
    processing_time_ms = models.PositiveIntegerField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["document", "chunk_index"],
                name="knowledge_chunk_unique_index",
            ),
        ]
        indexes = [
            models.Index(fields=["document", "chunk_index"]),
            # HNSW index — m=16 / ef_construction=64 are the sibling project's
            # tuned defaults (`content/models.py:DocumentEmbedding`).
            HnswIndex(
                name="knowchunk_vec_hnsw_idx",
                fields=["embedding_vector"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]
        ordering = ["document", "chunk_index"]

    def __str__(self) -> str:
        return f"{self.document.title} #{self.chunk_index}"
