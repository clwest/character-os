from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin

from .models import Membership, User, Workspace


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    """Custom-User admin. Mirrors Django's stock UserAdmin but keyed
    on email since there's no username column."""

    ordering = ("-date_joined",)
    list_display = ("email", "is_staff", "is_active", "date_joined")
    list_filter = ("is_staff", "is_superuser", "is_active")
    search_fields = ("email",)
    readonly_fields = ("date_joined", "last_login")

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("email", "password1", "password2"),
            },
        ),
    )


@admin.register(Workspace)
class WorkspaceAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "owner", "created_at")
    search_fields = ("name", "slug", "owner__email")
    readonly_fields = ("id", "created_at", "updated_at")
    list_filter = ("created_at",)


@admin.register(Membership)
class MembershipAdmin(admin.ModelAdmin):
    list_display = ("user", "workspace", "role", "created_at")
    list_filter = ("role", "created_at")
    search_fields = ("user__email", "workspace__name")
    readonly_fields = ("created_at",)
