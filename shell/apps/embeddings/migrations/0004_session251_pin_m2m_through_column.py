"""SESSION 251 — pin ``KnowledgeDocument.spokespeople`` M2M through
column to the physical ``spokesperson_id`` column.

Regression fix. SESSION 240 renamed the ``Spokesperson`` Django
class to ``Teammate`` (§17.1.b of the Canonical Identity Contract)
and preserved every persistence identifier via ``db_table`` on the
model itself — but the implicit M2M through on
``KnowledgeDocument.spokespeople`` was overlooked. Django computes
implicit-through join-table column names from the target class's
``_meta.model_name``, so after 0008 the ORM started emitting SQL
against ``embeddings_knowledgedocument_spokespeople.teammate_id``.
This surfaced two failure modes:

1. **Live DB drift** (pre-SESSION 240 DBs) — physical column is
   ``spokesperson_id`` (created before the rename); ORM queries
   ``teammate_id``; every endpoint that traversed the M2M returned
   HTTP 500 with ``psycopg.errors.UndefinedColumn``
   (``/api/workspace/overview/``, ``/api/knowledge/``, plus every
   downstream K2 retrieval consumer).

2. **Fresh DB drift** (post-SESSION 240 replays) — physical column
   is ``teammate_id`` (0002 CreateModel resolved the M2M target
   against the renamed class during migration replay); an ORM
   pinned to ``spokesperson_id`` would break there. Confirmed by
   inspecting a test DB after ``--create-db``.

Fix: swap the implicit M2M through for an explicit
``KnowledgeDocumentSpokesperson`` model whose ``teammate`` FK pins
``db_column="spokesperson_id"``, AND run an idempotent
``RENAME COLUMN teammate_id -> spokesperson_id`` guarded by
``information_schema.columns`` existence checks. The rename is a
no-op on live (already ``spokesperson_id``) and converges fresh
DBs (``teammate_id`` → ``spokesperson_id``). The auto-generated
index name keeps its identity across the rename because PG rewrites
indexed column references automatically. The FK constraint keeps
whatever name Django assigned at CreateModel time — functional
either way; we do not rename it.

The column contract is asserted by
``apps/embeddings/tests/test_m2m_through_column_contract.py`` so
this class of drift fails a test the next time it slips.
"""
from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


_RENAME_TEAMMATE_ID_TO_SPOKESPERSON_ID = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embeddings_knowledgedocument_spokespeople'
          AND column_name = 'teammate_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embeddings_knowledgedocument_spokespeople'
          AND column_name = 'spokesperson_id'
    ) THEN
        ALTER TABLE embeddings_knowledgedocument_spokespeople
        RENAME COLUMN teammate_id TO spokesperson_id;
    END IF;
END $$;
"""

# Reverse: rename spokesperson_id → teammate_id, only when needed.
# Kept for symmetry so ``migrate embeddings 0003`` doesn't fail.
_RENAME_SPOKESPERSON_ID_TO_TEAMMATE_ID = """
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embeddings_knowledgedocument_spokespeople'
          AND column_name = 'spokesperson_id'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'embeddings_knowledgedocument_spokespeople'
          AND column_name = 'teammate_id'
    ) THEN
        ALTER TABLE embeddings_knowledgedocument_spokespeople
        RENAME COLUMN spokesperson_id TO teammate_id;
    END IF;
END $$;
"""


class Migration(migrations.Migration):

    dependencies = [
        ("embeddings", "0003_alter_knowledgedocument_is_active"),
        ("spokespeople", "0009_alter_teammate_business_brief_and_more"),
    ]

    operations = [
        # Idempotent physical convergence. No-op on pre-SESSION 240
        # DBs (which already have ``spokesperson_id``); renames on
        # fresh DBs created post-SESSION 240 (which had
        # ``teammate_id`` because 0002 CreateModel resolved the
        # through-column name against the post-rename class).
        migrations.RunSQL(
            sql=_RENAME_TEAMMATE_ID_TO_SPOKESPERSON_ID,
            reverse_sql=_RENAME_SPOKESPERSON_ID_TO_TEAMMATE_ID,
        ),
        migrations.SeparateDatabaseAndState(
            state_operations=[
                migrations.CreateModel(
                    name="KnowledgeDocumentSpokesperson",
                    fields=[
                        (
                            "id",
                            models.BigAutoField(
                                auto_created=True,
                                primary_key=True,
                                serialize=False,
                                verbose_name="ID",
                            ),
                        ),
                        (
                            "knowledgedocument",
                            models.ForeignKey(
                                db_column="knowledgedocument_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                to="embeddings.knowledgedocument",
                            ),
                        ),
                        (
                            "teammate",
                            models.ForeignKey(
                                db_column="spokesperson_id",
                                on_delete=django.db.models.deletion.CASCADE,
                                to="spokespeople.teammate",
                            ),
                        ),
                    ],
                    options={
                        "db_table": "embeddings_knowledgedocument_spokespeople",
                    },
                ),
                migrations.AddConstraint(
                    model_name="knowledgedocumentspokesperson",
                    constraint=models.UniqueConstraint(
                        fields=("knowledgedocument", "teammate"),
                        name="embeddings_knowledgedocu_knowledgedocument_id_spo_e80c5133_uniq",
                    ),
                ),
                migrations.AlterField(
                    model_name="knowledgedocument",
                    name="spokespeople",
                    field=models.ManyToManyField(
                        blank=True,
                        related_name="knowledge_documents",
                        through="embeddings.KnowledgeDocumentSpokesperson",
                        to="spokespeople.teammate",
                    ),
                ),
            ],
            database_operations=[],
        ),
    ]
