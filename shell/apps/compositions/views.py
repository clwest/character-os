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
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Membership, Workspace
from apps.compositions.models import Asset, Composition
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
