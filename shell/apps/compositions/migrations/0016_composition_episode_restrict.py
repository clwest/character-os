# EPISODE_SCHEMA_V1 (SESSION 262) — Composition.episode PROTECT → RESTRICT.
#
# Design deviation from EPISODE_SCHEMA_V1.md §Q7 draft's PROTECT
# choice. Under Django 3.1+, RESTRICT participates in the
# shared-CASCADE-parent rule but PROTECT does not — Workspace
# cascade-delete would fail with PROTECT because Composition is
# cascaded via Workspace but Episode is cascaded via Universe;
# PROTECT does not treat this pair as "same cascade." Switching to
# RESTRICT preserves the same operator-facing safety (direct
# Episode.delete() with attached Compositions raises RestrictedError,
# and the API preflight already returns 409 before it can fire) and
# lets Workspace cascade-delete work cleanly.
#
# No data change; only the ORM's on_delete metadata + Django's
# in-memory cascade plan is affected.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compositions", "0015_composition_episode"),
        ("universe", "0003_alter_episode_universe"),
    ]

    operations = [
        migrations.AlterField(
            model_name="composition",
            name="episode",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.RESTRICT,
                related_name="compositions",
                to="universe.episode",
                help_text=(
                    "Story this render belongs to. NULL = standalone or "
                    "legacy Composition (never wrapped)."
                ),
            ),
        ),
    ]
