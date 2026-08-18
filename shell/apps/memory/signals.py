"""Memory app signals.

SESSION 264 Slice 1 — the ``m2m_changed pre_add`` signal on
``NarrativeMemory.witnessed_by`` enforces:

  1. Every witness Teammate belongs to the same Universe as the
     memory.
  2. Every witness Teammate belongs to the same Workspace as the
     memory (defense-in-depth; Universe check should already
     imply this).
  3. Every witness Teammate is a cast member of the memory's
     Episode (memories can only be witnessed by characters who
     were in the story).

Mirrors ``apps/universe/signals.py`` shape.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from apps.spokespeople.models import Teammate

from .models import NarrativeMemory


@receiver(m2m_changed, sender=NarrativeMemory.witnessed_by.through)
def reject_invalid_witness(
    sender, instance, action, reverse, model, pk_set, **kwargs,
):
    """Reject witness additions that cross Universe / Workspace
    boundaries or that name a Teammate who is not a cast member
    of the memory's Episode.

    Fires on ``pre_add`` for both forward
    (``memory.witnessed_by.add(teammate)``) and reverse
    (``teammate.witnessed_narrative_memories.add(memory)``) paths.
    """
    if action != "pre_add":
        return
    if not pk_set:
        return

    if reverse:
        # instance is a Teammate; pk_set is a set of NarrativeMemory PKs.
        teammate: Teammate = instance
        memories = list(
            NarrativeMemory.objects
            .filter(pk__in=pk_set)
            .select_related("universe", "workspace", "episode")
        )
        for mem in memories:
            _validate_pair(memory=mem, teammate=teammate)
    else:
        # instance is a NarrativeMemory; pk_set is a set of Teammate PKs.
        memory: NarrativeMemory = instance
        teammates = list(Teammate.objects.filter(pk__in=pk_set))
        # Preload cast set once to keep the O(N) check cheap.
        cast_ids = set(memory.episode.cast.values_list("id", flat=True))
        for tm in teammates:
            _validate_pair(memory=memory, teammate=tm, cast_ids=cast_ids)


def _validate_pair(
    *,
    memory: NarrativeMemory,
    teammate: Teammate,
    cast_ids: set | None = None,
) -> None:
    """Raise ValidationError if this witness attach is invalid."""
    if teammate.universe_id is None:
        raise ValidationError(
            f"Teammate {teammate.name!r} has no Universe (legacy). "
            f"Universe-scoped narrative memory cannot include a "
            f"legacy Teammate as a witness."
        )
    if teammate.universe_id != memory.universe_id:
        raise ValidationError(
            f"Teammate {teammate.name!r} belongs to Universe "
            f"{teammate.universe_id}, but this memory is in Universe "
            f"{memory.universe_id}. Cross-Universe witness attach "
            f"is forbidden."
        )
    if teammate.workspace_id != memory.workspace_id:
        raise ValidationError(
            f"Teammate {teammate.name!r} belongs to a different "
            f"Workspace than this memory."
        )
    if cast_ids is None:
        cast_ids = set(memory.episode.cast.values_list("id", flat=True))
    if teammate.id not in cast_ids:
        raise ValidationError(
            f"Teammate {teammate.name!r} is not a cast member of "
            f"Episode {memory.episode_id}. Witnesses must be in "
            f"the Episode's cast."
        )
