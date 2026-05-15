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

from .models import RealtimeSession, RealtimeToolInvocation


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
