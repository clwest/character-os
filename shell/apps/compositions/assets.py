"""Asset Library v1 (SESSION 187, A3) — storage-health helper.

The Asset table holds a mix of locations: Runway/Cloudfront URLs that
expire on a JWT-encoded clock, local files cached under
``media-engine/data/`` that may or may not still be on disk, inline
``data:`` URIs from V13/keyframe payloads, and the occasional empty
file_path (TRANSCRIPT Assets store their content in ``inline_content``).

``compute_storage_health(asset)`` is the v1 one-stop classifier the A4
read endpoint, the A5 SPA list view, and the A6 detail view all call to
get an operator-actionable status string.

Per SESSION 185 Q-a-3: **live per request for v1; cache only if A5
perf demands**. No caching, no model field — pure stateless function.
The seven status values land in :class:`StorageHealth`.

JWT exp parsing handles Runway's Cloudfront-signed URL shape:

    https://<cdn>/<uuid>.mp4?_jwt=<header>.<payload>.<signature>

Payload is base64url-encoded JSON with an ``exp`` claim
(unix-seconds). Malformed JWTs (corrupt encoding, missing exp,
non-numeric exp) fall back to ``HTTPS_LIVE`` — we don't have signal
to say otherwise without making a network round-trip.
"""
from __future__ import annotations

import base64
import json
import logging
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.utils import timezone

if TYPE_CHECKING:
    from apps.compositions.models import Asset


logger = logging.getLogger(__name__)


# 24-hour window before a JWT-bearing URL is flagged ``HTTPS_EXPIRING_SOON``.
_EXPIRY_WARNING_WINDOW_S = 24 * 60 * 60


class StorageHealth:
    """String constants for the seven storage-health states.

    Not a ``TextChoices`` enum — these aren't persisted on the model;
    they're computed per-request. Bare strings keep the serializer
    shape simple (no enum->value conversion in DRF).
    """

    HTTPS_LIVE = "https_live"
    HTTPS_EXPIRING_SOON = "https_expiring_soon"
    HTTPS_EXPIRED = "https_expired"
    LOCAL_PRESENT = "local_present"
    LOCAL_MISSING = "local_missing"
    DATA_URI = "data_uri"
    UPLOAD_PENDING = "upload_pending"

    @classmethod
    def all(cls) -> tuple[str, ...]:
        return (
            cls.HTTPS_LIVE,
            cls.HTTPS_EXPIRING_SOON,
            cls.HTTPS_EXPIRED,
            cls.LOCAL_PRESENT,
            cls.LOCAL_MISSING,
            cls.DATA_URI,
            cls.UPLOAD_PENDING,
        )


# Default media-engine data root. Asset.file_path values like
# ``/data/_internal/...`` resolve to ``<this>/data/_internal/...``.
# ``settings.MEDIA_ENGINE_DATA_ROOT`` overrides this — tests use it to
# point at a tmpdir; production deploys may use it to point at a
# different mounted volume.
_DEFAULT_MEDIA_ENGINE_DATA_ROOT = (
    Path(__file__).resolve().parents[3] / "media-engine"
)


def _media_engine_data_root() -> Path:
    override = getattr(settings, "MEDIA_ENGINE_DATA_ROOT", None)
    if override:
        return Path(override)
    return _DEFAULT_MEDIA_ENGINE_DATA_ROOT


def _b64url_decode(s: str) -> bytes:
    """JWT segments are base64url-encoded **without** padding. Pad
    explicitly before ``urlsafe_b64decode``."""
    padding = 4 - (len(s) % 4)
    if padding < 4:
        s += "=" * padding
    return base64.urlsafe_b64decode(s)


def parse_jwt_exp(url: str) -> int | None:
    """Return the ``exp`` claim (unix seconds) from a Runway-signed
    Cloudfront URL, or ``None`` if the URL doesn't carry a JWT or the
    JWT is malformed.

    Public helper so A4 can surface ``cdn_expires_at`` alongside the
    health status, and so smoke tools (SESSION 184 pattern) can check
    expiry without re-implementing the parse.
    """
    if not url:
        return None
    try:
        parsed = urlparse(url)
    except ValueError:
        return None
    qs = parse_qs(parsed.query)
    jwt_values = qs.get("_jwt")
    if not jwt_values:
        return None
    jwt = jwt_values[0]

    parts = jwt.split(".")
    if len(parts) != 3:
        return None

    try:
        payload_bytes = _b64url_decode(parts[1])
        payload = json.loads(payload_bytes.decode("utf-8"))
    except (ValueError, UnicodeDecodeError, json.JSONDecodeError):
        return None

    exp = payload.get("exp")
    if not isinstance(exp, (int, float)):
        return None
    return int(exp)


def _classify_https(url: str) -> str:
    """HTTPS branch — JWT-bearing URLs get LIVE/EXPIRING_SOON/EXPIRED;
    JWT-less URLs default to LIVE (we can't tell otherwise without a
    HEAD request)."""
    exp = parse_jwt_exp(url)
    if exp is None:
        return StorageHealth.HTTPS_LIVE

    now = int(timezone.now().timestamp())
    if exp < now:
        return StorageHealth.HTTPS_EXPIRED
    if exp - now < _EXPIRY_WARNING_WINDOW_S:
        return StorageHealth.HTTPS_EXPIRING_SOON
    return StorageHealth.HTTPS_LIVE


def _classify_local(file_path: str) -> str:
    """Local-path branch — strip the logical ``/data/...`` prefix,
    join under the media-engine data root, check ``Path.exists()``."""
    real_path = _media_engine_data_root() / file_path.lstrip("/")
    try:
        return (
            StorageHealth.LOCAL_PRESENT
            if real_path.is_file()
            else StorageHealth.LOCAL_MISSING
        )
    except OSError:  # pragma: no cover — defensive
        logger.warning("storage_health: OSError on stat %s", real_path)
        return StorageHealth.LOCAL_MISSING


def compute_storage_health(asset: "Asset") -> str:
    """Classify ``asset.file_path`` into one of the seven
    :class:`StorageHealth` constants.

    Branching:

    1. ``file_path`` empty → ``UPLOAD_PENDING`` (placeholder; v1 has
       no upload UI but TRANSCRIPT Assets with inline-only content
       land here too — the operator can tell them apart by
       ``asset_type``).
    2. ``data:...`` scheme → ``DATA_URI`` (Stability / V13 inline
       payloads).
    3. ``https://`` or ``http://`` → JWT-aware HTTPS classifier.
    4. ``/data/...`` (any leading-slash path) → filesystem existence
       check.
    5. Anything else → ``UPLOAD_PENDING`` (treat as unknown; the
       operator can sort the field out by hand if it ever shows up).
    """
    fp = (asset.file_path or "").strip()
    if not fp:
        return StorageHealth.UPLOAD_PENDING
    if fp.startswith("data:"):
        return StorageHealth.DATA_URI
    if fp.startswith("https://") or fp.startswith("http://"):
        return _classify_https(fp)
    if fp.startswith("/"):
        return _classify_local(fp)
    return StorageHealth.UPLOAD_PENDING


__all__ = [
    "StorageHealth",
    "compute_storage_health",
    "parse_jwt_exp",
]
