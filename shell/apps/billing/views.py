"""Billing API — subscription + usage meter for the SPA."""
from __future__ import annotations

from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from apps.accounts.models import Membership, Workspace, default_workspace_for

from .models import TIER_LIMITS
from .services import get_usage


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def subscription(request: Request) -> Response:
    """Subscription + usage for the requesting user's workspace.

    Query param: ``?workspace=<uuid>`` to target a specific workspace
    they're a member of. Defaults to their primary workspace if
    omitted — what the SPA dashboard wants on the home screen.
    """
    user = request.user
    workspace = _resolve_workspace(request, user)
    if workspace is None:
        return Response(
            {"error": "no workspace accessible for this user"},
            status=404,
        )

    usage = get_usage(workspace)
    return Response(
        {
            "workspace_id": str(workspace.id),
            "workspace_name": workspace.name,
            **usage.to_dict(),
        }
    )


@api_view(["GET"])
@permission_classes([AllowAny])
def tiers(request: Request) -> Response:
    """Public tier catalogue. Drives the pricing-page table + upgrade
    modal. No auth required so the marketing site can hit it."""
    rows = [
        {"id": tier_id, **limits} for tier_id, limits in TIER_LIMITS.items()
    ]
    return Response({"tiers": rows})


def _resolve_workspace(request: Request, user) -> Workspace | None:
    workspace_id = request.query_params.get("workspace")
    if workspace_id:
        ws = Workspace.objects.filter(pk=workspace_id).first()
        if ws is None:
            return None
        if Membership.objects.filter(user=user, workspace=ws).exists():
            return ws
        return None
    return default_workspace_for(user)
