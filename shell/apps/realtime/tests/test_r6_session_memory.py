"""R6 tests — cross-session memory projection.

Three pieces this slice ships:

1. ``compose_session_memory(spokesperson, *, max_sessions=3)``
   — queries prior ENDED RealtimeSession rows with attached
   ``Asset(TRANSCRIPT)``, summarizes via gpt-5-mini, returns
   a MemoryResult with body + provenance.
2. ``REALTIME_MEMORY_FORCE_MOCK`` settings/env flag — sixth
   force-mock in the family. Settings beats env.
3. ``compose_realtime_document`` integration — memory body
   lands as a ``## Recent Conversations`` section between
   ``## About`` and ``## Knowledge``. Drops first under
   max_chars budget pressure (per scope-lock §R4).

Covered:

* No prior sessions → empty result, no LLM call.
* Force-mock → deterministic body, no LLM call, session
  ids preserved.
* Single prior session → memory body present, provenance
  includes the session id.
* Multiple prior sessions → ordered newest-first.
* ENDED sessions without ``transcript_asset`` are excluded.
* Non-ENDED sessions (READY/CREATING/FAILED) are excluded.
* Missing OPENAI_API_KEY → empty body, session ids still
  recorded (degradation path).
* OpenAI synthesis exception → empty body, session ids
  recorded.
* Other-workspace prior sessions never appear in this
  spokesperson's memory (privacy parity with K0).
* Composer injects ``## Recent Conversations`` when memory
  is present.
* Composer skips memory section entirely when no history.
* Composer drops memory first when max_chars would be
  exceeded (knowledge stays).
"""
from __future__ import annotations

from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.embeddings.models import (
    EMBEDDING_DIMENSION,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeChunk,
    KnowledgeDocument,
)
from apps.realtime.models import RealtimeSession
from apps.spokespeople.models import Spokesperson
from character_os.realtime_document import compose_realtime_document
from character_os.realtime_memory import (
    MemoryResult,
    compose_session_memory,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _mocks():
    """Mirror R4's fixture — force-mock embeddings so retrieval
    works in tests without OpenAI."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        REALTIME_MEMORY_FORCE_MOCK=False,  # explicit; tests opt-in
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _vec(seed: float) -> list[float]:
    v = [0.0] * EMBEDDING_DIMENSION
    v[0] = seed
    return v


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_spokesperson(
    ws: Workspace,
    *,
    name: str = "Sasha",
    brief: str = "Sells artisan bicycle bells.",
) -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id="av_test",
        portrait_path="https://fake/p.png",
        business_brief=brief,
    )


def _make_transcript_asset(
    ws: Workspace, *, text: str = "Operator: hi. Sasha: hi back.",
) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.TRANSCRIPT,
        file_path="",
        inline_content=text,
        source_spec={"primitive_kind": "realtime_transcript"},
        mime_type="text/plain",
        size_bytes=len(text.encode("utf-8")),
    )


def _make_ended_session(
    ws: Workspace,
    sp: Spokesperson,
    *,
    transcript_text: str = "Operator: hello. Sasha: hi there.",
    ended_at: datetime | None = None,
    status: str = RealtimeSession.Status.ENDED,
    attach_transcript: bool = True,
) -> RealtimeSession:
    asset = (
        _make_transcript_asset(ws, text=transcript_text)
        if attach_transcript
        else None
    )
    session = RealtimeSession.objects.create(
        workspace=ws,
        spokesperson=sp,
        status=status,
        started_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
        ended_at=ended_at or datetime(2026, 5, 14, 12, 5, tzinfo=timezone.utc),
        duration_seconds=300,
        provider_session_id="rt_x",
        transcript_asset=asset,
    )
    return session


# ---- compose_session_memory ------------------------------------


def test_no_prior_sessions_returns_empty_memory():
    ws, _u = _make_workspace("r6nohist@test")
    sp = _make_spokesperson(ws)
    result = compose_session_memory(sp)
    assert isinstance(result, MemoryResult)
    assert result.body == ""
    assert result.session_ids == []
    assert result.used_synthesis is False


def test_force_mock_returns_deterministic_stub():
    ws, _u = _make_workspace("r6fm@test")
    sp = _make_spokesperson(ws)
    session = _make_ended_session(ws, sp)
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_session_memory(sp)
    assert result.body  # non-empty
    assert sp.name in result.body
    assert str(session.id) in result.body  # provenance suffix
    assert result.session_ids == [str(session.id)]
    assert result.used_synthesis is True
    assert "mock" in result.model


def test_single_prior_session_summarized():
    """Real-mode path with a stubbed responses API call.
    Mirrors K6 + K9 — patch ``_call_responses_api`` so the
    test stays hermetic without touching the OpenAI SDK."""
    ws, _u = _make_workspace("r6single@test")
    sp = _make_spokesperson(ws)
    session = _make_ended_session(ws, sp)

    fake_text = "We talked about bicycle bells. Hi again!"
    import os as _os
    with patch.dict(_os.environ, {"OPENAI_API_KEY": "sk-fake-for-test"}):
        with override_settings(REALTIME_MEMORY_FORCE_MOCK=False):
            with patch(
                "character_os.realtime_memory._call_responses_api",
                return_value=(fake_text, 120, 18),
            ):
                result = compose_session_memory(sp)

    assert result.body == fake_text
    assert result.session_ids == [str(session.id)]
    assert result.used_synthesis is True
    from character_os.realtime_memory import MEMORY_MODEL
    assert result.model == MEMORY_MODEL
    assert result.tokens_input == 120
    assert result.tokens_output == 18


def test_multiple_prior_sessions_ordered_newest_first():
    ws, _u = _make_workspace("r6order@test")
    sp = _make_spokesperson(ws)
    oldest = _make_ended_session(
        ws, sp,
        transcript_text="Old conversation",
        ended_at=datetime(2026, 5, 10, 12, 0, tzinfo=timezone.utc),
    )
    middle = _make_ended_session(
        ws, sp,
        transcript_text="Middle conversation",
        ended_at=datetime(2026, 5, 12, 12, 0, tzinfo=timezone.utc),
    )
    newest = _make_ended_session(
        ws, sp,
        transcript_text="Recent conversation",
        ended_at=datetime(2026, 5, 14, 12, 0, tzinfo=timezone.utc),
    )
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_session_memory(sp)
    # All three present, newest-first ordering.
    assert result.session_ids == [
        str(newest.id), str(middle.id), str(oldest.id),
    ]


def test_max_sessions_cap_respected():
    ws, _u = _make_workspace("r6cap@test")
    sp = _make_spokesperson(ws)
    sessions = [
        _make_ended_session(
            ws, sp,
            transcript_text=f"Session {i}",
            ended_at=datetime(2026, 5, 1 + i, 12, 0, tzinfo=timezone.utc),
        )
        for i in range(5)
    ]
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_session_memory(sp, max_sessions=2)
    # Only the two newest land in the projection.
    assert result.session_ids == [
        str(sessions[4].id), str(sessions[3].id),
    ]


def test_ended_session_without_transcript_excluded():
    """A session that ENDED but never had its transcript
    persisted (R5 task failure / Runway didn't record) must
    not appear in memory."""
    ws, _u = _make_workspace("r6notr@test")
    sp = _make_spokesperson(ws)
    _make_ended_session(ws, sp, attach_transcript=False)
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_session_memory(sp)
    assert result.body == ""
    assert result.session_ids == []


def test_non_ended_sessions_with_transcript_included():
    """R6.1 (SESSION 152): the original R6 filtered by
    ``status=ENDED``. R7.3's ``attach_memory`` tool needs
    READY sessions with mid-session transcript snapshots
    to surface in next-session memory. After R6.1's widen,
    ANY session with a transcript_asset surfaces,
    regardless of status."""
    ws, _u = _make_workspace("r6nonend@test")
    sp = _make_spokesperson(ws)
    # Five non-ENDED sessions, each with a transcript
    # attached (simulating mid-session attach_memory commit
    # in different lifecycle states).
    expected_ids = []
    for st in (
        RealtimeSession.Status.READY,
        RealtimeSession.Status.CREATING,
        RealtimeSession.Status.FAILED,
        RealtimeSession.Status.NOT_READY,
        RealtimeSession.Status.DRAFT,
    ):
        s = _make_ended_session(ws, sp, status=st)
        expected_ids.append(str(s.id))
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        # Default max_sessions=3 — only the 3 newest land
        result = compose_session_memory(sp, max_sessions=5)
    assert len(result.session_ids) == 5
    assert set(result.session_ids) == set(expected_ids)


def test_sessions_without_transcript_still_excluded():
    """The transcript_asset filter still gates — any
    status without an Asset attached doesn't surface
    (no content to summarize)."""
    ws, _u = _make_workspace("r6noasset@test")
    sp = _make_spokesperson(ws)
    for st in (
        RealtimeSession.Status.READY,
        RealtimeSession.Status.ENDED,
        RealtimeSession.Status.FAILED,
    ):
        _make_ended_session(ws, sp, status=st, attach_transcript=False)
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_session_memory(sp)
    assert result.session_ids == []


def test_missing_openai_key_degrades_to_empty(monkeypatch):
    """Real-mode requested but no API key: empty body, but
    session ids still recorded for telemetry."""
    ws, _u = _make_workspace("r6nokey@test")
    sp = _make_spokesperson(ws)
    session = _make_ended_session(ws, sp)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=False):
        result = compose_session_memory(sp)
    assert result.body == ""
    assert result.session_ids == [str(session.id)]
    assert result.used_synthesis is False


def test_openai_failure_degrades_to_empty():
    """LLM call raises → empty body, session ids preserved
    for telemetry, no crash."""
    ws, _u = _make_workspace("r6fail@test")
    sp = _make_spokesperson(ws)
    session = _make_ended_session(ws, sp)
    import os as _os
    with patch.dict(_os.environ, {"OPENAI_API_KEY": "sk-fake-for-test"}):
        with override_settings(REALTIME_MEMORY_FORCE_MOCK=False):
            with patch(
                "character_os.realtime_memory._call_responses_api",
                side_effect=RuntimeError("api down"),
            ):
                result = compose_session_memory(sp)
    assert result.body == ""
    assert result.session_ids == [str(session.id)]
    assert result.used_synthesis is False


def test_other_workspace_sessions_excluded():
    """Workspace A's spokesperson must never see workspace
    B's prior sessions — privacy parity with K0."""
    ws_a, _ua = _make_workspace("r6wsa@test", "A")
    ws_b, _ub = _make_workspace("r6wsb@test", "B")
    sp_a = _make_spokesperson(ws_a, name="A-speaker")
    sp_b = _make_spokesperson(ws_b, name="B-speaker")
    _make_ended_session(
        ws_b, sp_b, transcript_text="B-workspace private chat",
    )
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_session_memory(sp_a)
    assert result.body == ""
    assert result.session_ids == []


# ---- compose_realtime_document integration ----------------------


def _make_doc_with_chunks(
    ws: Workspace, *, title: str, chunks: list[str], seed: float = 0.9,
) -> KnowledgeDocument:
    doc = KnowledgeDocument.objects.create(
        workspace=ws, title=title,
        document_type=DocumentType.TEXT,
        ingested_via=IngestedVia.PASTE,
        raw_content="\n\n".join(chunks),
        processed_content="\n\n".join(chunks),
        content_hash=f"hash-{title}-{seed}",
        status=DocumentStatus.PROCESSED,
    )
    for i, text in enumerate(chunks):
        KnowledgeChunk.objects.create(
            document=doc,
            chunk_index=i,
            chunk_text=text,
            chunk_size=len(text),
            embedding_vector=_vec(seed),
        )
    return doc


def test_composer_injects_memory_section_when_present():
    ws, _u = _make_workspace("r6cmp1@test")
    sp = _make_spokesperson(ws)
    session = _make_ended_session(ws, sp)
    _make_doc_with_chunks(
        ws, title="Pricing",
        chunks=["Premium tier is $99/mo."],
        seed=0.99,
    )
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_realtime_document(sp, top_k=10)
    assert "## Recent Conversations" in result.body
    assert "## About" in result.body
    assert "## Knowledge" in result.body
    assert result.memory_session_ids == [str(session.id)]
    # Section ordering: About → Recent Conversations → Knowledge
    about_idx = result.body.index("## About")
    memory_idx = result.body.index("## Recent Conversations")
    knowledge_idx = result.body.index("## Knowledge")
    assert about_idx < memory_idx < knowledge_idx


def test_composer_no_memory_section_when_no_history():
    """Fresh spokesperson, no prior sessions: composer skips
    the ``## Recent Conversations`` heading entirely."""
    ws, _u = _make_workspace("r6cmp2@test")
    sp = _make_spokesperson(ws)
    _make_doc_with_chunks(
        ws, title="FAQ", chunks=["Hours: 9-5 weekdays."],
        seed=0.99,
    )
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_realtime_document(sp, top_k=10)
    assert "## Recent Conversations" not in result.body
    assert "## Knowledge" in result.body
    assert result.memory_session_ids == []


def test_composer_drops_memory_first_under_budget():
    """Per scope-lock §R4 priority: when max_chars is too
    tight to fit memory + knowledge + header, memory drops
    first. Knowledge survives."""
    ws, _u = _make_workspace("r6cmp3@test")
    sp = _make_spokesperson(ws)
    _make_ended_session(ws, sp)
    _make_doc_with_chunks(
        ws, title="Tight", chunks=["Short chunk."], seed=0.99,
    )
    # Synthetic small budget. Header + About + Knowledge
    # heading + chunk should fit; memory pushes over. Mock
    # memory body alone is ~260 chars, so 250 forces the
    # drop while still leaving room for header + knowledge.
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_realtime_document(sp, top_k=10, max_chars=250)
    assert "## Recent Conversations" not in result.body
    assert "## Knowledge" in result.body
    assert "Short chunk." in result.body
    # Memory session_ids should be empty since the section
    # was dropped (composer only records what landed).
    assert result.memory_session_ids == []


def test_composer_no_knowledge_with_memory():
    """Memory + no knowledge: composer produces About +
    Recent Conversations, no Knowledge section."""
    ws, _u = _make_workspace("r6cmp4@test")
    sp = _make_spokesperson(ws)
    session = _make_ended_session(ws, sp)
    with override_settings(REALTIME_MEMORY_FORCE_MOCK=True):
        result = compose_realtime_document(sp, top_k=10)
    assert "## About" in result.body
    assert "## Recent Conversations" in result.body
    assert "## Knowledge" not in result.body
    assert result.memory_session_ids == [str(session.id)]
    assert result.chunk_ids == []
