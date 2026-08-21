# SESSION 275 — audience-invariant enforcement.
#
# Adds ``KnowledgeDocument.deactivated_reason`` so soft-deleted rows
# distinguish operator-initiated deletes (``OPERATOR_DELETE``) from
# system-initiated orphan-archives (``ORPHANED_BY_TEAMMATE_DELETE``).
# The orphan-archive path is set by the new ``pre_delete`` signal on
# ``Teammate`` in ``apps.spokespeople.signals``; the operator-delete
# path is set by ``KnowledgeDocumentViewSet.destroy``.
#
# See ``docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md``
# §37 for the full implementation plan.
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("embeddings", "0005_universe_fk"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgedocument",
            name="deactivated_reason",
            field=models.CharField(
                blank=True,
                choices=[
                    ("operator_delete", "Operator deleted"),
                    (
                        "orphaned_by_teammate_delete",
                        "Orphaned by teammate delete",
                    ),
                ],
                default="",
                help_text=(
                    "Populated when ``is_active=False``. Blank when active. "
                    "Distinguishes operator soft-delete from system "
                    "orphan-archive."
                ),
                max_length=40,
            ),
        ),
    ]
