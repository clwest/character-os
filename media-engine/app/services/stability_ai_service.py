"""
Stability AI Service
====================

Ported from a sibling private project/core/services/stability_ai_service.py
(the sibling project session 872). Adapted for character-os media-engine: drops the
Django settings dependency, reads the API key from the FastAPI
``Settings`` object instead.

Provides:
- Adaptive timeout based on model complexity
- Exponential backoff retry for transient failures
- Centralized request helper for SD3 / Core / Ultra endpoints

Used by:
- ``app/services/stability_portrait.py`` — portrait orchestrator that
  ties this client to the style-library prompt presets
- ``app/routers/internal.py`` — ``POST /internal/portrait_stability/``
  endpoint that the Django rebake action calls when
  ``provider="stability"``
"""
from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

import httpx

from app.config import get_settings

logger = logging.getLogger(__name__)


# Model complexity affects generation time. Verbatim from the sibling project.
MODEL_TIMEOUT_MULTIPLIERS: Dict[str, float] = {
    "core": 1.0,   # Fastest - ~3.5s typical
    "sdxl": 1.5,   # Balanced - ~5.8s typical
    "sd3": 2.0,    # High quality - ~8.7s typical
    "ultra": 2.5,  # Premium - ~10.4s typical
}


def get_stability_api_key() -> Optional[str]:
    """Read the Stability API key from media-engine settings (which
    pulls from ``<repo-root>/.env``). Returns ``None`` when unset —
    callers should fall through to mock mode in that case.
    """
    key = (get_settings().stability_api_key or "").strip()
    return key or None


def calculate_adaptive_timeout(
    model: str, num_images: int = 1, base_timeout: int = 45,
) -> int:
    """Compute a request timeout in seconds based on model + count.

    Verbatim port of the sibling project's helper. Stability's ultra model can
    legitimately run 30+ seconds on a busy day; the 45s default
    floor + per-image addition keeps us from timing out before
    Stability does.
    """
    multiplier = MODEL_TIMEOUT_MULTIPLIERS.get(model, 1.5)
    per_image_time = 15  # Base time per image
    timeout = base_timeout + int(per_image_time * multiplier * num_images)
    return min(timeout, 180)  # 3-minute hard cap


def stability_request_with_retry(
    url: str,
    headers: Dict[str, str],
    *,
    data: Optional[Dict[str, Any]] = None,
    files: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None,
    timeout: int = 60,
    max_retries: int = 3,
    accept_type: str = "image/*",
) -> Dict[str, Any]:
    """POST to Stability AI with exponential-backoff retry.

    Ports the the sibling project helper. Returns a dict with one of two shapes:

    Success (image bytes):
        ``{"success": True, "content": <bytes>, "retries_used": int,
           "status_code": 200}``

    Success (JSON, when ``accept_type="application/json"``):
        ``{"success": True, "data": dict, "retries_used": int,
           "status_code": 200}``

    Failure:
        ``{"success": False, "error": str, "status_code": int|None,
           "retries_used": int}``

    Retries on transient errors (429, 5xx, timeout, connection
    error) with exponential backoff (2s, 5s, 9s). Non-retryable
    errors return immediately.
    """
    last_error: Optional[str] = None
    retries_used = 0

    for attempt in range(max_retries):
        try:
            logger.info(
                "stability request attempt=%d/%d timeout=%ds",
                attempt + 1, max_retries, timeout,
            )

            with httpx.Client(timeout=timeout) as client:
                if json_data is not None:
                    response = client.post(url, headers=headers, json=json_data)
                else:
                    # httpx multipart: files + data is the same shape as
                    # requests. ``files={"none": ""}`` forces multipart
                    # encoding even when no real file is uploaded —
                    # Stability's SD3/Core/Ultra endpoints require this.
                    response = client.post(
                        url, headers=headers, files=files, data=data,
                    )

            if response.status_code == 200:
                logger.info(
                    "stability request OK on attempt=%d", attempt + 1,
                )
                if accept_type == "application/json":
                    return {
                        "success": True,
                        "data": response.json(),
                        "retries_used": retries_used,
                        "status_code": 200,
                    }
                return {
                    "success": True,
                    "content": response.content,
                    "retries_used": retries_used,
                    "status_code": 200,
                }

            # Retryable error
            if response.status_code in {429, 500, 502, 503, 504}:
                last_error = (
                    f"HTTP {response.status_code}: {response.text[:200]}"
                )
                retries_used += 1
                wait_time = (2 ** attempt) + 1
                logger.warning(
                    "stability request retryable err=%s wait=%ds",
                    last_error, wait_time,
                )
                time.sleep(wait_time)
                continue

            # Non-retryable error — return immediately
            logger.error(
                "stability request non-retryable status=%d body=%s",
                response.status_code, response.text[:200],
            )
            return {
                "success": False,
                "error": response.text,
                "status_code": response.status_code,
                "retries_used": retries_used,
            }

        except httpx.TimeoutException:
            last_error = f"timeout after {timeout}s"
            retries_used += 1
            logger.warning("stability timeout attempt=%d", attempt + 1)
            timeout = min(timeout + 30, 180)
            continue

        except httpx.RequestError as exc:
            last_error = f"connection error: {exc!s}"
            retries_used += 1
            wait_time = (2 ** attempt) + 1
            logger.warning(
                "stability connection error wait=%ds err=%s",
                wait_time, exc,
            )
            time.sleep(wait_time)
            continue

        except Exception as exc:
            logger.exception("stability unexpected error: %s", exc)
            return {
                "success": False,
                "error": str(exc),
                "status_code": None,
                "retries_used": retries_used,
            }

    # All retries exhausted
    logger.error(
        "stability request failed after %d attempts: %s",
        max_retries, last_error,
    )
    return {
        "success": False,
        "error": f"failed after {max_retries} attempts: {last_error}",
        "status_code": None,
        "retries_used": retries_used,
    }
