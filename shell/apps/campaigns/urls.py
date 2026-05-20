"""URL routing for the C-arc personalized-video API."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import CampaignViewSet

router = DefaultRouter()
router.register(
    r"campaigns",
    CampaignViewSet,
    basename="campaign",
)

urlpatterns = router.urls
