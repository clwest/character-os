"""Serializer for Video."""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership

from .models import Video


class VideoSerializer(serializers.ModelSerializer):
    spokesperson_name = serializers.CharField(source="spokesperson.name", read_only=True)
    workspace_id = serializers.UUIDField(source="spokesperson.workspace_id", read_only=True)

    class Meta:
        model = Video
        fields = [
            "id",
            "spokesperson",
            "spokesperson_name",
            "workspace_id",
            "title",
            "brief",
            "kind",
            "status",
            "output_path",
            "duration_seconds",
            "tags",
            "media_engine_task_id",
            "error_message",
            "created_at",
            "updated_at",
            "completed_at",
        ]
        read_only_fields = [
            "id",
            "spokesperson_name",
            "workspace_id",
            "output_path",
            "duration_seconds",
            "media_engine_task_id",
            "error_message",
            "created_at",
            "updated_at",
            "completed_at",
        ]

    def validate_spokesperson(self, spokesperson):
        """Block creating a video on a spokesperson the user can't see."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(
            user=request.user,
            workspace=spokesperson.workspace,
        ).exists():
            raise serializers.ValidationError("spokesperson not in your workspaces")
        return spokesperson
