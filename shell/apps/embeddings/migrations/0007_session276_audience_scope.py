# SESSION 276 Slice 5 / Delta Stage 1 — first-class audience field.
#
# Adds the ``KnowledgeDocument.audience_scope`` CharField as the
# smallest first step of Direction Delta (Slice 4 §50, §66). This
# migration is intentionally minimal:
#
#   * pure AddField, nullable, no default that would classify any row
#   * ZERO data migration / backfill — every existing row stays NULL
#   * NO retrieval predicate change (empty-M2M-broadcast semantics at
#     ``apps/embeddings/retrieval.py:216-220`` remain authoritative)
#   * NO mutation-surface change (ingestion / serializer / views /
#     admin / signals do not set the field yet)
#   * NO invariant enforcement (CHARACTER→M2M≥1, UNIVERSE→universe
#     non-null, etc. — all deferred to later Delta stages)
#
# NULL is a MIGRATION-ONLY state and does NOT mean WORKSPACE. Later
# stages will populate deterministic rows, extend mutation surfaces,
# switch retrieval to key on the field positively, and finally add
# CHECK/NOT NULL constraints.
#
# Reversal: dropping the field is a pure DDL step; no data restore is
# required because no row has been backfilled.
#
# See ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`` §46-§80
# for the full Delta design + staged rollout plan.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("embeddings", "0006_session275_deactivated_reason"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledgedocument",
            name="audience_scope",
            field=models.CharField(
                blank=True,
                choices=[
                    ("character", "Character-specific"),
                    ("universe", "Universe-shared"),
                    ("workspace", "Workspace-shared"),
                    ("none", "None — fail-closed"),
                ],
                default=None,
                help_text=(
                    "Delta Stage 1 first-class audience marker. NULL is a "
                    "MIGRATION-ONLY state during Delta rollout; NULL does "
                    "NOT mean WORKSPACE. Retrieval currently does not "
                    "consult this field. See "
                    "SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md."
                ),
                max_length=20,
                null=True,
            ),
        ),
    ]
