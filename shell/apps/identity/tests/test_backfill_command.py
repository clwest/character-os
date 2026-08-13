"""3.c management-command tests — dry-run correctness, idempotency,
workspace filtering, --limit, --fail-fast, and per-teammate action
reporting.
"""
from __future__ import annotations

from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError

from apps.accounts.models import Workspace
from apps.identity.models import (
    CharacterIdentity,
    CharacterIdentityVersion,
    GenerationRecord,
    IdentityReference,
    ImportProvenance,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_teammate(ws: Workspace, **kwargs) -> Teammate:
    return Teammate.objects.create(workspace=ws, **kwargs)


def _run(**flags) -> str:
    """Call the command, capture stdout, return it as a string."""
    buf = StringIO()
    call_command("backfill_identity_substrate", stdout=buf, **flags)
    return buf.getvalue()


# ---- Dry-run correctness (Amendment F) -----------------------------


def test_dry_run_writes_nothing() -> None:
    ws = _make_workspace("cmd-dry-nothing@t")
    _make_teammate(ws, name="A", voice_id="voice_a")
    _make_teammate(ws, name="B")  # nothing to import
    _make_teammate(ws, name="C", portrait_path="bad-shape")
    out = _run(dry_run=True)
    assert "mode=dry-run" in out
    assert CharacterIdentity.objects.count() == 0
    assert CharacterIdentityVersion.objects.count() == 0
    assert IdentityReference.objects.count() == 0
    assert GenerationRecord.objects.count() == 0
    assert ImportProvenance.objects.count() == 0


def test_dry_run_reports_match_real_run_classifications() -> None:
    ws = _make_workspace("cmd-dry-match@t")
    _make_teammate(ws, name="A", voice_id="voice_a")
    _make_teammate(ws, name="B")  # nothing_to_import
    _make_teammate(ws, name="C", portrait_path="not-a-url")  # failed_incompatible

    dry_out = _run(dry_run=True)
    # Now run real. Because dry-run wrote nothing, real should
    # classify identically.
    real_out = _run()

    # Both outputs should mention the same action per teammate.
    for name, action in (("A", "imported"), ("B", "nothing_to_import"),
                        ("C", "failed_incompatible")):
        assert f"'{name}'" in dry_out
        assert f"'{name}'" in real_out
        # Extract the line with this teammate name from each.
        dry_line = next(line for line in dry_out.splitlines() if f"'{name}'" in line)
        real_line = next(line for line in real_out.splitlines() if f"'{name}'" in line)
        assert f"→ {action}" in dry_line
        assert f"→ {action}" in real_line


def test_summary_line_counts_by_action() -> None:
    ws = _make_workspace("cmd-summary@t")
    _make_teammate(ws, name="A", voice_id="v")
    _make_teammate(ws, name="B")
    _make_teammate(ws, name="C", portrait_path="junk")
    _make_teammate(ws, name="D", runway_avatar_id="avatar_d")
    out = _run()
    assert "imported                 2" in out
    assert "nothing_to_import        1" in out
    assert "failed_incompatible      1" in out
    assert "total                    4" in out


# ---- Idempotency (Amendment D) -------------------------------------


def test_second_run_reports_all_imported_teammates_as_already_imported() -> None:
    ws = _make_workspace("cmd-idempotent@t")
    _make_teammate(ws, name="A", voice_id="v_a")
    _make_teammate(ws, name="B", voice_id="v_b")
    _run()
    before = ImportProvenance.objects.count()
    assert before == 2

    out = _run()
    assert "already_imported         2" in out
    assert ImportProvenance.objects.count() == before  # unchanged


# ---- Workspace filter ---------------------------------------------


def test_workspace_filter_scopes_the_sweep() -> None:
    ws_a = _make_workspace("cmd-ws-a@t")
    ws_b = _make_workspace("cmd-ws-b@t")
    _make_teammate(ws_a, name="A", voice_id="v_a")
    _make_teammate(ws_b, name="B", voice_id="v_b")

    _run(workspace=str(ws_a.id))
    assert CharacterIdentity.objects.filter(workspace=ws_a).count() == 1
    assert CharacterIdentity.objects.filter(workspace=ws_b).count() == 0


def test_workspace_filter_rejects_non_uuid() -> None:
    with pytest.raises(CommandError):
        _run(workspace="not-a-uuid")


# ---- Limit --------------------------------------------------------


def test_limit_caps_number_of_teammates_processed() -> None:
    ws = _make_workspace("cmd-limit@t")
    for i in range(5):
        _make_teammate(ws, name=f"T{i}", voice_id=f"v_{i}")
    _run(limit=2)
    assert ImportProvenance.objects.count() == 2


# ---- Fail-fast ----------------------------------------------------


def test_fail_fast_halts_on_first_failed_incompatible() -> None:
    """Malformed classification (``failed_incompatible``) is a
    graceful classification result, NOT a runtime failure — the
    per-teammate transaction never opened. --fail-fast triggers
    only on ``failed`` (which comes from exception-during-import
    handling). Confirm the semantics with an actual failure.
    """
    ws = _make_workspace("cmd-fast-a@t")
    _make_teammate(ws, name="A", portrait_path="bad")  # failed_incompatible
    _make_teammate(ws, name="B", voice_id="v_b")
    _run(fail_fast=True)
    # A is failed_incompatible (not failed); B still imports.
    assert ImportProvenance.objects.count() == 1


def test_fail_fast_halts_on_real_failure(monkeypatch) -> None:
    """Force a real import-time exception on the first teammate;
    confirm the sweep halts before touching the second.
    """
    ws = _make_workspace("cmd-fast-real@t")
    _make_teammate(ws, name="A", voice_id="v_a")
    _make_teammate(ws, name="B", voice_id="v_b")

    from apps.identity import import_service

    original = import_service.import_legacy_teammate
    calls = {"n": 0}

    def _flaky(teammate, *, run_id, dry_run=False):
        calls["n"] += 1
        if calls["n"] == 1:
            # Return a ``failed`` result directly (as if the import
            # transaction raised and was caught).
            return import_service.ImportResult(
                teammate_id=teammate.id,
                action="failed",
                detail="simulated",
            )
        return original(teammate, run_id=run_id, dry_run=dry_run)

    monkeypatch.setattr(
        import_service, "import_legacy_teammate", _flaky,
    )
    _run(fail_fast=True)
    # Only the first call happened; second teammate untouched.
    assert calls["n"] == 1
    assert CharacterIdentity.objects.count() == 0


# ---- Empty database ------------------------------------------------


def test_no_teammates_reports_zero_across_all_actions() -> None:
    _make_workspace("cmd-empty-db@t")  # workspace only, no teammate
    out = _run()
    assert "total                    0" in out
    assert ImportProvenance.objects.count() == 0
