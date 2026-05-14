"""Thin DRF wrappers around ``character_os.prompts`` helpers.

The ``character_os.prompts`` package is intentionally pure-Python
(no Django imports). When the SPA needs to reach those helpers over
HTTP, the Django-aware glue lives here so the package stays clean.

Today the surface is a single endpoint:

  - ``GET /api/prompts/suggest-tone/?brief=<text>`` —
    returns ``{tone: "expert" | "tutor" | "authority" | "friend" |
    "performer"}`` from ``suggest_tone_from_brief()``.

All endpoints require an authenticated workspace member. The helpers
are stateless, so per-user rate limiting isn't necessary at v1 —
add if abuse appears.
"""
from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from character_os.prompts import suggest_tone_from_brief

# Cap on inbound brief length — guards against pathological inputs
# that the helper would scan over a megabyte. The wizard's brief is
# capped to 4 000 chars on the client; keep some headroom.
_MAX_BRIEF_CHARS = 8_000


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def suggest_tone(request: Request) -> Response:
    """``GET /api/prompts/suggest-tone/?brief=<text>``.

    Returns the inferred tone archetype for the supplied brief, or
    the default (``"expert"``) when no keywords match / brief is
    empty.

    Response shape::

        {"tone": "expert"}

    Always returns 200 with one of the five archetypes — there is
    no error path beyond "auth required" and "too-long brief"
    (400 ``brief_too_long``).
    """
    brief = request.query_params.get("brief", "")
    if len(brief) > _MAX_BRIEF_CHARS:
        return Response(
            {
                "error": (
                    f"brief is too long ({len(brief)} chars; "
                    f"max {_MAX_BRIEF_CHARS})."
                ),
                "code": "brief_too_long",
            },
            status=400,
        )
    return Response({"tone": suggest_tone_from_brief(brief)})
