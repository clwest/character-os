"""URL routing for the billing API."""
from __future__ import annotations

from django.urls import path

from .views import subscription, tiers

urlpatterns = [
    path("billing/subscription/", subscription, name="billing-subscription"),
    path("billing/tiers/", tiers, name="billing-tiers"),
]
