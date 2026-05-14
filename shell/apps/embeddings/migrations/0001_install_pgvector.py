"""SESSION 138 (K1) — install the pgvector extension.

Runs once against the Postgres database. Required before any model
in this app (K2 lands KnowledgeDocument + KnowledgeChunk) can use
VectorField. Idempotent — CreateExtension uses CREATE EXTENSION IF
NOT EXISTS under the hood.

apps.embeddings is the right place for this migration (not e.g.
apps.accounts) because pgvector exists *for* the embeddings app —
no other app uses VectorField. If sqlite ever needed to be
re-supported for a non-embeddings flow, only the embeddings app's
migrations would need to gate on engine.
"""
from django.contrib.postgres.operations import CreateExtension
from django.db import migrations


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        CreateExtension("vector"),
    ]
