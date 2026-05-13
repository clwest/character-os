from django.contrib import admin

from .models import Membership, Workspace


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    search_fields = ("name", "slug", "owner__username", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at")
    list_filter = ("created_at",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "workspace", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("user__username", "user__email", "workspace__name")
    readonly_fields = ("created_at",)
