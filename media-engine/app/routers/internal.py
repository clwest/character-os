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
(fire-then-poll video generation). Voice clone still pending.
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
    _create_avatar_real,
)
from ..services.runway_client import (
    GenerationSettingsError,
    create_task as runway_create_task,
    get_task as runway_get_task,
    resolve_model,
    validate_generation_settings,
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
