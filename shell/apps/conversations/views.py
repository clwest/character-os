"""DRF viewset for ConversationThread."""
from __future__ import annotations

from rest_framework import viewsets

from character_os.permissions import IsWorkspaceMember

from .models import ConversationThread
from .serializers import ConversationThreadSerializer


class ConversationThreadViewSet(viewsets.ModelViewSet):
    """CRUD on conversation threads in the user's workspaces."""

    serializer_class = ConversationThreadSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ConversationThread.objects.none()
        return (
            ConversationThread.objects.filter(
                spokesperson__workspace__memberships__user=user
            )
            .select_related("spokesperson", "spokesperson__workspace")
            .distinct()
        )
