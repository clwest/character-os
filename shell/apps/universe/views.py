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

from .models import Universe
from .serializers import UniverseSerializer

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
        teammate_count = instance.teammate_count()
        doc_count = instance.knowledge_document_count()
        if teammate_count or doc_count:
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
