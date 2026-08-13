"""B14.3 — DRF serializers for the D-arc publish-bundle REST surface.

Three serializers:

* ``PublishVariantSerializer`` — read-only per-row shape for
  the SPA progress grid.
* ``PublishBundleSerializer`` — read-only bundle shape with
  variant_counts (per-status rollup) + the snapshotted
  selected_platforms list.
* ``CreateBundleSerializer`` — write shape for
  ``POST /api/publish_bundles/``.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.compositions.platform_catalog import all_platform_keys

from .models import PublishBundle, PublishVariant


class PublishVariantSerializer(serializers.ModelSerializer):
    """Per-row shape for the SPA progress grid."""

    bundle_id = serializers.UUIDField(source="bundle.id", read_only=True)
    produced_composition_id = serializers.UUIDField(
        source="produced_composition.id",
        read_only=True,
        allow_null=True,
    )
    status_label = serializers.CharField(
        source="get_status_display", read_only=True,
    )

    class Meta:
        model = PublishVariant
        fields = [
            "id",
            "bundle_id",
            "platform_key",
            "target_ratio",
            "max_duration_ms",
            "status",
            "status_label",
            "produced_composition_id",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PublishBundleSerializer(serializers.ModelSerializer):
    """Bundle shape with per-status variant_counts. Detail
    surface includes the full variant list via the
    ``variants`` action (B14.3 ships that as a separate sub-
    route for SPA grid pagination later)."""

    workspace_id = serializers.UUIDField(source="workspace.id", read_only=True)
    source_clip_id = serializers.UUIDField(
        source="source_clip.id", read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display", read_only=True,
    )
    variant_counts = serializers.SerializerMethodField()

    class Meta:
        model = PublishBundle
        fields = [
            "id",
            "workspace_id",
            "source_clip_id",
            "name",
            "selected_platforms",
            "status",
            "status_label",
            "variant_counts",
            "launched_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_variant_counts(self, obj: PublishBundle) -> dict[str, int]:
        """Per-status counts for the SPA list / detail
        headers. One pass through the related variants.
        Catalog size 5 + hard cap 10 makes the N+1 list cost
        trivial."""
        counts = {
            choice: 0
            for choice, _ in PublishVariant.Status.choices
        }
        counts["total"] = 0
        for status_value in obj.variants.values_list("status", flat=True):
            counts[status_value] = counts.get(status_value, 0) + 1
            counts["total"] += 1
        return counts


class CreateBundleSerializer(serializers.Serializer):
    """Body shape for ``POST /api/publish_bundles/``.

    The viewset resolves the source clip + workspace from the
    requesting user's memberships; this serializer just
    validates the operator-supplied fields. Platform keys
    validated against the catalog (rule 7).
    """

    source_clip_id = serializers.UUIDField(required=True)
    name = serializers.CharField(max_length=120)
    selected_platforms = serializers.ListField(
        child=serializers.CharField(max_length=40),
        min_length=1,
        max_length=10,  # MAX_PLATFORMS_PER_BUNDLE
    )

    def validate_selected_platforms(self, value: list[str]) -> list[str]:
        """Every key must exist in the catalog. Duplicates
        rejected — the UniqueConstraint catches it at DB
        level too, but a 400 with a clean message beats a
        500 from an IntegrityError."""
        if len(value) != len(set(value)):
            raise serializers.ValidationError(
                "selected_platforms must not contain duplicates"
            )
        valid = set(all_platform_keys())
        invalid = [k for k in value if k not in valid]
        if invalid:
            raise serializers.ValidationError(
                f"unknown platform key(s): {invalid}. "
                f"Valid keys: {sorted(valid)}"
            )
        return value
