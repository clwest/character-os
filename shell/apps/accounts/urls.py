"""URL routing for the accounts API."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import MembershipViewSet, WorkspaceViewSet

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"memberships", MembershipViewSet, basename="membership")

urlpatterns = router.urls
