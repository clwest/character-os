"""B-roll cutaway composite (PR FG).

Splices a `cinematic_video` clip INTO the middle of a spokesperson
ad's video timeline. The avatar's AUDIO plays continuously across
the entire output (the cutaway just swaps the video frames for
those few seconds — voice keeps narrating the inset).

Timing defaults (operator-overridable on the route):
  - `insert_start_s` = `source_dur * 0.3` (start the cutaway at ~30%
    into the ad — past the hook, into the pitch)
  - `broll_duration_s` = `min(broll_natural_dur, source_dur * 0.4)`
    (use the b-roll's natural length, capped at 40% of the ad)

The cutaway is automatically skipped if the resulting end-of-cut
would land past the avatar's duration (e.g. very short ads with
very long b-roll).

Pure ffmpeg, no Runway calls. Reuses an existing cinematic_video
output (no fresh generation), so credit cost is zero.

Result lands as `spokesperson_ad_with_broll` in `data/finished/`.
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

# Default placement: start the cutaway 30% into the ad, give it up
# to 40% of the ad's duration (capped by the b-roll's natural
# length). These keep the hook + the CTA untouched.
_DEFAULT_INSERT_START_FRAC = 0.30
_DEFAULT_BROLL_DURATION_FRAC = 0.40
# Minimum b-roll window in seconds. Cutaways shorter than this feel
# like a glitch — better to skip than insert a flicker.
_MIN_BROLL_S = 1.5


@dataclass
class BrollResult:
    """Returned from `compose_with_broll_cutaway`."""

    status: str  # "ok" | "failed"
    output_path: Optional[Path] = None
    cache_filename: Optional[str] = None
    duration_s: Optional[float] = None
    insert_start_s: Optional[float] = None
    broll_duration_s: Optional[float] = None
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


def compose_with_broll_cutaway(
    *,
    source_video_path: Path,    # the spokesperson ad (audio + bookend video)
    broll_video_path: Path,     # the cinematic_video to splice in
    campaign_id: str,
    output_id: str,
    settings: Settings,
    insert_start_s: Optional[float] = None,
    broll_duration_s: Optional[float] = None,
) -> BrollResult:
    """ffmpeg-splice `broll_video_path` into the middle of
    `source_video_path`. Source audio plays continuously."""
    if not source_video_path.exists():
        return BrollResult(
            status="failed",
            error=f"source video not found at {source_video_path}",
        )
    if not broll_video_path.exists():
        return BrollResult(
            status="failed",
            error=f"b-roll video not found at {broll_video_path}",
        )
    if not is_ffmpeg_available():
        return BrollResult(status="failed", error="ffmpeg unavailable")

    source_dims = _probe_dims(source_video_path)
    if not source_dims:
        return BrollResult(
            status="failed",
            error="could not probe source video dimensions",
        )
    out_w, out_h = source_dims

    source_dur = probe_duration(source_video_path)
    broll_natural_dur = probe_duration(broll_video_path)
    if not source_dur or source_dur <= 0:
        return BrollResult(
            status="failed",
            error="could not probe source duration",
        )
    if not broll_natural_dur or broll_natural_dur <= 0:
        return BrollResult(
            status="failed",
            error="could not probe b-roll duration",
        )

    # Resolve timing — sensible defaults if operator didn't supply.
    start = (
        float(insert_start_s)
        if insert_start_s is not None
        else source_dur * _DEFAULT_INSERT_START_FRAC
    )
    requested_dur = (
        float(broll_duration_s)
        if broll_duration_s is not None
        else source_dur * _DEFAULT_BROLL_DURATION_FRAC
    )
    # Clamp duration: ≤ b-roll natural, ≤ remaining source time.
    available_after_start = max(0.0, source_dur - start)
    cut_dur = min(requested_dur, broll_natural_dur, available_after_start)

    if cut_dur < _MIN_BROLL_S:
        return BrollResult(
            status="failed",
            error=(
                f"computed cutaway window too short ({cut_dur:.2f}s; "
                f"min {_MIN_BROLL_S:.1f}s). Source={source_dur:.2f}s, "
                f"b-roll={broll_natural_dur:.2f}s, insert_start={start:.2f}s. "
                f"Try a shorter insert_start or a different b-roll source."
            ),
        )
    end = start + cut_dur
    if start <= 0 or end >= source_dur:
        return BrollResult(
            status="failed",
            error=(
                f"cutaway window [{start:.2f}, {end:.2f}] must be strictly "
                f"INSIDE the source [0, {source_dur:.2f}] so the avatar "
                f"appears before AND after the cut. Tighten the bounds."
            ),
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    cache_filename = (
        f"{campaign_id}-broll-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename

    # Filter graph — three video segments concatenated, source
    # audio kept whole:
    #   [v_pre]  : source[0:start]
    #   [v_cut]  : broll[0:cut_dur] scaled to source dims
    #   [v_post] : source[end:source_dur]
    #   concat n=3 v=1 a=0
    #   audio comes straight from source via `-map 0:a`
    filter_complex = (
        f"[0:v]trim=start=0:end={start:.3f},setpts=PTS-STARTPTS[v_pre];"
        f"[1:v]trim=start=0:end={cut_dur:.3f},setpts=PTS-STARTPTS,"
        f"scale={out_w}:{out_h}:force_original_aspect_ratio=increase,"
        f"crop={out_w}:{out_h},setsar=1[v_cut];"
        f"[0:v]trim=start={end:.3f}:end={source_dur:.3f},"
        f"setpts=PTS-STARTPTS[v_post];"
        f"[v_pre][v_cut][v_post]concat=n=3:v=1:a=0[outv]"
    )

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(source_video_path),
        "-i", str(broll_video_path),
        "-filter_complex", filter_complex,
        "-map", "[outv]",
        # Avatar's full audio plays over the entire output — the
        # cutaway is video-only.
        "-map", "0:a?",
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-b:a", "192k",
        "-movflags", "+faststart",
        str(output_path),
    ]
    logger.info(
        "broll ffmpeg campaign=%s output=%s start=%.2f cut_dur=%.2f "
        "src_dur=%.2f src=%s broll=%s",
        campaign_id, output_id, start, cut_dur, source_dur,
        source_video_path.name, broll_video_path.name,
    )
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=240,
        )
    except subprocess.TimeoutExpired:
        return BrollResult(status="failed", error="ffmpeg timed out")
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[-300:]
        return BrollResult(
            status="failed",
            error=f"ffmpeg rc={result.returncode}: {stderr}",
        )
    if not output_path.exists():
        return BrollResult(
            status="failed",
            error="ffmpeg succeeded but output missing",
        )
    duration = probe_duration(output_path)
    logger.info(
        "broll ok campaign=%s output=%s bytes=%d duration=%.2f "
        "insert=%.2f cut=%.2f",
        campaign_id, output_id, output_path.stat().st_size,
        duration or 0.0, start, cut_dur,
    )
    return BrollResult(
        status="ok",
        output_path=output_path,
        cache_filename=cache_filename,
        duration_s=duration,
        insert_start_s=start,
        broll_duration_s=cut_dur,
    )
