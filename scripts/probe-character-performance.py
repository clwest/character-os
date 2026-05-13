#!/usr/bin/env python3
"""Probe: does /v1/character_performance (Act-Two) work for us?

One-shot Runway call to validate the Act-Two endpoint shape against
a real character + operator performance video. Discovers/documents:

  1. Whether `act_two` accepts a data URI for `character.uri` when
     `character.type == "image"` (our portraits are cached locally).
  2. Whether it accepts a data URI for the operator's performance
     video on `reference.uri` (or if we need to upload to a real URL).
  3. What the output looks like — duration, format, lip-sync vs.
     full-body emotion, how much of the operator's expression makes
     it through to the rendered avatar.

Shape discovered via empty-body 400-probing on 2026-05-12:

    {
      "model": "act_two",
      "character": { "type": "image"|"video", "uri": <URL or data URI> },
      "reference": { "type": "video", "uri": <URL or data URI> }
    }

Both uris get fetched server-side — so data URIs work but real URLs
must be accessible.

Safety:
  - Refuses to fire without --yes-fire (dry-run by default).
  - Refuses to fire when RUNWAY_API_KEY is missing.
  - Reads character record from backend/data/characters.json
    directly — no app boot.
  - Writes full request + response log to /tmp/probe-act-two-<ts>.log.
  - Output MP4 saved to ~/Desktop/Donkey Betz Videos/ per the
    operator's preference (memory: feedback_artifact_storage.md).

Usage:
  # Dry-run — no credits burned, just shows planned body shape:
  python scripts/probe-character-performance.py \\
      --character-id ffc0dc094a92 \\
      --performance-video ~/Desktop/my-performance.mov

  # Real fire — burns ~500 credits (conservative estimate):
  python scripts/probe-character-performance.py \\
      --character-id ffc0dc094a92 \\
      --performance-video ~/Desktop/my-performance.mov \\
      --yes-fire

  # Drive a character video instead of a still image:
  python scripts/probe-character-performance.py \\
      --character-video ~/path/to/existing-riggs-clip.mp4 \\
      --performance-video ~/Desktop/my-performance.mov \\
      --yes-fire
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import subprocess
import sys
import tempfile
import time
from datetime import datetime
from pathlib import Path

import httpx


REPO_ROOT = Path(__file__).resolve().parent.parent
CHARACTERS_JSON = REPO_ROOT / "backend" / "data" / "characters.json"
ARTIFACT_DIR = Path.home() / "Desktop" / "Donkey Betz Videos"
LOG_PATH = Path(tempfile.gettempdir()) / (
    f"probe-act-two-{datetime.now().strftime('%Y%m%d-%H%M%S')}.log"
)


def setup_logging() -> logging.Logger:
    logger = logging.getLogger("act-two-probe")
    logger.setLevel(logging.INFO)
    fh = logging.FileHandler(LOG_PATH)
    fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
    logger.addHandler(fh)
    sh = logging.StreamHandler()
    sh.setFormatter(logging.Formatter("%(message)s"))
    logger.addHandler(sh)
    return logger


def load_character(character_id: str) -> dict:
    if not CHARACTERS_JSON.exists():
        raise SystemExit(f"characters.json not found at {CHARACTERS_JSON}")
    records = json.loads(CHARACTERS_JSON.read_text())
    for rec in records:
        if rec.get("id") == character_id:
            return rec
    raise SystemExit(
        f"character {character_id!r} not in characters.json. "
        f"Available ids: {[r.get('id') for r in records]}"
    )


def portrait_path_for(character_id: str) -> Path:
    return REPO_ROOT / "backend" / "data" / "characters" / f"{character_id}-portrait.png"


def ffprobe_duration_secs(path: Path) -> float:
    out = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(path),
        ],
        check=True, capture_output=True, text=True,
    )
    return float(out.stdout.strip() or 0.0)


def to_data_uri(path: Path, mime: str) -> str:
    raw = path.read_bytes()
    b64 = base64.b64encode(raw).decode("ascii")
    return f"data:{mime};base64,{b64}"


def post_character_performance(
    api_base: str,
    api_key: str,
    api_version: str,
    body: dict,
    logger: logging.Logger,
) -> str:
    url = f"{api_base}/v1/character_performance"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Runway-Version": api_version,
        "Content-Type": "application/json",
    }
    with httpx.Client(timeout=60.0) as client:
        resp = client.post(url, headers=headers, json=body)
    logger.info("POST %s -> %s", url, resp.status_code)
    logger.info("response body (truncated): %s", resp.text[:600])
    if resp.status_code != 200:
        raise SystemExit(
            f"character_performance create rejected: {resp.status_code} "
            f"{resp.text[:400]}"
        )
    created = resp.json()
    task_id = created.get("id")
    if not task_id:
        raise SystemExit(f"create missing task id: {created}")
    return task_id


def poll_task(
    api_base: str,
    api_key: str,
    api_version: str,
    task_id: str,
    logger: logging.Logger,
    deadline_secs: int = 600,
) -> dict:
    headers = {
        "Authorization": f"Bearer {api_key}",
        "X-Runway-Version": api_version,
    }
    url = f"{api_base}/v1/tasks/{task_id}"
    deadline = time.time() + deadline_secs
    last_status = ""
    with httpx.Client(timeout=20.0) as client:
        while time.time() < deadline:
            r = client.get(url, headers=headers)
            r.raise_for_status()
            payload = r.json()
            status = (payload.get("status") or "").upper()
            if status != last_status:
                logger.info("task %s -> %s", task_id, status)
                last_status = status
            if status in {"SUCCEEDED", "FAILED", "CANCELED"}:
                return payload
            time.sleep(5)
    raise SystemExit(f"task {task_id} timed out after {deadline_secs}s")


def download(url: str, target: Path, logger: logging.Logger) -> int:
    target.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    with httpx.stream("GET", url, timeout=120.0, follow_redirects=True) as resp:
        resp.raise_for_status()
        with open(target, "wb") as fh:
            for chunk in resp.iter_bytes():
                size += len(chunk)
                fh.write(chunk)
    logger.info("downloaded %d bytes -> %s", size, target)
    return size


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--character-id",
        help=(
            "Character id from backend/data/characters.json. Uses the "
            "cached portrait PNG as `character.uri` (type=image). "
            "Mutually exclusive with --character-video."
        ),
    )
    parser.add_argument(
        "--character-video",
        help=(
            "Path to a video to use as the character (type=video). "
            "Overrides --character-id. Useful for testing video-driven "
            "character mode (operator's expressions drive an existing "
            "Riggs/Donny clip rather than a still portrait)."
        ),
    )
    parser.add_argument(
        "--performance-video",
        required=True,
        help=(
            "Path to YOUR recorded performance video. 5-10s of "
            "deliberate facial expressions (eyebrow raise, smile, "
            "head tilt). Will be base64-encoded as a data URI for "
            "`reference.uri`."
        ),
    )
    parser.add_argument(
        "--yes-fire", action="store_true",
        help="REQUIRED to fire. Without it the script is dry-run.",
    )
    parser.add_argument(
        "--api-base",
        default=os.environ.get("RUNWAY_API_BASE", "https://api.dev.runwayml.com"),
    )
    parser.add_argument(
        "--api-version",
        default=os.environ.get("RUNWAY_API_VERSION", "2024-11-06"),
    )
    args = parser.parse_args()

    logger = setup_logging()
    logger.info("==== probe-character-performance (act_two) ====")
    logger.info("log path: %s", LOG_PATH)

    if args.character_id and args.character_video:
        raise SystemExit("--character-id and --character-video are mutually exclusive")
    if not args.character_id and not args.character_video:
        raise SystemExit("must pass --character-id OR --character-video")

    # --- character source ---
    if args.character_id:
        record = load_character(args.character_id)
        logger.info("character: %s (name=%r)", args.character_id, record.get("name"))
        portrait = portrait_path_for(args.character_id)
        if not portrait.exists():
            raise SystemExit(f"portrait PNG not found at {portrait}")
        character_type = "image"
        character_src_path = portrait
        character_mime = "image/png"
    else:
        character_video = Path(args.character_video).expanduser().resolve()
        if not character_video.exists():
            raise SystemExit(f"character video not found: {character_video}")
        character_type = "video"
        character_src_path = character_video
        character_mime = "video/mp4"
        logger.info("character: video at %s", character_video)

    char_bytes = character_src_path.stat().st_size
    logger.info(
        "character source: type=%s path=%s size=%.1f KB",
        character_type, character_src_path, char_bytes / 1024,
    )

    # --- reference (operator's performance video) ---
    performance_video = Path(args.performance_video).expanduser().resolve()
    if not performance_video.exists():
        raise SystemExit(f"performance video not found: {performance_video}")
    perf_duration = ffprobe_duration_secs(performance_video)
    perf_bytes = performance_video.stat().st_size
    logger.info(
        "performance video: path=%s duration=%.2fs size=%.1f KB",
        performance_video, perf_duration, perf_bytes / 1024,
    )

    if perf_duration > 30:
        logger.warning(
            "performance video is %.1fs — Act-Two may cap shorter; "
            "consider trimming if the response 400s",
            perf_duration,
        )

    # --- build body ---
    character_uri = to_data_uri(character_src_path, character_mime)
    reference_uri = to_data_uri(performance_video, "video/mp4")
    body = {
        "model": "act_two",
        "character": {"type": character_type, "uri": character_uri},
        "reference": {"type": "video", "uri": reference_uri},
    }
    planned_shape = {
        "model": "act_two",
        "character": {
            "type": character_type,
            "uri": f"data:{character_mime};base64,<{char_bytes} bytes>",
        },
        "reference": {
            "type": "video",
            "uri": f"data:video/mp4;base64,<{perf_bytes} bytes>",
        },
    }
    logger.info("planned POST body shape:")
    logger.info("  %s", json.dumps(planned_shape, indent=2))

    total_body_kb = (len(character_uri) + len(reference_uri)) / 1024
    logger.info("total payload size: ~%.1f KB", total_body_kb)
    if total_body_kb > 5000:
        logger.warning(
            "payload >5 MB — Runway has rejected larger requests before; "
            "if this 413s we'll need to use /v1/uploads"
        )

    if not args.yes_fire:
        logger.info("")
        logger.info("DRY RUN — no Runway call fired.")
        logger.info("Re-run with --yes-fire to actually send.")
        logger.info("Expected credit burn: ~300-700 credits (untested endpoint).")
        return 0

    api_key = os.environ.get("RUNWAY_API_KEY")
    if not api_key:
        raise SystemExit("RUNWAY_API_KEY missing. Source .env first.")

    # --- fire ---
    logger.info("firing live Runway call...")
    fire_t0 = time.time()
    task_id = post_character_performance(
        args.api_base, api_key, args.api_version, body, logger,
    )
    logger.info("task created: %s", task_id)

    payload = poll_task(args.api_base, api_key, args.api_version, task_id, logger)
    fire_elapsed = time.time() - fire_t0
    status = (payload.get("status") or "").upper()
    logger.info("terminal status=%s elapsed=%.1fs", status, fire_elapsed)

    if status != "SUCCEEDED":
        failure = payload.get("failure") or payload.get("error")
        code = payload.get("failureCode")
        print("")
        print("==== PROBE FAILED ====")
        print(f"task elapsed:      {fire_elapsed:.1f}s")
        print(f"status:            {status}")
        print(f"failureCode:       {code}")
        print(f"failure:           {failure}")
        print(f"full payload:      {json.dumps(payload, indent=2)[:600]}")
        print(f"log:               {LOG_PATH}")
        return 1

    # --- download output ---
    output_urls = payload.get("output") or []
    out_url = next((u for u in output_urls if isinstance(u, str)), None)
    if not out_url:
        raise SystemExit(f"SUCCEEDED but no output URL: {payload}")

    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    out_mp4 = ARTIFACT_DIR / f"act-two-probe-{ts}.mp4"
    download(out_url, out_mp4, logger)
    out_duration = ffprobe_duration_secs(out_mp4)

    print("")
    print("==== PROBE PASSED ====")
    print(f"character source:    {character_type} ({char_bytes / 1024:.1f} KB)")
    print(f"performance in:      {perf_duration:.2f}s ({perf_bytes / 1024:.1f} KB)")
    print(f"output video out:    {out_duration:.2f}s ({out_mp4.stat().st_size / 1024 / 1024:.1f} MB)")
    print(f"task elapsed:        {fire_elapsed:.1f}s")
    print(f"output MP4:          {out_mp4}")
    print(f"log:                 {LOG_PATH}")
    print("")
    print("Open the MP4 and check:")
    print("  - Does the character mimic YOUR facial expressions?")
    print("  - Lip-sync, eyebrow movement, head tilt — what makes it through?")
    print("  - Quality vs. the standard avatar_videos lip-sync path?")
    return 0


if __name__ == "__main__":
    sys.exit(main())
