# SESSION 271 §181.2 / Slice 9 §187.3 — canonical per-render
# audience_hint promotion from SESSION 270 env-var research
# plumbing to a persisted Composition field.
#
# Additive-nullable-or-empty per SESSION 262 discipline. Zero
# backfill (all pre-v6 Compositions retain empty audience_hint —
# semantically correct: they existed before the field). No index
# required. Immutability enforced at the model layer via
# ``Composition._IMMUTABLE_OBSERVABILITY_FIELDS`` (SESSION 262
# pattern; audience_hint added in the same slice as this migration).
#
# Django's ``makemigrations`` also detected help_text / options
# drift on unrelated SESSION 262 observability fields
# (corrective_hint, corrective_pass_synthesis, first_pass_synthesis,
# operator_topic, render_dispatched_at, synthesis_attempt_count,
# synthesis_predicted_seconds, target_duration_seconds,
# validation_failure_reason, writing_contract_version). Those
# AlterField operations are cosmetic no-ops at the database layer
# (same TextField/PositiveSmallIntegerField/etc. types + defaults)
# — deliberately omitted from this migration to keep it bounded to
# the SESSION 271 Slice 9 §187 scope (audience_hint field only).
# A separate future cleanup migration may absorb the metadata sync
# if desired.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compositions", "0017_composition_memory_ids_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="composition",
            name="audience_hint",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Per-render listener descriptor for audience-aware "
                    "communication (SESSION 271 §181.2). When non-empty, "
                    "emitted as a §5 HARD CONSTRAINT AUDIENCE DIRECTIVE "
                    "block for solo_scene renders. Left empty ⇒ the "
                    "universal Writing Contract v6 invariant reads "
                    "Teammate.who_you_help from §1 AUDIENCE as the "
                    "character's baseline listener."
                ),
            ),
        ),
    ]
