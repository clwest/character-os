"""DRF viewset for Teammate.

Historical note: previously `TeammateViewSet`; renamed to
`TeammateViewSet` in SESSION 240 per ratified §17.1.b. The URL path
`/api/spokespeople/`, router basename `spokesperson`, response
payload keys, and error-code strings are external contracts and
remain unchanged per the compatibility discipline.
"""
from __future__ import annotations

import logging
from pathlib import Path

from rest_framework import status as drf_status, status, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import ValidationError
from rest_framework.response import Response

from apps.billing.services import TierLimitExceeded, check_teammate_limit
from apps.identity import services as identity_services
from apps.identity.models import (
    ExecutionMode,
    ExecutionModeActual,
    GenerationProvider,
    PrequalificationSourceCall,
)
from apps.identity.prequalification import (
    PortraitRepresentation,
    RealtimeRepresentation,
    VoiceRepresentation,
)
from character_os.clients.media_engine import (
    AvatarCreateResult,
    MediaEngineClient,
    MediaEngineError,
    VoiceCloneResult,
)
from character_os.permissions import IsWorkspaceMember
from character_os.templates import TEMPLATES

from .models import Teammate
from .serializers import TeammateSerializer

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


# ---------------------------------------------------------------------
# Prequalification-authoring value-object builders.
#
# §19 Step 4.d — production write sites in this module route their
# canonical persistence through
# ``apps.identity.services.record_prequalification_representation``.
# The provider calls themselves stay exactly where they were; only
# the persistence changes. These small builders translate the
# media-engine result dataclasses into the value objects
# ``record_prequalification_representation`` accepts.
#
# ``execution_mode`` / ``execution_mode_actual`` are populated to
# preserve the Amendment 3 pairing invariant (non-legacy providers
# always carry both fields non-NULL). Mock-mode results record
# ``FORCED_MOCK`` / ``MOCK`` literally per Amendment 4's provenance-
# literal rule.
# ---------------------------------------------------------------------


def _portrait_representation_from_avatar_result(
    portrait_uri: str,
    result: AvatarCreateResult,
) -> PortraitRepresentation:
    """Build a portrait value object from the avatar-create result.

    ``portrait_uri`` is chosen upstream (SESSION 228 rule: prefer the
    operator-supplied reference image over Runway's regenerated
    interpretation for what appears on the workspace portrait tile;
    Runway's ``avatar_id`` continues to drive video generation).
    """
    is_mock = result.mock_mode
    return PortraitRepresentation(
        portrait_uri=portrait_uri,
        provider=(
            GenerationProvider.MOCK if is_mock
            else GenerationProvider.RUNWAY_AVATAR
        ),
        provider_model="",
        execution_mode=(
            ExecutionMode.FORCED_MOCK if is_mock
            else ExecutionMode.REAL_REQUIRED
        ),
        execution_mode_actual=(
            ExecutionModeActual.MOCK if is_mock
            else ExecutionModeActual.REAL
        ),
        mock_mode=is_mock,
        provider_response={
            "avatar_id": result.avatar_id,
            "status": result.status,
            "thumbnail_url": result.thumbnail_url,
        },
    )


def _realtime_representation_from_avatar_result(
    result: AvatarCreateResult,
) -> RealtimeRepresentation:
    """Build a realtime value object (Runway ``avatar_id``) from the
    avatar-create result. Provider-side identifier lives in the paired
    ``GenerationRecord.prompt_snapshot['provider_realtime_id']`` per
    §17.10.a Amendment 4 provider-output convention; §17.10.a explicitly
    bars this identifier from the permanent canonical schema.
    """
    is_mock = result.mock_mode
    return RealtimeRepresentation(
        provider_realtime_id=result.avatar_id,
        provider=(
            GenerationProvider.MOCK if is_mock
            else GenerationProvider.RUNWAY_AVATAR
        ),
        provider_model="",
        execution_mode=(
            ExecutionMode.FORCED_MOCK if is_mock
            else ExecutionMode.REAL_REQUIRED
        ),
        execution_mode_actual=(
            ExecutionModeActual.MOCK if is_mock
            else ExecutionModeActual.REAL
        ),
        mock_mode=is_mock,
        provider_response={
            "status": result.status,
            "thumbnail_url": result.thumbnail_url,
        },
    )


def _voice_representation_from_preset(
    preset: str,
    *,
    mock_mode: bool,
) -> VoiceRepresentation:
    """Named Runway voice presets bind by name — no media-engine call
    is required. Presets are Runway-owned voice capabilities per
    §17.10.a Amendment 4's voice-preset handling ratification, so
    ``provider=RUNWAY_TTS`` is the honest label. Execution fields
    reflect that the binding is a real Runway resource; no fallback
    to mock occurred.
    """
    return VoiceRepresentation(
        provider_voice_id=preset,
        provider=GenerationProvider.RUNWAY_TTS,
        provider_model="",
        execution_mode=ExecutionMode.REAL_REQUIRED,
        execution_mode_actual=ExecutionModeActual.REAL,
        mock_mode=mock_mode,
        voice_kind="preset",
        provider_response={},
    )


def _voice_representation_from_clone_result(
    result: VoiceCloneResult,
) -> VoiceRepresentation:
    """Build a voice value object from the clone_voice media-engine
    result. Preserves ``preview_url`` in ``provider_response`` for
    audit but does not persist it in a mirror.
    """
    is_mock = result.mock_mode
    return VoiceRepresentation(
        provider_voice_id=result.voice_id,
        provider=(
            GenerationProvider.MOCK if is_mock
            else GenerationProvider.RUNWAY_TTS
        ),
        provider_model="",
        execution_mode=(
            ExecutionMode.FORCED_MOCK if is_mock
            else ExecutionMode.REAL_REQUIRED
        ),
        execution_mode_actual=(
            ExecutionModeActual.MOCK if is_mock
            else ExecutionModeActual.REAL
        ),
        mock_mode=is_mock,
        voice_kind="clone",
        provider_response={
            "status": result.status,
            "preview_url": result.preview_url,
        },
    )


def _portrait_required_response() -> Response:
    """§19 Step 4.d D1 response — canonical bundle-approval invariant
    refuses a prequalification-authoring event without a
    ``portrait_reference/front``. Voice-first setup is deliberately
    not supported under Amendment 4's ratified authoring shape.
    Documented for a coordinated frontend pass per operator direction.
    """
    return Response(
        {
            "error": "A portrait is required before setting a voice.",
            "code": "portrait_required",
        },
        status=drf_status.HTTP_409_CONFLICT,
    )


def _voice_samples_dir() -> Path:
    """Resolve ``<repo-root>/web/public/voice-samples``.

    Static-file convention shared with ``bake_voice_samples``. Voice
    presets whose MP3 lives here get a real ``sample_url``; the rest
    surface as null (SPA renders "Sample coming soon").
    """
    # apps/spokespeople/views.py → ../../.. = shell/; parent = repo root
    return Path(__file__).resolve().parents[3] / "web" / "public" / "voice-samples"


class TeammateViewSet(viewsets.ModelViewSet):
    """CRUD on teammates in the requesting user's workspaces.

    URL path stays ``/api/spokespeople/`` and router basename stays
    ``spokesperson`` per §17.1.b compatibility. Response payload keys
    (e.g. ``"spokesperson":``) are external contracts consumed by the
    SPA — those also stay unchanged.
    """

    serializer_class = TeammateSerializer
    permission_classes = [IsWorkspaceMember]

    def get_queryset(self):
        user = self.request.user
        if not user.is_authenticated:
            return Teammate.objects.none()
        return (
            Teammate.objects.filter(workspace__memberships__user=user)
            .select_related("workspace")
            .distinct()
        )

    def create(self, request, *args, **kwargs):
        """Gate teammate creation by tier limit. 402 with the
        upgrade payload when at cap; otherwise fall through to default
        DRF create logic, then optionally fire the media-engine avatar
        create when ``portrait_data_uri`` is in the payload.
        """
        workspace_id = request.data.get("workspace")
        if workspace_id:
            workspace = self._workspace(workspace_id)
            if workspace is not None:
                try:
                    check_teammate_limit(workspace)
                except TierLimitExceeded as exc:
                    return Response(exc.payload, status=HTTP_PAYMENT_REQUIRED)
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as exc:
            # Log the field errors so future validation regressions are
            # diagnosable from the server log alone — DRF's default 400
            # body reaches the SPA but doesn't leave a server-side
            # breadcrumb. Portrait data URI omitted from the keys list
            # so the log line stays scannable (base64 payload is huge).
            payload_keys = sorted(k for k in request.data.keys() if k != "portrait_data_uri")
            logger.warning(
                "teammate create 400 keys=%s errors=%s",
                payload_keys, exc.detail,
            )
            raise

    def perform_create(self, serializer):
        """After the row lands, optionally fire the avatar create
        against the media-engine. Failures are logged + surfaced via
        the persisted ``runway_avatar_status`` ("failed") but do not
        roll back the row — Teammate creation is meaningful even
        without an avatar (the operator can retry later).

        §19 Step 4.d — the three ``Teammate`` compatibility mirrors
        (``portrait_path`` / ``voice_id`` / ``runway_avatar_id``) are
        persisted through
        ``identity_services.record_prequalification_representation``.
        The provider call itself is unchanged; only where its result
        lands changes. Non-mirror fields (``runway_avatar_status``,
        ``status``) continue to be written directly.
        """
        portrait_data_uri = serializer.validated_data.pop(
            "portrait_data_uri", ""
        ) or ""
        voice_preset = serializer.validated_data.pop("voice_preset", "") or ""

        instance: Teammate = serializer.save()

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
                "media-engine avatar create failed teammate=%s err=%s",
                instance.pk, exc,
            )
            instance.runway_avatar_status = "failed"
            instance.save(update_fields=["runway_avatar_status", "updated_at"])
            return

        # SESSION 137: persist the Runway thumbnail URL (or mock-mode
        # data URI) so the detail page's <Portrait> can actually
        # render the image. Without this, every avatar-bound
        # teammate rendered the initials-fallback box.
        #
        # SESSION 202: prefer a LOCAL persisted copy of the
        # portrait so the JWT-signed CloudFront URL doesn't
        # expire out from under the SPA every ~30 days. Best
        # effort — if the persist call fails (mock mode, network
        # hiccup), fall back to the JWT-signed URL.
        portrait_url = result.thumbnail_url or ""
        if result.avatar_id and not result.mock_mode:
            try:
                with MediaEngineClient() as client:
                    local_url = client.persist_avatar_portrait(
                        avatar_id=result.avatar_id,
                    )
                if local_url:
                    portrait_url = local_url
            except MediaEngineError as exc:
                logger.warning(
                    "persist_portrait failed during create "
                    "teammate=%s avatar=%s err=%s — falling "
                    "back to JWT-signed URL",
                    instance.pk, result.avatar_id, exc,
                )
        # SESSION 228 — display the reference image the operator picked,
        # not Runway's regenerated interpretation. Runway's avatar API
        # treats the input as a reference (their word: `referenceImage`)
        # and produces its own rendition; storing that rendition as the
        # workspace portrait creates a "this isn't the teammate I
        # made" mismatch. The Runway avatar_id is still what drives
        # video generation — this only affects what the workspace UI
        # displays as the identity portrait.
        portrait_uri_for_mirror = portrait_data_uri or portrait_url

        # §19 Step 4.d — canonical write for the three mirrors.
        author = (
            self.request.user
            if getattr(self.request, "user", None)
            and self.request.user.is_authenticated
            else None
        )
        try:
            identity_services.record_prequalification_representation(
                instance,
                source_call=PrequalificationSourceCall.WIZARD_CREATE,
                author=author,
                portrait=_portrait_representation_from_avatar_result(
                    portrait_uri_for_mirror, result,
                ),
                voice=(
                    _voice_representation_from_preset(
                        voice_preset, mock_mode=result.mock_mode,
                    )
                    if voice_preset
                    else None
                ),
                realtime=_realtime_representation_from_avatar_result(result),
            )
        except identity_services.BundleApprovalError:
            # Cannot legitimately fire here — perform_create supplied
            # a portrait input. Surface as failed avatar status so a
            # deploy misconfiguration doesn't silently corrupt state.
            logger.exception(
                "perform_create canonical write failed teammate=%s "
                "avatar=%s",
                instance.pk, result.avatar_id,
            )
            instance.runway_avatar_status = "failed"
            instance.save(update_fields=["runway_avatar_status", "updated_at"])
            return

        # Non-mirror fields. Refresh to pick up sync's mirror writes
        # + updated_at before we write status / runway_avatar_status.
        instance.refresh_from_db()
        instance.runway_avatar_status = result.status
        if result.ok:
            instance.status = Teammate.Status.READY
        instance.save(
            update_fields=["runway_avatar_status", "status", "updated_at"],
        )
        logger.info(
            "teammate %s avatar=%s status=%s mock=%s",
            instance.pk, result.avatar_id, result.status, result.mock_mode,
        )

    @action(detail=True, methods=["post"], url_path="clone-voice")
    def clone_voice(self, request, pk=None):
        """``POST /api/spokespeople/{id}/clone-voice/``.

        Set the teammate's voice. Two mutually-exclusive payload
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

        Response shape (uniform across both paths; the ``spokesperson``
        response key is an external contract consumed by the SPA and
        stays unchanged per §17.1.b compatibility):

            {
              "spokesperson": <serialized Teammate>,
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
        teammate: Teammate = self.get_object()  # type: ignore[assignment]
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
            # §19 Step 4.d — canonical write. Voice-only authoring on
            # a teammate with no approved portrait/front reference
            # fails with `portrait_required` per operator D1 direction.
            author = (
                self.request.user
                if getattr(self.request, "user", None)
                and self.request.user.is_authenticated
                else None
            )
            try:
                identity_services.record_prequalification_representation(
                    teammate,
                    source_call=PrequalificationSourceCall.CLONE_VOICE_PRESET,
                    author=author,
                    voice=_voice_representation_from_preset(
                        preset, mock_mode=False,
                    ),
                )
            except identity_services.BundleApprovalError as exc:
                if exc.code == "missing_front_portrait":
                    return _portrait_required_response()
                raise

            teammate.refresh_from_db()
            logger.info(
                "teammate %s voice preset=%s",
                teammate.pk, preset,
            )
            serializer = self.get_serializer(teammate)
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
                "clone_voice failed teammate=%s err=%s",
                teammate.pk, exc,
            )
            return Response(
                {
                    "error": str(exc)[:500],
                    "code": "upstream_media_engine",
                    "status_code": exc.status_code,
                },
                status=drf_status.HTTP_502_BAD_GATEWAY,
            )

        # §19 Step 4.d — canonical write for the cloned voice. Same
        # D1 portrait-required guard as the preset path.
        author = (
            self.request.user
            if getattr(self.request, "user", None)
            and self.request.user.is_authenticated
            else None
        )
        try:
            identity_services.record_prequalification_representation(
                teammate,
                source_call=PrequalificationSourceCall.CLONE_VOICE_CLONE,
                author=author,
                voice=_voice_representation_from_clone_result(result),
            )
        except identity_services.BundleApprovalError as exc:
            if exc.code == "missing_front_portrait":
                return _portrait_required_response()
            raise

        teammate.refresh_from_db()
        logger.info(
            "teammate %s voice cloned voice=%s status=%s mock=%s",
            teammate.pk, result.voice_id, result.status, result.mock_mode,
        )

        serializer = self.get_serializer(teammate)
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

        W11.2 (SESSION 170) — swap the teammate's voice preset
        on an already-baked avatar without re-baking. Mirrors
        ``clone-voice`` but for the simpler preset path: validates
        against ``SUPPORTED_VOICE_PRESETS``, fires the media-engine
        change-voice endpoint, updates ``voice_id`` on the row.

        Body shape: ``{preset: "marcus"}``. Returns the serialized
        teammate (under the ``spokesperson`` external-contract key)
        + the patch result so the SPA can surface success vs
        Runway-side failure.

        No-op cases:
        - Teammate has no ``runway_avatar_id``: just update
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

        teammate: Teammate = self.get_object()
        patch_status = "skipped"
        patch_error: str | None = None

        if teammate.runway_avatar_id:
            try:
                with MediaEngineClient() as client:
                    result = client.change_avatar_voice(
                        avatar_id=teammate.runway_avatar_id,
                        voice_id=preset,
                        voice_kind="preset",
                    )
                patch_status = result.get("status") or "unknown"
                patch_error = result.get("error")
            except MediaEngineError as exc:
                logger.warning(
                    "change_voice media-engine error teammate=%s err=%s",
                    teammate.pk, exc,
                )
                patch_status = "failed"
                patch_error = str(exc)[:200]

        # §19 Step 4.d — canonical write regardless of the media-
        # engine PATCH outcome. The PATCH is a runtime side-effect on
        # Runway's avatar; the canonical binding is the source of
        # truth for the next avatar bake. If the teammate has no
        # approved portrait/front reference (no prior canonical
        # authoring event), fail cleanly per D1.
        author = (
            request.user
            if getattr(request, "user", None) and request.user.is_authenticated
            else None
        )
        try:
            identity_services.record_prequalification_representation(
                teammate,
                source_call=PrequalificationSourceCall.CHANGE_VOICE,
                author=author,
                voice=_voice_representation_from_preset(
                    preset, mock_mode=False,
                ),
            )
        except identity_services.BundleApprovalError as exc:
            if exc.code == "missing_front_portrait":
                return _portrait_required_response()
            raise

        teammate.refresh_from_db()
        return Response(
            {
                "spokesperson": TeammateSerializer(
                    teammate, context={"request": request},
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
        Runway avatar from the teammate's current
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

        Response: serialized teammate with the new
        ``runway_avatar_id`` + ``portrait_path``.

        Errors:
            400 — invalid voice_preset / template / blank
                  visual_subject.
            502 — media-engine portrait or avatar bake failed.
        """
        teammate: Teammate = self.get_object()

        visual_subject = (
            request.data.get("visual_subject")
            or teammate.visual_subject
            or ""
        ).strip()
        voice_preset = (
            request.data.get("voice_preset") or teammate.voice_id or "vincent"
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
            or teammate.visual_template
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

        # Persist visual_subject / visual_template upfront so the row
        # carries the operator's non-mirror intent even if the bake
        # fails.
        # §19 Step 4.d — voice_id is no longer written directly here.
        # A requested voice change that is part of a failed rebake is
        # deliberately not treated as successfully-authored identity
        # state; canonical voice remains whatever the last successful
        # bake / clone / preset event admitted. The compatibility
        # mirror ``voice_id`` therefore stays consistent with
        # canonical state through a rebake failure. The
        # ``voice_preset`` local is still passed to the media-engine
        # avatar-create call below and, on bake success, is persisted
        # canonically as part of the single authoring event.
        teammate.visual_subject = visual_subject
        teammate.visual_template = template
        teammate.save(
            update_fields=[
                "visual_subject",
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
                    name=teammate.name,
                    portrait_data_uri=portrait.portrait_data_uri,
                    voice_preset=voice_preset,
                    # W11.y (SESSION 175) — personality / brief
                    # split. The Runway avatar ``personality``
                    # field maps to our new ``personality``
                    # field. Pre-split rows have personality
                    # backfilled from business_brief so rebakes
                    # produce the same Runway-side personality
                    # until the operator splits the content.
                    personality=teammate.personality or None,
                )
        except MediaEngineError as exc:
            logger.warning(
                "rebake_avatar media-engine error teammate=%s err=%s",
                teammate.pk, exc,
            )
            teammate.runway_avatar_status = "failed"
            teammate.save(update_fields=["runway_avatar_status", "updated_at"])
            return Response(
                {"detail": f"avatar re-bake failed: {exc!s}"[:300]},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # SESSION 202 — same persist-locally hook as the create
        # flow above. Best effort; falls back to the JWT-signed
        # URL when the persist call doesn't return one.
        portrait_url = avatar.thumbnail_url or ""
        if avatar.avatar_id and not avatar.mock_mode:
            try:
                with MediaEngineClient() as client:
                    local_url = client.persist_avatar_portrait(
                        avatar_id=avatar.avatar_id,
                    )
                if local_url:
                    portrait_url = local_url
            except MediaEngineError as exc:
                logger.warning(
                    "persist_portrait failed during rebake "
                    "teammate=%s avatar=%s err=%s — falling "
                    "back to JWT-signed URL",
                    teammate.pk, avatar.avatar_id, exc,
                )

        # §19 Step 4.d — canonical write for the three mirrors
        # (portrait / voice / realtime) as one authoring event. Voice
        # is landed here rather than pre-bake so a failed bake does
        # not overwrite canonical voice state.
        author = (
            request.user
            if getattr(request, "user", None) and request.user.is_authenticated
            else None
        )
        try:
            identity_services.record_prequalification_representation(
                teammate,
                source_call=PrequalificationSourceCall.WIZARD_REBAKE,
                author=author,
                portrait=_portrait_representation_from_avatar_result(
                    portrait_url, avatar,
                ),
                voice=_voice_representation_from_preset(
                    voice_preset, mock_mode=avatar.mock_mode,
                ),
                realtime=_realtime_representation_from_avatar_result(avatar),
            )
        except identity_services.BundleApprovalError:
            logger.exception(
                "rebake_avatar canonical write failed teammate=%s "
                "avatar=%s",
                teammate.pk, avatar.avatar_id,
            )
            teammate.runway_avatar_status = "failed"
            teammate.save(update_fields=["runway_avatar_status", "updated_at"])
            return Response(
                {"detail": "canonical persistence failed"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        # Non-mirror fields: refresh to pick up sync's mirror writes,
        # then persist runway_avatar_status + status.
        teammate.refresh_from_db()
        teammate.runway_avatar_status = avatar.status
        if avatar.ok:
            teammate.status = Teammate.Status.READY
        teammate.save(
            update_fields=[
                "runway_avatar_status",
                "status",
                "updated_at",
            ],
        )
        return Response(
            TeammateSerializer(
                teammate, context={"request": request},
            ).data
        )

    @action(detail=True, methods=["post"], url_path="ask")
    def ask(self, request, pk=None):
        """``POST /api/spokespeople/{id}/ask/``.

        Chapter 6 slice-1 (SESSION 234) — Beat 2 Ask + receipt.
        The operator types a question under the teammate's portrait;
        the teammate answers in-voice grounded in the workspace
        knowledge; the SPA renders the first-class receipt
        naming the docs consulted.

        Design lock: ``docs/design/CUSTOMER_JOURNEY_V1.md``
        §"Chapter 6 — Ongoing training", Beat 2. Ship bar: no
        fabricated citations. When retrieval returns nothing the
        response signals honest-fallback with an empty
        ``citations`` list.

        Body::

            {"question": "What do we sell?"}

        Response::

            {
              "answer": "...",
              "citations": [
                {"document_id": "...", "title": "...", "chunk_count": 3}
              ],
              "used_knowledge": true,
              "model": "gpt-5"
            }

        Errors:
            400 — blank / missing ``question``.
            404 — cross-workspace teammate (queryset filter).
        """
        from character_os.teammate_ask import ask_teammate

        teammate: Teammate = self.get_object()
        question = (request.data.get("question") or "").strip()
        if not question:
            return Response(
                {"error": "question is required", "code": "missing_question"},
                status=drf_status.HTTP_400_BAD_REQUEST,
            )

        result = ask_teammate(teammate, question)
        logger.info(
            "teammate_ask tm=%s used_knowledge=%s citations=%d",
            teammate.pk,
            result.used_knowledge,
            len(result.citations),
        )
        return Response(
            {
                "answer": result.answer,
                "citations": [
                    {
                        "document_id": c.document_id,
                        "title": c.title,
                        "chunk_count": c.chunk_count,
                    }
                    for c in result.citations
                ],
                "used_knowledge": result.used_knowledge,
                "model": result.model,
            }
        )

    @action(detail=True, methods=["post"], url_path="refresh-portrait")
    def refresh_portrait(self, request, pk=None):
        """``POST /api/spokespeople/{id}/refresh-portrait/``.

        SESSION 169 follow-up. Runway's CloudFront thumbnail URLs are
        JWT-signed with ~30-day expiry — after that the SPA's
        ``<img src=portrait_path>`` 401s. This action re-fetches a
        fresh signed URL from Runway via the media-engine and
        persists it onto ``Teammate.portrait_path``.

        No-op when:
        * The teammate has no ``runway_avatar_id`` set (nothing
          to refresh) — returns the current row unchanged.
        * Media-engine is in mock mode — returns the row unchanged.
        * Media-engine / Runway returns no fresh URL (network /
          non-2xx) — returns the row unchanged + 200.

        Response: the serialized teammate (so the SPA can
        replace its cache without a separate GET).
        """
        teammate: Teammate = self.get_object()
        if not teammate.runway_avatar_id:
            return Response(
                TeammateSerializer(
                    teammate, context={"request": request},
                ).data
            )
        try:
            with MediaEngineClient() as client:
                fresh = client.refresh_avatar_thumbnail(
                    avatar_id=teammate.runway_avatar_id,
                )
        except MediaEngineError as exc:
            logger.warning(
                "refresh_portrait media-engine error teammate=%s err=%s",
                teammate.pk, exc,
            )
            return Response(
                TeammateSerializer(
                    teammate, context={"request": request},
                ).data
            )
        if fresh:
            # §19 Step 4.d — canonical write. Under §5.4 a refreshed
            # URL is a change to the approved reference view set and
            # requires a new version. Amendment 4 versioning
            # consequences accept this noise; §5.5 keeps prior work
            # anchored to the version that produced it.
            #
            # Refresh operates on **existing** canonical state — it is
            # a URL freshness update, not an original authoring event.
            # If the teammate has no CharacterIdentity yet, the correct
            # remediation is running
            # ``python manage.py backfill_identity_substrate``. Silently
            # manufacturing canonical state from a URL refresh would
            # violate §5.4 semantics and undermine the operational
            # signal that a teammate needs backfilling.
            if not teammate.character_identities.exists():
                logger.warning(
                    "refresh_portrait refused teammate=%s — no canonical"
                    " identity yet; Step 3 backfill required",
                    teammate.pk,
                )
                return Response(
                    {
                        "error": (
                            "This teammate has not been imported into "
                            "the canonical identity substrate. Run "
                            "``python manage.py "
                            "backfill_identity_substrate`` and retry."
                        ),
                        "code": "canonical_identity_required",
                    },
                    status=drf_status.HTTP_409_CONFLICT,
                )

            author = (
                request.user
                if getattr(request, "user", None)
                and request.user.is_authenticated
                else None
            )
            try:
                identity_services.record_prequalification_representation(
                    teammate,
                    source_call=PrequalificationSourceCall.REFRESH_PORTRAIT,
                    author=author,
                    portrait=PortraitRepresentation(
                        portrait_uri=fresh,
                        provider=GenerationProvider.RUNWAY_AVATAR,
                        provider_model="",
                        execution_mode=ExecutionMode.REAL_REQUIRED,
                        execution_mode_actual=ExecutionModeActual.REAL,
                        mock_mode=False,
                        provider_response={"refreshed_thumbnail_url": fresh},
                    ),
                )
            except identity_services.BundleApprovalError:
                # Defensive: identity exists (checked above) and we
                # supplied a portrait, so bundle approval should have
                # succeeded. If it did not, log as exception and
                # surface a stable domain response — this is not a
                # provider failure.
                logger.exception(
                    "refresh_portrait canonical write failed teammate=%s"
                    " — unexpected substrate state",
                    teammate.pk,
                )
                return Response(
                    {
                        "error": (
                            "Canonical write failed unexpectedly. "
                            "The teammate may be in a partial substrate "
                            "state; contact operations."
                        ),
                        "code": "canonical_identity_required",
                    },
                    status=drf_status.HTTP_409_CONFLICT,
                )
            teammate.refresh_from_db()
        return Response(
            TeammateSerializer(
                teammate, context={"request": request},
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

        Static data — no DB, no Teammate row. Content is
        operator-collaborative starter material defined in
        ``character_os/templates/teammate_templates.py``.

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
        tab of the teammate voice-capture UI. Hard-coded here +
        mirrored from the media-engine's
        ``SUPPORTED_VOICE_PRESETS`` (cross-service imports are
        forbidden by CLAUDE.md).

        SESSION 230 — Chapter 2 Beat 3 voice sampling: shape now
        ``{"presets": [{"name": "adam", "sample_url": "/voice-samples/adam.mp3"}, ...]}``.
        ``sample_url`` points to a static file served by the SPA
        (``web/public/voice-samples/{name}.mp3``).

        SESSION 231 slice 1b — ``sample_url`` is now driven by disk
        truth. Presets whose MP3 has not been baked yet return
        ``sample_url: null``, which the SPA renders as
        "Sample coming soon" instead of a broken ``<audio>``.
        The bake tool is ``python manage.py bake_voice_samples
        --commit`` (from ``shell/``).
        """
        samples_dir = _voice_samples_dir()
        payload = [
            {
                "name": name,
                "sample_url": (
                    f"/voice-samples/{name}.mp3"
                    if (samples_dir / f"{name}.mp3").is_file()
                    else None
                ),
            }
            for name in sorted(SUPPORTED_VOICE_PRESETS)
        ]
        return Response({"presets": payload})

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
        Teammate row created here; the wizard accumulates
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
