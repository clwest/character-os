from django.contrib import admin

from .models import PublishBundle, PublishVariant


@admin.register(PublishBundle)
class PublishBundleAdmin(admin.ModelAdmin):
    list_display = (
        "id", "workspace", "name", "status",
        "launched_at", "completed_at", "created_at",
    )
    list_filter = ("status", "workspace")
    search_fields = ("name",)
    readonly_fields = (
        "id", "created_at", "updated_at", "selected_platforms",
    )
    raw_id_fields = ("workspace", "source_clip", "created_by")


@admin.register(PublishVariant)
class PublishVariantAdmin(admin.ModelAdmin):
    list_display = (
        "id", "bundle", "platform_key", "status",
        "produced_composition", "created_at",
    )
    list_filter = ("status", "platform_key", "bundle__workspace")
    readonly_fields = (
        "id", "target_ratio", "max_duration_ms",
        "created_at", "updated_at",
    )
    raw_id_fields = ("bundle", "produced_composition")
