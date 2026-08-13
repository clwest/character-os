"""Cross-workspace validation for the B-2 / E-arc auto-scripting
arc.

B2.1 (SESSION 206). Mirrors apps.publish.signals +
apps.campaigns.signals shape. ``clean()`` catches form +
``full_clean()`` paths; this signal catches the raw ``.save()``
path that doesn't run clean() by default.

The leak shape eliminated by construction:
* Script whose ``spokesperson`` belongs to a different workspace
  than the script itself.

B2.3 will extend this with a post_save Composition receiver to
flip Script.status → RENDERED when an ``auto_script`` Composition
fires.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Script

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Script)
def reject_cross_workspace_script_refs(
    sender,
    instance: Script,
    **kwargs,
) -> None:
    """Veto a Script whose spokesperson lives in another
    workspace.

    Skips state-only updates (status / approved_at /
    revision_history / draft_text / etc.) where the workspace +
    spokesperson FKs themselves aren't being touched.
    """
    if not instance.workspace_id or not instance.spokesperson_id:
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
