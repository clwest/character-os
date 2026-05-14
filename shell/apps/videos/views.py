"""DRF viewset for Video."""
from __future__ import annotations

import logging

from rest_framework import viewsets
from rest_framework.response import Response

from apps.billing.services import TierLimitExceeded, check_video_limit
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.permissions import IsWorkspaceMember
from character_os.script_synthesis import build_render_brief

from .models import Video
from .serializers import VideoSerializer
from .tasks import poll_video_until_terminal

logger = logging.getLogger(__name__)


# HTTP 402 Payment Required — semantically right for "your tier
# doesn't include this." Surface as a structured payload the SPA can
# translate into an upgrade prompt.
HTTP_PAYMENT_REQUIRED = 402


class VideoViewSet(viewsets.ModelViewSet):
    """CRUD on videos belonging to spokespeople in the user's workspaces."""

    serializer_class = VideoSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Video.objects.none()
        return (
            Video.objects.filter(spokesperson__workspace__memberships__user=user)
            .select_related("spokesperson", "spokesperson__workspace")
            .distinct()
        )

    def create(self, request, *args, **kwargs):
        """Gate by tier limit *before* the serializer validates so we
        return 402 with the upgrade payload instead of a generic 400."""
        spokesperson_id = request.data.get("spokesperson")
        if spokesperson_id:
            workspace = self._workspace_for_spokesperson(spokesperson_id)
            if workspace is not None:
                try:
                    check_video_limit(workspace)
                except TierLimitExceeded as exc:
                    return Response(exc.payload, status=HTTP_PAYMENT_REQUIRED)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """After the row lands, fire the media-engine create call and
        enqueue the Celery poll task. Failure to enqueue surfaces as
        ``status=failed`` on the row — better to fail fast than leave
        the row in ``pending`` indefinitely.

        Note: in SESSION 109 we always fire the media-engine call on
        create. A future "draft mode" (create row without rendering)
        is possible via a request-level flag — but adds complexity
        the SPA doesn't need yet.
        """
        instance: Video = serializer.save()

        spokesperson = instance.spokesperson
        if not spokesperson.runway_avatar_id:
            instance.status = Video.Status.FAILED
            instance.error_message = (
                "spokesperson has no avatar yet — create one before "
                "rendering a video"
            )
            instance.save(
                update_fields=["status", "error_message", "updated_at"]
            )
            return

        operator_brief = instance.brief.strip() or spokesperson.business_brief.strip()
        if not operator_brief:
            instance.status = Video.Status.FAILED
            instance.error_message = (
                "no brief supplied and the spokesperson has no "
                "default business_brief"
            )
            instance.save(
                update_fields=["status", "error_message", "updated_at"]
            )
            return

        # SESSION 139 / K6 — RAG + script synthesis.
        # ``build_render_brief`` is always safe: never raises,
        # degrades to the operator's brief when knowledge is
        # empty or the LLM call fails. Persist the citation
        # before firing the media-engine so a Runway failure
        # later still leaves us able to audit what fed the
        # render.
        script = build_render_brief(spokesperson, operator_brief)
        instance.knowledge_chunk_ids = script.chunk_ids
        instance.save(update_fields=["knowledge_chunk_ids", "updated_at"])
        brief = script.brief

        # SESSION 140 — Runway gen4_turbo is image-to-video: it
        # animates the spokesperson's portrait based on the brief.
        # Pass the portrait URL (populated by the avatar bind in
        # the wizard / seed_cast pipeline). Real-mode media-engine
        # rejects with 400 "prompt_image is required" without it;
        # mock-mode tolerates either.
        try:
            with MediaEngineClient() as client:
                result = client.create_video(
                    kind=instance.kind,
                    spokesperson_avatar_id=spokesperson.runway_avatar_id,
                    brief=brief,
                    prompt_image=spokesperson.portrait_path or None,
                )
        except MediaEngineError as exc:
            logger.warning(
                "media-engine create_video failed video=%s err=%s",
                instance.pk, exc,
            )
            instance.status = Video.Status.FAILED
            instance.error_message = f"media-engine: {exc}"[:500]
            instance.save(
                update_fields=["status", "error_message", "updated_at"]
            )
            return

        instance.media_engine_task_id = result.task_id
        instance.status = Video.Status.RENDERING
        instance.save(
            update_fields=[
                "media_engine_task_id",
                "status",
                "updated_at",
            ]
        )

        # Enqueue the poll. delay() returns immediately; the Celery
        # worker writes terminal state back to the row asynchronously.
        try:
            poll_video_until_terminal.delay(str(instance.pk))
        except Exception as exc:
            # Broker unreachable / serialisation failure. The row
            # would otherwise sit in `rendering` forever — surface
            # the failure so the SPA can prompt a retry.
            logger.warning(
                "failed to enqueue poll_video_until_terminal video=%s err=%s",
                instance.pk, exc,
            )
            instance.status = Video.Status.FAILED
            instance.error_message = f"failed to enqueue poll: {exc}"[:500]
            instance.save(
                update_fields=["status", "error_message", "updated_at"]
            )
            return

        logger.info(
            "video %s create→render task=%s kind=%s mock=%s",
            instance.pk, result.task_id, result.kind, result.mock_mode,
        )

    @staticmethod
    def _workspace_for_spokesperson(spokesperson_id):
        from apps.spokespeople.models import Spokesperson

        sp = (
            Spokesperson.objects.filter(pk=spokesperson_id)
            .select_related("workspace")
            .first()
        )
        return sp.workspace if sp else None
