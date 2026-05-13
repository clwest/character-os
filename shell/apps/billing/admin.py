from django.contrib import admin

from .models import Subscription


@admin.register(Subscription)
class SubscriptionAdmin(admin.ModelAdmin):
    list_display = (
        "workspace",
        "tier",
        "status",
        "current_period_start",
        "current_period_end",
    )
    list_filter = ("tier", "status")
    search_fields = ("workspace__name", "stripe_customer_id", "stripe_subscription_id")
    readonly_fields = ("id", "created_at", "updated_at")
    fieldsets = (
        (None, {"fields": ("id", "workspace", "tier", "status")}),
        (
            "Billing period",
            {"fields": ("current_period_start", "current_period_end")},
        ),
        (
            "Stripe",
            {
                "fields": ("stripe_customer_id", "stripe_subscription_id"),
                "classes": ("collapse",),
            },
        ),
        ("Timestamps", {"fields": ("created_at", "updated_at")}),
    )
