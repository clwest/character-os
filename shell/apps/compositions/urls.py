"""URL config for the V15 composition REST surface.

SESSION 144 / V15.0.

Routes:
  GET    /api/recipes/                  recipe gallery metadata
  GET    /api/recipes/<kind>/           one recipe's metadata
  GET    /api/compositions/             list (workspace-scoped)
  POST   /api/compositions/             create from a recipe
  GET    /api/compositions/<id>/        retrieve one composition
"""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import AssetViewSet, CompositionViewSet, RecipeViewSet

router = DefaultRouter()
router.register(r"recipes", RecipeViewSet, basename="recipe")
router.register(r"compositions", CompositionViewSet, basename="composition")
router.register(r"assets", AssetViewSet, basename="asset")

urlpatterns = router.urls
