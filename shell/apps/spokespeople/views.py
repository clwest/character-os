"""DRF viewset for Spokesperson."""
from __future__ import annotations

from rest_framework import viewsets
from rest_framework.response import Response

from apps.billing.services import TierLimitExceeded, check_spokesperson_limit
from character_os.permissions import IsWorkspaceMember

from .models import Spokesperson
from .serializers import SpokespersonSerializer

HTTP_PAYMENT_REQUIRED = 402


class SpokespersonViewSet(viewsets.ModelViewSet):
    """CRUD on spokespeople in the requesting user's workspaces."""

    serializer_class = SpokespersonSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Spokesperson.objects.none()
        return (
            Spokesperson.objects.filter(workspace__memberships__user=user)
            .select_related("workspace")
            .distinct()
        )

    def create(self, request, *args, **kwargs):
        """Gate spokesperson creation by tier limit. 402 with the
        upgrade payload when at cap; otherwise fall through to default
        DRF create logic."""
        workspace_id = request.data.get("workspace")
        if workspace_id:
            workspace = self._workspace(workspace_id)
            if workspace is not None:
                try:
                    check_spokesperson_limit(workspace)
                except TierLimitExceeded as exc:
                    return Response(exc.payload, status=HTTP_PAYMENT_REQUIRED)
        return super().create(request, *args, **kwargs)

    @staticmethod
    def _workspace(workspace_id):
        from apps.accounts.models import Workspace

        return Workspace.objects.filter(pk=workspace_id).first()
