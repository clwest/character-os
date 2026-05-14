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
from apps.spokespeople.models import Spokesperson


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


# Embedding model is locked to text-embedding-3-small for v1
# (scope lock §"Out of scope" — multi-model is a re-embed-all
# event we defer). 1536 is the dimension that model emits.
EMBEDDING_MODEL_DEFAULT = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


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

    # Visibility filter — empty M2M = visible to all
    # spokespeople in the workspace. Cross-workspace attaches
    # are blocked by `clean()` + the m2m_changed signal in
    # `signals.py`.
    spokespeople = models.ManyToManyField(
        Spokesperson,
        related_name="knowledge_documents",
        blank=True,
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
            "Soft delete. ``retrieve_for_spokesperson`` filters "
            "``is_active=True``; admins can audit deleted docs."
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
            # HNSW index — m=16 / ef_construction=64 are u-d-b's
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
