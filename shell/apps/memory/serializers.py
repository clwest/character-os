"""DRF serializers for NarrativeMemory.

SESSION 264 Slice 1. Two shapes:

* ``NarrativeMemorySerializer`` — full read + write payload for the
  list/detail endpoints on the resource.
* ``NarrativeMemoryPromoteItemSerializer`` — one entry in the batch
  body accepted by ``POST /api/compositions/<id>/promote-narrative-memory/``.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.spokespeople.models import Teammate
from apps.universe.models import Episode

from .models import (
    NarrativeMemory,
    NarrativeMemoryKind,
    NarrativeMemoryWeight,
)


class NarrativeMemoryWitnessSerializer(serializers.ModelSerializer):
    """Nested witness payload — just id + name."""

    class Meta:
        model = Teammate
        fields = ["id", "name"]
        read_only_fields = fields


class NarrativeMemorySerializer(serializers.ModelSerializer):
    """Full read payload for a memory row.

    Writes go through the promote endpoint on Composition; the
    resource endpoint (``/api/narrative-memories/``) accepts direct
    creates too but the operator surface uses promote.
    """

    universe_name = serializers.CharField(source="universe.name", read_only=True)
    episode_title = serializers.CharField(source="episode.title", read_only=True)
    source_composition_name = serializers.CharField(
        source="source_composition.name", read_only=True,
    )
    witnessed_by = NarrativeMemoryWitnessSerializer(many=True, read_only=True)
    is_current = serializers.SerializerMethodField()

    class Meta:
        model = NarrativeMemory
        fields = [
            "id",
            "episode",
            "episode_title",
            "source_composition",
            "source_composition_name",
            "workspace",
            "universe",
            "universe_name",
            "kind",
            "body",
            "witnessed_by",
            "weight",
            "status",
            "supersedes",
            "superseded_at",
            "superseded_reason",
            "archived_at",
            "promoted_by",
            "created_at",
            "updated_at",
            "is_current",
        ]
        read_only_fields = [
            "id",
            "episode_title",
            "source_composition_name",
            "workspace",
            "universe",
            "universe_name",
            "witnessed_by",
            "status",
            "supersedes",
            "superseded_at",
            "superseded_reason",
            "archived_at",
            "promoted_by",
            "created_at",
            "updated_at",
            "is_current",
        ]

    def get_is_current(self, obj: NarrativeMemory) -> bool:
        """A row is "current" for retrieval iff it is REMEMBERED
        and not archived. Convenience flag for SPA.
        """
        return (
            obj.status == "remembered"
            and obj.archived_at is None
        )


class NarrativeMemoryPromoteItemSerializer(serializers.Serializer):
    """One row inside the batch POST body accepted by
    ``POST /api/compositions/<id>/promote-narrative-memory/``.

    * ``body`` (required) — memory text.
    * ``kind`` (optional; defaults to EVENT).
    * ``weight`` (optional; defaults to PERIPHERAL).
    * ``witnessed_by`` (optional list of Teammate UUIDs). Empty or
      omitted = whole cast convention.
    * ``supersedes`` (optional UUID of a prior memory in the same
      Episode to retcon).
    * ``superseded_reason`` (optional; free-form operator note).
    """

    body = serializers.CharField(trim_whitespace=True)
    kind = serializers.ChoiceField(
        choices=NarrativeMemoryKind.choices,
        required=False,
        default=NarrativeMemoryKind.EVENT.value,
    )
    weight = serializers.ChoiceField(
        choices=NarrativeMemoryWeight.choices,
        required=False,
        default=NarrativeMemoryWeight.PERIPHERAL.value,
    )
    witnessed_by = serializers.ListField(
        child=serializers.UUIDField(),
        required=False,
        default=list,
    )
    supersedes = serializers.UUIDField(required=False, allow_null=True)
    superseded_reason = serializers.CharField(
        required=False, allow_blank=True, default="",
    )

    def validate_body(self, body: str) -> str:
        stripped = (body or "").strip()
        if not stripped:
            raise serializers.ValidationError("body cannot be blank")
        return stripped


class NarrativeMemoryPromoteRequestSerializer(serializers.Serializer):
    """Batch body: ``{"episode": UUID, "memories": [item, item, ...]}``.

    ``episode`` is required; the memories' ``episode`` FK is set
    from it. This lets the operator create + attach in one call
    even if the Composition is not yet Episode-attached (though
    in practice Slice 1 UX only enables promotion on
    Episode-attached Compositions).
    """

    episode = serializers.UUIDField()
    memories = serializers.ListField(
        child=NarrativeMemoryPromoteItemSerializer(),
        min_length=1,
    )

    def validate_episode(self, episode_id):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        # Scope to caller's workspaces to avoid disclosing cross-tenant IDs.
        episode = (
            Episode.objects
            .filter(
                pk=episode_id,
                universe__workspace__memberships__user=request.user,
            )
            .select_related("universe", "universe__workspace")
            .first()
        )
        if episode is None:
            raise serializers.ValidationError(
                "not found or not in an accessible workspace"
            )
        # Stash the resolved instance so the view can reuse it
        # without a second lookup.
        self.context["_resolved_episode"] = episode
        return episode_id
