"""DRF views for V15 recipe + composition REST surface.

SESSION 144 / V15.0. Three routes:

* GET  /api/recipes/             list 17 recipe metadata entries
* POST /api/compositions/        create a composition from a recipe
* GET  /api/compositions/{id}/   retrieve a composition (status poll)

The create flow:
  1. Validate ``kind`` is a registered recipe.
  2. Validate ``workspace`` is owned by the caller.
  3. Resolve form params → starter kwargs (recipes.resolve_kwargs).
  4. Call the recipe's starter inside a transaction.
  5. Enqueue ``execute_composition.delay(str(c.id))``.
  6. Return the freshly-created Composition (status DRAFT or
     RUNNING depending on celery eager mode).

W11.6.2 (SESSION 173) added the image generation surface:

* POST   /api/images/            generate + persist an image
* GET    /api/images/            list workspace images (filterable)
* GET    /api/images/<id>/       retrieve one image
* DELETE /api/images/<id>/       workspace-scoped delete
* GET    /api/styles/            categorized style preset library

Workspace isolation is structural — Teammate + Asset
lookups are scoped via ``Model.objects.get(pk=..., workspace=ws)``
so a foreign id raises DoesNotExist → 400. The V1 cross-
workspace signal is the second line of defense.

The viewset uses the existing ``IsWorkspaceMember`` permission;
list views return only compositions in workspaces the caller
is a member of.
"""
from __future__ import annotations

import logging

from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.db.models import Q
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Membership, Workspace, default_workspace_for
from apps.compositions.assets import StorageHealth, compute_storage_health
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.compositions.starters import (
    DialogueSynthesisFailedError,
    LongFormDurationError,
)
from apps.spokespeople.models import Teammate
from apps.universe.models import Episode
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.permissions import IsWorkspaceMember

from .recipes import RECIPES, get_recipe, resolve_kwargs
from .serializers import (
    CompositionListSerializer,
    CompositionSerializer,
    ImageAssetSerializer,
    RecipeSerializer,
)
from .tasks import execute_composition

logger = logging.getLogger(__name__)


# W11.6.2 — image generation constants. Mirror the media-engine
# enums; duplicated rather than imported because media-engine is
# a separate service that Django can't (and shouldn't) import.
IMAGE_VALID_PURPOSES = frozenset({
    "avatar", "scene", "broll", "product", "ad",
})

# Purposes that route through Stability (W11.6.1). Everything else
# (currently just ``avatar``) routes through Runway — but Contract
# rule 2 reserves the avatar wizard path for Teammate creation,
# so v1 of ``/api/images/`` rejects ``purpose=avatar`` with a 400
# pointing the operator to the wizard. W11.7+ may relax this if
# the "iterate cheaply before baking" journey (Journey 5) gains
# enough operator pull to need its own surface.
STABILITY_PURPOSES = frozenset({"scene", "broll", "product", "ad"})

STABILITY_VALID_ASPECT_RATIOS = frozenset({
    "1:1", "16:9", "9:16", "4:3", "3:4", "21:9",
})

STABILITY_VALID_MODELS = frozenset({
    "core", "sdxl", "sd3-medium", "sd3-large", "sd3-large-turbo", "ultra",
})

# Stability credit → micros (per Contract rule 7). 1 credit ≈ $0.001
# ≈ 1000 micros at the canonical conversion. Display-only multiplier
# for dollar conversion lives in the SPA (Q-img-G).
_STABILITY_CREDITS_TO_MICROS = 1000

# W11.6.5.1 — fallback title length when auto-deriving from
# subject. 60 chars fits comfortably in dropdown widths without
# truncation; longer subjects truncate with an ellipsis so the
# operator can still recognize them.
_AUTO_TITLE_MAX_CHARS = 60


def _derive_title_from_subject(subject: str) -> str:
    """Pull a usable picker label out of an operator's subject.

    Strategy: trim, collapse internal whitespace, snap to the
    first sentence boundary OR ``_AUTO_TITLE_MAX_CHARS`` —
    whichever comes first — and append an ellipsis when we
    truncated mid-thought. Empty subject → empty title (the
    picker falls back to the filename / data-URI tail).
    """
    if not subject:
        return ""
    cleaned = " ".join(subject.split())
    if not cleaned:
        return ""
    # First sentence boundary if it lands within the budget.
    for end_char in (". ", "! ", "? "):
        idx = cleaned.find(end_char)
        if 8 < idx <= _AUTO_TITLE_MAX_CHARS:
            return cleaned[: idx + 1].strip()
    if len(cleaned) <= _AUTO_TITLE_MAX_CHARS:
        return cleaned
    # Word-boundary truncation.
    cutoff = cleaned.rfind(" ", 0, _AUTO_TITLE_MAX_CHARS - 1)
    if cutoff < 20:
        cutoff = _AUTO_TITLE_MAX_CHARS - 1
    return cleaned[:cutoff].rstrip(",;:- ") + "…"


class AssetViewSet(viewsets.GenericViewSet):
    """Read-only list of workspace assets — powers the V15.2
    `asset_picker` form field. Filters by ``workspace`` (required),
    optional ``asset_type``, and (A7 / SESSION 190) optional
    ``role`` (comma-list of :class:`AssetRole` values).

    In v1 assets are produced by composition runs; there is no
    upload UI yet. Operators pick from previously-rendered output
    assets when wiring a layout/composite recipe.

    The ``role`` filter is the structural fix from
    ``docs/design/ASSET_LIBRARY_V1.md`` §A7 — V18's
    ``backdrop_clip_id`` dropdown narrows to ``role=backdrop``
    so smoke / talking-head / composite clips don't pollute the
    picker. Same pattern as the A4 endpoint's ``?role=`` (the
    two endpoints share zero code — A4 is paginated browse;
    this stays hard-capped at 200 since pickers are short
    lists).
    """

    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Asset.objects.none()
        return (
            Asset.objects.filter(workspace__memberships__user=user)
            .select_related("workspace")
            .distinct()
        )

    def list(self, request):
        qs = self.get_queryset()
        workspace_id = request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        asset_type = request.query_params.get("asset_type")
        if asset_type:
            qs = qs.filter(asset_type=asset_type)
        # A7 (SESSION 190) — optional role filter. Comma-list
        # like A4's ``?role=...``; empty / whitespace-only
        # entries are skipped. An unknown role value lands in
        # the IN clause and matches zero rows — that's the
        # correct behavior (operator typo'd a role; picker
        # shows empty).
        role_raw = request.query_params.get("role")
        if role_raw:
            roles = [r.strip() for r in role_raw.split(",") if r.strip()]
            if roles:
                qs = qs.filter(role__in=roles)
        # Newest first; cap to 200 — gallery picker isn't paginated yet.
        qs = qs.order_by("-created_at")[:200]
        # Inline shape (no separate serializer module dep) — same
        # fields the CompositionSerializer's AssetSerializer ships.
        data = [
            {
                "id": str(a.id),
                "workspace": str(a.workspace_id),
                "asset_type": a.asset_type,
                "file_path": a.file_path,
                "duration_ms": a.duration_ms,
                "width": a.width,
                "height": a.height,
                "mime_type": a.mime_type,
                "size_bytes": a.size_bytes,
                "cost_micros": a.cost_micros,
                "composition": str(a.composition_id) if a.composition_id else None,
                "created_at": a.created_at.isoformat(),
                # W11.6.5.1 — operator-facing label. Empty for
                # pre-W11.6.5.1 rows; the SPA assetLabel falls
                # back to filename / subject in that case.
                "title": a.title,
                "subject": a.subject,
            }
            for a in qs
        ]
        return Response(data)


class RecipeViewSet(viewsets.ViewSet):
    """Read-only metadata for the 17 starter compositions.

    No workspace scoping — recipe metadata is global (every
    workspace sees the same gallery). Auth required so the
    public internet doesn't probe our gallery.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        return Response(RecipeSerializer.all())

    def retrieve(self, request, pk: str | None = None):
        try:
            recipe = get_recipe(pk or "")
        except KeyError:
            raise NotFound(f"Unknown recipe kind: {pk!r}")
        return Response(recipe.to_json())


class CompositionPagination(PageNumberPagination):
    """Page-number pagination for the Composition list.

    Default 25/page, operator-overridable via ``?page_size=``
    up to 100. Response shape is
    ``{count, next, previous, results}`` — the SPA's Videos
    library reads these directly.
    """

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


class CompositionViewSet(viewsets.GenericViewSet):
    """Composition create + retrieve + list.

    Update / destroy intentionally absent in v1 — compositions
    are immutable once they start running; deleting a row
    breaks audit. Operators can mark a stuck composition
    failed via admin, not REST.

    List endpoint is paginated (page=1, page_size=25 default).
    Detail endpoints keep the full ``CompositionSerializer`` shape;
    only ``list()`` uses the light ``CompositionListSerializer``.
    """

    serializer_class = CompositionSerializer
    permission_classes = [IsWorkspaceMember]
    pagination_class = CompositionPagination

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Composition.objects.none()
        return (
            Composition.objects.filter(workspace__memberships__user=user)
            # SESSION 262 — select_related "episode" so the
            # CompositionSerializer's episode_title field can render
            # without an N+1. Same rationale for "spokesperson" +
            # "final_asset" already present.
            .select_related(
                "workspace", "spokesperson", "final_asset", "episode",
            )
            .prefetch_related("steps", "steps__output_asset")
            .distinct()
        )

    def list(self, request):
        qs = self.get_queryset().order_by("-created_at")
        workspace_id = request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        spokesperson_id = request.query_params.get("spokesperson")
        if spokesperson_id:
            qs = qs.filter(spokesperson_id=spokesperson_id)
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        # SESSION 262 / EPISODE_COMPOSITION_WORKFLOW_V1 — filter by
        # Episode FK so the Episode-detail SPA surface can render its
        # attached Composition/version list without a client-side
        # workspace-wide fetch. Cross-workspace / cross-Universe
        # isolation is already enforced by the get_queryset()
        # workspace-membership scoping above; this filter only
        # narrows the already-authorized set.
        episode_id = request.query_params.get("episode")
        if episode_id:
            qs = qs.filter(episode_id=episode_id)
        page = self.paginate_queryset(qs)
        serializer = CompositionListSerializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def retrieve(self, request, pk: str | None = None):
        try:
            comp = self.get_queryset().get(pk=pk)
        except Composition.DoesNotExist:
            raise NotFound("Composition not found")
        self.check_object_permissions(request, comp)
        return Response(CompositionSerializer(comp).data)

    @action(
        detail=True,
        methods=["post", "delete"],
        url_path="attach-episode",
    )
    def attach_episode(self, request, pk: str | None = None):
        """SESSION 262 — attach / move / detach Composition ↔ Episode.

        ``POST /api/compositions/<id>/attach-episode/`` with body
        ``{"episode": UUID}`` attaches (or moves) the Composition
        to the given Episode. Passing ``{"episode": null}`` detaches.

        ``DELETE`` on the same URL is equivalent to POST with
        ``episode: null``.

        Cross-Workspace / cross-Universe / legacy-spokesperson
        validation runs via ``Composition.clean()``. On success the
        save uses ``update_fields=["episode", "updated_at"]`` so
        SESSION 262 observability immutability is not disturbed
        (the guard sees the field is NOT in the immutability set
        and skips the check).

        Composition.episode uses ``on_delete=RESTRICT`` (see
        model comment for shared-CASCADE-parent rationale), which
        blocks direct Episode.delete() when Compositions attached
        AND surfaces the API 409 preflight before Django would
        raise the raw ``RestrictedError``.
        """
        try:
            comp = self.get_queryset().get(pk=pk)
        except Composition.DoesNotExist:
            raise NotFound("Composition not found")
        self.check_object_permissions(request, comp)

        if request.method == "DELETE":
            target_episode = None
        else:
            body = request.data or {}
            episode_id = body.get("episode")
            if episode_id in (None, "", "null"):
                target_episode = None
            else:
                target_episode = (
                    Episode.objects
                    .filter(
                        pk=episode_id,
                        universe__workspace__memberships__user=request.user,
                    )
                    .select_related("universe", "universe__workspace")
                    .first()
                )
                if target_episode is None:
                    raise ValidationError(
                        {"episode": "not found or not in an accessible workspace"}
                    )

        comp.episode = target_episode
        try:
            comp.full_clean()
        except DjangoValidationError as exc:
            raise ValidationError(exc.message_dict or {"detail": exc.messages})
        comp.save(update_fields=["episode", "updated_at"])
        comp.refresh_from_db()
        return Response(CompositionSerializer(comp).data)

    @action(
        detail=True,
        methods=["post"],
        url_path="promote-narrative-memory",
    )
    def promote_narrative_memory(self, request, pk: str | None = None):
        """SESSION 264 Slice 1 — promote turns to narrative memory.

        ``POST /api/compositions/<id>/promote-narrative-memory/``
        with body::

            {
              "episode": "<uuid>",
              "memories": [
                {"body": "...", "kind": "event",
                 "weight": "central",
                 "witnessed_by": ["<teammate-uuid>", ...]},
                ...
              ]
            }

        Each entry creates one ``NarrativeMemory`` row tied to
        this Composition + the specified Episode. Batch is
        atomic — a bad item fails the whole batch (all-or-
        nothing; operator resubmits cleaned batch).

        Never writes to KnowledgeDocument. Never modifies the
        Composition (no immutable-observability write). See
        ``docs/design/EPISODIC_CONTINUITY_CANON_PROMOTION_AUDIT_SESSION_264.md``
        §8 for the "synthesis never mutates canon" rule this
        endpoint upholds.
        """
        # Import inline to avoid a top-of-file dep from
        # compositions → memory (memory already imports
        # compositions). Same style as the existing tasks
        # import at the top of this file.
        from apps.memory.serializers import (
            NarrativeMemoryPromoteRequestSerializer,
        )
        from apps.memory.serializers import NarrativeMemorySerializer
        from apps.memory.views import promote_from_composition

        try:
            comp = self.get_queryset().get(pk=pk)
        except Composition.DoesNotExist:
            raise NotFound("Composition not found")
        self.check_object_permissions(request, comp)

        body_ser = NarrativeMemoryPromoteRequestSerializer(
            data=request.data or {},
            context={"request": request},
        )
        body_ser.is_valid(raise_exception=True)

        episode: Episode = body_ser.context["_resolved_episode"]

        # Sanity: the target Episode's workspace must match the
        # Composition's workspace (belt-and-suspenders — the
        # serializer already scoped Episode lookup to the
        # caller's workspace memberships).
        if episode.universe.workspace_id != comp.workspace_id:
            raise ValidationError({
                "episode": (
                    "Episode belongs to a different Workspace than "
                    "this Composition."
                ),
            })

        memory_items = body_ser.validated_data["memories"]

        try:
            created = promote_from_composition(
                composition=comp,
                episode=episode,
                memory_items=memory_items,
                promoted_by=request.user if request.user.is_authenticated else None,
            )
        except ValidationError:
            raise

        out = NarrativeMemorySerializer(created, many=True).data
        return Response(
            {"memories": out},
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def lineage(self, request, pk: str | None = None):
        """F5 — asset lineage for a composition.

        Returns the immediate-parent + immediate-child
        compositions that share assets with this one:

        * ``derived_from``: source compositions whose output
          assets this composition consumes as inputs. Walks
          each step's ``inputs`` JSON looking for
          ``asset_id`` entries (the ``from_step_position``
          shape is same-composition and not lineage). One hop
          per Q-f-5; the gallery doesn't surface chains.
        * ``used_by``: downstream compositions that consume
          assets produced by this one. Scans all
          ``CompositionStep.inputs`` whose JSON includes any
          of this composition's produced asset ids.

        Workspace scoping is structural — the parent
        composition lookup goes through the user's queryset;
        the asset_id strings can only resolve to in-workspace
        assets because of the V1 cross-workspace signal on
        save. Both lists are deduped by composition.
        """
        try:
            comp = self.get_queryset().get(pk=pk)
        except Composition.DoesNotExist:
            raise NotFound("Composition not found")
        self.check_object_permissions(request, comp)

        # ---- derived_from ------------------------------------
        # Collect every asset_id referenced as an input in
        # this composition's steps. asset_id appears when an
        # operator picked a workspace asset in the recipe form
        # (e.g. layout recipes' base_clip); from_step_position
        # is same-composition and excluded.
        input_asset_ids: set[str] = set()
        for step in comp.steps.all():
            for entry in step.inputs or []:
                if isinstance(entry, dict):
                    aid = entry.get("asset_id")
                    if aid:
                        input_asset_ids.add(str(aid))

        derived_from: list[dict] = []
        seen_source_comp_ids: set[str] = set()
        if input_asset_ids:
            source_assets = (
                Asset.objects.filter(
                    id__in=input_asset_ids,
                    workspace=comp.workspace,
                )
                .select_related("composition", "composition__spokesperson")
            )
            for asset in source_assets:
                src_comp = asset.composition
                if src_comp is None or str(src_comp.id) == str(comp.id):
                    continue
                # Dedup: one entry per source composition even
                # when several of its assets feed this one.
                if str(src_comp.id) in seen_source_comp_ids:
                    continue
                seen_source_comp_ids.add(str(src_comp.id))
                derived_from.append({
                    "asset_id": str(asset.id),
                    "asset_type": asset.asset_type,
                    "composition_id": str(src_comp.id),
                    "composition_name": src_comp.name,
                    "template_kind": src_comp.template_kind,
                    "status": src_comp.status,
                })

        # ---- used_by ----------------------------------------
        # Compositions whose steps reference any asset this
        # composition produced. Asset ids are stored as
        # strings inside CompositionStep.inputs JSON; we scan
        # the JSON for substring matches per asset to find
        # candidate steps, then group by composition.
        produced_asset_ids = list(
            comp.produced_assets.values_list("id", flat=True),
        )
        used_by: list[dict] = []
        seen_consumer_ids: set[str] = set()
        if produced_asset_ids:
            from django.db.models import Q

            # Per-id contains query — SQLite + Postgres both
            # support the JSON __icontains lookup well enough
            # for our v1 dataset sizes. Pre-cap to 100
            # candidates to keep the query bounded.
            q = Q()
            for aid in produced_asset_ids:
                q |= Q(inputs__icontains=str(aid))
            candidate_steps = (
                CompositionStep.objects
                .filter(q)
                .exclude(composition_id=comp.id)
                .select_related("composition", "composition__spokesperson")
                # Read-side workspace scope — the user must
                # be a member. Tests cover the cross-workspace
                # case; structurally V1's cross-workspace
                # signal prevents foreign assets from being
                # referenced in the first place.
                .filter(composition__workspace=comp.workspace)
                [:100]
            )
            for step in candidate_steps:
                consumer = step.composition
                if str(consumer.id) in seen_consumer_ids:
                    continue
                seen_consumer_ids.add(str(consumer.id))
                used_by.append({
                    "composition_id": str(consumer.id),
                    "composition_name": consumer.name,
                    "template_kind": consumer.template_kind,
                    "status": consumer.status,
                })

        return Response({
            "composition_id": str(comp.id),
            "derived_from": derived_from,
            "used_by": used_by,
        })

    def create(self, request):
        body = request.data or {}
        kind = body.get("kind")
        workspace_id = body.get("workspace")
        params = body.get("params") or {}
        # SESSION 262 / EPISODE_SCHEMA_V1 — optional Episode
        # attachment. NULL preserves standalone-Composition flow
        # (unchanged from pre-Episode behavior). Non-NULL resolves +
        # validates below; cross-Universe / cross-Workspace / legacy-
        # spokesperson rejections fire via ``Composition.clean()``.
        episode_id = body.get("episode")

        if not kind:
            raise ValidationError({"kind": "required"})
        if kind not in RECIPES:
            raise ValidationError(
                {"kind": f"unknown recipe {kind!r}. "
                         f"Registered: {sorted(RECIPES.keys())}"}
            )
        if not workspace_id:
            raise ValidationError({"workspace": "required"})

        # Membership check. Owner-only for v1 (mirrors video
        # create) — write surface, not read.
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise ValidationError({"workspace": "not found"})
        try:
            membership = Membership.objects.get(
                user=request.user, workspace=workspace,
            )
        except Membership.DoesNotExist:
            raise PermissionDenied("Not a member of this workspace")
        if membership.role != Membership.Role.OWNER:
            raise PermissionDenied(
                "Composition creation is restricted to workspace owners in v1"
            )

        # Resolve Episode (optional). Membership-scoped so foreign
        # Episode IDs don't disclose existence. `Composition.clean()`
        # enforces Workspace / Universe / legacy-spokesperson
        # invariants once we assign the FK below.
        episode = None
        if episode_id:
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
                raise ValidationError(
                    {"episode": "not found or not in an accessible workspace"}
                )
            if episode.universe.workspace_id != workspace.pk:
                raise ValidationError(
                    {"episode": (
                        "Episode belongs to a different workspace than the "
                        "requested composition workspace."
                    )}
                )

        recipe = get_recipe(kind)
        try:
            kwargs = resolve_kwargs(
                recipe,
                workspace=workspace,
                params=params,
                created_by=request.user,
            )
        except Teammate.DoesNotExist:
            raise ValidationError(
                {"params": "spokesperson_id not in this workspace"}
            )
        except Asset.DoesNotExist:
            raise ValidationError(
                {"params": "one of the asset ids is not in this workspace"}
            )
        except (ValueError, KeyError, TypeError) as exc:
            raise ValidationError({"params": str(exc)})

        try:
            with transaction.atomic():
                composition = recipe.starter(**kwargs)
                # SESSION 262 — attach optional Episode. The starter
                # doesn't know about Episode; we attach after it
                # returns. `Composition.clean()` validates cross-
                # Universe / cross-Workspace / legacy-spokesperson
                # invariants; failure raises ValidationError and
                # rolls back the outer atomic (composition never
                # persisted with a bad Episode attachment).
                if episode is not None:
                    composition.episode = episode
                    composition.full_clean()
                    composition.save(
                        update_fields=["episode", "updated_at"],
                    )
        except LongFormDurationError as exc:
            # SESSION 251 — long-form synthesis fell outside the ±20%
            # duration tolerance after one corrective pass. The starter
            # raises BEFORE touching Runway and BEFORE persisting the
            # failed row (see LongFormDurationError docstring: a nested
            # savepoint would be rolled back by this outer atomic).
            # Persist the FAILED row here, outside the atomic, so the
            # operator lands on the composition detail page and can see
            # exactly why the draft was rejected. Return 201 because
            # the composition IS created and the SPA's post-submit flow
            # (navigate to detail page) is correct — the FAILED status
            # itself is the operator-facing signal.
            composition = Composition.objects.create(
                workspace=exc.workspace,
                spokesperson=exc.spokesperson,
                name=exc.composition_name,
                template_kind="long_form_ad",
                mock_mode=exc.mock_mode,
                created_by=exc.created_by,
                status=CompositionStatus.FAILED,
                error_message=exc.error_message_text,
                synthesized_brief=exc.synthesized_brief,
                knowledge_chunk_ids=exc.knowledge_chunk_ids,
                verification_warnings=exc.verification_warnings,
                verification_status=exc.verification_status,
                # SESSION 262 — Composition observability. The starter
                # attached per-attempt provenance on the exception; the
                # rescue path persists it onto the FAILED row so audits
                # can reconstruct without terminal logs.
                operator_topic=exc.operator_topic,
                target_duration_seconds=exc.target_duration_seconds,
                synthesis_attempt_count=exc.synthesis_attempt_count,
                first_pass_synthesis=exc.first_pass_synthesis,
                corrective_hint=exc.corrective_hint,
                corrective_pass_synthesis=exc.corrective_pass_synthesis,
                synthesis_predicted_seconds=exc.synthesis_predicted_seconds,
                validation_failure_reason=exc.validation_failure_reason,
                # SESSION 262 / EPISODE_SCHEMA_V1 — carry the
                # optional Episode attachment through to the FAILED
                # row so retries under the same Episode keep the
                # narrative context. Composition.clean() has already
                # validated the pairing during the pre-rescue
                # `full_clean` call inside the atomic (if `episode`
                # was set); by this point we've raised past that.
                # Attach here unconditionally — invariants apply.
                episode=episode,
            )
            exc.composition_id = composition.id
            logger.warning(
                "composition long_form_ad OUT-OF-TOLERANCE composition=%s "
                "workspace=%s actual=%ds target=%ds range=%d-%ds",
                composition.id, workspace.id,
                exc.actual_seconds, exc.target_duration_seconds,
                exc.min_seconds, exc.max_seconds,
            )
            return Response(
                CompositionSerializer(composition).data,
                status=status.HTTP_201_CREATED,
            )
        except DialogueSynthesisFailedError as exc:
            # SESSION 257 / AI-D3 — dialogue AI Topic synthesis
            # rejected after one bounded corrective pass (or
            # strict K6.4 caught an unsupported claim in a
            # generated turn). Mirror the LongFormDurationError
            # handler: persist the FAILED composition row OUTSIDE
            # the outer atomic (nested savepoints don't survive
            # rollback), return 201 with the FAILED status so the
            # operator lands on the composition detail page with
            # full context. Zero avatar_video calls were dispatched.
            composition = Composition.objects.create(
                workspace=exc.workspace,
                spokesperson=exc.spokesperson,
                name=exc.composition_name,
                template_kind="dialogue_scene",
                mock_mode=exc.mock_mode,
                created_by=exc.created_by,
                status=CompositionStatus.FAILED,
                error_message=exc.error_message_text,
                rejected_synthesis=exc.rejected_synthesis,
                verification_warnings=exc.verification_warnings,
                verification_status=exc.verification_status,
                writing_contract_version=exc.writing_contract_version,
                knowledge_chunk_ids=exc.knowledge_chunk_ids,
                # SESSION 264 Slice 2 — carry narrative-memory
                # retrieval snapshot on FAILED dialogue rows.
                memory_ids=list(getattr(exc, "memory_ids", []) or []),
                synthesized_brief=exc.synthesized_brief,
                # SESSION 262 — Composition observability. Same
                # rescue pattern as the LongFormDurationError branch
                # above; the starter attaches per-attempt provenance
                # on the exception and this rescue persists it.
                operator_topic=exc.operator_topic,
                target_duration_seconds=exc.target_duration_seconds,
                synthesis_attempt_count=exc.synthesis_attempt_count,
                first_pass_synthesis=exc.first_pass_synthesis,
                corrective_hint=exc.corrective_hint,
                corrective_pass_synthesis=exc.corrective_pass_synthesis,
                synthesis_predicted_seconds=exc.synthesis_predicted_seconds,
                validation_failure_reason=exc.validation_failure_reason,
                # SESSION 262 / EPISODE_SCHEMA_V1 — carry the
                # optional Episode attachment (see LongForm branch
                # above for rationale).
                episode=episode,
            )
            exc.composition_id = composition.id
            logger.warning(
                "composition dialogue_scene AI-TOPIC REJECTED composition=%s "
                "workspace=%s reason=%s",
                composition.id, workspace.id, exc.reason,
            )
            return Response(
                CompositionSerializer(composition).data,
                status=status.HTTP_201_CREATED,
            )
        except (ValueError, DjangoValidationError) as exc:
            raise ValidationError({"params": str(exc)})

        # Fire the runtime. eager mode (tests) runs synchronously;
        # in real deployment a worker picks it up.
        execute_composition.delay(str(composition.pk))
        composition.refresh_from_db()

        logger.info(
            "composition created via recipe kind=%s composition=%s "
            "workspace=%s mock=%s",
            kind, composition.id, workspace.id, composition.mock_mode,
        )

        return Response(
            CompositionSerializer(composition).data,
            status=status.HTTP_201_CREATED,
        )


# =============================================================================
# W11.6.2 — Image generation REST surface (Media Generation V1)
# =============================================================================


class ImageViewSet(viewsets.GenericViewSet):
    """W11.6.2 — workspace-scoped image generation + library.

    Endpoints:

    * ``POST /api/images/`` — generate via Stability (purpose !=
      avatar) and persist as an ``Asset(image)`` row. Mock-mode is
      implicit (driven by ``STABILITY_API_KEY`` on the media-engine).
    * ``GET /api/images/`` — list workspace images, filterable by
      ``?workspace=`` (required for cross-workspace owners),
      ``?purpose=``, ``?model=``, ``?style_preset=``,
      ``?spokesperson=``. Newest first; capped at 200.
    * ``GET /api/images/<id>/`` — retrieve one image.
    * ``DELETE /api/images/<id>/`` — workspace-owner-only delete.

    Contract notes:
      - Contract rule 1 (purpose-routed) is honored by accepting
        the full purpose enum; the avatar wizard path is reserved
        per Contract rule 2 — ``purpose=avatar`` returns 400 with a
        pointer to the wizard. W11.7+ may relax this.
      - Stability cost in credits is converted to micros via the
        canonical 1 credit = 1000 micros factor (Contract rule 7).
      - Image bytes from Stability arrive as a base64 data URI and
        are stored directly in ``Asset.file_path`` (matches the
        spokesperson portrait pattern). Disk cache for re-use
        lives in media-engine.
    """

    permission_classes = [IsWorkspaceMember]
    serializer_class = ImageAssetSerializer

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Asset.objects.none()
        return (
            Asset.objects.filter(
                workspace__memberships__user=user,
                asset_type=AssetType.IMAGE,
            )
            .select_related("workspace", "spokesperson", "composition")
            .distinct()
        )

    def list(self, request):
        qs = self.get_queryset()
        workspace_id = request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        purpose = request.query_params.get("purpose")
        if purpose:
            qs = qs.filter(purpose=purpose)
        model_name = request.query_params.get("model")
        if model_name:
            qs = qs.filter(model=model_name)
        style_preset = request.query_params.get("style_preset")
        if style_preset:
            qs = qs.filter(style_preset=style_preset)
        spokesperson_id = request.query_params.get("spokesperson")
        if spokesperson_id:
            qs = qs.filter(spokesperson_id=spokesperson_id)
        qs = qs.order_by("-created_at")[:200]
        return Response(ImageAssetSerializer(qs, many=True).data)

    def retrieve(self, request, pk: str | None = None):
        try:
            asset = self.get_queryset().get(pk=pk)
        except Asset.DoesNotExist:
            raise NotFound("Image not found")
        self.check_object_permissions(request, asset)
        return Response(ImageAssetSerializer(asset).data)

    def destroy(self, request, pk: str | None = None):
        try:
            asset = self.get_queryset().get(pk=pk)
        except Asset.DoesNotExist:
            raise NotFound("Image not found")
        self.check_object_permissions(request, asset)
        # IsWorkspaceMember already enforced owner for mutating
        # methods via has_object_permission above.
        asset_id = asset.pk
        asset.delete()
        logger.info("image asset deleted id=%s workspace=%s",
                    asset_id, asset.workspace_id)
        return Response(status=status.HTTP_204_NO_CONTENT)

    def create(self, request):
        body = request.data or {}
        purpose = (body.get("purpose") or "").strip().lower()
        subject = (body.get("subject") or "").strip()
        workspace_id = body.get("workspace")
        model_name = body.get("model") or "sd3-large"
        style_preset = body.get("style_preset") or None
        aspect_ratio = body.get("aspect_ratio") or "16:9"
        negative_prompt_override = body.get("negative_prompt_override") or None
        spokesperson_id = body.get("spokesperson") or None
        # W11.6.5.1 — operator-facing label for pickers. Auto-
        # populated from the first ~60 chars of the subject when
        # the operator doesn't pass an explicit title. The
        # subject-as-default is the lowest-friction path; the
        # operator can override (or edit later) for distinctive
        # cases.
        title_raw = (body.get("title") or "").strip()
        title = title_raw[:120] if title_raw else _derive_title_from_subject(subject)

        # ---- payload validation -------------------------------------
        if not workspace_id:
            raise ValidationError({"workspace": "required"})
        if not subject:
            raise ValidationError({"subject": "required"})
        if not purpose:
            raise ValidationError({"purpose": "required"})
        if purpose not in IMAGE_VALID_PURPOSES:
            raise ValidationError({
                "purpose": (
                    f"unknown purpose {purpose!r}; "
                    f"valid: {sorted(IMAGE_VALID_PURPOSES)}"
                ),
            })
        if purpose == "avatar":
            # Contract rule 2 — avatar wizard owns the avatar path
            # for v1. The "iterate cheaply before baking" journey
            # (Journey 5) is best served by the ``scene`` purpose
            # with a creature-anatomy style preset, NOT by
            # circumventing the wizard.
            raise ValidationError({
                "purpose": (
                    "avatar purpose is reserved for the spokesperson "
                    "wizard in v1 (Contract rule 2). To iterate cheaply "
                    "on character concepts, use purpose=scene with a "
                    "creature-anatomy style preset."
                ),
            })
        if aspect_ratio not in STABILITY_VALID_ASPECT_RATIOS:
            raise ValidationError({
                "aspect_ratio": (
                    f"invalid aspect_ratio {aspect_ratio!r}; "
                    f"valid: {sorted(STABILITY_VALID_ASPECT_RATIOS)}"
                ),
            })
        if model_name not in STABILITY_VALID_MODELS:
            raise ValidationError({
                "model": (
                    f"unsupported model {model_name!r}; "
                    f"valid: {sorted(STABILITY_VALID_MODELS)}"
                ),
            })

        # ---- workspace + membership ---------------------------------
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except (Workspace.DoesNotExist, ValueError, DjangoValidationError):
            raise ValidationError({"workspace": "not found"})
        try:
            membership = Membership.objects.get(
                user=request.user, workspace=workspace,
            )
        except Membership.DoesNotExist:
            raise PermissionDenied("Not a member of this workspace")
        if membership.role != Membership.Role.OWNER:
            raise PermissionDenied(
                "Image generation is restricted to workspace owners in v1"
            )

        # ---- optional spokesperson linkage --------------------------
        spokesperson = None
        if spokesperson_id:
            try:
                spokesperson = Teammate.objects.get(
                    pk=spokesperson_id, workspace=workspace,
                )
            except (Teammate.DoesNotExist, ValueError, DjangoValidationError):
                raise ValidationError({
                    "spokesperson": "not in this workspace",
                })

        # ---- media-engine call --------------------------------------
        try:
            with MediaEngineClient() as client:
                result = client.create_stability_image(
                    purpose=purpose,
                    subject=subject,
                    model=model_name,
                    style_preset=style_preset,
                    aspect_ratio=aspect_ratio,
                    negative_prompt_override=negative_prompt_override,
                )
        except MediaEngineError as exc:
            logger.warning(
                "media-engine image_stability failed purpose=%s model=%s: %s",
                purpose, model_name, exc,
            )
            return Response(
                {"error": str(exc), "code": "upstream_media_engine"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # ---- persist Asset ------------------------------------------
        # file_path stores the data URI directly so the SPA can
        # render the image without a separate static-serve route.
        # The media-engine retains its sha-keyed disk cache for
        # idempotent regeneration.
        cost_micros = int(round(
            (result.cost_credits or 0.0) * _STABILITY_CREDITS_TO_MICROS
        ))
        asset = Asset.objects.create(
            workspace=workspace,
            asset_type=AssetType.IMAGE,
            file_path=result.image_data_uri,
            mime_type=result.mime_type or "image/png",
            cost_micros=cost_micros,
            purpose=result.purpose or purpose,
            model=result.model or model_name,
            style_preset=result.style_preset or "",
            prompt=result.prompt or "",
            subject=subject,
            title=title,
            negative_prompt=negative_prompt_override or "",
            aspect_ratio=result.aspect_ratio or aspect_ratio,
            spokesperson=spokesperson,
            created_by=request.user,
        )

        logger.info(
            "image asset created id=%s workspace=%s purpose=%s model=%s "
            "style=%s ratio=%s cost_credits=%.2f mock=%s",
            asset.pk, workspace.pk, purpose, asset.model, asset.style_preset,
            asset.aspect_ratio, result.cost_credits, result.mock_mode,
        )

        return Response(
            ImageAssetSerializer(asset).data,
            status=status.HTTP_201_CREATED,
        )


class StyleLibraryViewSet(viewsets.ViewSet):
    """W11.6.2 — ``GET /api/styles/``.

    Returns the categorized 42-preset style library snapshot. Pure
    proxy to the media-engine's ``/internal/styles/`` endpoint;
    cached by the SPA (the underlying data is a code-level constant
    on media-engine). Auth required so the public internet can't
    enumerate.
    """

    permission_classes = [IsAuthenticated]

    def list(self, request):
        try:
            with MediaEngineClient() as client:
                data = client.list_styles()
        except MediaEngineError as exc:
            logger.warning("media-engine list_styles failed: %s", exc)
            return Response(
                {"error": str(exc), "code": "upstream_media_engine"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(data)


# ===================================================================
# Asset Library v1 — A4 read endpoints (SESSION 188)
# ===================================================================
#
# `/api/workspace/assets/` (list, paginated) +
# `/api/workspace/assets/<id>/` (retrieve, full lineage).
#
# Distinct from the existing `/api/assets/` (AssetViewSet) which
# serves the V15.2 asset_picker dropdown — that endpoint stays as-is.
# A7 will extend AssetViewSet with the role filter; A5/A6 build the
# SPA against THIS endpoint.
#
# Workspace resolution mirrors F-arc's `/api/workspace/overview/`:
# `?workspace=<id>` if provided + member, else
# `default_workspace_for(user)`.
#
# `storage_health` is computed at serialize time via
# `apps.compositions.assets.compute_storage_health(asset)` (A3 — live
# per request, no caching for v1).
#
# Avatar / Voice / Portrait media live on Teammate (not the
# Asset table); per Q-a-6 they're deferred to v2 and this endpoint
# returns only Asset rows. A5 carries the honest gap note.


class WorkspaceAssetPagination(PageNumberPagination):
    """Pagination for the Asset Library browse view. Default 25 rows
    per page; max 100 — A5's SPA list with role+storage chips reads
    25 nicely, and the cap keeps a malicious / mis-configured
    `?page_size=10000` request from materializing the whole asset
    table."""

    page_size = 25
    page_size_query_param = "page_size"
    max_page_size = 100


def _resolve_workspace(request) -> Workspace:
    """Resolve the workspace for the request — explicit `?workspace=`
    if provided + member, else the user's default. Same pattern as
    F-arc's `workspace_overview`; raises the same exceptions so the
    SPA error handling lines up."""
    user = request.user
    workspace_id = request.query_params.get("workspace")
    if workspace_id:
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise NotFound("workspace not found")
        if not Membership.objects.filter(
            user=user, workspace=workspace,
        ).exists():
            raise PermissionDenied("not a member of this workspace")
        return workspace
    workspace = default_workspace_for(user)
    if workspace is None:
        raise ValidationError({"workspace": "user has no default workspace"})
    return workspace


def _csv_param(request, name: str) -> list[str] | None:
    """Parse a comma-list query param — `?role=BACKDROP,TALKING_HEAD`
    → ``["BACKDROP", "TALKING_HEAD"]``. Returns ``None`` when the
    param is absent so the caller can skip the filter."""
    raw = request.query_params.get(name)
    if not raw:
        return None
    values = [v.strip() for v in raw.split(",") if v.strip()]
    return values or None


def _producing_prompt(asset: Asset) -> str:
    """Best-effort extraction of the prompt-like text that produced
    this asset. Different primitives stash it under different keys
    in ``source_spec``; we read the standard ones the SPA list view
    will care about."""
    spec = asset.source_spec or {}
    for key in ("prompt", "script", "description"):
        val = spec.get(key)
        if isinstance(val, str) and val.strip():
            return val.strip()
    # ``params.prompt`` is where the recipe form payload lives for
    # most primitives — fall through there before giving up.
    params = spec.get("params") or {}
    if isinstance(params, dict):
        for key in ("prompt", "script", "subject", "description"):
            val = params.get(key)
            if isinstance(val, str) and val.strip():
                return val.strip()
    return ""


def _serialize_list_asset(asset: Asset) -> dict:
    """List-view shape — light. Lineage details land in retrieve.

    `composition` is pre-fetched via select_related, so accessing
    `asset.composition.name` doesn't fire an N+1 query."""
    comp = asset.composition
    return {
        "id": str(asset.id),
        "asset_type": asset.asset_type,
        "role": asset.role,
        "file_path": asset.file_path,
        "title": asset.title,
        "subject": asset.subject,
        "duration_ms": asset.duration_ms,
        "width": asset.width,
        "height": asset.height,
        "mime_type": asset.mime_type,
        "size_bytes": asset.size_bytes,
        "cost_micros": asset.cost_micros,
        "created_at": asset.created_at.isoformat(),
        "storage_health": compute_storage_health(asset),
        "primitive_kind": (asset.source_spec or {}).get("primitive_kind", ""),
        "producing_prompt": _producing_prompt(asset),
        "composition": (
            {
                "id": str(comp.id),
                "name": comp.name,
                "status": comp.status,
                "template_kind": comp.template_kind,
            }
            if comp is not None
            else None
        ),
    }


def _serialize_detail_asset(asset: Asset) -> dict:
    """Detail view — list shape plus producing step + downstream
    consumers. Same lineage shape as F5's
    `/api/compositions/<id>/lineage/` but inverted: F5 walks
    composition→composition; this walks asset→compositions on both
    sides.
    """
    base = _serialize_list_asset(asset)

    # Producing step (the step whose primitive emitted this asset).
    producing_step_payload: dict | None = None
    comp = asset.composition
    if comp is not None:
        step = (
            CompositionStep.objects.filter(
                composition=comp, output_asset=asset,
            )
            .first()
        )
        if step is not None:
            producing_step_payload = {
                "id": str(step.id),
                "position": step.position,
                "primitive": step.primitive,
                "params": step.params,
                "inputs": step.inputs,
                "source_spec": asset.source_spec,
            }

    # Downstream — compositions whose steps consumed this asset as
    # an input. Same `asset_id in step.inputs` scan as F5; one entry
    # per consuming composition (deduped).
    downstream: list[dict] = []
    seen_consumer_ids: set[str] = set()
    asset_id_str = str(asset.id)
    consuming_steps = (
        CompositionStep.objects.filter(
            composition__workspace=asset.workspace,
            inputs__contains=[{"asset_id": asset_id_str}],
        )
        .select_related("composition", "composition__spokesperson")
    )
    for step in consuming_steps:
        c = step.composition
        if c is None or str(c.id) in seen_consumer_ids:
            continue
        # Defensive: skip self-references in case a composition step
        # ever consumes one of its own outputs.
        if comp is not None and str(c.id) == str(comp.id):
            continue
        seen_consumer_ids.add(str(c.id))
        downstream.append({
            "id": str(c.id),
            "name": c.name,
            "status": c.status,
            "template_kind": c.template_kind,
        })

    base["producing_step"] = producing_step_payload
    base["downstream_compositions"] = downstream
    # A6: expose TRANSCRIPT body for the detail view. inline_content is
    # always present (defaults to ""); non-transcript assets return "".
    base["inline_content"] = asset.inline_content
    return base


class WorkspaceAssetViewSet(viewsets.GenericViewSet):
    """Asset Library v1 read endpoints (A4).

    Serves browse + detail for the SPA's `/workspace/assets` view
    (A5/A6). Workspace-scoped, paginated, multi-filter. Per Q-a-6
    the v1 endpoint returns Asset rows only — Avatar / Voice /
    Portrait media live on Teammate and are deferred to v2.

    Filters (all optional, all comma-separated):
      * ``role`` — TextChoices values from ``AssetRole``.
      * ``asset_type`` — TextChoices values from ``AssetType``.
      * ``primitive_kind`` — production-method filter.
      * ``storage`` — computed health states (``HTTPS_LIVE``,
        ``LOCAL_PRESENT``, ...). Applied post-query since storage
        health isn't a DB column; OK for v1's paginated reads.
      * ``q`` — case-insensitive contains over composition name +
        asset title + subject.
      * ``created_after`` / ``created_before`` — ISO-8601 dates.
    """

    permission_classes = [IsAuthenticated]
    pagination_class = WorkspaceAssetPagination

    def get_queryset(self):
        # Required by GenericViewSet; the actual filtering happens in
        # `list` after workspace resolution.
        return Asset.objects.none()

    def _base_queryset(self, workspace: Workspace):
        return (
            Asset.objects.filter(workspace=workspace)
            .select_related("workspace", "composition")
            .order_by("-created_at")
        )

    def list(self, request):
        workspace = _resolve_workspace(request)
        qs = self._base_queryset(workspace)

        # ---- role / asset_type / primitive_kind filters ----------
        roles = _csv_param(request, "role")
        if roles:
            qs = qs.filter(role__in=roles)

        asset_types = _csv_param(request, "asset_type")
        if asset_types:
            qs = qs.filter(asset_type__in=asset_types)

        primitive_kinds = _csv_param(request, "primitive_kind")
        if primitive_kinds:
            qs = qs.filter(source_spec__primitive_kind__in=primitive_kinds)

        # ---- full-text q ----------------------------------------
        q = (request.query_params.get("q") or "").strip()
        if q:
            qs = qs.filter(
                Q(title__icontains=q)
                | Q(subject__icontains=q)
                | Q(composition__name__icontains=q)
            )

        # ---- date range ----------------------------------------
        created_after = (request.query_params.get("created_after") or "").strip()
        if created_after:
            qs = qs.filter(created_at__gte=created_after)
        created_before = (request.query_params.get("created_before") or "").strip()
        if created_before:
            qs = qs.filter(created_at__lt=created_before)

        # ---- storage_health post-filter ------------------------
        # storage_health is computed, not a DB column. Apply after
        # query-time filters narrow the candidate set. For v1's
        # paginated reads this is acceptable; A5 perf testing may
        # require an annotated column later.
        storage_filter = _csv_param(request, "storage")
        valid_storage = set(StorageHealth.all())

        paginator = self.pagination_class()
        if storage_filter:
            # Need to materialize before pagination so storage
            # filtering applies across the whole filtered set, not
            # just one page. Cap at 1000 to stay sane on huge
            # workspaces — v1 SPA workflow never needs more than
            # ``max_page_size`` × few-pages.
            wanted = {s for s in storage_filter if s in valid_storage}
            if not wanted:
                # All requested storage values invalid → no matches.
                rows: list[Asset] = []
            else:
                rows = [
                    a for a in qs[:1000]
                    if compute_storage_health(a) in wanted
                ]
            page = paginator.paginate_queryset(rows, request, view=self)
        else:
            page = paginator.paginate_queryset(qs, request, view=self)

        if page is None:  # pragma: no cover — paginator always paginates
            data = [_serialize_list_asset(a) for a in qs[:25]]
            return Response(data)
        data = [_serialize_list_asset(a) for a in page]
        return paginator.get_paginated_response(data)

    def retrieve(self, request, pk: str | None = None):
        workspace = _resolve_workspace(request)
        try:
            asset = (
                self._base_queryset(workspace)
                .select_related(
                    "composition__spokesperson",
                    "spokesperson",
                )
                .get(pk=pk)
            )
        except Asset.DoesNotExist:
            raise NotFound("Asset not found")
        return Response(_serialize_detail_asset(asset))
