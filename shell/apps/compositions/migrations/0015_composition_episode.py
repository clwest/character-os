# EPISODE_SCHEMA_V1 (SESSION 262) — Composition.episode FK.
#
# Nullable FK, `on_delete=PROTECT`. Contract:
# `docs/design/EPISODE_SCHEMA_V1.md §Q7`.
#
# PROTECT (not SET_NULL, not CASCADE) is load-bearing:
#
# * SET_NULL would silently orphan Compositions from their story
#   on Episode delete — the exact hazard the Universe substrate
#   rejected in correction 75d17f5 for `KnowledgeDocument.universe`.
# * CASCADE would destroy render provenance when an operator
#   archives a story — unacceptable.
# * PROTECT surfaces `django.db.models.deletion.ProtectedError`
#   at the DB layer; the API preflights so operators see a clean
#   409 with `blocking.composition_count`.
#
# Legacy Compositions (created before Episode existed) land here
# with `episode=NULL` on migrate. No bulk backfill; no historical
# wrapping. Consistent with `UNIVERSE_BOUNDARY_V1.md §Q6` +
# `EPISODE_LIFECYCLE_V1.md §Q16 first paragraph`.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compositions", "0014_session262_composition_observability"),
        ("universe", "0002_episode_and_cast"),
    ]

    operations = [
        migrations.AddField(
            model_name="composition",
            name="episode",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="compositions",
                to="universe.episode",
                help_text=(
                    "Story this render belongs to. NULL = standalone or "
                    "legacy Composition (never wrapped)."
                ),
            ),
        ),
    ]
