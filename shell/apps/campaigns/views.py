"""B3.4 — REST surface for the personalized-video arc.

One ViewSet: ``CampaignViewSet``. Actions:

* ``list`` (GET /api/campaigns/) — recent campaigns for the
  user's workspace memberships, filterable by ``?status=``.
* ``retrieve`` (GET /api/campaigns/<id>/) — single campaign
  + per-status recipient counts.
* ``create`` (POST /api/campaigns/) — create a DRAFT
  campaign. Parses template placeholders + persists them on
  the row. Returns the row.
* ``destroy`` (DELETE /api/campaigns/<id>/) — DRAFT +
  terminal-state cascades; LAUNCHING / IN_FLIGHT refuses
  (409). Per Q-c-9.
* ``parse_csv`` (POST /api/campaigns/<id>/parse_csv/) —
  body ``{csv_text}``. Replaces this campaign's recipient
  rows with the parse result. DRAFT-only (active campaigns
  refuse).
* ``recipients`` (GET /api/campaigns/<id>/recipients/) —
  paginated recipient list for the SPA grid.

B3.5 will add ``forecast`` + ``launch`` actions; B3.6 adds
the per-recipient retry action. This slice is the read +
draft-edit surface.
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

from apps.accounts.models import Membership, Workspace
from apps.billing.models import tier_limit
from apps.billing.services import (
    TierLimitExceeded,
    get_usage,
)
from apps.spokespeople.models import Spokesperson
from character_os.csv_recipients import derive_label, parse_csv
from character_os.permissions import IsWorkspaceMember
from character_os.template_renderer import (
    TemplateError,
    parse_placeholders,
    render_template,
)

from .cost import (
    PER_RECIPIENT_COST_MICROS,
    estimate_campaign_cost_micros,
)
from .models import PersonalizedCampaign, PersonalizedRecipient
from .serializers import (
    CreateCampaignSerializer,
    ParseCsvSerializer,
    PersonalizedCampaignSerializer,
    PersonalizedRecipientSerializer,
)
from .services import check_personalized_batch

logger = logging.getLogger(__name__)


# Q-c-9 — which campaign statuses refuse a delete request.
_DELETE_REFUSING_STATUSES = {
    PersonalizedCampaign.Status.LAUNCHING,
    PersonalizedCampaign.Status.IN_FLIGHT,
}


class CampaignViewSet(GenericViewSet):
    """Personalized-video campaigns.

    Read + draft-edit surface in B3.4. B3.5 adds forecast +
    launch; B3.6 adds per-recipient retry.
    """

    queryset = PersonalizedCampaign.objects.all()
    serializer_class = PersonalizedCampaignSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return PersonalizedCampaign.objects.none()
        return (
            PersonalizedCampaign.objects.filter(
                workspace__memberships__user=user,
            )
            .select_related("workspace", "spokesperson", "created_by")
            .distinct()
        )

    # ---- list / retrieve / create / delete ---------------------

    def list(self, request):
        qs = self.get_queryset()
        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)
        # v1 page cap — list view returns at most 100;
        # operator can filter by status to narrow.
        return Response(
            PersonalizedCampaignSerializer(qs[:100], many=True).data,
        )

    def retrieve(self, request, pk=None):
        campaign = self._get_or_404(pk)
        return Response(PersonalizedCampaignSerializer(campaign).data)

    def create(self, request):
        """Create a DRAFT campaign.

        Validates:
        * workspace_id resolves to a workspace the user is a
          member of (404 otherwise).
        * spokesperson_id resolves to a spokesperson in that
          workspace (404 otherwise).
        * template parses cleanly (400 on syntax error via
          the serializer-level validate_template hook).
        """
        body = CreateCampaignSerializer(data=request.data or {})
        body.is_valid(raise_exception=True)
        params = body.validated_data

        workspace = self._resolve_member_workspace(
            request.user, params["workspace_id"],
        )
        spokesperson = self._resolve_workspace_spokesperson(
            workspace, params["spokesperson_id"],
        )

        # Recompute placeholders here — the validator already
        # checked syntax; this is the canonical persistence.
        placeholders = parse_placeholders(params["template"])

        campaign = PersonalizedCampaign(
            workspace=workspace,
            spokesperson=spokesperson,
            name=params["name"].strip() or "Untitled campaign",
            template=params["template"],
            placeholders=placeholders,
            created_by=request.user,
        )
        campaign.full_clean()  # cross-workspace guard
        campaign.save()
        logger.info(
            "campaign.create workspace=%s spokesperson=%s "
            "placeholders=%d",
            workspace.pk, spokesperson.pk, len(placeholders),
        )
        return Response(
            PersonalizedCampaignSerializer(campaign).data,
            status=http.HTTP_201_CREATED,
        )

    def destroy(self, request, pk=None):
        """Q-c-9 — refuses LAUNCHING / IN_FLIGHT. Other
        statuses cascade-delete recipients via the FK
        on_delete; produced compositions stay in the
        workspace as audit (recipient.produced_composition
        is SET_NULL, so the cascade stops at the recipient
        row)."""
        campaign = self._get_or_404(pk)
        if campaign.status in _DELETE_REFUSING_STATUSES:
            return Response(
                {
                    "detail": (
                        f"Cannot delete campaign in status "
                        f"{campaign.status!r}; wait for fan-out "
                        f"to complete or fail."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )
        campaign_id = campaign.pk
        campaign.delete()
        logger.info("campaign.delete id=%s status=%s",
                    campaign_id, campaign.status)
        return Response(status=http.HTTP_204_NO_CONTENT)

    # ---- parse_csv ---------------------------------------------

    @action(detail=True, methods=["post"], url_path="parse_csv")
    def parse_csv_action(self, request, pk=None):
        """Replace this campaign's recipient list with the
        parsed CSV body.

        v1 simplification: REPLACE on every paste (DRAFT-only).
        Operator wanting "add 3 more" pastes the full CSV
        again. The CSV body is small enough that this is
        cheaper than supporting append-with-dedupe.

        Returns the parse result + the persisted rows.
        """
        campaign = self._get_or_404(pk)
        if campaign.status != PersonalizedCampaign.Status.DRAFT:
            return Response(
                {
                    "detail": (
                        f"Cannot re-parse CSV for a campaign in "
                        f"status {campaign.status!r}; recipients "
                        f"are locked after launch."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )

        body = ParseCsvSerializer(data=request.data or {})
        body.is_valid(raise_exception=True)

        result = parse_csv(
            body.validated_data["csv_text"],
            campaign.placeholders,
        )

        if result.header_error:
            # Don't touch existing recipients on a header-level
            # rejection — operator fixes their paste + retries.
            return Response(
                {
                    "header_error": result.header_error,
                    "header": result.header,
                    "valid_count": 0,
                    "rejected_count": 0,
                    "rejected_rows": [],
                },
                status=http.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():
            # REPLACE — drop the prior recipient list.
            campaign.recipients.all().delete()
            new_rows: list[PersonalizedRecipient] = []
            for idx, variables in enumerate(result.valid_rows, start=1):
                row = PersonalizedRecipient(
                    campaign=campaign,
                    variables=variables,
                    label=derive_label(variables, position=idx),
                    position=idx,
                    status=PersonalizedRecipient.Status.PENDING,
                )
                new_rows.append(row)
            PersonalizedRecipient.objects.bulk_create(new_rows)

        logger.info(
            "campaign.parse_csv id=%s valid=%d rejected=%d",
            campaign.pk, len(new_rows), len(result.rejected_rows),
        )

        return Response({
            "header": result.header,
            "valid_count": len(new_rows),
            "rejected_count": len(result.rejected_rows),
            "rejected_rows": [
                {"row_number": r.row_number, "error": r.error, "raw": r.raw}
                for r in result.rejected_rows
            ],
            "recipients": PersonalizedRecipientSerializer(
                campaign.recipients.order_by("position"), many=True,
            ).data,
        })

    # ---- recipients sub-list -----------------------------------

    @action(detail=True, methods=["get"], url_path="recipients")
    def recipients_action(self, request, pk=None):
        campaign = self._get_or_404(pk)
        qs = campaign.recipients.select_related(
            "produced_composition",
        ).order_by("position")
        return Response(
            PersonalizedRecipientSerializer(qs, many=True).data,
        )

    # ---- forecast (B3.5) ---------------------------------------

    @action(detail=True, methods=["get"])
    def forecast(self, request, pk=None):
        """Cost preview + tier-gate status for the launch
        modal. Never mutates; doesn't raise on gate failure
        (returns ``ready_to_launch=False`` with a structured
        ``blocking_reason``).
        """
        campaign = self._get_or_404(pk)
        recipient_count = campaign.recipients.count()
        usage = get_usage(campaign.workspace)
        batch_cap = tier_limit(usage.tier, "personalized_batch_max")
        videos_remaining = (
            None
            if usage.videos_limit is None
            else max(0, usage.videos_limit - usage.videos_used)
        )

        # Determine blocker (if any) without raising.
        blocking_reason: dict | None = None
        ready_to_launch = True

        if campaign.status != PersonalizedCampaign.Status.DRAFT:
            ready_to_launch = False
            blocking_reason = {
                "code": "campaign_not_draft",
                "message": (
                    f"Campaign is in status {campaign.status!r}; "
                    "only DRAFT campaigns can launch."
                ),
            }
        elif recipient_count == 0:
            ready_to_launch = False
            blocking_reason = {
                "code": "no_recipients",
                "message": (
                    "Campaign has no recipients. Paste a CSV "
                    "before launching."
                ),
            }
        else:
            try:
                check_personalized_batch(
                    campaign.workspace, recipient_count,
                )
            except TierLimitExceeded as exc:
                ready_to_launch = False
                blocking_reason = exc.payload

        return Response({
            "recipient_count": recipient_count,
            "batch_cap": batch_cap,
            "videos_per_month_limit": usage.videos_limit,
            "videos_used_this_month": usage.videos_used,
            "videos_remaining": videos_remaining,
            "projected_cost_micros": estimate_campaign_cost_micros(
                recipient_count,
            ),
            "per_recipient_cost_micros": PER_RECIPIENT_COST_MICROS,
            "ready_to_launch": ready_to_launch,
            "blocking_reason": blocking_reason,
        })

    # ---- launch (B3.5) -----------------------------------------

    @action(detail=True, methods=["post"])
    def launch(self, request, pk=None):
        """Tier-gate + atomic fan-out of N talking_head_polished
        compositions.

        Rule 4 — runs BOTH tier gates (per-batch cap +
        per-month videos cap). Rule 6 — operator-explicit.
        Rule 8 — per-recipient render failures (missing
        template variables) flip that recipient to FAILED
        with the TemplateError message but DO NOT block the
        rest of the batch.

        Atomicity: the entire fan-out (recipient row mutations
        + composition creation + recipient.produced_composition
        linkage) lives in one transaction. The Celery enqueue
        happens AFTER commit so the worker can't race the
        rows.

        Returns the updated campaign serialized shape +
        per-recipient launch outcomes.
        """
        campaign = self._get_or_404(pk)

        if campaign.status != PersonalizedCampaign.Status.DRAFT:
            return Response(
                {
                    "detail": (
                        f"Cannot launch a campaign in status "
                        f"{campaign.status!r}; only DRAFT "
                        "campaigns can launch."
                    ),
                },
                status=http.HTTP_409_CONFLICT,
            )

        recipients = list(
            campaign.recipients
            .filter(status=PersonalizedRecipient.Status.PENDING)
            .order_by("position")
        )
        if not recipients:
            return Response(
                {
                    "detail": (
                        "Campaign has no PENDING recipients to "
                        "launch. Paste a CSV first (Q-c-8)."
                    ),
                },
                status=http.HTTP_400_BAD_REQUEST,
            )

        # Tier gates (rule 4).
        try:
            check_personalized_batch(campaign.workspace, len(recipients))
        except TierLimitExceeded as exc:
            return Response(exc.payload, status=402)

        # Atomic fan-out. Recipient render failures flip THAT
        # recipient to FAILED but don't bail the whole launch
        # (rule 8).
        from apps.compositions.recipes import RECIPES

        recipe = RECIPES.get("talking_head_polished")
        if recipe is None:
            return Response(
                {
                    "detail": (
                        "talking_head_polished recipe is not "
                        "registered — B-arc dependency broken. "
                        "Run inventory check."
                    ),
                },
                status=http.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        queued_composition_ids: list[str] = []
        with transaction.atomic():
            campaign.status = PersonalizedCampaign.Status.LAUNCHING
            campaign.launched_at = timezone.now()
            campaign.save(update_fields=[
                "status", "launched_at", "updated_at",
            ])

            for recipient in recipients:
                # Render the script for this recipient.
                try:
                    script = render_template(
                        campaign.template, recipient.variables,
                    )
                except TemplateError as exc:
                    recipient.status = PersonalizedRecipient.Status.FAILED
                    recipient.error_message = str(exc)
                    recipient.save(update_fields=[
                        "status", "error_message", "updated_at",
                    ])
                    continue

                # Fire the recipe.
                try:
                    composition = recipe.starter(
                        workspace=campaign.workspace,
                        spokesperson=campaign.spokesperson,
                        script=script,
                        name=f"{campaign.name} — {recipient.label}"[:200],
                        created_by=request.user,
                    )
                except Exception as exc:  # pragma: no cover — defensive
                    recipient.status = PersonalizedRecipient.Status.FAILED
                    recipient.error_message = (
                        f"starter failed: {exc!s}"[:500]
                    )
                    recipient.save(update_fields=[
                        "status", "error_message", "updated_at",
                    ])
                    continue

                recipient.status = PersonalizedRecipient.Status.QUEUED
                recipient.produced_composition = composition
                recipient.rendered_script = script
                recipient.error_message = ""
                recipient.save(update_fields=[
                    "status", "produced_composition",
                    "rendered_script", "error_message", "updated_at",
                ])
                queued_composition_ids.append(str(composition.id))

            # Roll up campaign status. If every recipient
            # failed at render time we never reached IN_FLIGHT
            # — short-circuit to FAILED so the SPA shows the
            # right terminal state.
            if queued_composition_ids:
                campaign.status = PersonalizedCampaign.Status.IN_FLIGHT
            else:
                campaign.status = PersonalizedCampaign.Status.FAILED
                campaign.completed_at = timezone.now()
            campaign.save(update_fields=[
                "status", "completed_at", "updated_at",
            ])

        # Enqueue after commit so the worker can't race the rows.
        from apps.compositions.tasks import execute_composition
        for composition_id in queued_composition_ids:
            execute_composition.delay(composition_id)

        logger.info(
            "campaign.launch id=%s queued=%d failed_at_render=%d",
            campaign.pk, len(queued_composition_ids),
            len(recipients) - len(queued_composition_ids),
        )

        campaign.refresh_from_db()
        return Response({
            "campaign": PersonalizedCampaignSerializer(campaign).data,
            "queued_count": len(queued_composition_ids),
            "failed_at_render_count": (
                len(recipients) - len(queued_composition_ids)
            ),
        })

    # ---- retry (B3.6) ------------------------------------------

    @action(detail=True, methods=["post"], url_path="retry_recipient")
    def retry_recipient_action(self, request, pk=None):
        """Per Q-c-6 — re-render a FAILED recipient.

        Body: ``{"recipient_id": "<uuid>"}``.

        Creates a NEW ``talking_head_polished`` composition;
        the failed composition (if any) stays in the workspace
        as audit. Resets recipient to QUEUED + sets the new
        produced_composition FK. Enqueues Celery after commit.

        If the campaign was in a terminal state (COMPLETED /
        PARTIAL / FAILED), flips it back to IN_FLIGHT — a
        recipient is running again.

        Refuses retry on non-FAILED recipients (PENDING never
        launched; QUEUED / RUNNING already in flight; COMPLETED
        already succeeded). 400 in those cases.
        """
        campaign = self._get_or_404(pk)

        recipient_id = (request.data or {}).get("recipient_id")
        if not recipient_id:
            return Response(
                {"detail": "recipient_id is required"},
                status=http.HTTP_400_BAD_REQUEST,
            )

        try:
            recipient = campaign.recipients.get(pk=recipient_id)
        except PersonalizedRecipient.DoesNotExist:
            raise NotFound("Recipient not found in this campaign")

        if recipient.status != PersonalizedRecipient.Status.FAILED:
            return Response(
                {
                    "detail": (
                        f"Cannot retry recipient in status "
                        f"{recipient.status!r}; only FAILED rows "
                        "are retryable."
                    ),
                },
                status=http.HTTP_400_BAD_REQUEST,
            )

        # Re-render the script. If template still references a
        # missing variable, surface that as the new error
        # without spinning up a composition.
        try:
            script = render_template(
                campaign.template, recipient.variables,
            )
        except TemplateError as exc:
            recipient.error_message = str(exc)
            recipient.save(update_fields=[
                "error_message", "updated_at",
            ])
            return Response(
                {"detail": str(exc)},
                status=http.HTTP_400_BAD_REQUEST,
            )

        from apps.compositions.recipes import RECIPES
        recipe = RECIPES.get("talking_head_polished")
        if recipe is None:  # pragma: no cover — same dep B3.5 has
            return Response(
                {"detail": "talking_head_polished recipe missing"},
                status=http.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        with transaction.atomic():
            composition = recipe.starter(
                workspace=campaign.workspace,
                spokesperson=campaign.spokesperson,
                script=script,
                name=(
                    f"{campaign.name} — {recipient.label} (retry)"
                )[:200],
                created_by=request.user,
            )

            # Failed composition stays for audit per Q-c-6 —
            # we point the recipient at the NEW one. The old
            # FK is overwritten; the old composition becomes
            # a dangling-but-browsable workspace asset.
            recipient.produced_composition = composition
            recipient.rendered_script = script
            recipient.status = PersonalizedRecipient.Status.QUEUED
            recipient.error_message = ""
            recipient.save(update_fields=[
                "produced_composition", "rendered_script",
                "status", "error_message", "updated_at",
            ])

            # If the campaign was terminal, flip it back to
            # IN_FLIGHT — a recipient is running again.
            terminal = {
                PersonalizedCampaign.Status.COMPLETED,
                PersonalizedCampaign.Status.PARTIAL,
                PersonalizedCampaign.Status.FAILED,
            }
            if campaign.status in terminal:
                campaign.status = PersonalizedCampaign.Status.IN_FLIGHT
                campaign.completed_at = None
                campaign.save(update_fields=[
                    "status", "completed_at", "updated_at",
                ])

        from apps.compositions.tasks import execute_composition
        execute_composition.delay(str(composition.id))

        logger.info(
            "campaign.retry_recipient campaign=%s recipient=%s "
            "new_composition=%s",
            campaign.pk, recipient.pk, composition.pk,
        )

        recipient.refresh_from_db()
        campaign.refresh_from_db()
        return Response({
            "recipient": PersonalizedRecipientSerializer(recipient).data,
            "campaign_status": campaign.status,
        })

    # ---- helpers ------------------------------------------------

    def _get_or_404(self, pk) -> PersonalizedCampaign:
        try:
            campaign = self.get_queryset().get(pk=pk)
        except PersonalizedCampaign.DoesNotExist:
            raise NotFound("Campaign not found")
        self.check_object_permissions(self.request, campaign)
        return campaign

    def _resolve_member_workspace(self, user, workspace_id) -> Workspace:
        try:
            workspace = Workspace.objects.get(pk=workspace_id)
        except Workspace.DoesNotExist:
            raise NotFound("Workspace not found")
        is_member = Membership.objects.filter(
            user=user, workspace=workspace,
        ).exists()
        if not is_member:
            raise NotFound("Workspace not found")
        return workspace

    def _resolve_workspace_spokesperson(
        self, workspace: Workspace, spokesperson_id,
    ) -> Spokesperson:
        try:
            sp = Spokesperson.objects.get(
                pk=spokesperson_id, workspace=workspace,
            )
        except Spokesperson.DoesNotExist:
            raise NotFound(
                "Spokesperson not found in this workspace"
            )
        return sp
