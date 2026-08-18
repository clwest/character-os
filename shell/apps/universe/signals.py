"""Universe app signals.

SESSION 262 / EPISODE_SCHEMA_V1 — the ``m2m_changed pre_add``
signal on ``Episode.cast`` enforces the Universe-consistency
invariant on the raw ``episode.cast.add(teammate)`` path (the
model-level ``clean()`` on ``EpisodeCast`` only fires for form-
driven / explicit ``full_clean()`` calls).

Mirrors the ``reject_cross_workspace_spokesperson`` +
``reject_cross_universe_spokesperson`` receivers in
``apps/embeddings/signals.py``. Load-bearing pattern per
``UNIVERSE_SCHEMA_V1.md``: defense-in-depth via signal + clean +
constraint.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models.signals import m2m_changed
from django.dispatch import receiver

from apps.spokespeople.models import Teammate

from .models import Episode


@receiver(m2m_changed, sender=Episode.cast.through)
def reject_cross_universe_cast(
    sender, instance, action, reverse, model, pk_set, **kwargs,
):
    """Reject cast additions that cross Universe (or Workspace)
    boundaries, and reject any legacy (``teammate.universe=NULL``)
    attachment.

    Fires on ``pre_add`` for both forward
    (``episode.cast.add(teammate)``) and reverse
    (``teammate.episodes.add(episode)``) paths.

    ``action != "pre_add"`` short-circuits — we only care about
    additions. Removals + clears do not need Universe validation.
    """
    if action != "pre_add":
        return
    if not pk_set:
        return

    if reverse:
        # instance is a Teammate; pk_set is a set of Episode PKs
        teammate: Teammate = instance
        episode_pks = pk_set
        episodes = list(Episode.objects.filter(pk__in=episode_pks).select_related("universe"))
        for ep in episodes:
            _validate_pair(episode=ep, teammate=teammate)
    else:
        # instance is an Episode; pk_set is a set of Teammate PKs
        episode: Episode = instance
        # Ensure the FK to universe is loaded once (avoids N+1).
        episode_universe_id = episode.universe_id
        episode_workspace_id = episode.universe.workspace_id
        teammates = list(Teammate.objects.filter(pk__in=pk_set))
        for tm in teammates:
            _validate_pair(
                episode=episode,
                teammate=tm,
                episode_universe_id=episode_universe_id,
                episode_workspace_id=episode_workspace_id,
            )


def _validate_pair(
    *,
    episode: Episode,
    teammate: Teammate,
    episode_universe_id=None,
    episode_workspace_id=None,
) -> None:
    """Raise ValidationError if (episode, teammate) is a cross-Universe,
    cross-Workspace, or legacy-Teammate attachment. Lookups are
    hoisted so the caller can pre-load and avoid repeated queries.
    """
    if episode_universe_id is None:
        episode_universe_id = episode.universe_id
    if episode_workspace_id is None:
        episode_workspace_id = episode.universe.workspace_id

    if teammate.universe_id is None:
        raise ValidationError(
            f"Teammate {teammate.name!r} has no Universe (legacy). "
            f"A Universe-scoped Episode cannot include a legacy "
            f"Teammate in its cast. Assign the Teammate to a "
            f"Universe first."
        )
    if teammate.universe_id != episode_universe_id:
        raise ValidationError(
            f"Teammate {teammate.name!r} belongs to Universe "
            f"{teammate.universe_id}, but Episode belongs to "
            f"Universe {episode_universe_id}. Cross-Universe cast "
            f"attachment is forbidden."
        )
    if teammate.workspace_id != episode_workspace_id:
        raise ValidationError(
            f"Teammate {teammate.name!r} belongs to a different "
            f"Workspace than Episode."
        )
