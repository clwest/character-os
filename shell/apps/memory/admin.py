"""Django admin registration for NarrativeMemory.

SESSION 264 Slice 1. Read-oriented admin surface — this app is
operator-facing via the SPA, so the admin is a lightweight
inspection surface for debugging.
"""
from __future__ import annotations

from django.contrib import admin

from .models import NarrativeMemory


@admin.register(NarrativeMemory)
class NarrativeMemoryAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "kind",
        "status",
        "universe",
        "episode",
        "source_composition",
        "created_at",
    )
    list_filter = ("kind", "status", "weight")
    search_fields = ("body", "id")
    autocomplete_fields = (
        "episode",
        "source_composition",
        "workspace",
        "universe",
        "supersedes",
        "promoted_by",
    )
    readonly_fields = ("created_at", "updated_at")
