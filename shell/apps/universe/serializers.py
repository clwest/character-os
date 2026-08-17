"""DRF serializer for the Universe model.

SESSION 261 / ``docs/design/UNIVERSE_SCHEMA_V1.md`` §"API contract".
"""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership

from .models import Universe


class UniverseSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    # Live counts of members in this Universe. Powers the SPA's
    # "N teammates, M docs" pill on the Universe list + the hard-
    # delete conflict body (enumerates blocking child counts).
    teammate_count = serializers.SerializerMethodField()
    knowledge_document_count = serializers.SerializerMethodField()

    class Meta:
        model = Universe
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "name",
            "slug",
            "description",
            "created_by",
            "created_at",
            "updated_at",
            "archived_at",
            "teammate_count",
            "knowledge_document_count",
        ]
        read_only_fields = [
            "id",
            "workspace_name",
            "slug",
            "created_by",
            "created_at",
            "updated_at",
            "archived_at",
            "teammate_count",
            "knowledge_document_count",
        ]

    def get_teammate_count(self, obj: Universe) -> int:
        return obj.teammate_count()

    def get_knowledge_document_count(self, obj: Universe) -> int:
        return obj.knowledge_document_count()

    def validate_workspace(self, workspace):
        """Block Universe creation in a workspace the caller
        isn't a Member of. Mirrors ``TeammateSerializer.
        validate_workspace``.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(
            user=request.user, workspace=workspace,
        ).exists():
            raise serializers.ValidationError("not a member of this workspace")
        return workspace

    def validate_name(self, name):
        stripped = (name or "").strip()
        if not stripped:
            raise serializers.ValidationError(
                "Universe name cannot be blank."
            )
        return stripped
