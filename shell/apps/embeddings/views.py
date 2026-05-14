"""DRF viewset for KnowledgeDocument.

SESSION 138. CRUD on workspace-scoped knowledge.

* GET    /api/knowledge/                   list (workspace=<uuid> filter; SESSION 138 / K4)
* POST   /api/knowledge/                   create (paste OR PDF; K4)
* GET    /api/knowledge/<id>/              detail (K4)
* PATCH  /api/knowledge/<id>/              update title + spokespeople (K4)
* DELETE /api/knowledge/<id>/              soft delete (is_active=False; K4)
* POST   /api/knowledge/<id>/attach/       {spokesperson_id: ...} (K5)
* POST   /api/knowledge/<id>/detach/       {spokesperson_id: ...} (K5)

The list view defaults to the requesting user's accessible
workspaces; a ``?workspace=<uuid>`` filter narrows to one.
``?spokesperson=<uuid>`` filters to docs visible to that
spokesperson (empty M2M OR M2M includes them) — same
visibility filter ``retrieve_for_spokesperson`` uses, so the
SPA's spokesperson Knowledge tab shows exactly what render-
time RAG would draw from.

Workspace scoping is enforced by ``IsWorkspaceMember`` +
queryset filter — the K2 retrieval-surface privacy contract
is unaffected because the chunk table is only queried through
``apps.embeddings.retrieval``.
"""
from __future__ import annotations

import logging

from django.db.models import Q
from rest_framework import status as drf_status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from apps.spokespeople.models import Spokesperson
from character_os.permissions import IsWorkspaceMember

from .models import KnowledgeDocument
from .serializers import KnowledgeDocumentSerializer

logger = logging.getLogger(__name__)


class KnowledgeDocumentViewSet(viewsets.ModelViewSet):
    """Workspace-scoped CRUD on KnowledgeDocument."""

    serializer_class = KnowledgeDocumentSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return KnowledgeDocument.objects.none()

        qs = (
            KnowledgeDocument.objects.filter(
                workspace__memberships__user=user,
                is_active=True,
            )
            .select_related("workspace")
            .prefetch_related("spokespeople")
            .distinct()
        )

        # Optional workspace narrowing.
        workspace_id = self.request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)

        # SESSION 138 / K5 — optional spokesperson visibility
        # filter. Returns docs visible to this spokesperson:
        # either no M2M attachments (visible to all) OR the
        # spokesperson is one of the attached.
        spokesperson_id = self.request.query_params.get("spokesperson")
        if spokesperson_id:
            qs = qs.filter(
                Q(spokespeople__isnull=True) | Q(spokespeople=spokesperson_id)
            ).distinct()

        # Optional doc-type filter (useful for the SPA's tab UI).
        doc_type = self.request.query_params.get("document_type")
        if doc_type:
            qs = qs.filter(document_type=doc_type)

        return qs

    def destroy(self, request, *args, **kwargs):
        """Soft delete — flip ``is_active=False`` instead of
        dropping the row. The chunk rows stay so the retrieval
        path's ``is_active=True`` filter is the gatekeeper.
        Hard-delete is an admin-only operation."""
        instance = self.get_object()
        instance.is_active = False
        instance.save(update_fields=["is_active", "updated_at"])
        return Response(status=drf_status.HTTP_204_NO_CONTENT)

    # ---- M2M toggle actions (K5) -----------------------

    @action(detail=True, methods=["post"])
    def attach(self, request, *args, **kwargs):
        """Attach a single spokesperson to this doc's visibility
        M2M. Body: ``{"spokesperson_id": "<uuid>"}``. Idempotent —
        attaching an already-attached spokesperson is a no-op
        that returns the updated doc.

        Cross-workspace attaches are rejected by the
        m2m_changed signal in ``apps.embeddings.signals``;
        we surface that as a 400 instead of a 500.
        """
        return self._toggle_spokesperson(request, attach=True)

    @action(detail=True, methods=["post"])
    def detach(self, request, *args, **kwargs):
        """Detach a single spokesperson from this doc's M2M.
        Body: ``{"spokesperson_id": "<uuid>"}``. Idempotent —
        detaching an unattached spokesperson is a no-op.

        Note: detaching the last spokesperson on a doc that
        previously had explicit M2M attachments collapses
        visibility back to *all* spokespeople in the workspace
        (empty M2M = visible to all). That's the intentional
        semantics of the scope-lock; surfaced loudly in the
        SPA's UI copy.
        """
        return self._toggle_spokesperson(request, attach=False)

    def _toggle_spokesperson(self, request, *, attach: bool):
        from django.core.exceptions import ValidationError as DjangoValidationError

        doc = self.get_object()
        sp_id = request.data.get("spokesperson_id")
        if not sp_id:
            raise ValidationError({"spokesperson_id": "Required."})

        try:
            sp = Spokesperson.objects.get(pk=sp_id)
        except Spokesperson.DoesNotExist as exc:
            raise NotFound(f"Spokesperson {sp_id} not found.") from exc

        if sp.workspace_id != doc.workspace_id:
            raise ValidationError({
                "spokesperson_id": (
                    f"Spokesperson {sp.name!r} is in another workspace."
                ),
            })

        try:
            if attach:
                doc.spokespeople.add(sp)
            else:
                doc.spokespeople.remove(sp)
        except DjangoValidationError as exc:
            # The m2m_changed signal raised — translate to DRF.
            raise ValidationError({"spokesperson_id": list(exc.messages)}) from exc

        serializer = self.get_serializer(doc)
        return Response(serializer.data)
