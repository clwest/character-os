"""§19 Step 3 legacy-identity backfill command.

Iterates over ``apps.spokespeople.Teammate`` rows and imports
each into the canonical identity substrate via
``apps.identity.import_service``. Idempotent — running the
command twice produces the same substrate state.

Flags:

* ``--dry-run`` runs the full ``classify_teammate`` logic on every
  Teammate and prints exactly what WOULD happen without touching
  any row (Amendment F). Reports the same action classes the real
  run reports: ``imported``, ``already_imported``, ``skipped_authored``,
  ``nothing_to_import``, ``failed_incompatible``, ``failed``.
* ``--workspace=<uuid>`` restricts the sweep to a single workspace.
* ``--limit=N`` processes at most N teammates (post-workspace-filter).
* ``--fail-fast`` stops on the first ``failed`` teammate. Default is
  continue-and-report so a bad row does not block the rest.
"""
from __future__ import annotations

import uuid
from collections import Counter

from django.core.management.base import BaseCommand, CommandError

from apps.identity import import_service
from apps.spokespeople.models import Teammate


class Command(BaseCommand):
    help = (
        "§19 Step 3 — Legacy Teammate → Canonical Identity substrate "
        "one-time historical backfill. Idempotent; re-runs report "
        "already_imported for previously-imported teammates."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help=(
                "Classify every teammate without writing. Reports "
                "the same action classes a real run would report."
            ),
        )
        parser.add_argument(
            "--workspace",
            type=str,
            default=None,
            help="Restrict the sweep to a single workspace UUID.",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=None,
            help="Process at most N teammates.",
        )
        parser.add_argument(
            "--fail-fast",
            action="store_true",
            help="Stop on the first ``failed`` teammate.",
        )

    def handle(self, *args, **options) -> None:
        dry_run: bool = options["dry_run"]
        workspace_id: str | None = options.get("workspace")
        limit: int | None = options.get("limit")
        fail_fast: bool = options["fail_fast"]

        queryset = Teammate.objects.all().order_by("created_at", "id")
        if workspace_id:
            try:
                workspace_uuid = uuid.UUID(workspace_id)
            except (TypeError, ValueError) as exc:
                raise CommandError(
                    f"--workspace must be a UUID; got {workspace_id!r}",
                ) from exc
            queryset = queryset.filter(workspace_id=workspace_uuid)
        if limit is not None:
            queryset = queryset[:limit]

        run_id = uuid.uuid4()
        mode_label = "dry-run" if dry_run else "real"
        self.stdout.write(
            self.style.NOTICE(
                f"backfill_identity_substrate: mode={mode_label} "
                f"run_id={run_id}"
            ),
        )

        counts: Counter[str] = Counter()
        for teammate in queryset:
            result = import_service.import_legacy_teammate(
                teammate, run_id=run_id, dry_run=dry_run,
            )
            counts[result.action] += 1
            self._print_result(teammate, result)
            if fail_fast and result.action == "failed":
                self.stdout.write(
                    self.style.ERROR(
                        "aborting on first ``failed`` teammate "
                        "(--fail-fast enabled)."
                    ),
                )
                break

        self._print_summary(counts, run_id, mode_label)

    def _print_result(self, teammate, result) -> None:
        style = {
            "imported": self.style.SUCCESS,
            "already_imported": self.style.SUCCESS,
            "skipped_authored": self.style.WARNING,
            "nothing_to_import": self.style.NOTICE,
            "failed_incompatible": self.style.ERROR,
            "failed": self.style.ERROR,
        }.get(result.action, self.style.NOTICE)
        detail = f" — {result.detail}" if result.detail else ""
        self.stdout.write(
            style(
                f"  {teammate.name!r} [{teammate.id}] "
                f"→ {result.action}{detail}",
            ),
        )

    def _print_summary(self, counts, run_id, mode_label) -> None:
        self.stdout.write("")
        self.stdout.write(
            self.style.NOTICE(
                f"summary (mode={mode_label} run_id={run_id}):"
            ),
        )
        for action in (
            "imported",
            "already_imported",
            "skipped_authored",
            "nothing_to_import",
            "failed_incompatible",
            "failed",
        ):
            n = counts.get(action, 0)
            self.stdout.write(f"  {action:<24} {n}")
        self.stdout.write(f"  {'total':<24} {sum(counts.values())}")
