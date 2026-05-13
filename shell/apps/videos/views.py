"""DRF viewset for Video."""
from __future__ import annotations

from rest_framework import status, viewsets
from rest_framework.response import Response

from apps.billing.services import TierLimitExceeded, check_video_limit
from character_os.permissions import IsWorkspaceMember

from .models import Video
from .serializers import VideoSerializer


# HTTP 402 Payment Required — semantically right for "your tier
# doesn't include this." Surface as a structured payload the SPA can
# translate into an upgrade prompt.
HTTP_PAYMENT_REQUIRED = 402


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

    def create(self, request, *args, **kwargs):
        """Gate by tier limit *before* the serializer validates so we
        return 402 with the upgrade payload instead of a generic 400."""
        spokesperson_id = request.data.get("spokesperson")
        if spokesperson_id:
            workspace = self._workspace_for_spokesperson(spokesperson_id)
            if workspace is not None:
                try:
                    check_video_limit(workspace)
                except TierLimitExceeded as exc:
                    return Response(exc.payload, status=HTTP_PAYMENT_REQUIRED)
        return super().create(request, *args, **kwargs)

    @staticmethod
    def _workspace_for_spokesperson(spokesperson_id):
        from apps.spokespeople.models import Spokesperson

        sp = (
            Spokesperson.objects.filter(pk=spokesperson_id)
            .select_related("workspace")
            .first()
        )
        return sp.workspace if sp else None
