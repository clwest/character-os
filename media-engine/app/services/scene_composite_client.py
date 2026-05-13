"""Scene composite generator (PR FI) — generate-and-composite in one call.

Operator types a scene prompt + picks an image source. Backend:
  1. Fires Runway `image_to_video` with `<motion preset> + <operator
     scene prompt>` against the chosen source image (avatar portrait
     OR campaign reference OR uploaded override).
  2. Polls to terminal (600s deadline).
  3. Downloads the result to `data/videos/` as a per-output file —
     same shape as a regular cinematic_video output, so the operator
     can reuse it later via the Backdrop or B-Roll pickers.
  4. ffmpeg-composites the scene as the background of the avatar
     ad with the spokesperson shrunk to a top-right corner tile
     (PR FD pattern). Audio stays the avatar's.

Reuses `backdrop_client.compose_with_backdrop` for the compositing
step so the visual layout is identical to picking-existing-cinematic.

Lands TWO OutputRecords:
  - `cinematic_video` (the generated scene — reusable)
  - `spokesperson_ad_with_backdrop` (the composite — final deliverable)
"""
from __future__ import annotations

import base64
import logging
import shutil
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import httpx

from ..config import Settings
from .animated_pip_client import MOTION_PRESETS
from .backdrop_client import compose_with_backdrop
from .finisher_service import is_ffmpeg_available, probe_duration

logger = logging.getLogger(__name__)

_MODEL = "gen4_turbo"
_POLL_DEADLINE_S = 600.0


@dataclass
class SceneCompositeResult:
    """Returned from `generate_scene_and_composite`."""

    status: str  # "ok" | "failed"
    composite_path: Optional[Path] = None
    composite_filename: Optional[str] = None
    composite_duration_s: Optional[float] = None
    scene_path: Optional[Path] = None
    scene_filename: Optional[str] = None
    scene_duration_s: Optional[float] = None
    task_id: Optional[str] = None
    error: Optional[str] = None
    mock_mode: bool = False


def _headers(settings: Settings) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {settings.runway_api_key}",
        "X-Runway-Version": settings.runway_api_version,
        "Content-Type": "application/json",
    }


def _image_to_data_uri(image_path: Path) -> str:
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


def _compose_prompt(scene_prompt: str, motion_id: Optional[str]) -> str:
    """Combine operator's scene prompt with optional motion-style
    suffix. Motion preset prompts are short cinematographic cues
    (push-in / pan / parallax / zoom-out); the operator's scene
    prompt describes the WHAT. Concatenating gives Runway both."""
    scene = (scene_prompt or "").strip()
    if not scene:
        scene = "A cinematic scene"
    if motion_id and motion_id in MOTION_PRESETS:
        motion = MOTION_PRESETS[motion_id]["prompt"]
        return f"{scene}. {motion}"
    return scene


def _create_image_to_video_task(
    *, image_uri: str, prompt: str, settings: Settings,
) -> str:
    body = {
        "model": _MODEL,
        "promptText": prompt,
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
                    f"unexpected content-type for scene download: {ctype}"
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


def generate_scene_and_composite(
    *,
    source_video_path: Path,  # the avatar ad (corner foreground)
    pip_image_path: Path,     # source for image_to_video
    scene_prompt: str,
    motion_id: Optional[str],
    campaign_id: str,
    output_id: str,
    settings: Settings,
) -> SceneCompositeResult:
    """Fire image_to_video with the operator's scene prompt + the
    chosen source image, then composite the result as the backdrop
    of the avatar ad."""
    if not source_video_path.exists():
        return SceneCompositeResult(
            status="failed",
            error=f"source video not found at {source_video_path}",
        )
    if not pip_image_path.exists():
        return SceneCompositeResult(
            status="failed",
            error=f"source image not found at {pip_image_path}",
        )
    if not is_ffmpeg_available():
        return SceneCompositeResult(
            status="failed",
            error="ffmpeg unavailable",
        )
    if not (scene_prompt or "").strip():
        return SceneCompositeResult(
            status="failed",
            error="scene_prompt is required",
        )

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d-%H%M%S")
    videos_dir = settings.data_path / "videos"
    videos_dir.mkdir(parents=True, exist_ok=True)
    # Generated scene gets a per-output cache filename so it's
    # reusable as a regular cinematic_video OutputRecord.
    scene_output_id = uuid.uuid4().hex[:12]
    scene_filename = (
        f"{campaign_id}-scene-{scene_output_id}-{timestamp}.mp4"
    )
    scene_path = videos_dir / scene_filename

    # Mock mode — skip Runway, copy the source video as the
    # placeholder scene so the rest of the pipeline exercises
    # end-to-end without keys.
    task_id: Optional[str]
    if settings.runway_mock:
        try:
            shutil.copyfile(source_video_path, scene_path)
        except Exception as exc:
            return SceneCompositeResult(
                status="failed",
                error=f"mock copy failed: {exc!s}"[:300],
                mock_mode=True,
            )
        task_id = f"mock_scene_{uuid.uuid4().hex[:8]}"
    else:
        try:
            image_uri = _image_to_data_uri(pip_image_path)
            full_prompt = _compose_prompt(scene_prompt, motion_id)
            task_id = _create_image_to_video_task(
                image_uri=image_uri,
                prompt=full_prompt,
                settings=settings,
            )
            logger.info(
                "scene-composite created campaign=%s output=%s task=%s "
                "motion=%s prompt=%r",
                campaign_id, output_id, task_id, motion_id,
                full_prompt[:120],
            )
            out_url = _poll_task(task_id, settings)
            _download(out_url, scene_path)
        except RuntimeError as exc:
            logger.warning(
                "scene-composite generate failed campaign=%s: %s",
                campaign_id, exc,
            )
            return SceneCompositeResult(
                status="failed",
                error=str(exc)[:300],
            )
        except httpx.HTTPError as exc:
            logger.warning("scene-composite http error: %s", exc)
            return SceneCompositeResult(
                status="failed",
                error=f"http error: {exc!s}"[:300],
            )

    scene_dur = probe_duration(scene_path)

    # ffmpeg composite — reuse backdrop_client so the result is
    # visually identical to picking-existing-cinematic via PR FD.
    composite_result = compose_with_backdrop(
        foreground_video_path=source_video_path,
        backdrop_video_path=scene_path,
        campaign_id=campaign_id,
        output_id=output_id,
        settings=settings,
    )
    if composite_result.status != "ok" or not composite_result.cache_filename:
        return SceneCompositeResult(
            status="failed",
            error=(
                composite_result.error
                or "compose_with_backdrop returned an empty result"
            )[:300],
            scene_path=scene_path,
            scene_filename=scene_filename,
            scene_duration_s=scene_dur,
            task_id=task_id,
        )

    logger.info(
        "scene-composite ok campaign=%s output=%s task=%s "
        "scene=%s composite=%s",
        campaign_id, output_id, task_id,
        scene_filename, composite_result.cache_filename,
    )
    return SceneCompositeResult(
        status="ok",
        composite_path=composite_result.output_path,
        composite_filename=composite_result.cache_filename,
        composite_duration_s=composite_result.duration_s,
        scene_path=scene_path,
        scene_filename=scene_filename,
        scene_duration_s=scene_dur,
        task_id=task_id,
        mock_mode=settings.runway_mock,
    )
