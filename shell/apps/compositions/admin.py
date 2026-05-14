"""Admin registration for the composition layer.

SESSION 142 / V1. Read-only-ish admin — operators inspect
rows here while we build out the SPA surfaces. Mutations
should flow through the runtime (V2+); admin edits are
intentionally narrow.
"""
from __future__ import annotations

from django.contrib import admin

from .models import Asset, Composition, CompositionStep


@admin.register(Asset)
class AssetAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "asset_type",
        "workspace",
        "composition",
        "mime_type",
        "duration_ms",
        "cost_micros",
        "created_at",
    )
    list_filter = ("asset_type", "workspace")
    search_fields = ("id", "file_path", "mime_type")
    readonly_fields = (
        "id",
        "source_spec",
        "cost_micros",
        "created_by",
        "created_at",
    )
    raw_id_fields = ("workspace", "composition")
    ordering = ("-created_at",)


class CompositionStepInline(admin.TabularInline):
    model = CompositionStep
    extra = 0
    fields = (
        "position",
        "primitive",
        "status",
        "cost_estimate_micros",
        "cost_actual_micros",
        "elapsed_ms",
        "media_engine_task_id",
        "error_message",
    )
    readonly_fields = fields
    show_change_link = True
    ordering = ("position",)


@admin.register(Composition)
class CompositionAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "name",
        "workspace",
        "spokesperson",
        "template_kind",
        "status",
        "mock_mode",
        "cost_estimate_micros",
        "cost_actual_micros",
        "created_at",
    )
    list_filter = ("status", "template_kind", "mock_mode", "workspace")
    search_fields = ("id", "name")
    readonly_fields = (
        "id",
        "knowledge_chunk_ids",
        "cost_estimate_micros",
        "cost_actual_micros",
        "created_by",
        "created_at",
        "updated_at",
    )
    raw_id_fields = ("workspace", "spokesperson", "final_asset")
    inlines = [CompositionStepInline]
    ordering = ("-created_at",)


@admin.register(CompositionStep)
class CompositionStepAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "composition",
        "position",
        "primitive",
        "status",
        "cost_estimate_micros",
        "cost_actual_micros",
        "elapsed_ms",
    )
    list_filter = ("status", "primitive")
    search_fields = ("id", "primitive", "media_engine_task_id")
    readonly_fields = (
        "id",
        "inputs",
        "params",
        "cost_estimate_micros",
        "cost_actual_micros",
        "elapsed_ms",
        "media_engine_task_id",
        "started_at",
        "completed_at",
    )
    raw_id_fields = ("composition", "output_asset")
    ordering = ("composition", "position")
