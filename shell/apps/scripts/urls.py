"""URL routing for the B-2 / E-arc scripts API."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import ScriptViewSet

router = DefaultRouter()
router.register(
    r"scripts",
    ScriptViewSet,
    basename="script",
)

urlpatterns = router.urls
