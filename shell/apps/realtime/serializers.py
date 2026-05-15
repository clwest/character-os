"""DRF serializers for the realtime arc — R3.

Two read shapes:

* ``RealtimeSessionSerializer`` — standard retrieve shape.
  Excludes ``provider_session_key`` (contract rule 9 — the
  SDK connect token is a secret never exposed in
  list/retrieve responses).
* ``RealtimeSessionWithKeySerializer`` — only used as the
  response to a successful create. Includes
  ``provider_session_key`` so the SPA can hand it to the
  Runway SDK. After that, the SPA holds the key in memory
  for the session's lifetime; subsequent retrieves return
  the standard shape.

The tool invocation serializer is read-only — invocations
get created internally by R7 (tool catalog) once it lands.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership

from .models import RealtimeSession, RealtimeToolInvocation


class RealtimeToolInvocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = RealtimeToolInvocation
        fields = [
            "id",
            "session",
            "tool_name",
            "args",
            "status",
            "error_message",
            "produced_asset",
            "produced_composition",
            "invoked_at",
            "completed_at",
        ]
        read_only_fields = fields


class RealtimeSessionSerializer(serializers.ModelSerializer):
    """Standard retrieve / list shape. NO session_key."""

    spokesperson_name = serializers.CharField(
        source="spokesperson.name",
        read_only=True,
    )
    tool_invocations = RealtimeToolInvocationSerializer(many=True, read_only=True)

    class Meta:
        model = RealtimeSession
        fields = [
            "id",
            "workspace",
            "spokesperson",
            "spokesperson_name",
            "thread",
            "provider",
            "provider_session_id",
            # provider_session_key INTENTIONALLY OMITTED
            # (contract rule 9).
            "provider_document_id",
            "knowledge_chunk_ids",
            "status",
            "error_message",
            "started_at",
            "ready_at",
            "ended_at",
            "expires_at",
            "cost_estimate_micros",
            "cost_actual_micros",
            "duration_seconds",
            "mock_mode",
            "transcript_asset",
            "created_at",
            "updated_at",
            "tool_invocations",
        ]
        read_only_fields = fields

    def validate_spokesperson(self, spokesperson):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(
            user=request.user,
            workspace=spokesperson.workspace,
        ).exists():
            raise serializers.ValidationError(
                "spokesperson not in your workspaces"
            )
        return spokesperson


class RealtimeSessionWithKeySerializer(RealtimeSessionSerializer):
    """Create-response shape. Adds provider_session_key —
    the SDK needs it to connect. ONLY used as the response to
    a successful POST /api/realtime_sessions/ create call."""

    provider_session_key = serializers.CharField(read_only=True)

    class Meta(RealtimeSessionSerializer.Meta):
        fields = RealtimeSessionSerializer.Meta.fields + ["provider_session_key"]
        read_only_fields = fields
