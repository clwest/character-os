from django.contrib import admin

from .models import (
    ConversationEmbedding,
    ConversationMessage,
    ConversationThread,
)


@admin.register(ConversationThread)
class ConversationThreadAdmin(admin.ModelAdmin):
    list_display = ("__str__", "spokesperson", "created_at", "last_activity_at")
    search_fields = ("title", "spokesperson__name")
    readonly_fields = ("id", "created_at", "last_activity_at")
    list_filter = ("created_at",)


@admin.register(ConversationMessage)
class ConversationMessageAdmin(admin.ModelAdmin):
    list_display = ("thread", "role", "created_at")
    list_filter = ("role",)
    search_fields = ("content", "thread__title")
    readonly_fields = ("id", "created_at")
    raw_id_fields = ("thread",)


@admin.register(ConversationEmbedding)
class ConversationEmbeddingAdmin(admin.ModelAdmin):
    list_display = ("message", "chunk_index", "chunk_size", "embedding_model", "created_at")
    list_filter = ("embedding_model",)
    readonly_fields = ("id", "embedding_vector", "embedding_model", "created_at")
    raw_id_fields = ("message",)
