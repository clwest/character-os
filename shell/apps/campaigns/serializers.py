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
    # SESSION 256 fix — SET_NULL on teammate deletion
    # (Campaign.spokesperson, models.py:85-88) means the FK can be
    # None; DRF's source-chain walker would SkipField and break
    # the SPA's zod parse (both fields required strings in
    # web/src/lib/api/campaigns.ts).
    spokesperson_id = serializers.SerializerMethodField()
    spokesperson_name = serializers.SerializerMethodField()
    status_label = serializers.CharField(
        source="get_status_display", read_only=True,
    )
    recipient_counts = serializers.SerializerMethodField()

    def get_spokesperson_id(self, obj) -> str | None:
        return str(obj.spokesperson_id) if obj.spokesperson_id else None

    def get_spokesperson_name(self, obj) -> str:
        if obj.spokesperson_id and obj.spokesperson:
            return obj.spokesperson.name
        return "(deleted teammate)"
    # BC3 — surfaces the optional Script derivation pointer for
    # the SPA detail page. Null when source_script is unset (the
    # vast majority of pre-BC Campaigns + any non-derived Campaign).
    source_script = serializers.SerializerMethodField()

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
            "source_script",
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

    def get_source_script(
        self, obj: PersonalizedCampaign,
    ) -> dict | None:
        """BC3 — light source_script block for the SPA detail
        page. Returns ``None`` when the Campaign isn't derived
        from a Script (the current shape for any pre-BC Campaign
        and any new free-form Campaign). When set, exposes only
        the fields the SPA needs for the "Derived from Script X
        (verified, 5 chunks)" hint — no draft_text spill, no
        revision history leak."""
        if obj.source_script_id is None:
            return None
        script = obj.source_script
        return {
            "id": str(script.pk),
            "name": script.name,
            "status": script.status,
            "verification_status": script.verification_status or "",
            "chunk_count": len(script.knowledge_chunk_ids or []),
        }


class CreateCampaignSerializer(serializers.Serializer):
    """Body shape for ``POST /api/campaigns/``.

    The viewset resolves ``workspace_id`` from the requesting
    user's memberships; ``spokesperson_id`` must point at a
    Teammate in that workspace (clean()+signal enforce
    at save time, but we re-check here for a cleaner 400).

    Template syntax is validated via ``parse_placeholders``;
    placeholders field on the created row is populated from
    the parse result.

    BC3 — when ``source_script_id`` is supplied:

    * The viewset fetches the Script (workspace-filtered).
    * If ``template`` is also supplied (non-empty), it wins —
      operator may have edited the draft before submit. The FK
      is persisted as audit trail (rule 2).
    * If ``template`` is empty / omitted, the viewset fills it
      from ``script.draft_text``.

    Either pattern persists ``source_script`` for the BC3 lineage
    propagation at launch time.
    """

    workspace_id = serializers.UUIDField(required=True)
    spokesperson_id = serializers.UUIDField(required=True)
    name = serializers.CharField(max_length=120)
    # BC3 — template becomes optional when source_script_id is
    # supplied (viewset back-fills from script.draft_text).
    template = serializers.CharField(
        max_length=4000, required=False, allow_blank=True, default="",
    )
    source_script_id = serializers.UUIDField(
        required=False, allow_null=True, default=None,
    )

    def validate_template(self, value: str) -> str:
        """Surface template syntax errors as 400 instead of
        letting them blow up at render time. Empty templates
        are allowed at this layer — the viewset enforces "must
        have a template OR source_script_id" cross-field."""
        if not value:
            return value
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

    def validate(self, attrs: dict) -> dict:
        """BC3 cross-field — must have either ``template`` or
        ``source_script_id``. The viewset will fill ``template``
        from ``script.draft_text`` when only the FK is supplied."""
        template = (attrs.get("template") or "").strip()
        source_script_id = attrs.get("source_script_id")
        if not template and not source_script_id:
            raise serializers.ValidationError({
                "template": (
                    "template is required when source_script_id "
                    "is not supplied"
                ),
            })
        return attrs


class ParseCsvSerializer(serializers.Serializer):
    """Body shape for ``POST /api/campaigns/<id>/parse_csv/``."""

    csv_text = serializers.CharField(required=True)
