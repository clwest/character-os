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
    check_realtime_minutes_budget,
    check_realtime_session_limit,
)
from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.permissions import IsWorkspaceMember

from .dispatch import (
    DispatchError,
    approve_invocation,
    dispatch_tool,
    reject_invocation,
)
from .models import RealtimeSession, RealtimeToolInvocation
from .serializers import (
    RealtimeSessionSerializer,
    RealtimeSessionWithKeySerializer,
    RealtimeToolInvocationSerializer,
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

        # R9 — finer-grained minutes-budget gate fires
        # alongside the session-count gate. Either can
        # independently veto.
        try:
            check_realtime_minutes_budget(workspace)
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

        # R4 — compose the Runway document from K-arc retrieval.
        # The doc is the avatar's grounding context. Composition
        # never raises (degrades to business_brief-only when
        # retrieval fails); empty knowledge produces a usable
        # but knowledge-less doc.
        from character_os.realtime_document import compose_realtime_document

        doc_result = compose_realtime_document(spokesperson)
        provider_document_id = ""
        document_ids: list[str] = []
        chunk_ids: list[str] = list(doc_result.chunk_ids)

        try:
            with MediaEngineClient() as client:
                # R4 — push the composed document to the
                # provider FIRST so we have a document_id to
                # pass into session_create.
                if doc_result.body.strip():
                    doc = client.realtime_document_create(
                        name=f"Spokesperson {spokesperson.name}",
                        content=doc_result.body,
                        provider=provider,
                    )
                    provider_document_id = doc.document_id
                    document_ids.append(doc.document_id)

                result = client.realtime_session_create(
                    avatar_id=spokesperson.runway_avatar_id,
                    personality=personality,
                    start_script=start_script,
                    document_ids=document_ids,
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
        session.provider_document_id = provider_document_id
        session.knowledge_chunk_ids = chunk_ids
        session.expires_at = _parse_iso(result.expires_at)
        session.mock_mode = result.mock_mode
        session.status = _map_status(result.status)
        if session.status == RealtimeSession.Status.READY:
            session.ready_at = timezone.now()
        # R9 — stamp the provider-rate-based cost estimate
        # for the full session cap. The CostTicker /
        # session-end actual landing happens via
        # _end_session below.
        from .cost import estimate_session_cost_micros

        session.cost_estimate_micros = estimate_session_cost_micros(
            provider,
        )
        if title:
            # `title` isn't a model field — kept on the
            # ConversationThread side when bound. For v1
            # the SPA may pass a title hint; we ignore it
            # at the model level. (Future polish: ship a
            # `title` field on RealtimeSession.)
            pass
        session.save(update_fields=[
            "provider_session_id", "provider_session_key",
            "provider_document_id", "knowledge_chunk_ids",
            "expires_at", "mock_mode", "status", "ready_at",
            "cost_estimate_micros", "updated_at",
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

    # ---- COST ESTIMATE (R9) -------------------------------------

    @action(detail=False, methods=["get"], url_path="cost_estimate")
    def cost_estimate(self, request):
        """Return per-provider rate + session cap + the
        workspace's remaining monthly minutes. SPA's
        IdlePanel + CostTicker use this to render real
        cost forecasts rather than the hardcoded
        placeholders R8.1 + R8.2 shipped.

        Query params:
          - ``workspace`` (optional): UUID. Defaults to
            the user's first membership. Useful when the
            SPA has multi-workspace context.
          - ``provider`` (optional): defaults to ``runway``.
        """
        from .cost import (
            PROVIDER_MAX_SESSION_MINUTES,
            cost_per_minute_micros,
        )
        from apps.accounts.models import Membership, Workspace
        from apps.billing.services import get_usage

        provider = (
            (request.query_params.get("provider") or "runway").strip()
            or "runway"
        )
        workspace_id = request.query_params.get("workspace")

        if workspace_id:
            try:
                workspace = Workspace.objects.get(pk=workspace_id)
            except Workspace.DoesNotExist:
                raise NotFound("Workspace not found")
            if not Membership.objects.filter(
                user=request.user, workspace=workspace,
            ).exists():
                raise NotFound("Workspace not found")
        else:
            membership = (
                Membership.objects.filter(user=request.user)
                .select_related("workspace")
                .first()
            )
            if not membership:
                raise NotFound("No workspaces for this user")
            workspace = membership.workspace

        rate = cost_per_minute_micros(provider)
        usage = get_usage(workspace)
        remaining = (
            None
            if usage.realtime_minutes_limit is None
            else max(
                0,
                usage.realtime_minutes_limit - usage.realtime_minutes_used,
            )
        )
        return Response(
            {
                "provider": provider,
                "cost_per_minute_micros": rate,
                "max_session_minutes": PROVIDER_MAX_SESSION_MINUTES,
                "monthly_minutes_used": usage.realtime_minutes_used,
                "monthly_minutes_limit": usage.realtime_minutes_limit,
                "monthly_minutes_remaining": remaining,
                "tier": usage.tier,
            }
        )

    # ---- TOOL DISPATCH (R7.0) -----------------------------------

    @action(detail=True, methods=["post"], url_path="invoke_tool")
    def invoke_tool(self, request, pk=None):
        """Dispatch a tool the avatar's LLM invoked.

        The SPA receives a tool-invocation event from the
        Runway SDK's `onClientEvent` callback, POSTs here
        with `{tool_name, args}`. The dispatcher resolves
        the tool in the registry, gates on workspace scope
        + cost threshold, and either executes inline or
        returns ``awaiting_approval``.

        Response shapes (always JSON, never 5xx for
        executor failures — the dispatcher catches +
        records):

        * Executed inline → 200 with `state=succeeded` +
          `result`.
        * Over threshold → 202 with `state=awaiting_approval`
          + `invocation_id` + `cost_micros` + `reason`.
        * Executor raised → 200 with `state=failed` +
          `error_message`.
        * Unknown tool / workspace mismatch → 400 / 403.
        """
        session = self._get_session_or_404(pk)
        body = request.data or {}
        tool_name = (body.get("tool_name") or "").strip()
        if not tool_name:
            raise ValidationError({"tool_name": "required"})
        args = body.get("args") or {}
        if not isinstance(args, dict):
            raise ValidationError({"args": "must be an object"})

        try:
            result = dispatch_tool(
                session, tool_name, args, user=request.user,
            )
        except DispatchError as exc:
            return Response(
                {"detail": str(exc), "tool_name": tool_name},
                status=exc.http_status,
            )

        return Response(
            _serialize_dispatch_result(result),
            status=(
                status.HTTP_202_ACCEPTED
                if result.state == "awaiting_approval"
                else status.HTTP_200_OK
            ),
        )

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
        """Mark a session ENDED. The SPA-side SDK unmounts on
        operator-clicked End, which disconnects the LiveKit
        room. Runway's lifecycle then naturally flips the
        underlying realtime_session to COMPLETED and the
        avatar_conversation to ended (with a populated
        transcript). We deliberately DO NOT fire a DELETE on
        /v1/realtime_sessions/<id> — that explicit cancel
        marks the session CANCELLED and the conversation
        FAILED with no transcript (proven against the live
        Runway dev API May 18 2026: same session shape,
        DELETE → status:failed transcript:[]; no DELETE →
        status:COMPLETED transcript:[3+ real turns])."""
        if session.status == RealtimeSession.Status.ENDED:
            return  # idempotent

        now = timezone.now()
        session.status = RealtimeSession.Status.ENDED
        session.ended_at = now
        if session.started_at:
            delta = (now - session.started_at).total_seconds()
            session.duration_seconds = max(0, int(round(delta)))
        # R9 — stamp actual cost from the final duration.
        # Helper handles the duration=0 short-circuit
        # (sessions that flipped to ENDED without going
        # live).
        from .cost import actual_session_cost_micros

        session.cost_actual_micros = actual_session_cost_micros(session)
        session.save(update_fields=[
            "status", "ended_at", "duration_seconds",
            "cost_actual_micros", "updated_at",
        ])

        # R5 — enqueue post-end transcript capture. Best-effort
        # via Celery; broker enqueue failure (broker down,
        # etc.) doesn't block the end response.
        #
        # 30-second countdown: Runway needs time after the
        # LiveKit room closes to flip /v1/realtime_sessions
        # to COMPLETED and populate the /v1/avatar_conversations
        # transcript. Empirically ~5-15s post-disconnect.
        # Fetching immediately (the pre-fix behavior) returned
        # an empty transcript even on healthy sessions.
        if session.provider_session_id:
            try:
                from .tasks import fetch_transcript_for_session

                fetch_transcript_for_session.apply_async(
                    args=[str(session.id)],
                    countdown=30,
                )
            except Exception as exc:
                logger.warning(
                    "realtime broker end transcript-enqueue failed "
                    "session=%s err=%s",
                    session.id, exc,
                )

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


# ---- Tool invocation viewset (R7.0) -------------------------------


def _serialize_dispatch_result(result) -> dict:
    """Serialize ``DispatchResult`` into the JSON shape the
    SPA expects. ``result`` (tool-specific payload) is
    omitted when None so awaiting-approval responses stay
    tight."""
    out = {
        "state": result.state,
        "invocation_id": result.invocation_id,
        "tool_name": result.tool_name,
        "cost_micros": result.cost_micros,
    }
    if result.result is not None:
        out["result"] = result.result
    if result.error_message:
        out["error_message"] = result.error_message
    if result.reason:
        out["reason"] = result.reason
    return out


class RealtimeToolInvocationViewSet(viewsets.GenericViewSet):
    """Audit + approval-gate surface for
    ``RealtimeToolInvocation`` rows.

    Workspace-scoped via the session FK: the queryset
    filters by the requesting user's workspace
    memberships, and `RealtimeToolInvocation.workspace`
    (the property added in R7.0) resolves the indirect FK
    for the shared `IsWorkspaceMember` permission.

    Actions:
    * ``list`` — recent invocations, filterable by
      ``?session=<uuid>``.
    * ``retrieve`` — single invocation detail.
    * ``approve`` — operator approves a deferred tool;
      executes it now + returns the dispatch result.
    * ``reject`` — operator declines; records the optional
      ``reason``.
    """

    queryset = RealtimeToolInvocation.objects.all()
    serializer_class = RealtimeToolInvocationSerializer
    permission_classes = [IsAuthenticated, IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return RealtimeToolInvocation.objects.none()
        return (
            RealtimeToolInvocation.objects.filter(
                session__workspace__memberships__user=user,
            )
            .select_related("session", "session__workspace")
            .distinct()
        )

    def list(self, request):
        qs = self.get_queryset()
        session_id = request.query_params.get("session")
        if session_id:
            qs = qs.filter(session_id=session_id)
        # Sensible default page — same shape as the session
        # list cap. SPA can paginate when this gets crowded.
        return Response(
            RealtimeToolInvocationSerializer(qs[:100], many=True).data,
        )

    def retrieve(self, request, pk=None):
        invocation = self._get_invocation_or_404(pk)
        return Response(
            RealtimeToolInvocationSerializer(invocation).data,
        )

    @action(detail=True, methods=["post"])
    def approve(self, request, pk=None):
        """Operator approved a deferred tool — execute it.
        Idempotent: already-resolved invocations return
        their current state."""
        invocation = self._get_invocation_or_404(pk)
        result = approve_invocation(invocation)
        return Response(_serialize_dispatch_result(result))

    @action(detail=True, methods=["post"])
    def reject(self, request, pk=None):
        """Operator declined a deferred tool. Optional
        ``reason`` lands on the audit row's error_message
        so the SPA can narrate it back through the WebRTC
        data channel."""
        invocation = self._get_invocation_or_404(pk)
        reason = (request.data or {}).get("reason", "")
        result = reject_invocation(invocation, reason=reason)
        return Response(_serialize_dispatch_result(result))

    def _get_invocation_or_404(self, pk) -> RealtimeToolInvocation:
        try:
            invocation = self.get_queryset().get(pk=pk)
        except RealtimeToolInvocation.DoesNotExist:
            raise NotFound("Realtime tool invocation not found")
        self.check_object_permissions(self.request, invocation)
        return invocation
