"""URL config for the V15 composition REST surface.

SESSION 144 / V15.0.
W11.6.2 / SESSION 173 — added /api/images/ + /api/styles/.
A4 / SESSION 188 — added /api/workspace/assets/ Asset Library v1 reads.

Routes:
  GET    /api/recipes/                  recipe gallery metadata
  GET    /api/recipes/<kind>/           one recipe's metadata
  GET    /api/compositions/             list (workspace-scoped)
  POST   /api/compositions/             create from a recipe
  GET    /api/compositions/<id>/        retrieve one composition
  GET    /api/assets/                   workspace asset picker (V15.2)
  GET    /api/workspace/assets/         Asset Library v1 browse (A4)
  GET    /api/workspace/assets/<id>/    Asset Library v1 detail (A4)
  GET    /api/images/                   workspace image library (filterable)
  POST   /api/images/                   generate + persist an image
  GET    /api/images/<id>/              retrieve one image
  DELETE /api/images/<id>/              workspace-owner delete
  GET    /api/styles/                   style preset library snapshot
"""
from __future__ import annotations

from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import (
    AssetViewSet,
    CompositionViewSet,
    ImageViewSet,
    RecipeViewSet,
    StyleLibraryViewSet,
    WorkspaceAssetViewSet,
)

router = DefaultRouter()
router.register(r"recipes", RecipeViewSet, basename="recipe")
router.register(r"compositions", CompositionViewSet, basename="composition")
router.register(r"assets", AssetViewSet, basename="asset")
router.register(r"images", ImageViewSet, basename="image")
router.register(r"styles", StyleLibraryViewSet, basename="style")


# Asset Library v1 (A4) lives at /api/workspace/assets/ — a different
# URL space from /api/assets/ (which serves the V15.2 asset_picker).
# Hand-mounted because DefaultRouter doesn't compose well with a
# leading prefix; the viewset has list + retrieve only, no other
# REST verbs, so two explicit paths are clearer than a router.
_workspace_asset_list = WorkspaceAssetViewSet.as_view({"get": "list"})
_workspace_asset_detail = WorkspaceAssetViewSet.as_view({"get": "retrieve"})

urlpatterns = [
    path(
        "workspace/assets/",
        _workspace_asset_list,
        name="workspace-asset-list",
    ),
    path(
        "workspace/assets/<uuid:pk>/",
        _workspace_asset_detail,
        name="workspace-asset-detail",
    ),
    *router.urls,
]
