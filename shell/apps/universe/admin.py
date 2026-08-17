from django.contrib import admin

from .models import Universe


@admin.register(Universe)
class UniverseAdmin(admin.ModelAdmin):
    """Admin surface for the Universe substrate. Read-heavy —
    creation and archive happen through the operator SPA, not
    the admin (SESSION 261 discipline: explicit-only canon)."""

    list_display = (
        "name",
        "workspace",
        "slug",
        "archived_at",
        "created_at",
    )
    list_filter = ("workspace", "archived_at")
    search_fields = ("name", "slug", "workspace__name")
    readonly_fields = ("id", "slug", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "workspace", "name", "slug")}),
        ("Prose", {"fields": ("description",)}),
        ("Lifecycle", {"fields": ("archived_at", "created_at", "updated_at")}),
        ("Audit", {"fields": ("created_by",)}),
    )
