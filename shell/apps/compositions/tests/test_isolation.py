"""V1 isolation test — repo-level grep for unsanctioned
``Asset.objects`` / ``CompositionStep.objects`` writes.

Mirrors ``apps/embeddings/tests/test_retrieval_privacy.py``'s
``test_only_retrieval_module_queries_chunk_tables`` pattern.

The composition-layer privacy guarantee depends on the
write surface staying narrow. Contract rule 3 (cross-
workspace asset reference rejection) is enforced by
``apps.compositions.signals`` + ``CompositionStep.clean()``.
Both fire on save paths going through the Django ORM.

The leak shape this test prevents: a view, serializer, or
ad-hoc helper that does ``Asset.objects.create(...)`` /
``CompositionStep.objects.create(...)`` /
``.update(...)`` outside the sanctioned writers — bypassing
the cross-workspace validation we depend on.

Reads (``Asset.objects.filter(...)``) are not concerning in
v1 — they don't bypass any validation. This test scopes to
writes that originate Asset / CompositionStep / Composition
rows.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# Files allowed to write to the composition tables. Everything
# else is rejected. Adding a new entry here is a code-review
# event — the entry should come with a note explaining why the
# caller doesn't / cannot route through the sanctioned path
# (the V2 runtime once it lands; until then this set is the
# entire write surface).
ALLOWED_FILES = {
    # Model definitions themselves
    "apps/compositions/models.py",
    # Admin (read-mostly; raw create paths are gated by Django
    # admin's own form validation, which runs clean())
    "apps/compositions/admin.py",
    # This test file + the model tests need to create rows
    "apps/compositions/tests/test_models.py",
    "apps/compositions/tests/test_isolation.py",
}


# Matches:
#   Asset.objects.create(...)
#   Asset.objects.update_or_create(...)
#   Composition.objects.create(...)
#   CompositionStep.objects.create(...)
#   Asset.objects.bulk_create(...)
#   etc.
WRITE_PATTERN = re.compile(
    r"\b(Asset|Composition|CompositionStep)\.objects\."
    r"(create|update|update_or_create|get_or_create|bulk_create)\b"
)


def test_only_composition_module_writes_composition_tables() -> None:
    """Walk the repo; fail if any code outside the sanctioned
    files writes to the composition tables.

    The privacy guarantees in ``apps.compositions.signals``
    fire on ``pre_save`` — they cover every write path that
    flows through Django's ORM. But if a future caller skips
    the validation by routing around the signal (raw SQL via
    ``cursor.execute``, or by importing a model and calling
    ``.objects.create`` directly from a context that hasn't
    been audited), the cross-workspace contract becomes a
    procedural one rather than a structural one.

    This test enforces the structural surface.
    """
    shell_root = Path(__file__).resolve().parents[3]
    assert shell_root.name == "shell", f"unexpected root: {shell_root}"

    offenders: list[tuple[str, int, str]] = []
    for py_path in shell_root.rglob("*.py"):
        rel = py_path.relative_to(shell_root).as_posix()

        if "/migrations/" in rel or rel.startswith("migrations/"):
            continue
        if rel.startswith(".venv/") or "/__pycache__/" in rel:
            continue
        if rel in ALLOWED_FILES:
            continue

        try:
            content = py_path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue

        for lineno, line in enumerate(content.splitlines(), start=1):
            if WRITE_PATTERN.search(line):
                offenders.append((rel, lineno, line.strip()))

    if offenders:
        msg_lines = [
            "Forbidden composition-table write outside the sanctioned surface:",
        ]
        msg_lines.extend(
            f"  {rel}:{lineno}  {snippet}"
            for rel, lineno, snippet in offenders[:10]
        )
        if len(offenders) > 10:
            msg_lines.append(f"  ... and {len(offenders) - 10} more")
        msg_lines.append(
            "Composition + Asset rows should be created by the V2 "
            "runtime once it lands. Until then, the only sanctioned "
            "writers are the model file + admin + tests. If a "
            "legitimate new caller needs to be added, update "
            "ALLOWED_FILES in this test with a code-review note."
        )
        pytest.fail("\n".join(msg_lines))
