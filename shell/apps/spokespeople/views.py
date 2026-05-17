"""DRF viewset for Spokesperson."""
from __future__ import annotations

import logging

from rest_framework import status as drf_status, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.billing.services import TierLimitExceeded, check_spokesperson_limit
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.permissions import IsWorkspaceMember
from character_os.templates import TEMPLATES

from .models import Spokesperson
from .serializers import SpokespersonSerializer

logger = logging.getLogger(__name__)

HTTP_PAYMENT_REQUIRED = 402

# Runway voice presets, mirrored from
# ``media-engine/app/services/character_host_client.py``
# (SUPPORTED_VOICE_PRESETS). Kept local because CLAUDE.md forbids
# direct cross-service imports — Django talks to the media-engine
# over HTTP/JSON only. If Runway's preset list ever shifts, the
# media-engine side is authoritative + this list needs an update.
SUPPORTED_VOICE_PRESETS: frozenset[str] = frozenset({
    "victoria", "vincent", "clara", "drew", "skye", "max",
    "morgan", "felix", "mia", "marcus", "summer", "ruby",
    "aurora", "jasper", "leo", "adrian", "nina", "emma",
    "blake", "david", "maya", "nathan", "sam", "georgia",
    "petra", "adam", "zach", "violet", "roman", "luna",
})

# Visual templates, mirrored from
# ``media-engine/app/services/character_studio_client.py``
# (PORTRAIT_TEMPLATES). Same rationale as SUPPORTED_VOICE_PRESETS —
# CLAUDE.md forbids direct cross-service imports.
SUPPORTED_PORTRAIT_TEMPLATES: frozenset[str] = frozenset({
    "mascot", "founder", "coach", "local_guide",
})


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
        # SESSION 137: persist the Runway thumbnail URL (or mock-mode
        # data URI) so the detail page's <Portrait> can actually
        # render the image. Without this, every avatar-bound
        # spokesperson rendered the initials-fallback box.
        instance.portrait_path = result.thumbnail_url or ""
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
                "portrait_path",
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

        Set the spokesperson's voice. Two mutually-exclusive payload
        shapes:

        1. **Preset** — ``{"preset": "vincent"}``. Validates against
           ``SUPPORTED_VOICE_PRESETS`` and persists the preset name
           as ``voice_id`` directly. No media-engine call (Runway
           identifies presets by name on the avatar_video request).
        2. **Clone** — ``{"audio_data_uri": "...", "name?": "..."}``.
           Forwards to ``POST /internal/voices/`` on the media-
           engine. The returned ``voice_id`` (Runway-vended) is
           persisted. The hosted ``preview_url`` is returned for the
           SPA to play back but not persisted (we re-vend via a
           future poll route when one lands).

        If both are supplied, ``preset`` wins — keeps the contract
        deterministic without needing a strict-mode flag.

        Response shape (uniform across both paths):

            {
              "spokesperson": <serialized Spokesperson>,
              "voice": {
                "voice_id": "...",
                "status": "preset|ready|mock",
                "preview_url": "https://..." | null,
                "mock_mode": false
              }
            }

        Errors:
            400 — neither preset nor audio_data_uri supplied, or
                  the supplied preset is not in the supported set.
            502 — media-engine unreachable, or upstream Runway
                  rejection (carries upstream message). Clone path
                  only.
        """
        spokesperson: Spokesperson = self.get_object()  # type: ignore[assignment]
        preset = (request.data.get("preset") or "").strip().lower()
        audio_data_uri = (request.data.get("audio_data_uri") or "").strip()

        # --- Preset path ---
        if preset:
            if preset not in SUPPORTED_VOICE_PRESETS:
                return Response(
                    {
                        "error": f"unknown voice preset: {preset!r}",
                        "code": "unknown_preset",
                    },
                    status=drf_status.HTTP_400_BAD_REQUEST,
                )
            spokesperson.voice_id = preset
            spokesperson.save(update_fields=["voice_id", "updated_at"])
            logger.info(
                "spokesperson %s voice preset=%s",
                spokesperson.pk, preset,
            )
            serializer = self.get_serializer(spokesperson)
            return Response(
                {
                    "spokesperson": serializer.data,
                    "voice": {
                        "voice_id": preset,
                        "status": "preset",
                        "preview_url": None,
                        "mock_mode": False,
                    },
                }
            )

        # --- Clone path ---
        if not audio_data_uri:
            return Response(
                {
                    "error": "Provide either 'preset' or 'audio_data_uri'.",
                    "code": "missing_input",
                },
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

    @action(detail=True, methods=["post"], url_path="change-voice")
    def change_voice(self, request, pk=None):
        """``POST /api/spokespeople/{id}/change-voice/``.

        W11.2 (SESSION 170) — swap the spokesperson's voice preset
        on an already-baked avatar without re-baking. Mirrors
        ``clone-voice`` but for the simpler preset path: validates
        against ``SUPPORTED_VOICE_PRESETS``, fires the media-engine
        change-voice endpoint, updates ``voice_id`` on the row.

        Body shape: ``{preset: "marcus"}``. Returns the serialized
        spokesperson + the patch result so the SPA can surface
        success vs Runway-side failure.

        No-op cases:
        - Spokesperson has no ``runway_avatar_id``: just update
          ``voice_id`` in the DB; the next avatar bake will pick
          up the preset from the row.
        - Media-engine returns ``status="failed"``: persist the
          ``voice_id`` anyway (next avatar create / re-bake uses
          it). Operator sees the failure status and can retry.
        """
        preset = (request.data.get("preset") or "").strip()
        if not preset:
            raise ValidationError({"preset": "Required."})
        if preset not in SUPPORTED_VOICE_PRESETS:
            raise ValidationError({
                "preset": (
                    f"unsupported voice preset {preset!r}; pick one of "
                    f"{sorted(SUPPORTED_VOICE_PRESETS)}"
                ),
            })

        spokesperson: Spokesperson = self.get_object()
        patch_status = "skipped"
        patch_error: str | None = None

        if spokesperson.runway_avatar_id:
            try:
                with MediaEngineClient() as client:
                    result = client.change_avatar_voice(
                        avatar_id=spokesperson.runway_avatar_id,
                        voice_id=preset,
                        voice_kind="preset",
                    )
                patch_status = result.get("status") or "unknown"
                patch_error = result.get("error")
            except MediaEngineError as exc:
                logger.warning(
                    "change_voice media-engine error spokesperson=%s err=%s",
                    spokesperson.pk, exc,
                )
                patch_status = "failed"
                patch_error = str(exc)[:200]

        # Persist regardless — the next avatar create / re-bake
        # will read voice_id from the row even if the live PATCH
        # failed.
        spokesperson.voice_id = preset
        spokesperson.save(update_fields=["voice_id", "updated_at"])

        return Response(
            {
                "spokesperson": SpokespersonSerializer(
                    spokesperson, context={"request": request},
                ).data,
                "voice_patch": {
                    "status": patch_status,
                    "error": patch_error,
                },
            }
        )

    @action(detail=True, methods=["post"], url_path="rebake-avatar")
    def rebake_avatar(self, request, pk=None):
        """``POST /api/spokespeople/{id}/rebake-avatar/``.

        W11.2 (SESSION 170) — regenerate the portrait + bake a new
        Runway avatar from the spokesperson's current
        ``visual_subject``. Swaps ``runway_avatar_id``,
        ``portrait_path``, ``runway_avatar_status``, and
        (optionally) ``voice_id`` on the row.

        Cost: ~$5-10 Runway credits + 30-180s wait. The operator
        must explicitly opt in via the SPA confirm modal — this
        endpoint will fire whatever it's called with.

        Body shape (all fields optional):
            {
              "visual_subject": "...",  # override; persisted on the row
              "voice_preset": "...",    # override; persisted on the row
              "template": "coach"       # PORTRAIT_TEMPLATES preset
            }

        Response: serialized spokesperson with the new
        ``runway_avatar_id`` + ``portrait_path``.

        Errors:
            400 — invalid voice_preset / template / blank
                  visual_subject.
            502 — media-engine portrait or avatar bake failed.
        """
        spokesperson: Spokesperson = self.get_object()

        visual_subject = (
            request.data.get("visual_subject")
            or spokesperson.visual_subject
            or ""
        ).strip()
        voice_preset = (
            request.data.get("voice_preset") or spokesperson.voice_id or "vincent"
        ).strip()
        # SESSION 171 fix — was hardcoded to "coach", which silently
        # flipped Marcus from a stylized battle unicorn (mascot
        # template) to a photorealistic human (coach template) on
        # re-bake. The row now persists ``visual_template`` from
        # wizard creation (migration 0004), so re-bake defaults to
        # the operator's original choice. Explicit body override
        # still wins.
        template = (
            request.data.get("template")
            or spokesperson.visual_template
            or "mascot"
        ).strip()

        if not visual_subject:
            raise ValidationError({
                "visual_subject": "Required (non-empty).",
            })
        if voice_preset not in SUPPORTED_VOICE_PRESETS:
            raise ValidationError({
                "voice_preset": f"unsupported preset {voice_preset!r}",
            })
        if template not in SUPPORTED_PORTRAIT_TEMPLATES:
            raise ValidationError({
                "template": f"unsupported template {template!r}",
            })

        # Persist visual_subject / voice_preset / visual_template
        # upfront so the row carries the operator's intent even if
        # the bake fails.
        spokesperson.visual_subject = visual_subject
        spokesperson.voice_id = voice_preset
        spokesperson.visual_template = template
        spokesperson.save(
            update_fields=[
                "visual_subject",
                "voice_id",
                "visual_template",
                "updated_at",
            ],
        )

        try:
            with MediaEngineClient() as client:
                portrait = client.create_portrait(
                    template=template,
                    subject=visual_subject,
                )
                avatar = client.create_avatar(
                    name=spokesperson.name,
                    portrait_data_uri=portrait.portrait_data_uri,
                    voice_preset=voice_preset,
                    # W11.y (SESSION 175) — personality / brief
                    # split. The Runway avatar ``personality``
                    # field maps to our new ``personality``
                    # field. Pre-split rows have personality
                    # backfilled from business_brief so rebakes
                    # produce the same Runway-side personality
                    # until the operator splits the content.
                    personality=spokesperson.personality or None,
                )
        except MediaEngineError as exc:
            logger.warning(
                "rebake_avatar media-engine error spokesperson=%s err=%s",
                spokesperson.pk, exc,
            )
            spokesperson.runway_avatar_status = "failed"
            spokesperson.save(update_fields=["runway_avatar_status", "updated_at"])
            return Response(
                {"detail": f"avatar re-bake failed: {exc!s}"[:300]},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        spokesperson.runway_avatar_id = avatar.avatar_id
        spokesperson.runway_avatar_status = avatar.status
        spokesperson.portrait_path = avatar.thumbnail_url or ""
        # Ensure status is READY now that the avatar is fresh.
        if avatar.ok:
            spokesperson.status = Spokesperson.Status.READY
        spokesperson.save(
            update_fields=[
                "runway_avatar_id",
                "runway_avatar_status",
                "portrait_path",
                "status",
                "updated_at",
            ],
        )
        return Response(
            SpokespersonSerializer(
                spokesperson, context={"request": request},
            ).data
        )

    @action(detail=True, methods=["post"], url_path="refresh-portrait")
    def refresh_portrait(self, request, pk=None):
        """``POST /api/spokespeople/{id}/refresh-portrait/``.

        SESSION 169 follow-up. Runway's CloudFront thumbnail URLs are
        JWT-signed with ~30-day expiry — after that the SPA's
        ``<img src=portrait_path>`` 401s. This action re-fetches a
        fresh signed URL from Runway via the media-engine and
        persists it onto ``Spokesperson.portrait_path``.

        No-op when:
        * The spokesperson has no ``runway_avatar_id`` set (nothing
          to refresh) — returns the current row unchanged.
        * Media-engine is in mock mode — returns the row unchanged.
        * Media-engine / Runway returns no fresh URL (network /
          non-2xx) — returns the row unchanged + 200.

        Response: the serialized spokesperson (so the SPA can
        replace its cache without a separate GET).
        """
        spokesperson: Spokesperson = self.get_object()
        if not spokesperson.runway_avatar_id:
            return Response(
                SpokespersonSerializer(
                    spokesperson, context={"request": request},
                ).data
            )
        try:
            with MediaEngineClient() as client:
                fresh = client.refresh_avatar_thumbnail(
                    avatar_id=spokesperson.runway_avatar_id,
                )
        except MediaEngineError as exc:
            logger.warning(
                "refresh_portrait media-engine error spokesperson=%s err=%s",
                spokesperson.pk, exc,
            )
            return Response(
                SpokespersonSerializer(
                    spokesperson, context={"request": request},
                ).data
            )
        if fresh:
            spokesperson.portrait_path = fresh
            spokesperson.save(update_fields=["portrait_path", "updated_at"])
        return Response(
            SpokespersonSerializer(
                spokesperson, context={"request": request},
            ).data
        )

    @action(detail=False, methods=["get"], url_path="templates")
    def templates(self, _request):
        """``GET /api/spokespeople/templates/``.

        Returns the named-template tiles for the wizard's Step 1
        picker (SESSION 133 — wizard slice 10). Each tile gives
        the operator a starting point: name + brief + tone +
        visual_subject + visual_template + voice_preset. Picking a
        tile dispatches the fields into the wizard reducer; the
        operator can edit anything before submit.

        Static data — no DB, no Spokesperson row. Content is
        operator-collaborative starter material defined in
        ``character_os/templates/spokesperson_templates.py``.

        Shape::

            {
              "templates": [
                {
                  "key": "riggs",
                  "name": "Riggs",
                  "tagline": "SMB owners — ...",
                  "business_brief": "...",
                  "tone_archetype": "authority",
                  "visual_template": "founder",
                  "visual_subject": "...",
                  "voice_preset": "vincent"
                },
                ...
              ]
            }
        """
        payload = [
            {
                "key": t.key,
                "name": t.name,
                "tagline": t.tagline,
                "business_brief": t.business_brief,
                "tone_archetype": t.tone_archetype,
                "visual_template": t.visual_template,
                "visual_subject": t.visual_subject,
                "voice_preset": t.voice_preset,
            }
            for t in TEMPLATES
        ]
        return Response({"templates": payload})

    @action(detail=False, methods=["get"], url_path="voice-presets")
    def voice_presets(self, _request):
        """``GET /api/spokespeople/voice-presets/``.

        Returns the supported Runway voice presets for the Preset
        tab of the spokesperson voice-capture UI. Hard-coded here +
        mirrored from the media-engine's
        ``SUPPORTED_VOICE_PRESETS`` (cross-service imports are
        forbidden by CLAUDE.md).

        Shape: ``{"presets": ["adam", "adrian", ...]}`` — alpha-
        sorted for stable UI ordering.
        """
        return Response({"presets": sorted(SUPPORTED_VOICE_PRESETS)})

    @action(detail=False, methods=["post"], url_path="generate-portrait")
    def generate_portrait(self, request):
        """``POST /api/spokespeople/generate-portrait/``.

        Generates a portrait via Runway gen4_image (in mock mode
        when ``RUNWAY_API_KEY`` is unset) by wrapping the
        media-engine's ``POST /internal/portrait/`` (SESSION 125).

        Used by the wizard's Step 2 (Generate tab) — the operator
        picks a visual template + types a subject + optional style,
        and the returned data URI flows through the same Step-4
        submit path that Upload + Camera modes use. No
        Spokesperson row created here; the wizard accumulates
        client-side state until Confirm.

        Request body::

            {
              "template": "mascot" | "founder" | "coach" | "local_guide",
              "subject": "optional free-text — defaults to the template's built-in",
              "style": "optional free-text style hint"
            }

        Response::

            {
              "portrait_data_uri": "data:image/png;base64,...",
              "template": "mascot",
              "prompt": "a friendly brand mascot ...",
              "mock_mode": true
            }

        Errors:
            400 — unknown / missing template.
            502 — media-engine unreachable, or upstream Runway
                  rejection.
        """
        template = (request.data.get("template") or "").strip().lower()
        if not template:
            return Response(
                {"error": "template is required", "code": "missing_template"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )
        if template not in SUPPORTED_PORTRAIT_TEMPLATES:
            return Response(
                {
                    "error": f"unknown visual template: {template!r}",
                    "code": "unknown_template",
                },
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        subject = (request.data.get("subject") or "").strip() or None
        style = (request.data.get("style") or "").strip() or None

        try:
            with MediaEngineClient() as client:
                result = client.create_portrait(
                    template=template,
                    subject=subject,
                    style=style,
                )
        except MediaEngineError as exc:
            logger.warning(
                "generate_portrait failed template=%s err=%s",
                template, exc,
            )
            return Response(
                {
                    "error": str(exc)[:500],
                    "code": "upstream_media_engine",
                    "status_code": exc.status_code,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        return Response(
            {
                "portrait_data_uri": result.portrait_data_uri,
                "template": result.template,
                "prompt": result.prompt,
                "mock_mode": result.mock_mode,
            }
        )

    @staticmethod
    def _workspace(workspace_id):
        from apps.accounts.models import Workspace

        return Workspace.objects.filter(pk=workspace_id).first()
