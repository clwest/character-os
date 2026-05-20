"""B2.3 — REST surface for the B-2 / E-arc auto-scripting arc.

One ViewSet: ``ScriptViewSet``. Actions:

* ``list`` (GET /api/scripts/) — filterable by ?status= /
  ?spokesperson= / ?verification_status=.
* ``retrieve`` (GET /api/scripts/<id>/) — full row + resolved
  ``cited_documents`` via F6's ``resolve_chunk_ids_to_docs``.
* ``create`` (POST /api/scripts/) — resolves spokesperson,
  tier-gates on ``check_drafts_per_month``, fires
  ``draft_script`` synchronously, returns the row (DRAFT
  status).
* ``regenerate`` (POST /api/scripts/<id>/regenerate/) —
  snapshots current draft to ``revision_history``, optionally
  updates prompt / opener / verifier_mode, re-fires
  ``draft_script``. Refuses on RENDERED/ARCHIVED (rule 10).
* ``approve`` (POST /api/scripts/<id>/approve/) — DRAFT →
  READY transition (rule 10). Refuses if
  ``verification_status='blocked'`` (rule 4).
* ``render`` (POST /api/scripts/<id>/render/) — requires
  status=READY. Creates an ``auto_script`` Composition via the
  starter, enqueues ``execute_composition.delay``. Flips
  Script → RENDERED on first launch.
* ``clone`` (POST /api/scripts/<id>/clone/) — produces a new
  DRAFT Script with the same prompt / opener / spokesperson +
  a fresh draft fire.
* ``destroy`` (DELETE /api/scripts/<id>/) — refuses on RENDERED
  (clone first then archive, per rule 10).
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Membership
from apps.billing.services import TierLimitExceeded, check_drafts_per_month
from apps.spokespeople.models import Spokesperson
from character_os.permissions import IsWorkspaceMember

from .models import Script
from .serializers import (
    CreateScriptSerializer,
    RegenerateScriptSerializer,
    ScriptDetailSerializer,
    ScriptListSerializer,
)
from .synthesis import (
    apply_draft_to_script,
    draft_script,
    snapshot_to_revision_history,
)

logger = logging.getLogger(__name__)


# Rule 10 — forward-only DRAFT → READY → RENDERED → ARCHIVED.
# Specific transitions refused below; centralized for clarity.
_REGENERATE_REFUSING_STATUSES = {
    Script.Status.RENDERED,
    Script.Status.ARCHIVED,
}
_APPROVE_REFUSING_STATUSES = {
    Script.Status.READY,
    Script.Status.RENDERED,
    Script.Status.ARCHIVED,
}
_DELETE_REFUSING_STATUSES = {
    Script.Status.RENDERED,
}


class ScriptViewSet(GenericViewSet):
    """Scripts at ``/api/scripts/``. v1 ships 8 actions covering
    the draft → approve → render lifecycle. Workspace-scoped via
    the shared ``IsWorkspaceMember`` permission + queryset
    filtering."""

    queryset = Script.objects.all()
    serializer_class = ScriptDetailSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Script.objects.none()
        return (
            Script.objects.filter(
                workspace__memberships__user=user,
            )
            .select_related("workspace", "spokesperson")
            .distinct()
        )

    # ---- list / retrieve / create / destroy --------------------

    def list(self, request):
        qs = self.get_queryset()
        status_filter = request.query_params.get("status")
        spokesperson_filter = request.query_params.get("spokesperson")
        verification_filter = request.query_params.get("verification_status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        if spokesperson_filter:
            qs = qs.filter(spokesperson_id=spokesperson_filter)
        if verification_filter:
            qs = qs.filter(verification_status=verification_filter)
        return Response(
            ScriptListSerializer(qs[:100], many=True).data,
        )

    def retrieve(self, request, pk=None):
        script = self._get_or_404(pk)
        return Response(ScriptDetailSerializer(script).data)

    def create(self, request):
        """Tier-gate, resolve spokesperson, fire draft_script,
        persist + return the new Script row."""
        body = CreateScriptSerializer(data=request.data or {})
        body.is_valid(raise_exception=True)
        params = body.validated_data

        spokesperson = self._resolve_workspace_spokesperson(
            request.user, params["spokesperson_id"],
        )
        workspace = spokesperson.workspace

        try:
            check_drafts_per_month(workspace)
        except TierLimitExceeded as exc:
            return Response(exc.payload, status=http.HTTP_402_PAYMENT_REQUIRED)

        # Fire synthesis BEFORE the transaction so a slow LLM
        # doesn't hold a DB transaction open. draft_script never
        # raises (rule 4 catches strict-mode internally).
        result = draft_script(
            spokesperson,
            params["prompt"],
            opener=params.get("opener") or None,
            verifier_mode=params.get("verifier_mode") or None,
        )

        with transaction.atomic():
            script = Script(
                workspace=workspace,
                spokesperson=spokesperson,
                name=params["name"].strip() or "Untitled script",
                prompt=params["prompt"],
                opener=params.get("opener") or "",
                verifier_mode=params.get("verifier_mode") or "",
                created_by=request.user,
            )
            apply_draft_to_script(script, result)
            script.full_clean()
            script.save()

        logger.info(
            "script.create id=%s workspace=%s spokesperson=%s "
            "verification=%s chunks=%d",
            script.pk, workspace.pk, spokesperson.pk,
            result.verification_status, len(result.knowledge_chunk_ids),
        )
        return Response(
            ScriptDetailSerializer(script).data,
            status=http.HTTP_201_CREATED,
        )

    def destroy(self, request, pk=None):
        """Rule 10 — RENDERED rows are immutable; clone first."""
        script = self._get_or_404(pk)
        if script.status in _DELETE_REFUSING_STATUSES:
            return Response(
                {
                    "detail": (
                        f"Cannot delete script in status "
                        f"{script.status!r}; clone first then "
                        "archive the clone."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )
        script_id = script.pk
        script.delete()
        logger.info("script.delete id=%s", script_id)
        return Response(status=http.HTTP_204_NO_CONTENT)

    # ---- regenerate ---------------------------------------------

    @action(detail=True, methods=["post"])
    def regenerate(self, request, pk=None):
        """Snapshot current draft → revision_history, re-fire
        draft_script, persist. Refuses on RENDERED/ARCHIVED."""
        script = self._get_or_404(pk)
        if script.status in _REGENERATE_REFUSING_STATUSES:
            return Response(
                {
                    "detail": (
                        f"Cannot regenerate script in status "
                        f"{script.status!r}; clone to draft a new "
                        "revision."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )

        body = RegenerateScriptSerializer(data=request.data or {})
        body.is_valid(raise_exception=True)
        params = body.validated_data

        try:
            check_drafts_per_month(script.workspace)
        except TierLimitExceeded as exc:
            return Response(exc.payload, status=http.HTTP_402_PAYMENT_REQUIRED)

        # Apply optional overrides BEFORE snapshot — the
        # revision_history entry captures the state being
        # overwritten, including the previous prompt / opener /
        # verifier_mode that produced the snapshotted draft.
        snapshot_to_revision_history(script)

        if "prompt" in params:
            script.prompt = params["prompt"]
        if "opener" in params:
            script.opener = params.get("opener") or ""
        if "verifier_mode" in params:
            script.verifier_mode = params.get("verifier_mode") or ""

        result = draft_script(
            script.spokesperson,
            script.prompt,
            opener=script.opener or None,
            verifier_mode=script.verifier_mode or None,
        )

        with transaction.atomic():
            apply_draft_to_script(script, result)
            # Regenerate snaps READY rows back to DRAFT — the
            # operator must re-approve a regenerated draft
            # before it can render. (Rule 10's forward-only
            # path treats READY→DRAFT as illegal, but the
            # state-machine "step back to DRAFT after editing"
            # is the standard CMS shape; the design doc's
            # immutability bite kicks in at RENDERED, which
            # _REGENERATE_REFUSING_STATUSES already blocks.)
            if script.status == Script.Status.READY:
                script.status = Script.Status.DRAFT
                script.approved_at = None
            script.save()

        logger.info(
            "script.regenerate id=%s verification=%s revisions=%d",
            script.pk, result.verification_status,
            len(script.revision_history or []),
        )
        return Response(ScriptDetailSerializer(script).data)

    # ---- approve ------------------------------------------------

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Rule 10 — DRAFT → READY. Sets approved_at. Refuses if
        verification_status=='blocked' (rule 4)."""
        script = self._get_or_404(pk)
        if script.status in _APPROVE_REFUSING_STATUSES:
            return Response(
                {
                    "detail": (
                        f"Cannot approve script in status "
                        f"{script.status!r}; only DRAFT scripts "
                        "can be approved."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )
        if script.verification_status == "blocked":
            return Response(
                {
                    "code": "verification_blocked",
                    "detail": (
                        "K6.4 strict-mode verifier rejected this "
                        "draft. Regenerate (operator may want to "
                        "edit the prompt) or switch to warn-mode "
                        "before approving."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )

        script.status = Script.Status.READY
        script.approved_at = timezone.now()
        script.save(update_fields=["status", "approved_at", "updated_at"])

        logger.info("script.approve id=%s", script.pk)
        return Response(ScriptDetailSerializer(script).data)

    # ---- render -------------------------------------------------

    @action(detail=True, methods=["post"])
    def render(self, request, pk=None):
        """Fire an auto_script Composition. Requires status=READY.
        Flips Script → RENDERED on first launch (rule 10)."""
        script = self._get_or_404(pk)
        if script.status != Script.Status.READY:
            return Response(
                {
                    "detail": (
                        f"Cannot render script in status "
                        f"{script.status!r}; approve first."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )

        # Lazy import — apps.compositions.starters depends on
        # apps.scripts indirectly via the TYPE_CHECKING import.
        from apps.compositions.starters import auto_script as starter

        try:
            with transaction.atomic():
                composition = starter(
                    workspace=script.workspace,
                    script=script,
                    name=f"{script.name}",
                    created_by=request.user,
                )
                # Flip Script → RENDERED. Subsequent re-fires
                # of the same Script are still allowed (rule 8
                # — same Script can fire multiple recipes /
                # variants); the immutability bite is on the
                # draft fields, not on re-rendering.
                if script.status != Script.Status.RENDERED:
                    script.status = Script.Status.RENDERED
                    script.save(update_fields=["status", "updated_at"])
        except ValueError as exc:
            return Response(
                {"detail": str(exc)},
                status=http.HTTP_400_BAD_REQUEST,
            )

        from apps.compositions.tasks import execute_composition
        execute_composition.delay(str(composition.id))

        logger.info(
            "script.render id=%s composition=%s",
            script.pk, composition.pk,
        )
        return Response({
            "script": ScriptDetailSerializer(script).data,
            "composition_id": str(composition.id),
        })

    # ---- clone --------------------------------------------------

    @action(detail=True, methods=["post"])
    def clone(self, request, pk=None):
        """Rule 10 — produce a new DRAFT Script with the same
        prompt + opener + spokesperson + a fresh draft fire."""
        source = self._get_or_404(pk)

        try:
            check_drafts_per_month(source.workspace)
        except TierLimitExceeded as exc:
            return Response(exc.payload, status=http.HTTP_402_PAYMENT_REQUIRED)

        result = draft_script(
            source.spokesperson,
            source.prompt,
            opener=source.opener or None,
            verifier_mode=source.verifier_mode or None,
        )

        with transaction.atomic():
            clone = Script(
                workspace=source.workspace,
                spokesperson=source.spokesperson,
                name=f"{source.name} (clone)",
                prompt=source.prompt,
                opener=source.opener,
                verifier_mode=source.verifier_mode,
                created_by=request.user,
            )
            apply_draft_to_script(clone, result)
            clone.full_clean()
            clone.save()

        logger.info(
            "script.clone source=%s clone=%s",
            source.pk, clone.pk,
        )
        return Response(
            ScriptDetailSerializer(clone).data,
            status=http.HTTP_201_CREATED,
        )

    # ---- derived_campaigns (BC3) --------------------------------

    @action(detail=True, methods=["get"], url_path="derived_campaigns")
    def derived_campaigns(self, request, pk=None):
        """BC3 / BC0 rule 1 — Script→Campaign back-reference
        flows via query, not schema. Returns the workspace-
        filtered, paginated list of Campaigns that derive from
        this Script.

        Q-bc-9 resolved as-proposed: standard cap at 100 +
        optional ``?status=`` filter mirroring the campaigns
        list endpoint shape.

        Empty list when no Campaigns derive from this Script
        (the common shape for any pre-BC Script).
        """
        # Lazy import — apps.scripts doesn't depend on
        # apps.campaigns at module load time.
        from apps.campaigns.models import PersonalizedCampaign

        script = self._get_or_404(pk)
        qs = (
            PersonalizedCampaign.objects
            .filter(source_script=script)
            # Defense-in-depth — only return Campaigns the user
            # has membership in. The Script being workspace-
            # filtered already covers this transitively
            # (Script.workspace == Campaign.workspace per rule 3),
            # but explicit filter keeps the contract obvious.
            .filter(workspace__memberships__user=request.user)
            .select_related("workspace", "spokesperson")
            .distinct()
        )
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        # v1 page cap — mirrors campaigns list. SPA can paginate
        # via repeat queries with status filters when a Script
        # spawns more than 100 Campaigns (extreme outlier).
        rows = list(qs.order_by("-created_at")[:100])

        payload = [
            {
                "id": str(c.pk),
                "name": c.name,
                "status": c.status,
                "recipient_count": c.recipients.count(),
                "spokesperson_name": (
                    c.spokesperson.name if c.spokesperson_id else None
                ),
                "created_at": c.created_at.isoformat(),
                "launched_at": (
                    c.launched_at.isoformat() if c.launched_at else None
                ),
            }
            for c in rows
        ]
        return Response(payload)

    # ---- helpers ------------------------------------------------

    def _get_or_404(self, pk) -> Script:
        try:
            script = self.get_queryset().get(pk=pk)
        except Script.DoesNotExist:
            raise NotFound("Script not found")
        self.check_object_permissions(self.request, script)
        return script

    def _resolve_workspace_spokesperson(
        self, user, spokesperson_id,
    ) -> Spokesperson:
        """Resolve a Spokesperson in one of the user's
        workspaces. Cross-workspace lookups return 404."""
        try:
            sp = Spokesperson.objects.select_related("workspace").get(
                pk=spokesperson_id,
            )
        except Spokesperson.DoesNotExist:
            raise NotFound("Spokesperson not found")
        is_member = Membership.objects.filter(
            user=user, workspace_id=sp.workspace_id,
        ).exists()
        if not is_member:
            raise NotFound("Spokesperson not found")
        return sp
