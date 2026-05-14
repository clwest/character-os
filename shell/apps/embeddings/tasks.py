"""Celery tasks for the knowledge layer.

SESSION 138 / K3 — only one task in this slice:
``embed_document``. It picks up a ``KnowledgeDocument`` row
created by ``apps.embeddings.ingestion.ingest_*`` in status
``pending``, chunks the processed content, calls the
embedding service per chunk, persists ``KnowledgeChunk``
rows, then flips the document to ``processed``. On failure,
the document goes to ``failed`` with ``error_message``
populated so the operator can see what went wrong.

The task is idempotent: re-running against a document with
existing chunks deletes them first. Useful when re-embedding
after a model change (post-v1) or after a partial failure.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from . import models as kn
from .embedding_service import EMBEDDING_DIMENSION, EMBEDDING_MODEL, embed
from .text_splitter import DEFAULT_CHUNK_OVERLAP, DEFAULT_CHUNK_SIZE, TextSplitter

logger = logging.getLogger(__name__)


@shared_task(name="embeddings.embed_document", bind=True, max_retries=2)
def embed_document(
    self,
    document_id: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
) -> dict:
    """Embed every chunk of a KnowledgeDocument and persist them.

    Args:
        document_id: ``KnowledgeDocument.pk`` to process.
        chunk_size / chunk_overlap: passed to ``TextSplitter``.
            Defaults match the locked v1 shape (1000 / 200).

    Returns:
        ``{'document_id', 'chunks_created', 'total_cost_micros',
        'cached_hits', 'status'}`` — useful for telemetry and
        for the ``smoke_ingest`` management command.
    """
    started_at = timezone.now()
    try:
        doc = kn.KnowledgeDocument.objects.get(pk=document_id)
    except kn.KnowledgeDocument.DoesNotExist:
        logger.error("embed_document: doc=%s not found", document_id)
        return {
            "document_id": document_id,
            "chunks_created": 0,
            "total_cost_micros": 0,
            "cached_hits": 0,
            "status": "not_found",
        }

    # Move to processing — operators see the row already exists
    # and is being worked on. Failure paths flip this to failed.
    doc.status = kn.DocumentStatus.PROCESSING
    doc.error_message = ""
    doc.save(update_fields=["status", "error_message", "updated_at"])

    # Idempotency: re-running the task on a document with
    # existing chunks wipes them before re-embedding.
    deleted, _ = kn.KnowledgeChunk.objects.filter(document=doc).delete()
    if deleted:
        logger.info("embed_document: cleared %d stale chunks doc=%s", deleted, doc.pk)

    splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    text_chunks = splitter.split(doc.processed_content)

    if not text_chunks:
        doc.status = kn.DocumentStatus.FAILED
        doc.error_message = "TextSplitter produced no chunks"
        doc.save(update_fields=["status", "error_message", "updated_at"])
        return {
            "document_id": str(doc.pk),
            "chunks_created": 0,
            "total_cost_micros": 0,
            "cached_hits": 0,
            "status": "failed",
        }

    chunks_created = 0
    total_cost_micros = 0
    cached_hits = 0

    try:
        for piece in text_chunks:
            result = embed(piece.text)

            kn.KnowledgeChunk.objects.create(
                document=doc,
                chunk_index=piece.index,
                chunk_text=piece.text,
                chunk_size=piece.size,
                overlap_size=chunk_overlap if piece.index > 0 else 0,
                embedding_vector=result.vector,
                embedding_model=result.model,
                embedding_dimension=EMBEDDING_DIMENSION,
                embedding_cost_micros=result.cost_micros,
                processing_time_ms=result.elapsed_ms,
            )
            chunks_created += 1
            total_cost_micros += result.cost_micros
            if result.cached:
                cached_hits += 1
    except Exception as exc:
        # Any failure mid-batch — mark the document failed,
        # keep whichever chunks succeeded so the operator can
        # see partial progress in admin. Celery retries handle
        # transient failures (network blips); permanent ones
        # land in status=failed for operator visibility.
        logger.exception(
            "embed_document mid-batch failure doc=%s chunks_done=%d",
            doc.pk, chunks_created,
        )
        if self.request.retries < self.max_retries and _is_retryable(exc):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)

        doc.status = kn.DocumentStatus.FAILED
        doc.error_message = f"{type(exc).__name__}: {exc}"[:500]
        doc.save(update_fields=["status", "error_message", "updated_at"])
        return {
            "document_id": str(doc.pk),
            "chunks_created": chunks_created,
            "total_cost_micros": total_cost_micros,
            "cached_hits": cached_hits,
            "status": "failed",
        }

    doc.status = kn.DocumentStatus.PROCESSED
    doc.save(update_fields=["status", "updated_at"])

    elapsed = (timezone.now() - started_at).total_seconds()
    logger.info(
        "embed_document doc=%s chunks=%d cached=%d cost_micros=%d elapsed=%.2fs model=%s",
        doc.pk, chunks_created, cached_hits, total_cost_micros, elapsed, EMBEDDING_MODEL,
    )

    return {
        "document_id": str(doc.pk),
        "chunks_created": chunks_created,
        "total_cost_micros": total_cost_micros,
        "cached_hits": cached_hits,
        "status": "processed",
    }


def _is_retryable(exc: Exception) -> bool:
    """Decide whether to retry the task. Network-y errors
    (rate limit, connection error, timeout) — yes. Validation
    or ORM bugs — no, retrying won't help."""
    name = type(exc).__name__.lower()
    return any(token in name for token in (
        "timeout", "ratelimit", "rate_limit", "connection", "apiconnection",
    ))
