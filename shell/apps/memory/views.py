"""DRF viewset for NarrativeMemory.

SESSION 264 Slice 1. Two entry points:

* ``/api/narrative-memories/`` — the resource itself. List (with
  ``?episode`` and ``?universe`` filters), retrieve, archive
  (``DELETE``), unarchive (``POST``).
* ``/api/compositions/<id>/promote-narrative-memory/`` — the
  batch promotion action. Defined on the ``CompositionViewSet``
  (see ``apps/compositions/views.py``); this module exposes the
  underlying ``promote_from_composition`` service that view calls.
"""
from __future__ import annotations

import logging
from typing import Any

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import status as drf_status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from character_os.permissions import IsWorkspaceMember

from apps.compositions.models import Composition
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode

from .models import NarrativeMemory, NarrativeMemoryStatus
from .serializers import NarrativeMemorySerializer

logger = logging.getLogger(__name__)


class NarrativeMemoryViewSet(viewsets.ReadOnlyModelViewSet):
    """List / retrieve NarrativeMemory rows plus archive/unarchive.

    Writes go through:
      * ``POST /api/compositions/<id>/promote-narrative-memory/``
        (batch promote, hangs off CompositionViewSet — see
        ``apps/compositions/views.py``).
      * ``DELETE /api/narrative-memories/<id>/`` — soft delete
        (``archived_at = now``). Idempotent.
      * ``POST /api/narrative-memories/<id>/unarchive/`` — reverse
        archive. Idempotent.

    List filters:
      * ``?episode=<uuid>`` — restrict to one Episode.
      * ``?universe=<uuid>`` — restrict to one Universe (all
        Episodes in that Universe).
      * ``?source_composition=<uuid>`` — restrict to memories
        promoted from a single Composition attempt.
      * ``?include_archived=true`` — include archived rows
        (default: active only).
      * ``?include_superseded=true`` — include superseded rows
        (default: current only).
    """

    serializer_class = NarrativeMemorySerializer
    permission_classes = [IsWorkspaceMember]
    # ReadOnlyModelViewSet + DELETE (archive) + POST (unarchive
    # action). We do not expose direct create/update on this
    # resource because promotion is the only sanctioned write path.
    http_method_names = ["get", "delete", "head", "options", "post"]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return NarrativeMemory.objects.none()

        qs = (
            NarrativeMemory.objects
            .filter(workspace__memberships__user=user)
            .select_related(
                "workspace",
                "universe",
                "episode",
                "source_composition",
                "supersedes",
                "promoted_by",
            )
            .prefetch_related("witnessed_by")
            .distinct()
        )

        episode_id = self.request.query_params.get("episode")
        if episode_id:
            qs = qs.filter(episode_id=episode_id)

        universe_id = self.request.query_params.get("universe")
        if universe_id:
            qs = qs.filter(universe_id=universe_id)

        source_id = self.request.query_params.get("source_composition")
        if source_id:
            qs = qs.filter(source_composition_id=source_id)

        include_archived = (
            self.request.query_params.get("include_archived") or ""
        ).strip().lower() in {"1", "true", "yes"}
        if not include_archived:
            qs = qs.filter(archived_at__isnull=True)

        include_superseded = (
            self.request.query_params.get("include_superseded") or ""
        ).strip().lower() in {"1", "true", "yes"}
        if not include_superseded:
            qs = qs.exclude(status=NarrativeMemoryStatus.SUPERSEDED)

        return qs

    def destroy(self, request, *args, **kwargs) -> Response:
        """Soft-delete via ``archived_at = now``. Idempotent.

        No hard-delete affordance in Slice 1 — narrative history
        is an audit surface.
        """
        instance: NarrativeMemory = self.get_object()
        if instance.archived_at is None:
            instance.archived_at = timezone.now()
            # Flip status so Slice 2 retrieval can skip archived
            # rows via a single status predicate if desired.
            instance.status = NarrativeMemoryStatus.ARCHIVED
            instance.save(update_fields=["archived_at", "status", "updated_at"])
        return Response(status=drf_status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, *args, **kwargs) -> Response:
        """Clear ``archived_at`` and restore status to REMEMBERED.

        Idempotent for already-active rows. If the row is
        SUPERSEDED (not archived) we do NOT flip it back to
        REMEMBERED — supersede is a distinct lifecycle move.
        """
        user = request.user
        # Manual lookup so we can inspect archived rows (the
        # default queryset filters them out).
        instance = (
            NarrativeMemory.objects
            .filter(
                pk=kwargs.get("pk"),
                workspace__memberships__user=user,
            )
            .first()
        )
        if instance is None:
            return Response(status=drf_status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, instance)

        if instance.archived_at is not None:
            instance.archived_at = None
            if instance.status == NarrativeMemoryStatus.ARCHIVED:
                instance.status = NarrativeMemoryStatus.REMEMBERED
            instance.save(update_fields=["archived_at", "status", "updated_at"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# ============================================================
# Service — called by the CompositionViewSet promote action.
# Lives here (not in a services.py) because it is the only
# service function in Slice 1; if the surface grows in Slice 2+
# we can extract to services.py without breaking imports.
# ============================================================


def promote_from_composition(
    *,
    composition: Composition,
    episode: Episode,
    memory_items: list[dict[str, Any]],
    promoted_by,
) -> list[NarrativeMemory]:
    """Create NarrativeMemory rows tied to ``composition`` + ``episode``.

    Called from ``CompositionViewSet.promote_narrative_memory``.
    Enforces the invariants named in the docstrings on
    ``NarrativeMemory.clean()`` and the ``witnessed_by`` pre_add
    signal. Wrapped in an atomic so a bad item in a batch fails
    the whole batch (all-or-nothing semantics; operator resubmits
    a cleaned batch).

    ``memory_items`` must already be validated by
    ``NarrativeMemoryPromoteItemSerializer`` (per-item UUIDs are
    real UUIDs, ``body`` is non-blank, etc.). This function does
    the model-level enforcement (Universe consistency, witness
    cast membership, supersede-in-same-Episode).
    """
    workspace_id = episode.universe.workspace_id
    universe_id = episode.universe_id
    cast_ids = set(episode.cast.values_list("id", flat=True))

    created: list[NarrativeMemory] = []

    with transaction.atomic():
        for item in memory_items:
            witnessed_by_ids = item.get("witnessed_by") or []
            # Fast-fail witness validation before we hit the DB
            # signal. Cross-Universe / cross-Workspace /
            # not-in-cast rejections surface as ValidationError
            # with clear per-teammate messages.
            for tm_id in witnessed_by_ids:
                if tm_id not in cast_ids:
                    raise ValidationError({
                        "witnessed_by": (
                            f"Teammate {tm_id} is not in Episode's cast "
                            f"(id={episode.id})."
                        ),
                    })

            supersedes = None
            supersedes_id = item.get("supersedes")
            if supersedes_id:
                supersedes = (
                    NarrativeMemory.objects
                    .filter(pk=supersedes_id, episode=episode)
                    .first()
                )
                if supersedes is None:
                    raise ValidationError({
                        "supersedes": (
                            f"memory {supersedes_id} not found in "
                            f"episode {episode.id}"
                        ),
                    })

            memory = NarrativeMemory(
                episode=episode,
                source_composition=composition,
                workspace_id=workspace_id,
                universe_id=universe_id,
                kind=item.get("kind"),
                body=item["body"],
                weight=item.get("weight"),
                supersedes=supersedes,
                superseded_reason=item.get("superseded_reason") or "",
                promoted_by=promoted_by,
            )
            try:
                memory.full_clean()
            except DjangoValidationError as exc:
                raise ValidationError(exc.message_dict or {"detail": exc.messages})
            memory.save()

            # M2M attach — the pre_add signal enforces cross-cast
            # + cross-Universe rejection defensively; anything the
            # fast-fail block above missed lands here.
            if witnessed_by_ids:
                witnesses = list(
                    Teammate.objects.filter(pk__in=witnessed_by_ids)
                )
                try:
                    memory.witnessed_by.set(witnesses)
                except DjangoValidationError as exc:
                    raise ValidationError({
                        "witnessed_by": exc.messages,
                    })

            # If this row supersedes another, flip the older row
            # to SUPERSEDED with a timestamp. Doesn't unarchive
            # or re-parent — the older row remains attached to
            # its own source_composition and Episode.
            if supersedes is not None:
                supersedes.status = NarrativeMemoryStatus.SUPERSEDED
                supersedes.superseded_at = timezone.now()
                supersedes.save(update_fields=[
                    "status", "superseded_at", "updated_at",
                ])

            created.append(memory)

    return created
