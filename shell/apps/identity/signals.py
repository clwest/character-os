"""Cross-workspace validation for the identity substrate.

Mirrors the R1 (SESSION 146) pattern in ``apps.realtime.signals``:
``clean()`` methods on the substrate models catch the form /
explicit ``full_clean()`` paths; these ``pre_save`` signals catch
the raw ``.save()`` path which does not run ``clean()`` by
default. Together = defense in depth.

The leak shape we eliminate by construction:

* An ``IdentityReference`` whose asset belongs to a different
  workspace than the parent identity (§7.5).
* A ``GenerationRecord`` whose raw or normalized output asset
  belongs to a different workspace than the parent identity.
* A ``NormalizationManifest`` whose raw or normalized asset
  belongs to a different workspace than the parent identity.

These signals do not implement any business rule beyond
delegating to ``clean()`` — the model methods carry the specific
field-level messages.
"""
from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import GenerationRecord, IdentityReference, NormalizationManifest


@receiver(pre_save, sender=IdentityReference)
def reject_cross_workspace_identity_reference(
    sender,
    instance: IdentityReference,
    **kwargs,
) -> None:
    if not instance.identity_version_id or not instance.asset_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {"asset", "identity_version"}
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        raise


@receiver(pre_save, sender=GenerationRecord)
def reject_cross_workspace_generation_record(
    sender,
    instance: GenerationRecord,
    **kwargs,
) -> None:
    if not instance.identity_version_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {
            "raw_output_asset",
            "normalized_output_asset",
            "identity_version",
        }
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        raise


@receiver(pre_save, sender=NormalizationManifest)
def reject_cross_workspace_normalization_manifest(
    sender,
    instance: NormalizationManifest,
    **kwargs,
) -> None:
    if not instance.generation_record_id:
        return

    update_fields = kwargs.get("update_fields")
    if update_fields is not None:
        validated_fields = {
            "raw_output_asset",
            "normalized_output_asset",
            "generation_record",
        }
        if not (set(update_fields) & validated_fields):
            return

    try:
        instance.clean()
    except ValidationError:
        raise
