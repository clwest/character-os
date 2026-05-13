"""Music bed mixer (PR FF).

Takes a rendered spokesperson ad MP4 + a music bed audio file from
`backend/data/audio_beds/` and ffmpeg-mixes the bed at ~-18 dB under
the avatar's voice. Bed is looped if shorter than the ad,
truncated if longer.

Pure ffmpeg, no Runway calls, no credits. ~5-15s wall time.

Why -18 dB: standard broadcast practice for music-under-dialogue.
Voice stays clearly intelligible; bed provides emotional support
without competing. -18 dB ≈ volume=0.13 on linear ffmpeg scale.

Result lands as `spokesperson_ad_with_music` in `data/finished/`.
"""
from __future__ import annotations

import logging
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from ..config import Settings
from .finisher_service import is_ffmpeg_available, probe_duration

logger = logging.getLogger(__name__)

# Bed mix level under the avatar's voice (linear amplitude scale —
# 0.13 ≈ -18 dB). Tunable if the operator wants a louder/quieter
# bed; -18 dB is the broadcast-standard sweet spot.
_BED_LEVEL = 0.13

# Accepted bed file extensions. ffmpeg can mix anything but we keep
# the picker tight and predictable.
_BED_EXTS: tuple[str, ...] = (".mp3", ".wav", ".m4a", ".aac", ".ogg", ".flac")


@dataclass
class MusicBedResult:
    """Returned from `mix_music_bed`."""

    status: str  # "ok" | "failed"
    output_path: Optional[Path] = None
    cache_filename: Optional[str] = None
    duration_s: Optional[float] = None
    error: Optional[str] = None


def audio_beds_dir(settings: Settings) -> Path:
    """Canonical location for music bed files.

    The directory is created if missing. Lives under
    `backend/data/audio_beds/` (gitignored via `data/`).
    """
    d = settings.data_path / "audio_beds"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _humanize_bed_id(bed_id: str) -> str:
    """`upbeat-acoustic` → `Upbeat Acoustic`. Used for picker labels
    so the operator's filename becomes a readable display name
    automatically."""
    cleaned = re.sub(r"[_-]+", " ", bed_id).strip()
    return " ".join(part.capitalize() for part in cleaned.split())


def list_beds(settings: Settings) -> list[dict]:
    """Return the available music beds as picker-ready dicts.

    Each entry: `{id, label, filename, duration_s, bytes}`. `id` is
    the filename stem (no extension); the route accepts that as the
    `bed_id` body field.
    """
    out: list[dict] = []
    bed_dir = audio_beds_dir(settings)
    for path in sorted(bed_dir.iterdir()):
        if not path.is_file():
            continue
        if path.suffix.lower() not in _BED_EXTS:
            continue
        try:
            size = path.stat().st_size
        except OSError:
            continue
        out.append(
            {
                "id": path.stem,
                "label": _humanize_bed_id(path.stem),
                "filename": path.name,
                "duration_s": probe_duration(path),
                "bytes": size,
            }
        )
    return out


def find_bed_path(settings: Settings, bed_id: str) -> Optional[Path]:
    """Resolve a bed `id` (filename stem) to its on-disk path. None
    when no file matches across the accepted extensions."""
    bed_dir = audio_beds_dir(settings)
    for ext in _BED_EXTS:
        candidate = bed_dir / f"{bed_id}{ext}"
        if candidate.exists():
            return candidate
    return None


def mix_music_bed(
    *,
    source_video_path: Path,
    bed_path: Path,
    campaign_id: str,
    output_id: str,
    settings: Settings,
    bed_level: float = _BED_LEVEL,
) -> MusicBedResult:
    """ffmpeg-mix a music bed under the avatar's voice. Bed loops if
    shorter than the ad; output is capped to the ad's duration."""
    if not source_video_path.exists():
        return MusicBedResult(
            status="failed",
            error=f"source video not found at {source_video_path}",
        )
    if not bed_path.exists():
        return MusicBedResult(
            status="failed",
            error=f"music bed not found at {bed_path}",
        )
    if not is_ffmpeg_available():
        return MusicBedResult(status="failed", error="ffmpeg unavailable")

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    cache_filename = (
        f"{campaign_id}-music-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename

    # Filter graph:
    #   [1:a]loudnorm=I=-16:TP=-1.5,volume=<level>,aloop=...  → ducked, looping bed
    #   [0:a][bed]amix=inputs=2:duration=first:normalize=0[outa]
    #
    # `loudnorm` (single-pass): normalises the bed to a known
    # integrated loudness target (-16 LUFS, broadcast-style) BEFORE
    # the operator's volume scaling. Without this, beds at vastly
    # different source levels (a quiet generated sine drone vs a
    # mastered pop track) would behave wildly differently for the
    # same `bed_level` slider value — the quiet ones inaudible, the
    # loud ones overpowering. With normalisation, the slider is
    # consistent across any uploaded MP3.
    #
    # `aloop=loop=-1` infinitely loops; `size=` is the number of
    # samples per loop body (we use a large value so short beds
    # tile without seam pops).
    #
    # `duration=first` means the mix runs as long as the FIRST input
    # (the avatar audio) — bed is truncated.
    #
    # **`normalize=0` on amix is critical**: amix defaults to dividing
    # each input by the number of inputs (so a 2-input mix halves both
    # — a -6 dB drop on the avatar voice). With normalize=0 the
    # filter ADDS without scaling, so the avatar's voice stays at
    # full source level and the already-ducked bed adds on top.
    bed_level_clamped = max(0.0, min(2.0, float(bed_level)))
    filter_complex = (
        f"[1:a]loudnorm=I=-16:TP=-1.5,"
        f"volume={bed_level_clamped:.3f},"
        f"aloop=loop=-1:size=2147483647[bed];"
        f"[0:a][bed]amix=inputs=2:duration=first:normalize=0[outa]"
    )

    cmd = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-i", str(source_video_path),
        "-i", str(bed_path),
        "-filter_complex", filter_complex,
        "-map", "0:v",
        "-map", "[outa]",
        # Video stream copied — no re-encode of the visual content.
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-shortest",
        "-movflags", "+faststart",
        str(output_path),
    ]
    logger.info(
        "music-bed ffmpeg campaign=%s output=%s bed=%s level=%.3f src=%s",
        campaign_id, output_id, bed_path.name, bed_level_clamped,
        source_video_path.name,
    )
    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )
    except subprocess.TimeoutExpired:
        return MusicBedResult(status="failed", error="ffmpeg timed out")
    if result.returncode != 0:
        stderr = (result.stderr or "").strip()[-300:]
        return MusicBedResult(
            status="failed",
            error=f"ffmpeg rc={result.returncode}: {stderr}",
        )
    if not output_path.exists():
        return MusicBedResult(
            status="failed",
            error="ffmpeg succeeded but output missing",
        )
    duration = probe_duration(output_path)
    logger.info(
        "music-bed ok campaign=%s output=%s bytes=%d duration=%.2f",
        campaign_id, output_id,
        output_path.stat().st_size, duration or 0.0,
    )
    return MusicBedResult(
        status="ok",
        output_path=output_path,
        cache_filename=cache_filename,
        duration_s=duration,
    )
