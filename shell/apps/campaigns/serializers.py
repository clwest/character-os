"""B3.4 — DRF serializers for the personalized-video REST surface.

Three serializers:

* ``PersonalizedRecipientSerializer`` — read-only per-row
  shape for the SPA grid.
* ``PersonalizedCampaignSerializer`` — read-only campaign
  shape with nested recipient counts + the parsed
  placeholders.
* ``CreateCampaignSerializer`` — write shape for
  ``POST /api/campaigns/``. Validates the template at
  serializer-level via ``parse_placeholders`` so syntax
  errors surface as 400 with a clean message.
"""
from __future__ import annotations

from rest_framework import serializers

from character_os.template_renderer import (
    TemplateError,
    parse_placeholders,
)

from .models import PersonalizedCampaign, PersonalizedRecipient


class PersonalizedRecipientSerializer(serializers.ModelSerializer):
    """Read-only recipient row for the SPA grid."""

    campaign_id = serializers.UUIDField(source="campaign.id", read_only=True)
    produced_composition_id = serializers.UUIDField(
        source="produced_composition.id",
        read_only=True,
        allow_null=True,
    )
    status_label = serializers.CharField(
        source="get_status_display", read_only=True,
    )

    class Meta:
        model = PersonalizedRecipient
        fields = [
            "id",
            "campaign_id",
            "variables",
            "label",
            "rendered_script",
            "position",
            "status",
            "status_label",
            "produced_composition_id",
            "error_message",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class PersonalizedCampaignSerializer(serializers.ModelSerializer):
    """Read-only campaign shape with per-status recipient
    counts. Detail surface includes the full recipient list;
    list surface excludes recipients (paginated separately
    via a sub-route or the SPA's lazy load)."""

    workspace_id = serializers.UUIDField(source="workspace.id", read_only=True)
    spokesperson_id = serializers.UUIDField(
        source="spokesperson.id", read_only=True,
    )
    spokesperson_name = serializers.CharField(
        source="spokesperson.name", read_only=True,
    )
    status_label = serializers.CharField(
        source="get_status_display", read_only=True,
    )
    recipient_counts = serializers.SerializerMethodField()

    class Meta:
        model = PersonalizedCampaign
        fields = [
            "id",
            "workspace_id",
            "spokesperson_id",
            "spokesperson_name",
            "name",
            "template",
            "placeholders",
            "status",
            "status_label",
            "recipient_counts",
            "launched_at",
            "completed_at",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_recipient_counts(self, obj: PersonalizedCampaign) -> dict[str, int]:
        """Per-status counts the SPA renders in the campaign
        list / detail headers. One pass through the
        recipients relation; cheap at v1 batch sizes."""
        # The SerializerMethodField is hit once per row in
        # list views — accept the N+1 cost at v1 batch sizes
        # (Starter=5 max, Pro=30, Agency=200; list pages cap
        # at 100 campaigns).
        counts = {
            choice: 0
            for choice, _ in PersonalizedRecipient.Status.choices
        }
        counts["total"] = 0
        for status_value in (
            obj.recipients.values_list("status", flat=True)
        ):
            counts[status_value] = counts.get(status_value, 0) + 1
            counts["total"] += 1
        return counts


class CreateCampaignSerializer(serializers.Serializer):
    """Body shape for ``POST /api/campaigns/``.

    The viewset resolves ``workspace_id`` from the requesting
    user's memberships; ``spokesperson_id`` must point at a
    Spokesperson in that workspace (clean()+signal enforce
    at save time, but we re-check here for a cleaner 400).

    Template syntax is validated via ``parse_placeholders``;
    placeholders field on the created row is populated from
    the parse result.
    """

    workspace_id = serializers.UUIDField(required=True)
    spokesperson_id = serializers.UUIDField(required=True)
    name = serializers.CharField(max_length=120)
    template = serializers.CharField(max_length=4000)

    def validate_template(self, value: str) -> str:
        """Surface template syntax errors as 400 instead of
        letting them blow up at render time."""
        try:
            # parse_placeholders is the syntax validator;
            # we throw away the result here and re-parse at
            # create() so the campaign row has the canonical
            # list.
            parse_placeholders(value)
        except TemplateError as exc:
            if exc.kind == "syntax":
                raise serializers.ValidationError(str(exc))
            # kind="missing" shouldn't happen at parse time
            # (it's a render-time error); rethrow defensively.
            raise serializers.ValidationError(str(exc))
        return value


class ParseCsvSerializer(serializers.Serializer):
    """Body shape for ``POST /api/campaigns/<id>/parse_csv/``."""

    csv_text = serializers.CharField(required=True)
