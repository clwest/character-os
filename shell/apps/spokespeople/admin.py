from django.contrib import admin

from .models import Teammate


@admin.register(Teammate)
class TeammateAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "status", "runway_avatar_status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "workspace__name", "business_brief")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "workspace", "name", "status")}),
        ("Brief", {"fields": ("business_brief",)}),
        (
            "Identity",
            {
                "fields": (
                    "who_you_help",
                    "what_you_sell",
                    "always_emphasize",
                    "never_say",
                    "desired_feeling",
                ),
            },
        ),
        (
            "Character Voice",
            {
                "fields": (
                    "personality",
                    "tone_archetype",
                    "character_point_of_view",
                    "voice_energy",
                    "voice_humor",
                    "voice_directness",
                    "voice_signature_phrases",
                    "voice_avoid_phrases",
                ),
            },
        ),
        (
            "Media engine",
            {
                "fields": (
                    "runway_avatar_id",
                    "runway_avatar_status",
                    "portrait_path",
                    "voice_id",
                    "visual_subject",
                    "visual_template",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
