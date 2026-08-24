"""K6.4 D-POS shadow diff reporter.

SESSION 278 Q-278-3.2 → refined Q-278-4.2. Reads recent compositions
with any of ``verification_warnings`` / ``verification_warnings_shadow``
/ ``verification_warnings_legacy`` populated and prints an
operator-readable LEGACY-ONLY / D-POS-ONLY / BOTH / AUTHORITY breakdown
so the shadow-evaluation phase can be judged with concrete deltas
rather than eyeballing individual composition rows.

Post-Q-278-4.2 semantics (dialogue-scene only):

* ``verification_warnings_shadow`` — always D-POS classifier output.
* ``verification_warnings_legacy`` — always legacy K6.4 output.
* ``verification_warnings`` — mirrors whichever classifier is
  authoritative per ``CHARACTER_OS_K64_DIALOGUE_AUTHORITY``.

Diff is computed between the two classifier-source columns
(``verification_warnings_shadow`` vs ``verification_warnings_legacy``)
so the report is stable under authority flips. The dispatcher-chosen
``verification_warnings`` column is displayed as the "AUTHORITY"
mirror indicator per row.

Legacy rows pre-Q-278-4.2 (populated before the new column shipped)
have ``verification_warnings_legacy = []`` — the report falls back to
comparing ``verification_warnings`` (assumed legacy) vs
``verification_warnings_shadow`` for those rows.

Usage::

    python manage.py k64_shadow_diff [--days=30] [--limit=50]
                                     [--workspace=<slug>]

Exit code is always 0 — this is a read-only report.
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.compositions.models import Composition


def _claim_key(warn: dict) -> tuple[str, int | None, str | None]:
    """Match key for cross-classifier comparison. Two claims are the
    same when (case-insensitive) claim text + line index + speaker
    alias line up. ``position`` deliberately excluded — spaCy tokenizes
    unicode punctuation slightly differently from the legacy regex."""
    return (
        (warn.get("claim") or "").lower(),
        warn.get("line_index"),
        warn.get("speaker_alias"),
    )


class Command(BaseCommand):
    help = (
        "Compare the legacy K6.4 verifier vs the D-POS shadow "
        "verifier across recent compositions. Read-only."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--days",
            type=int,
            default=30,
            help="Look back this many days (default: 30).",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help=(
                "Cap the number of compositions scanned per query "
                "(default: 50). Applied after the workspace + date "
                "filter."
            ),
        )
        parser.add_argument(
            "--workspace",
            default=None,
            help="Restrict to a workspace by slug. Default: all.",
        )

    def handle(self, *args, **options):
        days: int = options["days"]
        limit: int = options["limit"]
        workspace_slug: str | None = options["workspace"]

        cutoff = timezone.now() - timedelta(days=days)
        qs = Composition.objects.filter(created_at__gte=cutoff)
        if workspace_slug:
            qs = qs.filter(workspace__slug=workspace_slug)
        # Rows with ANY of the three columns populated. `.exclude()` with
        # multiple keyword arguments is an AND, so the compound match
        # excludes rows where ALL THREE are empty.
        qs = qs.exclude(
            verification_warnings=[],
            verification_warnings_shadow=[],
            verification_warnings_legacy=[],
        )
        qs = qs.order_by("-created_at")[:limit]

        rows = list(qs)
        if not rows:
            self.stdout.write(
                self.style.WARNING(
                    "No compositions with warnings in the last "
                    f"{days} day(s) (limit={limit}, workspace="
                    f"{workspace_slug or 'ALL'})."
                )
            )
            return

        total_old_only = 0
        total_shadow_only = 0
        total_both = 0

        self.stdout.write(
            self.style.MIGRATE_HEADING(
                f"K6.4 shadow diff — last {days} day(s), "
                f"{len(rows)} composition(s) with warnings\n"
            )
        )

        for comp in rows:
            authoritative = list(comp.verification_warnings or [])
            d_pos = list(comp.verification_warnings_shadow or [])
            legacy = list(comp.verification_warnings_legacy or [])

            # Pre-Q-278-4.2 rows have empty ``verification_warnings_legacy``.
            # Fall back to comparing ``verification_warnings`` (assumed
            # legacy pre-cutover) vs ``verification_warnings_shadow``.
            using_legacy_column = bool(legacy)
            if not using_legacy_column:
                legacy = authoritative

            legacy_keys = {_claim_key(w): w for w in legacy}
            d_pos_keys = {_claim_key(w): w for w in d_pos}

            only_legacy_keys = set(legacy_keys) - set(d_pos_keys)
            only_d_pos_keys = set(d_pos_keys) - set(legacy_keys)
            both_keys = set(legacy_keys) & set(d_pos_keys)

            total_old_only += len(only_legacy_keys)
            total_shadow_only += len(only_d_pos_keys)
            total_both += len(both_keys)

            # Infer authority per row by mirror equality.
            if not using_legacy_column:
                authority_tag = "legacy(pre-Q-278-4.2)"
            elif authoritative and authoritative == legacy:
                authority_tag = "legacy"
            elif authoritative and authoritative == d_pos:
                authority_tag = "d_pos"
            elif not authoritative:
                authority_tag = "clean"
            else:
                authority_tag = "unknown"

            header = (
                f"[{comp.created_at:%Y-%m-%d %H:%M}] "
                f"{comp.id}  {comp.template_kind}  "
                f"AUTH={authority_tag}  "
                f"LEGACY={len(legacy)}  D_POS={len(d_pos)}  "
                f"BOTH={len(both_keys)}  LEGACY_ONLY={len(only_legacy_keys)}  "
                f"D_POS_ONLY={len(only_d_pos_keys)}"
            )
            self.stdout.write(self.style.HTTP_INFO(header))
            self.stdout.write(f"    name: {comp.name}")

            if only_legacy_keys:
                self.stdout.write("    LEGACY_ONLY (legacy flagged, D-POS did not):")
                for k in sorted(only_legacy_keys, key=lambda x: (x[1] or 0, x[0])):
                    w = legacy_keys[k]
                    self.stdout.write(
                        f"      - {w.get('claim')!r:20} "
                        f"kind={w.get('kind')}  "
                        f"line={w.get('line_index')}  "
                        f"speaker={w.get('speaker_name') or w.get('speaker_alias')}"
                    )
            if only_d_pos_keys:
                self.stdout.write("    D_POS_ONLY (D-POS flagged, legacy did not):")
                for k in sorted(only_d_pos_keys, key=lambda x: (x[1] or 0, x[0])):
                    w = d_pos_keys[k]
                    self.stdout.write(
                        f"      - {w.get('claim')!r:20} "
                        f"kind={w.get('kind')}  "
                        f"line={w.get('line_index')}  "
                        f"speaker={w.get('speaker_name') or w.get('speaker_alias')}"
                    )
            if both_keys:
                self.stdout.write("    BOTH (agree):")
                for k in sorted(both_keys, key=lambda x: (x[1] or 0, x[0])):
                    w = legacy_keys[k]
                    self.stdout.write(
                        f"      - {w.get('claim')!r:20} "
                        f"line={w.get('line_index')}  "
                        f"speaker={w.get('speaker_name') or w.get('speaker_alias')}"
                    )
            self.stdout.write("")

        self.stdout.write(self.style.MIGRATE_HEADING("---- Aggregate ----"))
        self.stdout.write(
            f"  LEGACY_ONLY total: {total_old_only:>4}  "
            "(ordinary-language false positives D-POS removed)"
        )
        self.stdout.write(
            f"  D_POS_ONLY total : {total_shadow_only:>4}  "
            "(entities D-POS surfaces that legacy missed)"
        )
        self.stdout.write(
            f"  BOTH total       : {total_both:>4}  "
            "(both classifiers agree)"
        )
