from django.contrib import admin

from .models import Script


@admin.register(Script)
class ScriptAdmin(admin.ModelAdmin):
    list_display = (
        "id", "workspace", "spokesperson", "name", "status",
        "verification_status", "approved_at", "created_at",
    )
    list_filter = (
        "status", "verification_status", "workspace",
    )
    search_fields = ("name", "prompt")
    readonly_fields = (
        "id", "created_at", "updated_at",
        "tokens_input", "tokens_output", "model",
        "knowledge_chunk_ids", "verification_warnings",
        "revision_history",
    )
    raw_id_fields = ("workspace", "spokesperson", "created_by")
