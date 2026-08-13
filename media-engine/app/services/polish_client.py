"""Polish pass (PR FB) — ffmpeg-burn finishing layers onto a rendered ad.

Pure ffmpeg, no Runway calls. Takes any rendered ad MP4 + the script
that produced it + character/campaign metadata, and produces a
"polished" variant with:

  - 1.5 s intro card (business name centred on a black frame)
  - body section: captions chunked from the script, bottom-aligned
    drawtext with a translucent box; plus a persistent lower-third
    in the bottom-left (`character_name · business`)
  - 1.5 s outro card ("Learn more" CTA)

All three sections are stitched in one `ffmpeg -filter_complex`
invocation with the concat filter so parameter mismatches between
the lavfi-generated cards and the source MP4 get normalised
automatically.

Caption timing is estimated: the script is split into ~6-word
chunks and the chunks are distributed uniformly across the body
duration. We don't have word-level timings from avatar_videos, so
estimated timing is the only option for this slice. The visual cue
is "what's roughly being said now" not exact word sync.

Never raises in normal operation — returns a `PolishResult` the
router maps to HTTP responses.
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
    _FONT_CANDIDATES,
    _wrap_caption_text,
    is_ffmpeg_available,
    is_ffprobe_available,
    probe_duration,
)

logger = logging.getLogger(__name__)

# Intro / outro card duration (seconds). Short enough that the
# operator doesn't feel padding, long enough to read.
_CARD_DURATION_S = 1.5

# Caption chunking — about 6 short words fits comfortably on a
# single line in a 1280-wide frame at fontsize 44.
_CAPTION_WORDS_PER_CHUNK = 6
_CAPTION_MAX_CHARS = 44

# Lower-third positioning. PR FB-2 — moved to TOP-left and time-gated
# to the first N seconds because the original bottom-left placement
# collided with the bottom-centred caption block (same vertical real
# estate). Introducing the speaker once at the start is enough; we
# don't need to label them for the whole clip.
_LOWER_THIRD_MARGIN_X = 60
_LOWER_THIRD_MARGIN_Y = 60
_LOWER_THIRD_HOLD_S = 4.0

# Intro / outro card text wrapping. drawtext does not auto-wrap;
# anything wider than the frame gets clipped at both edges. Writing
# the text to a textfile and pre-wrapping by character width is the
# only robust fix. PR FB-2.
_CARD_MAX_CHARS = 22
_CARD_INTRO_FONT_SIZE = 64
_CARD_OUTRO_FONT_SIZE = 56


@dataclass
class PolishResult:
    """Returned from `polish_output_video`."""

    status: str  # "ok" | "failed"
    output_path: Optional[Path] = None
    cache_filename: Optional[str] = None
    duration_s: Optional[float] = None
    error: Optional[str] = None


def _resolve_font() -> Optional[str]:
    for f in _FONT_CANDIDATES:
        if Path(f).exists():
            return f
    return None


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


def _split_into_caption_chunks(script: str) -> list[str]:
    """Chunk the script into ~N-word pieces for line-by-line caption
    display. Strips leading punctuation lines like 'Hook:' or '(beat).
    """
    if not script:
        return []
    words = script.split()
    if not words:
        return []
    chunks: list[str] = []
    for i in range(0, len(words), _CAPTION_WORDS_PER_CHUNK):
        chunk = " ".join(words[i:i + _CAPTION_WORDS_PER_CHUNK]).strip()
        if chunk:
            chunks.append(chunk)
    return chunks


def _esc_path(p: Path) -> str:
    """Escape a filesystem path for ffmpeg filter args (only `:`
    needs escaping inside the filter string)."""
    return str(p).replace(":", r"\:")


def polish_output_video(
    *,
    source_video_path: Path,
    campaign_id: str,
    output_id: str,
    character_name: Optional[str],
    business: Optional[str],
    script: Optional[str],
    cta_text: Optional[str],
    settings: Settings,
) -> PolishResult:
    """ffmpeg-burn captions + lower-third + intro/outro cards onto an
    existing rendered MP4. Returns a PolishResult; never raises in
    normal operation."""
    if not source_video_path.exists():
        return PolishResult(
            status="failed",
            error=f"source video not found at {source_video_path}",
        )
    if not is_ffmpeg_available():
        return PolishResult(status="failed", error="ffmpeg unavailable")

    font = _resolve_font()
    if not font:
        return PolishResult(
            status="failed",
            error="no system font available for drawtext",
        )

    body_dur = probe_duration(source_video_path)
    if not body_dur or body_dur <= 0:
        return PolishResult(
            status="failed",
            error=f"could not probe source duration of {source_video_path}",
        )

    dims = _probe_dims(source_video_path)
    if not dims:
        return PolishResult(
            status="failed",
            error="could not probe source video dimensions",
        )
    width, height = dims

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    finished_dir = settings.data_path / "finished"
    finished_dir.mkdir(parents=True, exist_ok=True)
    cache_filename = (
        f"{campaign_id}-polished-{output_id}-{timestamp}.mp4"
    )
    output_path = finished_dir / cache_filename

    # Caption chunking + timing. Uniform distribution across body_dur
    # — we don't have word-level timings from avatar_videos. We pad a
    # small gap (50ms) between chunks so drawtext enable bounds don't
    # overlap by float-rounding.
    chunks = _split_into_caption_chunks(script or "")
    caption_segments: list[tuple[float, float, str]] = []
    if chunks:
        per = body_dur / len(chunks)
        for idx, text in enumerate(chunks):
            start = idx * per
            end = (idx + 1) * per - 0.05
            caption_segments.append((start, max(start + 0.1, end), text))

    # Write each caption chunk to its own textfile (ffmpeg drawtext
    # textfile= is the safest way to handle user text without escape
    # hell on apostrophes, percent signs, etc).
    scratch_files: list[Path] = []
    try:
        for idx, (_, _, text) in enumerate(caption_segments):
            wrapped = _wrap_caption_text(text, _CAPTION_MAX_CHARS)
            if not wrapped:
                continue
            cf = finished_dir / f".{cache_filename}-cap-{idx}.txt"
            cf.write_text(wrapped, encoding="utf-8")
            scratch_files.append(cf)

        # Build the filter graph.
        font_esc = font.replace(":", r"\:")

        # PR FB-2 — intro/outro/lower-third text all go through
        # textfile= so we get free wrapping + escape-safe handling
        # of apostrophes, percent signs, etc. Inline text= would
        # clip on long business names.
        intro_text = _wrap_caption_text(
            business or "Brand", _CARD_MAX_CHARS,
        )
        outro_text = _wrap_caption_text(
            cta_text or "Learn more", _CARD_MAX_CHARS,
        )
        lower_third_text = _wrap_caption_text(
            " · ".join([p for p in (character_name, business) if p])
            or "Spokesperson",
            _CARD_MAX_CHARS,
        )

        intro_file = finished_dir / f".{cache_filename}-intro.txt"
        outro_file = finished_dir / f".{cache_filename}-outro.txt"
        lower_third_file = finished_dir / f".{cache_filename}-lower3.txt"
        intro_file.write_text(intro_text, encoding="utf-8")
        outro_file.write_text(outro_text, encoding="utf-8")
        lower_third_file.write_text(lower_third_text, encoding="utf-8")
        scratch_files.extend([intro_file, outro_file, lower_third_file])

        # Intro card drawtext (centred, wrapped via textfile).
        intro_filter = (
            f"[1:v]drawtext=fontfile='{font_esc}':"
            f"textfile='{_esc_path(intro_file)}':"
            f"fontsize={_CARD_INTRO_FONT_SIZE}:"
            "fontcolor=white:"
            "line_spacing=10:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
            "[intro_v]"
        )

        # Outro card drawtext (centred, wrapped via textfile).
        outro_filter = (
            f"[3:v]drawtext=fontfile='{font_esc}':"
            f"textfile='{_esc_path(outro_file)}':"
            f"fontsize={_CARD_OUTRO_FONT_SIZE}:"
            "fontcolor=white:"
            "line_spacing=10:"
            "x=(w-text_w)/2:y=(h-text_h)/2"
            "[outro_v]"
        )

        # Body filter chain: captions (one drawtext per chunk) + a
        # time-gated lower-third in the TOP-LEFT (the original
        # bottom-left placement collided with the bottom-centre
        # caption block).
        body_drawtexts: list[str] = []
        for seg_idx, (start, end, _) in enumerate(caption_segments):
            cf_path = finished_dir / f".{cache_filename}-cap-{seg_idx}.txt"
            if not cf_path.exists():
                continue
            body_drawtexts.append(
                "drawtext="
                f"fontfile='{font_esc}':"
                f"textfile='{_esc_path(cf_path)}':"
                "fontsize=44:"
                "fontcolor=white:"
                "line_spacing=8:"
                "x=(w-text_w)/2:"
                "y=h-text_h-80:"
                "box=1:"
                "boxcolor=black@0.6:"
                "boxborderw=18:"
                f"enable='between(t\\,{start:.3f}\\,{end:.3f})'"
            )
        # Lower-third — TOP-LEFT, only the first _LOWER_THIRD_HOLD_S
        # seconds. Doesn't overlap captions; introduces the speaker
        # then steps out of the way.
        body_drawtexts.append(
            "drawtext="
            f"fontfile='{font_esc}':"
            f"textfile='{_esc_path(lower_third_file)}':"
            "fontsize=28:"
            "fontcolor=white:"
            "line_spacing=6:"
            f"x={_LOWER_THIRD_MARGIN_X}:"
            f"y={_LOWER_THIRD_MARGIN_Y}:"
            "box=1:"
            "boxcolor=black@0.55:"
            "boxborderw=10:"
            f"enable='between(t\\,0\\,{_LOWER_THIRD_HOLD_S:.2f})'"
        )
        body_filter = (
            "[0:v]" + ",".join(body_drawtexts) + "[body_v]"
        )

        # Concat: [intro_v][2:a][body_v][0:a][outro_v][4:a]concat=n=3:v=1:a=1[v][a]
        concat_filter = (
            "[intro_v][2:a][body_v][0:a][outro_v][4:a]"
            "concat=n=3:v=1:a=1[v][a]"
        )

        filter_complex = ";".join([intro_filter, body_filter, outro_filter, concat_filter])

        cmd = [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(source_video_path),
            "-f", "lavfi", "-i",
            f"color=c=black:s={width}x{height}:r=30:d={_CARD_DURATION_S}",
            "-f", "lavfi", "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=48000:d={_CARD_DURATION_S}",
            "-f", "lavfi", "-i",
            f"color=c=black:s={width}x{height}:r=30:d={_CARD_DURATION_S}",
            "-f", "lavfi", "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=48000:d={_CARD_DURATION_S}",
            "-filter_complex", filter_complex,
            "-map", "[v]",
            "-map", "[a]",
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
            "polish ffmpeg campaign=%s output=%s body=%.2fs captions=%d "
            "dims=%dx%d",
            campaign_id, output_id, body_dur, len(caption_segments),
            width, height,
        )
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=180,
        )
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()[-300:]
            return PolishResult(
                status="failed",
                error=f"ffmpeg rc={result.returncode}: {stderr}",
            )
        if not output_path.exists():
            return PolishResult(
                status="failed",
                error="ffmpeg succeeded but output missing",
            )
        final_dur = probe_duration(output_path)
        logger.info(
            "polish ok campaign=%s output=%s bytes=%d duration=%.2f",
            campaign_id, output_id,
            output_path.stat().st_size, final_dur or 0.0,
        )
        return PolishResult(
            status="ok",
            output_path=output_path,
            cache_filename=cache_filename,
            duration_s=final_dur,
        )
    except subprocess.TimeoutExpired:
        return PolishResult(status="failed", error="ffmpeg timed out")
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("polish unexpected")
        return PolishResult(status="failed", error=f"unexpected: {exc!s}"[:300])
    finally:
        for f in scratch_files:
            try:
                if f.exists():
                    f.unlink()
            except Exception:
                pass
