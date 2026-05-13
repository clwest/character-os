"""Internal API surface consumed by the Django shell.

The architectural boundary defined in
``docs/design/MEDIA_ENGINE_INTERNAL_API.md`` — pure JSON in/out,
stateless across calls, no CharacterStore touch. The Django shell is
the only system of record for spokespeople / videos / threads; this
module is a thin façade over the existing media-engine services so
those services keep working for the legacy ``/api/*`` surface during
the Phase 2 transition.

SESSION 108 implements just ``POST /internal/avatars/``. Additional
verbs (voice clone, video generation, poll) land as Django features
need them.
"""
from __future__ import annotations

import base64
import binascii
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional

import httpx
from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..config import Settings, get_settings
from ..services.character_host_client import SUPPORTED_VOICE_PRESETS
from ..services.character_studio_client import (
    CharacterStudioError,
    _create_avatar_real,
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
