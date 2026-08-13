"""Admin registration for the realtime arc.

R1 ships read-mostly admin so operators / on-call can
inspect session state during incident response. Edit paths
go through ``full_clean()`` which runs the cross-workspace
validation.

``provider_session_key`` is excluded from list/search/detail
display per contract rule 9 (the SDK connect token is
treated as a secret).
"""
from __future__ import annotations

from django.contrib import admin

from .models import EngineConnection, RealtimeSession, RealtimeToolInvocation


@admin.register(RealtimeSession)
class RealtimeSessionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workspace",
        "spokesperson",
        "provider",
        "status",
        "mock_mode",
        "duration_seconds",
        "created_at",
    )
    list_filter = ("provider", "status", "mock_mode")
    search_fields = ("id", "provider_session_id", "error_message")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "started_at",
        "ready_at",
        "ended_at",
        # Hide the SDK connect token in admin (contract
        # rule 9 — never display in human-readable UI).
        "provider_session_key",
    )
    raw_id_fields = ("workspace", "spokesperson", "thread", "transcript_asset", "created_by")
    ordering = ("-created_at",)

    def get_exclude(self, request, obj=None):
        # Defensive: even the form view should not surface
        # the session key. ``readonly_fields`` shows but
        # disables; we want it hidden.
        return ("provider_session_key",)


@admin.register(RealtimeToolInvocation)
class RealtimeToolInvocationAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "session",
        "tool_name",
        "status",
        "invoked_at",
        "completed_at",
    )
    list_filter = ("status", "tool_name")
    search_fields = ("id", "tool_name", "error_message")
    readonly_fields = ("id", "invoked_at", "completed_at")
    raw_id_fields = ("session", "produced_asset", "produced_composition")
    ordering = ("-invoked_at",)


@admin.register(EngineConnection)
class EngineConnectionAdmin(admin.ModelAdmin):
    """Engine-bridge config admin. EB.1 (SESSION 217).

    ``engine_token`` is masked in list display + excluded from the
    detail form per contract rule 4 (write-only over the surface).
    On-call / admins inspect connections to verify URL + kind +
    enabled state; rotating a token goes through the SPA admin UI
    or a Django shell — never the admin form (which doesn't redact
    on read).
    """

    list_display = (
        "id",
        "workspace",
        "engine_kind",
        "engine_url",
        "enabled",
        "last_test_status",
        "last_tested_at",
        "created_at",
    )
    list_filter = ("engine_kind", "enabled")
    search_fields = ("id", "engine_url", "label", "workspace__name")
    readonly_fields = (
        "id",
        "created_at",
        "updated_at",
        "last_tested_at",
        "last_test_status",
    )
    raw_id_fields = ("workspace",)
    ordering = ("-created_at",)

    def get_exclude(self, request, obj=None):
        # Hide the token from the admin form entirely — admins
        # should not see existing tokens in plaintext, and should
        # not paste new ones into the admin UI (rule 4 — SPA only).
        return ("engine_token",)
