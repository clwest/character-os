"""DRF viewset for Spokesperson."""
from __future__ import annotations

import logging

from rest_framework import viewsets
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

    @staticmethod
    def _workspace(workspace_id):
        from apps.accounts.models import Workspace

        return Workspace.objects.filter(pk=workspace_id).first()
