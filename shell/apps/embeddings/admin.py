"""Admin surfaces for the knowledge layer.

Read-mostly. The ``KnowledgeChunk`` admin is intentionally
minimal — the vector column is huge and not meaningful to
humans; ``chunk_text`` previews are the useful view.

Note: ``KnowledgeChunk`` is imported here legitimately (the
test in ``apps.embeddings.tests.test_retrieval_privacy``
allows ``apps/embeddings/admin.py`` because admin is the
read-only audit surface). Anything that *queries* the
chunk table for retrieval-shape purposes still must go
through ``apps.embeddings.retrieval``.
"""
from __future__ import annotations

from django.contrib import admin

from .models import KnowledgeChunk, KnowledgeDocument


@admin.register(KnowledgeDocument)
class KnowledgeDocumentAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "workspace",
        "document_type",
        "ingested_via",
        "status",
        "is_active",
        "created_at",
    )
    list_filter = ("status", "document_type", "ingested_via", "is_active")
    search_fields = ("title", "content_hash", "workspace__name")
    readonly_fields = ("id", "content_hash", "created_at", "updated_at")
    filter_horizontal = ("spokespeople",)
    raw_id_fields = ("workspace", "created_by")


@admin.register(KnowledgeChunk)
class KnowledgeChunkAdmin(admin.ModelAdmin):
    list_display = ("document", "chunk_index", "chunk_size", "embedding_model", "created_at")
    list_filter = ("embedding_model",)
    search_fields = ("document__title",)
    readonly_fields = (
        "id",
        "embedding_vector",
        "embedding_dimension",
        "embedding_model",
        "embedding_cost_micros",
        "processing_time_ms",
        "created_at",
    )
    raw_id_fields = ("document",)
