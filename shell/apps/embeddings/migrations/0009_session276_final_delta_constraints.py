# SESSION 276 Slice 21 / Delta Stage 8 — final Delta constraint bridge.
#
# Closes the Delta audience-invariant rollout by:
#
#   1. Making ``KnowledgeDocument.audience_scope`` NOT NULL (removes
#      the Stage-1 transitional-NULL bridge state introduced by
#      migration 0007). Every persisted row must now carry one of
#      ``character`` / ``universe`` / ``workspace`` / ``none``.
#
#   2. Installing three scalar-column ``CheckConstraint`` entries
#      that encode the Slice 4 §51 Delta invariants which live
#      entirely on ``KnowledgeDocument`` scalar columns:
#
#        * ``session276_universe_requires_universe_fk``  — an
#          ``audience_scope='universe'`` row MUST have a non-NULL
#          ``universe_id``.
#        * ``session276_workspace_forbids_universe_fk`` — an
#          ``audience_scope='workspace'`` row MUST have a NULL
#          ``universe_id`` (WORKSPACE audience is the pre-Universe
#          legacy-broadcast semantic).
#        * ``session276_none_requires_inactive`` — an
#          ``audience_scope='none'`` row MUST have ``is_active=False``.
#          NONE is the terminal fail-closed audience per Slice 8
#          orphan-archive contract.
#
# The remaining Slice 4 §51 invariant — ``audience_scope='character'``
# requires the M2M ``spokespeople`` set to be non-empty — is
# INTENTIONALLY NOT encoded here. The M2M lives in a separate
# through-table (``embeddings_knowledgedocument_spokespeople``) and a
# row-level CHECK on ``KnowledgeDocument`` cannot inspect through-table
# state. That invariant is enforced comprehensively at the application
# layer by SESSION 276 Slices 8, 10, 13, 14, 15, and 20 at every
# mutation surface. Adding a PostgreSQL trigger would duplicate that
# coverage without providing marginal safety. See
# ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`` §361 for
# the full DB-scalar vs application-layer enforcement distinction.
#
# **Backfill:** none required. Slice 20 executed a full DB reset via
# ``KnowledgeDocument.objects.all().delete()`` (§357), producing a
# zero-row table. Slice 20 also closed the fresh-write NULL loophole
# at both the DRF serializer boundary (`audience_scope_required_on_create`
# 4xx) and the ``ingestion._persist`` boundary
# (``DjangoValidationError`` raise), so no new NULL row can enter the
# table between Slice 20's reset and this migration. The
# ``AlterField(null=False)`` operation applies cleanly on an empty
# table.
#
# **Reversal:** reversing this migration restores the nullable field
# and drops the three constraints. Any post-Slice-21 rows that
# depend on the NOT NULL guarantee could then re-enter transitional
# state; the reversal is safe only if no downstream code assumes the
# permanent shape.
#
# See ``docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md`` §353-§368
# for the full Slice 20 preparation + §361.2 recommended architecture.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("embeddings", "0008_session276_stage2_backfill"),
    ]

    operations = [
        migrations.AlterField(
            model_name="knowledgedocument",
            name="audience_scope",
            field=models.CharField(
                choices=[
                    ("character", "Character-specific"),
                    ("universe", "Universe-shared"),
                    ("workspace", "Workspace-shared"),
                    ("none", "None — fail-closed"),
                ],
                help_text=(
                    "Delta first-class audience marker. Permanent "
                    "post-SESSION-276: every row is one of CHARACTER / "
                    "UNIVERSE / WORKSPACE / NONE. NULL is unrepresentable. "
                    "See SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md §353-§368."
                ),
                max_length=20,
            ),
        ),
        migrations.AddConstraint(
            model_name="knowledgedocument",
            constraint=models.CheckConstraint(
                # UNIVERSE audience requires a non-null universe FK.
                # Equivalent SQL: audience_scope <> 'universe' OR
                # universe_id IS NOT NULL.
                condition=(
                    ~models.Q(audience_scope="universe")
                    | models.Q(universe_id__isnull=False)
                ),
                name="session276_universe_requires_universe_fk",
            ),
        ),
        migrations.AddConstraint(
            model_name="knowledgedocument",
            constraint=models.CheckConstraint(
                # WORKSPACE audience requires a NULL universe FK
                # (WORKSPACE is the pre-Universe legacy broadcast).
                # SQL: audience_scope <> 'workspace' OR
                # universe_id IS NULL.
                condition=(
                    ~models.Q(audience_scope="workspace")
                    | models.Q(universe_id__isnull=True)
                ),
                name="session276_workspace_forbids_universe_fk",
            ),
        ),
        migrations.AddConstraint(
            model_name="knowledgedocument",
            constraint=models.CheckConstraint(
                # NONE audience requires is_active=False (Slice 8
                # orphan-archive contract). SQL: audience_scope <>
                # 'none' OR is_active = FALSE.
                condition=(
                    ~models.Q(audience_scope="none")
                    | models.Q(is_active=False)
                ),
                name="session276_none_requires_inactive",
            ),
        ),
    ]
