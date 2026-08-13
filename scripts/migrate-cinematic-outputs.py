#!/usr/bin/env python3
"""One-shot migration — backfill `cinematic_video` OutputRecords for
campaigns that already have `cached_video_url` set but never had the
matching OutputRecord appended (the legacy /cinematic-video route
only set the top-level cached_video_url field).

Without this migration, PR FD's Backdrop modal can't find existing
cinematics because it filters `campaign.outputs[]` by
`kind === 'cinematic_video'`. PR FD fix-1 adds the OutputRecord on
NEW generations; this script catches all the OLD ones.

Safe to run multiple times — skips campaigns that already have a
cinematic_video OutputRecord.

Usage:
  cd backend && source .venv/bin/activate
  python ../scripts/migrate-cinematic-outputs.py
"""
from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# Ensure we can import app.* whether run from repo root or backend/.
REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND = REPO_ROOT / "backend"
if str(BACKEND) not in sys.path:
    sys.path.insert(0, str(BACKEND))

from app.config import get_settings  # noqa: E402
from app.services.storage import CampaignStore  # noqa: E402


def main() -> int:
    settings = get_settings()
    store = CampaignStore(settings.data_path)

    videos_dir = settings.data_path / "videos"
    if not videos_dir.exists():
        print(f"✗ videos dir missing: {videos_dir}")
        return 1

    campaigns = store.list()
    print(f"scanning {len(campaigns)} campaigns...")

    migrated = 0
    skipped_already = 0
    skipped_no_file = 0
    skipped_no_cache = 0

    for record in campaigns:
        cached = (record.cached_video_url or "").strip()
        if not cached:
            skipped_no_cache += 1
            continue
        existing_cv = [o for o in record.outputs if o.kind == "cinematic_video"]
        if existing_cv:
            skipped_already += 1
            continue
        # Legacy cached file is at data/videos/{campaign_id}.mp4.
        legacy_file = videos_dir / f"{record.id}.mp4"
        if not legacy_file.exists():
            print(
                f"  ✗ {record.id}: cached_video_url set but file missing "
                f"({legacy_file.name})"
            )
            skipped_no_file += 1
            continue
        # Append a new OutputRecord pointing at the existing canonical
        # file. We don't copy — the cached_video_url field still points
        # here too, so legacy consumers keep working. New generations
        # (via the fixed /cinematic-video route) will use per-output
        # filenames to avoid clobbering.
        new_output_id = uuid.uuid4().hex[:12]
        cache_filename = legacy_file.name  # `<campaign_id>.mp4`
        entry = {
            "id": new_output_id,
            "kind": "cinematic_video",
            "video_url": (
                f"/api/campaigns/{record.id}/output/{new_output_id}"
            ),
            "cache_filename": cache_filename,
            "script": None,
            "task_id": None,
            "mock_mode": False,
            "parent_output_id": None,
            "variant_id": None,
            "variant_title": None,
            # Use the campaign's created_at as a best-effort timestamp
            # so the modal's "freshness" sort respects roughly-when-
            # the-cinematic-was-cached.
            "created_at": (
                record.created_at
                or datetime.now(timezone.utc).isoformat()
            ),
        }
        ok = store.append_output(record.id, entry)
        if ok:
            migrated += 1
            char_part = f" char={record.character_id}" if record.character_id else ""
            print(f"  ✓ {record.id}{char_part}: appended {new_output_id}")
        else:
            print(f"  ✗ {record.id}: append_output returned None")

    print()
    print("─── summary ───")
    print(f"migrated:           {migrated}")
    print(f"already had record: {skipped_already}")
    print(f"no cache field:     {skipped_no_cache}")
    print(f"file missing:       {skipped_no_file}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
