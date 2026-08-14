"""DRF viewsets for accounts: Workspace, Membership.

Also hosts the ``/api/me/`` endpoint that the SPA hits after auth to
discover the current user + their default workspace, and the F3
``/api/workspace/overview/`` cross-cut endpoint that powers the
workspace fabric dashboard.
"""
from __future__ import annotations

from django.db import transaction
from django.db.models import Count, Sum
from rest_framework import mixins, viewsets
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.exceptions import NotFound, PermissionDenied, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.request import Request
from rest_framework.response import Response

from character_os.permissions import IsWorkspaceMember

from .models import Membership, Workspace, default_workspace_for
from .serializers import MembershipSerializer, WorkspaceSerializer


class WorkspaceViewSet(viewsets.ModelViewSet):
    """CRUD on the workspaces the requesting user is a member of.

    On create, the requesting user becomes the workspace owner AND
    gets an owner-role Membership in one atomic transaction.
    """

    serializer_class = WorkspaceSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Workspace.objects.none()
        return Workspace.objects.filter(memberships__user=user).distinct()

    @transaction.atomic
    def perform_create(self, serializer):
        workspace = serializer.save(owner=self.request.user)
        Membership.objects.create(
            user=self.request.user,
            workspace=workspace,
            role=Membership.Role.OWNER,
        )

    @action(detail=True, methods=["get"])
    def members(self, request, pk=None):
        """List memberships in this workspace."""
        workspace = self.get_object()
        memberships = workspace.memberships.select_related("user").all()
        serializer = MembershipSerializer(memberships, many=True, context={"request": request})
        return Response(serializer.data)


class MembershipViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    viewsets.GenericViewSet,
):
    """Read-only listing of the requesting user's memberships."""

    serializer_class = MembershipSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Membership.objects.none()
        return Membership.objects.filter(user=user).select_related("workspace", "user")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def workspace_overview(request: Request) -> Response:
    """Cross-cut workspace summary for the F3 fabric dashboard.

    Returns a single aggregate shape — spokespeople (each with
    composition + doc badges), knowledge corpus stats, and
    recent compositions. The SPA dashboard's three tiles all
    consume slices of this one response so a fresh dashboard
    render is a single roundtrip.

    Workspace-scoped: the caller must be a member of the
    requested workspace. Falls back to the user's default
    workspace when ``?workspace=`` is omitted.

    F0 contract rule 1: zero new persistence. Every field is
    a query over existing models.
    """
    # Defer imports until the view runs — these apps may not be
    # loaded at module-import time in some test setups, and we
    # want this view file to stay light.
    from apps.compositions.models import Composition, CompositionStatus
    from apps.embeddings.models import (
        IngestedVia,
        KnowledgeDocument,
    )
    from apps.embeddings.retrieval import count_chunks_for_workspace
    from apps.spokespeople.models import Teammate

    user = request.user
    workspace_id = request.query_params.get("workspace")
    if workspace_id:
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise NotFound("workspace not found")
        if not Membership.objects.filter(user=user, workspace=workspace).exists():
            raise PermissionDenied("not a member of this workspace")
    else:
        workspace = default_workspace_for(user)
        if workspace is None:
            raise ValidationError(
                {"workspace": "user has no default workspace"}
            )

    # ---- Spokespeople with badges ----------------------------
    spokespeople = (
        Teammate.objects.filter(workspace=workspace)
        .annotate(
            composition_count=Count("compositions", distinct=True),
            attached_docs_count=Count("knowledge_documents", distinct=True),
        )
        .order_by("name")
    )
    spokespeople_payload = [
        {
            "id": str(sp.id),
            "name": sp.name,
            "status": sp.status,
            "tone_archetype": sp.tone_archetype,
            "runway_avatar_id": sp.runway_avatar_id,
            "portrait_path": sp.portrait_path,
            "composition_count": sp.composition_count,
            "attached_docs_count": sp.attached_docs_count,
        }
        for sp in spokespeople
    ]

    # ---- Knowledge corpus stats ------------------------------
    docs_qs = KnowledgeDocument.objects.filter(
        workspace=workspace, is_active=True,
    )
    doc_count = docs_qs.count()
    # Chunk count runs through the sanctioned retrieval surface
    # so the K0 contract (rule 2: only retrieval.py touches
    # chunk-level models) stays intact.
    chunk_count = count_chunks_for_workspace(workspace)
    source_mix_rows = (
        docs_qs.values("ingested_via")
        .annotate(c=Count("id"))
        .order_by("ingested_via")
    )
    # Seed all enum keys so the SPA can render fixed-order
    # entries even when a source has zero docs.
    source_mix = {choice.value: 0 for choice in IngestedVia}
    for row in source_mix_rows:
        source_mix[row["ingested_via"]] = row["c"]
    most_recent_doc = docs_qs.order_by("-created_at").first()
    knowledge_payload = {
        "doc_count": doc_count,
        "chunk_count": chunk_count,
        "source_mix": source_mix,
        "most_recent": (
            {
                "id": str(most_recent_doc.id),
                "title": most_recent_doc.title,
                "document_type": most_recent_doc.document_type,
                "ingested_via": most_recent_doc.ingested_via,
                "created_at": most_recent_doc.created_at.isoformat(),
            }
            if most_recent_doc
            else None
        ),
    }

    # ---- Compositions: activity feed -------------------------
    comps_qs = (
        Composition.objects.filter(workspace=workspace)
        .select_related("spokesperson")
    )
    running_count = comps_qs.filter(
        status__in=[
            CompositionStatus.DRAFT,
            CompositionStatus.PLANNING,
            CompositionStatus.RUNNING,
        ],
    ).count()
    total_count = comps_qs.count()
    total_cost = (
        comps_qs.aggregate(Sum("cost_actual_micros"))["cost_actual_micros__sum"]
        or 0
    )
    recent_compositions = list(comps_qs.order_by("-created_at")[:10])
    compositions_payload = {
        "running_count": running_count,
        "total_count": total_count,
        "total_cost_micros": total_cost,
        "recent": [
            {
                "id": str(c.id),
                "name": c.name,
                "template_kind": c.template_kind,
                "status": c.status,
                "spokesperson_id": str(c.spokesperson_id) if c.spokesperson_id else None,
                "spokesperson_name": c.spokesperson.name if c.spokesperson_id else None,
                "mock_mode": c.mock_mode,
                "cost_actual_micros": c.cost_actual_micros,
                "created_at": c.created_at.isoformat(),
            }
            for c in recent_compositions
        ],
    }

    # ---- Cost breakdown (K7.1) -------------------------------
    # Per-surface cost rollup so operators can see where their
    # spend lives. compositions_micros mirrors the existing
    # compositions.total_cost_micros (kept for back-compat);
    # images_micros sums W11.6 image-asset costs; realtime_micros
    # sums R-arc session actuals. mtd_micros is the same
    # aggregation but scoped to the current calendar-month
    # (workspace timezone deferred to W12; UTC for v1).
    from datetime import datetime, timezone as _tz
    from apps.compositions.models import Asset, AssetType
    from apps.realtime.models import RealtimeSession

    now_utc = datetime.now(_tz.utc)
    month_start = now_utc.replace(
        day=1, hour=0, minute=0, second=0, microsecond=0,
    )

    image_assets_qs = Asset.objects.filter(
        workspace=workspace, asset_type=AssetType.IMAGE,
    )
    realtime_qs = RealtimeSession.objects.filter(workspace=workspace)

    def _sum_micros(qs, field: str) -> int:
        return qs.aggregate(Sum(field))[f"{field}__sum"] or 0

    compositions_micros = total_cost
    images_micros = _sum_micros(image_assets_qs, "cost_micros")
    realtime_micros = _sum_micros(realtime_qs, "cost_actual_micros")
    total_micros = compositions_micros + images_micros + realtime_micros

    mtd_compositions = _sum_micros(
        comps_qs.filter(created_at__gte=month_start),
        "cost_actual_micros",
    )
    mtd_images = _sum_micros(
        image_assets_qs.filter(created_at__gte=month_start),
        "cost_micros",
    )
    mtd_realtime = _sum_micros(
        realtime_qs.filter(created_at__gte=month_start),
        "cost_actual_micros",
    )
    mtd_micros = mtd_compositions + mtd_images + mtd_realtime

    cost_breakdown = {
        "compositions_micros": compositions_micros,
        "images_micros": images_micros,
        "realtime_micros": realtime_micros,
        "total_micros": total_micros,
        "mtd_micros": mtd_micros,
        "mtd_compositions_micros": mtd_compositions,
        "mtd_images_micros": mtd_images,
        "mtd_realtime_micros": mtd_realtime,
        "month_start": month_start.isoformat(),
    }

    return Response(
        {
            "workspace": {
                "id": str(workspace.id),
                "name": workspace.name,
                "slug": workspace.slug,
            },
            "spokespeople": spokespeople_payload,
            "knowledge": knowledge_payload,
            "compositions": compositions_payload,
            "cost_breakdown": cost_breakdown,
        }
    )


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def provider_health(request: Request) -> Response:
    """Provider observability endpoint — P1 slice 2.2.

    Returns a truthful snapshot of provider *configuration* and
    (where a safe probe exists) *reachability*. **This endpoint
    does not invoke paid providers.** ``mode="real"`` means the
    real adapter would be selected; it is not a claim that any
    workflow succeeded.

    Query params:
      * ``workspace=<id>`` — optional. When supplied, the
        ``engine_bridge`` row uses the per-workspace resolver
        (evaluates ``EngineConnection`` + env fallback). Requires
        the caller to be a member of that workspace. When absent,
        ``engine_bridge`` reports env-fallback state only.

    Response contract lives in
    ``character_os/provider_status.py`` module docstring and in
    ``docs/production-readiness/REAL_MODE_PROVIDER_RUNBOOK.md``
    §2.4.
    """
    from character_os.provider_status import build_provider_report

    from django.core.exceptions import ValidationError as DjangoValidationError

    workspace: Workspace | None = None
    workspace_id = request.query_params.get("workspace")
    if workspace_id:
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except (Workspace.DoesNotExist, ValueError, DjangoValidationError):
            raise NotFound("workspace not found")
        if not Membership.objects.filter(
            user=request.user, workspace=workspace,
        ).exists():
            raise PermissionDenied("not a member of this workspace")

    report = build_provider_report(workspace=workspace)
    return Response(report.to_dict())


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def me(request: Request) -> Response:
    """Identity endpoint for the SPA.

    Returns the current user plus their default workspace + role. The
    SPA hits this after auth as its first call — gives it everything
    it needs to render the dashboard without a follow-up roundtrip.
    """
    user = request.user
    workspace = default_workspace_for(user)
    payload: dict = {
        "id": user.id,
        "email": user.email,
        "is_staff": user.is_staff,
        "default_workspace": None,
    }
    if workspace is not None:
        membership = workspace.memberships.filter(user=user).first()
        payload["default_workspace"] = {
            "id": str(workspace.id),
            "name": workspace.name,
            "slug": workspace.slug,
            "role": membership.role if membership else None,
        }
    return Response(payload)
