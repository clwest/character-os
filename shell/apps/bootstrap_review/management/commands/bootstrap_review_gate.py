"""SESSION 249 §19 Step 9.b.3b readiness CLI.

Pure inspection over the 9.b.3a ``derive_step10_readiness``
predicate. Emits JSON to stdout. Exit 0 iff the fixture (or all
authorized fixtures under ``--all-fixtures``) satisfies the full
readiness predicate; exit 1 otherwise.

No hidden repair behavior. No mutation. No provider execution.
"""
from __future__ import annotations

import json
import sys
from dataclasses import asdict

from django.core.management.base import BaseCommand, CommandError

from apps.bootstrap_review.evidence import AUTHORIZED_FIXTURE_IDS
from apps.bootstrap_review.readiness import derive_step10_readiness


class Command(BaseCommand):
    help = (
        "Inspect Step-10 readiness for one or all authorized human "
        "fixtures. Emits JSON; exits 0 when ready, 1 otherwise."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "fixture_id",
            nargs="?",
            default=None,
            help="Fixture identifier (e.g. fixture_h1). Omit with --all-fixtures.",
        )
        parser.add_argument(
            "--all-fixtures",
            action="store_true",
            help="Report readiness for every authorized human fixture.",
        )

    def handle(self, *args, **options):
        fixture_id = options.get("fixture_id")
        all_fixtures: bool = options.get("all_fixtures", False)

        if all_fixtures and fixture_id:
            raise CommandError(
                "Pass either <fixture_id> OR --all-fixtures, not both."
            )
        if not all_fixtures and not fixture_id:
            raise CommandError(
                "Pass a <fixture_id> or --all-fixtures."
            )

        if all_fixtures:
            fixtures = sorted(AUTHORIZED_FIXTURE_IDS)
        else:
            fixtures = [fixture_id]

        reports = [
            _serialize_readiness(derive_step10_readiness(f)) for f in fixtures
        ]
        all_ready = all(r["ready"] for r in reports)
        payload = {
            "reports": reports,
            "all_ready": all_ready,
        }
        self.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        if not all_ready:
            sys.exit(1)


def _serialize_readiness(readiness) -> dict:
    """Serialize FixtureReadiness dataclass to a plain JSON dict.

    Includes the aggregate ``ready`` property in the payload so
    consumers do not have to re-derive it.
    """
    data = asdict(readiness)
    data["ready"] = readiness.ready
    return data
