"""R1 isolation test — repo-level grep for unsanctioned
``RealtimeSession.objects`` / ``RealtimeToolInvocation.objects``
writes.

Mirrors ``apps/compositions/tests/test_isolation.py`` for the
realtime arc. The privacy guarantee depends on the write
surface staying narrow — every write path must run the
cross-workspace validation in ``models.py:clean()`` or in
``signals.py:reject_cross_workspace_*_references``.

The leak shape this prevents: a view, serializer, or ad-hoc
helper that does ``RealtimeSession.objects.create(...)`` or
``.update(...)`` outside the sanctioned writers — bypassing
the workspace-anchor validation.

Reads (``RealtimeSession.objects.filter(...)``) are not
concerning in v1 — they don't bypass any validation. This
test scopes to writes.
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest


# Files allowed to write to the realtime tables. Everything
# else is rejected. Adding a new entry is a code-review
# event — explain why the caller doesn't / cannot route
# through the broker (the eventual R3 surface) and what
# guarantees it preserves.
ALLOWED_FILES = {
    # Model definitions themselves.
    "apps/realtime/models.py",
    # Admin (read-mostly; raw create paths gate through
    # Django admin's form validation, which runs `clean()`).
    "apps/realtime/admin.py",
    # Tests need to create rows directly to exercise paths.
    "apps/realtime/tests/test_models.py",
    "apps/realtime/tests/test_isolation.py",
    # R3 broker tests seed RealtimeSession rows to exercise
    # the state machine + tier-limit path.
    "apps/realtime/tests/test_broker.py",
    # R3 broker writes RealtimeSession rows via the
    # sanctioned create/update path (workspace-scoped,
    # validation flows through the same signal).
    "apps/realtime/views.py",
    # R4 knowledge-bridge tests seed RealtimeSession rows
    # via the broker — same sanctioned path.
    "apps/realtime/tests/test_r4_knowledge_bridge.py",
    # R5 transcript-capture tests seed sessions to verify
    # the Celery task's post-end flow.
    "apps/realtime/tests/test_r5_transcript_capture.py",
    # R6 cross-session-memory tests seed ENDED sessions with
    # transcript_asset attached so the memory composer can
    # read them at compose time.
    "apps/realtime/tests/test_r6_session_memory.py",
}


WRITE_PATTERN = re.compile(
    r"\b(RealtimeSession|RealtimeToolInvocation)\.objects\."
    r"(create|update|update_or_create|get_or_create|bulk_create)\b"
)


def test_only_realtime_module_writes_realtime_tables() -> None:
    """Walk the repo; fail if any code outside the sanctioned
    files writes to the realtime tables.

    The privacy guarantees in ``apps.realtime.signals`` fire
    on ``pre_save`` — they cover every write path that flows
    through Django's ORM. But if a future caller skips
    validation by routing around the signal (raw SQL via
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
            "Forbidden realtime-table write outside the sanctioned surface:",
        ]
        msg_lines.extend(
            f"  {rel}:{lineno}  {snippet}"
            for rel, lineno, snippet in offenders[:10]
        )
        if len(offenders) > 10:
            msg_lines.append(f"  ... and {len(offenders) - 10} more")
        msg_lines.append(
            "RealtimeSession + RealtimeToolInvocation rows should be "
            "created by the R3 broker once it lands. Until then, the "
            "only sanctioned writers are the model file + admin + tests. "
            "If a legitimate new caller needs to be added, update "
            "ALLOWED_FILES in this test with a code-review note."
        )
        pytest.fail("\n".join(msg_lines))
