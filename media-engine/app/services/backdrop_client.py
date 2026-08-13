"""Reverse-PiP / cinematic-backdrop composite (PR FD).

Takes a rendered spokesperson ad MP4 + an existing `cinematic_video`
output and composites them so:

  - The cinematic clip fills the frame as the BACKGROUND
    (cover-scaled + cropped to the ad's dimensions, looped to match
    the ad's duration).
  - The spokesperson ad is shrunk into a TOP-RIGHT corner tile with
    a thin white border.
  - The spokesperson ad's audio is preserved (cinematic clips are
    silent — the `image_to_video` pipeline doesn't produce audio).

Pure ffmpeg, no Runway calls. Reuses two existing campaign outputs,
so no credit burn even at the first ship.

Result lands as `spokesperson_ad_with_backdrop` in `data/finished/`.
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

# Foreground tile sizing as a fraction of the output width. Larger
# than the PiP image overlay (PR FC used 0.28) because the avatar is
# now the SECONDARY visual element and needs to be readable — but
# not so large that the background gets crowded.
_TILE_WIDTH_FRAC = 0.34
_TILE_BORDER_PX = 6
_TILE_MARGIN_X = 48
_TILE_MARGIN_Y = 48


@dataclass
class BackdropResult:
    """Returned from `compose_with_backdrop`."""

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


def compose_with_backdrop(
    *,
    foreground_video_path: Path,  # the spokesperson ad (with audio)
    backdrop_video_path: Path,    # the cinematic_video (silent)
    campaign_id: str,
    output_id: str,
    settings: Settings,
) -> BackdropResult:
    """ffmpeg-composite foreground (corner tile) over backdrop (full
    frame, looped). Output dims match the foreground source so the
    avatar stays sharp at its native rendered resolution."""
    if not foreground_video_path.exists():
        return BackdropResult(
            status="failed",
            error=f"foreground video not found at {foreground_video_path}",
        )
    if not backdrop_video_path.exists():
        return BackdropResult(
            status="failed",
            error=f"backdrop video not found at {backdrop_video_path}",
        )
    if not is_ffmpeg_available():
        return BackdropResult(status="failed", error="ffmpeg unavailable")

    fg_dims = _probe_dims(foreground_video_path)
    if not fg_dims:
        return BackdropResult(
            status="failed",
            error="could not probe foreground dimensions",
        )
    out_w, out_h = fg_dims
    tile_w = max(240, int(out_w * _TILE_WIDTH_FRAC))

    fg_dur = probe_duration(foreground_video_path)
    if not fg_dur or fg_dur <= 0:
        return BackdropResult(
            status="failed",
            error="could not probe foreground duration",
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    cache_filename = (
        f"{campaign_id}-backdrop-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename

    # Filter graph:
    #   [1:v] = backdrop video (looped via -stream_loop on the input)
    #     → scale to cover the output dims (force_original_aspect_ratio
    #       =increase), then crop to exact dims so we end up at out_w x
    #       out_h without letterbox.
    #     → setsar=1 so downstream players don't apply a stretch hint.
    #   [0:v] = foreground (the avatar ad)
    #     → scale to `tile_w` wide (-2 keeps aspect, even-rounded for
    #       libx264).
    #     → pad with a thin white border so the tile pops against any
    #       backdrop colour.
    #   [bg][fg_bordered]overlay places the framed tile at TOP-right
    #     (a different corner than PR FC's bottom-right, since the
    #     backdrop will often have action in the centre/bottom).
    border = _TILE_BORDER_PX
    margin_x = _TILE_MARGIN_X
    margin_y = _TILE_MARGIN_Y
    filter_complex = (
        f"[1:v]scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},setsar=1[bg];"
        f"[0:v]scale={tile_w}:-2[fg_scaled];"
        f"[fg_scaled]pad=iw+{2 * border}:ih+{2 * border}:"
        f"{border}:{border}:color=white[fg_bordered];"
        f"[bg][fg_bordered]overlay=W-w-{margin_x}:{margin_y}[outv]"
    )

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(foreground_video_path),
        # Loop the backdrop infinitely (`-1`); `-shortest` below caps
        # the output to the foreground's duration.
        "-stream_loop", "-1", "-i", str(backdrop_video_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        "-map", "0:a?",  # foreground audio (avatar's voice); ? in
                          # case the source somehow has no audio.
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
        "backdrop ffmpeg campaign=%s output=%s out=%dx%d tile=%d "
        "fg_dur=%.2f fg=%s bg=%s",
        campaign_id, output_id, out_w, out_h, tile_w, fg_dur,
        foreground_video_path.name, backdrop_video_path.name,
    )
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=240,
        )
    except subprocess.TimeoutExpired:
        return BackdropResult(status="failed", error="ffmpeg timed out")
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[-300:]
        return BackdropResult(
            status="failed",
            error=f"ffmpeg rc={result.returncode}: {stderr}",
        )
    if not output_path.exists():
        return BackdropResult(
            status="failed",
            error="ffmpeg succeeded but output missing",
        )
    duration = probe_duration(output_path)
    logger.info(
        "backdrop ok campaign=%s output=%s bytes=%d duration=%.2f",
        campaign_id, output_id,
        output_path.stat().st_size, duration or 0.0,
    )
    return BackdropResult(
        status="ok",
        output_path=output_path,
        cache_filename=cache_filename,
        duration_s=duration,
    )
