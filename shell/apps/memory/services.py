"""Services for NarrativeMemory.

SESSION 264 Slice 2. Extracted here because embedding + retrieval
are separate concerns that both operate on ``NarrativeMemory``
outside the DRF view layer.

Load-bearing rules:

* **Embedding NEVER hits KnowledgeChunk / ConversationEmbedding.**
  Vectors land on ``NarrativeMemory.embedding_vector`` (this app's
  own column). Uses ``apps.embeddings.embedding_service.embed``,
  the same shared entry point ``KnowledgeChunk`` embedding uses,
  so cosine geometry matches across canon + memory retrieval.
* **Embedding failures do not roll back the promotion.** The row
  lands with ``embedding_vector=NULL``; retrieval simply excludes
  it until a re-embed lands. Operator intent (a manual "Remember
  this" click) is authoritative and must not be lost to a
  provider hiccup.
* **Idempotent.** If a row already has an embedding_vector,
  ``embed_memory`` is a no-op unless ``force=True``. Avoids paying
  for a re-embed on every promote-batch resubmit.
* **Mock-safe.** ``EMBEDDING_FORCE_MOCK=1`` env or
  ``settings.EMBEDDING_FORCE_MOCK=True`` routes through the
  deterministic hash-derived vector — same path canon-lane tests
  use.
"""
from __future__ import annotations

import logging
from typing import Iterable

from django.utils import timezone

from apps.embeddings.embedding_service import embed

from .models import NarrativeMemory

logger = logging.getLogger(__name__)


def embed_memory(memory: NarrativeMemory, *, force: bool = False) -> bool:
    """Populate ``memory.embedding_vector`` from ``memory.body``.

    Returns ``True`` if the row's embedding fields were written,
    ``False`` if the call was a no-op (already embedded and
    ``force=False``, or embedding failed and the row was left
    untouched).

    Never raises to the caller — embedding failures are logged
    and swallowed so a bad provider call cannot roll back the
    surrounding operator action (audit §9: operator authority is
    the primary signal).
    """
    if memory.embedding_vector is not None and not force:
        return False

    body = (memory.body or "").strip()
    if not body:
        # Serializer + model.clean() already reject blank bodies.
        # Defensive: don't spend money on a blank prompt.
        return False

    try:
        result = embed(body)
    except Exception as exc:  # pragma: no cover — defensive
        logger.warning(
            "narrative_memory embed_failed memory=%s reason=%s",
            memory.id, exc,
        )
        return False

    memory.embedding_vector = result.vector
    memory.embedding_model = result.model
    memory.embedding_dimension = result.dimension
    memory.embedding_cost_micros = result.cost_micros
    memory.embedded_at = timezone.now()
    memory.save(update_fields=[
        "embedding_vector",
        "embedding_model",
        "embedding_dimension",
        "embedding_cost_micros",
        "embedded_at",
        "updated_at",
    ])
    return True


def embed_memories(memories: Iterable[NarrativeMemory], *, force: bool = False) -> int:
    """Embed a batch. Returns the count that had their vectors
    written. Individual failures are logged and skipped."""
    count = 0
    for memory in memories:
        if embed_memory(memory, force=force):
            count += 1
    return count
