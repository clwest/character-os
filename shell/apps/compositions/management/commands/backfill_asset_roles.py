"""Asset Library v1 (SESSION 185, slice A1) — backfill management command.

Maps existing Asset rows from their default ``RAW_UPLOAD`` role
(set by the A0 migration) to a primitive_kind-derived role using
the heuristics in ``docs/design/ASSET_LIBRARY_V1.md`` §Taxonomy.

Behavior:

* **Dry-run is the default.** Prints a per-role summary plus the
  full list of assets that would change. Nothing is written.
* **``--commit`` actually applies the plan.** No silent backfills
  (Q-a-2, contract rule 17). Operator reviews the dry-run report,
  then re-runs with ``--commit``.
* **``--workspace <slug>`` scopes to one workspace** by name. Useful
  for staged rollout. Defaults to all workspaces.
* **Idempotent.** Only processes rows where ``role == RAW_UPLOAD``.
  Re-running after a partial commit picks up only the still-default
  rows.

The heuristic table itself lives in
:mod:`apps.compositions.asset_roles` (SESSION 186 / A2) so the same
mapping serves both production primitive emit sites and this
backfill. ``PRIMITIVE_TO_ROLE``, ``KNOWN_EXPERIMENT_UUID_PREFIXES``,
and ``derive_role`` are re-exported here for tests + imports that
pre-date the move.

Assets that match no heuristic are listed as **needs review** in
the report and left at ``RAW_UPLOAD``.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Workspace
from apps.compositions.asset_roles import (
    KNOWN_EXPERIMENT_UUID_PREFIXES,
    PRIMITIVE_TO_ROLE,
    derive_role,
)
from apps.compositions.models import Asset, AssetRole


class Command(BaseCommand):
    help = (
        "Backfill Asset.role from source_spec.primitive_kind. "
        "Dry-run by default; pass --commit to apply."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--commit",
            action="store_true",
            help=(
                "Apply the backfill plan. Without this flag the command "
                "only prints a report. Q-a-2 / rule 17."
            ),
        )
        parser.add_argument(
            "--workspace",
            metavar="NAME",
            help=(
                "Scope to a single workspace by name. Defaults to all "
                "workspaces."
            ),
        )

    def handle(self, *args, **options) -> None:
        commit: bool = options["commit"]
        workspace_name: str | None = options["workspace"]

        qs = Asset.objects.filter(role=AssetRole.RAW_UPLOAD)
        if workspace_name:
            try:
                ws = Workspace.objects.get(name=workspace_name)
            except Workspace.DoesNotExist as exc:
                raise CommandError(
                    f"workspace not found: {workspace_name!r}"
                ) from exc
            qs = qs.filter(workspace=ws)

        plan: dict[str, list[Asset]] = defaultdict(list)
        review: list[Asset] = []

        for asset in qs.iterator():
            target = derive_role(asset)
            if target is None:
                review.append(asset)
            else:
                plan[target].append(asset)

        self._print_report(plan, review, commit=commit)

        if not commit:
            return

        self._apply(plan)

    # ---- internal helpers --------------------------------------------

    def _print_report(
        self,
        plan: dict[str, list[Asset]],
        review: list[Asset],
        *,
        commit: bool,
    ) -> None:
        mode = "COMMIT" if commit else "DRY-RUN"
        total_planned = sum(len(rows) for rows in plan.values())
        total_review = len(review)
        total = total_planned + total_review

        self.stdout.write(f"backfill_asset_roles ({mode})")
        self.stdout.write("=" * 60)
        self.stdout.write(
            f"Candidates (Asset.role == RAW_UPLOAD): {total}"
        )
        self.stdout.write(
            f"  Mappable via heuristic:  {total_planned}"
        )
        self.stdout.write(
            f"  Needs operator review:   {total_review}"
        )
        self.stdout.write("")

        if plan:
            self.stdout.write("Per-role plan:")
            for role_value in sorted(plan):
                rows = plan[role_value]
                self.stdout.write(
                    f"  {role_value:>16} : {len(rows)} asset(s)"
                )
            self.stdout.write("")

        if review:
            self.stdout.write(
                "Needs operator review (no primitive_kind match, "
                "no known special-case UUID):"
            )
            for asset in review[:20]:
                self.stdout.write(
                    f"  {asset.id} "
                    f"asset_type={asset.asset_type} "
                    f"workspace={asset.workspace.name!r}"
                )
            remaining = len(review) - 20
            if remaining > 0:
                self.stdout.write(
                    f"  ... and {remaining} more (truncated)"
                )
            self.stdout.write("")

        if not commit:
            self.stdout.write(
                "DRY-RUN complete. Re-run with --commit to apply."
            )
        else:
            self.stdout.write("COMMIT mode — applying changes ...")

    def _apply(self, plan: dict[str, list[Asset]]) -> None:
        with transaction.atomic():
            for role_value, rows in plan.items():
                pks = [a.pk for a in rows]
                updated = Asset.objects.filter(pk__in=pks).update(
                    role=role_value
                )
                self.stdout.write(
                    f"  {role_value:>16} : {updated} row(s) updated"
                )
        self.stdout.write("done.")


# Re-exported for tests (and existing imports that pre-date the SESSION
# 186 / A2 move to apps.compositions.asset_roles).
__all__ = [
    "Command",
    "PRIMITIVE_TO_ROLE",
    "KNOWN_EXPERIMENT_UUID_PREFIXES",
    "derive_role",
]
