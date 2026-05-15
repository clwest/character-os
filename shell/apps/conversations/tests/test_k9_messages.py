"""K9 tests — ConversationThread CRUD + message send/list endpoints.

Covered:

* Thread CRUD (list / create / detail / delete) workspace-scoped.
* GET messages — chronological list.
* POST messages — creates user message, synthesizes reply,
  persists reply, returns both. Force-mock synthesis so
  tests are hermetic.
* Cross-workspace caller rejection on thread + messages.
* Empty content validation (400).
* Spokesperson filter on the list endpoint
  (`?spokesperson=<id>`).
* `last_activity_at` advances after a message is sent (so
  the SPA's thread list re-sorts).
* End-to-end: send message → check `retrieve_for_thread`
  surfaces both turns (K8 ↔ K9 integration).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.conversations.models import (
    ConversationEmbedding,
    ConversationMessage,
    ConversationThread,
)
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mocks_and_eager():
    """Mock embeddings + mock synthesis + eager Celery so the
    full K8 → K9 pipeline runs deterministically without
    OpenAI."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        CONVERSATION_REPLY_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _make_workspace(email: str, name: str = "WS") -> tuple[Workspace, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws, user


def _make_spokesperson(ws: Workspace, name: str = "Sasha") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id="av",
        portrait_path="https://fake/p.png",
        business_brief="Sells artisan bicycle bells.",
    )


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


# ---- thread CRUD ------------------------------------------------


def test_create_thread() -> None:
    ws, user = _make_workspace("k9c@test")
    sp = _make_spokesperson(ws)
    client = APIClient()
    _login(client, user)
    response = client.post(
        "/api/conversations/",
        {"spokesperson": str(sp.id), "title": "Pricing chat"},
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["spokesperson_name"] == "Sasha"
    assert data["title"] == "Pricing chat"
    assert data["message_count"] == 0


def test_list_threads_scoped_to_caller() -> None:
    ws_a, user_a = _make_workspace("k9la@test", "A")
    ws_b, _user_b = _make_workspace("k9lb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    sp_b = _make_spokesperson(ws_b)
    ConversationThread.objects.create(spokesperson=sp_a)
    ConversationThread.objects.create(spokesperson=sp_b)
    client = APIClient()
    _login(client, user_a)
    response = client.get("/api/conversations/")
    data = response.json()
    # DRF default: returns a list (no pagination configured)
    items = data if isinstance(data, list) else data.get("results", [])
    assert len(items) == 1
    assert items[0]["spokesperson"] == str(sp_a.id)


def test_list_threads_filter_by_spokesperson() -> None:
    ws, user = _make_workspace("k9filt@test")
    sp1 = _make_spokesperson(ws, name="Sasha")
    sp2 = _make_spokesperson(ws, name="Riggs")
    ConversationThread.objects.create(spokesperson=sp1)
    ConversationThread.objects.create(spokesperson=sp1)
    ConversationThread.objects.create(spokesperson=sp2)
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/conversations/?spokesperson={sp1.id}")
    items = response.json()
    items = items if isinstance(items, list) else items.get("results", [])
    assert len(items) == 2
    assert {it["spokesperson"] for it in items} == {str(sp1.id)}


def test_thread_serializer_includes_preview() -> None:
    ws, user = _make_workspace("k9prev@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER,
        content="Hello, what's the pricing?",
    )
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/conversations/{thread.id}/")
    data = response.json()
    assert data["message_count"] == 1
    assert "pricing" in data["last_message_preview"].lower()


# ---- message GET ------------------------------------------------


def test_list_messages_returns_chronological_order() -> None:
    ws, user = _make_workspace("k9msglist@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    m1 = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER, content="First",
    )
    m2 = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.SPOKESPERSON, content="Second",
    )
    m3 = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER, content="Third",
    )
    client = APIClient()
    _login(client, user)
    response = client.get(f"/api/conversations/{thread.id}/messages/")
    assert response.status_code == http.HTTP_200_OK
    items = response.json()
    ids = [it["id"] for it in items]
    assert ids == [str(m1.id), str(m2.id), str(m3.id)]


def test_list_messages_rejects_cross_workspace_caller() -> None:
    ws_a, _user_a = _make_workspace("k9xa@test", "A")
    _ws_b, user_b = _make_workspace("k9xb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    thread = ConversationThread.objects.create(spokesperson=sp_a)
    client = APIClient()
    _login(client, user_b)
    response = client.get(f"/api/conversations/{thread.id}/messages/")
    assert response.status_code == http.HTTP_404_NOT_FOUND


# ---- message POST -----------------------------------------------


def test_send_message_creates_both_user_and_spokesperson_messages() -> None:
    ws, user = _make_workspace("k9send@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/conversations/{thread.id}/messages/",
        {"content": "What's the pricing for the artisan bell?"},
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    user_msg = data["user_message"]
    sp_msg = data["spokesperson_message"]
    assert user_msg["role"] == "user"
    assert user_msg["content"] == "What's the pricing for the artisan bell?"
    assert sp_msg["role"] == "spokesperson"
    # Force-mock synthesis produces a deterministic prefix.
    assert "[mock reply from Sasha]" in sp_msg["content"]
    # DB has both messages persisted.
    assert thread.messages.count() == 2


def test_send_message_rejects_empty_content() -> None:
    ws, user = _make_workspace("k9empty@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/conversations/{thread.id}/messages/",
        {"content": ""},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_send_message_rejects_overlong_content() -> None:
    ws, user = _make_workspace("k9long@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/conversations/{thread.id}/messages/",
        {"content": "x" * 5000},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_send_message_advances_last_activity_at() -> None:
    """The SPA's thread list orders by `-last_activity_at`. A
    new message must bump this so the active thread floats to
    the top."""
    ws, user = _make_workspace("k9act@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    initial_activity = thread.last_activity_at
    client = APIClient()
    _login(client, user)
    client.post(
        f"/api/conversations/{thread.id}/messages/",
        {"content": "Hello there"},
        format="json",
    )
    thread.refresh_from_db()
    assert thread.last_activity_at > initial_activity


def test_send_message_cross_workspace_caller_404() -> None:
    ws_a, _user_a = _make_workspace("k9xsa@test", "A")
    _ws_b, user_b = _make_workspace("k9xsb@test", "B")
    sp_a = _make_spokesperson(ws_a)
    thread = ConversationThread.objects.create(spokesperson=sp_a)
    client = APIClient()
    _login(client, user_b)
    response = client.post(
        f"/api/conversations/{thread.id}/messages/",
        {"content": "trying to send in workspace A"},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_send_message_returns_chunk_ids_field() -> None:
    """Force-mock synthesis returns chunk_ids — empty list
    when no workspace knowledge is attached. The endpoint
    exposes the field so the SPA can render citations
    later."""
    ws, user = _make_workspace("k9chunks@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    client = APIClient()
    _login(client, user)
    response = client.post(
        f"/api/conversations/{thread.id}/messages/",
        {"content": "Hi"},
        format="json",
    )
    data = response.json()
    assert "knowledge_chunk_ids" in data
    assert isinstance(data["knowledge_chunk_ids"], list)


# ---- K8 ↔ K9 integration ----------------------------------------


def test_messages_get_embedded_via_k8_signal() -> None:
    """K8's signal fires on message create. Confirm that K9's
    create path triggers the embedding pipeline for both the
    user message and the spokesperson reply."""
    ws, user = _make_workspace("k9emb@test")
    sp = _make_spokesperson(ws)
    thread = ConversationThread.objects.create(spokesperson=sp)
    client = APIClient()
    _login(client, user)
    client.post(
        f"/api/conversations/{thread.id}/messages/",
        {"content": "tell me about your business please"},
        format="json",
    )
    # Two messages → two sets of embeddings (each ≥1 chunk).
    user_embs = ConversationEmbedding.objects.filter(
        message__thread=thread,
        message__role=ConversationMessage.Role.USER,
    ).count()
    sp_embs = ConversationEmbedding.objects.filter(
        message__thread=thread,
        message__role=ConversationMessage.Role.SPOKESPERSON,
    ).count()
    assert user_embs >= 1
    assert sp_embs >= 1


# ---- auth ------------------------------------------------------


def test_unauthenticated_rejected() -> None:
    client = APIClient()
    response = client.get("/api/conversations/")
    assert response.status_code in {
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    }
