"""SESSION 210 — operator-facing wrapper around
``apps.compositions.tasks.sweep_expired_assets``.

The Celery Beat schedule fires the same logic hourly at :07. This
command exists for the in-between case: operator just ran a render,
spotted an expired one in the Videos library, and wants to clean
up *now* rather than wait for the next Beat cycle.

Behavior mirrors ``backfill_asset_roles``:

* **Dry-run is the default.** Walks every HTTPS Asset, classifies
  via ``compute_storage_health``, and prints what *would* be
  detached. Nothing is written.
* **``--commit`` actually applies.** Same Composition.final_asset
  SET_NULL the Beat task uses.

The command is a thin wrapper — both this and the Celery task call
``run_expired_asset_sweep`` so behavior parity is guaranteed by
construction.
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.compositions.tasks import run_expired_asset_sweep


class Command(BaseCommand):
    help = (
        "Sweep expired Runway/CDN final_assets and detach them from "
        "their Compositions. Dry-run by default; pass --commit to apply."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--commit",
            action="store_true",
            help=(
                "Apply the sweep. Without this flag the command only "
                "prints what would change."
            ),
        )

    def handle(self, *args, **options) -> None:
        commit: bool = options["commit"]
        result = run_expired_asset_sweep(commit=commit)

        mode = "COMMIT" if commit else "DRY-RUN"
        self.stdout.write(self.style.MIGRATE_HEADING(f"[{mode}] expired-asset sweep"))
        self.stdout.write(
            f"  HTTPS assets scanned:  {result['scanned']}"
        )
        self.stdout.write(
            f"  expired (HTTPS_EXPIRED): {result['expired']}"
        )
        if commit:
            self.stdout.write(
                self.style.SUCCESS(
                    f"  compositions detached: {result['detached']}"
                )
            )
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"  would detach (dry-run): {result['expired']}  "
                    f"— rerun with --commit to apply"
                )
            )

        # Per-row breakdown — capped at 20 to keep the output sane
        # on a workspace with weeks of accumulated expiry. Operator
        # can always re-query the DB directly if they want the full
        # list.
        if result["expired_asset_ids"]:
            self.stdout.write("")
            preview = result["expired_asset_ids"][:20]
            for asset_id in preview:
                self.stdout.write(f"    - {asset_id}")
            remaining = result["expired"] - len(preview)
            if remaining > 0:
                self.stdout.write(f"    ... and {remaining} more")
