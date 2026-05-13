"""Serializers for accounts: Workspace, Membership."""
from __future__ import annotations

from rest_framework import serializers

from .models import Membership, Workspace


class MembershipSerializer(serializers.ModelSerializer):
    user_username = serializers.CharField(source="user.username", read_only=True)
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)

    class Meta:
        model = Membership
        fields = ["id", "user", "user_username", "workspace", "workspace_name", "role", "created_at"]
        read_only_fields = ["id", "user_username", "workspace_name", "created_at"]


class WorkspaceSerializer(serializers.ModelSerializer):
    owner_username = serializers.CharField(source="owner.username", read_only=True)
    role = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()

    class Meta:
        model = Workspace
        fields = [
            "id",
            "name",
            "slug",
            "owner",
            "owner_username",
            "role",
            "member_count",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "slug", "owner", "owner_username", "role", "member_count", "created_at", "updated_at"]

    def get_role(self, obj: Workspace) -> str | None:
        """Return the requesting user's role in this workspace."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            return None
        membership = obj.memberships.filter(user=request.user).first()
        return membership.role if membership else None

    def get_member_count(self, obj: Workspace) -> int:
        return obj.memberships.count()
