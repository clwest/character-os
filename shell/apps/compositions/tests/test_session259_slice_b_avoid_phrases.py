"""SESSION 259 / Slice B — ``voice_avoid_phrases`` reaches the dialogue
Character Voice block.

Closes the pre-existing bug where ``Teammate.voice_avoid_phrases`` was
authored by operators but never reached the dialogue synthesis prompt.
Prior to Slice B, ``dialogue_synthesis._build_character_voice_block``
explicitly self-labelled the omission as a bug ("that field's
LLM-injection gap remains a pre-existing bug outside AI-D2 scope").

Deterministic prompt-shape tests only. No LLM output assertions — an
acceptance test that hopes the model happens not to say a forbidden
phrase is not a contract; the contract is what enters the prompt.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os.dialogue_synthesis import (
    _build_character_voice_block,
    _build_character_voices_section,
)
from character_os.script_synthesis import _build_character_voice_section

User = get_user_model()
pytestmark = pytest.mark.django_db


def _teammate(ws, **kwargs) -> Teammate:
    defaults = {
        "name": "T",
        "business_brief": "b",
        "personality": "",
        "tone_archetype": "expert",
        "voice_energy": "medium",
        "voice_humor": "warm",
        "voice_directness": "balanced",
        "character_point_of_view": "",
        "voice_signature_phrases": "",
        "voice_avoid_phrases": "",
        "who_you_help": "",
        "what_you_sell": "",
        "always_emphasize": "",
        "never_say": "",
        "desired_feeling": "",
    }
    defaults.update(kwargs)
    return Teammate.objects.create(workspace=ws, **defaults)


@pytest.fixture
def ws() -> Workspace:
    u = User.objects.create_user(email="slice-b@example.com", password="x")
    workspace = Workspace.objects.filter(owner=u).first()
    assert workspace is not None
    return workspace


# ---- 1. avoids render in the correct character block --------------


def test_voice_avoid_phrases_renders_in_dialogue_character_block(ws):
    tm = _teammate(
        ws,
        name="Patch",
        personality="Curious tinkerer.",
        voice_avoid_phrases="revolutionary\ngroundbreaking",
    )
    out = _build_character_voice_block("patch", tm)

    # Block header appears.
    assert "AVOID PHRASES" in out
    # Each authored phrase reaches the prompt verbatim.
    assert "revolutionary" in out
    assert "groundbreaking" in out
    # Scoping language names the character explicitly.
    assert "Patch" in out
    # Scope guard: block is character-local.
    assert "lines ONLY" in out
    # Framing forbids narration (mirrors signature-phrases framing).
    assert "never narrate" in out


# ---- 2. per-character isolation (no cross-blending) ---------------


def test_avoid_phrases_do_not_leak_across_characters(ws):
    patch = _teammate(
        ws,
        name="Patch",
        voice_avoid_phrases="patch-specific-forbidden-token",
    )
    rivet = _teammate(
        ws,
        name="Rivet",
        voice_avoid_phrases="rivet-specific-forbidden-token",
    )
    section = _build_character_voices_section(
        {"patch": patch, "rivet": rivet}
    )

    # Both sub-blocks emitted.
    assert "CHARACTER PATCH" in section
    assert "CHARACTER RIVET" in section

    # Split at the second character header and inspect each half.
    idx = section.index("--- CHARACTER RIVET")
    patch_half = section[:idx]
    rivet_half = section[idx:]

    assert "patch-specific-forbidden-token" in patch_half
    assert "patch-specific-forbidden-token" not in rivet_half, (
        "Patch's avoid phrase leaked into Rivet's sub-block"
    )
    assert "rivet-specific-forbidden-token" in rivet_half
    assert "rivet-specific-forbidden-token" not in patch_half, (
        "Rivet's avoid phrase leaked into Patch's sub-block"
    )


# ---- 3. empty avoids preserve old prompt shape --------------------


def test_empty_avoid_phrases_omits_avoid_block(ws):
    tm = _teammate(
        ws,
        name="Patch",
        personality="Curious tinkerer.",
        voice_signature_phrases="Well… now I want to try it.",
        voice_avoid_phrases="",
    )
    out = _build_character_voice_block("patch", tm)

    # No AVOID PHRASES block when the field is empty (byte-stable
    # relative to pre-Slice-B behavior for that character).
    assert "AVOID PHRASES" not in out

    # All other §2 fields still emit as before.
    assert "SIGNATURE PHRASES" in out
    assert "Well… now I want to try it." in out
    assert "Curious tinkerer." in out
    assert "TONE ARCHETYPE:" in out
    assert "VOICE AXES:" in out


# ---- 4. existing Character Voice fields remain present -----------


def test_existing_character_voice_fields_still_render_with_avoids(ws):
    tm = _teammate(
        ws,
        name="Rivet",
        personality="Methodical robot.",
        character_point_of_view=(
            "Rivet distinguishes observation from explanation."
        ),
        voice_signature_phrases="Once.",
        voice_avoid_phrases="My job is simple\nAs a robot",
        tone_archetype="friend",
        voice_energy="low",
        voice_humor="dry",
        voice_directness="direct",
    )
    out = _build_character_voice_block("rivet", tm)

    # All pre-existing §2 fields still land.
    assert "TONE ARCHETYPE: friend" in out
    assert "energy=low; humor=dry; directness=direct" in out
    assert "WRITING STYLE" in out
    assert "Methodical robot." in out
    assert "POINT OF VIEW" in out
    assert "Rivet distinguishes observation from explanation." in out
    assert "SIGNATURE PHRASES" in out
    assert "Once." in out

    # New avoid-phrases block also lands, with both authored entries.
    assert "AVOID PHRASES" in out
    assert "My job is simple" in out
    assert "As a robot" in out


# ---- 5. single-character K6 behavior unchanged -------------------


def test_k6_single_character_prompt_unaffected_by_avoid_phrases(ws):
    """SESSION 259 / Slice B scope guard.

    Requirement 7 forbids changing single-character K6 behavior. This
    test proves the Slice B change did not accidentally activate a
    dormant K6 code path: script_synthesis._build_character_voice_section
    must produce identical output whether or not voice_avoid_phrases
    is populated, and the phrase itself must not appear.

    (Historical note: neither K6 nor dialogue consumed
    voice_avoid_phrases prior to Slice B. Slice B wires only the
    dialogue path per operator instruction; the K6 path remains a
    documented follow-up. This test ensures Slice B does not silently
    change K6.)
    """
    empty = _teammate(
        ws, name="Solo1", personality="p", voice_avoid_phrases="",
    )
    populated = _teammate(
        ws,
        name="Solo2",
        personality="p",
        voice_avoid_phrases="revolutionary-slice-b-marker",
    )

    # Normalize the name difference so structural comparison is meaningful.
    a = _build_character_voice_section(empty).replace("Solo1", "NAME")
    b = _build_character_voice_section(populated).replace("Solo2", "NAME")

    assert a == b, (
        "K6 single-character §2 output changed when voice_avoid_phrases "
        "was set — Slice B accidentally leaked into K6"
    )

    # And explicitly: the avoid phrase must NOT appear in K6 output.
    raw_populated = _build_character_voice_section(populated)
    assert "revolutionary-slice-b-marker" not in raw_populated
    assert "AVOID PHRASES" not in raw_populated
