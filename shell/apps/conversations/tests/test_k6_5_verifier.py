"""K6.5 (SESSION 162) — conversation synthesis verifier parity tests.

K6.4 shipped the post-synthesis claim verifier for video
script synthesis. K6.5 mirrors that into
``character_os.conversation_synthesis`` so the same
hallucination class can't leak through conversation
replies.

Covered:

* ``ReplyResult.verification_warnings`` is populated when
  the synthesized reply contains entities not in the corpus.
* Strict mode raises ``ClaimVerifierError`` (with
  ``synthesized_text``) instead of returning a result.
* Warn mode (default) persists ``verification_warnings`` on
  the SPOKESPERSON ``ConversationMessage`` and the API
  returns 201.
* Strict mode through the API view: 422 with the rejected
  text + claims; SPOKESPERSON placeholder message persisted;
  user message still recorded.
* Off mode (`K6_CLAIM_VERIFIER_MODE="off"`) bypasses the
  verifier — replies flow through, warnings stay empty.
* Operator's message content is in the corpus so terms the
  user introduced don't false-positive (parity with K6.4).
"""
from __future__ import annotations

import os
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.conversations.models import ConversationMessage, ConversationThread
from apps.embeddings.ingestion import ingest_text
from apps.embeddings.tasks import embed_document
from apps.spokespeople.models import Spokesperson
from character_os.claim_verifier import ClaimVerifierError
from character_os.conversation_synthesis import synthesize_spokesperson_reply

User = get_user_model()

pytestmark = pytest.mark.django_db


# Same fabrication-prone text we used in K6.4 tests.
DONNY_LIKE_REPLY = (
    "Drop a Wikipedia link into Character OS and the library "
    "doing the work is called trafilatura — Wikipedia is its "
    "absolute home turf."
)

RAG_DOC_EXCERPT = (
    "Retrieval-augmented generation (RAG) is a technique that "
    "enables large language models to retrieve and incorporate "
    "new information from external data sources. RAG improves "
    "LLMs by incorporating information retrieval before generating "
    "responses."
)


@pytest.fixture(autouse=True)
def _force_mock_embeddings_and_eager():
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _make_workspace(email: str, name: str = "K6.5 WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_spokesperson(ws: Workspace, name: str = "Donny") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws,
        name=name,
        runway_avatar_id="av-test",
        portrait_path="https://fake/p.png",
        business_brief="Documentary-style interviewer.",
    )


def _attach_doc(ws: Workspace, sp: Spokesperson, body: str = RAG_DOC_EXCERPT * 4) -> None:
    result = ingest_text(workspace=ws, title="RAG doc", content=body)
    embed_document.apply(args=[str(result.document.pk)])
    result.document.refresh_from_db()
    result.document.spokespeople.add(sp)


# ---------------------------------------------------------------
# synthesize_spokesperson_reply — unit-ish tests
# ---------------------------------------------------------------


def test_warn_mode_populates_verification_warnings() -> None:
    ws, _ = _make_workspace("k65a@test")
    sp = _make_spokesperson(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="warn",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(DONNY_LIKE_REPLY, 200, 80),
            ):
                result = synthesize_spokesperson_reply(thread, "Tell me about ingestion.")

    assert result.text == DONNY_LIKE_REPLY
    assert result.used_knowledge is True
    assert result.verification_warnings
    claims = {w["claim"] for w in result.verification_warnings}
    assert "Wikipedia" in claims


def test_strict_mode_raises_claim_verifier_error() -> None:
    ws, _ = _make_workspace("k65b@test")
    sp = _make_spokesperson(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="strict",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(DONNY_LIKE_REPLY, 200, 80),
            ):
                with pytest.raises(ClaimVerifierError) as exc_info:
                    synthesize_spokesperson_reply(thread, "Tell me about ingestion.")

    assert exc_info.value.synthesized_text == DONNY_LIKE_REPLY
    assert any(u.claim == "Wikipedia" for u in exc_info.value.unsupported)


def test_off_mode_bypasses_verifier() -> None:
    ws, _ = _make_workspace("k65c@test")
    sp = _make_spokesperson(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="off",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(DONNY_LIKE_REPLY, 200, 80),
            ):
                result = synthesize_spokesperson_reply(thread, "Tell me about ingestion.")

    assert result.text == DONNY_LIKE_REPLY
    assert result.verification_warnings == []


def test_user_message_terms_allow_listed() -> None:
    """User-introduced terms in their message should flow into
    the corpus so the reply can echo them. Mirrors K6.4's
    operator-prompt corpus contract."""
    ws, _ = _make_workspace("k65d@test")
    sp = _make_spokesperson(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    reply = "Wikipedia is a great source for general knowledge."

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="warn",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(reply, 200, 80),
            ):
                result = synthesize_spokesperson_reply(
                    thread, "Is Wikipedia a good source for your knowledge layer?",
                )

    claims = {w["claim"] for w in result.verification_warnings}
    assert "Wikipedia" not in claims, claims


# ---------------------------------------------------------------
# API view — strict mode 422 + warn mode persistence
# ---------------------------------------------------------------


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def test_api_warn_mode_persists_warnings_returns_201() -> None:
    ws, user = _make_workspace("k65api1@test")
    sp = _make_spokesperson(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    client = APIClient()
    _login(client, user)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="warn",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(DONNY_LIKE_REPLY, 200, 80),
            ):
                response = client.post(
                    f"/api/conversations/{thread.id}/messages/",
                    {"content": "Tell me about how your ingestion works."},
                    format="json",
                )

    assert response.status_code == http.HTTP_201_CREATED, response.data
    sp_msg_data = response.data["spokesperson_message"]
    assert sp_msg_data["content"] == DONNY_LIKE_REPLY
    assert sp_msg_data["verification_warnings"]
    claims = {w["claim"] for w in sp_msg_data["verification_warnings"]}
    assert "Wikipedia" in claims

    # Database confirms.
    sp_msg = ConversationMessage.objects.get(pk=sp_msg_data["id"])
    assert sp_msg.verification_warnings
    assert sp_msg.rejected_synthesis == ""  # not strict-rejected


def test_api_strict_mode_returns_422_with_rejected_synthesis() -> None:
    ws, user = _make_workspace("k65api2@test")
    sp = _make_spokesperson(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    client = APIClient()
    _login(client, user)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="strict",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(DONNY_LIKE_REPLY, 200, 80),
            ):
                response = client.post(
                    f"/api/conversations/{thread.id}/messages/",
                    {"content": "Tell me about how your ingestion works."},
                    format="json",
                )

    assert response.status_code == http.HTTP_422_UNPROCESSABLE_ENTITY, response.data
    assert response.data["verifier_rejection"]["mode"] == "strict"
    assert response.data["verifier_rejection"]["rejected_synthesis"] == DONNY_LIKE_REPLY
    rejected_claims = {
        c["claim"] for c in response.data["verifier_rejection"]["unsupported_claims"]
    }
    assert "Wikipedia" in rejected_claims

    # SPOKESPERSON placeholder + persistence.
    sp_msg_data = response.data["spokesperson_message"]
    assert "outside this workspace" in sp_msg_data["content"].lower()
    sp_msg = ConversationMessage.objects.get(pk=sp_msg_data["id"])
    assert sp_msg.rejected_synthesis == DONNY_LIKE_REPLY
    assert sp_msg.verification_warnings

    # User message still persisted.
    user_messages = thread.messages.filter(role=ConversationMessage.Role.USER)
    assert user_messages.count() == 1
