"""Internal API surface consumed by the Django shell.

The architectural boundary defined in
``docs/design/MEDIA_ENGINE_INTERNAL_API.md`` — pure JSON in/out,
stateless across calls, no CharacterStore touch. The Django shell is
the only system of record for spokespeople / videos / threads; this
module is a thin façade over the existing media-engine services so
those services keep working for the legacy ``/api/*`` surface during
the Phase 2 transition.

SESSION 108 — ``POST /internal/avatars/`` (avatar create).
SESSION 109 — ``POST /internal/videos/`` + ``GET /internal/videos/{task_id}/``
(fire-then-poll video generation).
SESSION 110 — ``POST /internal/voices/`` (inline voice clone).
SESSION 125 — ``POST /internal/portrait/`` (Runway-generated portraits
via gen4_image; wizard slice 2 of the create-spokesperson scope).
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import re
from pathlib import Path
from typing import Literal, Optional

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import Settings, get_settings
from ..models import RunwayGenerateRequest
from ..services.character_host_client import SUPPORTED_VOICE_PRESETS
from ..services.character_studio_client import (
    CharacterStudioError,
    PORTRAIT_TEMPLATES,
    _atomic_write_bytes,
    _create_avatar_real,
    _generate_portrait_real,
    _mock_color_for,
    _solid_png,
    build_prompt,
)
from ..services.runway_client import (
    GenerationSettingsError,
    create_task as runway_create_task,
    get_task as runway_get_task,
    resolve_model,
    validate_generation_settings,
)
from ..services.voice_clone_client import (
    MAX_AUDIO_BYTES,
    SUPPORTED_AUDIO_MIMES,
    clone_voice_from_audio,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/internal", tags=["internal"])


_DATA_URI_RE = re.compile(r"^data:(image/(?:png|jpe?g|webp));base64,(.+)$", re.IGNORECASE)
_MAX_DECODED_PORTRAIT_BYTES = 5 * 1024 * 1024  # 5 MB cap matches contract doc
_MIME_EXT = {
    "image/png": "png",
    "image/jpeg": "jpg",
    "image/jpg": "jpg",
    "image/webp": "webp",
}

# Audio data URI parser. Wider mime set than portraits — see
# voice_clone_client.SUPPORTED_AUDIO_MIMES for the allowlist.
_AUDIO_DATA_URI_RE = re.compile(
    r"^data:(audio/[a-zA-Z0-9.+\-]+);base64,(.+)$", re.IGNORECASE,
)


class InternalAvatarCreate(BaseModel):
    """Request body for ``POST /internal/avatars/`` — see
    ``docs/design/MEDIA_ENGINE_INTERNAL_API.md``."""

    name: str = Field(..., min_length=1, max_length=80)
    portrait_data_uri: str = Field(..., min_length=32)
    voice_preset: Optional[str] = Field(default=None)
    personality: Optional[str] = Field(default=None, max_length=600)


class InternalAvatarResponse(BaseModel):
    avatar_id: str
    status: str  # "ready" | "mock" | "failed"
    thumbnail_url: Optional[str] = None
    mock_mode: bool


def _error(status_code: int, code: str, message: str) -> JSONResponse:
    """Normalise to the contract error shape — ``{error, code}``."""
    return JSONResponse(
        status_code=status_code,
        content={"error": message, "code": code},
    )


def _decode_portrait(data_uri: str) -> tuple[str, bytes] | JSONResponse:
    """Validate + decode a ``data:image/...;base64,...`` portrait.

    Returns ``(mime, raw_bytes)`` on success or a JSONResponse error.
    The bytes cap matches the contract (5 MB decoded).
    """
    match = _DATA_URI_RE.match(data_uri.strip())
    if not match:
        return _error(
            400,
            "invalid_data_uri",
            "portrait_data_uri must be data:image/{png|jpeg|webp};base64,...",
        )
    mime = match.group(1).lower().replace("jpg", "jpeg")
    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except (ValueError, binascii.Error):
        return _error(400, "invalid_data_uri", "portrait_data_uri base64 payload is malformed")
    if not raw:
        return _error(400, "invalid_data_uri", "portrait_data_uri decoded to zero bytes")
    if len(raw) > _MAX_DECODED_PORTRAIT_BYTES:
        return _error(
            413,
            "portrait_too_large",
            f"portrait decodes to {len(raw):,} bytes; cap is {_MAX_DECODED_PORTRAIT_BYTES:,}",
        )
    return mime, raw


def _write_portrait_temp(settings: Settings, mime: str, raw: bytes) -> Path:
    """Cache the decoded portrait under ``data/_internal/avatars/`` so
    downstream code that expects a file path has one. The directory is
    gitignored via the existing ``media-engine/data/`` rule. Filename
    derives from a content-addressed hash so duplicate posts share a
    file."""
    target_dir = settings.data_path / "_internal" / "avatars"
    target_dir.mkdir(parents=True, exist_ok=True)
    digest = hashlib.sha256(raw).hexdigest()[:16]
    ext = _MIME_EXT.get(mime, "png")
    path = target_dir / f"{digest}.{ext}"
    if not path.exists():
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(raw)
        tmp.replace(path)
    return path


@router.post("/avatars/", response_model=InternalAvatarResponse)
def post_internal_avatar(
    body: InternalAvatarCreate,
    settings: Settings = Depends(get_settings),
):
    """Create a Runway avatar from an inline portrait + voice preset.

    Stateless — no CharacterStore touch, no spokesperson record kept.
    The decoded portrait is cached under ``data/_internal/avatars/``
    so re-posts with the same image are cheap, but the cache is
    informational only (Django is the system of record).
    """
    decoded = _decode_portrait(body.portrait_data_uri)
    if isinstance(decoded, JSONResponse):
        return decoded
    mime, raw = decoded

    voice = (body.voice_preset or "vincent").strip().lower()
    if voice not in SUPPORTED_VOICE_PRESETS:
        return _error(
            400,
            "unsupported_voice",
            f"voice_preset {body.voice_preset!r} not in {sorted(SUPPORTED_VOICE_PRESETS)}",
        )

    # Cached for diagnostics / re-use; not load-bearing on the response.
    _write_portrait_temp(settings, mime, raw)

    if settings.runway_mock:
        # Deterministic mock id keyed on inputs so repeated calls in the
        # smoke test (same name + same portrait bytes) produce the same
        # avatar_id. Contract says mock ids are prefixed `mock_`.
        digest = hashlib.sha256(body.name.encode("utf-8") + raw).hexdigest()[:12]
        avatar_id = f"mock_avatar_{digest}"
        thumb_uri = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
        logger.info(
            "internal avatar mock created name=%s avatar=%s portrait_bytes=%d",
            body.name, avatar_id, len(raw),
        )
        return InternalAvatarResponse(
            avatar_id=avatar_id,
            status="mock",
            thumbnail_url=thumb_uri,
            mock_mode=True,
        )

    try:
        portrait_data_uri = f"data:{mime};base64," + base64.b64encode(raw).decode("ascii")
        avatar_id, thumb_url = _create_avatar_real(
            name=f"Character OS — {body.name[:60]}",
            portrait_data_uri=portrait_data_uri,
            voice_preset=voice,
            personality=body.personality,
            settings=settings,
            custom_voice_id=None,
        )
    except CharacterStudioError as exc:
        logger.warning("internal avatar failed name=%s: %s", body.name, exc)
        return _error(502, "upstream_runway_error", str(exc)[:300])
    except httpx.HTTPError as exc:
        logger.warning("internal avatar http error name=%s: %s", body.name, exc)
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("internal avatar unexpected name=%s", body.name)
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    logger.info(
        "internal avatar ready name=%s avatar=%s portrait_bytes=%d",
        body.name, avatar_id, len(raw),
    )
    return InternalAvatarResponse(
        avatar_id=avatar_id,
        status="ready",
        thumbnail_url=thumb_url,
        mock_mode=False,
    )


# ---- POST /internal/videos/ + poll --------------------------------
#
# Fire-then-poll. The create endpoint wraps the existing
# ``runway_client.create_task`` so Runway-side behaviour matches the
# legacy ``/api/runway/generate`` route. SESSION 109 ships
# ``kind="spokesperson_ad"`` only — other kinds 400 until landed.

# Map our Django-side status vocabulary to Runway's task statuses.
# Contract uses lowercase; Runway uses uppercase.
_RUNWAY_TO_CONTRACT_STATUS = {
    "PENDING": "pending",
    "RUNNING": "rendering",
    "SUCCEEDED": "ready",
    "FAILED": "failed",
    "CANCELED": "failed",
}

# Supported video kinds. SESSION 109 ships one; others enumerated so
# the 400 message can list them.
_SUPPORTED_KINDS = {"spokesperson_ad"}
_PLANNED_KINDS = {"cinematic_video", "dialogue_scene", "long_ad"}

VideoKind = Literal[
    "spokesperson_ad", "cinematic_video", "dialogue_scene", "long_ad"
]


class InternalVideoCreate(BaseModel):
    """Request body for ``POST /internal/videos/``."""

    kind: VideoKind
    spokesperson_avatar_id: str = Field(..., min_length=4, max_length=120)
    brief: str = Field(..., min_length=4, max_length=2000)
    ratio: str = Field(default="1280:720")
    duration: int = Field(default=5, ge=5, le=10)
    prompt_image: Optional[str] = Field(default=None, max_length=2048)


class InternalVideoCreateResponse(BaseModel):
    task_id: str
    status: str  # "pending" | "rendering"
    kind: VideoKind
    mock_mode: bool


class InternalVideoPollResponse(BaseModel):
    task_id: str
    status: str  # "pending" | "rendering" | "ready" | "failed"
    progress: Optional[float] = None
    output_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    failure_code: Optional[str] = None
    mock_mode: bool


@router.post("/videos/", response_model=InternalVideoCreateResponse)
def post_internal_video(
    body: InternalVideoCreate,
    settings: Settings = Depends(get_settings),
):
    """Fire a video render. Returns immediately with the Runway task
    id; the caller polls ``GET /internal/videos/{task_id}/`` for
    terminal state.
    """
    if body.kind not in _SUPPORTED_KINDS:
        msg = (
            f"kind {body.kind!r} not yet supported. "
            f"shipped: {sorted(_SUPPORTED_KINDS)}; "
            f"planned: {sorted(_PLANNED_KINDS)}"
        )
        return _error(400, "unsupported_kind", msg)

    # For spokesperson_ad we use the avatar-derived video pipeline.
    # SESSION 109 takes the simplest path: route through the existing
    # ``runway_client.create_task`` (gen4.5 text→video, or
    # image-to-video when ``prompt_image`` is supplied). The
    # avatar id rides on the task metadata for traceability but
    # doesn't directly drive Runway today — the legacy
    # character_performance pipeline is the eventual upgrade path.
    model = resolve_model(None, settings)
    has_image = bool(body.prompt_image and body.prompt_image.strip())
    try:
        validate_generation_settings(
            model=model,
            ratio=body.ratio,
            duration=body.duration,
            has_image=has_image,
            enforce_image_required=not settings.runway_mock,
        )
    except GenerationSettingsError as exc:
        return _error(400, "invalid_settings", str(exc))

    req = RunwayGenerateRequest(
        prompt_text=body.brief,
        prompt_image=body.prompt_image,
        ratio=body.ratio,
        duration=body.duration,
        model=model,
    )

    try:
        runway_resp = runway_create_task(req, settings)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "internal video create runway error %s: %s",
            exc.response.status_code, exc.response.text[:300],
        )
        return _error(
            502, "upstream_runway_error",
            f"runway returned {exc.response.status_code}",
        )
    except httpx.HTTPError as exc:
        logger.warning("internal video create http error: %s", exc)
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("internal video create unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    contract_status = _RUNWAY_TO_CONTRACT_STATUS.get(runway_resp.status, "pending")
    logger.info(
        "internal video task created kind=%s avatar=%s task=%s status=%s mock=%s",
        body.kind, body.spokesperson_avatar_id, runway_resp.task_id,
        contract_status, runway_resp.mock_mode,
    )
    return InternalVideoCreateResponse(
        task_id=runway_resp.task_id,
        status=contract_status,
        kind=body.kind,
        mock_mode=runway_resp.mock_mode,
    )


@router.get(
    "/videos/{task_id}/", response_model=InternalVideoPollResponse,
)
def get_internal_video(
    task_id: str,
    settings: Settings = Depends(get_settings),
):
    """Poll a video task. Idempotent and cheap; safe to call on a
    tight loop from the Celery worker. Terminal states (`ready`,
    `failed`) never transition further.
    """
    try:
        runway_resp = runway_get_task(task_id, settings)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "internal video poll runway error task=%s status=%s body=%s",
            task_id, exc.response.status_code, exc.response.text[:200],
        )
        return _error(
            502, "upstream_runway_error",
            f"runway returned {exc.response.status_code}",
        )
    except httpx.HTTPError as exc:
        logger.warning("internal video poll http error task=%s: %s", task_id, exc)
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("internal video poll unexpected task=%s", task_id)
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    contract_status = _RUNWAY_TO_CONTRACT_STATUS.get(runway_resp.status, "pending")
    output_url = runway_resp.output[0] if runway_resp.output else None
    return InternalVideoPollResponse(
        task_id=task_id,
        status=contract_status,
        progress=runway_resp.progress if contract_status != "ready" else 1.0,
        output_url=output_url,
        # Runway response doesn't include duration directly; the
        # Django side fills it from the request when status=ready.
        # Surfacing None here keeps the contract honest.
        duration_seconds=None,
        error=runway_resp.failure_reason if contract_status == "failed" else None,
        failure_code=None,  # Runway exposes this only on character_performance
        mock_mode=runway_resp.mock_mode,
    )


# ---- POST /internal/clips/avatar_speech/ + generalised poll -------
#
# SESSION 143 / V3. Talking-head video generation via Runway's
# ``/v1/avatar_videos`` endpoint (model: ``gwm1_avatars``). Unlike
# ``/internal/videos/`` (which routes through ``gen4_turbo`` for
# silent visual animation), this endpoint generates speech +
# lip-sync from a text script and the avatar's bound voice preset.
#
# Closes the K6.5 audit finding: cast members will render
# *speaking* their synthesized scripts, not as silent animated
# portraits. The shape mirrors the legacy ``_generate_real`` flow
# in ``character_host_client.py`` but accepts the avatar id from
# the request body rather than a Campaign lookup, matching the
# stateless ``/internal/*`` contract.
#
# Returns immediately with the Runway task id. Caller polls
# ``GET /internal/tasks/{task_id}/`` (the generalised poll route)
# for terminal state. Same Runway task ID space as
# ``/internal/videos/`` — the poll logic is identical.
#
# v1 ignores ``ratio`` / ``duration`` on the request — Runway's
# avatar_videos endpoint controls those server-side based on the
# script length and the avatar's bound aspect ratio. The fields
# are accepted for forwards-compat with the V0 contract shape.

_AVATAR_VIDEO_MODEL = "gwm1_avatars"
_AVATAR_SPEECH_MAX_SCRIPT_CHARS = 2000  # matches /internal/videos/'s brief cap


class InternalAvatarSpeechCreate(BaseModel):
    """Request body for ``POST /internal/clips/avatar_speech/``."""

    spokesperson_avatar_id: str = Field(..., min_length=4, max_length=120)
    script: str = Field(..., min_length=1, max_length=_AVATAR_SPEECH_MAX_SCRIPT_CHARS)
    # Forwards-compat — accepted but not used in v1; Runway controls
    # these for avatar_videos.
    ratio: Optional[str] = Field(default=None, max_length=20)
    duration: Optional[int] = Field(default=None, ge=1, le=120)


class InternalAvatarSpeechCreateResponse(BaseModel):
    task_id: str
    status: str  # "pending" | "rendering"
    kind: Literal["avatar_speech"] = "avatar_speech"
    mock_mode: bool


class InternalTaskPollResponse(BaseModel):
    """Generalised poll response. Identical shape to the legacy
    ``InternalVideoPollResponse`` — same Runway task ID space, so
    both async primitive surfaces share one poll contract."""

    task_id: str
    status: str  # "pending" | "rendering" | "ready" | "failed"
    progress: Optional[float] = None
    output_url: Optional[str] = None
    duration_seconds: Optional[float] = None
    error: Optional[str] = None
    failure_code: Optional[str] = None
    mock_mode: bool


@router.post(
    "/clips/avatar_speech/",
    response_model=InternalAvatarSpeechCreateResponse,
)
def post_internal_avatar_speech(
    body: InternalAvatarSpeechCreate,
    settings: Settings = Depends(get_settings),
):
    """Fire a talking-head render. Returns immediately with a
    Runway task id; the caller polls ``GET /internal/tasks/{task_id}/``
    for terminal state.

    Stateless — no Campaign / CharacterStore touch. The avatar id
    is treated as opaque (the Django shell guarantees it's a real
    Runway avatar_id from a prior ``POST /internal/avatars/`` call).
    """
    avatar_id = body.spokesperson_avatar_id.strip()
    script = body.script.strip()
    if not script:
        return _error(422, "validation_error", "script must be non-empty")

    if settings.runway_mock:
        # Deterministic mock task id keyed on avatar + script so
        # repeated calls in the smoke test produce the same task_id.
        # Prefix matches the convention from /internal/avatars/.
        digest = hashlib.sha256(
            (avatar_id + script).encode("utf-8")
        ).hexdigest()[:16]
        task_id = f"mock_task_{digest}"
        logger.info(
            "internal avatar_speech mock task=%s avatar=%s script_chars=%d",
            task_id, avatar_id, len(script),
        )
        return InternalAvatarSpeechCreateResponse(
            task_id=task_id,
            status="pending",
            mock_mode=True,
        )

    body_payload = {
        "model": _AVATAR_VIDEO_MODEL,
        "avatar": {"type": "custom", "avatarId": avatar_id},
        "speech": {"type": "text", "text": script},
    }
    url = f"{settings.runway_api_base}/v1/avatar_videos"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(url, headers=_runway_headers(settings), json=body_payload)
        if resp.status_code != 200:
            logger.warning(
                "internal avatar_speech runway %s: %s",
                resp.status_code, resp.text[:300],
            )
            return _error(
                502, "upstream_runway_error",
                f"runway returned {resp.status_code}",
            )
        created = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("internal avatar_speech http error: %s", exc)
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("internal avatar_speech unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    task_id = created.get("id")
    if not task_id:
        logger.warning("internal avatar_speech missing task id: %s", created)
        return _error(
            502, "upstream_runway_error",
            "runway response missing task id",
        )

    logger.info(
        "internal avatar_speech task created avatar=%s task=%s script_chars=%d",
        avatar_id, task_id, len(script),
    )
    return InternalAvatarSpeechCreateResponse(
        task_id=task_id,
        status="pending",
        mock_mode=False,
    )


def _runway_headers(settings: Settings) -> dict[str, str]:
    """Local copy of the same helper in character_host_client.py.
    Inlined here so the internal router doesn't need to reach into
    a campaign-aware service module."""
    return {
        "Authorization": f"Bearer {settings.runway_api_key}",
        "X-Runway-Version": settings.runway_api_version,
        "Content-Type": "application/json",
    }


def _poll_runway_task(
    task_id: str,
    settings: Settings,
) -> InternalTaskPollResponse | JSONResponse:
    """Shared polling logic for ``GET /internal/tasks/{task_id}/``
    and the legacy ``GET /internal/videos/{task_id}/``. Both routes
    hit the same Runway task ID space."""
    try:
        runway_resp = runway_get_task(task_id, settings)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "internal task poll runway error task=%s status=%s body=%s",
            task_id, exc.response.status_code, exc.response.text[:200],
        )
        return _error(
            502, "upstream_runway_error",
            f"runway returned {exc.response.status_code}",
        )
    except httpx.HTTPError as exc:
        logger.warning("internal task poll http error task=%s: %s", task_id, exc)
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("internal task poll unexpected task=%s", task_id)
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    contract_status = _RUNWAY_TO_CONTRACT_STATUS.get(runway_resp.status, "pending")
    output_url = runway_resp.output[0] if runway_resp.output else None
    return InternalTaskPollResponse(
        task_id=task_id,
        status=contract_status,
        progress=runway_resp.progress if contract_status != "ready" else 1.0,
        output_url=output_url,
        duration_seconds=None,
        error=runway_resp.failure_reason if contract_status == "failed" else None,
        failure_code=None,
        mock_mode=runway_resp.mock_mode,
    )


@router.get(
    "/tasks/{task_id}/", response_model=InternalTaskPollResponse,
)
def get_internal_task(
    task_id: str,
    settings: Settings = Depends(get_settings),
):
    """Generalised task poll — same shape as ``/internal/videos/{task_id}/``.
    Used by every async primitive (avatar_speech, visual_clip,
    style_remix, transcribe) in the V0+ composition arc."""
    return _poll_runway_task(task_id, settings)


# ---- POST /internal/clips/visual/ ---------------------------------
#
# SESSION 143 / V4. Silent visual clip generation via Runway's
# ``/v1/image_to_video`` (``gen4_turbo``) or ``/v1/text_to_video``
# (``gen4.5``) — the same underlying call ``/internal/videos/``
# makes today, but exposed as a V0-aligned primitive endpoint
# without the legacy ``kind`` discriminator + avatar_id baggage.
#
# Same Runway task ID space as ``/internal/clips/avatar_speech/`` —
# both poll through ``GET /internal/tasks/{task_id}/``. The legacy
# ``/internal/videos/`` stays in place until V6 retires it.


class InternalVisualClipCreate(BaseModel):
    """Request body for ``POST /internal/clips/visual/``."""

    prompt: str = Field(..., min_length=1, max_length=2000)
    ratio: str = Field(default="1280:720")
    duration: int = Field(default=5, ge=5, le=10)
    prompt_image: Optional[str] = Field(default=None, max_length=2048)


class InternalVisualClipCreateResponse(BaseModel):
    task_id: str
    status: str  # "pending" | "rendering"
    kind: Literal["visual_clip"] = "visual_clip"
    mock_mode: bool


@router.post(
    "/clips/visual/", response_model=InternalVisualClipCreateResponse,
)
def post_internal_visual_clip(
    body: InternalVisualClipCreate,
    settings: Settings = Depends(get_settings),
):
    """Fire a silent visual clip render. Returns immediately with
    a Runway task id; caller polls
    ``GET /internal/tasks/{task_id}/`` for terminal state.

    Model resolution mirrors ``/internal/videos/``: ``gen4_turbo``
    when ``prompt_image`` is supplied (image-to-video),
    ``gen4.5`` otherwise (text-to-video).

    Same validation as the legacy route — per-model ratio +
    duration enforcement via ``validate_generation_settings``.
    """
    model = resolve_model(None, settings)
    has_image = bool(body.prompt_image and body.prompt_image.strip())
    try:
        validate_generation_settings(
            model=model,
            ratio=body.ratio,
            duration=body.duration,
            has_image=has_image,
            enforce_image_required=not settings.runway_mock,
        )
    except GenerationSettingsError as exc:
        return _error(400, "invalid_settings", str(exc))

    req = RunwayGenerateRequest(
        prompt_text=body.prompt,
        prompt_image=body.prompt_image,
        ratio=body.ratio,
        duration=body.duration,
        model=model,
    )

    try:
        runway_resp = runway_create_task(req, settings)
    except httpx.HTTPStatusError as exc:
        logger.warning(
            "internal visual_clip runway error %s: %s",
            exc.response.status_code, exc.response.text[:300],
        )
        return _error(
            502, "upstream_runway_error",
            f"runway returned {exc.response.status_code}",
        )
    except httpx.HTTPError as exc:
        logger.warning("internal visual_clip http error: %s", exc)
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("internal visual_clip unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    contract_status = _RUNWAY_TO_CONTRACT_STATUS.get(runway_resp.status, "pending")
    logger.info(
        "internal visual_clip task created model=%s has_image=%s task=%s status=%s mock=%s",
        model, has_image, runway_resp.task_id, contract_status, runway_resp.mock_mode,
    )
    return InternalVisualClipCreateResponse(
        task_id=runway_resp.task_id,
        status=contract_status,
        mock_mode=runway_resp.mock_mode,
    )


# ---- POST /internal/voices/ ---------------------------------------
#
# Inline / synchronous voice cloning. Runway's clone returns in <10 s
# in real mode and a fraction of a second in mock mode, so there's no
# value in fire-then-poll for this endpoint. The Django side blocks
# on the response.
#
# The media-engine holds zero state across calls — the decoded audio
# is in memory only as long as the Runway upload takes.


class InternalVoiceCreate(BaseModel):
    """Request body for ``POST /internal/voices/``."""

    audio_data_uri: str = Field(..., min_length=32)
    name: Optional[str] = Field(default=None, max_length=80)


class InternalVoiceResponse(BaseModel):
    voice_id: str
    status: str  # "ready" | "mock" | "failed"
    preview_url: Optional[str] = None
    mock_mode: bool


def _decode_audio(data_uri: str) -> tuple[str, bytes] | JSONResponse:
    """Validate + decode a ``data:audio/...;base64,...`` payload.

    Returns ``(mime, raw_bytes)`` on success or a JSONResponse error.
    Mime is normalised to lowercase and validated against
    ``SUPPORTED_AUDIO_MIMES``. Decoded cap matches the legacy
    multipart route (``MAX_AUDIO_BYTES`` = 15 MB).
    """
    match = _AUDIO_DATA_URI_RE.match(data_uri.strip())
    if not match:
        return _error(
            400,
            "invalid_data_uri",
            "audio_data_uri must be data:audio/{mp3|wav|m4a|webm|ogg|aac};base64,...",
        )
    mime = match.group(1).lower()
    if mime not in SUPPORTED_AUDIO_MIMES:
        return _error(
            400,
            "invalid_data_uri",
            f"unsupported audio mime {mime!r}; accepted: {sorted(SUPPORTED_AUDIO_MIMES)}",
        )
    try:
        raw = base64.b64decode(match.group(2), validate=True)
    except (ValueError, binascii.Error):
        return _error(
            400, "invalid_data_uri",
            "audio_data_uri base64 payload is malformed",
        )
    if not raw:
        return _error(422, "empty_audio", "audio_data_uri decoded to zero bytes")
    if len(raw) > MAX_AUDIO_BYTES:
        return _error(
            413,
            "audio_too_large",
            f"audio decodes to {len(raw):,} bytes; cap is {MAX_AUDIO_BYTES:,}",
        )
    return mime, raw


@router.post("/voices/", response_model=InternalVoiceResponse)
def post_internal_voice(
    body: InternalVoiceCreate,
    settings: Settings = Depends(get_settings),
):
    """Clone a voice from an inline audio sample.

    Stateless — no local cache; the decoded audio is forwarded
    immediately to Runway (real mode) or hashed for the mock id
    (mock mode). Mock-mode ids are deterministic on
    ``sha256(name + audio_bytes)`` so re-uploads are idempotent.
    """
    decoded = _decode_audio(body.audio_data_uri)
    if isinstance(decoded, JSONResponse):
        return decoded
    mime, raw = decoded

    name = (body.name or "Custom Voice").strip() or "Custom Voice"
    result = clone_voice_from_audio(name, raw, mime, settings)

    if result.status == "failed" or not result.voice_id:
        logger.warning(
            "internal voice clone failed name=%s err=%s",
            name, result.error,
        )
        return _error(
            502, "upstream_runway_error",
            result.error or "voice clone failed",
        )

    logger.info(
        "internal voice clone ok name=%s voice=%s status=%s mock=%s",
        name, result.voice_id, result.status, result.mock_mode,
    )
    return InternalVoiceResponse(
        voice_id=result.voice_id,
        status=result.status,
        preview_url=result.preview_url,
        mock_mode=result.mock_mode,
    )


# ---- POST /internal/portrait/ -------------------------------------
#
# Synchronous Runway gen4_image portrait generation. SESSION 125 —
# wizard slice 2. Operator types a subject + picks a visual archetype
# (template); we hand the inherited build_prompt() the combo, call
# Runway, and return the result as a base64 data URI. Stateless: no
# CharacterStore touch, no spokesperson record kept.


class InternalPortraitCreate(BaseModel):
    """Request body for ``POST /internal/portrait/``."""

    template: str = Field(..., min_length=1, max_length=40)
    subject: Optional[str] = Field(default=None, max_length=300)
    style: Optional[str] = Field(default=None, max_length=300)


class InternalPortraitResponse(BaseModel):
    portrait_data_uri: str
    template: str
    prompt: str
    mock_mode: bool


@router.post("/portrait/", response_model=InternalPortraitResponse)
def post_internal_portrait(
    body: InternalPortraitCreate,
    settings: Settings = Depends(get_settings),
):
    """Generate a portrait via Runway gen4_image (or the deterministic
    mock placeholder when ``RUNWAY_API_KEY`` is unset).

    Mock-mode short-circuits to ``_solid_png()`` with a deterministic
    colour seeded from the composed prompt — same inputs always
    produce the same placeholder. Real-mode calls
    ``_generate_portrait_real()`` against Runway gen4_image.
    """
    template = body.template.strip().lower()
    if template not in PORTRAIT_TEMPLATES:
        return _error(
            400,
            "unsupported_template",
            f"template {body.template!r} not in {sorted(PORTRAIT_TEMPLATES)}",
        )

    # Compose the prompt via the inherited builder so the wizard's
    # portrait generation produces the same shape as the legacy
    # /api/characters/{id}/generate-portrait route.
    prompt = build_prompt(
        template=template,
        subject=body.subject,
        style=body.style,
    )

    # Cache the rendered portrait under data/_internal/portraits/
    # (gitignored). Filename is the sha256 of the prompt so repeated
    # calls with the same inputs hit the same file — useful for
    # idempotency + smoke-test determinism.
    digest = hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:20]
    target_dir = settings.data_path / "_internal" / "portraits"
    target_dir.mkdir(parents=True, exist_ok=True)
    target = target_dir / f"{digest}.png"

    if settings.runway_mock:
        try:
            payload = _solid_png(512, 512, _mock_color_for(prompt))
            _atomic_write_bytes(target, payload)
        except OSError as exc:
            return _error(500, "internal_error", f"mock write failed: {exc}"[:200])
        logger.info(
            "internal portrait mock template=%s subject=%r prompt_len=%d",
            template, body.subject, len(prompt),
        )
    else:
        try:
            _generate_portrait_real(prompt, target, settings)
        except CharacterStudioError as exc:
            logger.warning("internal portrait failed template=%s: %s", template, exc)
            return _error(502, "upstream_runway_error", str(exc)[:300])
        except httpx.HTTPError as exc:
            logger.warning("internal portrait http error: %s", exc)
            return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
        except Exception as exc:  # pragma: no cover — defensive
            logger.exception("internal portrait unexpected")
            return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])
        logger.info(
            "internal portrait ready template=%s subject=%r path=%s",
            template, body.subject, target.name,
        )

    # Read back as data URI. The cached file stays on disk for
    # diagnostics; Django is the system of record for what was
    # actually shown to the operator.
    try:
        portrait_bytes = target.read_bytes()
    except OSError as exc:
        return _error(500, "internal_error", f"read-back failed: {exc}"[:200])
    portrait_data_uri = "data:image/png;base64," + base64.b64encode(portrait_bytes).decode("ascii")

    return InternalPortraitResponse(
        portrait_data_uri=portrait_data_uri,
        template=template,
        prompt=prompt,
        mock_mode=settings.runway_mock,
    )
