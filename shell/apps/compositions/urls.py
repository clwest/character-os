"""URL config for the V15 composition REST surface.

SESSION 144 / V15.0.
W11.6.2 / SESSION 173 — added /api/images/ + /api/styles/.

Routes:
  GET    /api/recipes/                  recipe gallery metadata
  GET    /api/recipes/<kind>/           one recipe's metadata
  GET    /api/compositions/             list (workspace-scoped)
  POST   /api/compositions/             create from a recipe
  GET    /api/compositions/<id>/        retrieve one composition
  GET    /api/assets/                   workspace asset library
  GET    /api/images/                   workspace image library (filterable)
  POST   /api/images/                   generate + persist an image
  GET    /api/images/<id>/              retrieve one image
  DELETE /api/images/<id>/              workspace-owner delete
  GET    /api/styles/                   style preset library snapshot
"""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import (
    AssetViewSet,
    CompositionViewSet,
    ImageViewSet,
    RecipeViewSet,
    StyleLibraryViewSet,
)

router = DefaultRouter()
router.register(r"recipes", RecipeViewSet, basename="recipe")
router.register(r"compositions", CompositionViewSet, basename="composition")
router.register(r"assets", AssetViewSet, basename="asset")
router.register(r"images", ImageViewSet, basename="image")
router.register(r"styles", StyleLibraryViewSet, basename="style")

urlpatterns = router.urls
