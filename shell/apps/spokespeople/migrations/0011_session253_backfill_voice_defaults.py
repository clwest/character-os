# SESSION 253 — backfill the three voice axes on existing rows
# from ``tone_archetype`` so pre-SESSION-253 teammates land on
# plausible defaults without operator action. The pure-schema
# migration 0010 sets safe global defaults (medium / warm /
# balanced); this migration refines those where a tone archetype
# suggests something more specific.
#
# Mapping (tone_archetype → voice_energy / voice_humor / voice_directness):
#
#   tutor     → medium / warm    / soft
#   authority → medium / dry     / direct
#   friend    → medium / warm    / balanced
#   expert    → medium / dry     / balanced   (also the unknown fallback)
#   performer → high   / playful / balanced

from django.db import migrations


_TONE_TO_VOICE_DEFAULTS = {
    "tutor":     ("medium", "warm",    "soft"),
    "authority": ("medium", "dry",     "direct"),
    "friend":    ("medium", "warm",    "balanced"),
    "expert":    ("medium", "dry",     "balanced"),
    "performer": ("high",   "playful", "balanced"),
}


def _backfill(apps, schema_editor):
    Teammate = apps.get_model("spokespeople", "Teammate")
    for row in Teammate.objects.all().iterator():
        energy, humor, directness = _TONE_TO_VOICE_DEFAULTS.get(
            row.tone_archetype or "expert",
            ("medium", "dry", "balanced"),
        )
        row.voice_energy = energy
        row.voice_humor = humor
        row.voice_directness = directness
        row.save(update_fields=[
            "voice_energy", "voice_humor", "voice_directness",
        ])


def _noop_reverse(apps, schema_editor):
    """Reverse is a no-op — the columns are dropped by the schema
    reversal of 0010; individual row values don't matter."""


class Migration(migrations.Migration):

    dependencies = [
        ("spokespeople", "0010_session253_character_voice_fields"),
    ]

    operations = [
        migrations.RunPython(_backfill, _noop_reverse),
    ]
