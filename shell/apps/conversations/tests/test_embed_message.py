"""K8 completion tests — `embed_message` Celery task + signal.

The K8 scope-lock said "Schema only. No SPA." That schema
landed during K2 alongside the doc models. What was missing
to make ``retrieve_for_thread`` useful: an actual message
embedding pipeline. K8 completion ships:

* ``apps.conversations.tasks.embed_message`` — mirrors K3's
  ``embed_document`` shape.
* Post-save signal on ``ConversationMessage`` enqueues the
  task.

Covered:

* Empty content → task no-ops with `skipped_empty`.
* Short message → one ConversationEmbedding row.
* Long message → multiple chunks (chunk_size=500).
* Both roles (USER + SPOKESPERSON) trigger the signal.
* Updates don't re-trigger (only create fires embedding).
* The full pipeline survives the retrieve_for_thread path —
  freshly-embedded messages show up in history retrieval.
* Idempotency — re-running the task wipes prior chunks
  cleanly.
* Signal can't 500 message creation when the broker is
  unreachable (best-effort enqueue).
"""
from __future__ import annotations

from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.conversations.models import (
    ConversationEmbedding,
    ConversationMessage,
    ConversationThread,
)
from apps.conversations.tasks import embed_message
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock_and_eager():
    """Mock embeddings + eager Celery — same shape as the
    K-arc tests in apps/embeddings."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
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


def _make_teammate(ws: Workspace) -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name="Sp", runway_avatar_id="av",
        portrait_path="https://fake/p.png", business_brief="b",
    )


def _make_thread(sp: Teammate) -> ConversationThread:
    return ConversationThread.objects.create(spokesperson=sp)


# ---- task-level behavior -----------------------------------------


def test_embed_message_short_message_creates_one_chunk() -> None:
    ws, _user = _make_workspace("k8short@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    msg = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER,
        content="Tell me about the spring launch.",
    )
    # The signal already fired (CELERY_TASK_ALWAYS_EAGER), so
    # embeddings exist. Re-running by hand is also fine.
    embeddings = ConversationEmbedding.objects.filter(message=msg)
    assert embeddings.count() == 1
    assert embeddings.first().chunk_index == 0


def test_embed_message_long_message_creates_multiple_chunks() -> None:
    """A 1500-char message should split into multiple chunks at
    the 500-char Q-k-1 boundary."""
    ws, _user = _make_workspace("k8long@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    # 1500 chars of sentences so the splitter has paragraph
    # boundaries to break on.
    long_content = (
        "This is sentence one of the first paragraph. " * 6 + "\n\n" +
        "This is sentence two of the second paragraph. " * 6 + "\n\n" +
        "Final paragraph rounds it out. " * 6
    )
    assert len(long_content) > 500
    msg = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER,
        content=long_content,
    )
    embeddings = ConversationEmbedding.objects.filter(message=msg)
    assert embeddings.count() >= 2
    # Indexes are 0-based + monotonic.
    indexes = list(embeddings.order_by("chunk_index").values_list(
        "chunk_index", flat=True,
    ))
    assert indexes == list(range(len(indexes)))


def test_embed_message_empty_content_is_no_op() -> None:
    ws, _user = _make_workspace("k8empty@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    # Empty content — signal short-circuits, task wouldn't be
    # called. To verify the task itself also no-ops, call it
    # directly with a message we built carefully.
    msg = ConversationMessage(
        thread=thread, role=ConversationMessage.Role.USER, content="",
    )
    # bypass the signal by saving with raw-like discipline
    msg.save()
    # Manually call the task; should skip.
    result = embed_message.apply(args=[str(msg.pk)]).get()
    assert result["status"] == "skipped_empty"
    assert ConversationEmbedding.objects.filter(message=msg).count() == 0


def test_embed_message_handles_unknown_id_gracefully() -> None:
    """Stale message ids (deleted between enqueue + run) should
    return not_found, not raise."""
    result = embed_message.apply(
        args=["11111111-1111-1111-1111-111111111111"],
    ).get()
    assert result["status"] == "not_found"


def test_embed_message_idempotent_on_rerun() -> None:
    """Re-running the task on a message that already has chunks
    should wipe + re-create them cleanly (useful for content
    edits or re-embedding after a model swap)."""
    ws, _user = _make_workspace("k8idem@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    msg = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER,
        content="One short message.",
    )
    first_count = ConversationEmbedding.objects.filter(message=msg).count()
    assert first_count == 1
    # Manual re-run via the task entry point.
    result = embed_message.apply(args=[str(msg.pk)]).get()
    assert result["status"] == "processed"
    assert ConversationEmbedding.objects.filter(message=msg).count() == 1


# ---- signal-level behavior ---------------------------------------


def test_signal_fires_for_user_role() -> None:
    ws, _user = _make_workspace("k8sigu@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    msg = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER,
        content="A user-side message.",
    )
    assert ConversationEmbedding.objects.filter(message=msg).count() >= 1


def test_signal_fires_for_spokesperson_role() -> None:
    """Teammate-side replies should also embed — context
    for the next turn pulls from prior assistant text too."""
    ws, _user = _make_workspace("k8sigs@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    msg = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.SPOKESPERSON,
        content="A spokesperson-side reply.",
    )
    assert ConversationEmbedding.objects.filter(message=msg).count() >= 1


def test_signal_does_not_refire_on_update() -> None:
    """Updates to an existing message should NOT re-trigger
    embedding — embedding cost is paid once. Test by capturing
    the embedding row's id before + after a non-content save."""
    ws, _user = _make_workspace("k8sigup@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    msg = ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER,
        content="Original content.",
    )
    original_ids = set(
        ConversationEmbedding.objects.filter(message=msg).values_list(
            "id", flat=True,
        )
    )
    assert len(original_ids) == 1
    # Save again without changing content.
    msg.save()
    after_ids = set(
        ConversationEmbedding.objects.filter(message=msg).values_list(
            "id", flat=True,
        )
    )
    assert after_ids == original_ids


def test_signal_swallows_broker_failure() -> None:
    """If the Celery broker is unreachable, message creation
    must NOT 500. Operator UX trumps embedding completeness on
    the create path."""
    ws, _user = _make_workspace("k8sigbroker@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    with patch(
        "apps.conversations.signals.embed_message.delay",
        side_effect=RuntimeError("broker down"),
    ):
        # Should not raise.
        msg = ConversationMessage.objects.create(
            thread=thread, role=ConversationMessage.Role.USER,
            content="Will not embed but should save.",
        )
    assert ConversationMessage.objects.filter(pk=msg.pk).exists()


# ---- retrieve_for_thread integration ----------------------------


def test_retrieve_for_thread_returns_newly_embedded_history() -> None:
    """End-to-end: create messages → embed via signal → retrieve
    surfaces them. Confirms the K8 pipeline closes the loop
    between message create and history retrieval."""
    from apps.embeddings.retrieval import retrieve_for_thread

    ws, _user = _make_workspace("k8retrieval@test")
    sp = _make_teammate(ws)
    thread = _make_thread(sp)
    ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.USER,
        content="First turn about launch dates.",
    )
    ConversationMessage.objects.create(
        thread=thread, role=ConversationMessage.Role.SPOKESPERSON,
        content="Our spring launch is in March.",
    )
    docs, history = retrieve_for_thread(
        thread, query="when is the launch",
        top_k_docs=3, top_k_history=5,
    )
    # Doc side is empty (no workspace knowledge in this test)
    assert docs == []
    # History side should surface both messages.
    assert len(history) == 2


def test_retrieve_for_thread_does_not_bleed_across_threads() -> None:
    """Cross-thread isolation — the K0 contract guarantee
    holds even when both threads share a spokesperson. Mirror
    of the K2 privacy test, but exercising K8's actual
    embedding pipeline rather than seeded rows."""
    from apps.embeddings.retrieval import retrieve_for_thread

    ws, _user = _make_workspace("k8nobleed@test")
    sp = _make_teammate(ws)
    thread_a = _make_thread(sp)
    thread_b = _make_thread(sp)
    ConversationMessage.objects.create(
        thread=thread_a, role=ConversationMessage.Role.USER,
        content="Thread A's private content.",
    )
    ConversationMessage.objects.create(
        thread=thread_b, role=ConversationMessage.Role.USER,
        content="Thread B's private content.",
    )
    _docs_a, history_a = retrieve_for_thread(
        thread_a, query="private content",
    )
    a_texts = {h.chunk_text for h in history_a}
    assert any("Thread A" in t for t in a_texts)
    assert not any("Thread B" in t for t in a_texts)
