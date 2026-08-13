# SESSION 232 — Identity surface (contract rule 10; three-layer
# sequence body → identity → knowledge). Adds five new TextField
# columns to Spokesperson so the customer can define their
# spokesperson's operating rules on the new
# ``/spokespeople/{id}/identity`` page. All fields accept empty;
# only ``business_brief`` (slot 1, already on the model) remains
# server-required.
#
# No data backfill needed — new columns default to empty string
# and existing rows carry the current ``business_brief`` unchanged.
#
# Full design lock at ``docs/design/CUSTOMER_JOURNEY_V1.md``
# §"The spokesperson detail page — where identity gets defined".

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("spokespeople", "0006_widen_visual_subject"),
    ]

    operations = [
        migrations.AddField(
            model_name="spokesperson",
            name="who_you_help",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Identity slot 2 — WHO the spokesperson is talking "
                    "to (target customer / audience). Always-on "
                    "operating rule; shapes every video and "
                    "conversation. Not a facts field."
                ),
            ),
        ),
        migrations.AddField(
            model_name="spokesperson",
            name="what_you_sell",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Identity slot 3 — the offering (products / "
                    "services / packages), described at the shape "
                    "level. Not a catalog — deep product detail lives "
                    "on the knowledge side."
                ),
            ),
        ),
        migrations.AddField(
            model_name="spokesperson",
            name="always_emphasize",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Identity slot 4 — the things the customer wants "
                    "in every video and every conversation. Signature "
                    "messages, positioning, brand claims. Positive "
                    "direction."
                ),
            ),
        ),
        migrations.AddField(
            model_name="spokesperson",
            name="never_say",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Identity slot 5 — guardrails. Off-limits topics, "
                    "competitor names, legal claims that cannot be "
                    "made. Negative direction; complements "
                    "always_emphasize."
                ),
            ),
        ),
        migrations.AddField(
            model_name="spokesperson",
            name="desired_feeling",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "Identity slot 6 — the emotional outcome the "
                    "customer wants people to walk away with after "
                    "interacting with the spokesperson. Not "
                    "personality; not what they said — how they "
                    "*felt.*"
                ),
            ),
        ),
    ]
