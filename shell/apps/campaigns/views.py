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
from django.utils import timezone  # noqa: F401 — used by B3.5
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Membership, Workspace
from apps.spokespeople.models import Spokesperson
from character_os.csv_recipients import derive_label, parse_csv
from character_os.permissions import IsWorkspaceMember
from character_os.template_renderer import parse_placeholders

from .models import PersonalizedCampaign, PersonalizedRecipient
from .serializers import (
    CreateCampaignSerializer,
    ParseCsvSerializer,
    PersonalizedCampaignSerializer,
    PersonalizedRecipientSerializer,
)

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
