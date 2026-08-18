"""Backfill / re-embed NarrativeMemory rows.

SESSION 264 Slice 2. Rows created before the Slice 2 migration
(memory 0002) have ``embedding_vector=NULL`` and are excluded
from retrieval until embedded. This command walks the active set
(status=REMEMBERED, archived_at NULL) and embeds any row missing
a vector.

Idempotent — rows with a vector are skipped unless ``--force``.

Usage:

    python manage.py embed_narrative_memories                # missing only
    python manage.py embed_narrative_memories --force        # re-embed all
    python manage.py embed_narrative_memories --dry-run      # list only
    python manage.py embed_narrative_memories --memory <id>  # single row
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from apps.memory.models import NarrativeMemory, NarrativeMemoryStatus
from apps.memory.services import embed_memory


class Command(BaseCommand):
    help = "Embed active NarrativeMemory rows missing an embedding_vector."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-embed even if the row already has a vector.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="List target rows; do not call the provider.",
        )
        parser.add_argument(
            "--memory",
            metavar="UUID",
            default=None,
            help="Target a single memory row by id.",
        )
        parser.add_argument(
            "--include-archived",
            action="store_true",
            help=(
                "Include archived / superseded rows (retained "
                "vectors are still queryable via admin)."
            ),
        )

    def handle(self, *args, **opts) -> None:
        qs = NarrativeMemory.objects.all()
        if opts["memory"]:
            qs = qs.filter(pk=opts["memory"])
        else:
            if not opts["include_archived"]:
                qs = qs.filter(
                    status=NarrativeMemoryStatus.REMEMBERED,
                    archived_at__isnull=True,
                )
            if not opts["force"]:
                qs = qs.filter(embedding_vector__isnull=True)

        rows = list(qs.select_related("episode", "universe", "workspace"))
        self.stdout.write(f"targets: {len(rows)}")
        if not rows:
            return

        if opts["dry_run"]:
            for m in rows:
                self.stdout.write(
                    f"  {m.id} · {m.status} · has_vec={m.embedding_vector is not None} · "
                    f"body[:60]={m.body[:60]!r}"
                )
            return

        embedded = 0
        for m in rows:
            wrote = embed_memory(m, force=opts["force"])
            self.stdout.write(
                f"  {m.id} · wrote={wrote} · cost_micros={m.embedding_cost_micros}"
            )
            if wrote:
                embedded += 1
        self.stdout.write(self.style.SUCCESS(
            f"embedded {embedded}/{len(rows)}"
        ))
