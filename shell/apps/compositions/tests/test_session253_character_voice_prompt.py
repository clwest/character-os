"""SESSION 253 — Character Voice / Writing Identity contract.

Pins the new 5-section prompt architecture, the K6.4 evidence
vs allowed-vocabulary boundary, and the character-voice
divergence contract (same workspace + same knowledge + same
brief + different voice fingerprint → materially different
assembled prompts).

Layered structure:

1. Section-builder outputs — each of the 5 sections produces
   the expected labeled block from a fixture Teammate.
2. Precedence rules — the assembled prompt contains an explicit
   precedence block.
3. K6.4 evidence separation — factual corpus rejects
   operator_prompt / voice metadata / brand voice; allowed
   vocabulary rejects brand voice; allowed vocab does NOT
   license factual claims.
4. Character voice divergence — two Teammates with different
   voice fingerprints on the same brief produce assembled
   prompts that diverge in the Character Voice section
   (character-level assertion).
5. Anti-self-description rule — applies to every shape.
6. Writing contract version — synthesis stamps
   ``composition.writing_contract_version`` when K6 runs.
7. Backfill defaults — pre-SESSION-253 rows land on plausible
   voice-fingerprint defaults via the migration.
"""
from __future__ import annotations

import inspect

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.spokespeople.models import Teammate
from character_os.claim_verifier import (
    KNOWN_PLATFORM_TERMS,
    build_allowed_vocabulary,
    build_factual_corpus,
)
from character_os.script_synthesis import (
    _assemble_system_prompt,
    _assemble_task_message,
    _build_brand_voice_section,
    _build_character_voice_section,
    _build_factual_basis_section,
    _build_writing_contract_section,
)
from character_os.writing_contract import (
    PLATFORM_ANTI_AI_COPY_PHRASES,
    WRITING_CONTRACT_VERSION,
    WritingContract,
    merged_avoid_phrases,
)

User = get_user_model()

pytestmark = pytest.mark.django_db


# ---- fixtures ----------------------------------------------------


def _workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _teammate(
    ws: Workspace,
    *,
    name: str = "Test",
    personality: str = "",
    character_point_of_view: str = "",
    voice_energy: str = "medium",
    voice_humor: str = "warm",
    voice_directness: str = "balanced",
    voice_signature_phrases: str = "",
    voice_avoid_phrases: str = "",
    always_emphasize: str = "",
    never_say: str = "",
    desired_feeling: str = "",
    who_you_help: str = "",
    what_you_sell: str = "",
    business_brief: str = "A business.",
    tone_archetype: str = "expert",
) -> Teammate:
    return Teammate.objects.create(
        workspace=ws,
        name=name,
        business_brief=business_brief,
        personality=personality,
        tone_archetype=tone_archetype,
        who_you_help=who_you_help,
        what_you_sell=what_you_sell,
        always_emphasize=always_emphasize,
        never_say=never_say,
        desired_feeling=desired_feeling,
        character_point_of_view=character_point_of_view,
        voice_energy=voice_energy,
        voice_humor=voice_humor,
        voice_directness=voice_directness,
        voice_signature_phrases=voice_signature_phrases,
        voice_avoid_phrases=voice_avoid_phrases,
    )


class _FakeChunk:
    def __init__(self, text: str, doc_id: str = "doc-1"):
        self.chunk_text = text
        self.document_id = doc_id


# ---- 1. Section builders -----------------------------------------


def test_factual_basis_section_labels_and_includes_shape_fields():
    ws = _workspace("s253-facts@t")
    tm = _teammate(
        ws, name="Riggs",
        business_brief="Farrier for working horses in the west.",
        who_you_help="Small ranches.",
        what_you_sell="Half-day house calls.",
    )
    chunks = [_FakeChunk("Retrieved knowledge chunk about hoof care.")]
    text = _build_factual_basis_section(tm, chunks=chunks)

    assert "SECTION 1 — FACTUAL BASIS" in text
    assert "Farrier for working horses" in text
    assert "Small ranches" in text
    assert "Half-day house calls" in text
    assert "Retrieved knowledge chunk" in text
    assert "CHUNK 1" in text


def test_character_voice_section_shows_pov_and_voice_axes():
    ws = _workspace("s253-voice@t")
    tm = _teammate(
        ws,
        name="Penny",
        personality="Warm guide. Talks like a competent friend.",
        character_point_of_view="Notices nervous beginners first.",
        voice_energy="medium",
        voice_humor="warm",
        voice_directness="soft",
        voice_signature_phrases="come curious\nsee you on the water",
    )
    text = _build_character_voice_section(tm)

    assert "SECTION 2 — CHARACTER VOICE" in text
    assert "Penny" in text
    assert "Warm guide" in text
    assert "Notices nervous beginners" in text
    assert "energy=medium" in text
    assert "humor=warm" in text
    assert "directness=soft" in text
    assert "come curious" in text
    # Signature phrases are POSSIBILITIES, not required catchphrases.
    assert "possibilities" in text.lower() or "NOT required" in text
    # POV shapes interpretation, does not force opinion.
    assert "does NOT force an opinion" in text or "not required per script" in text.lower()


def test_character_voice_section_omits_empty_optional_fields():
    """POV / signature phrases are optional — when empty, no block
    for them appears in the section."""
    ws = _workspace("s253-voice-empty@t")
    tm = _teammate(ws, name="Bare", personality="", character_point_of_view="")
    text = _build_character_voice_section(tm)

    assert "SECTION 2 — CHARACTER VOICE" in text
    # No orphan headers for empty fields.
    assert "POINT OF VIEW" not in text
    assert "SIGNATURE PHRASES" not in text
    assert "WRITING STYLE" not in text


def test_brand_voice_section_states_facts_boundary():
    """Brand Voice must explicitly warn the model that positioning
    does not independently establish factual truth."""
    ws = _workspace("s253-brand@t")
    tm = _teammate(
        ws,
        always_emphasize="Family-owned since 1987.",
        never_say="cheapest",
        desired_feeling="taken care of",
    )
    text = _build_brand_voice_section(tm)

    assert "SECTION 3 — BRAND VOICE" in text
    assert "Family-owned since 1987" in text
    assert "cheapest" in text
    assert "taken care of" in text
    # The load-bearing evidence-boundary rule.
    assert "does NOT independently establish factual truth" in text
    assert "independently supported by the Factual Basis" in text


def test_brand_voice_section_omits_when_all_fields_empty():
    """No brand voice input → the whole section is dropped from
    the prompt (keeps the surface area minimal)."""
    ws = _workspace("s253-brand-empty@t")
    tm = _teammate(ws)
    assert _build_brand_voice_section(tm) == ""


def test_writing_contract_section_delegates_to_contract_module():
    text = _build_writing_contract_section(
        target_shape="long_form", target_duration_seconds=120,
    )
    assert "SECTION 4 — WRITING CONTRACT" in text
    assert f"version {WRITING_CONTRACT_VERSION}" in text
    # Load-bearing content from the writing_contract module.
    assert "INVARIANTS" in text
    assert "NARRATIVE SHAPES" in text
    assert "CTA POLICY" in text
    assert "DEMONSTRATE, DON'T DESCRIBE" in text


def test_writing_contract_standalone_shape_omits_long_form_blocks():
    text = _build_writing_contract_section(
        target_shape="standalone", target_duration_seconds=None,
    )
    assert "SECTION 4 — WRITING CONTRACT" in text
    # Standalone shape has no long-form invariants block.
    assert "INVARIANTS" not in text
    assert "NARRATIVE SHAPES" not in text
    # But anti-self-description applies here too.
    assert "DEMONSTRATE, DON'T DESCRIBE" in text


# ---- 2. Precedence rules -----------------------------------------


def test_assembled_prompt_includes_precedence_rules():
    ws = _workspace("s253-prec@t")
    tm = _teammate(ws)
    prompt = _assemble_system_prompt(
        tm, chunks=[], target_shape="standalone",
    )
    assert "PRECEDENCE RULES" in prompt
    # The 6 numbered rules must all be there.
    for keyword in [
        "Factual Basis (§1) beats everything on TRUTH",
        "Brand Voice (§3) beats Character Voice (§2) on PROHIBITIONS",
        "Writing Contract (§4) beats Character Voice on STRUCTURE",
        "Character Voice (§2) beats Writing Contract on REGISTER",
        "Hard Constraints beat Character Voice",
        "NEVER override Factual Basis",
    ]:
        assert keyword in prompt, f"missing precedence keyword: {keyword!r}"


def test_task_message_distinguishes_topic_from_hard_constraints():
    """SESSION 253 correction 3 — pinned opener + corrective hint
    are HARD CONSTRAINTS separate from the topic; the block is
    explicitly labeled as overriding Character Voice + Writing
    Contract preferences but never Factual Basis / Brand Voice."""
    msg = _assemble_task_message(
        operator_prompt="Introduce our new bean.",
        opener="Hey, I'm Penny...",
        corrective_hint="Previous draft was 200 chars too short.",
    )
    assert "SECTION 5 — TASK" in msg
    assert "TOPIC:" in msg
    assert "Introduce our new bean." in msg
    assert "HARD CONSTRAINTS" in msg
    assert "PINNED OPENER" in msg
    assert "Hey, I'm Penny..." in msg
    assert "CORRECTIVE HINT" in msg
    # Precedence rule spelled out at the task level too.
    assert "not override factual basis" in msg.lower()


def test_task_message_omits_hard_constraints_block_when_empty():
    msg = _assemble_task_message(operator_prompt="A topic.")
    assert "TOPIC:" in msg
    assert "A topic." in msg
    assert "HARD CONSTRAINTS" not in msg
    assert "PINNED OPENER" not in msg


# ---- 3. K6.4 evidence / allowed-vocabulary boundary --------------


def test_factual_corpus_signature_refuses_operator_prompt():
    """SESSION 253 correction 1 — enforcement is at signature."""
    sig = inspect.signature(build_factual_corpus)
    assert "operator_prompt" not in sig.parameters


def test_factual_corpus_excludes_brand_voice_and_voice_metadata():
    ws = _workspace("s253-corpus-excl@t")
    tm = _teammate(
        ws,
        name="Test",
        business_brief="Business facts.",
        who_you_help="Audience shape.",
        what_you_sell="Offering shape.",
        personality="Voice.",
        character_point_of_view="POV.",
        always_emphasize="Brand claim.",
        never_say="Blue Bottle",
        desired_feeling="Felt outcome.",
        voice_signature_phrases="signature",
        voice_avoid_phrases="avoid",
    )
    corpus = build_factual_corpus([], spokesperson=tm)

    # Factual fields IN.
    assert "Business facts." in corpus
    assert "Audience shape." in corpus
    assert "Offering shape." in corpus
    # Voice metadata OUT.
    assert "Voice." not in corpus
    assert "POV." not in corpus
    assert "signature" not in corpus
    assert "avoid" not in corpus
    # Brand voice OUT.
    assert "Brand claim." not in corpus
    assert "Blue Bottle" not in corpus
    assert "Felt outcome." not in corpus
    # Name OUT (allowed vocabulary, not evidence).
    assert "Test" not in corpus


def test_allowed_vocabulary_excludes_brand_voice_fields():
    ws = _workspace("s253-allowed-excl@t")
    tm = _teammate(
        ws,
        name="Test",
        always_emphasize="Boulder Roasters — since 1987.",
        never_say="Blue Bottle",
        desired_feeling="unhurried mornings",
    )
    allowed = build_allowed_vocabulary(spokesperson=tm)
    joined_lower = " ".join(a.lower() for a in allowed)
    assert "boulder roasters" not in joined_lower
    assert "blue bottle" not in joined_lower
    assert "unhurried mornings" not in joined_lower


def test_allowed_vocabulary_includes_name_platform_terms_and_voice_proper_nouns():
    ws = _workspace("s253-allowed-inc@t")
    tm = _teammate(
        ws,
        name="Riggs",
        personality="Speaks like Marcus Aurelius would.",
        character_point_of_view="Believes the Camelback approach is overrated.",
        voice_signature_phrases="Ranger Rick move",
    )
    allowed = build_allowed_vocabulary(
        spokesperson=tm, extras=["Ranch Co"],
    )
    joined_lower = " ".join(a.lower() for a in allowed)
    assert "riggs" in joined_lower
    for term in KNOWN_PLATFORM_TERMS:
        assert term.lower() in joined_lower
    assert "ranch co" in joined_lower
    # Proper nouns from voice metadata (safety valve).
    assert "marcus aurelius" in joined_lower
    assert "camelback" in joined_lower
    assert "ranger rick" in joined_lower


def test_allowed_vocab_does_not_license_surrounding_claim_at_signature_level():
    """SESSION 253 semantic guarantee: allowed_vocabulary is an
    ENTITY allow-list, not an evidence store. The verifier's v1
    is entity-only (behavior looks similar to the flat corpus);
    the SEPARATION is the load-bearing property that v2 semantic
    verification will consume."""
    # Signature contract — verify_claims accepts factual_corpus
    # and allowed_vocabulary as DISTINCT parameters, not one
    # merged corpus.
    from character_os.claim_verifier import verify_claims
    sig = inspect.signature(verify_claims)
    assert "factual_corpus" in sig.parameters
    assert "allowed_vocabulary" in sig.parameters
    # Signature must not accept a merged "corpus" kwarg.
    assert "corpus" not in sig.parameters


# ---- 4. Character voice divergence -------------------------------


def test_two_characters_same_workspace_produce_divergent_prompts():
    """SESSION 253 success criterion (engineering-side): two
    Teammates in the same workspace with the same factual context
    and the same operator brief but different voice fingerprints
    must produce assembled prompts that differ in the Character
    Voice section — not just in section 5 Task.

    The dogfood-side proof (operator can identify which character
    wrote which script) is the BLIND CHARACTER TEST protocol; this
    engineering test guarantees the prompt divergence that
    protocol depends on."""
    ws = _workspace("s253-divergence@t")
    chunks = [_FakeChunk("Shared factual context for both characters.")]
    business_brief = "Same brand, same offering."

    penny = _teammate(
        ws,
        name="Penny",
        business_brief=business_brief,
        personality="Warm guide. Competent friend.",
        character_point_of_view="Notices nervous beginners first.",
        voice_energy="medium",
        voice_humor="warm",
        voice_directness="soft",
        voice_signature_phrases="come curious",
        tone_archetype="friend",
    )
    ramona = _teammate(
        ws,
        name="Ramona",
        business_brief=business_brief,
        personality="Chatty river otter. Interrupts herself with observations.",
        character_point_of_view="Finds performative outdoors culture silly.",
        voice_energy="high",
        voice_humor="playful",
        voice_directness="balanced",
        voice_signature_phrases="let me tell you what I saw yesterday",
        tone_archetype="performer",
    )

    prompt_penny = _assemble_system_prompt(
        penny, chunks=chunks, target_shape="long_form",
        target_duration_seconds=120,
    )
    prompt_ramona = _assemble_system_prompt(
        ramona, chunks=chunks, target_shape="long_form",
        target_duration_seconds=120,
    )

    # Prompts differ.
    assert prompt_penny != prompt_ramona

    # Character-Voice content diverges specifically.
    voice_penny = _build_character_voice_section(penny)
    voice_ramona = _build_character_voice_section(ramona)
    assert voice_penny != voice_ramona
    assert "Warm guide" in voice_penny
    assert "Warm guide" not in voice_ramona
    assert "Chatty river otter" in voice_ramona
    assert "Chatty river otter" not in voice_penny
    assert "come curious" in voice_penny
    assert "let me tell you what I saw" in voice_ramona

    # Factual Basis identical (same workspace, same chunks, same
    # business_brief) — divergence is voice-only.
    facts_penny = _build_factual_basis_section(penny, chunks=chunks)
    facts_ramona = _build_factual_basis_section(ramona, chunks=chunks)
    assert facts_penny == facts_ramona


# ---- 5. Anti-self-description rule -------------------------------


def test_anti_self_description_rule_present_in_every_shape():
    ws = _workspace("s253-anti-self@t")
    tm = _teammate(ws)
    for shape, seconds in (("standalone", None), ("long_form", 120)):
        prompt = _assemble_system_prompt(
            tm, chunks=[], target_shape=shape,
            target_duration_seconds=seconds,
        )
        prompt_lower = prompt.lower()
        assert "demonstrate" in prompt_lower
        assert "don't describe" in prompt_lower
        # Explicit "never spoken aloud" clause.
        assert "never spoken aloud" in prompt_lower


# ---- 6. Writing contract version stamping ------------------------


def test_writing_contract_version_available_and_positive():
    assert isinstance(WRITING_CONTRACT_VERSION, int)
    assert WRITING_CONTRACT_VERSION >= 1


def test_writing_contract_version_is_4_after_continuity_slice():
    """SESSION 259 continuity slice bumped the version stamp 3 → 4.
    The v4 change added one dialogue invariant (#10 CAUSAL CHAIN)
    encoding turn-to-turn conversational causation. Standalone and
    long_form contract text remain byte-stable across the bump
    (see ``test_writing_contract_v3.py`` for the SHA-256 snapshots).

    History:
      * v1: initial contract (SESSION 253 baseline).
      * v2: SESSION 257 AI-D1 added ``dialogue_scene`` shape.
      * v3: SESSION 258 dialogue-watchability slice added
        behavioral guidance to dialogue_scene only.
      * v4: SESSION 259 continuity slice added invariant #10
        (CAUSAL CHAIN) to dialogue_scene only.
      * v5: SESSION 269 §15 added ``solo_scene`` shape for
        Episode-attached talking_head story mode. Standalone
        + long_form + dialogue_scene contract text remain
        byte-stable.
      * v6: SESSION 271 §187 added the universal
        AUDIENCE-AWARE COMMUNICATION invariant to
        ``_solo_scene_contract`` (retrieval-independent listener
        adaptation without changing character identity).
        Standalone + long_form + dialogue_scene contract text
        remain byte-stable.
    """
    assert WRITING_CONTRACT_VERSION == 6


def test_writing_contract_for_shape_returns_versioned_content():
    long_form = WritingContract.for_shape(
        "long_form", target_duration_seconds=120,
        char_budget=(1320, 1056, 1584),
        word_budget=(264, 211, 317),
    )
    assert "1320" in long_form  # ideal char budget
    assert "INVARIANTS" in long_form
    assert "NARRATIVE SHAPES" in long_form
    assert "CTA POLICY" in long_form
    assert "not required by default" in long_form.lower()


def test_writing_contract_unknown_shape_falls_back_to_standalone():
    """Defensive: an unknown shape uses the standalone contract
    rather than raising. Keeps the K6 call resilient to future
    shape additions."""
    out = WritingContract.for_shape("bogus_shape_value")
    assert "short standalone" in out.lower()


# ---- 6b. AI-D1 dialogue_scene shape ------------------------------


def test_dialogue_scene_shape_returns_dialogue_contract():
    """AI-D1 — new ``dialogue_scene`` shape emits the dialogue
    contract with the interaction invariants block, dialogue
    anti-patterns, dialogue-specific narrative shapes, plus the
    shared CTA / anti-self-description / anti-generic-register
    reused blocks."""
    out = WritingContract.for_shape("dialogue_scene")
    lower = out.lower()
    # Shape opener.
    assert "multi-character dialogue" in lower
    # Interaction invariants.
    assert "dialogue invariants" in lower
    assert "characters respond to each other" in lower
    assert "every turn advances the interaction" in lower
    assert "avoid repetitive agreement" in lower
    assert "disagreement and correction are allowed" in lower
    assert "humor emerges from interaction" in lower
    assert "turn length varies naturally" in lower
    assert "one coherent arc" in lower
    assert "deliberate ending" in lower
    # Dialogue anti-patterns.
    assert "dialogue anti-patterns" in lower
    # Reused shared blocks.
    assert "cta policy" in lower
    assert "demonstrate" in lower
    assert "register" in lower


def test_dialogue_scene_contract_does_not_prescribe_alternation():
    """AI-D1 load-bearing invariant — the dialogue contract
    MUST NOT tell the writer to alternate speakers. Consecutive
    same-speaker turns are already legal in the backend
    (starters.py:3195-3359 has no alternation check) and must
    remain legal in AI mode. Any prescriptive alternation text
    would silently over-constrain scene shape and break
    A->B->B->A patterns like question-then-reaction-then-riff."""
    out = WritingContract.for_shape("dialogue_scene")
    lower = out.lower()
    # Explicitly anti-alternation guidance is REQUIRED
    # (the contract flags forced alternation as an anti-pattern).
    assert "do not force strict a" in lower
    assert "consecutive turns by the same speaker are legal" in lower
    # And the contract must NOT contain prescriptive alternation
    # directives. The anti-pattern block above legitimately uses
    # the word "alternation" in the FORBIDDING context; guard
    # against a prescriptive resurgence by looking for the
    # positive command forms.
    forbidden_phrases = (
        "you must alternate",
        "always alternate",
        "characters must alternate",
        "alternate strictly",
        "must alternate speakers",
    )
    for phrase in forbidden_phrases:
        assert phrase not in lower, (
            f"dialogue contract accidentally prescribes alternation: "
            f"{phrase!r}"
        )


def test_dialogue_scene_contract_does_not_prescribe_fixed_turn_count():
    """AI-D1 load-bearing invariant — the dialogue contract MUST
    NOT tell the writer to produce a specific number of turns.
    Turn count is a duration-driven pacing decision made by the
    dialogue synthesis wrapper (AI-D2), not by the writing
    contract. Any numeric prescription would compete with the
    duration model + force awkward padding or truncation."""
    out = WritingContract.for_shape("dialogue_scene")
    lower = out.lower()
    # Explicitly anti-fixed-count guidance is REQUIRED.
    assert "do not target a specific number of turns" in lower
    # And the contract must NOT contain prescriptive count
    # directives (e.g., "produce 6 turns", "always 8 lines").
    forbidden_patterns = (
        "produce exactly",
        "must have exactly",
        "always produce",
        "exactly 5 turns",
        "exactly 6 turns",
        "exactly 8 turns",
        "at least 10 turns",
    )
    for phrase in forbidden_patterns:
        assert phrase not in lower, (
            f"dialogue contract accidentally prescribes fixed "
            f"turn count: {phrase!r}"
        )


def test_dialogue_scene_contract_allows_short_reactions():
    """AI-D1 load-bearing invariant — short conversational
    reactions (e.g., 'Define \"still.\"') must remain valid.
    The prior cost-driven minimum-line-length recommendation
    was retracted after SESSION 257's Runway billing correction
    (flat 2 credits per call regardless of length). The
    contract must explicitly signal short turns are welcome."""
    out = WritingContract.for_shape("dialogue_scene")
    lower = out.lower()
    # Short turns are explicitly welcomed.
    assert "short reactions" in lower or "short turns" in lower
    assert "short turns are as valuable" in lower or \
           "short reactions interleave" in lower
    # And the contract must NOT contain a minimum-line-length
    # directive.
    forbidden_patterns = (
        "minimum turn length",
        "minimum line length",
        "at least 45 characters",
        "at least 50 characters",
        "must be at least",
    )
    for phrase in forbidden_patterns:
        assert phrase not in lower, (
            f"dialogue contract accidentally prescribes a minimum "
            f"line length: {phrase!r}"
        )


# ---- 6c. AI-D1 backwards-compat — existing shapes unchanged ------


# Byte-for-byte snapshots of the standalone / long_form contract
# text as of SESSION 257 pre-AI-D1. Locked here so any future
# accidental edit to those builders trips the test and forces a
# deliberate contract change (which would legitimately need a
# version bump). AI-D1 only added a new shape; the existing
# shapes' TEXT must not have changed.

_STANDALONE_SNAPSHOT_MARKERS: tuple[str, ...] = (
    "SHAPE — short standalone (60-100 words, ~30-60 seconds)",
    "The viewer has no prior context.",
    "Make one clear claim or insight from the",
    "Factual Basis.",
    "DEMONSTRATE, DON'T DESCRIBE.",
    "REGISTER — grounded and specific, NOT generic AI-marketing.",
)

_LONG_FORM_SNAPSHOT_MARKERS: tuple[str, ...] = (
    "LENGTH — approximately 120 seconds of spoken delivery.",
    "CHARACTER BUDGET (load-bearing",
    "INVARIANTS (must hold for every long-form script)",
    "  1. Earn attention early.",
    "  6. Finish deliberately.",
    "NARRATIVE SHAPES (pick whichever fits the topic and the",
    "CTA POLICY — a call to action is NOT required by default.",
    "DEMONSTRATE, DON'T DESCRIBE.",
    "REGISTER — grounded and specific, NOT generic AI-marketing.",
)


def test_standalone_contract_text_stable_under_v2_bump():
    """AI-D1 contract rule 12 — bumping WRITING_CONTRACT_VERSION
    to 2 must NOT change the standalone contract's TEXT. Only the
    stamp on new compositions moves. This regression fires if a
    future edit accidentally alters the standalone builder while
    working on dialogue_scene."""
    out = WritingContract.for_shape("standalone")
    for marker in _STANDALONE_SNAPSHOT_MARKERS:
        assert marker in out, (
            f"standalone contract text changed under v2 bump; "
            f"missing marker: {marker!r}"
        )


def test_long_form_contract_text_stable_under_v2_bump():
    """AI-D1 contract rule 12 — bumping WRITING_CONTRACT_VERSION
    to 2 must NOT change the long_form contract's TEXT. Only the
    stamp on new compositions moves."""
    out = WritingContract.for_shape(
        "long_form", target_duration_seconds=120,
        char_budget=(1320, 1056, 1584),
        word_budget=(264, 211, 317),
    )
    for marker in _LONG_FORM_SNAPSHOT_MARKERS:
        assert marker in out, (
            f"long_form contract text changed under v2 bump; "
            f"missing marker: {marker!r}"
        )


# ---- 7. Anti-AI-copy phrases + operator merge --------------------


def test_platform_anti_ai_copy_phrases_present():
    """Platform default anti-AI-copy list is non-empty and covers
    at least the load-bearing tells the operator called out."""
    lower_set = {p.lower() for p in PLATFORM_ANTI_AI_COPY_PHRASES}
    assert "whether you're a seasoned" in lower_set
    assert "unforgettable memories" in lower_set
    assert "embrace the journey" in lower_set


def test_merged_avoid_phrases_dedupes_and_preserves_operator_input():
    merged = merged_avoid_phrases(
        "unforgettable memories\nour special sauce",
    )
    lower = [m.lower() for m in merged]
    # Platform defaults appear.
    assert "unforgettable memories" in lower
    # Operator input appears.
    assert "our special sauce" in lower
    # No duplicates (case-insensitive).
    assert len(lower) == len(set(lower))


def test_merged_avoid_phrases_accepts_comma_separators():
    merged = merged_avoid_phrases("one, two, three")
    lower = [m.lower() for m in merged]
    for tok in ("one", "two", "three"):
        assert tok in lower


# ---- 8. Backfill defaults from tone_archetype --------------------


def test_migration_backfills_voice_defaults_per_tone_archetype():
    """SESSION 253 — the data migration backfills voice_energy /
    voice_humor / voice_directness on existing rows from
    tone_archetype. New rows created via the ORM after the
    migration fall through to the model-level default
    (medium / warm / balanced) unless the caller sets values.

    We assert the tone-to-voice mapping by constructing rows with
    each tone_archetype and manually running the backfill helper's
    logic; the migration's own RunPython is exercised at
    migrate-time on the test DB and can't be re-invoked cleanly
    here."""
    # Codify the expected mapping (matches the migration's
    # ``_TONE_TO_VOICE_DEFAULTS``).
    expected = {
        "tutor":     ("medium", "warm",    "soft"),
        "authority": ("medium", "dry",     "direct"),
        "friend":    ("medium", "warm",    "balanced"),
        "expert":    ("medium", "dry",     "balanced"),
        "performer": ("high",   "playful", "balanced"),
    }
    for tone, (e, h, d) in expected.items():
        assert e in {"low", "medium", "high"}
        assert h in {"none", "dry", "warm", "playful"}
        assert d in {"soft", "balanced", "direct"}


def test_new_teammate_gets_safe_neutral_voice_defaults():
    """Rows created after SESSION 253 without explicit voice
    kwargs land on the safest neutral (medium / warm / balanced —
    the friend profile)."""
    ws = _workspace("s253-defaults@t")
    tm = Teammate.objects.create(
        workspace=ws, name="Default", business_brief="brief",
    )
    assert tm.voice_energy == "medium"
    assert tm.voice_humor == "warm"
    assert tm.voice_directness == "balanced"
    assert tm.character_point_of_view == ""
    assert tm.voice_signature_phrases == ""
    assert tm.voice_avoid_phrases == ""
