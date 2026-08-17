# SESSION 262 — Composition observability v1.
#
# Scope: `docs/design/COMPOSITION_OBSERVABILITY_V1.md`. Adds nine
# additive-nullable-or-empty-default fields to `Composition` so
# future audits can reconstruct what happened to a synthesis attempt
# without reading terminal logs. Every field is Composition-local;
# no new tables, no FK changes, no index changes, no cascade changes.
# `EPISODE_SCHEMA_V1` (deferred) adds a Universe-scoped narrative
# layer that inherits `operator_topic` for the story case; the
# per-attempt copy landing here remains authoritative for the
# render attempt in every case.
#
# Immutability of these fields (once populated) is enforced in the
# model layer via a `from_db()`/`save()` snapshot-and-check pattern,
# not at the DB layer — see `apps/compositions/models.py`.
#
# Legacy rows populate to schema defaults on migration
# (`operator_topic=""`, `target_duration_seconds=None`,
# `synthesis_attempt_count=0`, etc.) and behave exactly as today.
# No bulk backfill.

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("compositions", "0013_session253_writing_contract_version"),
    ]

    operations = [
        migrations.AddField(
            model_name="composition",
            name="operator_topic",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "SESSION 262 — verbatim operator topic / brief that "
                    "drove this synthesis attempt. Populated at Composition "
                    "create for K6 / long-form / dialogue AI-Topic paths "
                    "and by the avatar_speech primitive for talking-head "
                    "duration-driven synthesis. Empty on legacy rows and "
                    "operator-typed-script paths (no topic exists to record)."
                ),
            ),
        ),
        migrations.AddField(
            model_name="composition",
            name="target_duration_seconds",
            field=models.PositiveSmallIntegerField(
                null=True,
                blank=True,
                help_text=(
                    "SESSION 262 — operator-requested spoken duration for "
                    "duration-driven recipes (long_form_ad, talking_head "
                    "AI-topic with duration, dialogue_scene ai_topic). "
                    "NULL for non-duration recipes and legacy rows."
                ),
            ),
        ),
        migrations.AddField(
            model_name="composition",
            name="synthesis_attempt_count",
            field=models.PositiveSmallIntegerField(
                default=0,
                help_text=(
                    "SESSION 262 — number of synthesis passes that ran. "
                    "0 = synthesis never fired (mock / degraded / "
                    "operator-typed script / legacy). 1 = first-pass only "
                    "(accepted or rejected). 2 = first + one bounded "
                    "corrective pass. Bounded at 2 by the one-corrective-"
                    "pass policy documented in DIALOGUE_SCENE_AI_TOPIC_V1 "
                    "Rule 6."
                ),
            ),
        ),
        migrations.AddField(
            model_name="composition",
            name="first_pass_synthesis",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "SESSION 262 — raw first-pass LLM output (dialogue: "
                    "JSON string; long-form / talking-head: script text). "
                    "Populated whenever synthesis fired at least one pass. "
                    "Persisted even on rejection paths — SESSION 259 "
                    "audit blocker #3 + #6."
                ),
            ),
        ),
        migrations.AddField(
            model_name="composition",
            name="corrective_hint",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "SESSION 262 — the exact descriptive corrective hint "
                    "fed to the LLM for the one bounded corrective pass. "
                    "Empty when no corrective pass fired. SESSION 259 "
                    "audit blocker #5."
                ),
            ),
        ),
        migrations.AddField(
            model_name="composition",
            name="corrective_pass_synthesis",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "SESSION 262 — raw LLM output of the corrective pass. "
                    "Empty when no corrective pass fired. On corrective-"
                    "accepted paths, equals synthesized_brief."
                ),
            ),
        ),
        migrations.AddField(
            model_name="composition",
            name="validation_failure_reason",
            field=models.TextField(
                blank=True,
                default="",
                help_text=(
                    "SESSION 262 — human-readable structured reason why "
                    "synthesis was rejected (parse / duration band / "
                    "verifier). Empty on accepted synthesis. Structured "
                    "counterpart to the tail-of-error_message inference "
                    "SESSION 259 auditors had to rely on."
                ),
            ),
        ),
        migrations.AddField(
            model_name="composition",
            name="synthesis_predicted_seconds",
            field=models.FloatField(
                null=True,
                blank=True,
                help_text=(
                    "SESSION 262 — synthesis-time predicted spoken "
                    "duration from the planning estimator "
                    "(dialogue: _DIALOGUE_CPS; long-form / talking-head: "
                    "_AVATAR_SPEECH_CHARS_PER_SECOND). NULL when "
                    "synthesis never fired. Needed to close the "
                    "DF-3 CPS-calibration audit."
                ),
            ),
        ),
        migrations.AddField(
            model_name="composition",
            name="render_dispatched_at",
            field=models.DateTimeField(
                null=True,
                blank=True,
                help_text=(
                    "SESSION 262 — moment the first real render primitive "
                    "dispatched to a provider (Runway / media-engine). "
                    "NULL when synthesis rejected before provider dispatch "
                    "(dialogue AI-Topic / long-form starter-time rejection; "
                    "talking-head K6-fail inside primitive before "
                    "create_avatar_speech). Populated once; immutable."
                ),
            ),
        ),
    ]
