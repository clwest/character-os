from django.contrib import admin

from .models import Episode, EpisodeCast, Universe


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


class EpisodeCastInline(admin.TabularInline):
    """Inline cast table on the Episode admin.

    Read-only in admin — cast mutation is operator-authoritative
    and happens through the SPA (EPISODE_SCHEMA_V1 §Q6). Admin
    can still delete rows if a support engineer needs to detach a
    cast attachment manually.
    """
    model = EpisodeCast
    extra = 0
    fields = ("teammate", "added_at")
    readonly_fields = ("added_at",)
    autocomplete_fields = ("teammate",)


@admin.register(Episode)
class EpisodeAdmin(admin.ModelAdmin):
    """Admin surface for Episode (SESSION 262). Read-heavy;
    creation + archive happen through the SPA. Cast is inline
    (see EpisodeCastInline)."""

    list_display = (
        "title",
        "universe",
        "archived_at",
        "created_at",
    )
    list_filter = ("universe", "archived_at")
    search_fields = ("title", "operator_topic", "universe__name")
    readonly_fields = ("id", "created_at", "updated_at")
    inlines = [EpisodeCastInline]
    fieldsets = (
        (None, {"fields": ("id", "universe", "title")}),
        ("Story intent", {"fields": ("operator_topic",)}),
        ("Lifecycle", {"fields": ("archived_at", "created_at", "updated_at")}),
        ("Audit", {"fields": ("created_by",)}),
    )


@admin.register(EpisodeCast)
class EpisodeCastAdmin(admin.ModelAdmin):
    list_display = ("episode", "teammate", "added_at")
    list_filter = ("episode__universe",)
    search_fields = (
        "episode__title", "teammate__name", "episode__universe__name",
    )
    readonly_fields = ("id", "added_at")
    autocomplete_fields = ("episode", "teammate")
