"""DRF viewset for Spokesperson."""
from __future__ import annotations

from rest_framework import viewsets

from character_os.permissions import IsWorkspaceMember

from .models import Spokesperson
from .serializers import SpokespersonSerializer


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
