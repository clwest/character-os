"""URL routing for the Universe API.

SESSION 261 / ``docs/design/UNIVERSE_SCHEMA_V1.md`` §"API
contract". Registered under ``/api/`` from ``character_os/urls.py``.
"""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import UniverseViewSet

router = DefaultRouter()
router.register(r"universes", UniverseViewSet, basename="universe")

urlpatterns = router.urls
