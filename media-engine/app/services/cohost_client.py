"""Multi-avatar PiP / co-host composite (PR FE).

Takes a MAIN spokesperson ad MP4 + a CO-HOST spokesperson ad MP4
(which can be from any character on any campaign) and ffmpeg-
composites them so:

  - The main video fills the frame at its native dimensions with
    its OWN audio playing throughout.
  - The co-host video shrinks into a TOP-LEFT corner tile (a
    different corner than PR FD's top-right backdrop tile so a
    stacked Backdrop + Co-Host result has both tiles visible).
  - The co-host video loops via `-stream_loop -1` if it's shorter
    than the main; `-shortest` caps the output to the main's
    duration.
  - The co-host's AUDIO is muted in v1 — both speaking
    simultaneously is cacophonous; ducking the co-host under the
    main makes the co-host's mouth move silently to the wrong
    words. Visual co-presence is the win; scripted audio
    alternation is a later slice.

Pure ffmpeg, no Runway calls. Reuses two existing avatar_videos
renders so credit cost is zero.

Result lands as `spokesperson_ad_with_cohost` in `data/finished/`.
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

# Co-host tile sizing — same proportion as the Backdrop foreground
# tile (PR FD used 0.34) for visual consistency when both layers
# stack on the same source ad.
_TILE_WIDTH_FRAC = 0.30
_TILE_BORDER_PX = 6
# TOP-LEFT margins. PR FD puts the avatar-tile in the top-right;
# co-host lands in the top-LEFT so a Backdrop + Co-Host composite
# shows three layers cleanly: main (centre), backdrop (background),
# co-host (top-left).
_TILE_MARGIN_X = 48
_TILE_MARGIN_Y = 48


@dataclass
class CohostResult:
    """Returned from `compose_with_cohost`."""

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


def compose_with_cohost(
    *,
    main_video_path: Path,    # the spokesperson ad (audio source)
    cohost_video_path: Path,  # the co-host avatar clip (muted)
    campaign_id: str,
    output_id: str,
    settings: Settings,
) -> CohostResult:
    """ffmpeg-composite main (full-frame, audio kept) with cohost
    (top-left corner tile, audio muted). Cohost loops if shorter
    than main; output is capped to main's duration via `-shortest`."""
    if not main_video_path.exists():
        return CohostResult(
            status="failed",
            error=f"main video not found at {main_video_path}",
        )
    if not cohost_video_path.exists():
        return CohostResult(
            status="failed",
            error=f"co-host video not found at {cohost_video_path}",
        )
    if not is_ffmpeg_available():
        return CohostResult(status="failed", error="ffmpeg unavailable")

    main_dims = _probe_dims(main_video_path)
    if not main_dims:
        return CohostResult(
            status="failed",
            error="could not probe main video dimensions",
        )
    out_w, _ = main_dims
    tile_w = max(220, int(out_w * _TILE_WIDTH_FRAC))

    main_dur = probe_duration(main_video_path)
    if not main_dur or main_dur <= 0:
        return CohostResult(
            status="failed",
            error="could not probe main video duration",
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    cache_filename = (
        f"{campaign_id}-cohost-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename

    # Filter graph:
    #   [1:v] = co-host (looped via -stream_loop on the input)
    #     → scale to `tile_w` wide (-2 keeps aspect, even-rounded
    #       for libx264).
    #     → pad with a 6px white border so the tile pops against
    #       any main-video colour.
    #   [0:v][cohost_bordered]overlay positions the framed tile at
    #     TOP-LEFT (different corner than PR FD's top-right backdrop
    #     tile so stacked composites read cleanly).
    border = _TILE_BORDER_PX
    margin_x = _TILE_MARGIN_X
    margin_y = _TILE_MARGIN_Y
    filter_complex = (
        f"[1:v]scale={tile_w}:-2[cohost_scaled];"
        f"[cohost_scaled]pad=iw+{2 * border}:ih+{2 * border}:"
        f"{border}:{border}:color=white[cohost_bordered];"
        f"[0:v][cohost_bordered]overlay={margin_x}:{margin_y}[outv]"
    )

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(main_video_path),
        # Loop the co-host infinitely; `-shortest` below caps the
        # output to the main's duration.
        "-stream_loop", "-1", "-i", str(cohost_video_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        # Main audio only. Co-host audio intentionally not mapped
        # so the result plays only the main speaker's voice.
        "-map", "0:a?",
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
        "cohost ffmpeg campaign=%s output=%s tile=%d main_dur=%.2f "
        "main=%s cohost=%s",
        campaign_id, output_id, tile_w, main_dur,
        main_video_path.name, cohost_video_path.name,
    )
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=240,
        )
    except subprocess.TimeoutExpired:
        return CohostResult(status="failed", error="ffmpeg timed out")
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[-300:]
        return CohostResult(
            status="failed",
            error=f"ffmpeg rc={result.returncode}: {stderr}",
        )
    if not output_path.exists():
        return CohostResult(
            status="failed",
            error="ffmpeg succeeded but output missing",
        )
    duration = probe_duration(output_path)
    logger.info(
        "cohost ok campaign=%s output=%s bytes=%d duration=%.2f",
        campaign_id, output_id,
        output_path.stat().st_size, duration or 0.0,
    )
    return CohostResult(
        status="ok",
        output_path=output_path,
        cache_filename=cache_filename,
        duration_s=duration,
    )
