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
    # V2 runtime — the sanctioned writer for step-output Assets +
    # state-machine transitions. Cross-workspace validation
    # still flows through the V1 signal at save time.
    "apps/compositions/tasks.py",
    # V3 starter helpers — create Composition + first
    # CompositionStep rows from named recipes. Same workspace-
    # anchor guarantee as direct creation.
    "apps/compositions/starters.py",
    # V15.0 — recipe registry's custom resolver builds the
    # ``lines`` list for dialogue_scene (no direct ORM creates,
    # but it does call Spokesperson.objects.get).
    "apps/compositions/recipes.py",
    # V15.0 REST surface. The viewset calls each recipe's
    # starter; no direct ``.objects.create`` on composition
    # tables — Spokesperson/Asset ``.objects.get`` resolution
    # only.
    "apps/compositions/views.py",
    # Tests need to create rows directly to exercise paths
    "apps/compositions/tests/test_models.py",
    "apps/compositions/tests/test_isolation.py",
    "apps/compositions/tests/test_runtime.py",
    "apps/compositions/tests/test_primitive_avatar_speech.py",
    "apps/compositions/tests/test_primitive_visual_clip.py",
    "apps/compositions/tests/test_v5_long_form.py",
    "apps/compositions/tests/test_v7_composite.py",
    "apps/compositions/tests/test_v8_backdrop.py",
    "apps/compositions/tests/test_v9_polish.py",
    "apps/compositions/tests/test_v10_voice.py",
    "apps/compositions/tests/test_v11_style_remix.py",
    "apps/compositions/tests/test_v12_transcribe.py",
    "apps/compositions/tests/test_v13_storyboard.py",
    "apps/compositions/tests/test_v14_dialogue.py",
    "apps/compositions/tests/test_v15_api.py",
    "apps/compositions/tests/test_v16_remove_avatar_background.py",
    "apps/compositions/tests/test_v17_extend_visual_clip.py",
    "apps/compositions/tests/test_v17_cinematic_visual_extended.py",
    # F3 overview endpoint tests construct Composition rows
    # directly to exercise the dashboard cross-cut query path.
    "apps/accounts/tests/test_workspace_overview.py",
    # F5 lineage endpoint tests construct producer/consumer
    # composition graphs to exercise both lineage shapes.
    "apps/compositions/tests/test_f5_lineage.py",
    # F6 citation tests seed compositions with
    # knowledge_chunk_ids to exercise the doc resolver.
    "apps/compositions/tests/test_f6_citations.py",
    # F7 reverse-lookup tests seed compositions to verify
    # the doc → compositions reverse-query path.
    "apps/embeddings/tests/test_f7_compositions_reverse.py",
    # R1 tests construct Composition rows to exercise the
    # tool-invocation cross-workspace check
    # (produced_composition refs).
    "apps/realtime/tests/test_models.py",
    # R5 transcript-capture task creates Asset(TRANSCRIPT)
    # rows in the session's workspace. Sanctioned writer
    # — Asset.workspace inherits from session.workspace,
    # so the row is always in-workspace by construction.
    "apps/realtime/tasks.py",
    # R5 tests verify the task creates the right Asset
    # row + wires it to the session.
    "apps/realtime/tests/test_r5_transcript_capture.py",
    # R6 cross-session-memory tests seed Asset(TRANSCRIPT)
    # rows on the session's workspace to exercise the
    # memory composer's transcript-read path. Same
    # workspace-anchor guarantee as R5.
    "apps/realtime/tests/test_r6_session_memory.py",
    # R7.1 sync-tool tests seed Asset(TRANSCRIPT) rows to
    # exercise `recall_recent_conversations`. Same
    # workspace-anchor guarantee as R5/R6.
    "apps/realtime/tests/test_r7_1_sync_tools.py",
    # V6 — videos app shim tests construct Composition/Asset
    # rows directly to simulate terminal-state sync paths.
    "apps/videos/tests/test_v6_shim.py",
    # K6.4 v2 — stoplist watchdog tests seed Composition rows
    # with verification_warnings to exercise the warn-mode
    # "no text context" reporting branch. Read-only command
    # otherwise; no row mutation in the watchdog itself.
    "apps/compositions/tests/test_stoplist_watchdog.py",
    # W11.6.2 — image API tests seed Asset(IMAGE) rows directly
    # to exercise the list/retrieve/delete paths without firing
    # an end-to-end generation per row. The production write
    # path goes through ImageViewSet.create → MediaEngineClient
    # → Asset.objects.create in views.py (already sanctioned).
    "apps/compositions/tests/test_images_api.py",
    # Asset Library A1 (SESSION 185) — backfill management
    # command updates Asset.role on existing rows. Doesn't
    # touch workspace anchor; cross-workspace isolation
    # guarantee is unaffected by definition (the field being
    # written is role only).
    "apps/compositions/management/commands/backfill_asset_roles.py",
    "apps/compositions/tests/test_backfill_asset_roles.py",
    # Asset Library A2 (SESSION 186) — contract-rule-20 coverage
    # tests construct Composition + CompositionStep rows + drive
    # ``_persist_output_asset`` directly to verify the
    # PrimitiveResult.role → Asset.role round-trip + the runner's
    # raise-on-missing-role backstop. Uses _make_workspace +
    # Spokesperson + Composition.objects.create within the test
    # body; cross-workspace isolation guarantee is unaffected
    # (every row anchors to the same _make_workspace ws).
    "apps/compositions/tests/test_primitive_role_coverage.py",
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
