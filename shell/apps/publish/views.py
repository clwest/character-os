"""B14.3 — REST surface for the D-arc publish-bundle arc.

One ViewSet: ``PublishBundleViewSet``. Actions:

* ``list`` (GET /api/publish_bundles/)
* ``retrieve`` (GET /api/publish_bundles/<id>/)
* ``create`` (POST /api/publish_bundles/) — body
  ``{source_clip_id, name, selected_platforms[]}``; creates
  a DRAFT bundle + 1 PublishVariant per platform (snapshot
  target_ratio + max_duration_ms from the catalog).
* ``destroy`` (DELETE /api/publish_bundles/<id>/) — Q-d-9
  immutability: DRAFT + terminal cascade; LAUNCHING /
  IN_FLIGHT refuses (409).
* ``variants`` (GET /api/publish_bundles/<id>/variants/) —
  per-variant list for the SPA grid.
* ``forecast`` (GET /api/publish_bundles/<id>/forecast/) —
  Q-d-6: ``{variant_count, projected_cost_micros: 0,
  estimated_wall_time_s, ready_to_launch, blocking_reason?}``.
* ``launch`` (POST /api/publish_bundles/<id>/launch/) — fires
  N publish_variant compositions in one atomic transaction;
  enqueues Celery after commit.
* ``retry_variant`` (POST /api/publish_bundles/<id>/retry_variant/)
  — body ``{variant_id}``. Creates a new composition;
  failed one stays in workspace as audit (Q-d / mirrors
  C-arc Q-c-6).
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError as DRFValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Membership
from apps.compositions.models import Asset, AssetType
from apps.compositions.platform_catalog import (
    all_platform_keys,
    get_platform,
)
from character_os.permissions import IsWorkspaceMember

from .models import PublishBundle, PublishVariant
from .serializers import (
    CreateBundleSerializer,
    PublishBundleSerializer,
    PublishVariantSerializer,
)
from .services import (
    check_bundle_platforms,
    estimate_bundle_wall_time_s,
)


def _resolve_source_spokesperson(source_clip: Asset):
    """The publish_variant starter needs a Teammate FK on
    the resulting Composition (V1 rule). The right answer is
    "whoever produced the source clip" — recover via the
    Asset → producing CompositionStep → Composition →
    spokesperson lineage. Fallback to the workspace's first
    spokesperson when the lineage isn't set (legacy uploads,
    smoke test assets). Raises if no spokesperson exists in
    the workspace at all (degenerate)."""
    from apps.spokespeople.models import Teammate

    step = source_clip.produced_by_step.first()
    if step is not None and step.composition is not None:
        sp = step.composition.spokesperson
        if sp is not None:
            return sp

    fallback = Teammate.objects.filter(
        workspace_id=source_clip.workspace_id,
    ).first()
    if fallback is None:
        raise ValueError(
            f"source clip {source_clip.id} has no producing-step "
            f"lineage and no spokesperson in the workspace — "
            f"cannot launch a publish bundle."
        )
    return fallback

logger = logging.getLogger(__name__)


# Q-d-9 — immutability after launch. LAUNCHING / IN_FLIGHT
# refuse delete.
_DELETE_REFUSING_STATUSES = {
    PublishBundle.Status.LAUNCHING,
    PublishBundle.Status.IN_FLIGHT,
}


class PublishBundleViewSet(GenericViewSet):
    """Publish bundles at ``/api/publish_bundles/``. v1 ships
    8 actions covering the full draft → launch → retry
    lifecycle. Workspace-scoped via the shared
    ``IsWorkspaceMember`` permission + queryset filtering."""

    queryset = PublishBundle.objects.all()
    serializer_class = PublishBundleSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return PublishBundle.objects.none()
        return (
            PublishBundle.objects.filter(
                workspace__memberships__user=user,
            )
            .select_related("workspace", "source_clip")
            .distinct()
        )

    # ---- list / retrieve / create / destroy --------------------

    def list(self, request):
        qs = self.get_queryset()
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        return Response(
            PublishBundleSerializer(qs[:100], many=True).data,
        )

    def retrieve(self, request, pk=None):
        bundle = self._get_or_404(pk)
        return Response(PublishBundleSerializer(bundle).data)

    def create(self, request):
        """Create a DRAFT bundle + N PublishVariant rows
        snapshotted from the catalog."""
        body = CreateBundleSerializer(data=request.data or {})
        body.is_valid(raise_exception=True)
        params = body.validated_data

        source_clip = self._resolve_workspace_clip(
            request.user, params["source_clip_id"],
        )
        workspace = source_clip.workspace

        with transaction.atomic():
            bundle = PublishBundle(
                workspace=workspace,
                source_clip=source_clip,
                name=params["name"].strip() or "Untitled bundle",
                selected_platforms=list(params["selected_platforms"]),
                created_by=request.user,
            )
            bundle.full_clean()
            bundle.save()

            # Snapshot catalog values onto each variant at
            # create time (rule 7).
            variants = [
                PublishVariant(
                    bundle=bundle,
                    platform_key=key,
                    target_ratio=get_platform(key).target_ratio,
                    max_duration_ms=get_platform(key).max_duration_ms,
                )
                for key in params["selected_platforms"]
            ]
            PublishVariant.objects.bulk_create(variants)

        logger.info(
            "publish_bundle.create workspace=%s source=%s platforms=%s",
            workspace.pk, source_clip.pk, params["selected_platforms"],
        )
        return Response(
            PublishBundleSerializer(bundle).data,
            status=http.HTTP_201_CREATED,
        )

    def destroy(self, request, pk=None):
        """Q-d-9 immutability. DRAFT + terminal cascade-delete;
        LAUNCHING / IN_FLIGHT returns 409."""
        bundle = self._get_or_404(pk)
        if bundle.status in _DELETE_REFUSING_STATUSES:
            return Response(
                {
                    "detail": (
                        f"Cannot delete bundle in status "
                        f"{bundle.status!r}; wait for fan-out "
                        f"to complete or fail."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )
        bundle_id = bundle.pk
        bundle.delete()
        logger.info("publish_bundle.delete id=%s", bundle_id)
        return Response(status=http.HTTP_204_NO_CONTENT)

    # ---- variants sub-list -------------------------------------

    @action(detail=True, methods=["get"], url_path="variants")
    def variants_action(self, request, pk=None):
        bundle = self._get_or_404(pk)
        qs = bundle.variants.select_related(
            "produced_composition",
        ).order_by("platform_key")
        return Response(
            PublishVariantSerializer(qs, many=True).data,
        )

    # ---- forecast (Q-d-6) --------------------------------------

    @action(detail=True, methods=["get"])
    def forecast(self, request, pk=None):
        """Cost preview + tier status for the launch modal.
        Never raises; ``ready_to_launch=false`` carries the
        structured ``blocking_reason``."""
        bundle = self._get_or_404(pk)
        variant_count = bundle.variants.count()

        ready_to_launch = True
        blocking_reason: dict | None = None

        if bundle.status != PublishBundle.Status.DRAFT:
            ready_to_launch = False
            blocking_reason = {
                "code": "bundle_not_draft",
                "message": (
                    f"Bundle is in status {bundle.status!r}; "
                    "only DRAFT bundles can launch."
                ),
            }
        elif variant_count == 0:
            ready_to_launch = False
            blocking_reason = {
                "code": "no_variants",
                "message": (
                    "Bundle has no variants. Select platforms "
                    "before launching."
                ),
            }
        else:
            try:
                check_bundle_platforms(bundle.selected_platforms)
            except DRFValidationError as exc:
                ready_to_launch = False
                blocking_reason = {
                    "code": "platforms_invalid",
                    "message": str(exc),
                }
            except Exception as exc:  # ValidationError from clean
                ready_to_launch = False
                blocking_reason = {
                    "code": "platforms_invalid",
                    "message": str(exc),
                }

        return Response({
            "variant_count": variant_count,
            "projected_cost_micros": 0,  # rule 5 — ffmpeg only
            "estimated_wall_time_s": estimate_bundle_wall_time_s(variant_count),
            "ready_to_launch": ready_to_launch,
            "blocking_reason": blocking_reason,
        })

    # ---- launch ------------------------------------------------

    @action(detail=True, methods=["post"])
    def launch(self, request, pk=None):
        """Atomic fan-out: fire one ``publish_variant``
        composition per PENDING variant; flip variants to
        QUEUED; enqueue Celery after commit.

        Per-variant starter failures (e.g. source clip
        duration_ms is None — degenerate case caught by the
        starter's ValueError) flip THAT variant to FAILED
        with the message but don't bail the bundle (rule 3).
        """
        bundle = self._get_or_404(pk)

        if bundle.status != PublishBundle.Status.DRAFT:
            return Response(
                {
                    "detail": (
                        f"Cannot launch bundle in status "
                        f"{bundle.status!r}; only DRAFT bundles "
                        "can launch."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )

        variants = list(
            bundle.variants
            .filter(status=PublishVariant.Status.PENDING)
            .order_by("platform_key")
        )
        if not variants:
            return Response(
                {
                    "detail": (
                        "Bundle has no PENDING variants to launch."
                    ),
                },
                status=http.HTTP_400_BAD_REQUEST,
            )

        # Defense-in-depth platform cap.
        try:
            check_bundle_platforms(bundle.selected_platforms)
        except Exception as exc:
            return Response(
                {"detail": str(exc)},
                status=http.HTTP_400_BAD_REQUEST,
            )

        # Lazy import — apps.compositions.starters depends on
        # apps.publish indirectly (catalog) so keep the
        # publish→compositions direction one-way via lazy.
        from apps.compositions.starters import publish_variant as starter

        queued_composition_ids: list[str] = []
        with transaction.atomic():
            bundle.status = PublishBundle.Status.LAUNCHING
            bundle.launched_at = timezone.now()
            bundle.save(update_fields=[
                "status", "launched_at", "updated_at",
            ])

            for variant in variants:
                try:
                    composition = starter(
                        workspace=bundle.workspace,
                        spokesperson=_resolve_source_spokesperson(
                            bundle.source_clip,
                        ),
                        source_clip=bundle.source_clip,
                        target_ratio=variant.target_ratio,
                        max_duration_ms=variant.max_duration_ms,
                        name=(
                            f"{bundle.name} — "
                            f"{get_platform(variant.platform_key).display}"
                        )[:200],
                        created_by=request.user,
                    )
                except Exception as exc:
                    variant.status = PublishVariant.Status.FAILED
                    variant.error_message = (
                        f"starter failed: {exc!s}"[:500]
                    )
                    variant.save(update_fields=[
                        "status", "error_message", "updated_at",
                    ])
                    continue

                variant.status = PublishVariant.Status.QUEUED
                variant.produced_composition = composition
                variant.error_message = ""
                variant.save(update_fields=[
                    "status", "produced_composition",
                    "error_message", "updated_at",
                ])
                queued_composition_ids.append(str(composition.id))

            # Roll up.
            if queued_composition_ids:
                bundle.status = PublishBundle.Status.IN_FLIGHT
            else:
                bundle.status = PublishBundle.Status.FAILED
                bundle.completed_at = timezone.now()
            bundle.save(update_fields=[
                "status", "completed_at", "updated_at",
            ])

        # Enqueue after commit so the worker can't race the rows.
        from apps.compositions.tasks import execute_composition
        for composition_id in queued_composition_ids:
            execute_composition.delay(composition_id)

        logger.info(
            "publish_bundle.launch id=%s queued=%d failed=%d",
            bundle.pk, len(queued_composition_ids),
            len(variants) - len(queued_composition_ids),
        )

        bundle.refresh_from_db()
        return Response({
            "bundle": PublishBundleSerializer(bundle).data,
            "queued_count": len(queued_composition_ids),
            "failed_at_start_count": (
                len(variants) - len(queued_composition_ids)
            ),
        })

    # ---- retry_variant -----------------------------------------

    @action(detail=True, methods=["post"], url_path="retry_variant")
    def retry_variant_action(self, request, pk=None):
        """Per-variant retry. Creates a NEW composition (old
        failed one stays for audit). Resets variant to QUEUED;
        flips bundle back to IN_FLIGHT if terminal."""
        bundle = self._get_or_404(pk)
        variant_id = (request.data or {}).get("variant_id")
        if not variant_id:
            return Response(
                {"detail": "variant_id is required"},
                status=http.HTTP_400_BAD_REQUEST,
            )

        try:
            variant = bundle.variants.get(pk=variant_id)
        except PublishVariant.DoesNotExist:
            raise NotFound("Variant not found in this bundle")

        if variant.status != PublishVariant.Status.FAILED:
            return Response(
                {
                    "detail": (
                        f"Cannot retry variant in status "
                        f"{variant.status!r}; only FAILED rows "
                        "are retryable."
                    ),
                },
                status=http.HTTP_400_BAD_REQUEST,
            )

        from apps.compositions.starters import publish_variant as starter

        with transaction.atomic():
            try:
                composition = starter(
                    workspace=bundle.workspace,
                    spokesperson=_resolve_source_spokesperson(
                        bundle.source_clip,
                    ),
                    source_clip=bundle.source_clip,
                    target_ratio=variant.target_ratio,
                    max_duration_ms=variant.max_duration_ms,
                    name=(
                        f"{bundle.name} — "
                        f"{get_platform(variant.platform_key).display} (retry)"
                    )[:200],
                    created_by=request.user,
                )
            except Exception as exc:
                variant.error_message = (
                    f"starter failed: {exc!s}"[:500]
                )
                variant.save(update_fields=[
                    "error_message", "updated_at",
                ])
                return Response(
                    {"detail": str(exc)},
                    status=http.HTTP_400_BAD_REQUEST,
                )

            # Failed composition stays for audit per Q-c-6/Q-d.
            variant.produced_composition = composition
            variant.status = PublishVariant.Status.QUEUED
            variant.error_message = ""
            variant.save(update_fields=[
                "produced_composition", "status",
                "error_message", "updated_at",
            ])

            # Flip bundle back to IN_FLIGHT if it had rolled
            # to a terminal state.
            terminal = {
                PublishBundle.Status.COMPLETED,
                PublishBundle.Status.PARTIAL,
                PublishBundle.Status.FAILED,
            }
            if bundle.status in terminal:
                bundle.status = PublishBundle.Status.IN_FLIGHT
                bundle.completed_at = None
                bundle.save(update_fields=[
                    "status", "completed_at", "updated_at",
                ])

        from apps.compositions.tasks import execute_composition
        execute_composition.delay(str(composition.id))

        logger.info(
            "publish_bundle.retry_variant bundle=%s variant=%s "
            "new_composition=%s",
            bundle.pk, variant.pk, composition.pk,
        )

        variant.refresh_from_db()
        bundle.refresh_from_db()
        return Response({
            "variant": PublishVariantSerializer(variant).data,
            "bundle_status": bundle.status,
        })

    # ---- helpers ------------------------------------------------

    def _get_or_404(self, pk) -> PublishBundle:
        try:
            bundle = self.get_queryset().get(pk=pk)
        except PublishBundle.DoesNotExist:
            raise NotFound("Publish bundle not found")
        self.check_object_permissions(self.request, bundle)
        return bundle

    def _resolve_workspace_clip(self, user, asset_id) -> Asset:
        """Resolve a CLIP Asset in one of the user's
        workspaces. Cross-workspace lookups return 404."""
        try:
            asset = Asset.objects.get(pk=asset_id)
        except Asset.DoesNotExist:
            raise NotFound("Source clip not found")
        if asset.asset_type != AssetType.CLIP:
            raise NotFound("Source asset is not a CLIP")
        is_member = Membership.objects.filter(
            user=user, workspace_id=asset.workspace_id,
        ).exists()
        if not is_member:
            raise NotFound("Source clip not found")
        return asset
