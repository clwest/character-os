"""URL routing for the character-os shell.

Phase 1 — admin + the four core REST endpoints (workspaces,
memberships, spokespeople, videos, conversations). Each app exposes
its own DRF router and gets included here under `/api/`.
"""

from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.spokespeople.urls")),
    path("api/", include("apps.videos.urls")),
    path("api/", include("apps.conversations.urls")),
    # path("api/billing/", include("apps.billing.urls")),
    # path("api/auth/", include("apps.accounts.auth_urls")),  # Google OAuth slice
]
