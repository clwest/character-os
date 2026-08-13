# §17.10.a Amendment 3 (post-SESSION 242 correction) — remove the
# unratified ``LEGACY_HISTORICAL`` enum values that SESSION 242
# introduced on ``ExecutionMode`` / ``ExecutionModeActual``. Origin
# for legacy imports is carried by ``GenerationProvider.LEGACY_IMPORTED``
# + ``ImportProvenance`` + ``spec_schema_version=0``; the execution
# fields are now nullable and NULL is the honest label for "no
# provider execution ever ran through the framework for this row"
# (§9.4). The pairing invariant on ``GenerationRecord.clean()``
# enforces that ``provider = LEGACY_IMPORTED`` iff both execution
# fields are NULL.
#
# Data migration:
#   - Forward: any row with ``execution_mode = 'legacy_historical'``
#     (and its actual counterpart) → NULL / NULL. Filter matches on
#     the persisted string literal, not the removed enum members.
#   - Reverse: any ``provider = 'legacy_imported'`` row with NULL
#     execution fields → restore literal 'legacy_historical' /
#     'legacy_historical'. String literals, not enum members —
#     the enum values no longer exist in the current source.

from django.db import migrations, models


def _drop_legacy_historical_execution_values(apps, schema_editor):
    GenerationRecord = apps.get_model("identity", "GenerationRecord")
    GenerationRecord.objects.filter(execution_mode="legacy_historical").update(
        execution_mode=None,
    )
    GenerationRecord.objects.filter(
        execution_mode_actual="legacy_historical",
    ).update(execution_mode_actual=None)


def _restore_legacy_historical_execution_values(apps, schema_editor):
    GenerationRecord = apps.get_model("identity", "GenerationRecord")
    GenerationRecord.objects.filter(
        provider="legacy_imported",
        execution_mode__isnull=True,
    ).update(execution_mode="legacy_historical")
    GenerationRecord.objects.filter(
        provider="legacy_imported",
        execution_mode_actual__isnull=True,
    ).update(execution_mode_actual="legacy_historical")


class Migration(migrations.Migration):

    dependencies = [
        ("identity", "0002_step3_legacy_provenance"),
    ]

    operations = [
        migrations.AlterField(
            model_name="generationrecord",
            name="execution_mode",
            field=models.CharField(
                blank=True,
                choices=[
                    ("forced_mock", "Forced mock"),
                    ("auto", "Auto"),
                    ("real_required", "Real required"),
                    ("unavailable", "Unavailable"),
                ],
                help_text=(
                    "NULL iff no provider execution occurred through the "
                    "execution framework for this row (currently: Step 3 "
                    "legacy imports). Non-NULL for every executable "
                    "provider record. See ``ExecutionMode`` docstring and "
                    "§17.10.a Amendment 3 (post-SESSION 242 correction)."
                ),
                max_length=24,
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="generationrecord",
            name="execution_mode_actual",
            field=models.CharField(
                blank=True,
                choices=[
                    ("real", "Real"),
                    ("mock", "Mock"),
                    ("mock_fallback", "Mock fallback"),
                ],
                help_text=(
                    "Companion to ``execution_mode``. NULL iff no adapter "
                    "actually ran through the framework for this row. "
                    "``execution_mode`` and ``execution_mode_actual`` are "
                    "always both NULL or both non-NULL (invariant enforced "
                    "at ``clean()``)."
                ),
                max_length=24,
                null=True,
            ),
        ),
        migrations.RunPython(
            _drop_legacy_historical_execution_values,
            reverse_code=_restore_legacy_historical_execution_values,
        ),
    ]
