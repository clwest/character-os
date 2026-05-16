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
from apps.compositions.models import Asset, AssetType, Composition, CompositionStep
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.permissions import IsWorkspaceMember

from .recipes import RECIPES, get_recipe, resolve_kwargs
from .serializers import (
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
# rule 2 reserves the avatar wizard path for Spokesperson creation,
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
                spokesperson = Spokesperson.objects.get(
                    pk=spokesperson_id, workspace=workspace,
                )
            except (Spokesperson.DoesNotExist, ValueError, DjangoValidationError):
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
