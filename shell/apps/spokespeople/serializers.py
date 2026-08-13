"""Serializer for Teammate."""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership

from .models import Teammate


class TeammateSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    video_count = serializers.SerializerMethodField()
    # SESSION 232 — powers the SPA's masthead button state
    # ("Define {name}" when < 4 filled; plain "Identity" when >= 4)
    # + the "N of 6 filled" progress signal on the identity page.
    # Server-derived so the SPA has one authoritative source.
    identity_fields_filled = serializers.SerializerMethodField()

    # Write-only. When supplied on create, ``TeammateViewSet.create``
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
        model = Teammate
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "name",
            "business_brief",
            # W11.y (SESSION 175) — see Teammate.personality docstring.
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
            # SESSION 232 — Identity surface (contract rule 10).
            # Five new slots that pair with business_brief above to
            # form the six identity fields the customer fills on
            # ``/spokespeople/{id}/identity``. All PATCH-able. All
            # accept empty; only business_brief is server-required.
            "who_you_help",
            "what_you_sell",
            "always_emphasize",
            "never_say",
            "desired_feeling",
            "identity_fields_filled",
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
            "identity_fields_filled",
            "video_count",
            "created_at",
            "updated_at",
        ]

    def get_video_count(self, obj: Teammate) -> int:
        return obj.videos.count()

    def get_identity_fields_filled(self, obj: Teammate) -> int:
        return obj.identity_fields_filled_count()

    def validate_workspace(self, workspace):
        """Block creating a teammate in a workspace the user
        isn't a member of."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(user=request.user, workspace=workspace).exists():
            raise serializers.ValidationError("not a member of this workspace")
        return workspace
