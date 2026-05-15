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
import json
import logging
import os
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


# ---- POST /internal/clips/concat/ ---------------------------------
#
# SESSION 143 / V5. Synchronous ffmpeg concat — fires the long-form
# stitch the hackathon's ``long_ad_service.py`` was doing inline.
# Operators ship multi-minute talking-head ads via the
# ``long_form_ad`` starter: split_script → N× generate_avatar_speech →
# concat_clips. This endpoint is the third leg.
#
# Synchronous, not fire-then-poll: ffmpeg concat of ~10 clips takes
# 5-30 seconds wall-clock — well within HTTP keep-alive. The
# operation is CPU-bound + idempotent; no polling infrastructure
# needed. Matches the ``/internal/voices/`` shape (also synchronous).
#
# Mock-mode returns a deterministic stub URL keyed off the input
# URLs so tests stay hermetic.


class InternalConcatClipsCreate(BaseModel):
    """Request body for ``POST /internal/clips/concat/``."""

    clip_urls: list[str] = Field(..., min_length=1, max_length=64)
    # ``reencode=True`` runs filter_complex normalization so heterogeneous
    # inputs (e.g. clips from different Runway models) concat cleanly.
    # Default False uses the demuxer (-c copy) — fast, requires uniform
    # codec/dims/fps. V5's long-form path is uniform (all gwm1_avatars
    # output), so the default is safe.
    reencode: bool = Field(default=False)


class InternalConcatClipsResponse(BaseModel):
    output_url: str
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    mock_mode: bool


def _concat_clips_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "concats"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _download_concat_input(
    url: str,
    target_dir: Path,
    settings: Settings,
) -> Path:
    """Resolve a concat input URL to a local path. External
    ``http(s)://`` URLs are downloaded to ``target_dir``; already-
    local paths under ``settings.data_path`` are returned as-is."""
    target_dir.mkdir(parents=True, exist_ok=True)
    if url.startswith(("http://", "https://")):
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
        dest = target_dir / f"src-{digest}.mp4"
        if dest.exists():
            return dest
        tmp = dest.with_suffix(".mp4.tmp")
        with httpx.Client(timeout=60.0) as client:
            with client.stream("GET", url) as resp:
                resp.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in resp.iter_bytes(64 * 1024):
                        fh.write(chunk)
        tmp.replace(dest)
        return dest
    # Local path — strip optional leading ``/`` and resolve under
    # data_path. Operators driving the endpoint via shell pass
    # paths like ``/data/_internal/...`` (relative to
    # ``settings.data_path``); the host filesystem path is the
    # same prefix.
    candidate = Path(url)
    if not candidate.is_absolute():
        candidate = settings.data_path / url.lstrip("/")
    if not candidate.exists():
        raise FileNotFoundError(f"concat input not found: {url}")
    return candidate


@router.post(
    "/clips/concat/", response_model=InternalConcatClipsResponse,
)
def post_internal_concat_clips(
    body: InternalConcatClipsCreate,
    settings: Settings = Depends(get_settings),
):
    """Stitch N video clips into one MP4 via ffmpeg concat.

    Synchronous — operator's Celery worker blocks for the
    duration. Output is cached at
    ``data/_internal/concats/<hash>.mp4`` keyed off the input
    URL list so re-calls with the same inputs are idempotent.
    """
    clip_urls = [u.strip() for u in body.clip_urls if u and u.strip()]
    if not clip_urls:
        return _error(422, "validation_error", "clip_urls must contain at least one URL")

    # Deterministic cache key from input URLs + reencode flag.
    cache_seed = ("|".join(clip_urls) + f"|reencode={body.reencode}").encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/concats/mock-{cache_key}.mp4"
        logger.info(
            "internal concat_clips mock output=%s inputs=%d",
            output_url, len(clip_urls),
        )
        return InternalConcatClipsResponse(
            output_url=output_url,
            duration_seconds=float(len(clip_urls) * 5),
            size_bytes=1024 * 1024,
            mock_mode=True,
        )

    import shutil
    import subprocess

    if not shutil.which("ffmpeg"):
        return _error(
            500, "internal_error",
            "ffmpeg not found on PATH — install ffmpeg in the "
            "media-engine container",
        )

    target_dir = _concat_clips_dir(settings)
    output_path = target_dir / f"{cache_key}.mp4"
    if output_path.exists():
        return InternalConcatClipsResponse(
            output_url=f"/data/_internal/concats/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            mock_mode=False,
        )

    # Resolve every input to a local path (downloading externals).
    try:
        local_paths = [
            _download_concat_input(u, target_dir / "sources", settings)
            for u in clip_urls
        ]
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        logger.warning("concat_clips download failed: %s", exc)
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    tmp = output_path.with_suffix(".mp4.tmp")
    try:
        if body.reencode:
            cmd = _build_reencode_cmd(local_paths, tmp)
        else:
            # concat demuxer with -c copy. Fast, requires uniform inputs.
            filelist_path = target_dir / f"{cache_key}.txt"
            with filelist_path.open("w") as fh:
                for p in local_paths:
                    # ffmpeg concat-demuxer file lines must be POSIX-quoted.
                    fh.write(f"file '{p.as_posix()}'\n")
            cmd = [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat", "-safe", "0",
                "-i", str(filelist_path),
                "-c", "copy",
                "-movflags", "+faststart",
                "-f", "mp4",
                str(tmp),
            ]

        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=300,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-400:]
            tmp.unlink(missing_ok=True)
            logger.warning(
                "concat_clips ffmpeg rc=%s stderr=%s",
                result.returncode, stderr,
            )
            return _error(
                500, "internal_error",
                f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not tmp.exists():
            return _error(500, "internal_error", "ffmpeg produced no output file")
        tmp.replace(output_path)
    except subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", "ffmpeg concat timed out")
    except Exception as exc:  # pragma: no cover — defensive
        tmp.unlink(missing_ok=True)
        logger.exception("concat_clips unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    logger.info(
        "internal concat_clips done output=%s inputs=%d size=%d",
        output_path.name, len(clip_urls), output_path.stat().st_size,
    )
    return InternalConcatClipsResponse(
        output_url=f"/data/_internal/concats/{output_path.name}",
        duration_seconds=None,
        size_bytes=output_path.stat().st_size,
        mock_mode=False,
    )


def _build_reencode_cmd(local_paths: list[Path], tmp: Path) -> list[str]:
    """Build the filter_complex normalization cmd for
    heterogeneous inputs. Mirrors finisher_service's storyboard
    concat but preserves audio (concat=n=N:v=1:a=1)."""
    target_w, target_h, fps = 1280, 720, 30
    norm_filters = []
    concat_in = ""
    for idx in range(len(local_paths)):
        norm_filters.append(
            f"[{idx}:v]scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
            f"crop={target_w}:{target_h},setsar=1,fps={fps}[v{idx}]"
        )
        norm_filters.append(
            f"[{idx}:a]aresample=async=1[a{idx}]"
        )
        concat_in += f"[v{idx}][a{idx}]"
    filter_complex = (
        ";".join(norm_filters)
        + f";{concat_in}concat=n={len(local_paths)}:v=1:a=1[outv][outa]"
    )
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p in local_paths:
        cmd += ["-i", str(p)]
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-f", "mp4",
        str(tmp),
    ]
    return cmd


# ---- POST /internal/clips/composite/ + /internal/audio/mix/ ------
#
# SESSION 143 / V7. Composite primitives — the missing piece that
# unlocks every scene-composition starter (pip / backdrop / cohost /
# broll) + the music_bed mix path. Same synchronous shape as the V5
# concat endpoint; same cache-by-hash discipline.
#
# Layout kinds (composite_video):
#   * "pip"      — base + tile overlaid bottom-right with a white
#                  border. Audio = base.
#   * "backdrop" — bg cinematic clip + fg avatar tile overlaid
#                  top-right. Audio = foreground (avatar).
#   * "cohost"   — main + cohost overlay (top-left by default).
#                  Audio = main; cohost is video-only.
#   * "broll"    — base avatar with a single cinematic cutaway
#                  spliced into a window of the avatar timeline.
#                  Audio = base avatar (cutaway is video-only).
#
# Mix specs (mix_audio):
#   * music_gain_db (default -18): how much the music sits under
#     the base clip's voice track.
#   * fade_in_ms / fade_out_ms (default 1000/2000): smooth boundary.
#
# Each layout is a different filter_complex builder; the dispatch
# table at the bottom of this block keeps the handler small.


_COMPOSITE_KINDS = {"pip", "backdrop", "cohost", "broll"}

# Layout defaults — tunable per-layout without forcing operators
# to send all the knobs. Hackathon's empirical values for the
# corresponding clients.
_PIP_DEFAULT_WIDTH = 360
_PIP_DEFAULT_MARGIN = 40
_PIP_BORDER_PX = 6

_BACKDROP_DEFAULT_FG_WIDTH = 320
_BACKDROP_DEFAULT_MARGIN = 40
_BACKDROP_BORDER_PX = 6

_COHOST_DEFAULT_WIDTH = 240
_COHOST_DEFAULT_MARGIN = 40
_COHOST_BORDER_PX = 6


class InternalCompositeCreate(BaseModel):
    """Request body for ``POST /internal/clips/composite/``."""

    clip_urls: list[str] = Field(..., min_length=2, max_length=8)
    layout_spec: dict = Field(...)


class InternalCompositeResponse(BaseModel):
    output_url: str
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    mock_mode: bool


class InternalAudioMixCreate(BaseModel):
    """Request body for ``POST /internal/audio/mix/``."""

    base_clip_url: str = Field(..., min_length=1, max_length=2048)
    audio_urls: list[str] = Field(..., min_length=1, max_length=4)
    mix_spec: dict = Field(default_factory=dict)


class InternalAudioMixResponse(BaseModel):
    output_url: str
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    mock_mode: bool


def _composite_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "composites"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _build_pip_filter(options: dict) -> str:
    """filter_complex for `pip` layout — base at [0], tile at [1]."""
    pip_w = int(options.get("pip_width", _PIP_DEFAULT_WIDTH))
    margin_x = int(options.get("margin_x", _PIP_DEFAULT_MARGIN))
    margin_y = int(options.get("margin_y", _PIP_DEFAULT_MARGIN))
    border = int(options.get("border_px", _PIP_BORDER_PX))
    return (
        f"[1:v]scale={pip_w}:-2[pip_scaled];"
        f"[pip_scaled]pad=iw+{2 * border}:ih+{2 * border}:"
        f"{border}:{border}:color=white[pip_bordered];"
        f"[0:v][pip_bordered]overlay=W-w-{margin_x}:H-h-{margin_y}[outv]"
    )


def _build_backdrop_filter(options: dict) -> str:
    """filter_complex for `backdrop` — cinematic bg at [0],
    foreground avatar tile at [1]. Output sized to background's
    dims with the avatar tile overlaid top-right."""
    fg_w = int(options.get("fg_width", _BACKDROP_DEFAULT_FG_WIDTH))
    margin_x = int(options.get("margin_x", _BACKDROP_DEFAULT_MARGIN))
    margin_y = int(options.get("margin_y", _BACKDROP_DEFAULT_MARGIN))
    border = int(options.get("border_px", _BACKDROP_BORDER_PX))
    return (
        f"[0:v]setpts=PTS-STARTPTS[bg];"
        f"[1:v]scale={fg_w}:-2,setpts=PTS-STARTPTS[fg_scaled];"
        f"[fg_scaled]pad=iw+{2 * border}:ih+{2 * border}:"
        f"{border}:{border}:color=white[fg_bordered];"
        f"[bg][fg_bordered]overlay=W-w-{margin_x}:{margin_y}[outv]"
    )


def _build_cohost_filter(options: dict) -> str:
    """filter_complex for `cohost` — main at [0], cohost overlay
    at [1]. Cohost positioned top-left by default."""
    cohost_w = int(options.get("cohost_width", _COHOST_DEFAULT_WIDTH))
    margin_x = int(options.get("margin_x", _COHOST_DEFAULT_MARGIN))
    margin_y = int(options.get("margin_y", _COHOST_DEFAULT_MARGIN))
    border = int(options.get("border_px", _COHOST_BORDER_PX))
    return (
        f"[1:v]scale={cohost_w}:-2[cohost_scaled];"
        f"[cohost_scaled]pad=iw+{2 * border}:ih+{2 * border}:"
        f"{border}:{border}:color=white[cohost_bordered];"
        f"[0:v][cohost_bordered]overlay={margin_x}:{margin_y}[outv]"
    )


def _build_broll_filter(options: dict, base_dur: float) -> str:
    """filter_complex for `broll` — base at [0], cutaway at [1].
    Splices [start, end] of base with cutaway scaled to base
    dims. Audio stays from base (mapped via -map 0:a outside
    the filter)."""
    start = float(options.get("cutaway_start_s", base_dur * 0.3))
    end = float(options.get("cutaway_end_s", base_dur * 0.7))
    cut_dur = end - start
    if cut_dur <= 0 or start < 0 or end > base_dur:
        raise ValueError(
            f"broll cutaway window [{start:.2f}, {end:.2f}] must be inside "
            f"base [0, {base_dur:.2f}] with positive duration"
        )
    return (
        f"[0:v]trim=start=0:end={start:.3f},setpts=PTS-STARTPTS[v_pre];"
        f"[1:v]trim=start=0:end={cut_dur:.3f},setpts=PTS-STARTPTS,"
        f"scale=1280:720:force_original_aspect_ratio=increase,"
        f"crop=1280:720,setsar=1[v_cut];"
        f"[0:v]trim=start={end:.3f}:end={base_dur:.3f},"
        f"setpts=PTS-STARTPTS[v_post];"
        f"[v_pre][v_cut][v_post]concat=n=3:v=1:a=0[outv]"
    )


def _probe_duration(path: Path) -> float:
    """Use ffprobe to get a clip's duration in seconds. Falls
    back to 5.0 if probing fails."""
    import shutil
    import subprocess

    if not shutil.which("ffprobe"):
        return 5.0
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            capture_output=True, text=True, timeout=30,
        )
        return float(out.stdout.strip()) if out.returncode == 0 else 5.0
    except (ValueError, subprocess.TimeoutExpired, OSError):
        return 5.0


@router.post(
    "/clips/composite/", response_model=InternalCompositeResponse,
)
def post_internal_composite(
    body: InternalCompositeCreate,
    settings: Settings = Depends(get_settings),
):
    """Stitch N clips via ffmpeg filter_complex according to
    ``layout_spec.kind``. Synchronous; output cached by hash of
    inputs + spec."""
    layout = body.layout_spec or {}
    kind = (layout.get("kind") or "").strip()
    if kind not in _COMPOSITE_KINDS:
        return _error(
            400, "unsupported_layout",
            f"layout_spec.kind must be one of {sorted(_COMPOSITE_KINDS)}; "
            f"got {kind!r}",
        )

    clip_urls = [u.strip() for u in body.clip_urls if u and u.strip()]
    if len(clip_urls) < 2:
        return _error(
            422, "validation_error",
            "composite requires at least two clip_urls (base + overlay)",
        )

    options = layout.get("options") or {}
    cache_seed = (
        "|".join(clip_urls) + "|" + json.dumps({"kind": kind, "options": options}, sort_keys=True)
    ).encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/composites/mock-{cache_key}.mp4"
        logger.info(
            "internal composite mock kind=%s output=%s inputs=%d",
            kind, output_url, len(clip_urls),
        )
        return InternalCompositeResponse(
            output_url=output_url,
            duration_seconds=5.0,
            size_bytes=1024 * 1024,
            mock_mode=True,
        )

    import shutil as _shutil
    import subprocess as _subprocess

    if not _shutil.which("ffmpeg"):
        return _error(
            500, "internal_error",
            "ffmpeg not found on PATH — install ffmpeg in the "
            "media-engine container",
        )

    target_dir = _composite_dir(settings)
    output_path = target_dir / f"{kind}-{cache_key}.mp4"
    if output_path.exists():
        return InternalCompositeResponse(
            output_url=f"/data/_internal/composites/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            mock_mode=False,
        )

    try:
        local_paths = [
            _download_concat_input(u, target_dir / "sources", settings)
            for u in clip_urls
        ]
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        logger.warning("composite download failed: %s", exc)
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    # Dispatch to per-kind filter builder.
    try:
        if kind == "pip":
            filter_complex = _build_pip_filter(options)
            map_audio = ["-map", "0:a?"]
        elif kind == "backdrop":
            filter_complex = _build_backdrop_filter(options)
            # Audio from fg (avatar) — the bg is the silent cinematic.
            map_audio = ["-map", "1:a?"]
        elif kind == "cohost":
            filter_complex = _build_cohost_filter(options)
            map_audio = ["-map", "0:a?"]
        elif kind == "broll":
            base_dur = _probe_duration(local_paths[0])
            filter_complex = _build_broll_filter(options, base_dur)
            map_audio = ["-map", "0:a?"]
        else:  # pragma: no cover — guarded by _COMPOSITE_KINDS
            return _error(400, "unsupported_layout", f"unknown kind {kind!r}")
    except ValueError as exc:
        return _error(400, "validation_error", str(exc))

    tmp = output_path.with_suffix(".mp4.tmp")
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p in local_paths:
        cmd += ["-i", str(p)]
    cmd += [
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        *map_audio,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-f", "mp4",
        str(tmp),
    ]

    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-400:]
            tmp.unlink(missing_ok=True)
            logger.warning(
                "composite ffmpeg rc=%s stderr=%s", result.returncode, stderr,
            )
            return _error(
                500, "internal_error",
                f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not tmp.exists():
            return _error(500, "internal_error", "ffmpeg produced no output")
        tmp.replace(output_path)
    except _subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", "ffmpeg composite timed out")
    except Exception as exc:  # pragma: no cover — defensive
        tmp.unlink(missing_ok=True)
        logger.exception("composite unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    logger.info(
        "internal composite done kind=%s output=%s inputs=%d size=%d",
        kind, output_path.name, len(clip_urls), output_path.stat().st_size,
    )
    return InternalCompositeResponse(
        output_url=f"/data/_internal/composites/{output_path.name}",
        duration_seconds=None,
        size_bytes=output_path.stat().st_size,
        mock_mode=False,
    )


def _mixed_audio_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "mixes"
    target.mkdir(parents=True, exist_ok=True)
    return target


@router.post(
    "/audio/mix/", response_model=InternalAudioMixResponse,
)
def post_internal_audio_mix(
    body: InternalAudioMixCreate,
    settings: Settings = Depends(get_settings),
):
    """Mix N audio tracks under a base clip. v1 supports the
    ``music_bed`` pattern: one base clip + one audio track,
    music sits at ``mix_spec.music_gain_db`` (default -18 dB)
    under the base voice.

    Synchronous; output cached by hash of inputs + spec."""
    base = body.base_clip_url.strip()
    audio_urls = [u.strip() for u in body.audio_urls if u and u.strip()]
    if not base or not audio_urls:
        return _error(
            422, "validation_error",
            "audio mix requires a base_clip_url and at least one audio_url",
        )

    spec = body.mix_spec or {}
    music_gain_db = float(spec.get("music_gain_db", -18))
    fade_in_ms = int(spec.get("fade_in_ms", 1000))
    fade_out_ms = int(spec.get("fade_out_ms", 2000))

    cache_seed = (
        base + "|" + "|".join(audio_urls)
        + "|" + json.dumps(spec, sort_keys=True)
    ).encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/mixes/mock-{cache_key}.mp4"
        logger.info(
            "internal audio_mix mock output=%s tracks=%d gain=%.1fdB",
            output_url, len(audio_urls), music_gain_db,
        )
        return InternalAudioMixResponse(
            output_url=output_url,
            duration_seconds=5.0,
            size_bytes=1024 * 1024,
            mock_mode=True,
        )

    import shutil as _shutil
    import subprocess as _subprocess

    if not _shutil.which("ffmpeg"):
        return _error(
            500, "internal_error",
            "ffmpeg not found on PATH",
        )

    target_dir = _mixed_audio_dir(settings)
    output_path = target_dir / f"{cache_key}.mp4"
    if output_path.exists():
        return InternalAudioMixResponse(
            output_url=f"/data/_internal/mixes/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            mock_mode=False,
        )

    try:
        base_path = _download_concat_input(base, target_dir / "sources", settings)
        audio_paths = [
            _download_concat_input(u, target_dir / "sources", settings)
            for u in audio_urls
        ]
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        logger.warning("audio_mix download failed: %s", exc)
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    # v1: support one audio track (music bed). Multi-track is a
    # later capability; the API accepts a list for forward-compat.
    audio_path = audio_paths[0]

    fade_in_s = fade_in_ms / 1000.0
    fade_out_s = fade_out_ms / 1000.0
    # Filter graph: scale music to gain + fade in/out, then amix
    # with normalize=0 so the base voice keeps full volume.
    filter_complex = (
        f"[1:a]volume={music_gain_db}dB,"
        f"afade=t=in:st=0:d={fade_in_s:.2f},"
        f"afade=t=out:st=999999:d={fade_out_s:.2f}[bed];"
        f"[0:a][bed]amix=inputs=2:duration=first:normalize=0[outa]"
    )

    tmp = output_path.with_suffix(".mp4.tmp")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(base_path), "-i", str(audio_path),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[outa]",
        "-c:v", "copy",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-f", "mp4",
        str(tmp),
    ]

    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-400:]
            tmp.unlink(missing_ok=True)
            return _error(
                500, "internal_error",
                f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not tmp.exists():
            return _error(500, "internal_error", "ffmpeg produced no output")
        tmp.replace(output_path)
    except _subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", "ffmpeg audio mix timed out")
    except Exception as exc:  # pragma: no cover — defensive
        tmp.unlink(missing_ok=True)
        logger.exception("audio_mix unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    logger.info(
        "internal audio_mix done output=%s tracks=%d gain=%.1fdB size=%d",
        output_path.name, len(audio_urls), music_gain_db,
        output_path.stat().st_size,
    )
    return InternalAudioMixResponse(
        output_url=f"/data/_internal/mixes/{output_path.name}",
        duration_seconds=None,
        size_bytes=output_path.stat().st_size,
        mock_mode=False,
    )


# ---- V9 polish primitives -----------------------------------------
#
# SESSION 143 / V9. Four ffmpeg-only synchronous endpoints that
# polish + format existing clips:
#
#   POST /internal/clips/captions/    — burn-in subtitles from
#                                       operator-supplied caption
#                                       timing (SRT-based).
#   POST /internal/clips/intro_outro/ — prepend/append black title
#                                       cards via lavfi color +
#                                       drawtext.
#   POST /internal/clips/trim/        — stream-copy trim
#                                       (-ss / -to).
#   POST /internal/clips/reformat/    — scale + crop to a target
#                                       aspect ratio (e.g.,
#                                       1280:720 → 720:1280 for
#                                       Reels).
#
# All four follow the V5/V7 synchronous shape: cache by hash,
# mock-mode stub, ffmpeg subprocess with timeout. None of them
# call Runway; they're CPU-bound transformations of existing
# media files.


# ---- POST /internal/clips/captions/ -------------------------------


class CaptionRange(BaseModel):
    """One SRT subtitle entry."""

    start_s: float = Field(..., ge=0)
    end_s: float = Field(..., gt=0)
    text: str = Field(..., min_length=1, max_length=400)


class InternalCaptionsCreate(BaseModel):
    """Request body for ``POST /internal/clips/captions/``."""

    clip_url: str = Field(..., min_length=1, max_length=2048)
    captions: list[CaptionRange] = Field(..., min_length=1, max_length=200)


class InternalProcessedClipResponse(BaseModel):
    """Generic response shape — same as ConcatClipsResponse +
    CompositeResponse + AudioMixResponse. All four V9 endpoints
    return this shape."""

    output_url: str
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    mock_mode: bool


def _captions_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "captions"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _format_srt_timestamp(seconds: float) -> str:
    """SRT format: HH:MM:SS,mmm."""
    if seconds < 0:
        seconds = 0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis >= 1000:
        secs += 1
        millis -= 1000
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def _write_srt(captions: list, target: Path) -> None:
    """Write captions to an SRT file at ``target``."""
    lines: list[str] = []
    for i, entry in enumerate(captions, start=1):
        start = _format_srt_timestamp(entry.start_s)
        end = _format_srt_timestamp(entry.end_s)
        lines.append(str(i))
        lines.append(f"{start} --> {end}")
        lines.append(entry.text)
        lines.append("")
    target.write_text("\n".join(lines), encoding="utf-8")


@router.post(
    "/clips/captions/", response_model=InternalProcessedClipResponse,
)
def post_internal_captions(
    body: InternalCaptionsCreate,
    settings: Settings = Depends(get_settings),
):
    """Burn-in subtitles via the ``subtitles=`` ffmpeg filter.
    Synchronous; output cached by hash of clip URL + captions."""
    captions = body.captions
    for entry in captions:
        if entry.end_s <= entry.start_s:
            return _error(
                422, "validation_error",
                f"caption end_s ({entry.end_s}) must be > start_s ({entry.start_s})",
            )

    captions_payload = [
        {"s": e.start_s, "e": e.end_s, "t": e.text} for e in captions
    ]
    cache_seed = (
        body.clip_url + "|" + json.dumps(captions_payload, sort_keys=True)
    ).encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/captions/mock-{cache_key}.mp4"
        logger.info(
            "internal captions mock output=%s segments=%d",
            output_url, len(captions),
        )
        return InternalProcessedClipResponse(
            output_url=output_url,
            duration_seconds=5.0,
            size_bytes=1024 * 1024,
            mock_mode=True,
        )

    import shutil as _shutil
    import subprocess as _subprocess

    if not _shutil.which("ffmpeg"):
        return _error(500, "internal_error", "ffmpeg not found on PATH")

    target_dir = _captions_dir(settings)
    output_path = target_dir / f"{cache_key}.mp4"
    if output_path.exists():
        return InternalProcessedClipResponse(
            output_url=f"/data/_internal/captions/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            mock_mode=False,
        )

    try:
        clip_path = _download_concat_input(body.clip_url, target_dir / "sources", settings)
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        logger.warning("captions download failed: %s", exc)
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    srt_path = target_dir / f"{cache_key}.srt"
    _write_srt(captions, srt_path)

    tmp = output_path.with_suffix(".mp4.tmp")
    # Escape colons + special chars for the ffmpeg filter graph.
    srt_escaped = str(srt_path).replace(":", r"\\:")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(clip_path),
        "-vf", f"subtitles='{srt_escaped}'",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-f", "mp4",
        str(tmp),
    ]

    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-400:]
            tmp.unlink(missing_ok=True)
            return _error(
                500, "internal_error",
                f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not tmp.exists():
            return _error(500, "internal_error", "ffmpeg produced no output")
        tmp.replace(output_path)
    except _subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", "ffmpeg captions timed out")
    except Exception as exc:  # pragma: no cover — defensive
        tmp.unlink(missing_ok=True)
        logger.exception("captions unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    logger.info(
        "internal captions done output=%s segments=%d size=%d",
        output_path.name, len(captions), output_path.stat().st_size,
    )
    return InternalProcessedClipResponse(
        output_url=f"/data/_internal/captions/{output_path.name}",
        duration_seconds=None,
        size_bytes=output_path.stat().st_size,
        mock_mode=False,
    )


# ---- POST /internal/clips/intro_outro/ ----------------------------


class TitleCardSpec(BaseModel):
    """A single title card (intro or outro)."""

    text: str = Field(..., min_length=1, max_length=400)
    duration_s: float = Field(default=3.0, ge=0.5, le=15)
    bg_color: str = Field(default="black")
    text_color: str = Field(default="white")
    font_size: int = Field(default=48, ge=16, le=200)


class InternalIntroOutroCreate(BaseModel):
    """Request body for ``POST /internal/clips/intro_outro/``."""

    clip_url: str = Field(..., min_length=1, max_length=2048)
    intro: Optional[TitleCardSpec] = None
    outro: Optional[TitleCardSpec] = None


def _intro_outro_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "intro_outros"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _build_card_filter(
    spec: TitleCardSpec,
    canvas_w: int,
    canvas_h: int,
    input_label: str,
    output_label: str,
) -> str:
    """drawtext filter for a single title card. ``input_label``
    is the ffmpeg input label (e.g. ``[1:v]``) referencing a
    lavfi color source; ``output_label`` is the named output
    (e.g. ``[intro_v]``)."""
    # Escape text for drawtext — backslashes, colons, single quotes.
    escaped = (
        spec.text
        .replace("\\", "\\\\")
        .replace(":", r"\:")
        .replace("'", r"\\'")
    )
    return (
        f"{input_label}drawtext="
        f"text='{escaped}':"
        f"fontsize={spec.font_size}:"
        f"fontcolor={spec.text_color}:"
        "x=(w-text_w)/2:y=(h-text_h)/2"
        f"{output_label}"
    )


@router.post(
    "/clips/intro_outro/", response_model=InternalProcessedClipResponse,
)
def post_internal_intro_outro(
    body: InternalIntroOutroCreate,
    settings: Settings = Depends(get_settings),
):
    """Wrap a body clip with an intro and/or outro title card.
    At least one of ``intro`` / ``outro`` must be supplied —
    otherwise the operation is a no-op and the API rejects it."""
    if body.intro is None and body.outro is None:
        return _error(
            422, "validation_error",
            "intro_outro requires at least one of intro / outro",
        )

    intro_dict = body.intro.model_dump() if body.intro else None
    outro_dict = body.outro.model_dump() if body.outro else None
    cache_seed = (
        body.clip_url + "|"
        + json.dumps({"intro": intro_dict, "outro": outro_dict}, sort_keys=True)
    ).encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/intro_outros/mock-{cache_key}.mp4"
        logger.info(
            "internal intro_outro mock output=%s intro=%s outro=%s",
            output_url, body.intro is not None, body.outro is not None,
        )
        return InternalProcessedClipResponse(
            output_url=output_url,
            duration_seconds=5.0 + (body.intro.duration_s if body.intro else 0)
                + (body.outro.duration_s if body.outro else 0),
            size_bytes=1024 * 1024,
            mock_mode=True,
        )

    import shutil as _shutil
    import subprocess as _subprocess

    if not _shutil.which("ffmpeg"):
        return _error(500, "internal_error", "ffmpeg not found on PATH")

    target_dir = _intro_outro_dir(settings)
    output_path = target_dir / f"{cache_key}.mp4"
    if output_path.exists():
        return InternalProcessedClipResponse(
            output_url=f"/data/_internal/intro_outros/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            mock_mode=False,
        )

    try:
        clip_path = _download_concat_input(body.clip_url, target_dir / "sources", settings)
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    # Probe the body clip's dims so the cards match.
    base_dur = _probe_duration(clip_path)
    canvas_w, canvas_h = 1280, 720  # safe default; real probe would refine

    # Build filter_complex + ffmpeg input list. Indexing: body
    # video is [0]; intro card (if present) is [1:v]+[2:a]; body
    # audio is [0:a]; outro card (if present) is [3:v]+[4:a] (or
    # [1:v]+[2:a] when no intro). Use a builder that tracks
    # input indices.
    ffmpeg_inputs: list[str] = ["-i", str(clip_path)]
    filter_parts: list[str] = []
    concat_chain: list[str] = []

    if body.intro:
        intro_v_idx = len(ffmpeg_inputs) // 2
        ffmpeg_inputs += [
            "-f", "lavfi",
            "-i", f"color=c={body.intro.bg_color}:s={canvas_w}x{canvas_h}:r=30:d={body.intro.duration_s}",
        ]
        intro_a_idx = len(ffmpeg_inputs) // 2
        ffmpeg_inputs += [
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000:d={body.intro.duration_s}",
        ]
        filter_parts.append(_build_card_filter(
            body.intro, canvas_w, canvas_h,
            f"[{intro_v_idx}:v]", "[intro_v]",
        ))
        concat_chain.append(f"[intro_v][{intro_a_idx}:a]")

    # Body — already at [0:v]/[0:a]
    concat_chain.append("[0:v][0:a]")

    if body.outro:
        outro_v_idx = len(ffmpeg_inputs) // 2
        ffmpeg_inputs += [
            "-f", "lavfi",
            "-i", f"color=c={body.outro.bg_color}:s={canvas_w}x{canvas_h}:r=30:d={body.outro.duration_s}",
        ]
        outro_a_idx = len(ffmpeg_inputs) // 2
        ffmpeg_inputs += [
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000:d={body.outro.duration_s}",
        ]
        filter_parts.append(_build_card_filter(
            body.outro, canvas_w, canvas_h,
            f"[{outro_v_idx}:v]", "[outro_v]",
        ))
        concat_chain.append(f"[outro_v][{outro_a_idx}:a]")

    n = len(concat_chain)
    concat_filter = "".join(concat_chain) + f"concat=n={n}:v=1:a=1[outv][outa]"
    filter_parts.append(concat_filter)
    filter_complex = ";".join(filter_parts)

    tmp = output_path.with_suffix(".mp4.tmp")
    cmd = ["ffmpeg", "-y", "-loglevel", "error", *ffmpeg_inputs, "-filter_complex", filter_complex]
    cmd += [
        "-map", "[outv]", "-map", "[outa]",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-b:a", "192k",
        "-movflags", "+faststart",
        "-f", "mp4",
        str(tmp),
    ]

    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-400:]
            tmp.unlink(missing_ok=True)
            return _error(
                500, "internal_error",
                f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not tmp.exists():
            return _error(500, "internal_error", "ffmpeg produced no output")
        tmp.replace(output_path)
    except _subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", "ffmpeg intro_outro timed out")
    except Exception as exc:  # pragma: no cover — defensive
        tmp.unlink(missing_ok=True)
        logger.exception("intro_outro unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    total_extra = (body.intro.duration_s if body.intro else 0) + (body.outro.duration_s if body.outro else 0)
    return InternalProcessedClipResponse(
        output_url=f"/data/_internal/intro_outros/{output_path.name}",
        duration_seconds=base_dur + total_extra,
        size_bytes=output_path.stat().st_size,
        mock_mode=False,
    )


# ---- POST /internal/clips/trim/ -----------------------------------


class InternalTrimCreate(BaseModel):
    """Request body for ``POST /internal/clips/trim/``."""

    clip_url: str = Field(..., min_length=1, max_length=2048)
    start_ms: int = Field(..., ge=0)
    end_ms: int = Field(..., gt=0)


def _trim_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "trims"
    target.mkdir(parents=True, exist_ok=True)
    return target


@router.post(
    "/clips/trim/", response_model=InternalProcessedClipResponse,
)
def post_internal_trim(
    body: InternalTrimCreate,
    settings: Settings = Depends(get_settings),
):
    """Trim a clip to ``[start_ms, end_ms]``. Stream-copy
    (no re-encode) for speed."""
    if body.end_ms <= body.start_ms:
        return _error(
            422, "validation_error",
            f"end_ms ({body.end_ms}) must be > start_ms ({body.start_ms})",
        )

    cache_seed = (
        f"{body.clip_url}|trim|{body.start_ms}|{body.end_ms}"
    ).encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/trims/mock-{cache_key}.mp4"
        return InternalProcessedClipResponse(
            output_url=output_url,
            duration_seconds=(body.end_ms - body.start_ms) / 1000.0,
            size_bytes=1024 * 1024,
            mock_mode=True,
        )

    import shutil as _shutil
    import subprocess as _subprocess

    if not _shutil.which("ffmpeg"):
        return _error(500, "internal_error", "ffmpeg not found on PATH")

    target_dir = _trim_dir(settings)
    output_path = target_dir / f"{cache_key}.mp4"
    if output_path.exists():
        return InternalProcessedClipResponse(
            output_url=f"/data/_internal/trims/{output_path.name}",
            duration_seconds=(body.end_ms - body.start_ms) / 1000.0,
            size_bytes=output_path.stat().st_size,
            mock_mode=False,
        )

    try:
        clip_path = _download_concat_input(body.clip_url, target_dir / "sources", settings)
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    start_s = body.start_ms / 1000.0
    end_s = body.end_ms / 1000.0
    tmp = output_path.with_suffix(".mp4.tmp")
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-ss", f"{start_s:.3f}",
        "-to", f"{end_s:.3f}",
        "-i", str(clip_path),
        "-c", "copy",
        "-movflags", "+faststart",
        "-f", "mp4",
        str(tmp),
    ]

    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-400:]
            tmp.unlink(missing_ok=True)
            return _error(
                500, "internal_error",
                f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not tmp.exists():
            return _error(500, "internal_error", "ffmpeg produced no output")
        tmp.replace(output_path)
    except _subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", "ffmpeg trim timed out")
    except Exception as exc:  # pragma: no cover — defensive
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    return InternalProcessedClipResponse(
        output_url=f"/data/_internal/trims/{output_path.name}",
        duration_seconds=(body.end_ms - body.start_ms) / 1000.0,
        size_bytes=output_path.stat().st_size,
        mock_mode=False,
    )


# ---- POST /internal/clips/reformat/ -------------------------------


# Supported target aspect ratios. Locked to the same set Runway
# itself supports (see runway_client.GENERATION_POLICY).
_REFORMAT_RATIOS = {
    "1280:720": (1280, 720),
    "720:1280": (720, 1280),
    "960:960": (960, 960),
}


class InternalReformatCreate(BaseModel):
    """Request body for ``POST /internal/clips/reformat/``."""

    clip_url: str = Field(..., min_length=1, max_length=2048)
    target_ratio: str = Field(...)


def _reformat_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "reformats"
    target.mkdir(parents=True, exist_ok=True)
    return target


@router.post(
    "/clips/reformat/", response_model=InternalProcessedClipResponse,
)
def post_internal_reformat(
    body: InternalReformatCreate,
    settings: Settings = Depends(get_settings),
):
    """Scale + crop a clip to the target aspect ratio. The
    canonical use case is Reels conversion (1280:720 → 720:1280)."""
    if body.target_ratio not in _REFORMAT_RATIOS:
        return _error(
            400, "unsupported_ratio",
            f"target_ratio must be one of {sorted(_REFORMAT_RATIOS.keys())}; "
            f"got {body.target_ratio!r}",
        )

    target_w, target_h = _REFORMAT_RATIOS[body.target_ratio]
    cache_seed = (
        f"{body.clip_url}|reformat|{body.target_ratio}"
    ).encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/reformats/mock-{cache_key}.mp4"
        return InternalProcessedClipResponse(
            output_url=output_url,
            duration_seconds=5.0,
            size_bytes=1024 * 1024,
            mock_mode=True,
        )

    import shutil as _shutil
    import subprocess as _subprocess

    if not _shutil.which("ffmpeg"):
        return _error(500, "internal_error", "ffmpeg not found on PATH")

    target_dir = _reformat_dir(settings)
    output_path = target_dir / f"{cache_key}.mp4"
    if output_path.exists():
        return InternalProcessedClipResponse(
            output_url=f"/data/_internal/reformats/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            mock_mode=False,
        )

    try:
        clip_path = _download_concat_input(body.clip_url, target_dir / "sources", settings)
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    tmp = output_path.with_suffix(".mp4.tmp")
    # scale to fit then crop centered.
    vf = (
        f"scale={target_w}:{target_h}:force_original_aspect_ratio=increase,"
        f"crop={target_w}:{target_h},setsar=1"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(clip_path),
        "-vf", vf,
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        "-f", "mp4",
        str(tmp),
    ]

    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=180)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-400:]
            tmp.unlink(missing_ok=True)
            return _error(
                500, "internal_error",
                f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not tmp.exists():
            return _error(500, "internal_error", "ffmpeg produced no output")
        tmp.replace(output_path)
    except _subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", "ffmpeg reformat timed out")
    except Exception as exc:  # pragma: no cover — defensive
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    return InternalProcessedClipResponse(
        output_url=f"/data/_internal/reformats/{output_path.name}",
        duration_seconds=None,
        size_bytes=output_path.stat().st_size,
        mock_mode=False,
    )


# ---- V10 voice flows ---------------------------------------------
#
# SESSION 143 / V10. Ports the hackathon's audio_client.py voice
# design + multilingual dubbing into the V0+ composition arc.
# These were already shipped + production-tested at the
# hackathon (the operator used dub_audio across 29 languages);
# V10 restores them under Asset+Composition shape rather than
# Campaign storage.
#
#   POST /internal/voices/design/ — generate a custom Runway
#                                   voice from a text
#                                   description. Synchronous
#                                   (Runway voice design
#                                   completes in ~10-30s).
#   POST /internal/audio/dub/     — multilingual voice dub of
#                                   an existing audio track.
#                                   Synchronous (Runway dub
#                                   completes in 30-240s).
#
# Both use the same Runway-side anchors as the hackathon
# (eleven_multilingual_ttv_v2 for design, eleven_voice_dubbing
# for dubbing) so billing + behavior match what operators
# already experienced.


_VOICE_DESIGN_MODEL = "eleven_multilingual_ttv_v2"
_VOICE_DUB_MODEL = "eleven_voice_dubbing"


# Ported verbatim from audio_client.py — 29 languages enumerated
# in the dub schema probe. Keep this tuple identical to the
# hackathon's set so any operator who used a language there
# can use the same code here.
SUPPORTED_DUB_LANGS: tuple[str, ...] = (
    "en", "hi", "pt", "zh", "es", "fr", "de", "ja", "ar", "ru",
    "ko", "id", "it", "nl", "tr", "pl", "sv", "fil", "ms", "ro",
    "uk", "el", "cs", "da", "fi", "bg", "hr", "sk", "ta",
)


# ---- POST /internal/voices/design/ -------------------------------


class InternalVoiceDesignCreate(BaseModel):
    """Request body for ``POST /internal/voices/design/``."""

    description: str = Field(..., min_length=4, max_length=1000)
    name: Optional[str] = Field(default=None, max_length=80)


class InternalVoiceDesignResponse(BaseModel):
    voice_id: str
    preview_url: Optional[str] = None
    mock_mode: bool


def _voice_design_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "voices"
    target.mkdir(parents=True, exist_ok=True)
    return target


@router.post(
    "/voices/design/", response_model=InternalVoiceDesignResponse,
)
def post_internal_voice_design(
    body: InternalVoiceDesignCreate,
    settings: Settings = Depends(get_settings),
):
    """Design a Runway custom voice from a text description.
    Synchronous — Runway's voice design polls inside the
    handler. Returns voice_id + preview MP3 URL (Runway-hosted
    or local mock)."""
    description = body.description.strip()
    name = (body.name or "").strip() or "Character OS Voice"

    if settings.runway_mock:
        digest = hashlib.sha256(
            (description + name).encode("utf-8")
        ).hexdigest()[:16]
        voice_id = f"mock_voice_{digest}"
        preview_url = f"/data/_internal/voices/mock-{digest}.mp3"
        logger.info(
            "internal voice_design mock voice=%s description_chars=%d",
            voice_id, len(description),
        )
        return InternalVoiceDesignResponse(
            voice_id=voice_id,
            preview_url=preview_url,
            mock_mode=True,
        )

    body_payload = {
        "name": name[:80],
        "from": {
            "type": "text",
            "prompt": description,
            "model": _VOICE_DESIGN_MODEL,
        },
    }
    create_url = f"{settings.runway_api_base}/v1/voices"
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                create_url, headers=_runway_headers(settings), json=body_payload,
            )
            if resp.status_code != 200:
                logger.warning(
                    "voice design create rc=%s body=%s",
                    resp.status_code, resp.text[:300],
                )
                return _error(
                    502, "upstream_runway_error",
                    f"runway returned {resp.status_code}",
                )
            created = resp.json()
    except httpx.HTTPError as exc:
        logger.warning("voice design http error: %s", exc)
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover
        logger.exception("voice design unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    voice_id = created.get("id")
    if not voice_id:
        return _error(
            502, "upstream_runway_error",
            "runway voice design response missing id",
        )

    # Poll until READY/FAILED. Matches the hackathon's 90s
    # ceiling — voice design usually completes in ~10-30s.
    import time as _time

    detail_url = f"{settings.runway_api_base}/v1/voices/{voice_id}"
    final_status = (created.get("status") or "").upper()
    payload = created
    deadline = _time.time() + 90
    try:
        with httpx.Client(timeout=20.0) as client:
            while _time.time() < deadline and final_status not in {"READY", "FAILED"}:
                _time.sleep(3)
                r = client.get(detail_url, headers=_runway_headers(settings))
                r.raise_for_status()
                payload = r.json()
                final_status = (payload.get("status") or "").upper()
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"poll error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover
        logger.exception("voice design poll unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    if final_status == "FAILED":
        return _error(
            502, "upstream_runway_error",
            "runway rejected the voice design request",
        )
    if final_status != "READY":
        return _error(
            500, "internal_error",
            f"voice design did not reach READY (final: {final_status})",
        )

    preview_url = payload.get("previewUrl") or payload.get("preview_url")
    logger.info(
        "internal voice_design ready voice=%s preview=%s",
        voice_id, bool(preview_url),
    )
    return InternalVoiceDesignResponse(
        voice_id=voice_id,
        preview_url=preview_url,
        mock_mode=False,
    )


# ---- POST /internal/audio/dub/ -----------------------------------


class InternalAudioDubCreate(BaseModel):
    """Request body for ``POST /internal/audio/dub/``."""

    audio_url: str = Field(..., min_length=1, max_length=2048)
    target_language: str = Field(..., min_length=2, max_length=10)


class InternalAudioDubResponse(BaseModel):
    output_url: str
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    target_language: str
    mock_mode: bool


def _dub_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "dubs"
    target.mkdir(parents=True, exist_ok=True)
    return target


@router.post(
    "/audio/dub/", response_model=InternalAudioDubResponse,
)
def post_internal_audio_dub(
    body: InternalAudioDubCreate,
    settings: Settings = Depends(get_settings),
):
    """Dub an audio track into the target language.
    Synchronous — Runway's dub task polls inside the handler.
    Returns the cached dubbed MP3 URL."""
    target_lang = body.target_language.strip().lower()
    if target_lang not in SUPPORTED_DUB_LANGS:
        return _error(
            400, "unsupported_language",
            f"target_language must be one of {sorted(SUPPORTED_DUB_LANGS)}; "
            f"got {body.target_language!r}",
        )

    audio_url = body.audio_url.strip()
    cache_seed = f"{audio_url}|dub|{target_lang}".encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/dubs/mock-{target_lang}-{cache_key}.mp3"
        logger.info(
            "internal audio_dub mock lang=%s output=%s",
            target_lang, output_url,
        )
        return InternalAudioDubResponse(
            output_url=output_url,
            duration_seconds=3.0,
            size_bytes=1024 * 50,
            target_language=target_lang,
            mock_mode=True,
        )

    target_dir = _dub_dir(settings)
    output_path = target_dir / f"{cache_key}-{target_lang}.mp3"
    if output_path.exists():
        return InternalAudioDubResponse(
            output_url=f"/data/_internal/dubs/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            target_language=target_lang,
            mock_mode=False,
        )

    # Resolve source URL to a local file then encode as data URI
    # for Runway. Same pattern as concat_clips download.
    try:
        local_audio = _download_concat_input(
            audio_url, target_dir / "sources", settings,
        )
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    # Encode as audio data URI for the Runway dub endpoint.
    try:
        audio_bytes = local_audio.read_bytes()
    except OSError as exc:
        return _error(500, "internal_error", f"failed to read source audio: {exc}")
    if len(audio_bytes) > 25 * 1024 * 1024:
        return _error(
            413, "audio_too_large",
            "source audio exceeds 25 MB cap",
        )
    # Determine mime from extension; default to audio/mpeg.
    ext = local_audio.suffix.lower().lstrip(".")
    mime_by_ext = {
        "mp3": "audio/mpeg", "wav": "audio/wav", "m4a": "audio/mp4",
        "ogg": "audio/ogg", "webm": "audio/webm", "aac": "audio/aac",
    }
    mime = mime_by_ext.get(ext, "audio/mpeg")
    audio_data_uri = f"data:{mime};base64," + base64.b64encode(audio_bytes).decode("ascii")

    create_url = f"{settings.runway_api_base}/v1/voice_dubbing"
    body_payload = {
        "model": _VOICE_DUB_MODEL,
        "audioUri": audio_data_uri,
        "targetLang": target_lang,
    }
    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                create_url, headers=_runway_headers(settings), json=body_payload,
            )
            if resp.status_code != 200:
                logger.warning(
                    "dub create rc=%s body=%s",
                    resp.status_code, resp.text[:300],
                )
                return _error(
                    502, "upstream_runway_error",
                    f"runway returned {resp.status_code}",
                )
            created = resp.json()
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover
        logger.exception("dub create unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    task_id = created.get("id")
    if not task_id:
        return _error(
            502, "upstream_runway_error",
            "runway dub response missing task id",
        )

    # Poll /v1/tasks/{id} until terminal. Matches hackathon's
    # 4-minute deadline; voice dubbing typically completes in
    # 30-240s depending on source length + target language.
    import time as _time

    deadline = _time.time() + 240
    final_payload = None
    try:
        with httpx.Client(timeout=20.0) as client:
            while _time.time() < deadline:
                r = client.get(
                    f"{settings.runway_api_base}/v1/tasks/{task_id}",
                    headers=_runway_headers(settings),
                )
                r.raise_for_status()
                payload = r.json()
                status = (payload.get("status") or "").upper()
                if status == "SUCCEEDED":
                    final_payload = payload
                    break
                if status in {"FAILED", "CANCELED"}:
                    reason = payload.get("failure") or payload.get("error") or status
                    return _error(
                        502, "upstream_runway_error",
                        f"dub task {status}: {reason}",
                    )
                _time.sleep(5)
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"poll error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover
        logger.exception("dub poll unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    if not final_payload:
        return _error(500, "internal_error", f"dub task {task_id} timed out")

    output = final_payload.get("output")
    out_url: Optional[str] = None
    if isinstance(output, list):
        for v in output:
            if isinstance(v, str):
                out_url = v
                break
    if not out_url:
        return _error(
            502, "upstream_runway_error",
            f"dub task {task_id} produced no output url",
        )

    # Download the dubbed audio to local cache so downstream
    # primitives can re-use it without re-downloading from
    # Runway's CDN. Same pattern as character_host_client._download.
    tmp = output_path.with_suffix(".mp3.tmp")
    try:
        with httpx.Client(timeout=120.0) as client:
            with client.stream("GET", out_url) as r:
                r.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in r.iter_bytes(64 * 1024):
                        fh.write(chunk)
        tmp.replace(output_path)
    except httpx.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover
        tmp.unlink(missing_ok=True)
        logger.exception("dub download unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    logger.info(
        "internal audio_dub done lang=%s task=%s output=%s size=%d",
        target_lang, task_id, output_path.name, output_path.stat().st_size,
    )
    return InternalAudioDubResponse(
        output_url=f"/data/_internal/dubs/{output_path.name}",
        duration_seconds=None,
        size_bytes=output_path.stat().st_size,
        target_language=target_lang,
        mock_mode=False,
    )


# ---- V11 style_remix (Aleph) -------------------------------------
#
# SESSION 143 / V11. Ports the hackathon's aleph_client.py — full
# chunked path included. Aleph (gen4_aleph) has a hard ~5s output
# cap regardless of source length, so sources longer than ~5.5s
# get split → parallel-remix → concat to cover the whole timeline.
#
# The capability shipped at the hackathon and operators used the
# style presets in production; V11 is a restoration under
# Asset+Composition shape, not a net-new feature.
#
#   POST /internal/clips/style_remix/  — synchronous; handles
#                                        both single-clip and
#                                        chunked paths internally.
#
# Style presets are hardcoded server-side (operator can't typo
# into a no-op prompt; ops can tune prompts without re-shipping
# the SPA).


_ALEPH_MODEL = "gen4_aleph"
_ALEPH_MAX_SOURCE_BYTES = 16 * 1024 * 1024  # 16 MB per-clip data-URI cap
_ALEPH_CHUNK_SECONDS = 5
_ALEPH_CHUNK_THRESHOLD_S = 5.5
_ALEPH_PARALLEL_CHUNKS = 4
_ALEPH_POLL_DEADLINE_S = 600.0


# Style presets ported verbatim from
# runway-hackathon/backend/app/services/aleph_client.py:STYLE_PRESETS.
# Keep this dict identical so operators who used a preset in
# production get the same Aleph behavior here.
ALEPH_STYLE_PRESETS: dict[str, dict[str, str]] = {
    "noir": {
        "label": "Cinematic Noir",
        "prompt": (
            "Cinematic film noir, high contrast black-and-white, deep "
            "shadows, dramatic side lighting, 35mm film grain, vintage "
            "1940s cinematography"
        ),
    },
    "anime": {
        "label": "Anime",
        "prompt": (
            "Hand-drawn anime style, bold flat colors, expressive line "
            "art, soft cel shading, Studio Ghibli-inspired backgrounds, "
            "exaggerated character features"
        ),
    },
    "chrome": {
        "label": "Liquid Chrome",
        "prompt": (
            "Liquid chrome metallic style, reflective polished metal "
            "surfaces, futuristic neon highlights, mirror-finish "
            "subject, electric blue and silver palette"
        ),
    },
    "watercolor": {
        "label": "Watercolor",
        "prompt": (
            "Loose watercolor painting style, soft pastel washes, "
            "bleeding edges, visible brush strokes, hand-painted on "
            "textured paper, dreamy diffused light"
        ),
    },
    "cyberpunk": {
        "label": "Cyberpunk Neon",
        "prompt": (
            "Cyberpunk neon style, saturated magenta and cyan lighting, "
            "rain-soaked streets, holographic overlays, Blade Runner "
            "atmosphere, high-tech low-life aesthetic"
        ),
    },
}


class InternalStyleRemixCreate(BaseModel):
    """Request body for ``POST /internal/clips/style_remix/``."""

    clip_url: str = Field(..., min_length=1, max_length=2048)
    style_preset: str = Field(..., min_length=1, max_length=40)
    seed: Optional[int] = Field(default=None, ge=0, le=2**32 - 1)


class InternalStyleRemixResponse(BaseModel):
    output_url: str
    duration_seconds: Optional[float] = None
    size_bytes: Optional[int] = None
    style_preset: str
    chunked: bool
    task_ids: list[str] = Field(default_factory=list)
    mock_mode: bool


def _style_remix_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "style_remixes"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _aleph_create_task(
    *,
    video_uri: str,
    prompt: str,
    seed: Optional[int],
    settings: Settings,
) -> str:
    """POST /v1/video_to_video with model=gen4_aleph. Returns
    Runway task id. Raises httpx errors on transport failure."""
    body: dict = {
        "model": _ALEPH_MODEL,
        "videoUri": video_uri,
        "promptText": prompt,
    }
    if seed is not None:
        body["seed"] = int(seed)
    url = f"{settings.runway_api_base}/v1/video_to_video"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=_runway_headers(settings), json=body)
        if resp.status_code != 200:
            raise RuntimeError(
                f"aleph create rejected: {resp.status_code} {resp.text[:300]}"
            )
        created = resp.json()
    task_id = created.get("id")
    if not task_id:
        raise RuntimeError(f"aleph create missing task id: {created}")
    return task_id


def _aleph_poll_task(task_id: str, settings: Settings) -> str:
    """Poll /v1/tasks/{id} until terminal. Returns the output
    URL on SUCCEEDED; raises on FAILED/CANCELED/timeout."""
    import time as _time

    deadline = _time.time() + _ALEPH_POLL_DEADLINE_S
    with httpx.Client(timeout=30.0) as client:
        while _time.time() < deadline:
            r = client.get(
                f"{settings.runway_api_base}/v1/tasks/{task_id}",
                headers=_runway_headers(settings),
            )
            r.raise_for_status()
            payload = r.json()
            status = (payload.get("status") or "").upper()
            if status == "SUCCEEDED":
                output = payload.get("output")
                if isinstance(output, list):
                    for v in output:
                        if isinstance(v, str):
                            return v
                raise RuntimeError(
                    f"aleph task {task_id} succeeded with no output url"
                )
            if status in {"FAILED", "CANCELED"}:
                reason = payload.get("failure") or payload.get("error") or status
                raise RuntimeError(f"aleph task {status}: {reason}")
            _time.sleep(5)
    raise RuntimeError(
        f"aleph task {task_id} timed out after {_ALEPH_POLL_DEADLINE_S:.0f}s"
    )


def _aleph_download(url: str, target: Path) -> int:
    """Stream Runway output to ``target``. Returns bytes written."""
    tmp = target.with_suffix(target.suffix + ".tmp")
    try:
        with httpx.Client(timeout=120.0) as client:
            with client.stream("GET", url) as r:
                r.raise_for_status()
                size = 0
                with tmp.open("wb") as fh:
                    for chunk in r.iter_bytes(64 * 1024):
                        fh.write(chunk)
                        size += len(chunk)
        tmp.replace(target)
        return size
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def _aleph_remix_one(
    *,
    source_path: Path,
    prompt: str,
    seed: Optional[int],
    target_path: Path,
    settings: Settings,
) -> str:
    """End-to-end single Aleph fire: read → POST → poll →
    download. Returns the Runway task_id."""
    clip_bytes = source_path.read_bytes()
    if len(clip_bytes) > _ALEPH_MAX_SOURCE_BYTES:
        raise RuntimeError(
            f"clip {source_path.name} is {len(clip_bytes):,} bytes; "
            f"exceeds the {_ALEPH_MAX_SOURCE_BYTES // (1024 * 1024)} MB cap"
        )
    video_uri = (
        "data:video/mp4;base64," + base64.b64encode(clip_bytes).decode("ascii")
    )
    task_id = _aleph_create_task(
        video_uri=video_uri, prompt=prompt, seed=seed, settings=settings,
    )
    out_url = _aleph_poll_task(task_id, settings)
    _aleph_download(out_url, target_path)
    return task_id


def _aleph_split_into_chunks(
    source: Path, chunk_seconds: int, scratch_dir: Path,
) -> list[Path]:
    """ffmpeg-split source into N-second chunks with FORCED
    keyframes so cuts land at exact chunk_seconds boundaries.
    Aleph truncates to ~5s regardless of source length, so
    keyframe-aligned 8s chunks would still get truncated."""
    import subprocess as _subprocess

    chunk_glob = scratch_dir / "chunk-%03d.mp4"
    _subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(source),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "128k",
            "-force_key_frames", f"expr:gte(t,n_forced*{chunk_seconds})",
            "-map", "0",
            "-f", "segment",
            "-segment_time", str(chunk_seconds),
            "-reset_timestamps", "1",
            str(chunk_glob),
        ],
        check=True, capture_output=True, text=True, timeout=180,
    )
    chunks = sorted(scratch_dir.glob("chunk-*.mp4"))
    if not chunks:
        raise RuntimeError(f"ffmpeg segment produced no chunks for {source}")
    return chunks


def _aleph_concat_chunks(chunk_paths: list[Path], target: Path) -> None:
    """ffmpeg-concat the remixed chunks with -c copy. Same seed
    across chunks means encoding parameters align, so no re-encode
    needed."""
    import subprocess as _subprocess

    list_file = target.parent / f"{target.stem}-concat-list.txt"
    try:
        list_file.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in chunk_paths) + "\n"
        )
        _subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                "-movflags", "+faststart",
                str(target),
            ],
            check=True, capture_output=True, text=True, timeout=180,
        )
    finally:
        list_file.unlink(missing_ok=True)


@router.post(
    "/clips/style_remix/", response_model=InternalStyleRemixResponse,
)
def post_internal_style_remix(
    body: InternalStyleRemixCreate,
    settings: Settings = Depends(get_settings),
):
    """Style-remix a CLIP via Runway Aleph. Routes internally
    on duration: ≤5.5s single-fires; longer sources go through
    the chunked path (ffmpeg split → parallel Aleph → concat).

    Cached by hash(clip_url + preset + seed). Operators rerunning
    the same remix don't pay Runway twice."""
    preset_id = body.style_preset.strip().lower()
    preset = ALEPH_STYLE_PRESETS.get(preset_id)
    if preset is None:
        return _error(
            400, "unsupported_preset",
            f"style_preset must be one of {sorted(ALEPH_STYLE_PRESETS.keys())}; "
            f"got {body.style_preset!r}",
        )

    # Lock seed at request time. The chunked path reuses one
    # seed across every chunk so the visual style stays coherent
    # at chunk boundaries. Operator-supplied seed wins for
    # reproducibility; otherwise we pick a random one and record
    # it in the cache key so retries with new randomness still
    # cache-miss correctly.
    import random as _random

    seed = body.seed if body.seed is not None else _random.randrange(0, 2**32)

    cache_seed = f"{body.clip_url}|aleph|{preset_id}|{seed}".encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    if settings.runway_mock:
        output_url = f"/data/_internal/style_remixes/mock-{preset_id}-{cache_key}.mp4"
        return InternalStyleRemixResponse(
            output_url=output_url,
            duration_seconds=5.0,
            size_bytes=1024 * 1024,
            style_preset=preset_id,
            chunked=False,
            task_ids=[f"mock_aleph_{cache_key}"],
            mock_mode=True,
        )

    import shutil as _shutil

    if not _shutil.which("ffmpeg") or not _shutil.which("ffprobe"):
        return _error(
            500, "internal_error",
            "ffmpeg/ffprobe not found on PATH",
        )

    target_dir = _style_remix_dir(settings)
    output_path = target_dir / f"{preset_id}-{cache_key}.mp4"
    if output_path.exists():
        return InternalStyleRemixResponse(
            output_url=f"/data/_internal/style_remixes/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            style_preset=preset_id,
            chunked=False,  # cache hit — unknown
            task_ids=[],
            mock_mode=False,
        )

    try:
        source_path = _download_concat_input(
            body.clip_url, target_dir / "sources", settings,
        )
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    source_duration = _probe_duration(source_path)
    use_chunking = source_duration > _ALEPH_CHUNK_THRESHOLD_S

    try:
        if not use_chunking:
            # Single-fire path.
            task_id = _aleph_remix_one(
                source_path=source_path,
                prompt=preset["prompt"],
                seed=seed,
                target_path=output_path,
                settings=settings,
            )
            task_ids = [task_id]
        else:
            # Chunked path. Split → parallel remix → concat.
            import concurrent.futures
            import tempfile as _tempfile

            with _tempfile.TemporaryDirectory(prefix="aleph-chunks-") as tmpd:
                scratch = Path(tmpd)
                chunks = _aleph_split_into_chunks(
                    source_path, _ALEPH_CHUNK_SECONDS, scratch,
                )
                chunk_outputs: list[Path] = [
                    scratch / f"remix-out-{idx:03d}.mp4"
                    for idx in range(len(chunks))
                ]
                task_ids: list[str] = ["" for _ in chunks]
                errors: list[str] = []

                def _fire_one(idx: int) -> None:
                    try:
                        tid = _aleph_remix_one(
                            source_path=chunks[idx],
                            prompt=preset["prompt"],
                            seed=seed,
                            target_path=chunk_outputs[idx],
                            settings=settings,
                        )
                        task_ids[idx] = tid
                    except Exception as exc:
                        errors.append(f"chunk {idx + 1}/{len(chunks)}: {exc!s}")

                with concurrent.futures.ThreadPoolExecutor(
                    max_workers=min(_ALEPH_PARALLEL_CHUNKS, len(chunks)),
                ) as pool:
                    list(pool.map(_fire_one, range(len(chunks))))

                if errors:
                    return _error(
                        502, "upstream_runway_error",
                        f"{len(errors)}/{len(chunks)} chunks failed: "
                        + "; ".join(errors[:3]),
                    )

                _aleph_concat_chunks(chunk_outputs, output_path)

        logger.info(
            "internal style_remix done preset=%s chunked=%s output=%s tasks=%d",
            preset_id, use_chunking, output_path.name, len(task_ids),
        )
        return InternalStyleRemixResponse(
            output_url=f"/data/_internal/style_remixes/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            style_preset=preset_id,
            chunked=use_chunking,
            task_ids=task_ids,
            mock_mode=False,
        )
    except RuntimeError as exc:
        return _error(502, "upstream_runway_error", str(exc)[:300])
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("style_remix unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])


# ---- V12 transcribe (Whisper) ------------------------------------
#
# SESSION 143 / V12. First net-new capability beyond what the
# hackathon shipped. OpenAI Whisper transcription unlocks
# auto-captioning + the recut_teaser composition (take a long
# rendered ad, auto-pick the strongest sentence, output a
# vertical teaser).
#
# Server-side handling:
#   1. Download source CLIP or AUDIO to local cache
#   2. If CLIP: ffmpeg-extract audio to MP3
#   3. POST audio to OpenAI Whisper API
#   4. Return verbose JSON with segment-level timing
#
# The composition primitive sees one input + one TRANSCRIPT
# output regardless. Audio extraction is invisible — primitive
# accepts both CLIP and AUDIO inputs uniformly.


_WHISPER_MODEL = "whisper-1"
_TRANSCRIBE_MAX_AUDIO_BYTES = 25 * 1024 * 1024  # OpenAI's hard limit


class InternalTranscribeCreate(BaseModel):
    """Request body for ``POST /internal/transcribe/``."""

    source_url: str = Field(..., min_length=1, max_length=2048)
    # Set when source is a video; media-engine extracts the audio
    # track first. ``True`` is the default since most operator
    # input is CLIP-shaped (talking_head outputs); AUDIO sources
    # (e.g. design_voice previews) set False to skip extraction.
    extract_audio: bool = Field(default=True)


class TranscriptSegment(BaseModel):
    start_s: float
    end_s: float
    text: str


class InternalTranscribeResponse(BaseModel):
    segments: list[TranscriptSegment]
    duration_seconds: Optional[float] = None
    language: Optional[str] = None
    full_text: str
    mock_mode: bool


def _transcribe_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "transcripts"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _extract_audio_for_whisper(source: Path, target: Path) -> None:
    """ffmpeg-extract audio track to MP3 for Whisper. Quality
    is set to 64kbps mono — well above Whisper's needs while
    keeping the upload under OpenAI's 25 MB cap for typical
    ad-length clips (10+ minutes fits comfortably)."""
    import subprocess as _subprocess

    _subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(source),
            "-vn",
            "-ac", "1",
            "-ar", "16000",
            "-acodec", "libmp3lame",
            "-b:a", "64k",
            "-f", "mp3",
            str(target),
        ],
        check=True, capture_output=True, text=True, timeout=180,
    )


def _mock_transcript_segments(source_url: str) -> list[dict]:
    """Deterministic mock segments keyed by source URL hash.
    Three short sentences spaced across a 9-second window.
    Same hash → same segments so tests stay stable."""
    digest = hashlib.sha256(source_url.encode("utf-8")).hexdigest()[:8]
    return [
        {"start_s": 0.0, "end_s": 2.5, "text": f"Welcome to the demo {digest[:4]}."},
        {"start_s": 2.5, "end_s": 6.0, "text": "This is the strongest line in the ad."},
        {"start_s": 6.0, "end_s": 9.0, "text": "Visit us today."},
    ]


@router.post(
    "/transcribe/", response_model=InternalTranscribeResponse,
)
def post_internal_transcribe(
    body: InternalTranscribeCreate,
    settings: Settings = Depends(get_settings),
):
    """Transcribe a CLIP or AUDIO asset to sentence-level
    timing via OpenAI Whisper. Synchronous; output cached by
    hash of source URL."""
    source_url = body.source_url.strip()
    cache_seed = f"{source_url}|whisper|{body.extract_audio}".encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]
    target_dir = _transcribe_dir(settings)
    output_json = target_dir / f"{cache_key}.json"

    if output_json.exists():
        try:
            cached = json.loads(output_json.read_text())
            return InternalTranscribeResponse(**cached)
        except (json.JSONDecodeError, ValueError):
            output_json.unlink(missing_ok=True)  # stale cache; fall through

    # Mock mode short-circuits — deterministic segments + no
    # OpenAI call. Set when OPENAI_API_KEY is missing or when
    # the operator forces mock-mode via env.
    use_mock = settings.runway_mock or not os.environ.get("OPENAI_API_KEY")
    if use_mock:
        segments = _mock_transcript_segments(source_url)
        response_dict = {
            "segments": segments,
            "duration_seconds": segments[-1]["end_s"] if segments else None,
            "language": "en",
            "full_text": " ".join(s["text"] for s in segments),
            "mock_mode": True,
        }
        output_json.write_text(json.dumps(response_dict))
        logger.info(
            "internal transcribe mock source=%s segments=%d",
            source_url[:80], len(segments),
        )
        return InternalTranscribeResponse(**response_dict)

    # Real mode — download source, extract audio if CLIP, POST to Whisper.
    try:
        source_path = _download_concat_input(
            source_url, target_dir / "sources", settings,
        )
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    if body.extract_audio:
        audio_path = target_dir / "sources" / f"{cache_key}.mp3"
        if not audio_path.exists():
            try:
                _extract_audio_for_whisper(source_path, audio_path)
            except Exception as exc:
                return _error(
                    500, "internal_error",
                    f"audio extraction failed: {exc!s}"[:300],
                )
    else:
        audio_path = source_path

    if audio_path.stat().st_size > _TRANSCRIBE_MAX_AUDIO_BYTES:
        return _error(
            413, "audio_too_large",
            f"audio exceeds OpenAI's "
            f"{_TRANSCRIBE_MAX_AUDIO_BYTES // (1024 * 1024)} MB Whisper cap",
        )

    try:
        from openai import OpenAI

        client = OpenAI()
        with audio_path.open("rb") as fh:
            result = client.audio.transcriptions.create(
                model=_WHISPER_MODEL,
                file=fh,
                response_format="verbose_json",
                timestamp_granularities=["segment"],
            )
    except Exception as exc:
        logger.exception("whisper transcribe failed")
        return _error(
            502, "upstream_runway_error",
            f"openai whisper error: {exc!s}"[:300],
        )

    # The verbose_json response shape from OpenAI's SDK includes
    # `segments` with start/end/text. Whisper's `segments` are
    # roughly sentence-level by default.
    raw_segments = getattr(result, "segments", None) or []
    segments = [
        {
            "start_s": float(getattr(seg, "start", 0.0)),
            "end_s": float(getattr(seg, "end", 0.0)),
            "text": str(getattr(seg, "text", "")).strip(),
        }
        for seg in raw_segments
        if str(getattr(seg, "text", "")).strip()
    ]
    full_text = str(getattr(result, "text", "") or "")
    language = getattr(result, "language", None)
    duration = getattr(result, "duration", None)

    response_dict = {
        "segments": segments,
        "duration_seconds": float(duration) if duration is not None else None,
        "language": language,
        "full_text": full_text,
        "mock_mode": False,
    }
    output_json.write_text(json.dumps(response_dict))

    logger.info(
        "internal transcribe done source=%s segments=%d duration=%s lang=%s",
        source_url[:80], len(segments), duration, language,
    )
    return InternalTranscribeResponse(**response_dict)


# ---- V13 generate_image ------------------------------------------
#
# SESSION 143 / V13. Generic Runway image generation via
# /v1/text_to_image with model gen4_image. The existing
# /internal/portrait/ stays in place for the wizard's
# portrait-template flow; /internal/images/ is the generic
# version that accepts free-form prompts + optional
# reference images for the V13 storyboard recipe.


_GEN4_IMAGE_MODEL = "gen4_image"
_IMAGE_GEN_DEADLINE_S = 90.0
_IMAGE_RATIOS = {"1280:720", "720:1280", "1024:1024"}


class InternalImageCreate(BaseModel):
    """Request body for ``POST /internal/images/``."""

    prompt: str = Field(..., min_length=4, max_length=2000)
    ratio: str = Field(default="1280:720")
    seed: Optional[int] = Field(default=None, ge=0, le=2**32 - 1)
    reference_image_url: Optional[str] = Field(default=None, max_length=2048)


class InternalImageResponse(BaseModel):
    image_url: str
    width: Optional[int] = None
    height: Optional[int] = None
    seed: Optional[int] = None
    mock_mode: bool


def _images_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "images"
    target.mkdir(parents=True, exist_ok=True)
    return target


def _ratio_dims(ratio: str) -> tuple[int, int]:
    w, _, h = ratio.partition(":")
    try:
        return int(w), int(h)
    except ValueError:
        return 1280, 720


@router.post(
    "/images/", response_model=InternalImageResponse,
)
def post_internal_image(
    body: InternalImageCreate,
    settings: Settings = Depends(get_settings),
):
    """Generate an image via Runway gen4_image. Synchronous;
    polls /v1/tasks/{id} inside the handler. Caches output by
    hash(prompt + ratio + seed + reference_image)."""
    if body.ratio not in _IMAGE_RATIOS:
        return _error(
            400, "invalid_settings",
            f"ratio must be one of {sorted(_IMAGE_RATIOS)}; got {body.ratio!r}",
        )

    prompt = body.prompt.strip()
    ref_url = (body.reference_image_url or "").strip() or None
    seed = body.seed

    cache_seed = (
        f"{prompt}|{body.ratio}|{seed}|{ref_url or ''}"
    ).encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]

    target_dir = _images_dir(settings)
    output_path = target_dir / f"{cache_key}.png"
    width, height = _ratio_dims(body.ratio)

    if output_path.exists():
        return InternalImageResponse(
            image_url=f"/data/_internal/images/{output_path.name}",
            width=width, height=height, seed=seed,
            mock_mode=False,
        )

    if settings.runway_mock:
        # Deterministic 1x1 mock PNG keyed off cache_key. Same
        # _solid_png helper the existing portrait endpoint uses
        # — picks a deterministic color from the seed string.
        mock_color = _mock_color_for(cache_key)
        png_bytes = _solid_png(width, height, mock_color)
        _atomic_write_bytes(output_path, png_bytes)
        logger.info(
            "internal image mock prompt_chars=%d ratio=%s output=%s",
            len(prompt), body.ratio, output_path.name,
        )
        return InternalImageResponse(
            image_url=f"/data/_internal/images/{output_path.name}",
            width=width, height=height, seed=seed,
            mock_mode=True,
        )

    # Real mode — POST /v1/text_to_image, poll, download.
    body_payload: dict = {
        "model": _GEN4_IMAGE_MODEL,
        "promptText": prompt[:2000],
        "ratio": body.ratio,
    }
    if seed is not None:
        body_payload["seed"] = int(seed)
    # Reference image is required by gen4_image; if the operator
    # didn't supply one, seed with a 1x1 neutral grey so the API
    # doesn't reject. Same workaround the existing portrait
    # endpoint uses.
    ref_data_uri = _image_url_to_data_uri(ref_url, settings) if ref_url else None
    if ref_data_uri is None:
        ref_data_uri = _seed_neutral_data_uri()
    body_payload["referenceImages"] = [{"uri": ref_data_uri, "tag": "ref"}]

    create_url = f"{settings.runway_api_base}/v1/text_to_image"
    import time as _time

    try:
        with httpx.Client(timeout=30.0) as client:
            resp = client.post(
                create_url, headers=_runway_headers(settings), json=body_payload,
            )
            if resp.status_code != 200:
                logger.warning(
                    "image create rc=%s body=%s",
                    resp.status_code, resp.text[:300],
                )
                return _error(
                    502, "upstream_runway_error",
                    f"runway returned {resp.status_code}",
                )
            created = resp.json()
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover
        logger.exception("image create unexpected")
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    task_id = created.get("id")
    if not task_id:
        return _error(
            502, "upstream_runway_error",
            "runway image response missing task id",
        )

    deadline = _time.time() + _IMAGE_GEN_DEADLINE_S
    final_payload = None
    try:
        with httpx.Client(timeout=20.0) as client:
            while _time.time() < deadline:
                r = client.get(
                    f"{settings.runway_api_base}/v1/tasks/{task_id}",
                    headers=_runway_headers(settings),
                )
                r.raise_for_status()
                payload = r.json()
                status = (payload.get("status") or "").upper()
                if status == "SUCCEEDED":
                    final_payload = payload
                    break
                if status in {"FAILED", "CANCELED"}:
                    reason = payload.get("failure") or payload.get("error") or status
                    code = payload.get("failureCode") or ""
                    return _error(
                        502, "upstream_runway_error",
                        f"image task {status}: {reason}"
                        + (f" [code={code}]" if code else ""),
                    )
                _time.sleep(3)
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"poll error: {exc!s}"[:300])

    if not final_payload:
        return _error(500, "internal_error", f"image task {task_id} timed out")

    output = final_payload.get("output")
    out_url: Optional[str] = None
    if isinstance(output, list):
        for v in output:
            if isinstance(v, str):
                out_url = v
                break
    if not out_url:
        return _error(
            502, "upstream_runway_error",
            f"image task {task_id} produced no output url",
        )

    # Download the generated image to local cache.
    tmp = output_path.with_suffix(".png.tmp")
    try:
        with httpx.Client(timeout=60.0) as client:
            with client.stream("GET", out_url) as r:
                r.raise_for_status()
                with tmp.open("wb") as fh:
                    for chunk in r.iter_bytes(64 * 1024):
                        fh.write(chunk)
        tmp.replace(output_path)
    except httpx.HTTPError as exc:
        tmp.unlink(missing_ok=True)
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    logger.info(
        "internal image done prompt_chars=%d ratio=%s task=%s size=%d",
        len(prompt), body.ratio, task_id, output_path.stat().st_size,
    )
    return InternalImageResponse(
        image_url=f"/data/_internal/images/{output_path.name}",
        width=width, height=height, seed=seed,
        mock_mode=False,
    )


def _seed_neutral_data_uri() -> str:
    """1x1 neutral-grey PNG as a base64 data URI. Used as the
    referenceImages seed when the operator didn't supply one
    (gen4_image rejects requests without at least one reference
    image)."""
    png = _solid_png(1, 1, (200, 200, 200))
    return "data:image/png;base64," + base64.b64encode(png).decode("ascii")


def _image_url_to_data_uri(url: str, settings: Settings) -> Optional[str]:
    """Resolve a reference image URL to a data URI. Tries local
    path under data_path first, then HTTP(S) download. Returns
    None if the URL can't be resolved (caller falls back to the
    neutral seed)."""
    try:
        local = _download_concat_input(
            url, _images_dir(settings) / "refs", settings,
        )
    except Exception:
        return None
    if not local.exists():
        return None
    try:
        data = local.read_bytes()
    except OSError:
        return None
    ext = local.suffix.lower().lstrip(".")
    mime_by_ext = {
        "png": "image/png", "jpg": "image/jpeg", "jpeg": "image/jpeg",
        "webp": "image/webp",
    }
    mime = mime_by_ext.get(ext, "image/png")
    return f"data:{mime};base64," + base64.b64encode(data).decode("ascii")


# ---- V14 audio_extract -------------------------------------------
#
# SESSION 143 / V14. Extract the audio track from a CLIP via
# ffmpeg `-vn`. Synchronous; output cached by source URL hash.
# Unblocks the deferred storyboard_voiced starter (V13) by
# making it possible to take a generate_avatar_speech CLIP and
# pull its audio for mixing under a silent storyboard.


_AUDIO_EXTRACT_FORMATS = {"mp3", "aac", "wav"}


class InternalAudioExtractCreate(BaseModel):
    """Request body for ``POST /internal/audio/extract/``."""

    clip_url: str = Field(..., min_length=1, max_length=2048)
    format: str = Field(default="mp3")


def _audio_extract_dir(settings: Settings) -> Path:
    target = settings.data_path / "_internal" / "audio_extracts"
    target.mkdir(parents=True, exist_ok=True)
    return target


@router.post(
    "/audio/extract/", response_model=InternalProcessedClipResponse,
)
def post_internal_audio_extract(
    body: InternalAudioExtractCreate,
    settings: Settings = Depends(get_settings),
):
    """Extract the audio track from a CLIP. Synchronous;
    output cached by hash(clip_url + format)."""
    fmt = body.format.strip().lower()
    if fmt not in _AUDIO_EXTRACT_FORMATS:
        return _error(
            400, "invalid_settings",
            f"format must be one of {sorted(_AUDIO_EXTRACT_FORMATS)}; "
            f"got {body.format!r}",
        )

    cache_seed = f"{body.clip_url}|extract|{fmt}".encode("utf-8")
    cache_key = hashlib.sha256(cache_seed).hexdigest()[:16]
    ext = "m4a" if fmt == "aac" else fmt
    target_dir = _audio_extract_dir(settings)
    output_path = target_dir / f"{cache_key}.{ext}"

    if settings.runway_mock:
        output_url = f"/data/_internal/audio_extracts/mock-{cache_key}.{ext}"
        return InternalProcessedClipResponse(
            output_url=output_url,
            duration_seconds=5.0,
            size_bytes=1024 * 50,
            mock_mode=True,
        )

    if output_path.exists():
        return InternalProcessedClipResponse(
            output_url=f"/data/_internal/audio_extracts/{output_path.name}",
            duration_seconds=None,
            size_bytes=output_path.stat().st_size,
            mock_mode=False,
        )

    import shutil as _shutil
    import subprocess as _subprocess

    if not _shutil.which("ffmpeg"):
        return _error(500, "internal_error", "ffmpeg not found on PATH")

    try:
        clip_path = _download_concat_input(
            body.clip_url, target_dir / "sources", settings,
        )
    except FileNotFoundError as exc:
        return _error(400, "validation_error", str(exc))
    except httpx.HTTPError as exc:
        return _error(502, "upstream_runway_error", f"download error: {exc!s}"[:300])

    tmp = output_path.with_suffix(output_path.suffix + ".tmp")
    codec_args: list[str] = []
    if fmt == "mp3":
        codec_args = ["-c:a", "libmp3lame", "-b:a", "192k"]
    elif fmt == "aac":
        codec_args = ["-c:a", "aac", "-b:a", "192k"]
    elif fmt == "wav":
        codec_args = ["-c:a", "pcm_s16le"]
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(clip_path),
        "-vn",
        *codec_args,
        "-f", fmt if fmt != "aac" else "mp4",
        str(tmp),
    ]

    try:
        result = _subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-400:]
            tmp.unlink(missing_ok=True)
            return _error(
                500, "internal_error",
                f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not tmp.exists():
            return _error(500, "internal_error", "ffmpeg produced no output")
        tmp.replace(output_path)
    except _subprocess.TimeoutExpired:
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", "ffmpeg audio_extract timed out")
    except Exception as exc:  # pragma: no cover — defensive
        tmp.unlink(missing_ok=True)
        return _error(500, "internal_error", f"unexpected: {exc!s}"[:300])

    return InternalProcessedClipResponse(
        output_url=f"/data/_internal/audio_extracts/{output_path.name}",
        duration_seconds=None,
        size_bytes=output_path.stat().st_size,
        mock_mode=False,
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


# ---- POST /internal/realtime_sessions/ -------------------------
# SESSION 146 / R2 — realtime avatar arc. Two endpoints in
# this slice: POST creates a session, GET polls it. End +
# transcript come in R3 / R5.


class InternalRealtimeToolDef(BaseModel):
    """A tool the avatar may invoke during a session.
    Matches `RealtimeProvider.ToolDef`."""

    name: str = Field(..., min_length=1, max_length=80)
    description: str = Field(..., max_length=500)
    parameters: dict = Field(default_factory=dict)


class InternalRealtimeSessionCreate(BaseModel):
    """Request body for ``POST /internal/realtime_sessions/``.

    Primitive inputs — no `Campaign` coupling. The Django
    broker (R3) composes these from `RealtimeSession` +
    spokesperson + K-arc retrieval; this endpoint just
    forwards to the configured provider.
    """

    avatar_id: str = Field(..., min_length=1, max_length=200)
    personality: str = Field(default="", max_length=9500)
    start_script: str = Field(default="", max_length=280)
    document_ids: list[str] = Field(default_factory=list)
    tools: list[InternalRealtimeToolDef] = Field(default_factory=list)
    provider: str = Field(default="runway", max_length=20)


class InternalRealtimeSessionResponse(BaseModel):
    session_id: str
    # NEVER log this — JWT-shaped SDK connect token.
    session_key: str
    status: str
    expires_at: Optional[str] = None
    avatar_id: Optional[str] = None
    mock_mode: bool


@router.post(
    "/realtime_sessions/",
    response_model=InternalRealtimeSessionResponse,
)
def post_internal_realtime_session(
    body: InternalRealtimeSessionCreate,
    settings: Settings = Depends(get_settings),
):
    """Create a Runway realtime session via the configured
    provider. Returns the SDK-safe payload (session id,
    session key, expiry).

    In mock mode the deterministic stubs land instead;
    `mock_mode=True` is set on the response.
    """
    from ..services.realtime_provider import (
        RealtimeProviderError,
        ToolDef,
        get_provider,
    )

    try:
        provider = get_provider(body.provider, settings)
    except RealtimeProviderError as exc:
        return _error(503, "realtime_unavailable", str(exc)[:300])

    tool_defs = [
        ToolDef(name=t.name, description=t.description, parameters=t.parameters)
        for t in body.tools
    ]

    try:
        result = provider.create_session(
            avatar_id=body.avatar_id,
            personality=body.personality,
            start_script=body.start_script,
            document_ids=list(body.document_ids),
            tools=tool_defs,
        )
    except RealtimeProviderError as exc:
        return _error(502, "upstream_runway_error", str(exc)[:300])

    # Deliberately log session_id only — never session_key.
    logger.info(
        "internal realtime_session create session_id=%s avatar=%s "
        "status=%s mock=%s docs=%d tools=%d",
        result.session_id, body.avatar_id, result.status,
        settings.runway_mock, len(body.document_ids), len(tool_defs),
    )

    return InternalRealtimeSessionResponse(
        session_id=result.session_id,
        session_key=result.session_key,
        status=result.status,
        expires_at=result.expires_at,
        avatar_id=result.avatar_id,
        mock_mode=settings.runway_mock,
    )


class InternalRealtimeSessionPollResponse(BaseModel):
    session_id: str
    status: str
    expires_at: Optional[str] = None
    error_message: str = ""
    mock_mode: bool


@router.get(
    "/realtime_sessions/{session_id}/",
    response_model=InternalRealtimeSessionPollResponse,
)
def get_internal_realtime_session(
    session_id: str,
    provider: str = "runway",
    settings: Settings = Depends(get_settings),
):
    """Poll a realtime session. Drives the broker's
    creating → not_ready → ready state machine."""
    from ..services.realtime_provider import (
        RealtimeProviderError,
        get_provider,
    )

    try:
        provider_impl = get_provider(provider, settings)
    except RealtimeProviderError as exc:
        return _error(503, "realtime_unavailable", str(exc)[:300])

    try:
        state = provider_impl.poll_session(session_id)
    except RealtimeProviderError as exc:
        return _error(502, "upstream_runway_error", str(exc)[:300])

    return InternalRealtimeSessionPollResponse(
        session_id=state.session_id,
        status=state.status,
        expires_at=state.expires_at,
        error_message=state.error_message,
        mock_mode=settings.runway_mock,
    )


class InternalRealtimeDocumentCreate(BaseModel):
    """Request body for ``POST /internal/realtime_documents/``.

    R4 — broker calls this with the composed Markdown body
    (built shell-side from K2 retrieval) to push a
    knowledge document to Runway. Returns the
    ``document_id`` the broker persists on
    ``RealtimeSession.provider_document_id``.
    """

    name: str = Field(..., min_length=1, max_length=200)
    content: str = Field(..., min_length=1, max_length=40_000)
    provider: str = Field(default="runway", max_length=20)


class InternalRealtimeDocumentResponse(BaseModel):
    document_id: str
    mock_mode: bool


@router.post(
    "/realtime_documents/",
    response_model=InternalRealtimeDocumentResponse,
)
def post_internal_realtime_document(
    body: InternalRealtimeDocumentCreate,
    settings: Settings = Depends(get_settings),
):
    """Create a Runway document via the configured provider.
    R4 — the realtime-session create flow calls this before
    create_session, then passes the returned document_id in
    the session payload's ``document_ids`` array."""
    from ..services.realtime_provider import (
        RealtimeProviderError,
        get_provider,
    )

    try:
        provider_impl = get_provider(body.provider, settings)
    except RealtimeProviderError as exc:
        return _error(503, "realtime_unavailable", str(exc)[:300])

    try:
        result = provider_impl.create_document(
            name=body.name, content=body.content,
        )
    except RealtimeProviderError as exc:
        return _error(502, "upstream_runway_error", str(exc)[:300])

    logger.info(
        "internal realtime_document create doc_id=%s name=%r chars=%d mock=%s",
        result.document_id, body.name, len(body.content), settings.runway_mock,
    )
    return InternalRealtimeDocumentResponse(
        document_id=result.document_id,
        mock_mode=settings.runway_mock,
    )


class InternalRealtimeTranscriptSegment(BaseModel):
    role: str
    text: str
    ts: Optional[str] = None


class InternalRealtimeTranscriptResponse(BaseModel):
    """Response for ``GET /internal/realtime_sessions/<id>/transcript/``.
    R5 — broker calls this after a session ends to persist
    the transcript as an Asset(TRANSCRIPT)."""

    session_id: str
    text: str
    segments: list[InternalRealtimeTranscriptSegment]
    mock_mode: bool


@router.get(
    "/realtime_sessions/{session_id}/transcript/",
    response_model=InternalRealtimeTranscriptResponse,
)
def get_internal_realtime_session_transcript(
    session_id: str,
    provider: str = "runway",
    settings: Settings = Depends(get_settings),
):
    """Pull the post-session transcript. Returns an empty
    result (rather than 404) when the conversation isn't
    recorded yet — the broker treats empty transcripts as
    "no content captured this session" rather than a
    failure."""
    from ..services.realtime_provider import (
        RealtimeProviderError,
        get_provider,
    )

    try:
        provider_impl = get_provider(provider, settings)
    except RealtimeProviderError as exc:
        return _error(503, "realtime_unavailable", str(exc)[:300])

    try:
        result = provider_impl.fetch_transcript(session_id)
    except RealtimeProviderError as exc:
        return _error(502, "upstream_runway_error", str(exc)[:300])

    # Normalize segments to the pydantic shape.
    segments = [
        InternalRealtimeTranscriptSegment(
            role=str(s.get("role", "")),
            text=str(s.get("text", "")),
            ts=(str(s["ts"]) if s.get("ts") is not None else None),
        )
        for s in result.segments
    ]
    logger.info(
        "internal realtime_session transcript session_id=%s turns=%d chars=%d mock=%s",
        session_id, len(segments), len(result.text), settings.runway_mock,
    )
    return InternalRealtimeTranscriptResponse(
        session_id=session_id,
        text=result.text,
        segments=segments,
        mock_mode=settings.runway_mock,
    )


class InternalRealtimeSessionEndResponse(BaseModel):
    session_id: str
    ended: bool
    mock_mode: bool


@router.delete(
    "/realtime_sessions/{session_id}/",
    response_model=InternalRealtimeSessionEndResponse,
)
def delete_internal_realtime_session(
    session_id: str,
    provider: str = "runway",
    settings: Settings = Depends(get_settings),
):
    """End a realtime session. R3 — the Django broker calls this
    on operator-initiated close. Best-effort: upstream 404 / 410
    (already gone) is treated as success."""
    from ..services.realtime_provider import (
        RealtimeProviderError,
        get_provider,
    )

    try:
        provider_impl = get_provider(provider, settings)
    except RealtimeProviderError as exc:
        return _error(503, "realtime_unavailable", str(exc)[:300])

    try:
        provider_impl.end_session(session_id)
    except RealtimeProviderError as exc:
        return _error(502, "upstream_runway_error", str(exc)[:300])

    logger.info(
        "internal realtime_session end session_id=%s mock=%s",
        session_id, settings.runway_mock,
    )
    return InternalRealtimeSessionEndResponse(
        session_id=session_id,
        ended=True,
        mock_mode=settings.runway_mock,
    )
