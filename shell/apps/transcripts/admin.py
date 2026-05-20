from django.contrib import admin

from .models import TranscriptHighlight


@admin.register(TranscriptHighlight)
class TranscriptHighlightAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "workspace",
        "status",
        "char_start",
        "char_end",
        "mined_at",
        "decided_at",
    )
    list_filter = ("status", "workspace", "llm_model_id")
    search_fields = ("text", "llm_reasoning")
    readonly_fields = (
        "id",
        "mined_at",
        "decided_at",
        "llm_model_id",
        "llm_cost_micros",
        "llm_tokens_input",
        "llm_tokens_output",
    )
    raw_id_fields = ("workspace", "source_transcript", "produced_composition")
