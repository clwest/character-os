"""Cross-workspace validation for the campaigns arc.

B3.2 (SESSION 203). Mirrors ``apps.realtime.signals`` +
``apps.transcripts.signals``. ``clean()`` catches the form /
``full_clean()`` paths; this signal catches the raw ``.save()``
path which doesn't run ``clean()`` by default.

The leak shapes eliminated by construction:
* PersonalizedCampaign whose ``spokesperson`` belongs to a
  different workspace.
* PersonalizedRecipient whose ``produced_composition``
  belongs to a different workspace than its
  campaign.workspace.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import PersonalizedCampaign, PersonalizedRecipient

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=PersonalizedCampaign)
def reject_cross_workspace_campaign_refs(
    sender,
    instance: PersonalizedCampaign,
    **kwargs,
) -> None:
    """Veto a campaign whose spokesperson lives in another
    workspace.

    Skips state-only updates (status / launched_at /
    completed_at).
    """
    if not instance.workspace_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {"workspace", "spokesperson"}
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        raise


@receiver(pre_save, sender=PersonalizedRecipient)
def reject_cross_workspace_recipient_refs(
    sender,
    instance: PersonalizedRecipient,
    **kwargs,
) -> None:
    """Veto a recipient whose produced_composition lives in
    another workspace.

    Skips state-only updates (status / error_message /
    rendered_script).
    """
    if not instance.campaign_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {"campaign", "produced_composition"}
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        raise
