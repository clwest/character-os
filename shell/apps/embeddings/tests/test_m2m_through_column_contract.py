"""SESSION 251 — regression: pin M2M through column names.

Guards against silent ORM ↔ physical-schema drift on the
``KnowledgeDocument.spokespeople`` M2M. SESSION 240 renamed the
target class ``Spokesperson`` → ``Teammate`` and preserved every
persistence identifier per CLAUDE.md §"Naming note", but the
implicit M2M through recomputes column names from the target's
``_meta.model_name`` — so before this session's fix the ORM was
querying ``teammate_id`` while the physical column is still
``spokesperson_id``. Every endpoint that traversed the M2M
crashed with ``psycopg.errors.UndefinedColumn``.

The explicit ``KnowledgeDocumentSpokesperson`` through model pins
``db_column="spokesperson_id"`` on the teammate FK. These tests
assert that pin — introspectively AND by running a real query
against the physical table — so future refactors can't silently
regress this.

If either test fails: the ORM will emit SQL against a column that
doesn't exist. Do not "fix" the tests by changing them. Fix the
model or the migration so the pin holds.
"""
from __future__ import annotations

import pytest

from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.embeddings.models import (
    KnowledgeDocument,
    KnowledgeDocumentSpokesperson,
)
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


def test_through_teammate_fk_db_column_is_spokesperson_id():
    """Introspective contract: the ``teammate`` FK on the through
    model MUST use ``db_column='spokesperson_id'``. This is the
    single line that stops the ORM from computing ``teammate_id``
    from the target class name."""
    fk = KnowledgeDocumentSpokesperson._meta.get_field("teammate")
    assert fk.db_column == "spokesperson_id", (
        f"KnowledgeDocumentSpokesperson.teammate.db_column must be "
        f"'spokesperson_id' — CLAUDE.md persistence-preservation "
        f"contract from SESSION 240. Got {fk.db_column!r}."
    )


def test_through_knowledgedocument_fk_db_column_is_pinned():
    """Companion to the teammate-side pin. Not strictly load-bearing
    today (Django's implicit column would already be
    ``knowledgedocument_id``) but pinning it here means a future
    rename of ``KnowledgeDocument`` cannot silently rename the
    physical column."""
    fk = KnowledgeDocumentSpokesperson._meta.get_field("knowledgedocument")
    assert fk.db_column == "knowledgedocument_id", (
        f"KnowledgeDocumentSpokesperson.knowledgedocument.db_column "
        f"must be 'knowledgedocument_id'. Got {fk.db_column!r}."
    )


def test_through_model_binds_to_physical_table():
    """The explicit through must map to the SAME physical table
    Django's implicit through created — otherwise attaches/detaches
    would silently start writing to a different table."""
    assert (
        KnowledgeDocumentSpokesperson._meta.db_table
        == "embeddings_knowledgedocument_spokespeople"
    )


def test_m2m_reverse_column_matches_physical_schema():
    """Django exposes M2M-side column names via
    ``field.m2m_reverse_name()``. Assert it resolves to the
    physical column, not the class-derived name. This is the exact
    layer that was emitting bad SQL before the fix."""
    field = KnowledgeDocument._meta.get_field("spokespeople")
    assert field.m2m_reverse_name() == "spokesperson_id", (
        f"M2M reverse column must resolve to 'spokesperson_id'. "
        f"Got {field.m2m_reverse_name()!r}. If this is 'teammate_id' "
        f"the ORM will emit SQL against a column that does not "
        f"exist and every knowledge/teammate M2M endpoint will 500."
    )
    assert field.m2m_column_name() == "knowledgedocument_id"


def test_knowledge_m2m_filter_runs_against_physical_db():
    """End-to-end regression. Runs the exact query shape that 500'd
    on ``/api/knowledge/?spokesperson=…`` before the fix. If the
    through column contract regresses this test will surface
    ``UndefinedColumn`` before any endpoint does."""
    # Workspace auto-provisions on User post_save.
    user = User.objects.create_user(email="m2m-regression@test", password="x")
    workspace = Workspace.objects.filter(owner=user).first()
    assert workspace is not None
    teammate = Teammate.objects.create(
        workspace=workspace,
        name="regression teammate",
    )
    # The filter itself is the assertion — if the column contract
    # is broken this call raises ``ProgrammingError`` /
    # ``UndefinedColumn``. Executing the queryset (list()) forces
    # SQL evaluation.
    list(KnowledgeDocument.objects.filter(spokespeople=teammate))

    # Reverse direction too — ``teammate.knowledge_documents.all()``
    # uses the same through table.
    list(teammate.knowledge_documents.all())
