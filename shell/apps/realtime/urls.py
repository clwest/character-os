"""URL routing for the realtime API — R3 broker + R7.0 tool
dispatch surface."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import RealtimeSessionViewSet, RealtimeToolInvocationViewSet

router = DefaultRouter()
router.register(
    r"realtime_sessions",
    RealtimeSessionViewSet,
    basename="realtime-session",
)
router.register(
    r"realtime_tool_invocations",
    RealtimeToolInvocationViewSet,
    basename="realtime-tool-invocation",
)

urlpatterns = router.urls
