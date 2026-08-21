"""SESSION 139 / K6 — render-time script synthesis tests.

Covers ``character_os.script_synthesis.build_render_brief``:

* Force-mock returns a deterministic shape including chunk IDs.
* Empty knowledge degrades to the operator prompt (contract
  rule 6).
* Knowledge present + force-mock surfaces ``used_knowledge=True``.
* Empty operator prompt + no business brief still produces a
  non-empty mock brief (defensive fallback).
* Real-mode without ``OPENAI_API_KEY`` degrades silently
  rather than raising (the render keeps working).
* OpenAI failure inside ``_call_responses_api`` degrades to
  the operator brief; chunk_ids are still populated for audit.

The real OpenAI Responses-API call is exercised manually via
the ``smoke_video`` end-to-end command with a real key. These
tests stay hermetic via force-mock or by patching the OpenAI
call directly.
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.embeddings.ingestion import ingest_text
from apps.embeddings.models import DocumentStatus
from apps.embeddings.tasks import embed_document
from apps.spokespeople.models import Teammate
from character_os.script_synthesis import (
    SCRIPT_MODEL,
    ScriptResult,
    build_render_brief,
)
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock_embeddings_and_eager():
    """Embedding calls go through the mock path so we don't need
    OPENAI_API_KEY for the ingest fixture, and Celery runs eagerly
    so chunks land synchronously before assertions."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _make_workspace(email: str, ws_name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = ws_name
    ws.save()
    return ws


def _make_teammate(ws: Workspace, name: str, brief: str = "") -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief=brief,
    )


def _ingest(ws: Workspace, title: str, body: str) -> str:
    """Create + embed a knowledge doc, return its id."""
    # SESSION 276 Slice 20 — explicit workspace-shared audience signal.
    result = ingest_text(workspace=ws, title=title, content=body, workspace_shared_intent=True)
    embed_document.apply(args=[str(result.document.pk)])
    result.document.refresh_from_db()
    assert result.document.status == DocumentStatus.PROCESSED
    return str(result.document.pk)


# ---- force-mock path -----------------------------------------------


@override_settings(RENDER_SCRIPT_FORCE_MOCK=True)
def test_force_mock_returns_deterministic_brief_with_knowledge() -> None:
    ws = _make_workspace("k6a@test", "K6 WS A")
    sp = _make_teammate(ws, "Riggs", brief="Sell bicycle bells.")

    _ingest(ws, "doc-1", "Our bells are brass and ring at 110 dB.")

    result = build_render_brief(sp, "Tell viewers what makes our bells special.")

    assert isinstance(result, ScriptResult)
    assert result.used_knowledge is True
    assert len(result.chunk_ids) >= 1
    # Mock brief embeds the chunk ids in a parseable shape so
    # downstream assertions (e2e, smoke) can verify citation flow.
    assert "[knowledge:" in result.brief
    assert result.chunk_ids[0] in result.brief
    # business_brief + operator_prompt both appear in mock output.
    assert "bicycle bells" in result.brief
    assert "Tell viewers" in result.brief
    assert "mock" in result.model


@override_settings(RENDER_SCRIPT_FORCE_MOCK=True)
def test_force_mock_empty_knowledge_returns_used_knowledge_false() -> None:
    ws = _make_workspace("k6b@test", "K6 WS B")
    sp = _make_teammate(ws, "Sasha", brief="Sales-tone spokesperson.")

    # No ingestion → no chunks visible to this spokesperson.
    result = build_render_brief(sp, "Make this video persuasive.")

    assert result.used_knowledge is False
    assert result.chunk_ids == []
    # Brief still contains the operator prompt + business brief.
    assert "Make this video persuasive." in result.brief
    assert "Sales-tone" in result.brief


@override_settings(RENDER_SCRIPT_FORCE_MOCK=True)
def test_force_mock_empty_prompt_and_brief_still_produces_string() -> None:
    """Defensive: even when the operator prompt is empty AND the
    business brief is empty, ``build_render_brief`` returns a
    non-empty string. The render flow should never crash from
    here."""
    ws = _make_workspace("k6c@test", "K6 WS C")
    sp = _make_teammate(ws, "Donny", brief="")
    result = build_render_brief(sp, "")
    assert result.brief  # non-empty
    assert "spokesperson=Donny" in result.brief


# ---- real-mode degradation (no OpenAI key) -------------------------


def test_real_mode_without_key_degrades_to_operator_prompt() -> None:
    """When force-mock is OFF, knowledge is visible, but
    OPENAI_API_KEY is unset, the render must still work — it
    falls back to the operator brief with no LLM call. Citation
    list is still populated (we know which chunks WOULD have
    been used)."""
    ws = _make_workspace("k6d@test", "K6 WS D")
    sp = _make_teammate(ws, "Maya", brief="Educator tone.")
    _ingest(ws, "doc-d", "Classroom-friendly content here.")

    old_key = os.environ.pop("OPENAI_API_KEY", None)
    try:
        with override_settings(RENDER_SCRIPT_FORCE_MOCK=False):
            result = build_render_brief(sp, "Explain photosynthesis.")
        assert result.used_knowledge is False
        assert len(result.chunk_ids) >= 1  # we know what we'd have used
        assert "Explain photosynthesis." in result.brief
    finally:
        if old_key is not None:
            os.environ["OPENAI_API_KEY"] = old_key


def test_real_mode_without_key_and_no_knowledge_returns_operator_prompt() -> None:
    ws = _make_workspace("k6e@test", "K6 WS E")
    sp = _make_teammate(ws, "Empty", brief="Generic brief.")

    old_key = os.environ.pop("OPENAI_API_KEY", None)
    try:
        with override_settings(RENDER_SCRIPT_FORCE_MOCK=False):
            result = build_render_brief(sp, "Just say something.")
        assert result.used_knowledge is False
        assert result.chunk_ids == []
        assert result.brief == "Just say something."
    finally:
        if old_key is not None:
            os.environ["OPENAI_API_KEY"] = old_key


# ---- LLM failure handling -----------------------------------------


def test_openai_failure_degrades_with_citations() -> None:
    """If the OpenAI call raises, we degrade to the operator
    brief but STILL record which chunks were retrieved — that's
    the audit signal for 'we tried to use these but the LLM
    fell over.'"""
    ws = _make_workspace("k6f@test", "K6 WS F")
    sp = _make_teammate(ws, "Riggs2", brief="Founder voice.")
    _ingest(ws, "doc-f", "Our product is brass bicycle bells.")

    # Pretend a key is present so we don't take the no-key branch.
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake-for-test"}):
        with override_settings(RENDER_SCRIPT_FORCE_MOCK=False):
            with patch(
                "character_os.script_synthesis._call_responses_api",
                side_effect=RuntimeError("simulated openai outage"),
            ):
                result = build_render_brief(sp, "Tell viewers about our bells.")

    assert result.used_knowledge is False
    assert len(result.chunk_ids) >= 1
    assert "Tell viewers about our bells." in result.brief


def test_real_mode_synthesis_returns_used_knowledge_true() -> None:
    """When the LLM call succeeds, ``used_knowledge=True`` and
    the model field reflects the real model used (no 'mock'
    suffix). The real responses.create is patched so the test
    stays hermetic."""
    ws = _make_workspace("k6g@test", "K6 WS G")
    sp = _make_teammate(ws, "Sasha2", brief="Sales tone.")
    _ingest(ws, "doc-g", "Black Friday: 30% off all bells.")

    fake_text = "Riggs here. Black Friday is on — 30% off our brass bells."

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake-for-test"}):
        with override_settings(RENDER_SCRIPT_FORCE_MOCK=False):
            with patch(
                "character_os.script_synthesis._call_responses_api",
                return_value=(fake_text, 120, 35),
            ):
                result = build_render_brief(sp, "Pitch the Black Friday sale.")

    assert result.used_knowledge is True
    assert result.brief == fake_text
    assert result.model == SCRIPT_MODEL
    assert result.tokens_input == 120
    assert result.tokens_output == 35
    assert len(result.chunk_ids) >= 1


# ---- retrieval failure handling -----------------------------------


def test_retrieval_failure_degrades() -> None:
    """If retrieval itself blows up (e.g., Postgres hiccup), we
    still return a usable brief — the render keeps working."""
    ws = _make_workspace("k6h@test", "K6 WS H")
    sp = _make_teammate(ws, "Retry", brief="Brief.")

    with override_settings(RENDER_SCRIPT_FORCE_MOCK=False):
        with patch(
            "character_os.script_synthesis.retrieve_for_teammate",
            side_effect=RuntimeError("db blip"),
        ):
            result = build_render_brief(sp, "Some prompt.")

    assert result.used_knowledge is False
    assert result.chunk_ids == []
    assert result.brief == "Some prompt."
