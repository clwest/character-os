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
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from apps.compositions.models import Composition, CompositionStatus

from .models import PersonalizedCampaign, PersonalizedRecipient

logger = logging.getLogger(__name__)


# Composition statuses we treat as terminal for B3.6 purposes.
# COMPLETED -> recipient COMPLETED; FAILED / PARTIAL ->
# recipient FAILED with the composition's error_message.
_TERMINAL_SUCCESS = {CompositionStatus.COMPLETED}
_TERMINAL_FAILURE = {
    CompositionStatus.FAILED,
    CompositionStatus.PARTIAL,
}


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
        # BC1 — include source_script in validated_fields so a
        # source_script update on an existing campaign triggers
        # the workspace check.
        validated_fields = {"workspace", "spokesperson", "source_script"}
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


@receiver(post_save, sender=Composition)
def flip_recipient_on_composition_completion(
    sender,
    instance: Composition,
    update_fields=None,
    created: bool = False,
    **kwargs,
) -> None:
    """B3.6 — when a per-recipient composition reaches a
    terminal status, flip the linked recipient row + roll up
    the campaign status.

    Mirrors the B-arc's post_save receiver shape (cheap
    filter + lazy lookup) but with richer state transitions:
    COMPLETED → recipient COMPLETED + campaign rollup;
    FAILED / PARTIAL → recipient FAILED + campaign rollup.

    Idempotent — re-running on an already-terminal recipient
    is a no-op (the update is guarded by current_status).
    """
    if created:
        # First save is at status DRAFT — never a terminal
        # transition.
        return

    if update_fields is not None and "status" not in update_fields:
        return

    is_success = instance.status in _TERMINAL_SUCCESS
    is_failure = instance.status in _TERMINAL_FAILURE
    if not (is_success or is_failure):
        return

    # Lazy import the campaign rollup helper — apps.campaigns
    # depends on apps.compositions transitively via models, so
    # putting this at the top of the module is fine, but
    # keeping the rollup import lazy mirrors the B-arc style
    # and helps when the apps graph reorders.
    from .services import rollup_campaign_status

    # Find any recipient row pointing at this composition.
    # The relation lives on PersonalizedRecipient via the
    # ``source_recipients`` reverse-name on
    # Composition.source_recipients (see model definition).
    recipients = list(
        PersonalizedRecipient.objects
        .filter(produced_composition=instance)
        # Skip already-terminal rows — idempotency.
        .exclude(status__in=[
            PersonalizedRecipient.Status.COMPLETED,
            PersonalizedRecipient.Status.FAILED,
        ])
        .select_related("campaign")
    )
    if not recipients:
        return

    new_status = (
        PersonalizedRecipient.Status.COMPLETED
        if is_success
        else PersonalizedRecipient.Status.FAILED
    )
    # Capture the composition's error message for FAILED
    # transitions so the SPA can render it.
    error_message = "" if is_success else (instance.error_message or "")[:500]

    seen_campaigns = set()
    for recipient in recipients:
        recipient.status = new_status
        if not is_success:
            recipient.error_message = error_message
        recipient.save(update_fields=[
            "status", "error_message", "updated_at",
        ])
        seen_campaigns.add(recipient.campaign_id)

    # Roll up each touched campaign. Usually exactly one;
    # multi-campaign pointing at the same composition would
    # be a data-shape oddity but we handle it cleanly.
    for campaign in PersonalizedCampaign.objects.filter(
        pk__in=seen_campaigns,
    ):
        flipped = rollup_campaign_status(campaign)
        if flipped:
            logger.info(
                "campaign %s rolled up to %s after composition %s "
                "terminal",
                campaign.pk, campaign.status, instance.pk,
            )
