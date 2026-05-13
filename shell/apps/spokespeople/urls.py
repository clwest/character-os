"""URL routing for the spokespeople API."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import SpokespersonViewSet

router = DefaultRouter()
router.register(r"spokespeople", SpokespersonViewSet, basename="spokesperson")

urlpatterns = router.urls
