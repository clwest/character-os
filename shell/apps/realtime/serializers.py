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

from .models import EngineConnection, RealtimeSession, RealtimeToolInvocation


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

    # SESSION 256 fix — SET_NULL on teammate deletion
    # (RealtimeSession.spokesperson, models.py:71-74) means the
    # FK can be None; DRF's source-chain walker would SkipField
    # and break the SPA's zod parse (spokesperson_name required
    # string in web/src/lib/api/realtime.ts).
    spokesperson_name = serializers.SerializerMethodField()
    tool_invocations = RealtimeToolInvocationSerializer(many=True, read_only=True)

    def get_spokesperson_name(self, obj) -> str:
        if obj.spokesperson_id and obj.spokesperson:
            return obj.spokesperson.name
        return "(deleted teammate)"

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


# ---- EngineConnection (EB.3) -------------------------------------


class EngineConnectionSerializer(serializers.ModelSerializer):
    """Engine-bridge connection — EB.3 (SESSION 217).

    Token is **write-only over the API** (contract rule 4). The
    serializer accepts ``engine_token`` on POST/PATCH but never
    returns it on GET; instead, ``engine_token_preview`` surfaces
    a redacted *…last4* preview so the SPA can tell the operator
    "you have a token stored" without leaking it.

    Workspace is set from the request user's primary membership at
    create time; the SPA never specifies it. Cross-workspace
    create attempts are blocked by the viewset's get_queryset
    filter + tier gate.
    """

    engine_token = serializers.CharField(write_only=True, required=False)
    engine_token_preview = serializers.SerializerMethodField()
    workspace = serializers.UUIDField(source="workspace_id", read_only=True)

    class Meta:
        model = EngineConnection
        fields = [
            "id",
            "workspace",
            "engine_kind",
            "engine_url",
            "engine_token",
            "engine_token_preview",
            "enabled",
            "label",
            "last_tested_at",
            "last_test_status",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "workspace",
            "engine_token_preview",
            "last_tested_at",
            "last_test_status",
            "created_at",
            "updated_at",
        ]

    def get_engine_token_preview(self, obj) -> str:
        """Render a *…last4* redaction of the stored token. Empty
        string when no token (shouldn't happen post-create; covers
        the edge case of a malformed migration). Never returns the
        full token."""
        token = obj.engine_token or ""
        if not token:
            return ""
        # Always exactly 4 asterisks + at most 4 trailing chars.
        # Short tokens (< 4 chars) show only what's there with the
        # same prefix; this is a configuration error anyway (real
        # bearer tokens are 30+ chars).
        return f"****{token[-4:]}" if len(token) >= 4 else f"****{token}"
