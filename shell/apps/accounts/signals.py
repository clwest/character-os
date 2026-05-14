"""Auto-Workspace bootstrap signal.

Every freshly created User gets a default Workspace + an owner-role
Membership in one transaction. Triggers on User.post_save when
``created=True``, regardless of which auth path created them — email/
password, Google OAuth, Django admin, or a management-shell call.

The workspace name defaults to a friendly form of the user's email
prefix (``alice@example.com`` → ``"Alice's workspace"``). Operators
can rename it via the SPA later.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Membership, Workspace

logger = logging.getLogger(__name__)


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def ensure_default_workspace(sender, instance, created, **kwargs) -> None:
    if not created:
        return
    if Workspace.objects.filter(owner=instance).exists():
        # Defensive — should never happen on the create branch, but if
        # a fixture or test pre-creates a workspace under this user the
        # signal must be idempotent.
        return

    with transaction.atomic():
        name = _suggested_workspace_name(instance)
        workspace = Workspace.objects.create(name=name, owner=instance)
        Membership.objects.create(
            user=instance,
            workspace=workspace,
            role=Membership.Role.OWNER,
        )
    logger.info(
        "auto-created workspace=%s for user=%s",
        workspace.slug,
        instance.email,
    )


def _suggested_workspace_name(user) -> str:
    """Build a friendly workspace name from the user's email. The
    custom User model (SESSION 119) makes email the sole identifier,
    so the previous ``username`` fallback is gone."""
    email = (getattr(user, "email", "") or "").strip()
    if email and "@" in email:
        prefix = email.split("@", 1)[0]
        return f"{prefix.capitalize()}'s workspace"
    return "My workspace"
