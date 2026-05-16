"""Serializers for ConversationThread + ConversationMessage."""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership

from .models import ConversationMessage, ConversationThread


class ConversationMessageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ConversationMessage
        fields = [
            "id",
            "thread",
            "role",
            "content",
            "created_at",
            # K6.5 — verifier surface for the SPA
            "verification_warnings",
            "rejected_synthesis",
            # K6.4 v1.2 — verification_status badge
            "verification_status",
        ]
        read_only_fields = [
            "id",
            "thread",
            "role",
            "created_at",
            "verification_warnings",
            "rejected_synthesis",
            "verification_status",
        ]


class ConversationThreadSerializer(serializers.ModelSerializer):
    spokesperson_name = serializers.CharField(source="spokesperson.name", read_only=True)
    message_count = serializers.SerializerMethodField()
    last_message_preview = serializers.SerializerMethodField()

    class Meta:
        model = ConversationThread
        fields = [
            "id",
            "spokesperson",
            "spokesperson_name",
            "title",
            "message_count",
            "last_message_preview",
            "created_at",
            "last_activity_at",
        ]
        read_only_fields = [
            "id",
            "spokesperson_name",
            "message_count",
            "last_message_preview",
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

    def get_message_count(self, obj) -> int:
        return obj.messages.count()

    def get_last_message_preview(self, obj) -> str:
        last = obj.messages.order_by("-created_at").first()
        if last is None:
            return ""
        preview = (last.content or "").strip().replace("\n", " ")
        return preview[:160]
