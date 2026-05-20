from django.contrib import admin

from .models import PersonalizedCampaign, PersonalizedRecipient


@admin.register(PersonalizedCampaign)
class PersonalizedCampaignAdmin(admin.ModelAdmin):
    list_display = (
        "id", "workspace", "name", "status",
        "launched_at", "completed_at", "created_at",
    )
    list_filter = ("status", "workspace")
    search_fields = ("name", "template")
    readonly_fields = ("id", "created_at", "updated_at", "placeholders")
    raw_id_fields = ("workspace", "spokesperson", "created_by")


@admin.register(PersonalizedRecipient)
class PersonalizedRecipientAdmin(admin.ModelAdmin):
    list_display = (
        "id", "campaign", "label", "status",
        "produced_composition", "position", "created_at",
    )
    list_filter = ("status", "campaign__workspace")
    search_fields = ("label", "rendered_script")
    readonly_fields = (
        "id", "rendered_script", "created_at", "updated_at",
    )
    raw_id_fields = ("campaign", "produced_composition")
