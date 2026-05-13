"""Animated PiP (PR FH) — `image_to_video` motion source + ffmpeg overlay.

Generates a 5s looping clip from the campaign's reference image
(or character portrait fallback) via Runway `image_to_video` with a
motion-style prompt, then ffmpeg-overlays the result in the
bottom-right corner of the avatar ad. Bed-loops to match the ad's
duration.

This is the dynamic upgrade to PR FC's static-image PiP. Same
corner placement + white border; only the corner content changes
from "still" to "looping video".

The motion presets live in the table below — keeping prompts
server-side means they can be tuned without an SPA redeploy.

Fires ONE `image_to_video` task per click (~30s-5min wall time +
1 Runway credit). No caching in v1 — every fire regenerates.
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
from .finisher_service import (
    is_ffmpeg_available,
    is_ffprobe_available,
    probe_duration,
)

logger = logging.getLogger(__name__)

# Five motion presets. Operator picks; backend sends the prompt
# verbatim to Runway image_to_video.
MOTION_PRESETS: dict[str, dict[str, str]] = {
    "push-in": {
        "label": "Slow Push-In",
        "prompt": (
            "Slow cinematic camera push-in toward the subject. "
            "Gentle steady motion, no rotation, no shake. "
            "Subject stays centred."
        ),
    },
    "pan-left": {
        "label": "Pan Left",
        "prompt": (
            "Slow gentle horizontal camera pan from right to left. "
            "Smooth steady motion, cinematic, no zoom."
        ),
    },
    "pan-right": {
        "label": "Pan Right",
        "prompt": (
            "Slow gentle horizontal camera pan from left to right. "
            "Smooth steady motion, cinematic, no zoom."
        ),
    },
    "parallax": {
        "label": "Parallax Depth",
        "prompt": (
            "Subtle parallax depth motion. Foreground subject "
            "shifts slightly faster than the background. Cinematic "
            "depth-of-field feel, gentle."
        ),
    },
    "zoom-out": {
        "label": "Zoom Out",
        "prompt": (
            "Slow cinematic zoom out revealing more of the scene. "
            "Steady gentle motion, no pan, no rotation."
        ),
    },
}

_MODEL = "gen4_turbo"  # image_to_video model
_POLL_DEADLINE_S = 600.0
# Bottom-right corner tile sizing for the video overlay.
_PIP_WIDTH_FRAC = 0.28
_PIP_BORDER_PX = 6
_PIP_MARGIN_X = 48
_PIP_MARGIN_Y = 48


@dataclass
class AnimatedPipResult:
    """Returned from `animate_and_compose`."""

    status: str  # "ok" | "failed"
    output_path: Optional[Path] = None
    cache_filename: Optional[str] = None
    duration_s: Optional[float] = None
    task_id: Optional[str] = None
    motion_id: Optional[str] = None
    error: Optional[str] = None
    mock_mode: bool = False


def _headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.runway_api_key}",
        "X-Runway-Version": settings.runway_api_version,
        "Content-Type": "application/json",
    }


def _probe_dims(source: Path) -> Optional[tuple[int, int]]:
    if not is_ffprobe_available():
        return None
    try:
        r = subprocess.run(
            [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height",
                "-of", "csv=p=0",
                str(source),
            ],
            check=True, capture_output=True, text=True, timeout=10,
        )
        parts = (r.stdout or "").strip().split(",")
        if len(parts) >= 2:
            return int(parts[0]), int(parts[1])
    except Exception:
        pass
    return None


def _image_to_data_uri(image_path: Path) -> str:
    """Encode a local image file as a data URI for Runway."""
    suffix = image_path.suffix.lstrip(".").lower()
    media = {
        "png": "image/png",
        "jpg": "image/jpeg",
        "jpeg": "image/jpeg",
        "webp": "image/webp",
    }.get(suffix, "image/png")
    return (
        f"data:{media};base64,"
        + base64.b64encode(image_path.read_bytes()).decode("ascii")
    )


def _create_image_to_video_task(
    *,
    image_uri: str,
    motion_prompt: str,
    settings: Settings,
) -> str:
    """POST /v1/image_to_video, return task id."""
    body = {
        "model": _MODEL,
        "promptText": motion_prompt,
        "promptImage": image_uri,
        "duration": 5,
        "ratio": "1280:720",
    }
    url = f"{settings.runway_api_base}/v1/image_to_video"
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=_headers(settings), json=body)
        if resp.status_code != 200:
            raise RuntimeError(
                f"image_to_video create failed: {resp.status_code} "
                f"{resp.text[:300]}"
            )
        created = resp.json()
    task_id = created.get("id") or created.get("taskId")
    if not task_id:
        raise RuntimeError(f"image_to_video create missing task id: {created}")
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
                    or payload.get("failureCode")
                    or status
                )
                raise RuntimeError(f"image_to_video task {status}: {reason}")
            time.sleep(5)
    if not final:
        raise RuntimeError(
            f"image_to_video task {task_id} timed out after "
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
        raise RuntimeError(
            f"image_to_video task {task_id} produced no output url"
        )
    return out_url


def _download(url: str, target: Path) -> int:
    """Stream `url` to `target`. Returns bytes written."""
    tmp = target.with_suffix(target.suffix + ".tmp")
    size = 0
    try:
        with httpx.stream(
            "GET", url, timeout=120.0, follow_redirects=True,
        ) as resp:
            resp.raise_for_status()
            ctype = (resp.headers.get("content-type") or "").lower()
            if not (
                ctype.startswith("video/")
                or ctype.startswith("application/octet-stream")
            ):
                raise RuntimeError(
                    f"unexpected content-type for animated PiP source: {ctype}"
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


def animate_and_compose(
    *,
    source_video_path: Path,
    pip_image_path: Path,
    campaign_id: str,
    output_id: str,
    motion_id: str,
    settings: Settings,
) -> AnimatedPipResult:
    """Generate an animated PiP clip from `pip_image_path` via Runway
    image_to_video with the chosen motion preset's prompt, then
    ffmpeg-overlay the looped result onto `source_video_path`."""
    preset = MOTION_PRESETS.get(motion_id)
    if not preset:
        return AnimatedPipResult(
            status="failed",
            error=(
                f"unknown motion_id '{motion_id}'. supported: "
                f"{sorted(MOTION_PRESETS.keys())}"
            ),
            mock_mode=settings.runway_mock,
        )
    if not source_video_path.exists():
        return AnimatedPipResult(
            status="failed",
            error=f"source video not found at {source_video_path}",
        )
    if not pip_image_path.exists():
        return AnimatedPipResult(
            status="failed",
            error=f"pip image not found at {pip_image_path}",
        )
    if not is_ffmpeg_available():
        return AnimatedPipResult(status="failed", error="ffmpeg unavailable")

    dims = _probe_dims(source_video_path)
    if not dims:
        return AnimatedPipResult(
            status="failed",
            error="could not probe source video dimensions",
        )
    pip_w = max(160, int(dims[0] * _PIP_WIDTH_FRAC))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    # Cache directory for the intermediate animated PiP clip — kept
    # under data/animated_pip/ so future iterations can lookup-cache
    # by (image, motion) hash if it becomes a cost concern.
    pip_clip_dir = settings.data_path / "animated_pip"
    pip_clip_dir.mkdir(parents=True, exist_ok=True)

    cache_filename = (
        f"{campaign_id}-animpip-{motion_id}-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename
    pip_clip_filename = (
        f"{campaign_id}-pipsrc-{motion_id}-{output_id}-{timestamp}.mp4"
    )
    pip_clip_path = pip_clip_dir / pip_clip_filename

    # Mock mode — skip Runway, copy a copy of the source video as the
    # placeholder PiP so the rest of the pipeline exercises end-to-end.
    if settings.runway_mock:
        try:
            shutil.copyfile(source_video_path, pip_clip_path)
        except Exception as exc:
            return AnimatedPipResult(
                status="failed",
                error=f"mock copy failed: {exc!s}"[:300],
                mock_mode=True,
            )
        task_id = f"mock_animpip_{uuid.uuid4().hex[:8]}"
    else:
        # 1. Generate the animated PiP clip via Runway.
        try:
            image_uri = _image_to_data_uri(pip_image_path)
            task_id = _create_image_to_video_task(
                image_uri=image_uri,
                motion_prompt=preset["prompt"],
                settings=settings,
            )
            logger.info(
                "animated-pip created campaign=%s output=%s motion=%s task=%s",
                campaign_id, output_id, motion_id, task_id,
            )
            out_url = _poll_task(task_id, settings)
            _download(out_url, pip_clip_path)
        except RuntimeError as exc:
            logger.warning(
                "animated-pip generate failed campaign=%s motion=%s: %s",
                campaign_id, motion_id, exc,
            )
            return AnimatedPipResult(
                status="failed",
                error=str(exc)[:300],
                motion_id=motion_id,
            )
        except httpx.HTTPError as exc:
            logger.warning("animated-pip http error: %s", exc)
            return AnimatedPipResult(
                status="failed",
                error=f"http error: {exc!s}"[:300],
                motion_id=motion_id,
            )

    # 2. ffmpeg overlay — looped animated PiP in bottom-right.
    #    Same corner / border as PR FC's static PiP overlay.
    border = _PIP_BORDER_PX
    margin_x = _PIP_MARGIN_X
    margin_y = _PIP_MARGIN_Y
    filter_complex = (
        f"[1:v]scale={pip_w}:-2[pip_scaled];"
        f"[pip_scaled]pad=iw+{2 * border}:ih+{2 * border}:"
        f"{border}:{border}:color=white[pip_bordered];"
        f"[0:v][pip_bordered]overlay=W-w-{margin_x}:H-h-{margin_y}[outv]"
    )
    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(source_video_path),
        # Loop the animated PiP clip infinitely; -shortest caps to
        # the main video's duration.
        "-stream_loop", "-1", "-i", str(pip_clip_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",  # avatar audio
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    logger.info(
        "animated-pip overlay campaign=%s output=%s motion=%s pip_w=%d "
        "pip_src=%s",
        campaign_id, output_id, motion_id, pip_w, pip_clip_path.name,
    )
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=240,
        )
    except subprocess.TimeoutExpired:
        return AnimatedPipResult(
            status="failed",
            error="ffmpeg timed out on overlay",
            motion_id=motion_id,
            task_id=task_id,
        )
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[-300:]
        return AnimatedPipResult(
            status="failed",
            error=f"ffmpeg rc={result.returncode}: {stderr}",
            motion_id=motion_id,
            task_id=task_id,
        )
    if not output_path.exists():
        return AnimatedPipResult(
            status="failed",
            error="ffmpeg succeeded but output missing",
            motion_id=motion_id,
            task_id=task_id,
        )
    duration = probe_duration(output_path)
    logger.info(
        "animated-pip ok campaign=%s output=%s motion=%s bytes=%d "
        "duration=%.2f",
        campaign_id, output_id, motion_id,
        output_path.stat().st_size, duration or 0.0,
    )
    return AnimatedPipResult(
        status="ok",
        output_path=output_path,
        cache_filename=cache_filename,
        duration_s=duration,
        task_id=task_id,
        motion_id=motion_id,
        mock_mode=settings.runway_mock,
    )
