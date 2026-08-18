"""DRF serializers for the Universe substrate.

SESSION 261 / ``docs/design/UNIVERSE_SCHEMA_V1.md`` §"API contract"
— Universe.
SESSION 262 / ``docs/design/EPISODE_SCHEMA_V1.md §Q16`` — Episode.
"""
from __future__ import annotations

from rest_framework import serializers

from apps.accounts.models import Membership
from apps.spokespeople.models import Teammate

from .models import Episode, EpisodeCast, Universe


class UniverseSerializer(serializers.ModelSerializer):
    workspace_name = serializers.CharField(source="workspace.name", read_only=True)
    # Live counts of members in this Universe. Powers the SPA's
    # "N teammates, M docs" pill on the Universe list + the hard-
    # delete conflict body (enumerates blocking child counts).
    teammate_count = serializers.SerializerMethodField()
    knowledge_document_count = serializers.SerializerMethodField()
    # SESSION 262 — surfaces Episode child count so the SPA can
    # render Universes with "N teammates, M docs, K episodes"
    # pills and so the hard-delete conflict body has the
    # authoritative blocking counts.
    episode_count = serializers.SerializerMethodField()

    class Meta:
        model = Universe
        fields = [
            "id",
            "workspace",
            "workspace_name",
            "name",
            "slug",
            "description",
            "created_by",
            "created_at",
            "updated_at",
            "archived_at",
            "teammate_count",
            "knowledge_document_count",
            "episode_count",
        ]
        read_only_fields = [
            "id",
            "workspace_name",
            "slug",
            "created_by",
            "created_at",
            "updated_at",
            "archived_at",
            "teammate_count",
            "knowledge_document_count",
            "episode_count",
        ]

    def get_teammate_count(self, obj: Universe) -> int:
        return obj.teammate_count()

    def get_knowledge_document_count(self, obj: Universe) -> int:
        return obj.knowledge_document_count()

    def validate_workspace(self, workspace):
        """Block Universe creation in a workspace the caller
        isn't a Member of. Mirrors ``TeammateSerializer.
        validate_workspace``.
        """
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(
            user=request.user, workspace=workspace,
        ).exists():
            raise serializers.ValidationError("not a member of this workspace")
        return workspace

    def get_episode_count(self, obj: Universe) -> int:
        return obj.episode_count()

    def validate_name(self, name):
        stripped = (name or "").strip()
        if not stripped:
            raise serializers.ValidationError(
                "Universe name cannot be blank."
            )
        return stripped


# ============================================================
# EPISODE_SCHEMA_V1 (SESSION 262)
# ============================================================


class EpisodeCastTeammateSerializer(serializers.ModelSerializer):
    """Nested cast-member payload for Episode responses."""

    class Meta:
        model = Teammate
        fields = ["id", "name"]
        read_only_fields = fields


class EpisodeSerializer(serializers.ModelSerializer):
    """Full Episode payload.

    ``cast`` is a nested read-only list of ``{id, name}`` cast
    members (Teammate). Cast mutation lives on dedicated
    endpoints (``POST /api/episodes/<id>/cast/`` +
    ``DELETE /api/episodes/<id>/cast/<teammate_id>/``) so per-add
    Universe-consistency validation surfaces distinct 400s.

    ``composition_count`` is a live count for SPA list surfaces
    and the hard-delete preflight body.
    """

    universe_name = serializers.CharField(
        source="universe.name", read_only=True,
    )
    cast = EpisodeCastTeammateSerializer(many=True, read_only=True)
    composition_count = serializers.SerializerMethodField()

    class Meta:
        model = Episode
        fields = [
            "id",
            "universe",
            "universe_name",
            "title",
            "operator_topic",
            "cast",
            "composition_count",
            "archived_at",
            "created_by",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "id",
            "universe_name",
            "cast",
            "composition_count",
            "archived_at",
            "created_by",
            "created_at",
            "updated_at",
        ]

    def get_composition_count(self, obj: Episode) -> int:
        return obj.composition_count()

    def validate_universe(self, universe):
        request = self.context.get("request")
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("authentication required")
        if not Membership.objects.filter(
            user=request.user, workspace=universe.workspace,
        ).exists():
            raise serializers.ValidationError(
                "not a member of this Universe's workspace"
            )
        return universe

    def validate_title(self, title):
        stripped = (title or "").strip()
        if not stripped:
            raise serializers.ValidationError(
                "Episode title cannot be blank."
            )
        return stripped

    def validate_operator_topic(self, operator_topic):
        stripped = (operator_topic or "").strip()
        if not stripped:
            raise serializers.ValidationError(
                "Episode operator_topic cannot be blank."
            )
        return stripped

    def update(self, instance: Episode, validated_data):
        """Episode.universe is immutable after create — reject any
        attempt to change it via PATCH. Guards against
        cross-Universe migration outside the deferred crossover
        primitive."""
        if "universe" in validated_data:
            new_universe = validated_data.pop("universe")
            if new_universe.pk != instance.universe_id:
                raise serializers.ValidationError({
                    "universe": (
                        "Episode.universe is immutable after create. "
                        "Cross-Universe migration is not supported in v1."
                    ),
                })
        return super().update(instance, validated_data)

