"""DRF viewset for ConversationThread + the K9 message endpoints."""
from __future__ import annotations

import logging

from django.db import transaction
from rest_framework import status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.response import Response

from character_os.permissions import IsWorkspaceMember

from .models import ConversationMessage, ConversationThread
from .serializers import (
    ConversationMessageSerializer,
    ConversationThreadSerializer,
)

logger = logging.getLogger(__name__)


class ConversationThreadViewSet(viewsets.ModelViewSet):
    """CRUD on conversation threads + K9 message surface.

    Standard CRUD via the router covers list/create/retrieve/
    delete on the thread itself. The K9 additions:

    * GET  /api/conversations/<id>/messages/   list messages
    * POST /api/conversations/<id>/messages/   send a user
      message; synthesizes + persists the spokesperson reply
      in the same request; returns both.

    Workspace scoping flows through `IsWorkspaceMember` +
    the spokesperson-anchored queryset filter. The K6/K8
    retrieval guarantees apply at the retrieval layer; this
    viewset just orchestrates.
    """

    serializer_class = ConversationThreadSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return ConversationThread.objects.none()
        qs = (
            ConversationThread.objects.filter(
                spokesperson__workspace__memberships__user=user
            )
            .select_related("spokesperson", "spokesperson__workspace")
            .distinct()
        )
        # Optional spokesperson filter for the SPA's
        # "Conversations" tab on the spokesperson detail page.
        spokesperson_id = self.request.query_params.get("spokesperson")
        if spokesperson_id:
            qs = qs.filter(spokesperson_id=spokesperson_id)
        return qs

    @action(detail=True, methods=["get", "post"], url_path="messages")
    def messages(self, request, pk=None):
        """List or send messages for a thread.

        GET → ordered chronological list of all messages.
        POST → {content} body. Creates a user message (which
        fires K8's embedding signal), synthesizes the
        spokesperson reply via K9's
        `synthesize_spokesperson_reply`, persists the reply
        (also embedded by signal), bumps
        `thread.last_activity_at`, and returns both messages.
        """
        thread = self.get_object()  # honors IsWorkspaceMember

        if request.method == "GET":
            qs = thread.messages.order_by("created_at")
            return Response(
                ConversationMessageSerializer(qs, many=True).data,
            )

        content = (request.data.get("content") or "").strip()
        if not content:
            raise ValidationError({"content": "Required."})
        if len(content) > 4000:
            raise ValidationError(
                {"content": "Message too long (>4000 chars)."}
            )

        # Lazy-import the synthesizer + verifier so this app
        # doesn't depend on character_os.* at module-load time.
        from character_os.claim_verifier import ClaimVerifierError
        from character_os.conversation_synthesis import (
            synthesize_spokesperson_reply,
        )

        with transaction.atomic():
            user_msg = ConversationMessage.objects.create(
                thread=thread,
                role=ConversationMessage.Role.USER,
                content=content,
            )

        # Synthesize OUTSIDE the transaction — the LLM call
        # can take seconds; we don't want a long-running DB
        # transaction. The user message is already persisted
        # + embedded by K8's signal at this point.
        verifier_warnings: list[dict] = []
        rejected_synthesis = ""
        try:
            result = synthesize_spokesperson_reply(thread, content)
        except ClaimVerifierError as exc:
            # K6.5 — Strict mode. The LLM produced something
            # the verifier rejected. Persist a SPOKESPERSON
            # message that captures the rejection (rather than
            # the rejected text) so the thread has continuity,
            # and return 422 with the forensic surface so the
            # operator can review what was withheld.
            logger.warning(
                "K6.5 strict-mode rejection on thread=%s: %d claim(s)",
                thread.pk, len(exc.unsupported),
            )
            unsupported_dicts = [u.to_dict() for u in exc.unsupported]
            with transaction.atomic():
                spokesperson_msg = ConversationMessage.objects.create(
                    thread=thread,
                    role=ConversationMessage.Role.SPOKESPERSON,
                    content=(
                        "I had a response but it referenced things outside "
                        "this workspace's knowledge. The operator can review "
                        "what I almost said and decide whether to relax the "
                        "verifier."
                    ),
                    verification_warnings=unsupported_dicts,
                    rejected_synthesis=exc.synthesized_text or "",
                )
                thread.save(update_fields=["last_activity_at"])
            return Response(
                {
                    "user_message": ConversationMessageSerializer(user_msg).data,
                    "spokesperson_message": ConversationMessageSerializer(
                        spokesperson_msg,
                    ).data,
                    "knowledge_chunk_ids": [],
                    "verifier_rejection": {
                        "mode": "strict",
                        "rejected_synthesis": exc.synthesized_text or "",
                        "unsupported_claims": unsupported_dicts,
                    },
                },
                status=status.HTTP_422_UNPROCESSABLE_ENTITY,
            )
        except Exception as exc:
            logger.exception(
                "synthesize_spokesperson_reply hard-failed thread=%s",
                thread.pk,
            )
            # Defense in depth — synthesizer should already
            # return a degraded ReplyResult on any inner
            # failure. If it raised, persist a placeholder
            # reply so the thread keeps working.
            reply_text = (
                f"Couldn't generate a reply right now ({type(exc).__name__})."
            )
            reply_result_chunk_ids: list[str] = []
        else:
            reply_text = result.text
            reply_result_chunk_ids = list(result.chunk_ids)
            verifier_warnings = list(result.verification_warnings or [])

        with transaction.atomic():
            spokesperson_msg = ConversationMessage.objects.create(
                thread=thread,
                role=ConversationMessage.Role.SPOKESPERSON,
                content=reply_text,
                verification_warnings=verifier_warnings,
                rejected_synthesis=rejected_synthesis,
            )
            # Bump last_activity_at — auto_now only fires on
            # thread.save(). Force the update so the SPA's
            # thread list re-sorts correctly.
            thread.save(update_fields=["last_activity_at"])

        return Response(
            {
                "user_message": ConversationMessageSerializer(user_msg).data,
                "spokesperson_message": ConversationMessageSerializer(
                    spokesperson_msg,
                ).data,
                "knowledge_chunk_ids": reply_result_chunk_ids,
            },
            status=status.HTTP_201_CREATED,
        )
