from django.contrib import admin

from .models import Spokesperson


@admin.register(Spokesperson)
class SpokespersonAdmin(admin.ModelAdmin):
    list_display = ("name", "workspace", "status", "runway_avatar_status", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("name", "workspace__name", "business_brief")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "workspace", "name", "status")}),
        ("Brief", {"fields": ("business_brief",)}),
        (
            "Media engine",
            {
                "fields": (
                    "runway_avatar_id",
                    "runway_avatar_status",
                    "portrait_path",
                    "voice_id",
                ),
                "classes": ("collapse",),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
