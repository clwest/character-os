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
from apps.spokespeople.models import Teammate
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


def _make_teammate(ws: Workspace, name: str = "Donny") -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        runway_avatar_id="av-test",
        portrait_path="https://fake/p.png",
        business_brief="Documentary-style interviewer.",
    )


def _attach_doc(ws: Workspace, sp: Teammate, body: str = RAG_DOC_EXCERPT * 4) -> None:
    # SESSION 276 Slice 20 — pass spokespeople to ingest_text so audience
    # is CHARACTER at creation. Prior "attach after" pattern created a
    # transitional NULL row that Slice 20's fresh-write closure rejects.
    result = ingest_text(workspace=ws, title="RAG doc", content=body, spokespeople=[sp])
    embed_document.apply(args=[str(result.document.pk)])
    result.document.refresh_from_db()


# ---------------------------------------------------------------
# synthesize_spokesperson_reply — unit-ish tests
# ---------------------------------------------------------------


def test_warn_mode_populates_verification_warnings() -> None:
    ws, _ = _make_workspace("k65a@test")
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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
    sp = _make_teammate(ws)
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


def test_user_message_terms_do_not_license_reply_claims() -> None:
    """SESSION 253 correction 1 — the user's message may itself
    contain unsupported assertions. A term appearing in the
    user prompt does NOT flow into the factual corpus and does
    NOT license the reply to make claims about it.

    Pre-SESSION-253 behavior (user-message terms allow-listed
    the reply) was explicitly removed for the same reason the
    K6 operator prompt was removed from the factual corpus:
    treating any input as evidence silently grounds its own
    assertions."""
    ws, _ = _make_workspace("k65d@test")
    sp = _make_teammate(ws)
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
    # Wikipedia is neither in the attached RAG doc nor in the
    # SESSION-253 allowed vocabulary — so it flags, even though
    # the user mentioned it.
    assert "Wikipedia" in claims, claims


# ---------------------------------------------------------------
# API view — strict mode 422 + warn mode persistence
# ---------------------------------------------------------------


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def test_api_warn_mode_persists_warnings_returns_201() -> None:
    ws, user = _make_workspace("k65api1@test")
    sp = _make_teammate(ws)
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


def test_verification_status_verified_on_clean_warn_k6_4_v1_2() -> None:
    """v1.2 — verifier ran in warn mode, no claims unsupported →
    verification_status='verified'."""
    ws, _ = _make_workspace("k64v12a@test")
    sp = _make_teammate(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    clean_reply = "I hear you. The docs lay out RAG plainly: retrieve, then generate."

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="warn",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(clean_reply, 100, 30),
            ):
                result = synthesize_spokesperson_reply(thread, "Explain RAG.")

    assert result.verification_status == "verified"


def test_verification_status_skipped_on_off_mode_k6_4_v1_2() -> None:
    ws, _ = _make_workspace("k64v12b@test")
    sp = _make_teammate(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="off",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(DONNY_LIKE_REPLY, 100, 30),
            ):
                result = synthesize_spokesperson_reply(thread, "Anything.")

    assert result.verification_status == "skipped"
    assert result.verification_warnings == []


def test_verification_status_trusted_passthrough_when_no_openai_key_k6_4_v1_2() -> None:
    ws, _ = _make_workspace("k64v12c@test")
    sp = _make_teammate(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    with patch.dict(os.environ, {}, clear=True):
        with override_settings(CONVERSATION_REPLY_FORCE_MOCK=False):
            result = synthesize_spokesperson_reply(thread, "Anything.")

    assert result.verification_status == "trusted_passthrough"
    assert result.used_knowledge is False


def test_api_strict_rejection_persists_status_rejected_k6_4_v1_2() -> None:
    """K6.4 v1.2 — strict-rejection placeholder spokesperson
    message carries verification_status='rejected' on the
    persisted row so the SPA can show a 'rejected' badge."""
    ws, user = _make_workspace("k64v12d@test")
    sp = _make_teammate(ws)
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
                return_value=(DONNY_LIKE_REPLY, 100, 30),
            ):
                response = client.post(
                    f"/api/conversations/{thread.id}/messages/",
                    {"content": "Anything."},
                    format="json",
                )

    assert response.status_code == http.HTTP_422_UNPROCESSABLE_ENTITY
    sp_msg = ConversationMessage.objects.get(pk=response.data["spokesperson_message"]["id"])
    assert sp_msg.verification_status == "rejected"


def test_api_per_request_verifier_mode_overrides_settings_k6_4_v1_1() -> None:
    """K6.4 v1.1 — operator can flip strict/warn/off per-request
    via the POST body without changing
    settings.K6_CLAIM_VERIFIER_MODE. Confirms the override path
    is wired all the way through view → synthesizer → verifier."""
    ws, user = _make_workspace("k64v11api@test")
    sp = _make_teammate(ws)
    _attach_doc(ws, sp)
    thread = ConversationThread.objects.create(spokesperson=sp)

    client = APIClient()
    _login(client, user)

    # Default mode = "off"; per-request = "strict" should rule.
    with patch.dict(os.environ, {"OPENAI_API_KEY": "sk-fake"}):
        with override_settings(
            CONVERSATION_REPLY_FORCE_MOCK=False,
            K6_CLAIM_VERIFIER_MODE="off",
        ):
            with patch(
                "character_os.conversation_synthesis._call_responses_api",
                return_value=(DONNY_LIKE_REPLY, 200, 80),
            ):
                response = client.post(
                    f"/api/conversations/{thread.id}/messages/",
                    {"content": "Tell me.", "verifier_mode": "strict"},
                    format="json",
                )

    # Per-request strict overrode settings off → 422.
    assert response.status_code == http.HTTP_422_UNPROCESSABLE_ENTITY


def test_api_invalid_verifier_mode_returns_400_k6_4_v1_1() -> None:
    ws, user = _make_workspace("k64v11bad@test")
    sp = _make_teammate(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)

    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/conversations/{thread.id}/messages/",
        {"content": "Hi", "verifier_mode": "totally-wrong"},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    assert "verifier_mode" in response.data


def test_api_strict_mode_returns_422_with_rejected_synthesis() -> None:
    ws, user = _make_workspace("k65api2@test")
    sp = _make_teammate(ws)
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
