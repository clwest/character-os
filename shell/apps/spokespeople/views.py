"""DRF viewset for Spokesperson."""
from __future__ import annotations

import logging

from rest_framework import status as drf_status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.billing.services import TierLimitExceeded, check_spokesperson_limit
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.permissions import IsWorkspaceMember

from .models import Spokesperson
from .serializers import SpokespersonSerializer

logger = logging.getLogger(__name__)

HTTP_PAYMENT_REQUIRED = 402


class SpokespersonViewSet(viewsets.ModelViewSet):
    """CRUD on spokespeople in the requesting user's workspaces."""

    serializer_class = SpokespersonSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Spokesperson.objects.none()
        return (
            Spokesperson.objects.filter(workspace__memberships__user=user)
            .select_related("workspace")
            .distinct()
        )

    def create(self, request, *args, **kwargs):
        """Gate spokesperson creation by tier limit. 402 with the
        upgrade payload when at cap; otherwise fall through to default
        DRF create logic, then optionally fire the media-engine avatar
        create when ``portrait_data_uri`` is in the payload.
        """
        workspace_id = request.data.get("workspace")
        if workspace_id:
            workspace = self._workspace(workspace_id)
            if workspace is not None:
                try:
                    check_spokesperson_limit(workspace)
                except TierLimitExceeded as exc:
                    return Response(exc.payload, status=HTTP_PAYMENT_REQUIRED)
        return super().create(request, *args, **kwargs)

    def perform_create(self, serializer):
        """After the row lands, optionally fire the avatar create
        against the media-engine. Failures are logged + surfaced via
        the persisted ``runway_avatar_status`` ("failed") but do not
        roll back the row — Spokesperson creation is meaningful even
        without an avatar (the operator can retry later).
        """
        portrait_data_uri = serializer.validated_data.pop(
            "portrait_data_uri", ""
        ) or ""
        voice_preset = serializer.validated_data.pop("voice_preset", "") or ""

        instance: Spokesperson = serializer.save()

        if not portrait_data_uri.strip():
            return  # no portrait → SETUP_NEEDED, no avatar call

        try:
            with MediaEngineClient() as client:
                result = client.create_avatar(
                    name=instance.name,
                    portrait_data_uri=portrait_data_uri,
                    voice_preset=voice_preset or None,
                )
        except MediaEngineError as exc:
            logger.warning(
                "media-engine avatar create failed spokesperson=%s err=%s",
                instance.pk, exc,
            )
            instance.runway_avatar_status = "failed"
            instance.save(update_fields=["runway_avatar_status", "updated_at"])
            return

        instance.runway_avatar_id = result.avatar_id
        instance.runway_avatar_status = result.status
        if voice_preset:
            instance.voice_id = voice_preset
        # Once the avatar is ready (or its mock equivalent), the
        # spokesperson is ready to use.
        if result.ok:
            instance.status = Spokesperson.Status.READY
        instance.save(
            update_fields=[
                "runway_avatar_id",
                "runway_avatar_status",
                "voice_id",
                "status",
                "updated_at",
            ]
        )
        logger.info(
            "spokesperson %s avatar=%s status=%s mock=%s",
            instance.pk, result.avatar_id, result.status, result.mock_mode,
        )

    @action(detail=True, methods=["post"], url_path="clone-voice")
    def clone_voice(self, request, pk=None):
        """``POST /api/spokespeople/{id}/clone-voice/``.

        Takes ``{audio_data_uri, name?}``, forwards to the media-
        engine's ``POST /internal/voices/``, and persists the
        returned ``voice_id`` onto the Spokesperson row. The Runway-
        hosted ``preview_url`` is returned in the response for the
        SPA to play back; we don't persist it (Runway can re-vend it
        via a future poll route when one lands).

        Response shape:

            {
              "spokesperson": <serialized Spokesperson>,
              "voice": {
                "voice_id": "...",
                "status": "ready|mock",
                "preview_url": "https://...",
                "mock_mode": false
              }
            }

        Errors:
            400 — audio_data_uri missing.
            502 — media-engine unreachable, or upstream Runway
                  rejection (carries upstream message).
        """
        spokesperson: Spokesperson = self.get_object()  # type: ignore[assignment]
        audio_data_uri = (request.data.get("audio_data_uri") or "").strip()
        if not audio_data_uri:
            return Response(
                {"error": "audio_data_uri is required", "code": "missing_audio"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        name = (request.data.get("name") or "").strip() or None

        try:
            with MediaEngineClient() as client:
                result = client.clone_voice(
                    audio_data_uri=audio_data_uri,
                    name=name,
                )
        except MediaEngineError as exc:
            logger.warning(
                "clone_voice failed spokesperson=%s err=%s",
                spokesperson.pk, exc,
            )
            return Response(
                {
                    "error": str(exc)[:500],
                    "code": "upstream_media_engine",
                    "status_code": exc.status_code,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        spokesperson.voice_id = result.voice_id
        spokesperson.save(update_fields=["voice_id", "updated_at"])

        logger.info(
            "spokesperson %s voice cloned voice=%s status=%s mock=%s",
            spokesperson.pk, result.voice_id, result.status, result.mock_mode,
        )

        serializer = self.get_serializer(spokesperson)
        return Response(
            {
                "spokesperson": serializer.data,
                "voice": {
                    "voice_id": result.voice_id,
                    "status": result.status,
                    "preview_url": result.preview_url,
                    "mock_mode": result.mock_mode,
                },
            }
        )

    @staticmethod
    def _workspace(workspace_id):
        from apps.accounts.models import Workspace

        return Workspace.objects.filter(pk=workspace_id).first()
