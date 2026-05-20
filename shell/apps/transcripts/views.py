"""B1.3 + B1.4 — REST surface for the transcript miner.

One ViewSet: ``TranscriptHighlightViewSet``. Actions:

* ``list`` (GET ``/api/transcript_highlights/``) — recent
  highlights for the requesting user's workspaces, filterable
  by ``?status=`` and ``?source_transcript=``. Paginated to
  100 by default.
* ``retrieve`` (GET ``/api/transcript_highlights/<id>/``) —
  single row.
* ``mine`` (POST ``/api/transcript_highlights/mine/``) —
  invoke the LLM helper against the transcript asset id;
  persist N PENDING rows; return them.
* ``approve`` (POST ``/api/transcript_highlights/<id>/approve/``)
  (B1.4) — flip status PENDING → APPROVED, fire a
  ``talking_head_polished`` composition via the recipe
  registry, link ``produced_composition`` FK, enqueue
  ``execute_composition``, return the updated highlight +
  composition shape.
* ``reject`` (POST ``/api/transcript_highlights/<id>/reject/``)
  (B1.4) — flip status PENDING → REJECTED, capture optional
  ``rejection_reason``.

Workspace isolation flows through the standard pattern:
* ``get_queryset()`` filters by ``workspace__memberships__user``.
* ``IsWorkspaceMember`` runs on detail routes.
* The mine action explicitly re-checks workspace membership
  before reading the transcript body or persisting rows.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status as http
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from apps.accounts.models import Membership
from apps.compositions.models import Asset, AssetType
from character_os.permissions import IsWorkspaceMember
from character_os.transcript_miner import (
    DEFAULT_TARGET_COUNT,
    MAX_HIGHLIGHT_CHARS,
    select_transcript_highlights,
)

from .models import TranscriptHighlight
from .serializers import (
    MineRequestSerializer,
    TranscriptHighlightSerializer,
)

logger = logging.getLogger(__name__)


class TranscriptHighlightViewSet(GenericViewSet):
    """Highlight rows. Read-only list/retrieve in B1.3;
    approve/reject mutators land in B1.4."""

    queryset = TranscriptHighlight.objects.all()
    serializer_class = TranscriptHighlightSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return TranscriptHighlight.objects.none()
        return (
            TranscriptHighlight.objects.filter(
                workspace__memberships__user=user,
            )
            .select_related("workspace", "source_transcript", "produced_composition")
            .distinct()
        )

    # ---- list / retrieve ---------------------------------------

    def list(self, request):
        qs = self.get_queryset()

        source_id = request.query_params.get("source_transcript")
        if source_id:
            qs = qs.filter(source_transcript_id=source_id)

        status_filter = request.query_params.get("status")
        if status_filter:
            qs = qs.filter(status=status_filter)

        # Default page cap — same shape as R7 invocations.
        # SPA can opt into pagination when this gets crowded.
        return Response(
            TranscriptHighlightSerializer(qs[:100], many=True).data,
        )

    def retrieve(self, request, pk=None):
        highlight = self._get_or_404(pk)
        return Response(
            TranscriptHighlightSerializer(highlight).data,
        )

    # ---- mine --------------------------------------------------

    @action(
        detail=False, methods=["post"], url_path="mine",
    )
    def mine(self, request):
        """Invoke the LLM helper against a transcript asset.

        Body: ``{transcript_asset_id, target_count?, max_chars?}``.

        Resolves the transcript asset via the requesting
        user's workspace memberships (cross-workspace reads
        return 404). Calls
        ``select_transcript_highlights``; persists N PENDING
        rows; returns the serialized rows.

        Empty result (no body content, missing OpenAI key,
        LLM failure) returns ``{"highlights": [],
        "used_synthesis": <bool>}`` with HTTP 200 — the SPA
        treats empty as "nothing to mine; try again with
        different knobs" rather than as an error. The
        ``used_synthesis`` flag distinguishes "LLM ran but
        found nothing" from "LLM never ran" (no key /
        force-mock disabled / etc.).
        """
        req = MineRequestSerializer(data=request.data or {})
        req.is_valid(raise_exception=True)
        params = req.validated_data

        transcript = self._resolve_workspace_asset(
            request.user, params["transcript_asset_id"],
        )

        target_count = params.get("target_count", DEFAULT_TARGET_COUNT)
        max_chars = params.get("max_chars", MAX_HIGHLIGHT_CHARS)

        result = select_transcript_highlights(
            transcript.inline_content or "",
            target_count=target_count,
            max_chars=max_chars,
        )

        persisted: list[TranscriptHighlight] = []
        if result.picks:
            with transaction.atomic():
                for idx, pick in enumerate(result.picks):
                    # Q-b-5 — first row holds the full LLM
                    # call cost + token totals; other rows
                    # get zeros so the per-call accounting
                    # doesn't double-count.
                    row = TranscriptHighlight(
                        workspace=transcript.workspace,
                        source_transcript=transcript,
                        text=pick.text,
                        char_start=pick.char_start,
                        char_end=pick.char_end,
                        llm_reasoning=pick.llm_reasoning,
                        status=TranscriptHighlight.Status.PENDING,
                        llm_model_id=result.model if idx == 0 else "",
                        llm_cost_micros=0,  # SESSION 202 v1 — cost
                                            # accounting layered in B1.7
                        llm_tokens_input=result.tokens_input if idx == 0 else 0,
                        llm_tokens_output=result.tokens_output if idx == 0 else 0,
                    )
                    row.full_clean()  # contract rules at clean()
                    row.save()
                    persisted.append(row)

        logger.info(
            "transcript_highlights.mine workspace=%s transcript=%s "
            "target=%d picks=%d synthesis=%s",
            transcript.workspace_id, transcript.pk, target_count,
            len(persisted), result.used_synthesis,
        )

        return Response(
            {
                "highlights": TranscriptHighlightSerializer(
                    persisted, many=True,
                ).data,
                "used_synthesis": result.used_synthesis,
                "model": result.model,
            },
            status=http.HTTP_201_CREATED if persisted else http.HTTP_200_OK,
        )

    # ---- approve / reject (B1.4) -------------------------------

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Operator approved a PENDING highlight — flip status,
        fire a ``talking_head_polished`` composition, link the
        FK, enqueue ``execute_composition``, return the row.

        Idempotent on already-decided rows: approving an
        APPROVED row returns its current state without
        re-firing. Approving a REJECTED or RENDERED row is a
        400 — the operator should mine again or create a
        fresh highlight.
        """
        highlight = self._get_or_404(pk)

        # Idempotent: already APPROVED returns current state.
        if highlight.status == TranscriptHighlight.Status.APPROVED:
            return Response(TranscriptHighlightSerializer(highlight).data)

        # Already RENDERED → also idempotent; the render
        # already completed.
        if highlight.status == TranscriptHighlight.Status.RENDERED:
            return Response(TranscriptHighlightSerializer(highlight).data)

        if highlight.status != TranscriptHighlight.Status.PENDING:
            raise ValidationError(
                f"cannot approve highlight in status {highlight.status!r}; "
                "only PENDING highlights are approvable."
            )

        spokesperson = self._resolve_spokesperson(highlight)
        composition = self._fire_render(highlight, spokesperson)

        with transaction.atomic():
            highlight.status = TranscriptHighlight.Status.APPROVED
            highlight.produced_composition = composition
            highlight.decided_at = timezone.now()
            highlight.save(
                update_fields=[
                    "status", "produced_composition", "decided_at",
                ],
            )

        # Enqueue after the transaction commits so the worker
        # can't race the row.
        from apps.compositions.tasks import execute_composition
        execute_composition.delay(str(composition.id))

        logger.info(
            "transcript_highlights.approve highlight=%s composition=%s",
            highlight.pk, composition.pk,
        )
        return Response(TranscriptHighlightSerializer(highlight).data)

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Operator rejected a PENDING highlight. Optional
        ``rejection_reason`` body lands on the row for audit.

        Idempotent on already-REJECTED rows. Rejecting an
        APPROVED or RENDERED row is a 400 — the operator
        should delete the produced composition separately if
        needed (Q-b-4 deferred to v2)."""
        highlight = self._get_or_404(pk)

        if highlight.status == TranscriptHighlight.Status.REJECTED:
            return Response(TranscriptHighlightSerializer(highlight).data)

        if highlight.status != TranscriptHighlight.Status.PENDING:
            raise ValidationError(
                f"cannot reject highlight in status {highlight.status!r}; "
                "only PENDING highlights are rejectable."
            )

        reason = ((request.data or {}).get("rejection_reason") or "").strip()
        highlight.status = TranscriptHighlight.Status.REJECTED
        highlight.rejection_reason = reason
        highlight.decided_at = timezone.now()
        highlight.save(
            update_fields=[
                "status", "rejection_reason", "decided_at",
            ],
        )
        logger.info(
            "transcript_highlights.reject highlight=%s reason_chars=%d",
            highlight.pk, len(reason),
        )
        return Response(TranscriptHighlightSerializer(highlight).data)

    # ---- helpers ------------------------------------------------

    def _get_or_404(self, pk) -> TranscriptHighlight:
        try:
            highlight = self.get_queryset().get(pk=pk)
        except TranscriptHighlight.DoesNotExist:
            raise NotFound("Transcript highlight not found")
        self.check_object_permissions(self.request, highlight)
        return highlight

    def _resolve_spokesperson(self, highlight: TranscriptHighlight):
        """Q-b-7 — find the spokesperson who originally spoke
        the transcript via the reverse FK from RealtimeSession.
        Fails loudly if the transcript has no realtime session
        attached (e.g. operator-uploaded transcript in v2; not
        in scope for B1.4)."""
        from apps.realtime.models import RealtimeSession

        session = (
            RealtimeSession.objects
            .filter(transcript_asset=highlight.source_transcript)
            .select_related("spokesperson")
            .first()
        )
        if session is None:
            raise ValidationError(
                "highlight's source transcript has no realtime session "
                "attached — cannot determine which spokesperson to "
                "re-bake. Mining from operator-uploaded transcripts "
                "lands in B-1 v2."
            )
        if session.spokesperson is None:
            raise ValidationError(
                "highlight's source session has no spokesperson — "
                "data corruption; contact support."
            )
        return session.spokesperson

    def _fire_render(self, highlight: TranscriptHighlight, spokesperson):
        """Create a ``talking_head_polished`` composition for
        the highlight. Returns the Composition row; caller
        enqueues ``execute_composition`` after the highlight
        row is updated."""
        from apps.compositions.recipes import RECIPES

        recipe = RECIPES.get("talking_head_polished")
        if recipe is None:
            raise ValidationError(
                "talking_head_polished recipe is not registered — "
                "B-arc depends on V9. Run inventory check."
            )

        composition = recipe.starter(
            workspace=highlight.workspace,
            spokesperson=spokesperson,
            script=highlight.text,
            name=f"Highlight: {highlight.text[:30]!r}",
            created_by=self.request.user,
        )
        return composition

    def _resolve_workspace_asset(self, user, asset_id) -> Asset:
        """Resolve a TRANSCRIPT Asset belonging to one of the
        user's workspaces. Cross-workspace lookups return 404
        — same shape as A4's workspace asset resolver."""
        try:
            asset = Asset.objects.get(pk=asset_id)
        except Asset.DoesNotExist:
            raise NotFound("Transcript asset not found")

        if asset.asset_type != AssetType.TRANSCRIPT:
            raise NotFound("Asset is not a transcript")

        is_member = Membership.objects.filter(
            user=user, workspace_id=asset.workspace_id,
        ).exists()
        if not is_member:
            raise NotFound("Transcript asset not found")

        return asset
