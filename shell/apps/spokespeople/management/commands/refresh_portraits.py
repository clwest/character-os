"""Refresh stale portrait URLs across all spokespeople.

SESSION 169 follow-up. Runway's CloudFront thumbnail URLs are
JWT-signed with ~30-day expiry. After the JWT expires the SPA's
``<img src=portrait_path>`` 401s. This command hits
``GET /v1/avatars/{id}`` for every spokesperson with a
``runway_avatar_id`` set and refreshes ``portrait_path`` in one
shot.

Usage::

    python manage.py refresh_portraits [--workspace=<slug>] [--dry-run]

Skip cases:

* No ``runway_avatar_id`` → skipped silently.
* Media-engine in mock mode → skipped with a note.
* Network / non-2xx from Runway → skipped + logged warning.

Read-only on Runway. Only mutates the local row's
``portrait_path``.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.spokespeople.models import Spokesperson
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)


class Command(BaseCommand):
    help = (
        "Refresh portrait_path on all spokespeople with a Runway "
        "avatar_id. Hits media-engine to re-fetch fresh JWT-signed "
        "thumbnail URLs."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--workspace",
            default=None,
            help="Restrict to one workspace by slug.",
        )
        parser.add_argument(
            "--dry-run",
            dest="dry_run",
            action="store_true",
            help="Print what would change without persisting.",
        )

    def handle(self, *args, **options):
        out = self.stdout.write
        workspace_slug: str | None = options["workspace"]
        dry_run: bool = options["dry_run"]

        qs = Spokesperson.objects.exclude(runway_avatar_id="").order_by(
            "workspace__slug", "name",
        )
        if workspace_slug:
            qs = qs.filter(workspace__slug=workspace_slug)

        rows = list(qs)
        out(f"Refreshing portrait URLs for {len(rows)} spokesperson(s)")
        if dry_run:
            out("  (dry-run — no DB writes)")
        out("")

        refreshed = 0
        skipped = 0
        failed = 0
        for sp in rows:
            label = f"  {sp.workspace.slug}/{sp.name}  (avatar={sp.runway_avatar_id[:12]}…)"
            try:
                with MediaEngineClient() as client:
                    fresh = client.refresh_avatar_thumbnail(
                        avatar_id=sp.runway_avatar_id,
                    )
            except MediaEngineError as exc:
                out(f"{label}  FAILED  ({exc})")
                failed += 1
                continue
            if not fresh:
                out(f"{label}  SKIPPED  (no fresh URL — mock mode or Runway 4xx)")
                skipped += 1
                continue
            old_prefix = (sp.portrait_path or "")[:60]
            new_prefix = fresh[:60]
            out(f"{label}  REFRESHED")
            out(f"      old: {old_prefix}{'…' if len(sp.portrait_path or '') > 60 else ''}")
            out(f"      new: {new_prefix}{'…' if len(fresh) > 60 else ''}")
            if not dry_run:
                sp.portrait_path = fresh
                sp.save(update_fields=["portrait_path", "updated_at"])
            refreshed += 1

        out("")
        out(f"Summary: refreshed={refreshed}  skipped={skipped}  failed={failed}")
