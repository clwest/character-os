"""URL routing for the realtime API — R3 broker."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import RealtimeSessionViewSet

router = DefaultRouter()
router.register(
    r"realtime_sessions",
    RealtimeSessionViewSet,
    basename="realtime-session",
)

urlpatterns = router.urls
