from django.contrib import admin

from .models import Video


@admin.register(Video)
class VideoAdmin(admin.ModelAdmin):
    list_display = ("__str__", "spokesperson", "kind", "status", "duration_seconds", "created_at")
    list_filter = ("kind", "status", "created_at")
    search_fields = (
        "title",
        "brief",
        "spokesperson__name",
        "spokesperson__workspace__name",
    )
    readonly_fields = ("id", "created_at", "updated_at", "completed_at")
    fieldsets = (
        (None, {"fields": ("id", "spokesperson", "title", "kind", "status")}),
        ("Brief", {"fields": ("brief", "tags")}),
        (
            "Output",
            {
                "fields": (
                    "output_path",
                    "duration_seconds",
                    "media_engine_task_id",
                    "error_message",
                )
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at", "completed_at")}),
    )
