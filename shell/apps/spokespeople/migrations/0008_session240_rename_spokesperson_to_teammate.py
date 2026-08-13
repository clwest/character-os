"""SESSION 240 — Spokesperson → Teammate class rename.

Ratified §17.1.b of ``docs/design/visual/portrait_qualification/CANONICAL_IDENTITY_CONTRACT_V1.md``.

Renames the Django model class ``Spokesperson`` to ``Teammate``.
**Emits zero physical DDL.** The DB table remains
``spokespeople_spokesperson`` and the unique constraint remains
``spokesperson_unique_name_per_workspace`` — both preserved via
explicit ``db_table`` (pinned on the old model name here via
``AlterModelTable`` before the rename) and via the explicit
``db_table`` in ``Teammate.Meta`` post-rename.

Sequence:

1. ``AlterModelTable("spokesperson", "spokespeople_spokesperson")``
   — pin the explicit db_table on the old model so the subsequent
   RenameModel emits no physical ALTER TABLE (Django's RenameModel
   is a no-op when source and target db_table are identical).
2. ``RenameModel("Spokesperson", "Teammate")``.
3. ``AlterField(...related_name="teammates")`` — reverse-accessor
   rename per D1 ratification (state-only, no SQL).

Not wrapped in ``SeparateDatabaseAndState`` because that pattern
breaks fresh migration replay (historical migrations that
reference ``"spokespeople.spokesperson"`` as a string FK target
fail to resolve when the rename is purely state-only). Verified
with ``sqlmigrate spokespeople 0008`` — every operation reports
``(no-op)`` between BEGIN and COMMIT.
"""
from __future__ import annotations

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("accounts", "0001_initial"),
        ("spokespeople", "0007_session232_identity_fields"),
        # Every historical migration in another app that has an FK
        # to "spokespeople.spokesperson" (the pre-rename model
        # name) must run BEFORE this rename lands. Without these
        # explicit dependencies, Django's topological sort can
        # place the rename earlier in the graph — then those
        # historical migrations try to resolve
        # "spokespeople.spokesperson" against a state where the
        # model has already been renamed to Teammate, which fails.
        # Only historical migrations that literally string-
        # reference the old name are listed.
        ("videos", "0001_initial"),
        ("campaigns", "0001_initial"),
        ("compositions", "0001_initial"),
        ("compositions", "0006_w11_6_1_asset_image_fields"),
        ("conversations", "0001_initial"),
        ("embeddings", "0002_initial"),
        ("realtime", "0001_initial"),
        ("scripts", "0001_initial"),
    ]

    operations = [
        # Pin the explicit db_table on the pre-rename model so the
        # subsequent RenameModel operation sees "before and after
        # have the same db_table" and emits no physical rename.
        migrations.AlterModelTable(
            name="spokesperson",
            table="spokespeople_spokesperson",
        ),
        # Rename the model class. With db_table pinned above and in
        # the Meta of Teammate, Django's RenameModel emits no
        # physical ALTER TABLE.
        migrations.RenameModel(
            old_name="Spokesperson",
            new_name="Teammate",
        ),
        # Update the workspace FK's related_name from
        # ``spokespeople`` to ``teammates`` (D1 ratification).
        # State-only — reverse-accessor names are not persistence.
        migrations.AlterField(
            model_name="teammate",
            name="workspace",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="teammates",
                to="accounts.workspace",
            ),
        ),
    ]
