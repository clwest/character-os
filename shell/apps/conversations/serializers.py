"""Serializer for ConversationThread."""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership

from .models import ConversationThread


class ConversationThreadSerializer(serializers.ModelSerializer):
    spokesperson_name = serializers.CharField(source="spokesperson.name", read_only=True)

    class Meta:
        model = ConversationThread
        fields = [
            "id",
            "spokesperson",
            "spokesperson_name",
            "title",
            "created_at",
            "last_activity_at",
        ]
        read_only_fields = [
            "id",
            "spokesperson_name",
            "created_at",
            "last_activity_at",
        ]

    def validate_spokesperson(self, spokesperson):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(
            user=request.user,
            workspace=spokesperson.workspace,
        ).exists():
            raise serializers.ValidationError("spokesperson not in your workspaces")
        return spokesperson
