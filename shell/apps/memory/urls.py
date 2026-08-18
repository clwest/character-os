"""URL routing for the NarrativeMemory API.

SESSION 264 Slice 1. Registered under ``/api/`` from
``character_os/urls.py``. Mounts
``/api/narrative-memories/`` for list/retrieve/archive/unarchive.

The promote-from-composition action lives on the
``CompositionViewSet`` at
``/api/compositions/<id>/promote-narrative-memory/``.
"""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import NarrativeMemoryViewSet

router = DefaultRouter()
router.register(
    r"narrative-memories",
    NarrativeMemoryViewSet,
    basename="narrative-memory",
)

urlpatterns = router.urls
