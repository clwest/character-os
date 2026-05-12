"""Aleph style remix (PR FA — `/v1/video_to_video`).

Single public entry point: ``remix_output_video``. Takes a cached
source MP4 + a style prompt, posts the bytes (as a data URI) to
Runway's Aleph endpoint with ``model: "gen4_aleph"``, polls until the
task terminates, downloads the remix MP4 to ``data/finished/``, and
returns a ``RemixResult`` the router uses to append a new
OutputRecord (``kind="spokesperson_ad_remix"``, ``remix_style`` set
to the human-readable style slug).

Body shape (locked via empty-body 400-probe, 2026-05-12):

    {
      "model": "gen4_aleph",
      "videoUri": "<URL or data URI>",
      "promptText": "<free-text style prompt>",
      "ratio": "1280:720"           # optional; defaults match source
    }

Five other models are advertised on the same route
(``robotics_v1``, ``aleph2_alpha``, ``seedance2``, ``klingO3_pro``,
``klingO3_standard``) but ``gen4_aleph`` is the canonical Aleph
style-transfer model in the API map.

Mock mode skips Runway entirely and copies the source MP4 into the
target location so the UI + storage code paths exercise end-to-end
without keys. The "remix" is visually identical to the source in
mock — the OutputRecord pathing is real.

Never raises in normal operation — returns a structured result. The
router maps failure to HTTP 502 with the embedded error string.
"""
from __future__ import annotations

import base64
import logging
import shutil
import subprocess
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from ..config import Settings

logger = logging.getLogger(__name__)

_MODEL = "gen4_aleph"
_MAX_SOURCE_BYTES = 16 * 1024 * 1024  # 16 MB data-URI cap
_POLL_DEADLINE_S = 600.0  # Aleph is slow — ~minutes per short clip

# Hardcoded style presets. The frontend sends a `style_id` from this
# map; the prompt text is the canonical Aleph prompt we use. Keeping
# the table server-side means the operator can't typo into a no-op
# prompt + lets us tune the prompts without a redeploy of the SPA.
STYLE_PRESETS: dict[str, dict[str, str]] = {
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


@dataclass
class RemixResult:
    """Returned from `remix_output_video`."""

    status: str  # "ok" | "failed"
    output_path: Optional[Path] = None
    cache_filename: Optional[str] = None
    duration_s: Optional[float] = None
    task_id: Optional[str] = None
    error: Optional[str] = None
    mock_mode: bool = False


class AlephError(RuntimeError):
    """Internal — caught by the public entry point."""


def _headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.runway_api_key}",
        "X-Runway-Version": settings.runway_api_version,
        "Content-Type": "application/json",
    }


def _ffprobe_duration(path: Path) -> Optional[float]:
    try:
        out = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(path),
            ],
            check=True, capture_output=True, text=True, timeout=10,
        )
        return float(out.stdout.strip() or 0.0)
    except Exception:
        return None


def _create_task(
    *, video_uri: str, prompt: str, settings: Settings,
) -> str:
    """POST /v1/video_to_video, return task id."""
    body = {
        "model": _MODEL,
        "videoUri": video_uri,
        "promptText": prompt,
    }
    url = f"{settings.runway_api_base}/v1/video_to_video"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=_headers(settings), json=body)
        if resp.status_code != 200:
            raise AlephError(
                f"video_to_video create failed: {resp.status_code} "
                f"{resp.text[:300]}"
            )
        created = resp.json()
    task_id = created.get("id")
    if not task_id:
        raise AlephError(f"video_to_video create missing task id: {created}")
    return task_id


def _poll_task(task_id: str, settings: Settings) -> str:
    """Poll until SUCCEEDED, return the first output URL."""
    deadline = time.time() + _POLL_DEADLINE_S
    final = None
    with httpx.Client(timeout=30.0) as client:
        while time.time() < deadline:
            r = client.get(
                f"{settings.runway_api_base}/v1/tasks/{task_id}",
                headers=_headers(settings),
            )
            r.raise_for_status()
            payload = r.json()
            status = (payload.get("status") or "").upper()
            if status == "SUCCEEDED":
                final = payload
                break
            if status in {"FAILED", "CANCELED"}:
                reason = (
                    payload.get("failure")
                    or payload.get("error")
                    or payload.get("failureCode")
                    or status
                )
                raise AlephError(f"video_to_video task {status}: {reason}")
            time.sleep(5)
    if not final:
        raise AlephError(
            f"video_to_video task {task_id} timed out after "
            f"{int(_POLL_DEADLINE_S)}s"
        )
    output = final.get("output")
    out_url: Optional[str] = None
    if isinstance(output, list):
        for v in output:
            if isinstance(v, str):
                out_url = v
                break
    if not out_url:
        raise AlephError(
            f"video_to_video task {task_id} produced no output url"
        )
    return out_url


def _download(url: str, target: Path) -> int:
    """Stream `url` to `target`. Returns bytes written. Raises on
    non-200 or a non-video content type."""
    tmp = target.with_suffix(target.suffix + ".tmp")
    size = 0
    try:
        with httpx.stream(
            "GET", url, timeout=120.0, follow_redirects=True,
        ) as resp:
            resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").lower()
            if not (ctype.startswith("video/") or ctype.startswith("application/octet-stream")):
                raise AlephError(
                    f"unexpected content-type for remix output: {ctype}"
                )
            with open(tmp, "wb") as fh:
                for chunk in resp.iter_bytes():
                    size += len(chunk)
                    fh.write(chunk)
        tmp.rename(target)
    except Exception:
        try:
            if tmp.exists():
                tmp.unlink()
        except Exception:
            pass
        raise
    return size


def remix_output_video(
    *,
    source_video_path: Path,
    campaign_id: str,
    output_id: str,
    style_id: str,
    settings: Settings,
) -> RemixResult:
    """Style-remix an existing rendered MP4 via Runway Aleph.

    Caller is responsible for validating the source OutputRecord and
    appending the resulting OutputRecord to the campaign once the
    return value is `status == "ok"`.
    """
    preset = STYLE_PRESETS.get(style_id)
    if not preset:
        return RemixResult(
            status="failed",
            error=(
                f"unknown style_id '{style_id}'. supported: "
                f"{sorted(STYLE_PRESETS.keys())}"
            ),
            mock_mode=settings.runway_mock,
        )

    if not source_video_path.exists():
        return RemixResult(
            status="failed",
            error=f"source video not found at {source_video_path}",
            mock_mode=settings.runway_mock,
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    cache_filename = (
        f"{campaign_id}-remix-{style_id}-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename

    # Mock mode — copy the source so the UI flow exercises end-to-end.
    if settings.runway_mock:
        try:
            shutil.copyfile(source_video_path, output_path)
        except Exception as exc:
            return RemixResult(
                status="failed",
                error=f"mock copy failed: {exc!s}"[:300],
                mock_mode=True,
            )
        return RemixResult(
            status="ok",
            output_path=output_path,
            cache_filename=cache_filename,
            duration_s=_ffprobe_duration(source_video_path),
            task_id=f"mock_remix_{uuid.uuid4().hex[:8]}",
            mock_mode=True,
        )

    # Real mode.
    video_bytes = source_video_path.read_bytes()
    if len(video_bytes) > _MAX_SOURCE_BYTES:
        return RemixResult(
            status="failed",
            error=(
                f"source video {len(video_bytes):,} bytes exceeds the "
                f"{_MAX_SOURCE_BYTES // (1024 * 1024)}MB data-URI cap. "
                f"Try a shorter ad or downscale the source."
            ),
        )
    video_uri = (
        "data:video/mp4;base64,"
        + base64.b64encode(video_bytes).decode("ascii")
    )

    try:
        task_id = _create_task(
            video_uri=video_uri,
            prompt=preset["prompt"],
            settings=settings,
        )
        logger.info(
            "remix task created campaign=%s output=%s style=%s task=%s",
            campaign_id, output_id, style_id, task_id,
        )
        out_url = _poll_task(task_id, settings)
        bytes_written = _download(out_url, output_path)
        duration = _ffprobe_duration(output_path)
        logger.info(
            "remix ok campaign=%s output=%s style=%s bytes=%d duration=%.2f task=%s",
            campaign_id, output_id, style_id,
            bytes_written, duration or 0.0, task_id,
        )
        return RemixResult(
            status="ok",
            output_path=output_path,
            cache_filename=cache_filename,
            duration_s=duration,
            task_id=task_id,
        )
    except AlephError as exc:
        logger.warning(
            "remix failed campaign=%s output=%s style=%s: %s",
            campaign_id, output_id, style_id, exc,
        )
        return RemixResult(status="failed", error=str(exc)[:300])
    except httpx.HTTPError as exc:
        logger.warning("remix http error: %s", exc)
        return RemixResult(status="failed", error=f"http error: {exc!s}"[:300])
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("remix unexpected")
        return RemixResult(status="failed", error=f"unexpected: {exc!s}"[:300])
