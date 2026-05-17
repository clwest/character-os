"""Serializer for Spokesperson."""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership

from .models import Spokesperson


class SpokespersonSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    video_count = serializers.SerializerMethodField()

    # Write-only. When supplied on create, ``SpokespersonViewSet.create``
    # fires ``MediaEngineClient.create_avatar`` after the DB row lands
    # and persists the resulting ``runway_avatar_id`` /
    # ``runway_avatar_status`` onto the model. Format:
    # ``data:image/{png|jpeg|webp};base64,...`` (5 MB cap, enforced
    # media-engine side).
    portrait_data_uri = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=10 * 1024 * 1024,
        trim_whitespace=False,
    )
    voice_preset = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=80,
    )

    class Meta:
        model = Spokesperson
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "name",
            "business_brief",
            # W11.y (SESSION 175) — see Spokesperson.personality docstring.
            # Splits HOW (personality) from WHAT (business_brief) so
            # operators can swap business briefs across personality
            # types.
            "personality",
            "visual_subject",
            "visual_template",
            "tone_archetype",
            "status",
            "runway_avatar_id",
            "runway_avatar_status",
            "portrait_path",
            "voice_id",
            "video_count",
            "created_at",
            "updated_at",
            "portrait_data_uri",
            "voice_preset",
        ]
        read_only_fields = [
            "id",
            "workspace_name",
            "runway_avatar_id",
            "runway_avatar_status",
            "portrait_path",
            "voice_id",
            "video_count",
            "created_at",
            "updated_at",
        ]

    def get_video_count(self, obj: Spokesperson) -> int:
        return obj.videos.count()

    def validate_workspace(self, workspace):
        """Block creating a spokesperson in a workspace the user
        isn't a member of."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(user=request.user, workspace=workspace).exists():
            raise serializers.ValidationError("not a member of this workspace")
        return workspace
