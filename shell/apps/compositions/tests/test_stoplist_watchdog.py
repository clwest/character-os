"""K6.4 stoplist watchdog management command tests.

SESSION 165. Anchors the watchdog's output shape so future
edits don't accidentally drop a section or break the
sentence-initial classification.

Coverage:
* Empty DB → empty report with the "stoplist coverage looks
  healthy" empty-state notes.
* Conversation message with a sentence-initial flag → token
  surfaces in SENTENCE-INITIAL CANDIDATES + a stoplist
  suggestion is emitted.
* Conversation message with a mid-sentence flag → token
  surfaces in MID-SENTENCE FLAGS (verifier doing its job).
* Composition warn-mode flag (no rejected_synthesis) → token
  surfaces in WARN-MODE COMPOSITION FLAGS (no text context).
* ``--days`` window excludes older events.
"""
from __future__ import annotations

from datetime import timedelta
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.utils import timezone

from apps.accounts.models import Workspace
from apps.compositions.models import Composition
from apps.conversations.models import (
    ConversationMessage,
    ConversationThread,
)
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_workspace(email: str = "wd@test", name: str = "Watchdog WS") -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_spokesperson(ws: Workspace) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name="Donny", runway_avatar_id="av",
        portrait_path="https://fake/p.png",
        business_brief="brief",
    )


def _run() -> str:
    buf = StringIO()
    call_command("stoplist_watchdog", "--days=30", "--limit=20", stdout=buf)
    return buf.getvalue()


def test_empty_db_renders_healthy_state() -> None:
    output = _run()
    assert "scanned 0 verifier-flagged event(s)" in output
    assert "stoplist coverage looks healthy" in output
    # No suggestion section when nothing to suggest.
    assert "Suggested additions" not in output


def test_sentence_initial_flag_surfaces_as_candidate() -> None:
    ws = _make_workspace("wd-si@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    # Sentence-initial false positive: "Alright" at start.
    text = "Alright — the docs lay out RAG plainly. RAG retrieves, then generates."
    ConversationMessage.objects.create(
        thread=thread,
        role=ConversationMessage.Role.SPOKESPERSON,
        content=text,
        verification_warnings=[
            {"claim": "Alright", "kind": "proper_noun", "position": 0},
        ],
        verification_status="verified",
    )

    output = _run()
    assert "SENTENCE-INITIAL CANDIDATES" in output
    assert "Alright" in output
    assert "Suggested additions" in output
    assert '"alright"' in output


def test_mid_sentence_flag_surfaces_as_doing_its_job() -> None:
    ws = _make_workspace("wd-mid@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    text = "I love Wikipedia for general knowledge."
    pos = text.index("Wikipedia")
    ConversationMessage.objects.create(
        thread=thread,
        role=ConversationMessage.Role.SPOKESPERSON,
        content=text,
        verification_warnings=[
            {"claim": "Wikipedia", "kind": "proper_noun", "position": pos},
        ],
        verification_status="verified",
    )

    output = _run()
    assert "MID-SENTENCE FLAGS" in output
    assert "Wikipedia" in output
    # Wikipedia is a real entity — should NOT show up in suggestions.
    if "Suggested additions" in output:
        # Suggestions section only appears when sentence_initial
        # has entries. If there's nothing sentence-initial, the
        # suggestions section is suppressed.
        assert '"wikipedia"' not in output


def test_warn_mode_composition_flag_lands_in_no_context_section() -> None:
    ws = _make_workspace("wd-ctx@test")
    sp = _make_spokesperson(ws)
    # Composition with verification_warnings but EMPTY
    # rejected_synthesis (warn-mode flag). No text context →
    # falls into the third bucket.
    Composition.objects.create(
        workspace=ws,
        spokesperson=sp,
        name="warn-flagged",
        template_kind="talking_head",
        verification_warnings=[
            {"claim": "Modernized", "kind": "proper_noun", "position": 5},
        ],
        verification_status="verified",
    )

    output = _run()
    assert "WARN-MODE COMPOSITION FLAGS" in output
    assert "Modernized" in output


def test_days_window_excludes_older_events() -> None:
    ws = _make_workspace("wd-old@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    msg = ConversationMessage.objects.create(
        thread=thread,
        role=ConversationMessage.Role.SPOKESPERSON,
        content="Alright — text.",
        verification_warnings=[
            {"claim": "Alright", "kind": "proper_noun", "position": 0},
        ],
        verification_status="verified",
    )
    # Backdate the row 60 days. auto_now_add fields need an update().
    old = timezone.now() - timedelta(days=60)
    ConversationMessage.objects.filter(pk=msg.pk).update(created_at=old)

    output = _run()
    assert "scanned 0 verifier-flagged event(s)" in output
