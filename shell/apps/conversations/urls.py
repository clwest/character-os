"""URL routing for the conversations API."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import ConversationThreadViewSet

router = DefaultRouter()
router.register(r"conversations", ConversationThreadViewSet, basename="conversation")

urlpatterns = router.urls
