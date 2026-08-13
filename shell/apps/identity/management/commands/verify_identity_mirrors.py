"""§19 Step 4.e — read-only compatibility-mirror verifier command.

Runs ``apps.identity.compat.verify_all_mirrors`` against the current
database and reports drift + operational-migration-debt signals.

**Read-only.** Never runs Step 3 backfill. Never repairs mirrors.
Never creates ``CharacterIdentity`` rows. Never invokes
``record_prequalification_representation``. Only SELECT queries
execute.

Usage::

    python manage.py verify_identity_mirrors
    python manage.py verify_identity_mirrors --workspace <UUID>
    python manage.py verify_identity_mirrors --json
    python manage.py verify_identity_mirrors --fail-on-drift

Exit codes:

* ``0`` — no drift found (all clean-match + not-applicable). Even
  when many teammates are in ``no_identity`` + all-blank shape (a
  legitimate not-applicable), the command exits ``0`` — N/A alone
  is not drift.
* ``1`` (with ``--fail-on-drift``) — one or more teammates show
  true drift, including ``no_identity`` + at least one populated
  mirror (the ``canonical_backfill_required`` signal).

The JSON output shape is stable and machine-readable so downstream
tooling (CI gates, operational dashboards) can consume it without
depending on the human-readable text.
"""
from __future__ import annotations

import json
import sys
import uuid
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from apps.identity import compat


class Command(BaseCommand):
    help = (
        "Read-only compatibility-mirror verifier (§17.10.a "
        "Amendment 4). Reports drift + operational migration debt "
        "(``canonical_backfill_required_count``) across all "
        "Teammate rows. Never mutates state."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--workspace",
            type=str,
            default=None,
            help="Restrict the sweep to a single workspace UUID.",
        )
        parser.add_argument(
            "--json",
            action="store_true",
            dest="json_output",
            help=(
                "Emit machine-readable JSON instead of the "
                "human-readable summary."
            ),
        )
        parser.add_argument(
            "--fail-on-drift",
            action="store_true",
            dest="fail_on_drift",
            help=(
                "Exit non-zero if any drift is detected (including "
                "populated mirrors on no-identity teammates). N/A "
                "alone does not fail."
            ),
        )

    def handle(self, *_, **options: Any) -> None:
        workspace_arg: str | None = options.get("workspace")
        json_output: bool = options.get("json_output", False)
        fail_on_drift: bool = options.get("fail_on_drift", False)

        workspace_id: uuid.UUID | None = None
        if workspace_arg is not None:
            try:
                workspace_id = uuid.UUID(workspace_arg)
            except (TypeError, ValueError) as exc:
                raise CommandError(
                    f"--workspace must be a UUID; got {workspace_arg!r}"
                ) from exc

        report = compat.verify_all_mirrors(workspace_id=workspace_id)

        if json_output:
            self.stdout.write(json.dumps(_report_to_json(report), indent=2))
        else:
            self._print_human_readable(report)

        if fail_on_drift and report.drift_count > 0:
            sys.exit(1)

    def _print_human_readable(self, report: compat.MirrorVerifyReport) -> None:
        out = self.stdout.write
        out("§17.10.a Amendment 4 compatibility-mirror verifier")
        out("=" * 55)
        out(f"Total Teammates inspected: {report.total_inspected}")
        out("")
        out("Identity-class breakdown:")
        for cls, count in sorted(report.identity_class_counts.items()):
            out(f"  {cls:32s}  {count}")
        out("")
        out(f"Clean matches:                    {report.clean_match_count}")
        out(f"Drifted teammates:                {report.drift_count}")
        out(
            f"Canonical backfill required:      "
            f"{report.canonical_backfill_required_count}"
        )
        if report.canonical_backfill_required_count > 0:
            out(
                "  → run ``python manage.py backfill_identity_substrate`` "
                "for these teammates"
            )
        out("")
        if report.drift_by_field:
            out("Drift by field:")
            for name, count in sorted(report.drift_by_field.items()):
                out(f"  {name:24s}  {count}")
            out("")
        if report.drift_by_reason:
            out("Drift by reason:")
            for reason, count in sorted(report.drift_by_reason.items()):
                out(f"  {reason:40s}  {count}")
            out("")
        if report.na_by_reason:
            out("Not-applicable by reason:")
            for reason, count in sorted(report.na_by_reason.items()):
                out(f"  {reason:40s}  {count}")
            out("")

        drifted = [r for r in report.per_teammate if r.has_drift]
        if drifted:
            out(f"Drifted teammates ({len(drifted)}):")
            for r in drifted[:50]:  # cap to keep output scannable
                marker = "!" if r.canonical_backfill_required else " "
                out(
                    f"  {marker} {r.teammate_id}  [{r.identity_class}]"
                )
                for f in r.fields:
                    if f.status == compat.MirrorStatus.DRIFT:
                        out(
                            f"      {f.field_name:22s}  "
                            f"{f.reason:40s}  "
                            f"mirror={_truncate(f.mirror_value)!r:44s} "
                            f"canonical={_truncate(f.canonical_value)!r}"
                        )
            if len(drifted) > 50:
                out(f"  ... {len(drifted) - 50} more drifted rows elided")


def _truncate(value, *, limit: int = 60) -> str | None:
    """Human-readable truncation. Long base64 data URIs stored as
    ``portrait_path`` mirror values (common in mock-mode / pre-4.d
    dev data) would otherwise explode the terminal output. JSON
    output preserves full values for machine consumption.
    """
    if value is None:
        return None
    text = str(value)
    if len(text) <= limit:
        return text
    return text[:limit] + f"...(+{len(text) - limit} chars)"


def _report_to_json(report: compat.MirrorVerifyReport) -> dict:
    """Stable JSON shape for the verifier output.

    Consumers (CI, dashboards) may depend on the field names + nesting;
    changing this schema requires a versioned bump. Currently
    unversioned because 4.e is the first landing.
    """
    return {
        "summary": {
            "total_inspected": report.total_inspected,
            "identity_class_counts": dict(report.identity_class_counts),
            "clean_match_count": report.clean_match_count,
            "drift_count": report.drift_count,
            "canonical_backfill_required_count": (
                report.canonical_backfill_required_count
            ),
            "drift_by_field": dict(report.drift_by_field),
            "drift_by_reason": dict(report.drift_by_reason),
            "na_by_reason": dict(report.na_by_reason),
        },
        "teammates": [
            {
                "teammate_id": str(r.teammate_id),
                "workspace_id": str(r.workspace_id),
                "identity_class": r.identity_class,
                "has_drift": r.has_drift,
                "canonical_backfill_required": r.canonical_backfill_required,
                "fields": {
                    f.field_name: {
                        "mirror_value": f.mirror_value,
                        "canonical_value": f.canonical_value,
                        "status": f.status,
                        "reason": f.reason,
                    }
                    for f in r.fields
                },
            }
            for r in report.per_teammate
        ],
    }
