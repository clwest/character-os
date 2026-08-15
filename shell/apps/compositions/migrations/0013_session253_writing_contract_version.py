# SESSION 253 — writing_contract_version stamp on Composition.
#
# Tags each composition with the version of
# ``character_os.writing_contract`` that shaped its K6 synthesis.
# 0 = pre-contract (rows from before SESSION 253 land, and any
# path that never went through K6 synthesis). Positive integers
# correspond to ``WRITING_CONTRACT_VERSION`` at the time of
# synthesis so future audits can trace which rule set produced a
# given script.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compositions", "0012_alter_composition_spokesperson"),
    ]

    operations = [
        migrations.AddField(
            model_name="composition",
            name="writing_contract_version",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text=(
                    "SESSION 253 — which version of "
                    "``character_os.writing_contract`` shaped this "
                    "composition's synthesized script. 0 = pre-contract "
                    "(never populated by K6 after this session lands). "
                    "Positive integers correspond to "
                    "``WRITING_CONTRACT_VERSION`` at time of synthesis."
                ),
            ),
        ),
    ]
