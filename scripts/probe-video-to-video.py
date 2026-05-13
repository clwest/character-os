#!/usr/bin/env python3
"""Probe: does /v1/video_to_video (Aleph style remix) work for us?

Three-phase probe to discover the Aleph endpoint shape:

  Phase 1 — empty-body POST to /v1/video_to_video to capture the
            required-field error list (no credits burned).
  Phase 2 — minimum-viable body posted to capture the next layer of
            errors (still no credits if the body fails validation).
  Phase 3 — (optional, --yes-fire) one real remix on a chosen MP4 +
            style prompt. Polls to terminal, downloads to
            ~/Desktop/Donkey Betz Videos/.

Run order matches the Act-Two probe (PR EX). Phase 1/2 are zero-cost.
Phase 3 burns credits (Aleph is ~$$ per second; estimate before run).

Usage:
  # Phase 1/2 only (free) — discovers the body shape:
  python scripts/probe-video-to-video.py

  # Phase 3 (real fire) — needs a source MP4 + style prompt:
  python scripts/probe-video-to-video.py \\
      --source-video "~/Desktop/Donkey Betz Videos/fart-tester-video.mp4" \\
      --style "cinematic noir, high contrast, desaturated, 35mm film grain" \\
      --yes-fire

Output:
  - Full request+response log → /tmp/probe-v2v-<ts>.log
  - Remix MP4 (Phase 3) → ~/Desktop/Donkey Betz Videos/v2v-<style>-<ts>.mp4
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path

import httpx  # type: ignore

# ---- env discovery ----------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
ENV_PATH = REPO_ROOT / ".env"


def _load_env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV_PATH.exists():
        return out
    for raw in ENV_PATH.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        out[k.strip()] = v.strip().strip('"').strip("'")
    return out


ENV = _load_env()
API_BASE = ENV.get("RUNWAY_API_BASE", "https://api.dev.runwayml.com")
API_KEY = os.environ.get("RUNWAY_API_KEY") or ENV.get("RUNWAY_API_KEY", "")
API_VERSION = ENV.get("RUNWAY_API_VERSION", "2024-11-06")


def _slug(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", s.lower()).strip("-")[:40] or "style"


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
        "X-Runway-Version": API_VERSION,
    }


def _log_lines(log_path: Path, *lines: str) -> None:
    with open(log_path, "a") as fh:
        for line in lines:
            fh.write(f"{line}\n")


def phase_empty_body(log_path: Path) -> dict:
    """Phase 1 — empty-body POST. Captures the top-level required keys."""
    url = f"{API_BASE}/v1/video_to_video"
    print(f"[phase 1] POST {url} with body={{}}")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(url, headers=_headers(), json={})
    print(f"  → status: {r.status_code}")
    body = r.text
    _log_lines(log_path, f"[phase 1] POST {url}", f"status: {r.status_code}", body)
    try:
        parsed = r.json()
    except Exception:
        parsed = {"raw": body[:500]}
    print("  → response:")
    print(json.dumps(parsed, indent=2)[:1500])
    return parsed


def phase_minimum_body(log_path: Path) -> dict:
    """Phase 2 — minimum body guess based on conventions from peer
    routes (image_to_video, character_performance, voice_dubbing).
    """
    url = f"{API_BASE}/v1/video_to_video"
    # Best-guess minimum body. Refined after phase 1's error list.
    body = {
        "model": "gen4_aleph",
        "videoUri": "data:video/mp4;base64,AAAA",
        "promptText": "cinematic noir style transfer",
    }
    print(f"[phase 2] POST {url} with body={json.dumps(body)[:200]}")
    with httpx.Client(timeout=30.0) as client:
        r = client.post(url, headers=_headers(), json=body)
    print(f"  → status: {r.status_code}")
    text = r.text
    _log_lines(
        log_path,
        f"[phase 2] POST {url}",
        f"body: {json.dumps(body)[:1000]}",
        f"status: {r.status_code}",
        text,
    )
    try:
        parsed = r.json()
    except Exception:
        parsed = {"raw": text[:500]}
    print("  → response:")
    print(json.dumps(parsed, indent=2)[:1500])
    return parsed


def phase_real_fire(
    log_path: Path, source_video: Path, style: str
) -> Path | None:
    """Phase 3 — real Aleph fire. Burns credits."""
    url = f"{API_BASE}/v1/video_to_video"
    print(f"[phase 3] real fire — source={source_video} style={style!r}")

    video_bytes = source_video.read_bytes()
    print(f"  source bytes: {len(video_bytes):,}")
    if len(video_bytes) > 16 * 1024 * 1024:
        print("  ✗ source exceeds 16MB data-URI cap; need a hosted URL.")
        sys.exit(2)

    encoded = base64.b64encode(video_bytes).decode("ascii")
    video_uri = f"data:video/mp4;base64,{encoded}"

    body = {
        "model": "gen4_aleph",
        "videoUri": video_uri,
        "promptText": style,
        "ratio": "1280:720",
    }

    with httpx.Client(timeout=120.0) as client:
        r = client.post(url, headers=_headers(), json=body)
        print(f"  → create status: {r.status_code}")
        body_text = r.text
        _log_lines(
            log_path,
            f"[phase 3] POST {url}",
            f"body keys: {list(body.keys())}",
            f"status: {r.status_code}",
            body_text[:2000],
        )
        if r.status_code >= 400:
            print(f"  ✗ {body_text[:500]}")
            return None
        task = r.json()
        task_id = task.get("id")
        if not task_id:
            print(f"  ✗ no task id in response: {task}")
            return None
        print(f"  task id: {task_id}")

        # Poll. Aleph is slow (~minutes for short clips per Phase J docs).
        # 600s deadline.
        deadline = time.time() + 600
        last_status = None
        while time.time() < deadline:
            time.sleep(5)
            pr = client.get(
                f"{API_BASE}/v1/tasks/{task_id}", headers=_headers()
            )
            if pr.status_code != 200:
                print(f"  poll status {pr.status_code}: {pr.text[:200]}")
                continue
            t = pr.json()
            status = t.get("status")
            if status != last_status:
                print(f"  status: {status}")
                last_status = status
            if status == "SUCCEEDED":
                outputs = t.get("output", [])
                if not outputs:
                    print(f"  ✗ SUCCEEDED but no output: {t}")
                    return None
                out_url = outputs[0]
                print(f"  output url: {out_url}")
                # Download.
                desktop = Path.home() / "Desktop" / "Donkey Betz Videos"
                desktop.mkdir(parents=True, exist_ok=True)
                ts = datetime.now().strftime("%Y%m%d-%H%M%S")
                target = desktop / f"v2v-{_slug(style)}-{ts}.mp4"
                with httpx.stream("GET", out_url, timeout=120.0) as resp:
                    resp.raise_for_status()
                    with open(target, "wb") as fh:
                        for chunk in resp.iter_bytes():
                            fh.write(chunk)
                print(f"  ✓ saved: {target} ({target.stat().st_size:,} bytes)")
                _log_lines(log_path, f"saved: {target}")
                return target
            if status == "FAILED":
                print(f"  ✗ task FAILED: {t}")
                return None
        print("  ✗ polling deadline reached, task did not complete")
        return None


def main() -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--source-video",
        type=Path,
        help="Path to a local MP4 to remix. Required for --yes-fire.",
    )
    parser.add_argument(
        "--style",
        default="cinematic noir, desaturated, 35mm film grain, high contrast",
        help="Aleph style prompt. Free-text describing the visual transform.",
    )
    parser.add_argument(
        "--yes-fire",
        action="store_true",
        help="Burn credits on a real remix in Phase 3. Without this flag, "
        "only Phase 1/2 (free discovery) run.",
    )
    args = parser.parse_args()

    if not API_KEY:
        print("✗ RUNWAY_API_KEY not set (.env or env)")
        return 1
    print(f"✓ API_BASE: {API_BASE}")
    print(f"✓ API_KEY length: {len(API_KEY)}")

    ts = datetime.now().strftime("%Y%m%d-%H%M%S")
    log_path = Path(f"/tmp/probe-v2v-{ts}.log")
    print(f"log: {log_path}")

    # Phase 1.
    print()
    phase_empty_body(log_path)

    # Phase 2.
    print()
    phase_minimum_body(log_path)

    # Phase 3 (gated).
    if not args.yes_fire:
        print()
        print("Phase 3 skipped (no --yes-fire). Phases 1+2 logged above.")
        print(f"Full log: {log_path}")
        return 0

    if not args.source_video:
        print("✗ --yes-fire requires --source-video")
        return 1
    src = args.source_video.expanduser().resolve()
    if not src.exists():
        print(f"✗ source video not found: {src}")
        return 1

    print()
    phase_real_fire(log_path, src, args.style)
    print(f"Full log: {log_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
