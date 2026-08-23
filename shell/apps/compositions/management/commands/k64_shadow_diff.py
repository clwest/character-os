"""K6.4 D-POS shadow diff reporter.

SESSION 278 Q-278-3.2. Reads recent compositions with either
``verification_warnings`` OR ``verification_warnings_shadow``
populated and prints an operator-readable OLD-ONLY / SHADOW-ONLY /
BOTH breakdown so the shadow-evaluation phase can be judged with
concrete deltas rather than eyeballing individual composition rows.

Usage::

    python manage.py k64_shadow_diff [--days=30] [--limit=50]
                                     [--workspace=<slug>]

Exit code is always 0 — this is a read-only report.

Only compositions where ``CHARACTER_OS_K64_NER_SHADOW_EXPERIMENT``
was truthy at synthesis time will have non-empty
``verification_warnings_shadow``. Legacy rows show OLD-ONLY / NEITHER
only.
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
        # Rows with EITHER column populated. `~` avoids requiring both.
        qs = qs.exclude(verification_warnings=[], verification_warnings_shadow=[])
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
            old = list(comp.verification_warnings or [])
            shadow = list(comp.verification_warnings_shadow or [])
            old_keys = {_claim_key(w): w for w in old}
            shadow_keys = {_claim_key(w): w for w in shadow}

            only_old_keys = set(old_keys) - set(shadow_keys)
            only_shadow_keys = set(shadow_keys) - set(old_keys)
            both_keys = set(old_keys) & set(shadow_keys)

            total_old_only += len(only_old_keys)
            total_shadow_only += len(only_shadow_keys)
            total_both += len(both_keys)

            header = (
                f"[{comp.created_at:%Y-%m-%d %H:%M}] "
                f"{comp.id}  {comp.template_kind}  "
                f"OLD={len(old)}  SHADOW={len(shadow)}  "
                f"BOTH={len(both_keys)}  OLD_ONLY={len(only_old_keys)}  "
                f"SHADOW_ONLY={len(only_shadow_keys)}"
            )
            self.stdout.write(self.style.HTTP_INFO(header))
            self.stdout.write(f"    name: {comp.name}")

            if only_old_keys:
                self.stdout.write("    OLD_ONLY (legacy flagged, shadow did not):")
                for k in sorted(only_old_keys, key=lambda x: (x[1] or 0, x[0])):
                    w = old_keys[k]
                    self.stdout.write(
                        f"      - {w.get('claim')!r:20} "
                        f"kind={w.get('kind')}  "
                        f"line={w.get('line_index')}  "
                        f"speaker={w.get('speaker_name') or w.get('speaker_alias')}"
                    )
            if only_shadow_keys:
                self.stdout.write("    SHADOW_ONLY (D-POS flagged, legacy did not):")
                for k in sorted(only_shadow_keys, key=lambda x: (x[1] or 0, x[0])):
                    w = shadow_keys[k]
                    self.stdout.write(
                        f"      - {w.get('claim')!r:20} "
                        f"kind={w.get('kind')}  "
                        f"line={w.get('line_index')}  "
                        f"speaker={w.get('speaker_name') or w.get('speaker_alias')}"
                    )
            if both_keys:
                self.stdout.write("    BOTH (agree):")
                for k in sorted(both_keys, key=lambda x: (x[1] or 0, x[0])):
                    w = old_keys[k]
                    self.stdout.write(
                        f"      - {w.get('claim')!r:20} "
                        f"line={w.get('line_index')}  "
                        f"speaker={w.get('speaker_name') or w.get('speaker_alias')}"
                    )
            self.stdout.write("")

        self.stdout.write(self.style.MIGRATE_HEADING("---- Aggregate ----"))
        self.stdout.write(
            f"  OLD_ONLY total   : {total_old_only:>4}  "
            "(ordinary-language false positives the shadow removed)"
        )
        self.stdout.write(
            f"  SHADOW_ONLY total: {total_shadow_only:>4}  "
            "(entities the shadow surfaces that legacy missed)"
        )
        self.stdout.write(
            f"  BOTH total       : {total_both:>4}  "
            "(both classifiers agree)"
        )
