"""Writing contract — SESSION 253.

Format-specific writing rules that apply to EVERY character for
a given shape. Kept separate from character voice so:

* Two characters share the same contract for the same shape.
* The contract can evolve independently of any single character.
* Composition rows carry a ``writing_contract_version`` stamp so
  future audits can trace which rule set shaped a given script.

Consumers:

* ``character_os.script_synthesis._build_writing_contract_section``
  reads the shape and interpolates ``WritingContract.for_shape``
  into the K6 system prompt (§4).
* ``apps.compositions.models.Composition.writing_contract_version``
  is stamped with ``WRITING_CONTRACT_VERSION`` at synthesis time.

The contract text covers:

* **Invariants** (for long-form): earn attention early, forward
  motion, develop-don't-restate, at least one meaningful change,
  every section earns its runtime, finish deliberately.
* **Narrative shape menu** (any legitimate shape, not a
  mandatory skeleton): story → realization, observation →
  explanation, opinion → argument → reversal, question →
  exploration → answer, mistake → lesson, mini-rant → practical
  advice, confession → recommendation.
* **CTA policy** (not required by default).
* **Anti-self-description rule** — demonstrate the character;
  never narrate personality metadata / archetype / POV
  directions as if speaking them.
* **Anti-generic-AI-copy** — a small versioned platform default
  phrase blacklist + register examples showing the difference
  between generic AI-marketing text and specific grounded
  writing. The operator's ``voice_avoid_phrases`` is merged in
  at prompt-assembly time (see script_synthesis).

Shapes recognized:

* ``"standalone"`` — 60-100 word single-claim short-form script.
* ``"long_form"`` — 60-180 second multi-beat narrative script.

Adding a new shape means adding a branch to ``for_shape`` and
bumping ``WRITING_CONTRACT_VERSION``.
"""
from __future__ import annotations


# Version stamp. Bump when the contract text changes materially.
# Stamped onto ``Composition.writing_contract_version`` at K6
# synthesis time.
WRITING_CONTRACT_VERSION: int = 1


# ---- Anti-generic-AI-copy defaults --------------------------------
#
# Platform-level phrases the writer should not produce. Merged
# with the teammate's ``voice_avoid_phrases`` at prompt-assembly
# time. Case-insensitive substring match by the model.
#
# Small on purpose (~15-25 entries) — the anti-register examples
# below carry more weight than a long blacklist. New failure
# modes get one-line additions here as they surface in dogfood.

PLATFORM_ANTI_AI_COPY_PHRASES: tuple[str, ...] = (
    # Register tells — generic AI-marketing shape
    "whether you're a seasoned",
    "just getting started",
    "we've got you covered",
    "let me tell you a secret",
    "in today's fast-paced world",
    "at the end of the day",
    "here's the thing",
    "look no further",
    # Empty-inspirational patterns
    "unforgettable memories",
    "embrace the journey",
    "something magical about",
    "elevate your",
    "unlock your potential",
    "take your ___ to the next level",
    "on a journey",
    # Formulaic openings
    "have you ever wondered",
    "picture this",
    "imagine a world where",
    # Filler transitions
    "with that being said",
    "that being said",
    "moving forward",
)


# GOOD / BAD register example pairs. Shown to the model as a
# contrast set rather than a rule. Empirically the register
# difference is what the model learns from — not the phrase
# list. Keep to 5-8; each pair should illustrate a different
# failure mode.

_REGISTER_EXAMPLES: tuple[tuple[str, str], ...] = (
    (
        "whether you're a seasoned pro or just getting started, "
        "we've got you covered",
        "if you've paddled twice or two hundred times, the calm "
        "bend is where I'd put you",
    ),
    (
        "our team is passionate about creating unforgettable "
        "experiences",
        "we run three trips a day and remember who came back a "
        "second time",
    ),
    (
        "there's something magical about the great outdoors",
        "the water's usually glass at 6 a.m. — that's the part "
        "nobody tells you",
    ),
    (
        "unlock your potential and embrace the journey with us",
        "come once. If you like it, come back. If you don't, we "
        "still had a good morning",
    ),
    (
        "at the end of the day, we're here to help you succeed",
        "the hardest part is usually the five minutes before you "
        "actually get in the kayak",
    ),
)


# ---- Section builders --------------------------------------------


class WritingContract:
    """The writing contract API. Static class, stateless.
    Consumers call ``WritingContract.for_shape("long_form")``."""

    @staticmethod
    def for_shape(
        shape: str,
        *,
        target_duration_seconds: int | None = None,
        char_budget: tuple[int, int, int] | None = None,
        word_budget: tuple[int, int, int] | None = None,
    ) -> str:
        """Return the writing-contract text for the given shape.

        Args:
            shape: ``"standalone"`` or ``"long_form"``.
            target_duration_seconds: long-form only; interpolated
                into the length section. Ignored on standalone.
            char_budget: ``(ideal, min, max)``. Long-form only.
                Passed from the caller so the contract and the
                script_synthesis length-reminder speak identically.
            word_budget: same shape, secondary guidance.
        """
        if shape == "long_form":
            return _long_form_contract(
                target_duration_seconds=target_duration_seconds,
                char_budget=char_budget,
                word_budget=word_budget,
            )
        return _standalone_contract()


def _standalone_contract() -> str:
    return "\n".join([
        "SHAPE — short standalone (60-100 words, ~30-60 seconds)",
        "The viewer has no prior context. Open with a brief setup",
        "grounding what this video is about (one or two short",
        "sentences). Make one clear claim or insight from the",
        "Factual Basis. Close with ONE natural next step ONLY if",
        "the topic naturally warrants one; otherwise close on the",
        "point.",
        "",
        _ANTI_SELF_DESCRIPTION_BLOCK,
        "",
        _ANTI_GENERIC_REGISTER_BLOCK,
    ])


def _long_form_contract(
    *,
    target_duration_seconds: int | None,
    char_budget: tuple[int, int, int] | None,
    word_budget: tuple[int, int, int] | None,
) -> str:
    if target_duration_seconds and char_budget and word_budget:
        ideal_c, min_c, max_c = char_budget
        target_w, min_w, max_w = word_budget
        length_block = (
            f"LENGTH — approximately {target_duration_seconds} "
            f"seconds of spoken delivery.\n"
            f"CHARACTER BUDGET (load-bearing — the accept/reject "
            f"gate is character-based, not word-based): aim for "
            f"~{ideal_c} characters. Must stay between {min_c} "
            f"and {max_c}. Under {min_c} will be rejected as too "
            f"short; over {max_c} will be rejected as too long.\n"
            f"Word guidance (secondary): ~{target_w} words "
            f"(range {min_w}-{max_w}). Character count is what "
            f"actually matters."
        )
    else:
        length_block = (
            "LENGTH — long-form spoken delivery. Follow the "
            "character / word budget the caller supplies in the "
            "system prompt above."
        )

    return "\n".join([
        length_block,
        "",
        _INVARIANTS_BLOCK,
        "",
        _NARRATIVE_SHAPES_BLOCK,
        "",
        _CTA_POLICY_BLOCK,
        "",
        _ANTI_SELF_DESCRIPTION_BLOCK,
        "",
        _ANTI_GENERIC_REGISTER_BLOCK,
    ])


_INVARIANTS_BLOCK = (
    "INVARIANTS (must hold for every long-form script)\n"
    "  1. Earn attention early. The first two sentences give a "
    "specific reason to keep listening. Not a rhetorical 'have "
    "you ever…', not a brand namedrop, not a self-introduction.\n"
    "  2. Establish forward motion. By the end of the opening, "
    "the audience knows the direction being explored — not "
    "necessarily the conclusion.\n"
    "  3. Develop, don't restate. Each subsequent section adds "
    "new observation, new stakes, new information, or a new "
    "angle. Restating the same idea in different words is a "
    "failure.\n"
    "  4. At least one meaningful change. Somewhere in the "
    "middle there must be a shift — a turn in thought, a piece "
    "of tension, an unexpected detail, a reversal, a specific "
    "observation the audience wouldn't have anticipated at the "
    "top.\n"
    "  5. Every section earns its runtime. If a paragraph could "
    "be cut without loss, cut it. Character budget is not "
    "permission to pad.\n"
    "  6. Finish deliberately. The ending resolves the arc it "
    "opened — not 'one more thing' and not a fresh sales pitch. "
    "One conclusion. No reintroductions."
)


_NARRATIVE_SHAPES_BLOCK = (
    "NARRATIVE SHAPES (pick whichever fits the topic and the "
    "character; a legitimate hybrid is fine; no mandatory "
    "skeleton)\n"
    "  • story → realization  (something happened; here's what "
    "I learned)\n"
    "  • observation → explanation  (I noticed this; here's why)\n"
    "  • opinion → argument → reversal  (I thought X, then Y "
    "turned out to be true)\n"
    "  • question → exploration → answer\n"
    "  • mistake → lesson\n"
    "  • mini-rant → practical advice\n"
    "  • confession → recommendation"
)


_CTA_POLICY_BLOCK = (
    "CTA POLICY — a call to action is NOT required by default.\n"
    "Include one only when:\n"
    "  • the operator's Task explicitly asks for one, OR\n"
    "  • the topic is clearly promotional (how to work with us, "
    "book, buy), OR\n"
    "  • the ending naturally IS an invitation given the "
    "character and topic.\n"
    "When included: ONE CTA, natural, arising from the content. "
    "Never tacked on. Never repeated. Never a second CTA after "
    "the first."
)


_ANTI_SELF_DESCRIPTION_BLOCK = (
    "DEMONSTRATE, DON'T DESCRIBE.\n"
    "The audience learns who this character is from what they "
    "notice, what they say, and how they say it — not from the "
    "character saying 'as a friendly guide who loves helping "
    "beginners' or 'I'm a curious river otter who…'.\n"
    "Personality text, archetype, point-of-view directions, "
    "brand positioning, and every configuration in the sections "
    "above are notes to you the writer. NEVER spoken aloud. "
    "NEVER narrated. NEVER restated in the script.\n"
    "The single exception: when the operator's Task section "
    "EXPLICITLY asks for an introduction, profile, or "
    "'here's who I am' piece."
)


def _register_examples_block() -> str:
    lines = [
        "REGISTER — grounded and specific, NOT generic AI-marketing.",
        "Contrast set (BAD → GOOD):",
    ]
    for bad, good in _REGISTER_EXAMPLES:
        lines.append(f"  BAD:  {bad}")
        lines.append(f"  GOOD: {good}")
        lines.append("")
    return "\n".join(lines).rstrip()


_ANTI_GENERIC_REGISTER_BLOCK = _register_examples_block()


def merged_avoid_phrases(operator_avoid: str = "") -> list[str]:
    """Merge platform anti-AI-copy defaults with the operator's
    ``voice_avoid_phrases`` free-text. Returns a de-duplicated
    list preserving platform-first order (so platform defaults
    appear at the top of the prompt block).

    Operator input is split on newlines OR commas — either
    convention works; empty tokens are dropped.
    """
    tokens: list[str] = []
    seen: set[str] = set()
    for phrase in PLATFORM_ANTI_AI_COPY_PHRASES:
        key = phrase.strip().lower()
        if key and key not in seen:
            tokens.append(phrase.strip())
            seen.add(key)
    if operator_avoid:
        for raw in operator_avoid.replace(",", "\n").split("\n"):
            phrase = raw.strip()
            key = phrase.lower()
            if key and key not in seen:
                tokens.append(phrase)
                seen.add(key)
    return tokens


__all__ = [
    "WRITING_CONTRACT_VERSION",
    "WritingContract",
    "PLATFORM_ANTI_AI_COPY_PHRASES",
    "merged_avoid_phrases",
]
