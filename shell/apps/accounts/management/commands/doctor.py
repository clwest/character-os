"""Runtime-truth doctor — refuses to open a slice when critical
operational documentation has silently drifted beyond the code it
describes.

**General project capability.** INVENTORY is the first consumer;
any future runtime-mirror doc opts in via frontmatter (see
"Opt-in convention" below) and doctor picks it up automatically.

Doctrine (SESSION 222, P1 2.4-a fold):

    "Critical operational documentation cannot silently drift
    beyond the code it describes."

The Character OS "runtime wins" convention has failed as memorized
discipline three times (S147, S151, S221). Each recurrence had the
same root cause: the discipline is real but no tool enforces it.
Doctor is that tool.

Opt-in convention
-----------------

A doc opts in to runtime-truth checking by carrying the following
YAML frontmatter fields:

    ---
    status: regenerated
    generated_at: <ISO-8601 timestamp>
    git_sha: <short sha, optionally followed by trailing annotation
             like " (working tree dirty)">
    ---

Doctor scans ``docs/**/*.md``, treats any doc whose frontmatter
sets ``status: regenerated`` as a runtime mirror, and asserts:

* ``git_sha`` short-hash equals the current ``HEAD`` short-hash
  — the clean case.
* On mismatch, the check falls through to ``generated_at``:
  * ``generated_at`` within ``--max-stale-age-days`` (default 7):
    advisory — same-session commits move HEAD faster than a
    regen is warranted; a fresh regen is recommended before
    pushing but does not block.
  * ``generated_at`` older than ``--max-stale-age-days``: blocking
    — the doc has silently drifted beyond the code across a
    session boundary. This is the S147/S151/S221 pathology.
* ``generated_at`` older than ``--max-age-days`` (default 30):
  advisory — regen recommended even when SHA matches (rare,
  but possible if the code hasn't changed in a month).

Trailing annotations after the SHA (e.g. "``(working tree dirty)``")
are stripped before comparison; they document generator state, not
git identity.

**Why age-gated instead of strict SHA equality?** Strict SHA
equality means every commit invalidates INVENTORY, which either
forces a regen after every commit (untenable) or produces false
positives on doctor (louder than useful). The pathology doctor
exists to catch is *bit-rot across session boundaries* (weeks
stale, dozens of commits behind), not intra-session drift. Age
is the right axis. Extension: a future version could add
ancestor-of-HEAD reachability checks (rejects rewritten branches)
without changing the primary block criterion.

Exit codes
----------

* ``0`` — clean (every runtime-mirror doc matches HEAD within age
  thresholds). Slice work may proceed.
* ``1`` — blocking drift found. Regenerate the reported doc(s)
  before opening the slice.

Usage
-----

    python manage.py doctor                 # human-readable report
    python manage.py doctor --json          # machine-readable output
    python manage.py doctor --max-age-days 7

Non-goals for v1
----------------

* Doctor does NOT regenerate docs. Regeneration is the domain of
  each doc's own generator (INVENTORY uses ``manage.py inventory``).
  Doctor points at the fix; it does not perform it.
* Doctor does NOT diff introspected values (model counts, route
  counts). If the doc regenerated at HEAD, its inputs are the same
  inputs the current code sees — a numeric divergence would mean
  the generator itself is broken, which is a bigger issue than
  drift.
* Doctor does NOT introspect commit contents. A commit that only
  touches docs/ still counts as drift in v1; the "smart" version
  that skips docs-only commits is a later extension.
"""
from __future__ import annotations

import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

_REPO_ROOT = Path(settings.BASE_DIR).resolve().parent
_DOCS_ROOT = _REPO_ROOT / "docs"


@dataclass(frozen=True)
class RuntimeMirrorCheck:
    """Result of checking one runtime-mirror doc against HEAD."""

    path: Path
    declared_sha: str | None
    head_sha: str | None
    generated_at: str | None
    age_days: float | None
    blocking: list[str] = field(default_factory=list)
    advisory: list[str] = field(default_factory=list)

    @property
    def clean(self) -> bool:
        return not self.blocking

    def to_dict(self) -> dict:
        try:
            path_str = str(self.path.relative_to(_REPO_ROOT))
        except ValueError:
            path_str = str(self.path)
        return {
            "path": path_str,
            "declared_sha": self.declared_sha,
            "head_sha": self.head_sha,
            "generated_at": self.generated_at,
            "age_days": (
                round(self.age_days, 2) if self.age_days is not None else None
            ),
            "blocking": list(self.blocking),
            "advisory": list(self.advisory),
        }


class Command(BaseCommand):
    help = (
        "Runtime-truth doctor. Refuses to open a slice when critical "
        "operational documentation has silently drifted beyond the "
        "code it describes."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit machine-readable JSON instead of human text.",
        )
        parser.add_argument(
            "--max-age-days",
            type=float,
            default=30.0,
            help=(
                "Advisory age threshold for regenerated docs whose "
                "SHA already matches HEAD. Age > threshold prints a "
                "warning but does not block."
            ),
        )
        parser.add_argument(
            "--max-stale-age-days",
            type=float,
            default=7.0,
            help=(
                "Blocking age threshold for regenerated docs whose "
                "SHA does NOT match HEAD. Age > threshold blocks "
                "(session-boundary bit-rot); age ≤ threshold is "
                "advisory (intra-session commits moving HEAD)."
            ),
        )
        parser.add_argument(
            "--docs-root",
            type=Path,
            default=None,
            help=(
                "Override the docs root path scanned for runtime-mirror "
                "docs. Defaults to ``<repo>/docs/``. Test seam."
            ),
        )
        parser.add_argument(
            "--head-sha",
            default=None,
            help=(
                "Override the HEAD sha (short form). Defaults to the "
                "current HEAD via ``git rev-parse --short HEAD``. "
                "Test seam."
            ),
        )

    def handle(self, *_, **opts) -> None:
        docs_root = opts["docs_root"] or _DOCS_ROOT
        head_sha = opts["head_sha"] or _current_head_sha()

        checks = run_doctor(
            docs_root=docs_root,
            head_sha=head_sha,
            max_age_days=opts["max_age_days"],
            max_stale_age_days=opts["max_stale_age_days"],
        )

        if opts["json"]:
            self.stdout.write(
                json.dumps(
                    {
                        "head_sha": head_sha,
                        "docs_root": str(docs_root),
                        "checks": [c.to_dict() for c in checks],
                        "blocking_count": sum(
                            1 for c in checks if c.blocking
                        ),
                        "clean": all(c.clean for c in checks),
                    },
                    indent=2,
                )
            )
        else:
            self._emit_text_report(checks, head_sha=head_sha)

        if any(c.blocking for c in checks):
            raise SystemExit(1)

    def _emit_text_report(
        self, checks: list[RuntimeMirrorCheck], *, head_sha: str
    ) -> None:
        self.stdout.write(f"doctor: HEAD={head_sha}")
        self.stdout.write(
            f"doctor: scanned {len(checks)} runtime-mirror doc(s)"
        )
        for check in checks:
            try:
                rel = check.path.relative_to(_REPO_ROOT)
            except ValueError:
                rel = check.path
            if check.blocking:
                self.stdout.write(f"  ✗ {rel}")
                for line in check.blocking:
                    self.stdout.write(f"      BLOCK: {line}")
                for line in check.advisory:
                    self.stdout.write(f"      warn:  {line}")
            elif check.advisory:
                self.stdout.write(f"  ! {rel}")
                for line in check.advisory:
                    self.stdout.write(f"      warn:  {line}")
            else:
                self.stdout.write(f"  ✓ {rel}")

        blocking = [c for c in checks if c.blocking]
        if blocking:
            self.stdout.write("")
            self.stdout.write(
                "doctor: BLOCKING DRIFT — do not open a new slice "
                "until every ✗ above is regenerated."
            )
        else:
            self.stdout.write("")
            self.stdout.write("doctor: clean.")


def run_doctor(
    *,
    docs_root: Path,
    head_sha: str,
    max_age_days: float,
    max_stale_age_days: float = 7.0,
) -> list[RuntimeMirrorCheck]:
    """Programmatic entry point. Returns one check per opted-in doc.

    Callers that want the exit-code semantics should inspect
    ``any(c.blocking for c in run_doctor(...))``.
    """
    results: list[RuntimeMirrorCheck] = []
    for doc in _iter_runtime_mirrors(docs_root):
        results.append(
            _check_one(
                doc,
                head_sha=head_sha,
                max_age_days=max_age_days,
                max_stale_age_days=max_stale_age_days,
            )
        )
    return results


def _iter_runtime_mirrors(docs_root: Path):
    """Yield (path, frontmatter_dict) for every ``.md`` file whose
    frontmatter declares ``status: regenerated``.
    """
    if not docs_root.exists():
        return
    for path in sorted(docs_root.rglob("*.md")):
        fm = _parse_frontmatter(path)
        if fm.get("status") == "regenerated":
            yield (path, fm)


def _check_one(
    doc: tuple[Path, dict],
    *,
    head_sha: str,
    max_age_days: float,
    max_stale_age_days: float,
) -> RuntimeMirrorCheck:
    path, fm = doc
    declared = _extract_sha(fm.get("git_sha"))
    generated_at = fm.get("generated_at")
    blocking: list[str] = []
    advisory: list[str] = []

    # Parse age first — downstream branches use it.
    age_days: float | None = None
    if generated_at:
        try:
            when = datetime.fromisoformat(generated_at.replace("Z", "+00:00"))
        except ValueError:
            advisory.append(
                f"generated_at={generated_at!r} is not ISO-8601 parseable"
            )
        else:
            if when.tzinfo is None:
                when = when.replace(tzinfo=timezone.utc)
            age_days = (
                datetime.now(timezone.utc) - when
            ).total_seconds() / 86400.0
    else:
        advisory.append(
            "no generated_at frontmatter — age cannot be checked"
        )

    sha_matches = declared is not None and declared == head_sha

    if declared is None:
        blocking.append(
            "frontmatter declares status=regenerated but no parseable "
            "git_sha field — cannot verify against HEAD"
        )
    elif not sha_matches:
        # SHA drift — block only if the doc is old enough to indicate
        # session-boundary bit-rot (S147/S151/S221 pathology). Fresh
        # SHA mismatches are treated as intra-session HEAD movement.
        if age_days is None:
            blocking.append(
                f"git_sha={declared!r} != HEAD={head_sha!r} and no "
                f"generated_at to gauge staleness — regenerate this doc"
            )
        elif age_days > max_stale_age_days:
            blocking.append(
                f"git_sha={declared!r} != HEAD={head_sha!r} AND "
                f"generated_at is {age_days:.1f}d old (block threshold "
                f"{max_stale_age_days:.0f}d) — regenerate this doc"
            )
        else:
            advisory.append(
                f"git_sha={declared!r} != HEAD={head_sha!r} "
                f"(regen was {age_days:.1f}d ago; block threshold "
                f"{max_stale_age_days:.0f}d) — regen recommended "
                f"before pushing"
            )

    if sha_matches and age_days is not None and age_days > max_age_days:
        advisory.append(
            f"generated_at is {age_days:.1f}d old "
            f"(threshold {max_age_days:.0f}d) — consider a fresh regen"
        )

    return RuntimeMirrorCheck(
        path=path,
        declared_sha=declared,
        head_sha=head_sha,
        generated_at=generated_at,
        age_days=age_days,
        blocking=blocking,
        advisory=advisory,
    )


def _parse_frontmatter(path: Path) -> dict:
    """Parse the leading ``--- ... ---`` YAML-ish frontmatter block.

    Deliberately does not depend on PyYAML — the runtime-mirror
    frontmatter we care about is flat ``key: value`` pairs. If a
    doc later needs richer frontmatter, teach this parser (and add
    a test) rather than pulling in a YAML dependency for one field.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return {}
    if not text.startswith("---"):
        return {}
    lines = text.splitlines()
    if len(lines) < 3 or lines[0].strip() != "---":
        return {}
    end = None
    for i, line in enumerate(lines[1:], start=1):
        if line.strip() == "---":
            end = i
            break
    if end is None:
        return {}
    out: dict[str, str] = {}
    for line in lines[1:end]:
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if ":" not in stripped:
            continue
        key, _, value = stripped.partition(":")
        out[key.strip()] = value.strip().strip('"').strip("'")
    return out


def _extract_sha(raw: str | None) -> str | None:
    """Return the short SHA prefix of a frontmatter git_sha field.

    Handles trailing annotations like ``"f542434 (working tree dirty)"``
    by taking only the first whitespace-delimited token.
    """
    if not raw:
        return None
    parts = raw.split()
    if not parts:
        return None
    token = parts[0].strip()
    return token or None


def _current_head_sha() -> str:
    """Read the short SHA of the current HEAD via git.

    Isolated so tests can bypass the subprocess call via
    ``--head-sha``.
    """
    result = subprocess.run(
        ["git", "rev-parse", "--short", "HEAD"],
        capture_output=True,
        text=True,
        cwd=_REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"doctor: could not read HEAD sha "
            f"(git returned {result.returncode}: {result.stderr.strip()})"
        )
    return result.stdout.strip()
