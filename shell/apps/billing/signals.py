"""Auto-Subscription bootstrap signal.

Every newly created Workspace gets a default Starter-tier Subscription
in trialing status. Keeps the tier-limit middleware able to assume
"every workspace has a subscription" without null-checks everywhere.
"""
from __future__ import annotations

import logging

from django.db.models.signals import post_save
from django.dispatch import receiver

from apps.accounts.models import Workspace

from .models import Subscription

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Workspace)
def ensure_default_subscription(sender, instance, created, **kwargs) -> None:
    if not created:
        return
    if Subscription.objects.filter(workspace=instance).exists():
        return
    Subscription.objects.create(
        workspace=instance,
        tier=Subscription.Tier.STARTER,
        status=Subscription.Status.TRIALING,
    )
    logger.info(
        "auto-created Starter subscription for workspace=%s",
        instance.slug,
    )
