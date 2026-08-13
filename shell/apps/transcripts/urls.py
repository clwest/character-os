"""URL routing for the B-arc transcript miner."""
from __future__ import annotations

from rest_framework.routers import DefaultRouter

from .views import TranscriptHighlightViewSet

router = DefaultRouter()
router.register(
    r"transcript_highlights",
    TranscriptHighlightViewSet,
    basename="transcript-highlight",
)

urlpatterns = router.urls
