"""URL routing for the knowledge layer API.

SESSION 138 / K4. Registered under ``/api/`` from
``character_os/urls.py``:

  /api/knowledge/        list + create
  /api/knowledge/<id>/   detail + update + (soft) delete
"""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import KnowledgeDocumentViewSet

router = DefaultRouter()
router.register(r"knowledge", KnowledgeDocumentViewSet, basename="knowledge")

urlpatterns = router.urls
