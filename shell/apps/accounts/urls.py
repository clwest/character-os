"""URL routing for the accounts API."""
from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import MembershipViewSet, WorkspaceViewSet, me, workspace_overview

router = DefaultRouter()
router.register(r"workspaces", WorkspaceViewSet, basename="workspace")
router.register(r"memberships", MembershipViewSet, basename="membership")

urlpatterns = [
    path("me/", me, name="me"),
    path("workspace/overview/", workspace_overview, name="workspace-overview"),
    *router.urls,
]
