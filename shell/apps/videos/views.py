"""DRF viewset for Video."""
from __future__ import annotations

from rest_framework import viewsets

from character_os.permissions import IsWorkspaceMember

from .models import Video
from .serializers import VideoSerializer


class VideoViewSet(viewsets.ModelViewSet):
    """CRUD on videos belonging to spokespeople in the user's workspaces."""

    serializer_class = VideoSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Video.objects.none()
        return (
            Video.objects.filter(spokesperson__workspace__memberships__user=user)
            .select_related("spokesperson", "spokesperson__workspace")
            .distinct()
        )
