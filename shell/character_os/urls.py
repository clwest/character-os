"""URL routing for the character-os shell.

Phase 1 scaffold — only the admin is wired up. Per-app routers land
in their own slices via include() as the apps fill in.
"""

from django.contrib import admin
from django.urls import path

urlpatterns = [
    path("admin/", admin.site.urls),
    # path("api/accounts/", include("apps.accounts.urls")),
    # path("api/spokespeople/", include("apps.spokespeople.urls")),
    # path("api/videos/", include("apps.videos.urls")),
    # path("api/conversations/", include("apps.conversations.urls")),
    # path("api/billing/", include("apps.billing.urls")),
]
