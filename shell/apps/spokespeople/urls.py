"""URL routing for the spokespeople API.

URL path segment ``spokespeople`` and router basename ``spokesperson``
are external contracts (SPA consumes ``/api/spokespeople/`` and code
elsewhere reverses ``spokesperson-list``, ``spokesperson-detail``, and
custom action names). Preserved unchanged per ratified §17.1.b even
after the underlying viewset was renamed to ``TeammateViewSet``.
"""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import TeammateViewSet

router = DefaultRouter()
router.register(r"spokespeople", TeammateViewSet, basename="spokesperson")

urlpatterns = router.urls
