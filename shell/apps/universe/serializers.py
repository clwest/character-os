"""DRF serializers for the Universe substrate.

SESSION 261 / ``docs/design/UNIVERSE_SCHEMA_V1.md`` §"API contract"
— Universe.
SESSION 262 / ``docs/design/EPISODE_SCHEMA_V1.md §Q16`` — Episode.
SESSION 269 §12 — Episode create accepts ``cast_ids`` write-only
so the SPA Create Episode form can persist the full cast atomically
in one request (instead of requiring a follow-up per-teammate
POST /api/episodes/<id>/cast/ for every member). Fixes the
empty-cast Episode footgun that produced ``91a63409`` — see
``docs/design/SESSION_269_PATCH_WORKSHOP_DOGFOOD.md §11.4``.
"""
from __future__ import annotations

from django.db import transaction
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
    members (Teammate) sorted by ``EpisodeCast.added_at`` so the
    SPA can seed recipe-form performer slots deterministically
    (first-added = default primary, second-added = default
    secondary). **This ordering is a UI convention, NOT a
    protagonist/lead/narrator/story-role designation** — that is
    an explicit deferral per
    ``EPISODE_COMPOSITION_WORKFLOW_DOGFOOD_V1.md``. If a schema-
    level role field is ever needed it lands in a separate slice
    with its own migration + tests.

    Cast mutation lives on dedicated endpoints
    (``POST /api/episodes/<id>/cast/`` +
    ``DELETE /api/episodes/<id>/cast/<teammate_id>/``) so per-add
    Universe-consistency validation surfaces distinct 400s.

    ``composition_count`` is a live count for SPA list surfaces
    and the hard-delete preflight body.
    """

    universe_name = serializers.CharField(
        source="universe.name", read_only=True,
    )
    cast = serializers.SerializerMethodField()
    composition_count = serializers.SerializerMethodField()

    # SESSION 269 §12 — write-only cast seed for atomic Create.
    # ``cast_ids`` is optional on create; every value must be a
    # Teammate UUID belonging to this Episode's Universe. The
    # ``create()`` override attaches under the transaction so a
    # bad UUID aborts the whole create (Episode row is never left
    # partially populated). Never surfaced on responses — the
    # read shape stays the SESSION 262 ``cast`` nested list. The
    # dedicated per-add endpoint remains the source of truth for
    # post-create mutation; this is create-only convenience so
    # the SPA can capture cast on the same screen as topic.
    cast_ids = serializers.ListField(
        child=serializers.UUIDField(),
        write_only=True,
        required=False,
        default=list,
        help_text=(
            "SESSION 269 §12 — optional list of Teammate UUIDs to "
            "attach as cast at create time. Each must belong to "
            "this Episode's Universe. Duplicates are dropped."
        ),
    )

    def get_cast(self, obj: Episode) -> list[dict]:
        """Sorted-by-added_at cast payload. See class docstring
        for why ordering is only a UI default, not a story role.
        """
        rows = (
            obj.cast_rows
            .order_by("added_at")
            .select_related("teammate")
        )
        return [
            {"id": str(r.teammate.id), "name": r.teammate.name}
            for r in rows
        ]

    class Meta:
        model = Episode
        fields = [
            "id",
            "universe",
            "universe_name",
            "title",
            "operator_topic",
            "cast",
            "cast_ids",
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
        primitive.

        SESSION 269 §12 — ``cast_ids`` is create-only; strip it
        silently on update so PATCH callers don't accidentally
        re-seed cast through the wrong surface. Cast mutation on
        an existing Episode uses the dedicated ``/cast/`` action.
        """
        validated_data.pop("cast_ids", None)
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

    def create(self, validated_data):
        """SESSION 269 §12 — create Episode + optionally attach
        cast in one atomic step.

        ``cast_ids`` is resolved and validated BEFORE the Episode
        row is written so a bad UUID / cross-Universe teammate /
        cross-workspace teammate aborts the whole request with a
        clear 400 rather than leaving a naked Episode row behind.
        Attachments happen under the same transaction using the
        same M2M ``pre_add`` signal path as the dedicated per-add
        endpoint — so Universe-consistency + Workspace-consistency
        + legacy-Teammate rejection all continue to fire.

        Behaviour when ``cast_ids`` is omitted or empty is
        byte-identical to pre-§12: the Episode is created with an
        empty cast (the operator can add later via the dedicated
        cast endpoint).
        """
        cast_ids = validated_data.pop("cast_ids", None) or []
        # Preserve order of first-appearance while dropping
        # duplicates. Cast order is a UI convention (added_at)
        # per class docstring — the SPA seeds recipe-form performer
        # slots deterministically from this order.
        seen: set[str] = set()
        ordered_cast_ids: list[str] = []
        for cid in cast_ids:
            key = str(cid)
            if key in seen:
                continue
            seen.add(key)
            ordered_cast_ids.append(key)

        universe = validated_data.get("universe")
        request = self.context.get("request")
        caller = getattr(request, "user", None) if request else None

        resolved_teammates: list[Teammate] = []
        if ordered_cast_ids:
            if universe is None:
                raise serializers.ValidationError({
                    "cast_ids": (
                        "cannot attach cast without a Universe on the "
                        "Episode."
                    ),
                })
            # Resolve one teammate at a time so per-ID error messages
            # can point at the specific bad UUID. Scope to caller's
            # workspace-member set to avoid leaking cross-workspace
            # Teammate identities.
            teammate_lookup = {
                str(tm.id): tm
                for tm in Teammate.objects.filter(
                    pk__in=ordered_cast_ids,
                    workspace__memberships__user=caller,
                )
            }
            missing = [
                cid for cid in ordered_cast_ids
                if cid not in teammate_lookup
            ]
            if missing:
                raise serializers.ValidationError({
                    "cast_ids": (
                        f"teammate(s) not found or not in an accessible "
                        f"workspace: {missing}"
                    ),
                })
            # Universe consistency check — the M2M pre_add signal
            # also enforces this, but surfacing it as a serializer
            # error is a clearer 400 than the signal's ValidationError.
            wrong_universe = [
                cid for cid, tm in teammate_lookup.items()
                if tm.universe_id != universe.id
            ]
            if wrong_universe:
                raise serializers.ValidationError({
                    "cast_ids": (
                        f"teammate(s) not in Universe {universe.name!r}: "
                        f"{wrong_universe}"
                    ),
                })
            resolved_teammates = [
                teammate_lookup[cid] for cid in ordered_cast_ids
            ]

        with transaction.atomic():
            episode = super().create(validated_data)
            for tm in resolved_teammates:
                # Same code path as the /cast/ endpoint —
                # pre_add signal enforces Workspace consistency
                # + legacy-Teammate rejection defense-in-depth.
                episode.cast.add(tm)

        return episode

