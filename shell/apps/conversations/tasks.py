"""Celery tasks for the conversation pipeline.

SESSION 145 / K8 completion — `embed_message` mirrors the K3
`embed_document` task shape: pick up a ``ConversationMessage``
by id, split it, embed each chunk, persist
``ConversationEmbedding`` rows.

Conversation messages are typically much shorter than
uploaded docs — Q-k-1 from the knowledge-layer scope lock
locked the chunk size at **500 chars / 0 overlap**. Most
turns fit in one chunk; longer turns split into a handful.

The pipeline fires for both roles (USER + SPOKESPERSON) so
``retrieve_for_thread`` can surface either side's history in
later turns — the LLM rebuilds context across both.

Idempotency mirrors `embed_document` — re-running deletes
prior embeddings for the message before re-embedding. Useful
when a content edit lands (post-v1) or after a partial
failure retries.
"""
from __future__ import annotations

import logging

from celery import shared_task
from django.utils import timezone

from apps.embeddings.embedding_service import EMBEDDING_DIMENSION, embed
from apps.embeddings.text_splitter import TextSplitter

from .models import ConversationEmbedding, ConversationMessage

logger = logging.getLogger(__name__)


# Conversation-specific chunk shape (Q-k-1). Shorter than
# K3's docs because chat turns are short; zero overlap
# because each turn is a complete thought boundary.
CONVERSATION_CHUNK_SIZE = 500
CONVERSATION_CHUNK_OVERLAP = 0


@shared_task(name="conversations.embed_message", bind=True, max_retries=2)
def embed_message(
    self,
    message_id: str,
    *,
    chunk_size: int = CONVERSATION_CHUNK_SIZE,
    chunk_overlap: int = CONVERSATION_CHUNK_OVERLAP,
) -> dict:
    """Embed every chunk of a ConversationMessage and persist.

    Args:
        message_id: ``ConversationMessage.pk`` to process.
        chunk_size / chunk_overlap: passed to ``TextSplitter``.
            Defaults match Q-k-1's conversation chunk shape
            (500 / 0).

    Returns:
        ``{'message_id', 'chunks_created', 'total_cost_micros',
        'cached_hits', 'status'}``.
    """
    started_at = timezone.now()
    try:
        msg = ConversationMessage.objects.get(pk=message_id)
    except ConversationMessage.DoesNotExist:
        logger.error("embed_message: msg=%s not found", message_id)
        return {
            "message_id": message_id,
            "chunks_created": 0,
            "total_cost_micros": 0,
            "cached_hits": 0,
            "status": "not_found",
        }

    # Idempotency: re-running the task wipes prior chunks.
    deleted, _ = ConversationEmbedding.objects.filter(message=msg).delete()
    if deleted:
        logger.info(
            "embed_message: cleared %d stale chunks msg=%s", deleted, msg.pk,
        )

    text = (msg.content or "").strip()
    if not text:
        logger.info("embed_message: skip empty content msg=%s", msg.pk)
        return {
            "message_id": str(msg.pk),
            "chunks_created": 0,
            "total_cost_micros": 0,
            "cached_hits": 0,
            "status": "skipped_empty",
        }

    splitter = TextSplitter(chunk_size=chunk_size, chunk_overlap=chunk_overlap)
    text_chunks = splitter.split(text)
    if not text_chunks:
        logger.warning(
            "embed_message: splitter produced no chunks msg=%s len=%d",
            msg.pk, len(text),
        )
        return {
            "message_id": str(msg.pk),
            "chunks_created": 0,
            "total_cost_micros": 0,
            "cached_hits": 0,
            "status": "skipped_empty",
        }

    chunks_created = 0
    total_cost_micros = 0
    cached_hits = 0

    try:
        for piece in text_chunks:
            result = embed(piece.text)
            ConversationEmbedding.objects.create(
                message=msg,
                chunk_index=piece.index,
                chunk_text=piece.text,
                chunk_size=piece.size,
                embedding_vector=result.vector,
                embedding_model=result.model,
            )
            chunks_created += 1
            total_cost_micros += result.cost_micros
            if result.cached:
                cached_hits += 1
    except Exception as exc:
        logger.exception(
            "embed_message mid-batch failure msg=%s chunks_done=%d",
            msg.pk, chunks_created,
        )
        if self.request.retries < self.max_retries and _is_retryable(exc):
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        return {
            "message_id": str(msg.pk),
            "chunks_created": chunks_created,
            "total_cost_micros": total_cost_micros,
            "cached_hits": cached_hits,
            "status": "failed",
            "error": f"{type(exc).__name__}: {exc}"[:500],
        }

    elapsed = (timezone.now() - started_at).total_seconds()
    logger.info(
        "embed_message msg=%s chunks=%d cached=%d cost=%d elapsed=%.2fs dim=%d",
        msg.pk, chunks_created, cached_hits,
        total_cost_micros, elapsed, EMBEDDING_DIMENSION,
    )
    return {
        "message_id": str(msg.pk),
        "chunks_created": chunks_created,
        "total_cost_micros": total_cost_micros,
        "cached_hits": cached_hits,
        "status": "processed",
    }


def _is_retryable(exc: Exception) -> bool:
    """Mirror of `embed_document._is_retryable` — only retry
    on network-y errors, not validation/ORM bugs."""
    name = type(exc).__name__.lower()
    return any(token in name for token in (
        "timeout", "ratelimit", "rate_limit", "connection", "apiconnection",
    ))
