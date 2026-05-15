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

Workspace isolation is structural — Spokesperson + Asset
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
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import Asset, Composition, CompositionStep
from apps.spokespeople.models import Spokesperson
from character_os.permissions import IsWorkspaceMember

from .recipes import RECIPES, get_recipe, resolve_kwargs
from .serializers import CompositionSerializer, RecipeSerializer
from .tasks import execute_composition

logger = logging.getLogger(__name__)


class AssetViewSet(viewsets.GenericViewSet):
    """Read-only list of workspace assets — powers the V15.2
    `asset_picker` form field. Filters by ``workspace`` (required)
    and optional ``asset_type``.

    In v1 assets are produced by composition runs; there is no
    upload UI yet. Operators pick from previously-rendered output
    assets when wiring a layout/composite recipe.
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


class CompositionViewSet(viewsets.GenericViewSet):
    """Composition create + retrieve + list.

    Update / destroy intentionally absent in v1 — compositions
    are immutable once they start running; deleting a row
    breaks audit. Operators can mark a stuck composition
    failed via admin, not REST.
    """

    serializer_class = CompositionSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Composition.objects.none()
        return (
            Composition.objects.filter(workspace__memberships__user=user)
            .select_related("workspace", "spokesperson", "final_asset")
            .prefetch_related("steps", "steps__output_asset")
            .distinct()
        )

    def list(self, request):
        qs = self.get_queryset()
        workspace_id = request.query_params.get("workspace")
        if workspace_id:
            qs = qs.filter(workspace_id=workspace_id)
        spokesperson_id = request.query_params.get("spokesperson")
        if spokesperson_id:
            qs = qs.filter(spokesperson_id=spokesperson_id)
        # Reasonable default — V15.0 doesn't paginate yet.
        qs = qs[:100]
        return Response(CompositionSerializer(qs, many=True).data)

    def retrieve(self, request, pk: str | None = None):
        try:
            comp = self.get_queryset().get(pk=pk)
        except Composition.DoesNotExist:
            raise NotFound("Composition not found")
        self.check_object_permissions(request, comp)
        return Response(CompositionSerializer(comp).data)

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

        recipe = get_recipe(kind)
        try:
            kwargs = resolve_kwargs(
                recipe,
                workspace=workspace,
                params=params,
                created_by=request.user,
            )
        except Spokesperson.DoesNotExist:
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
