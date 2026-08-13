"""Shared DRF permission classes for workspace-scoped resources.

The multi-tenant boundary is enforced here: every workspace-owned
resource (Workspace, Teammate, Video, ConversationThread) is
queryable only by users who have a Membership in the workspace.

v1 rule: any Membership role can read; only ``owner`` can write or
delete. Refine when the Agency tier ships and ``admin`` / ``editor``
roles get meaningful UI.
"""
from __future__ import annotations

from rest_framework.permissions import SAFE_METHODS, BasePermission

from apps.accounts.models import Membership


class IsWorkspaceMember(BasePermission):
    """Allow access when the user has a Membership in the workspace
    the object belongs to. Read-only methods (GET/HEAD/OPTIONS) require
    any role; mutating methods require ``Role.OWNER``.

    Object resolution — works for objects with either:
      - ``.workspace`` attribute (direct FK), or
      - ``.spokesperson.workspace`` chain (indirect FK).
    """

    def has_permission(self, request, view) -> bool:
        # List + create both need an authenticated user; per-object
        # membership check happens in has_object_permission for the
        # detail routes, and queryset filtering keeps lists scoped.
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj) -> bool:
        workspace = _workspace_of(obj)
        if workspace is None:
            return False
        try:
            membership = Membership.objects.get(user=request.user, workspace=workspace)
        except Membership.DoesNotExist:
            return False
        if request.method in SAFE_METHODS:
            return True
        return membership.role == Membership.Role.OWNER


def _workspace_of(obj):
    """Resolve the workspace an object belongs to.

    Knows how to traverse the FK chain for the four core model shapes.
    Returns ``None`` if the object isn't workspace-scoped (e.g., a User).
    """
    # Import lazily to avoid circular import on module load.
    from apps.accounts.models import Workspace

    if isinstance(obj, Workspace):
        return obj
    workspace = getattr(obj, "workspace", None)
    if workspace is not None:
        return workspace
    spokesperson = getattr(obj, "spokesperson", None)
    if spokesperson is not None:
        return getattr(spokesperson, "workspace", None)
    return None
