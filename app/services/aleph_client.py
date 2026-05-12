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
import concurrent.futures
import logging
import random
import shutil
import subprocess
import tempfile
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

# PR FA-2 — Aleph `gen4_aleph` has a hard ~5s output cap regardless of
# source length (validated against the OpenAPI spec; there is no
# duration field on the request body). Sources longer than this get
# chunked: ffmpeg split → parallel remix → ffmpeg concat.
_ALEPH_CHUNK_SECONDS = 5
# Anything above this triggers the chunked path. Below it we just
# single-fire and accept that ~5s clips don't need splitting.
_CHUNK_THRESHOLD_S = 5.5
# Throttle parallel chunk fires so we're not abusive toward Runway
# in case of a 60-second source (12 chunks). 4 is comfortable for
# the dev tier; can be tuned via env later if needed.
_PARALLEL_CHUNKS = 4

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
    *,
    video_uri: str,
    prompt: str,
    settings: Settings,
    seed: Optional[int] = None,
) -> str:
    """POST /v1/video_to_video, return task id. When chunking a long
    source, pass the same `seed` across every chunk so the visual
    style stays coherent at chunk boundaries (per Runway's docs:
    'Using the same seed integer for an identical request will
    produce similar results')."""
    body: dict = {
        "model": _MODEL,
        "videoUri": video_uri,
        "promptText": prompt,
    }
    if seed is not None:
        body["seed"] = int(seed)
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


def _split_into_chunks(
    source: Path, chunk_seconds: int, scratch_dir: Path,
) -> list[Path]:
    """ffmpeg-split `source` into N-second chunks in `scratch_dir`.

    Re-encodes (no `-c copy`) so cuts land at EXACT chunk_seconds
    boundaries rather than the nearest keyframe. Aleph truncates
    any input longer than ~5s to 5s of output, so keyframe-aligned
    8s chunks would still get truncated to 5s by Aleph — defeating
    the chunker. `-force_key_frames` + `libx264 -preset fast` gives
    us precise cuts with modest CPU cost.

    Returns the sorted list of chunk paths.
    """
    chunk_glob = scratch_dir / "chunk-%03d.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-i", str(source),
            "-c:v", "libx264",
            "-preset", "fast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "128k",
            "-force_key_frames", f"expr:gte(t,n_forced*{chunk_seconds})",
            "-map", "0",
            "-f", "segment",
            "-segment_time", str(chunk_seconds),
            "-reset_timestamps", "1",
            str(chunk_glob),
        ],
        check=True, capture_output=True, text=True, timeout=120,
    )
    chunks = sorted(scratch_dir.glob("chunk-*.mp4"))
    if not chunks:
        raise AlephError(f"ffmpeg segment produced no chunks for {source}")
    return chunks


def _concat_chunks(chunk_paths: list[Path], target: Path) -> None:
    """ffmpeg-concat the in-order list of MP4 chunks into one MP4.

    Uses the concat demuxer with stream copy — no re-encode, so
    chunk-level encoding artefacts are preserved (which is fine,
    because all chunks were produced by the same Aleph model with
    the same seed; their encoding parameters are aligned).
    """
    list_file = target.parent / f"{target.stem}-concat-list.txt"
    try:
        list_file.write_text(
            "\n".join(f"file '{p.resolve()}'" for p in chunk_paths) + "\n"
        )
        subprocess.run(
            [
                "ffmpeg", "-y", "-loglevel", "error",
                "-f", "concat",
                "-safe", "0",
                "-i", str(list_file),
                "-c", "copy",
                "-movflags", "+faststart",
                str(target),
            ],
            check=True, capture_output=True, text=True, timeout=120,
        )
    finally:
        try:
            list_file.unlink()
        except Exception:
            pass


def _remix_single_clip(
    *,
    source_path: Path,
    prompt: str,
    seed: Optional[int],
    target_path: Path,
    settings: Settings,
) -> tuple[str, int]:
    """End-to-end Aleph fire for ONE clip: read bytes → POST → poll →
    download to `target_path`. Returns (task_id, bytes_written).

    Called once for the un-chunked path and N times (in parallel) for
    the chunked path.
    """
    clip_bytes = source_path.read_bytes()
    if len(clip_bytes) > _MAX_SOURCE_BYTES:
        raise AlephError(
            f"clip {source_path.name} is {len(clip_bytes):,} bytes; "
            f"exceeds the {_MAX_SOURCE_BYTES // (1024 * 1024)}MB cap"
        )
    video_uri = (
        "data:video/mp4;base64,"
        + base64.b64encode(clip_bytes).decode("ascii")
    )
    task_id = _create_task(
        video_uri=video_uri,
        prompt=prompt,
        settings=settings,
        seed=seed,
    )
    out_url = _poll_task(task_id, settings)
    bytes_written = _download(out_url, target_path)
    return task_id, bytes_written


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

    # Real mode. Branch on source duration: if it's ≤ the chunk
    # threshold, single-fire (Aleph handles short clips fine). If
    # longer, chunk → parallel remix → concat so we cover the whole
    # source instead of getting truncated to ~5s.
    source_duration = _ffprobe_duration(source_video_path)
    use_chunking = (
        source_duration is not None and source_duration > _CHUNK_THRESHOLD_S
    )
    # One seed per remix invocation, reused across every chunk so the
    # visual style stays coherent at chunk boundaries.
    invocation_seed = random.randrange(0, 2**32)

    try:
        if not use_chunking:
            # Single-fire path. Either the source is short enough or
            # the duration probe failed (be conservative + skip the
            # chunker rather than guessing wrong).
            task_id, bytes_written = _remix_single_clip(
                source_path=source_video_path,
                prompt=preset["prompt"],
                seed=invocation_seed,
                target_path=output_path,
                settings=settings,
            )
            logger.info(
                "remix single-fire campaign=%s output=%s style=%s "
                "source_dur=%s seed=%d task=%s bytes=%d",
                campaign_id, output_id, style_id,
                source_duration, invocation_seed, task_id, bytes_written,
            )
            duration = _ffprobe_duration(output_path)
            logger.info(
                "remix ok campaign=%s output=%s style=%s bytes=%d duration=%.2f",
                campaign_id, output_id, style_id,
                bytes_written, duration or 0.0,
            )
            return RemixResult(
                status="ok",
                output_path=output_path,
                cache_filename=cache_filename,
                duration_s=duration,
                task_id=task_id,
            )

        # Chunked path. ffmpeg-split → parallel remix → ffmpeg-concat.
        with tempfile.TemporaryDirectory(prefix="aleph-chunks-") as tmpd:
            scratch = Path(tmpd)
            chunks = _split_into_chunks(
                source_video_path, _ALEPH_CHUNK_SECONDS, scratch,
            )
            logger.info(
                "remix chunked campaign=%s output=%s style=%s "
                "source_dur=%.2fs chunks=%d seed=%d",
                campaign_id, output_id, style_id,
                source_duration, len(chunks), invocation_seed,
            )

            # Per-chunk output filenames live in the scratch dir so
            # cleanup is automatic when the with-block exits.
            chunk_outputs: list[Path] = [
                scratch / f"remix-out-{idx:03d}.mp4"
                for idx in range(len(chunks))
            ]

            errors: list[str] = []
            task_ids: list[str] = ["" for _ in chunks]

            def _fire_one(idx: int) -> None:
                try:
                    tid, _ = _remix_single_clip(
                        source_path=chunks[idx],
                        prompt=preset["prompt"],
                        seed=invocation_seed,
                        target_path=chunk_outputs[idx],
                        settings=settings,
                    )
                    task_ids[idx] = tid
                    logger.info(
                        "remix chunk %d/%d ok campaign=%s task=%s",
                        idx + 1, len(chunks), campaign_id, tid,
                    )
                except Exception as exc:
                    errors.append(f"chunk {idx + 1}/{len(chunks)}: {exc!s}")
                    logger.warning(
                        "remix chunk %d/%d failed campaign=%s: %s",
                        idx + 1, len(chunks), campaign_id, exc,
                    )

            # Fire all chunks in parallel (bounded by _PARALLEL_CHUNKS).
            # Total wall time ≈ slowest_chunk_duration + a small
            # scheduling overhead; vastly better than sequential.
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(_PARALLEL_CHUNKS, len(chunks)),
            ) as pool:
                list(pool.map(_fire_one, range(len(chunks))))

            if errors:
                return RemixResult(
                    status="failed",
                    error=(
                        f"{len(errors)}/{len(chunks)} chunks failed: "
                        + "; ".join(errors)
                    )[:300],
                )

            # Concat in order. ffmpeg `-c copy` so no re-encode.
            _concat_chunks(chunk_outputs, output_path)

        final_duration = _ffprobe_duration(output_path)
        total_bytes = output_path.stat().st_size
        # Use the first chunk's task id as the canonical task_id on
        # the OutputRecord — the others are recorded in the log.
        canonical_task_id = task_ids[0] if task_ids else None
        logger.info(
            "remix ok (chunked) campaign=%s output=%s style=%s "
            "chunks=%d bytes=%d duration=%.2f",
            campaign_id, output_id, style_id,
            len(task_ids), total_bytes, final_duration or 0.0,
        )
        return RemixResult(
            status="ok",
            output_path=output_path,
            cache_filename=cache_filename,
            duration_s=final_duration,
            task_id=canonical_task_id,
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
    except subprocess.CalledProcessError as exc:
        stderr = (exc.stderr or "").strip()[:300] if exc.stderr else ""
        logger.warning(
            "remix ffmpeg failed campaign=%s output=%s err=%s",
            campaign_id, output_id, stderr,
        )
        return RemixResult(
            status="failed",
            error=f"ffmpeg failed: {stderr}"[:300],
        )
    except Exception as exc:  # pragma: no cover — defensive
        logger.exception("remix unexpected")
        return RemixResult(status="failed", error=f"unexpected: {exc!s}"[:300])
