"""Persist Spokesperson portraits locally to eliminate JWT-expiry churn.

SESSION 202 follow-up. SESSION 169's ``refresh_portraits`` command
re-fetches fresh JWT-signed CloudFront URLs from Runway —
solving today's 401s for ~30 days, until the new JWT expires
too. This command is the canonical fix: download the portrait
bytes ONCE + persist to media-engine's filesystem +
update ``portrait_path`` to the stable local URL.

After running, ``portrait_path`` looks like
``/data/_internal/avatar_portraits/<avatar_id>.png`` —
served via the media-engine's StaticFiles mount + the
vite ``/data`` proxy. Never expires.

Usage::

    python manage.py persist_spokesperson_portraits [--workspace=<slug>] [--dry-run]

Skip cases:

* No ``runway_avatar_id`` → skipped silently.
* portrait_path already starts with ``/data/_internal/avatar_portraits/``
  → already persisted; skipped (idempotent).
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


_PERSISTED_PREFIX = "/data/_internal/avatar_portraits/"


class Command(BaseCommand):
    help = (
        "Persist Spokesperson portraits locally so portrait_path "
        "never expires. One-shot backfill; future spokespeople "
        "get the same treatment via the avatar creation hook in "
        "apps.spokespeople.views."
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
        out(f"Persisting portraits for {len(rows)} spokesperson(s)")
        if dry_run:
            out("  (dry-run — no DB writes)")
        out("")

        persisted = 0
        already_local = 0
        skipped = 0
        failed = 0
        for sp in rows:
            label = (
                f"  {sp.workspace.slug}/{sp.name}  "
                f"(avatar={sp.runway_avatar_id[:12]}…)"
            )

            # Idempotency — already-local rows skip the Runway
            # round-trip entirely.
            if (sp.portrait_path or "").startswith(_PERSISTED_PREFIX):
                out(f"{label}  ALREADY LOCAL")
                already_local += 1
                continue

            try:
                with MediaEngineClient() as client:
                    local_url = client.persist_avatar_portrait(
                        avatar_id=sp.runway_avatar_id,
                    )
            except MediaEngineError as exc:
                out(f"{label}  FAILED  ({exc})")
                failed += 1
                continue
            if not local_url:
                out(
                    f"{label}  SKIPPED  "
                    f"(no persisted URL — mock mode or Runway 4xx)"
                )
                skipped += 1
                continue

            out(f"{label}  PERSISTED  ->  {local_url}")
            if not dry_run:
                sp.portrait_path = local_url
                sp.save(update_fields=["portrait_path", "updated_at"])
            persisted += 1

        out("")
        out(
            f"Summary: persisted={persisted}  "
            f"already_local={already_local}  "
            f"skipped={skipped}  failed={failed}"
        )
