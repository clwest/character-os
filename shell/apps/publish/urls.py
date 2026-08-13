"""URL routing for the D-arc publish-bundle API."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import PublishBundleViewSet

router = DefaultRouter()
router.register(
    r"publish_bundles",
    PublishBundleViewSet,
    basename="publish-bundle",
)

urlpatterns = router.urls
