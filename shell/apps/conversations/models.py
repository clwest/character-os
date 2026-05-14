"""Realtime conversations with a spokesperson.

A ``ConversationThread`` is a single chat session between one
user and one spokesperson. Messages are stored as
``ConversationMessage`` rows; each message is later embedded
into one or more ``ConversationEmbedding`` rows for retrieval.

SESSION 138 / K2 — conversation embeddings live in a
*separate table* from ``KnowledgeChunk`` (the upload
embeddings) by deliberate design. The privacy contract
(``docs/design/KNOWLEDGE_LAYER.md`` §"Contract rules" 4)
requires that the workspace-knowledge retrieval path
(``retrieve_for_spokesperson``) cannot reach conversation
turns and vice versa. Separate tables make the leak shape
structurally impossible — no discriminator filter to forget.
"""
from __future__ import annotations

import uuid

from django.db import models
from pgvector.django import HnswIndex, VectorField

from apps.spokespeople.models import Spokesperson


# Mirror the constants from ``apps.embeddings.models`` — kept in
# sync deliberately; conversation embeddings use the same
# OpenAI ``text-embedding-3-small`` model so the same retrieval
# vocabulary applies. Re-declared here (rather than imported)
# so this module has no dependency on the embeddings app.
EMBEDDING_MODEL_DEFAULT = "text-embedding-3-small"
EMBEDDING_DIMENSION = 1536


class ConversationThread(models.Model):
    """A realtime conversation thread with a spokesperson."""

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    spokesperson = models.ForeignKey(
        Spokesperson,
        on_delete=models.CASCADE,
        related_name="conversation_threads",
    )
    title = models.CharField(max_length=200, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)
    last_activity_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-last_activity_at"]
        indexes = [
            models.Index(fields=["spokesperson", "-last_activity_at"]),
        ]

    def __str__(self) -> str:
        label = self.title or f"Thread {str(self.id)[:8]}"
        return f"{label} ({self.spokesperson.name})"


class ConversationMessage(models.Model):
    """A single message (user-side or spokesperson-side) within
    a thread. Both roles are stored so the LLM can rebuild
    context on the next turn and so the retrieval layer can
    pull from past spokesperson responses, not just user input.
    """

    class Role(models.TextChoices):
        USER = "user", "User"
        SPOKESPERSON = "spokesperson", "Spokesperson"

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    thread = models.ForeignKey(
        ConversationThread,
        on_delete=models.CASCADE,
        related_name="messages",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["thread", "created_at"]
        indexes = [
            models.Index(fields=["thread", "created_at"]),
        ]

    def __str__(self) -> str:
        preview = self.content[:60].replace("\n", " ")
        return f"[{self.role}] {preview}"


class ConversationEmbedding(models.Model):
    """One embedded chunk of a ``ConversationMessage``.

    Conversation chunks are typically smaller than upload
    chunks because chat turns are short. The chunk size used
    at ingest time is settled in K8/K9 when the message-receive
    pipeline lands — see ``docs/design/KNOWLEDGE_LAYER.md``
    §"Open questions" Q-k-1.

    *No code outside ``apps.embeddings.retrieval`` should
    import this model* — contract rule 2, enforced by the
    repo-level grep test.
    """

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    message = models.ForeignKey(
        ConversationMessage,
        on_delete=models.CASCADE,
        related_name="embeddings",
    )

    chunk_index = models.PositiveIntegerField()
    chunk_text = models.TextField()
    chunk_size = models.PositiveIntegerField()

    embedding_vector = VectorField(dimensions=EMBEDDING_DIMENSION)
    embedding_model = models.CharField(
        max_length=100,
        default=EMBEDDING_MODEL_DEFAULT,
    )

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["message", "chunk_index"],
                name="conversation_embedding_unique_index",
            ),
        ]
        indexes = [
            HnswIndex(
                name="convemb_vec_hnsw_idx",
                fields=["embedding_vector"],
                m=16,
                ef_construction=64,
                opclasses=["vector_cosine_ops"],
            ),
        ]
        ordering = ["message", "chunk_index"]

    def __str__(self) -> str:
        return f"{self.message_id} #{self.chunk_index}"
