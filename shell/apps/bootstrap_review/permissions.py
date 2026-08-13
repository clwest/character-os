"""IsOperator — DRF permission for the §19 Step 9.b bootstrap-review
API surface (SESSION 249, 9.b.0).

The bootstrap-review surface is operator-only. The
``bootstrap-fixtures`` workspace has no user memberships by design
(SESSION 249 architecture plan, L1 ratification), so the existing
``IsWorkspaceMember`` gate cannot admit anyone. This permission
authorizes by Django admin flags instead:

    user.is_authenticated and (user.is_staff or user.is_superuser)

Deliberate scope (SESSION 249 L2 ratification):

* No new role, group, entitlement, or "Chris" concept is introduced.
* The authenticated ``User`` remains the reviewer identity recorded in
  review/audit state at 9.b.2+.
* Use only on the internal Step 9.b bootstrap-review API surface —
  never elsewhere.
"""
from __future__ import annotations

from rest_framework.permissions import BasePermission


class IsOperator(BasePermission):
    """Authorize the current request iff the user is authenticated AND
    is either Django staff or a superuser.

    Unauthenticated requests are rejected. Ordinary authenticated
    users (staff=False, superuser=False) are rejected. Staff and
    superuser both pass.
    """

    message = "Operator access required for the §19 Step 9.b bootstrap-review surface."

    def has_permission(self, request, view) -> bool:  # type: ignore[override]
        user = getattr(request, "user", None)
        if user is None or not user.is_authenticated:
            return False
        return bool(user.is_staff or user.is_superuser)

    def has_object_permission(self, request, view, obj) -> bool:  # type: ignore[override]
        # No object-level narrowing needed for 9.b.0 (no objects yet).
        # Later slices attach objects that live in the bootstrap-fixtures
        # workspace; the workspace has no memberships so has_permission's
        # staff/superuser gate is the only admission control.
        return self.has_permission(request, view)
