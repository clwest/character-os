"""DRF viewset for RealtimeSession — R3 broker.

The broker is the Django-side orchestrator that:

1. **Create** — workspace-scoped tier-limit gate → builds a
   RealtimeSession row in DRAFT → calls
   `MediaEngineClient.realtime_session_create()` → persists
   the provider-issued session_id / session_key /
   expires_at → flips status to CREATING → returns the
   SDK-safe payload INCLUDING session_key so the SPA can
   connect.
2. **Retrieve** — workspace-scoped GET. Polls upstream if
   status is CREATING or NOT_READY to advance the state
   machine to READY. NEVER returns session_key.
3. **End** — workspace-scoped DELETE. Calls
   `realtime_session_end()` on the media-engine; marks the
   row ENDED with `ended_at` + computed `duration_seconds`.
   Best-effort: marks ENDED even if the upstream call
   fails (keeps the Django row consistent; operators can
   force-end via admin if Runway holds the session open).

Contract rule 9 — `provider_session_key` is in the create
response shape only. Every retrieve uses the standard
serializer that omits the field. The session_key never
appears in admin display, never in logs, never in retrieve.
"""
from __future__ import annotations

import logging

from django.db import transaction
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from apps.accounts.models import Membership
from apps.billing.services import (
    TierLimitExceeded,
    check_realtime_session_limit,
)
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.permissions import IsWorkspaceMember

from .models import RealtimeSession
from .serializers import (
    RealtimeSessionSerializer,
    RealtimeSessionWithKeySerializer,
)

logger = logging.getLogger(__name__)


# Map media-engine session status strings to RealtimeSession.Status.
_STATUS_MAP = {
    "creating": RealtimeSession.Status.CREATING,
    "not_ready": RealtimeSession.Status.NOT_READY,
    "ready": RealtimeSession.Status.READY,
    "ended": RealtimeSession.Status.ENDED,
    "failed": RealtimeSession.Status.FAILED,
}


def _map_status(upstream: str) -> str:
    return _STATUS_MAP.get(
        (upstream or "").lower(), RealtimeSession.Status.CREATING,
    )


class RealtimeSessionViewSet(viewsets.GenericViewSet):
    """Broker for RealtimeSession. Workspace-scoped via the
    spokesperson FK chain (sessions live in
    spokesperson.workspace)."""

    queryset = RealtimeSession.objects.all()
    serializer_class = RealtimeSessionSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return RealtimeSession.objects.none()
        return (
            RealtimeSession.objects.filter(
                workspace__memberships__user=user,
            )
            .select_related("spokesperson", "workspace")
            .prefetch_related("tool_invocations")
            .distinct()
        )

    # ---- LIST ---------------------------------------------------

    def list(self, request):
        qs = self.get_queryset()
        spokesperson_id = request.query_params.get("spokesperson")
        if spokesperson_id:
            qs = qs.filter(spokesperson_id=spokesperson_id)
        thread_id = request.query_params.get("thread")
        if thread_id:
            qs = qs.filter(thread_id=thread_id)
        return Response(
            RealtimeSessionSerializer(qs[:50], many=True).data,
        )

    # ---- RETRIEVE (with poll) -----------------------------------

    def retrieve(self, request, pk=None):
        session = self._get_session_or_404(pk)
        # Advance state if we're mid-creation. Upstream poll
        # only fires when there's something useful to learn
        # (CREATING / NOT_READY); terminal states are
        # cached.
        if session.status in (
            RealtimeSession.Status.CREATING,
            RealtimeSession.Status.NOT_READY,
        ) and session.provider_session_id:
            self._poll_and_update(session)
        return Response(RealtimeSessionSerializer(session).data)

    # ---- CREATE -------------------------------------------------

    def create(self, request):
        body = request.data or {}
        spokesperson_id = body.get("spokesperson")
        if not spokesperson_id:
            raise ValidationError({"spokesperson": "required"})

        try:
            spokesperson = Spokesperson.objects.select_related(
                "workspace",
            ).get(pk=spokesperson_id)
        except Spokesperson.DoesNotExist:
            raise ValidationError({"spokesperson": "not found"})

        workspace = spokesperson.workspace
        if not Membership.objects.filter(
            user=request.user, workspace=workspace,
        ).exists():
            raise ValidationError(
                {"spokesperson": "spokesperson not in your workspaces"}
            )

        if not spokesperson.runway_avatar_id:
            raise ValidationError({
                "spokesperson": (
                    "spokesperson has no runway_avatar_id — finish the "
                    "create-spokesperson wizard first"
                ),
            })

        try:
            check_realtime_session_limit(workspace)
        except TierLimitExceeded as exc:
            return Response(exc.payload, status=402)

        personality = (body.get("personality") or "").strip()
        start_script = (body.get("start_script") or "").strip()
        title = (body.get("title") or "").strip()
        thread_id = body.get("thread")
        provider = (body.get("provider") or "runway").strip()
        tools = body.get("tools") or []

        # Build the row in DRAFT; we'll flip to CREATING once
        # the upstream POST succeeds.
        with transaction.atomic():
            session = RealtimeSession.objects.create(
                workspace=workspace,
                spokesperson=spokesperson,
                thread_id=thread_id or None,
                provider=provider,
                mock_mode=False,  # broker decides; media-engine
                # also reports actual mode in response
                status=RealtimeSession.Status.DRAFT,
                started_at=timezone.now(),
                created_by=request.user,
            )

        # Outside the transaction — the upstream call can take
        # a few seconds and we don't want a DB row lock open.
        try:
            with MediaEngineClient() as client:
                result = client.realtime_session_create(
                    avatar_id=spokesperson.runway_avatar_id,
                    personality=personality,
                    start_script=start_script,
                    document_ids=[],  # R4 will populate
                    tools=list(tools),
                    provider=provider,
                )
        except MediaEngineError as exc:
            session.status = RealtimeSession.Status.FAILED
            session.error_message = f"media-engine: {exc}"[:500]
            session.ended_at = timezone.now()
            session.save(update_fields=[
                "status", "error_message", "ended_at", "updated_at",
            ])
            logger.warning(
                "realtime broker create upstream failed session=%s: %s",
                session.id, exc,
            )
            return Response(
                {"detail": "realtime backend unavailable", "error": str(exc)[:200]},
                status=502,
            )

        # Persist upstream details + flip status.
        session.provider_session_id = result.session_id
        session.provider_session_key = result.session_key
        session.expires_at = _parse_iso(result.expires_at)
        session.mock_mode = result.mock_mode
        session.status = _map_status(result.status)
        if session.status == RealtimeSession.Status.READY:
            session.ready_at = timezone.now()
        if title:
            # `title` isn't a model field — kept on the
            # ConversationThread side when bound. For v1
            # the SPA may pass a title hint; we ignore it
            # at the model level. (Future polish: ship a
            # `title` field on RealtimeSession.)
            pass
        session.save(update_fields=[
            "provider_session_id", "provider_session_key",
            "expires_at", "mock_mode", "status", "ready_at",
            "updated_at",
        ])

        logger.info(
            "realtime broker create session=%s spokesperson=%s status=%s "
            "mock=%s",
            session.id, spokesperson.id, session.status, session.mock_mode,
        )

        return Response(
            RealtimeSessionWithKeySerializer(session).data,
            status=status.HTTP_201_CREATED,
        )

    # ---- DELETE / end -------------------------------------------

    def destroy(self, request, pk=None):
        session = self._get_session_or_404(pk)
        self._end_session(session)
        return Response(RealtimeSessionSerializer(session).data)

    @action(detail=True, methods=["post"])
    def end(self, request, pk=None):
        """Alternate end endpoint for SPA clients that prefer
        a POST verb to a DELETE (some auth proxies strip
        DELETE)."""
        session = self._get_session_or_404(pk)
        self._end_session(session)
        return Response(RealtimeSessionSerializer(session).data)

    # ---- helpers -----------------------------------------------

    def _get_session_or_404(self, pk) -> RealtimeSession:
        try:
            session = self.get_queryset().get(pk=pk)
        except RealtimeSession.DoesNotExist:
            raise NotFound("Realtime session not found")
        self.check_object_permissions(self.request, session)
        return session

    def _poll_and_update(self, session: RealtimeSession) -> None:
        """Best-effort upstream poll. Any failure leaves the
        session in its current state — operator can retry
        the retrieve."""
        try:
            with MediaEngineClient() as client:
                state = client.realtime_session_poll(
                    session.provider_session_id, provider=session.provider,
                )
        except MediaEngineError as exc:
            logger.warning(
                "realtime broker poll session=%s upstream failed: %s",
                session.id, exc,
            )
            return

        new_status = _map_status(state.status)
        update_fields = ["status", "updated_at"]
        session.status = new_status
        if new_status == RealtimeSession.Status.READY and not session.ready_at:
            session.ready_at = timezone.now()
            update_fields.append("ready_at")
        if state.error_message:
            session.error_message = state.error_message[:500]
            update_fields.append("error_message")
        if state.expires_at:
            session.expires_at = _parse_iso(state.expires_at)
            update_fields.append("expires_at")
        session.save(update_fields=update_fields)

    def _end_session(self, session: RealtimeSession) -> None:
        """Mark a session ENDED. Tries to notify upstream but
        the Django row flips ENDED regardless — keeps state
        consistent for the operator."""
        if session.status == RealtimeSession.Status.ENDED:
            return  # idempotent

        # Best-effort upstream teardown. If it fails, log
        # but proceed — the Django row is our source of
        # truth post-end.
        if session.provider_session_id:
            try:
                with MediaEngineClient() as client:
                    client.realtime_session_end(
                        session.provider_session_id, provider=session.provider,
                    )
            except MediaEngineError as exc:
                logger.warning(
                    "realtime broker end upstream failed session=%s: %s",
                    session.id, exc,
                )

        now = timezone.now()
        session.status = RealtimeSession.Status.ENDED
        session.ended_at = now
        if session.started_at:
            delta = (now - session.started_at).total_seconds()
            session.duration_seconds = max(0, int(round(delta)))
        session.save(update_fields=[
            "status", "ended_at", "duration_seconds", "updated_at",
        ])

        logger.info(
            "realtime broker end session=%s duration=%ds",
            session.id, session.duration_seconds,
        )


def _parse_iso(value):
    """Best-effort ISO timestamp parsing. Returns None on
    failure — the field is nullable so an unparseable
    upstream value is recoverable."""
    if not value:
        return None
    from datetime import datetime

    try:
        # Python 3.11 handles "Z" via fromisoformat directly.
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
