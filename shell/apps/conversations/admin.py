from django.contrib import admin

from .models import ConversationThread


@admin.register(ConversationThread)
class ConversationThreadAdmin(admin.ModelAdmin):
    list_display = ("__str__", "spokesperson", "created_at", "last_activity_at")
    search_fields = ("title", "spokesperson__name")
    readonly_fields = ("id", "created_at", "last_activity_at")
    list_filter = ("created_at",)
