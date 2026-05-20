"""B2.1 — Script model tests.

Eight concerns:

1. Happy-path save with realistic FK shape.
2. Status enum coverage matches scope-lock state machine (rule 10).
3. VerificationStatus enum coverage matches K6.4 outcomes (rule 4).
4. Cross-workspace spokesperson rejected at clean() (rule 1).
5. Cross-workspace spokesperson rejected at pre_save signal.
6. Same-workspace happy path saves.
7. JSON field defaults are independent (list-default mutation
   guard — common Django gotcha).
8. ``approved_at`` defaults to NULL; ``draft_text`` /
   ``knowledge_chunk_ids`` allow empty (rule 9 degraded path).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

from apps.accounts.models import Workspace
from apps.scripts.models import Script
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _make_spokesperson(ws: Workspace, name: str = "Marcus") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test.",
    )


# ---- happy path -------------------------------------------------


def test_script_persists_with_realistic_fields() -> None:
    _, ws = _make_user_workspace("b21hp@test")
    sp = _make_spokesperson(ws)
    s = Script.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="Q3 launch script",
        prompt="30s about our new pricing",
    )
    assert s.id is not None
    assert s.status == Script.Status.DRAFT
    assert s.approved_at is None
    assert s.draft_text == ""
    assert s.opener == ""
    assert s.knowledge_chunk_ids == []
    assert s.revision_history == []
    assert s.verification_warnings == []
    assert s.tokens_input == 0
    assert s.tokens_output == 0
    assert s.verifier_mode == ""


def test_script_str_repr_includes_status_and_id_prefix() -> None:
    _, ws = _make_user_workspace("b21str@test")
    sp = _make_spokesperson(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="hello", prompt="x",
    )
    rendered = str(s)
    assert "[draft]" in rendered
    assert "hello" in rendered


# ---- enum coverage ---------------------------------------------


def test_script_status_enum_matches_scope_lock() -> None:
    """Rule 10 — forward-only DRAFT → READY → RENDERED → ARCHIVED."""
    expected = {"draft", "ready", "rendered", "archived"}
    actual = {choice for choice, _ in Script.Status.choices}
    assert actual == expected


def test_verification_status_enum_matches_k6_4() -> None:
    """Rule 4 — K6.4 outcomes surface on the row."""
    expected = {
        "verified", "warned", "skipped",
        "blocked", "trusted_passthrough",
    }
    actual = {
        choice for choice, _ in Script.VerificationStatus.choices
    }
    assert actual == expected


# ---- workspace isolation (rule 1) -------------------------------


def test_cross_workspace_spokesperson_rejected_at_clean() -> None:
    """Rule 1 — spokesperson + script must share a workspace."""
    _, ws_a = _make_user_workspace("b21iso_a@test")
    _, ws_b = _make_user_workspace("b21iso_b@test")
    sp_b = _make_spokesperson(ws_b, name="Bob")

    s = Script(
        workspace=ws_a, spokesperson=sp_b,
        name="leaky", prompt="x",
    )
    with pytest.raises(ValidationError) as exc:
        s.full_clean()
    assert "different workspace" in str(exc.value)


def test_cross_workspace_spokesperson_rejected_at_signal() -> None:
    """The pre_save signal catches the raw .save() path that
    skips clean() (mirrors apps.publish + apps.campaigns)."""
    _, ws_a = _make_user_workspace("b21sig_a@test")
    _, ws_b = _make_user_workspace("b21sig_b@test")
    sp_b = _make_spokesperson(ws_b, name="Bob")

    s = Script(
        workspace=ws_a, spokesperson=sp_b,
        name="leaky", prompt="x",
    )
    with pytest.raises(ValidationError):
        s.save()


def test_same_workspace_save_succeeds() -> None:
    _, ws = _make_user_workspace("b21ok@test")
    sp = _make_spokesperson(ws)
    s = Script(
        workspace=ws, spokesperson=sp,
        name="ok", prompt="x",
    )
    s.full_clean()
    s.save()
    assert s.pk is not None


# ---- JSON field defaults are independent (common gotcha) -------


def test_json_field_defaults_do_not_share_lists() -> None:
    """Bare ``default=[]`` is a classic Django footgun — all rows
    share the same list instance. ``default=list`` is the fix;
    this test pins it down.
    """
    _, ws = _make_user_workspace("b21json@test")
    sp = _make_spokesperson(ws)
    a = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="a", prompt="x",
    )
    b = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="b", prompt="y",
    )
    a.revision_history.append({"ts": "now", "draft_text": "v1"})
    a.save()
    b.refresh_from_db()
    assert b.revision_history == [], (
        "b's revision_history was mutated by a's append — list "
        "default is shared (regression of the bare-list footgun)"
    )


def test_revision_history_persists_across_save() -> None:
    _, ws = _make_user_workspace("b21revhist@test")
    sp = _make_spokesperson(ws)
    s = Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="x", prompt="x",
    )
    s.revision_history = [
        {
            "ts": "2026-05-20T17:00:00Z",
            "draft_text": "v1 draft",
            "knowledge_chunk_ids": ["c1", "c2"],
            "model": "gpt-5",
            "verification_status": "warned",
            "tokens_input": 100,
            "tokens_output": 50,
        }
    ]
    s.save()
    s.refresh_from_db()
    assert len(s.revision_history) == 1
    assert s.revision_history[0]["draft_text"] == "v1 draft"
    assert s.revision_history[0]["knowledge_chunk_ids"] == ["c1", "c2"]
