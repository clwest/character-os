"""DRF viewset for Video.

SESSION 143 / V6 reframed how this works:

* ``kind=spokesperson_ad`` now flows through the V0+ composition
  arc — perform_create builds a ``talking_head`` composition and
  enqueues ``execute_composition``. The legacy media-engine
  ``/internal/videos/`` call is no longer reached for this kind.
  Terminal-state fields on the Video row are populated by the
  Composition→Video sync signal in ``apps.videos.signals``.
* Other kinds (cinematic_video, dialogue_scene, etc.) still
  fall through to the legacy media-engine path. Those kinds
  were never wired in production v1 anyway — the SPA only
  emits ``spokesperson_ad`` — but the fallback keeps any
  in-flight integrations from breaking.
* The K6 build_render_brief synthesis stays in perform_create
  (eager): we want Video.knowledge_chunk_ids populated *before*
  composition execution starts so the audit trail is intact
  even if the composition fails. The composition step receives
  the already-synthesized brief and runs with use_knowledge=False.
"""
from __future__ import annotations

import logging
import os

from django.conf import settings as django_settings
from rest_framework import viewsets
from rest_framework.response import Response

from apps.billing.services import TierLimitExceeded, check_video_limit
from apps.compositions.starters import talking_head
from apps.compositions.tasks import execute_composition
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


def _runway_force_mock() -> bool:
    """Mirror the same flag check used by other primitives.
    Composition mock-mode flows from operator/env intent at
    create time; once set, every step honors it (V0 contract
    rule 9)."""
    if os.environ.get("RUNWAY_FORCE_MOCK"):
        return True
    return bool(getattr(django_settings, "RUNWAY_FORCE_MOCK", False))


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
        # SESSION 142 / K6.2 — pre-render validation. Fail fast
        # at the shell layer with a clear operator-facing message
        # rather than letting media-engine return an opaque 400
        # ("avatar_id is required" / "prompt_image is required").
        if not spokesperson.runway_avatar_id:
            instance.status = Video.Status.FAILED
            instance.error_message = (
                "spokesperson has no avatar yet — finish the create-"
                "spokesperson wizard (or run seed_cast) before rendering"
            )
            instance.save(
                update_fields=["status", "error_message", "updated_at"]
            )
            return
        if not spokesperson.portrait_path:
            instance.status = Video.Status.FAILED
            instance.error_message = (
                "spokesperson has no portrait yet — finish the create-"
                "spokesperson wizard (the portrait is generated alongside "
                "the avatar) before rendering"
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
        # before firing the render so a downstream failure
        # leaves us able to audit what fed the render.
        script = build_render_brief(spokesperson, operator_brief)
        instance.knowledge_chunk_ids = script.chunk_ids
        instance.save(update_fields=["knowledge_chunk_ids", "updated_at"])
        brief = script.brief

        # SESSION 143 / V6 — backwards-compat shim. For
        # ``spokesperson_ad`` we route through the V0+
        # composition arc: build a ``talking_head`` composition
        # (knowledge already synthesized above, so the
        # primitive runs use_knowledge=False), enqueue
        # ``execute_composition``, and let the
        # Composition→Video sync signal in apps.videos.signals
        # populate output_path / status / etc. when the
        # composition reaches a terminal state.
        if instance.kind == Video.Kind.SPOKESPERSON_AD:
            self._dispatch_via_composition(instance, brief)
            return

        # Fallback — other kinds still flow through the legacy
        # /internal/videos/ media-engine path. v1 production
        # only exercises spokesperson_ad; this branch exists
        # so any in-flight integrations don't break.
        self._dispatch_via_legacy(instance, brief)

    def _dispatch_via_composition(self, instance: Video, brief: str) -> None:
        spokesperson = instance.spokesperson
        try:
            composition = talking_head(
                workspace=spokesperson.workspace,
                spokesperson=spokesperson,
                script=brief,
                # Knowledge already synthesized into ``brief``
                # — don't re-run synthesis at step execute time.
                use_knowledge=False,
                mock_mode=_runway_force_mock(),
                name=instance.title or f"Video {instance.pk}",
            )
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception(
                "v6 talking_head starter failed video=%s", instance.pk,
            )
            instance.status = Video.Status.FAILED
            instance.error_message = f"composition setup: {exc}"[:500]
            instance.save(
                update_fields=["status", "error_message", "updated_at"],
            )
            return

        # Stamp the citation list onto the composition for audit
        # parity with the Video row (K6 contract).
        if instance.knowledge_chunk_ids:
            composition.knowledge_chunk_ids = list(instance.knowledge_chunk_ids)
            composition.save(
                update_fields=["knowledge_chunk_ids", "updated_at"],
            )

        instance.composition = composition
        instance.status = Video.Status.RENDERING
        instance.save(
            update_fields=["composition", "status", "updated_at"],
        )

        try:
            execute_composition.delay(str(composition.pk))
        except Exception as exc:
            # Broker unreachable / serialisation failure. Mirror
            # the legacy enqueue-failure recovery: mark FAILED
            # so the SPA can prompt a retry.
            logger.warning(
                "v6 failed to enqueue execute_composition video=%s composition=%s err=%s",
                instance.pk, composition.pk, exc,
            )
            instance.status = Video.Status.FAILED
            instance.error_message = f"failed to enqueue composition: {exc}"[:500]
            instance.save(
                update_fields=["status", "error_message", "updated_at"],
            )
            return

        logger.info(
            "v6 video %s -> composition %s queued mock=%s",
            instance.pk, composition.pk, composition.mock_mode,
        )

    def _dispatch_via_legacy(self, instance: Video, brief: str) -> None:
        """Legacy path — kept for non-spokesperson_ad kinds that
        the composition arc doesn't yet have starters for. v1
        production only emits spokesperson_ad so this branch is
        rarely exercised."""
        spokesperson = instance.spokesperson
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

        try:
            poll_video_until_terminal.delay(str(instance.pk))
        except Exception as exc:
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
            "legacy video %s create->render task=%s kind=%s mock=%s",
            instance.pk, result.task_id, result.kind, result.mock_mode,
        )

    @staticmethod
    def _workspace_for_spokesperson(spokesperson_id):
        from apps.spokespeople.models import Teammate

        sp = (
            Teammate.objects.filter(pk=spokesperson_id)
            .select_related("workspace")
            .first()
        )
        return sp.workspace if sp else None
