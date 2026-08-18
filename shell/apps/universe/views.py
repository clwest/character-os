"""DRF viewset for Universe.

SESSION 261. See ``docs/design/UNIVERSE_SCHEMA_V1.md`` §"API
contract" for the endpoint surface. Uniform pattern with
``KnowledgeDocumentViewSet`` (soft-delete via ``DELETE``, custom
``unarchive`` action, ``?workspace=`` and
``?include_archived=`` filters).
"""
from __future__ import annotations

import logging
from typing import Any

from django.db import models as djmodels
from django.utils import timezone
from rest_framework import status as drf_status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from character_os.permissions import IsWorkspaceMember

from apps.accounts.models import Membership
from apps.spokespeople.models import Teammate

from .models import Episode, Universe
from .serializers import EpisodeSerializer, UniverseSerializer

logger = logging.getLogger(__name__)


class UniverseViewSet(viewsets.ModelViewSet):
    """Workspace-scoped CRUD on Universe.

    List defaults to non-archived Universes across every workspace
    the caller is a member of. ``?workspace=<uuid>`` narrows to
    one workspace; ``?include_archived=true`` includes archived
    rows.
    """

    serializer_class = UniverseSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Universe.objects.none()

        qs = (
            Universe.objects
            .filter(workspace__memberships__user=user)
            .select_related("workspace")
            .distinct()
        )

        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)

        include_archived = (
            self.request.query_params.get("include_archived") or ""
        ).strip().lower() in {"1", "true", "yes"}
        if not include_archived:
            qs = qs.filter(archived_at__isnull=True)

        return qs

    def perform_create(self, serializer: UniverseSerializer) -> None:
        """Stamp ``created_by`` from the authenticated user.
        The serializer marks ``created_by`` as read-only so the
        caller cannot spoof it.
        """
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)

    # ---- Soft delete + hard-delete conflict preflight ----

    def destroy(self, request, *args, **kwargs) -> Response:
        """Soft-delete (archive) by default. Hard-delete via
        ``?hard=true`` requires the Universe be empty (no
        Teammate members, no KnowledgeDocument members) —
        RESTRICT on the child FKs would raise
        ``django.db.models.RestrictedError`` at the DB level; we
        preflight-check to return a clean ``409 Conflict`` with
        a helpful body enumerating blocking child counts.

        This preserves the load-bearing property named in
        UNIVERSE_SCHEMA_V1.md §"Universe deletion (direct)":
        populated Universes never silently demote their children
        to ``universe=NULL``.
        """
        instance: Universe = self.get_object()
        hard = (
            (request.query_params.get("hard") or "").strip().lower()
            in {"1", "true", "yes"}
        )

        if not hard:
            # Soft delete via archive. Idempotent: already-archived
            # rows just refresh ``archived_at``.
            instance.archived_at = timezone.now()
            instance.save(update_fields=["archived_at", "updated_at"])
            return Response(status=drf_status.HTTP_204_NO_CONTENT)

        # Hard-delete preflight — populated Universes are blocked.
        # SESSION 262 — Episode.universe = RESTRICT, so populated
        # Universes with Episodes also can't hard-delete. Preflight
        # extended to enumerate Episode counts too.
        teammate_count = instance.teammate_count()
        doc_count = instance.knowledge_document_count()
        episode_count = instance.episode_count()
        if teammate_count or doc_count or episode_count:
            return Response(
                {
                    "error": (
                        "Cannot hard-delete a populated Universe. "
                        "Reassign every member to another Universe "
                        "(or to legacy) first."
                    ),
                    "code": "universe_populated",
                    "blocking": {
                        "teammate_count": teammate_count,
                        "knowledge_document_count": doc_count,
                        "episode_count": episode_count,
                    },
                },
                status=drf_status.HTTP_409_CONFLICT,
            )

        # Empty — RESTRICT will not fire; safe to delete.
        instance.delete()
        return Response(status=drf_status.HTTP_204_NO_CONTENT)

    # ---- Unarchive ----

    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, *args, **kwargs) -> Response:
        """Clear ``archived_at``, un-archiving the Universe.
        Idempotent — active Universes just no-op.

        Manual lookup: the default ``get_queryset`` filters out
        archived rows unless ``?include_archived=true`` is passed,
        so a call to ``.get_object()`` on an archived Universe
        without the query param would 404. Unarchive is the one
        endpoint whose whole purpose is to act on an archived row,
        so we look up broadly (still workspace-scoped) here.
        """
        user = request.user
        instance = (
            Universe.objects
            .filter(
                pk=kwargs.get("pk"),
                workspace__memberships__user=user,
            )
            .first()
        )
        if instance is None:
            return Response(status=drf_status.HTTP_404_NOT_FOUND)
        # Enforce owner-write parity with IsWorkspaceMember.
        self.check_object_permissions(request, instance)

        if instance.archived_at is not None:
            instance.archived_at = None
            instance.save(update_fields=["archived_at", "updated_at"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)


# ============================================================
# EPISODE_SCHEMA_V1 (SESSION 262)
# ============================================================


class EpisodeViewSet(viewsets.ModelViewSet):
    """Universe-scoped CRUD on Episode + cast add/remove.

    List filters:
      * ``?universe=<uuid>`` — restrict to one Universe.
      * ``?include_archived=true`` — include archived rows
        (default: active only).

    Delete:
      * Default = archive (``archived_at = now``). Idempotent.
      * ``?hard=true`` = hard-delete. Blocked with 409 when any
        Composition is attached (``PROTECT`` on
        ``Composition.episode``). Cast M2M cascades cleanly
        (does NOT block per EPISODE_SCHEMA_V1 §Q8 correction).

    Custom actions:
      * ``POST /api/episodes/<id>/unarchive/`` — reverse archive.
      * ``POST /api/episodes/<id>/cast/`` — add cast member.
      * ``DELETE /api/episodes/<id>/cast/<teammate_id>/`` — remove.
    """

    serializer_class = EpisodeSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Episode.objects.none()

        qs = (
            Episode.objects
            .filter(universe__workspace__memberships__user=user)
            .select_related("universe", "universe__workspace")
            .prefetch_related("cast")
            .distinct()
        )

        universe_id = self.request.query_params.get("universe")
        if universe_id:
            qs = qs.filter(universe_id=universe_id)

        include_archived = (
            self.request.query_params.get("include_archived") or ""
        ).strip().lower() in {"1", "true", "yes"}
        if not include_archived:
            qs = qs.filter(archived_at__isnull=True)

        return qs

    def perform_create(self, serializer: EpisodeSerializer) -> None:
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(created_by=user)

    # ---- Delete (archive default; hard-delete gated) ----

    def destroy(self, request, *args, **kwargs) -> Response:
        instance: Episode = self.get_object()
        hard = (
            (request.query_params.get("hard") or "").strip().lower()
            in {"1", "true", "yes"}
        )

        if not hard:
            instance.archived_at = timezone.now()
            instance.save(update_fields=["archived_at", "updated_at"])
            return Response(status=drf_status.HTTP_204_NO_CONTENT)

        # Hard-delete preflight — only attached Compositions block.
        # Cast membership does NOT block (EpisodeCast rows cascade
        # cleanly with the Episode row). See EPISODE_SCHEMA_V1 §Q8.
        composition_count = instance.composition_count()
        if composition_count:
            return Response(
                {
                    "error": (
                        "Cannot hard-delete a populated Episode. "
                        "Detach every Composition (or archive) first."
                    ),
                    "code": "episode_populated",
                    "blocking": {
                        "composition_count": composition_count,
                    },
                },
                status=drf_status.HTTP_409_CONFLICT,
            )

        instance.delete()
        return Response(status=drf_status.HTTP_204_NO_CONTENT)

    # ---- Unarchive ----

    @action(detail=True, methods=["post"], url_path="unarchive")
    def unarchive(self, request, *args, **kwargs) -> Response:
        user = request.user
        instance = (
            Episode.objects
            .filter(
                pk=kwargs.get("pk"),
                universe__workspace__memberships__user=user,
            )
            .select_related("universe", "universe__workspace")
            .prefetch_related("cast")
            .first()
        )
        if instance is None:
            return Response(status=drf_status.HTTP_404_NOT_FOUND)
        self.check_object_permissions(request, instance)

        if instance.archived_at is not None:
            instance.archived_at = None
            instance.save(update_fields=["archived_at", "updated_at"])
        serializer = self.get_serializer(instance)
        return Response(serializer.data)

    # ---- Cast add / remove ----

    @action(
        detail=True, methods=["post", "delete"], url_path="cast",
    )
    def cast_add(self, request, *args, **kwargs) -> Response:
        """POST /api/episodes/<id>/cast/ with {"teammate": UUID}
        adds a Teammate. Universe-consistency + Workspace-consistency
        + legacy-Teammate rejection are enforced by the pre_add
        signal in ``apps/universe/signals.py``.

        DELETE on this URL is not defined — cast removal uses the
        ``cast_remove`` URL below with a Teammate PK.
        """
        instance: Episode = self.get_object()

        if request.method == "DELETE":
            # DELETE on the plural cast path is not the removal API;
            # removals hit /cast/<teammate_id>/ handled by
            # cast_remove. Return 405.
            return Response(
                {"error": "Use DELETE /api/episodes/<id>/cast/<teammate_id>/."},
                status=drf_status.HTTP_405_METHOD_NOT_ALLOWED,
            )

        teammate_id = (request.data or {}).get("teammate")
        if not teammate_id:
            return Response(
                {"teammate": "required"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        # Resolve Teammate. Scope to caller's workspace-member set to
        # avoid disclosing cross-workspace Teammate IDs.
        teammate = (
            Teammate.objects.filter(
                pk=teammate_id,
                workspace__memberships__user=request.user,
            )
            .first()
        )
        if teammate is None:
            return Response(
                {"teammate": "not found or not in an accessible workspace"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        try:
            instance.cast.add(teammate)
        except Exception as exc:
            # Universe / Workspace / legacy-Teammate rejections
            # bubble as ValidationError from the pre_add signal.
            return Response(
                {"teammate": str(exc)},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        # Return fresh Episode payload with updated cast.
        instance.refresh_from_db()
        serializer = self.get_serializer(instance)
        return Response(
            serializer.data,
            status=drf_status.HTTP_201_CREATED,
        )

    @action(
        detail=True,
        methods=["delete"],
        url_path=r"cast/(?P<teammate_id>[^/.]+)",
    )
    def cast_remove(self, request, *args, **kwargs) -> Response:
        """DELETE /api/episodes/<id>/cast/<teammate_id>/ — remove
        one cast member. Idempotent; missing cast row → 204."""
        instance: Episode = self.get_object()
        teammate_id = kwargs.get("teammate_id")
        try:
            teammate = Teammate.objects.get(pk=teammate_id)
        except Teammate.DoesNotExist:
            # 204 — nothing to remove is idempotent success.
            return Response(status=drf_status.HTTP_204_NO_CONTENT)
        instance.cast.remove(teammate)
        return Response(status=drf_status.HTTP_204_NO_CONTENT)
