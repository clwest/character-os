"""Cross-workspace asset reference validation for
``CompositionStep``.

The privacy contract (``docs/design/VIDEO_COMPOSITION_V1.md``
§"Contract rules" 3) requires that every ``asset_id`` in a
step's ``inputs`` list belongs to the composition's workspace.

``CompositionStep.clean()`` catches the form / explicit
``full_clean()`` flows. This signal catches the raw
``step.save()`` flow which does not run ``clean()`` by
default. Together: defense in depth — every persistence path
runs the same check.

The cross-composition-workspace + step-asset-workspace
relationship is the leak shape we eliminate by construction.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import Asset, Composition, CompositionStep

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=CompositionStep)
def reject_cross_workspace_asset_references(
    sender,
    instance: CompositionStep,
    **kwargs,
) -> None:
    """Veto any ``CompositionStep`` whose ``inputs`` reference
    Assets in another workspace."""
    if not instance.composition_id:
        return

    composition_workspace_id = (
        Composition.objects.filter(pk=instance.composition_id)
        .values_list("workspace_id", flat=True)
        .first()
    )
    if not composition_workspace_id:
        return

    asset_ids = instance.referenced_asset_ids()
    if asset_ids:
        bad = list(
            Asset.objects.filter(pk__in=asset_ids)
            .exclude(workspace_id=composition_workspace_id)
            .values_list("pk", flat=True)
        )
        if bad:
            raise ValidationError(
                f"CompositionStep cannot reference assets from another "
                f"workspace. Composition workspace: "
                f"{composition_workspace_id}. Bad asset ids: {bad}"
            )

    # Also veto output_asset cross-workspace assignment.
    if instance.output_asset_id:
        output_workspace_id = (
            Asset.objects.filter(pk=instance.output_asset_id)
            .values_list("workspace_id", flat=True)
            .first()
        )
        if output_workspace_id and output_workspace_id != composition_workspace_id:
            raise ValidationError(
                f"CompositionStep.output_asset must be in the composition's "
                f"workspace. Composition workspace: "
                f"{composition_workspace_id}, asset workspace: "
                f"{output_workspace_id}."
            )
