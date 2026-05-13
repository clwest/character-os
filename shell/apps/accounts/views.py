"""DRF viewsets for accounts: Workspace, Membership."""
from __future__ import annotations

from django.db import transaction
from rest_framework import mixins, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from character_os.permissions import IsWorkspaceMember

from .models import Membership, Workspace
from .serializers import MembershipSerializer, WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    """CRUD on the workspaces the requesting user is a member of.

    On create, the requesting user becomes the workspace owner AND
    gets an owner-role Membership in one atomic transaction.
    """

    serializer_class = WorkspaceSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Workspace.objects.none()
        return Workspace.objects.filter(memberships__user=user).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        workspace = serializer.save(owner=self.request.user)
        Membership.objects.create(
            user=self.request.user,
            workspace=workspace,
            role=Membership.Role.OWNER,
        )

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """List memberships in this workspace."""
        workspace = self.get_object()
        memberships = workspace.memberships.select_related("user").all()
        serializer = MembershipSerializer(memberships, many=True, context={"request": request})
        return Response(serializer.data)


class MembershipViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only listing of the requesting user's memberships."""

    serializer_class = MembershipSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Membership.objects.none()
        return Membership.objects.filter(user=user).select_related("workspace", "user")
