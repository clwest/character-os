"""B2.2 — Script synthesis tests.

Covers ``apps.scripts.synthesis.draft_script`` +
``snapshot_to_revision_history`` + ``apply_draft_to_script``.

Concerns:

1. Force-mock with knowledge → ScriptDraftResult with chunks +
   used_knowledge=True (rule 3).
2. Force-mock with NO knowledge → degraded path; empty chunks,
   used_knowledge=False, draft_text falls back to the prompt
   (rule 9).
3. Strict-mode verifier rejection → blocked status + warnings
   surface (rule 4); function does NOT raise.
4. Field-mapping correctness — brief → draft_text, chunk_ids →
   knowledge_chunk_ids, verification_status passes through.
5. opener kwarg propagates.
6. snapshot_to_revision_history appends chronologically.
7. snapshot_to_revision_history skips no-op (never-drafted row).
8. snapshot_to_revision_history preserves prior history.
9. apply_draft_to_script copies all draft fields.
10. apply_draft_to_script leaves status + approved_at untouched
    (regression guard — state machine owned by viewset).
"""
from __future__ import annotations

from unittest import mock

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.embeddings.ingestion import ingest_text
from apps.embeddings.models import DocumentStatus
from apps.embeddings.tasks import embed_document
from apps.scripts.models import Script
from apps.scripts.synthesis import (
    ScriptDraftResult,
    apply_draft_to_script,
    draft_script,
    snapshot_to_revision_history,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock_embeddings_and_eager():
    """Embeddings via mock path; Celery eager so ingest chunks
    land synchronously."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_teammate(
    ws: Workspace, *, name: str = "Riggs", brief: str = "Sell bells.",
) -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief=brief,
    )


def _ingest(ws: Workspace, title: str, body: str) -> None:
    # SESSION 276 Slice 20 — explicit workspace-shared audience signal.
    result = ingest_text(workspace=ws, title=title, content=body, workspace_shared_intent=True)
    embed_document.apply(args=[str(result.document.pk)])
    result.document.refresh_from_db()
    assert result.document.status == DocumentStatus.PROCESSED


def _make_script(ws: Workspace, sp: Teammate) -> Script:
    return Script.objects.create(
        workspace=ws, spokesperson=sp,
        name="test", prompt="x",
    )


# ---- draft_script: force-mock with knowledge --------------------


@override_settings(RENDER_SCRIPT_FORCE_MOCK=True)
def test_draft_script_force_mock_with_knowledge() -> None:
    """Rule 3 — citations persist as first-class data."""
    ws = _make_workspace("b22mk@test")
    sp = _make_teammate(ws)
    _ingest(ws, "doc-1", "Our bells are brass and ring at 110 dB.")

    result = draft_script(sp, "Tell viewers about our bells.")

    assert isinstance(result, ScriptDraftResult)
    assert result.used_knowledge is True
    assert len(result.knowledge_chunk_ids) >= 1
    assert result.draft_text  # non-empty
    assert "mock" in result.model
    # Mock embeds chunk ids in the draft for downstream assertions.
    assert "[knowledge:" in result.draft_text


# ---- draft_script: empty-knowledge degraded path ----------------


@override_settings(RENDER_SCRIPT_FORCE_MOCK=True)
def test_draft_script_empty_knowledge_degrades_to_prompt() -> None:
    """Rule 9 — empty knowledge degrades gracefully; the
    operator's prompt flows through verbatim as the draft."""
    ws = _make_workspace("b22ek@test")
    sp = _make_teammate(ws, brief="")

    result = draft_script(sp, "Just say something useful.")

    assert isinstance(result, ScriptDraftResult)
    assert result.used_knowledge is False
    assert result.knowledge_chunk_ids == []
    # Falls back to operator prompt (rule 9 / K6 contract rule 6).
    assert "Just say something useful." in result.draft_text


# ---- draft_script: strict-mode verifier rejection ---------------


def test_draft_script_strict_mode_returns_blocked_not_raises() -> None:
    """Rule 4 — strict-mode rejection persists as blocked
    instead of raising into the caller, so the Script row can
    show the operator what was rejected.
    """
    ws = _make_workspace("b22strict@test")
    sp = _make_teammate(ws)

    from character_os.claim_verifier import ClaimVerifierError, UnsupportedClaim

    unsupported = [
        UnsupportedClaim(
            claim="Wikipedia",
            kind="proper_noun",
            position=42,
        ),
    ]

    with mock.patch(
        "apps.scripts.synthesis.build_render_brief",
        side_effect=ClaimVerifierError(
            unsupported,
            synthesized_text="On Wikipedia we find the truth.",
        ),
    ):
        result = draft_script(sp, "Tell viewers about our process.")

    assert isinstance(result, ScriptDraftResult)
    assert result.verification_status == "blocked"
    assert result.draft_text == "On Wikipedia we find the truth."
    assert len(result.verification_warnings) == 1
    assert result.verification_warnings[0]["claim"] == "Wikipedia"
    assert result.used_knowledge is False


# ---- draft_script: field mapping --------------------------------


def test_draft_script_field_mapping_from_k6_shape() -> None:
    """brief → draft_text, chunk_ids → knowledge_chunk_ids,
    verification_status passes through unchanged.
    """
    ws = _make_workspace("b22map@test")
    sp = _make_teammate(ws)

    from character_os.script_synthesis import ScriptResult

    fake = ScriptResult(
        brief="The actual draft.",
        chunk_ids=["c1", "c2", "c3"],
        used_knowledge=True,
        model="gpt-5",
        tokens_input=1500,
        tokens_output=400,
        verification_warnings=[{"claim": "X", "kind": "proper_noun", "position": 0}],
        verification_status="warned",
    )

    with mock.patch(
        "apps.scripts.synthesis.build_render_brief",
        return_value=fake,
    ):
        result = draft_script(sp, "x")

    assert result.draft_text == "The actual draft."
    assert result.knowledge_chunk_ids == ["c1", "c2", "c3"]
    assert result.used_knowledge is True
    assert result.model == "gpt-5"
    assert result.tokens_input == 1500
    assert result.tokens_output == 400
    assert result.verification_status == "warned"
    assert len(result.verification_warnings) == 1


def test_draft_script_passes_opener_through() -> None:
    """K6.6 opener pin propagates to build_render_brief."""
    ws = _make_workspace("b22op@test")
    sp = _make_teammate(ws)

    from character_os.script_synthesis import ScriptResult

    with mock.patch(
        "apps.scripts.synthesis.build_render_brief",
        return_value=ScriptResult(brief="x"),
    ) as patched:
        draft_script(sp, "topic", opener="Here is the opener.")

    _, kwargs = patched.call_args
    assert kwargs.get("opener") == "Here is the opener."


def test_draft_script_passes_verifier_mode_through() -> None:
    """Per-script verifier mode override propagates."""
    ws = _make_workspace("b22vmm@test")
    sp = _make_teammate(ws)

    from character_os.script_synthesis import ScriptResult

    with mock.patch(
        "apps.scripts.synthesis.build_render_brief",
        return_value=ScriptResult(brief="x"),
    ) as patched:
        draft_script(sp, "topic", verifier_mode="strict")

    _, kwargs = patched.call_args
    assert kwargs.get("verifier_mode") == "strict"


# ---- snapshot_to_revision_history -------------------------------


def test_snapshot_appends_chronologically() -> None:
    """Append, not prepend — chronological order (oldest first)."""
    ws = _make_workspace("b22snap@test")
    sp = _make_teammate(ws)
    s = _make_script(ws, sp)
    s.draft_text = "first draft"
    s.knowledge_chunk_ids = ["c1"]
    s.model = "gpt-5"
    s.verification_status = "verified"
    s.tokens_input = 100
    s.tokens_output = 50
    s.save()

    snapshot_to_revision_history(s)
    s.save()

    assert len(s.revision_history) == 1
    entry = s.revision_history[0]
    assert entry["draft_text"] == "first draft"
    assert entry["knowledge_chunk_ids"] == ["c1"]
    assert entry["model"] == "gpt-5"
    assert entry["verification_status"] == "verified"
    assert entry["tokens_input"] == 100
    assert entry["tokens_output"] == 50
    assert "ts" in entry


def test_snapshot_preserves_prior_entries() -> None:
    """Rule 10 — revision_history entries never mutated."""
    ws = _make_workspace("b22prior@test")
    sp = _make_teammate(ws)
    s = _make_script(ws, sp)
    s.draft_text = "v1"
    s.model = "gpt-5"
    s.revision_history = [
        {"ts": "2026-05-19T00:00:00Z", "draft_text": "v0", "model": "gpt-5"}
    ]
    s.save()

    snapshot_to_revision_history(s)
    s.save()

    assert len(s.revision_history) == 2
    assert s.revision_history[0]["draft_text"] == "v0"  # untouched
    assert s.revision_history[1]["draft_text"] == "v1"  # appended


def test_snapshot_skips_never_drafted_row() -> None:
    """Idempotent on row that's never been drafted — no
    draft_text, no model, no prior history. Capturing an empty
    snapshot would just pollute the audit log.
    """
    ws = _make_workspace("b22skip@test")
    sp = _make_teammate(ws)
    s = _make_script(ws, sp)
    # draft_text, model, revision_history all empty by default.

    snapshot_to_revision_history(s)

    assert s.revision_history == []


def test_snapshot_captures_when_only_draft_text_set() -> None:
    """A row with a draft but no model (e.g. force-mock /
    degraded path) still gets snapshotted — the draft is the
    audit-worthy bit."""
    ws = _make_workspace("b22onlydraft@test")
    sp = _make_teammate(ws)
    s = _make_script(ws, sp)
    s.draft_text = "degraded fallback"
    s.save()

    snapshot_to_revision_history(s)
    s.save()

    assert len(s.revision_history) == 1
    assert s.revision_history[0]["draft_text"] == "degraded fallback"


# ---- apply_draft_to_script --------------------------------------


def test_apply_draft_copies_all_draft_fields() -> None:
    """Helper for B2.3 viewset — every field from
    ScriptDraftResult lands on the Script row."""
    ws = _make_workspace("b22apply@test")
    sp = _make_teammate(ws)
    s = _make_script(ws, sp)

    result = ScriptDraftResult(
        draft_text="final draft",
        knowledge_chunk_ids=["c1", "c2"],
        used_knowledge=True,
        model="gpt-5",
        tokens_input=2000,
        tokens_output=500,
        verification_status="warned",
        verification_warnings=[{"claim": "X", "kind": "x", "position": 0}],
    )
    apply_draft_to_script(s, result)

    assert s.draft_text == "final draft"
    assert s.knowledge_chunk_ids == ["c1", "c2"]
    assert s.model == "gpt-5"
    assert s.tokens_input == 2000
    assert s.tokens_output == 500
    assert s.verification_status == "warned"
    assert len(s.verification_warnings) == 1


def test_apply_draft_does_not_touch_status_or_approved_at() -> None:
    """Rule 10 — state machine owned by viewset, not synthesis.
    apply_draft_to_script must not mutate status / approved_at.
    """
    ws = _make_workspace("b22status@test")
    sp = _make_teammate(ws)
    s = _make_script(ws, sp)
    s.status = Script.Status.READY
    s.save()
    pre_status = s.status
    pre_approved_at = s.approved_at

    result = ScriptDraftResult(draft_text="x")
    apply_draft_to_script(s, result)

    assert s.status == pre_status
    assert s.approved_at == pre_approved_at
