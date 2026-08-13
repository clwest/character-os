"""URL routing for the character-os shell.

Phase 1 — admin + the four core REST endpoints (workspaces,
memberships, spokespeople, videos, conversations). Each app exposes
its own DRF router and gets included here under `/api/`.
"""

from django.contrib import admin
from django.urls import include, path

from character_os.api_prompts import suggest_tone

urlpatterns = [
    path("admin/", admin.site.urls),
    # allauth — /accounts/login/, /accounts/signup/, /accounts/google/login/,
    # /accounts/password/reset/, /accounts/logout/, etc.
    path("accounts/", include("allauth.urls")),
    # allauth.headless — JSON-API surface consumed by the SPA. Lives
    # under /_allauth/ so /accounts/ stays the HTML surface; the two
    # coexist during the Phase 3 SPA transition.
    path("_allauth/", include("allauth.headless.urls")),
    # REST API — one path("api/", …) per app router.
    path("api/", include("apps.accounts.urls")),
    path("api/", include("apps.spokespeople.urls")),
    path("api/", include("apps.videos.urls")),
    path("api/", include("apps.conversations.urls")),
    path("api/", include("apps.billing.urls")),
    path("api/", include("apps.embeddings.urls")),
    path("api/", include("apps.compositions.urls")),
    path("api/", include("apps.realtime.urls")),
    path("api/", include("apps.transcripts.urls")),
    path("api/", include("apps.campaigns.urls")),
    path("api/", include("apps.publish.urls")),
    path("api/", include("apps.scripts.urls")),
    # §19 Step 9.b bootstrap-review (SESSION 249, 9.b.0). Operator-only.
    path("api/", include("apps.bootstrap_review.urls")),
    # Thin wrappers around character_os.prompts helpers (SESSION 129).
    path("api/prompts/suggest-tone/", suggest_tone, name="suggest-tone"),
]
