"""Serializer for Teammate."""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership
from apps.universe.models import Universe

from .models import Teammate


class TeammateSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    video_count = serializers.SerializerMethodField()
    # SESSION 232 — powers the SPA's masthead button state
    # ("Define {name}" when < 4 filled; plain "Identity" when >= 4)
    # + the "N of 6 filled" progress signal on the identity page.
    # Server-derived so the SPA has one authoritative source.
    identity_fields_filled = serializers.SerializerMethodField()

    # Write-only. When supplied on create, ``TeammateViewSet.create``
    # fires ``MediaEngineClient.create_avatar`` after the DB row lands
    # and persists the resulting ``runway_avatar_id`` /
    # ``runway_avatar_status`` onto the model. Format:
    # ``data:image/{png|jpeg|webp};base64,...`` (5 MB cap, enforced
    # media-engine side).
    portrait_data_uri = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=10 * 1024 * 1024,
        trim_whitespace=False,
    )
    voice_preset = serializers.CharField(
        write_only=True,
        required=False,
        allow_blank=True,
        max_length=80,
    )

    class Meta:
        model = Teammate
        fields = [
            "id",
            "workspace",
            "workspace_name",
            # SESSION 261 — Universe substrate FK. Optional; NULL
            # means "legacy teammate; use pre-Universe semantics."
            # `PrimaryKeyRelatedField(allow_null=True, required=
            # False)` distinguishes "absent" (no change on PATCH)
            # from "explicit null" (detach from Universe). See
            # UNIVERSE_SCHEMA_V1.md §"Endpoints that MUST change".
            "universe",
            "name",
            "business_brief",
            # W11.y (SESSION 175) — see Teammate.personality docstring.
            # Splits HOW (personality) from WHAT (business_brief) so
            # operators can swap business briefs across personality
            # types.
            "personality",
            "visual_subject",
            "visual_template",
            "tone_archetype",
            "status",
            "runway_avatar_id",
            "runway_avatar_status",
            "portrait_path",
            "voice_id",
            # SESSION 232 — Identity surface (contract rule 10).
            # Five new slots that pair with business_brief above to
            # form the six identity fields the customer fills on
            # ``/spokespeople/{id}/identity``. All PATCH-able. All
            # accept empty; only business_brief is server-required.
            "who_you_help",
            "what_you_sell",
            "always_emphasize",
            "never_say",
            "desired_feeling",
            # SESSION 253 — Character Voice / Writing Identity
            # fields. All PATCH-able. All accept empty. Three
            # ``voice_*`` axes have server-side defaults (medium /
            # warm / balanced — the friend profile); existing rows
            # backfill from tone_archetype via the data migration.
            "character_point_of_view",
            "voice_energy",
            "voice_humor",
            "voice_directness",
            "voice_signature_phrases",
            "voice_avoid_phrases",
            "identity_fields_filled",
            "video_count",
            "created_at",
            "updated_at",
            "portrait_data_uri",
            "voice_preset",
        ]
        read_only_fields = [
            "id",
            "workspace_name",
            "runway_avatar_id",
            "runway_avatar_status",
            "portrait_path",
            "voice_id",
            "identity_fields_filled",
            "video_count",
            "created_at",
            "updated_at",
        ]

    def get_video_count(self, obj: Teammate) -> int:
        return obj.videos.count()

    def get_identity_fields_filled(self, obj: Teammate) -> int:
        return obj.identity_fields_filled_count()

    def validate_workspace(self, workspace):
        """Block creating a teammate in a workspace the user
        isn't a member of."""
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(user=request.user, workspace=workspace).exists():
            raise serializers.ValidationError("not a member of this workspace")
        return workspace

    def validate(self, attrs):
        """SESSION 261 — cross-workspace Universe guard.

        The Universe FK is workspace-consistent by invariant
        (UNIVERSE_SCHEMA_V1.md §"Universe consistency invariant").
        This surfaces a clean 400 at the API boundary instead of
        letting Teammate.clean() raise mid-save.

        SESSION 277 Slice 5 (Q-277-5) — CREATE-time positive-Universe
        requirement. New ordinary teammates must be created inside a
        World. Existing legacy ``universe=NULL`` rows remain readable
        and PATCH-able (the DB column stays nullable per Slice 4 §78);
        this is CREATE-only enforcement. Mirror of the SESSION 276
        Delta ``audience_scope_required_on_create`` pattern.
        """
        attrs = super().validate(attrs)
        universe: Universe | None = attrs.get("universe")
        # On PATCH, workspace comes from the instance; on POST, from
        # validated data.
        workspace = attrs.get("workspace") or (
            self.instance.workspace if self.instance else None
        )
        if universe is not None and workspace is not None:
            if universe.workspace_id != workspace.pk:
                raise serializers.ValidationError({
                    "universe": (
                        "Universe belongs to a different workspace than "
                        "this teammate."
                    ),
                })

        # SESSION 277 Slice 5 — CREATE-only positive-Universe guard.
        # ``self.instance is None`` distinguishes CREATE from UPDATE;
        # PATCH of an existing legacy row (universe still NULL) is
        # explicitly allowed so legacy teammates remain editable
        # without a forced migration. New rows must have a Universe.
        if self.instance is None and universe is None:
            raise serializers.ValidationError({
                "universe": {
                    "code": "universe_required_on_create",
                    "detail": (
                        "New characters must belong to a World. Supply "
                        "``universe: <uuid>`` in the payload. Existing "
                        "legacy Universe-less teammates remain readable "
                        "and PATCH-able — this requirement applies to "
                        "new creates only. See "
                        "docs/design/SESSION_277_OPERATOR_KNOWLEDGE_DOGFOOD.md "
                        "§68-§86 for the Slice 5 rationale."
                    ),
                },
            })

        return attrs
