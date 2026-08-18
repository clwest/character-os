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


# ============================================================
# SESSION 264 Slice 3 — Composition memory provenance resolver
# ============================================================
#
# ``CompositionSerializer.memories_used`` enriches the raw
# ``Composition.memory_ids`` JSONField (a flat list of
# ``NarrativeMemory.id`` strings written by SESSION 264 Slice 2
# at synthesis time) into a display-friendly list the SPA panel
# can render without a second network hop.
#
# Read-only. Never mutates any NarrativeMemory. Never touches
# KnowledgeDocument / KnowledgeChunk. Respects the audit's
# "Remembered != Canon" rule; this is provenance visibility,
# not promotion.
#
# Rows that have been ARCHIVED or SUPERSEDED SINCE the render
# still appear — they FED the render at the time, and hiding
# them would erase provenance. The serialized shape carries the
# current status so the SPA can render an "archived after this
# render" indicator.


def resolve_memory_ids_to_rows(
    memory_ids: list[str],
    *,
    workspace,
) -> list[dict]:
    """Resolve a flat list of ``NarrativeMemory.id`` strings into a
    display-shaped payload for the SPA composition detail page.

    Workspace-scoped defense-in-depth — the retrieval predicate
    already filters by workspace at synthesis time, but a
    cross-workspace ID smuggled into ``Composition.memory_ids``
    would be silently dropped here (never re-hydrated across the
    tenant boundary).

    Missing / archived-since-render / superseded-since-render
    rows all appear (with their current status surfaced) so the
    operator sees the honest historical provenance instead of a
    silent gap.

    Returns ``[]`` when ``memory_ids`` is empty or nothing
    resolves in-workspace.
    """
    if not memory_ids:
        return []

    ordered_ids = [str(mid) for mid in memory_ids if mid]
    if not ordered_ids:
        return []

    rows = {
        str(m.id): m
        for m in NarrativeMemory.objects
        .filter(id__in=ordered_ids, workspace=workspace)
        .select_related("episode", "universe")
        .prefetch_related("witnessed_by")
    }

    payload: list[dict] = []
    for mid in ordered_ids:
        m = rows.get(mid)
        if m is None:
            # Row deleted / never existed / cross-workspace
            # smuggle attempt — surface as a stub so the SPA
            # can render a "no longer available" indicator
            # without breaking layout.
            payload.append({
                "id": mid,
                "resolved": False,
            })
            continue

        witnesses = [
            {"id": str(w.id), "name": w.name}
            for w in m.witnessed_by.all()
        ]
        payload.append({
            "id": str(m.id),
            "resolved": True,
            "kind": m.kind,
            "body": m.body,
            "weight": m.weight,
            "status": m.status,
            "archived_at": (
                m.archived_at.isoformat() if m.archived_at else None
            ),
            "witnessed_by": witnesses,
            "episode_id": str(m.episode_id) if m.episode_id else None,
            "episode_title": m.episode.title if m.episode_id else None,
            "universe_id": str(m.universe_id) if m.universe_id else None,
            "universe_name": m.universe.name if m.universe_id else None,
            "source_composition_id": (
                str(m.source_composition_id) if m.source_composition_id else None
            ),
        })
    return payload
