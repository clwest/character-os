"""Picture-in-Picture overlay (PR FC).

Takes a rendered spokesperson ad MP4 + a still image (the campaign's
reference image, or a character portrait fallback) and ffmpeg-
overlays the image in the bottom-right corner with a small white
border. Persistent for the full duration. Pure ffmpeg, no Runway
calls, ~5-15s wall time depending on source length.

The PiP visualizes "what they're pitching" alongside the avatar
talking, transforming a plain talking-head clip into something that
reads more like an actual product ad.

Never raises in normal operation — returns a `PipResult` the router
maps to HTTP responses.
"""
from __future__ import annotations

import logging
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import Settings
from .finisher_service import (
    is_ffmpeg_available,
    is_ffprobe_available,
    probe_duration,
)

logger = logging.getLogger(__name__)

# PiP sizing as a fraction of the source video width. 0.28 gives a
# comfortable "product callout" tile that doesn't dominate the
# avatar's face while still being readable.
_PIP_WIDTH_FRAC = 0.28
# Border around the PiP image (px) — small white edge that helps
# the tile pop against arbitrary video backgrounds.
_PIP_BORDER_PX = 6
# Bottom-right margins (px) measured from the source frame edges.
_PIP_MARGIN_X = 48
_PIP_MARGIN_Y = 48


@dataclass
class PipResult:
    """Returned from `add_pip_overlay`."""

    status: str  # "ok" | "failed"
    output_path: Optional[Path] = None
    cache_filename: Optional[str] = None
    duration_s: Optional[float] = None
    error: Optional[str] = None


def _probe_dims(source: Path) -> Optional[tuple[int, int]]:
    """ffprobe for (width, height). None on failure."""
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


def add_pip_overlay(
    *,
    source_video_path: Path,
    pip_image_path: Path,
    campaign_id: str,
    output_id: str,
    settings: Settings,
) -> PipResult:
    """Overlay `pip_image_path` in the bottom-right of
    `source_video_path`. Pure ffmpeg, no Runway."""
    if not source_video_path.exists():
        return PipResult(
            status="failed",
            error=f"source video not found at {source_video_path}",
        )
    if not pip_image_path.exists():
        return PipResult(
            status="failed",
            error=f"pip image not found at {pip_image_path}",
        )
    if not is_ffmpeg_available():
        return PipResult(status="failed", error="ffmpeg unavailable")

    dims = _probe_dims(source_video_path)
    if not dims:
        return PipResult(
            status="failed",
            error="could not probe source video dimensions",
        )
    pip_w = max(160, int(dims[0] * _PIP_WIDTH_FRAC))

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    cache_filename = (
        f"{campaign_id}-pip-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename

    # Filter graph:
    #   [1:v] = PiP image
    #     → scale to `pip_w` wide (keep aspect via -1)
    #     → pad with a `_PIP_BORDER_PX` white border (acts as a
    #       framed tile that pops against any background)
    #   [0:v][pip_bordered]overlay positions the framed tile at
    #     bottom-right with `_PIP_MARGIN_*` margins.
    border = _PIP_BORDER_PX
    margin_x = _PIP_MARGIN_X
    margin_y = _PIP_MARGIN_Y
    filter_complex = (
        f"[1:v]scale={pip_w}:-2[pip_scaled];"
        f"[pip_scaled]pad=iw+{2 * border}:ih+{2 * border}:"
        f"{border}:{border}:color=white[pip_bordered];"
        f"[0:v][pip_bordered]overlay=W-w-{margin_x}:H-h-{margin_y}"
    )

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(source_video_path),
        "-i", str(pip_image_path),
        "-filter_complex", filter_complex,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "copy",
        "-movflags", "+faststart",
        str(output_path),
    ]
    logger.info(
        "pip ffmpeg campaign=%s output=%s pip_w=%d src=%s pip=%s",
        campaign_id, output_id, pip_w,
        source_video_path.name, pip_image_path.name,
    )
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        return PipResult(status="failed", error="ffmpeg timed out")
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[-300:]
        return PipResult(
            status="failed",
            error=f"ffmpeg rc={result.returncode}: {stderr}",
        )
    if not output_path.exists():
        return PipResult(
            status="failed",
            error="ffmpeg succeeded but output missing",
        )
    duration = probe_duration(output_path)
    logger.info(
        "pip ok campaign=%s output=%s bytes=%d duration=%.2f",
        campaign_id, output_id,
        output_path.stat().st_size, duration or 0.0,
    )
    return PipResult(
        status="ok",
        output_path=output_path,
        cache_filename=cache_filename,
        duration_s=duration,
    )
