"""DRF viewsets for accounts: Workspace, Membership.

Also hosts the ``/api/me/`` endpoint that the SPA hits after auth to
discover the current user + their default workspace.
"""
from __future__ import annotations

from django.db import transaction
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from character_os.permissions import IsWorkspaceMember

from .models import Membership, Workspace, default_workspace_for
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


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request: Request) -> Response:
    """Identity endpoint for the SPA.

    Returns the current user plus their default workspace + role. The
    SPA hits this after auth as its first call — gives it everything
    it needs to render the dashboard without a follow-up roundtrip.
    """
    user = request.user
    workspace = default_workspace_for(user)
    payload: dict = {
        "id": user.id,
        "email": user.email,
        "is_staff": user.is_staff,
        "default_workspace": None,
    }
    if workspace is not None:
        membership = workspace.memberships.filter(user=user).first()
        payload["default_workspace"] = {
            "id": str(workspace.id),
            "name": workspace.name,
            "slug": workspace.slug,
            "role": membership.role if membership else None,
        }
    return Response(payload)
