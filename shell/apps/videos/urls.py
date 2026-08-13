"""URL routing for the videos API."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import VideoViewSet

router = DefaultRouter()
router.register(r"videos", VideoViewSet, basename="video")

urlpatterns = router.urls
