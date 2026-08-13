"""Prompt sharpening — turns hedging language into decisive language.

Ported SESSION 122 from `a sibling private-project source module`.
Core sharpening logic + replacement tables + analysis/debate/synthesis
rule blocks are unchanged from the sibling project. The character-os addition is
``clean_business_brief()`` — a softer pass tuned for user-typed copy
(no ALL-CAPS replacements, preserves the operator's voice).

Two intended use sites in character-os:

  1. **Internal system prompts** (Runway / OpenAI calls) — use the
     aggressive ``sharpen_prompt()`` to strip hedges from prompts
     the model never sees. Example: a brief becomes a Runway
     script instruction.
  2. **User-facing copy normalisation** — use the gentle
     ``clean_business_brief()`` to remove obvious hedges from a
     spokesperson's ``business_brief`` before storing it. The
     operator's tone is preserved; only the most generic hedges
     get trimmed.

Both functions are pure — no Django, no I/O, no LLM calls.
"""
from __future__ import annotations

import re
from typing import Any, Dict

# === SHARPENING RULES =================================================
# These transform hedging phrases into decisive ones.

SHARPENING_REPLACEMENTS: Dict[str, str] = {
    # Validation hedges
    "we should validate": "THIS REQUIRES validation of",
    "should validate": "MUST validate",
    "needs validation": "BLOCKED until validated:",
    "consider validating": "VALIDATE",
    # Exploration hedges
    "we should explore": "CRITICAL GAP:",
    "should explore": "MUST investigate",
    "consider exploring": "MUST investigate",
    "might want to explore": "UNKNOWN BLOCKER:",
    # Analysis hedges
    "further analysis": "BLOCKED until we analyze",
    "more research needed": "MISSING DATA:",
    "needs investigation": "BLOCKER - investigate",
    "requires study": "UNKNOWN RISK - must study",
    # Suggestion hedges
    "we might want to": "WE MUST",
    "could potentially": "WILL",
    "might be worth": "IS REQUIRED:",
    "perhaps we should": "WE WILL",
    "it might be good to": "WE NEED TO",
    # Politeness hedges
    "I think we should": "WE MUST",
    "I believe": "THE DATA SHOWS",
    "in my opinion": "BASED ON EVIDENCE,",
    "I would suggest": "THE SOLUTION IS",
    # Agreement hedges
    "that's a good point": "AGREED, and",
    "interesting perspective": "YOUR DATA SHOWS",
    "I see your point": "YOUR EVIDENCE INDICATES",
    "that makes sense": "CONFIRMED:",
    # Uncertainty hedges
    "I'm not sure but": "THE UNCERTAINTY IS",
    "maybe": "LIKELY or UNLIKELY -",
    "possibly": "PROBABILITY:",
    "potentially": "RISK:",
}


# === GENTLE PASS FOR USER COPY ========================================
# Softer replacements for the spokesperson's ``business_brief`` and
# similar user-typed surfaces. The aggressive ALL-CAPS replacements
# above would mangle an operator's natural voice; this pass strips
# only the most generic hedges and preserves casing.

_GENTLE_REPLACEMENTS: Dict[str, str] = {
    "i think we": "we",
    "i think this is": "this is",
    "we kind of": "we",
    "we sort of": "we",
    "kind of a": "a",
    "sort of a": "a",
    "we're probably": "we are",
    "we are probably": "we are",
    "we should probably": "we",
    "we might want to": "we want to",
    "we kinda": "we",
    "honestly": "",
    "basically": "",
    "literally": "",
    "actually": "",
}

# Apply only when these words appear as standalone tokens, not inside
# longer ones. ``\b`` boundaries catch this.

_DOUBLE_SPACE_RE = re.compile(r"\s{2,}")
_LEADING_PUNCT_RE = re.compile(r"^[\s,]+")
# When a filler word gets deleted between two commas
# ("we, honestly, sell") the result has an orphan comma pair
# ("we, , sell"). Collapse those across whitespace.
_ORPHAN_COMMA_RE = re.compile(r",\s*,")
_ORPHAN_PERIOD_RE = re.compile(r"\.\s*\.")


# === SHARP DEBATE / SYNTHESIS / ANALYSIS RULES =======================
# Embed these in agent prompts when stronger framing is required.
# Unchanged from the sibling project.

SHARP_DEBATE_RULES = """
## SHARPNESS REQUIREMENTS

You MUST use decisive language. Soft hedging weakens analysis.

### FORBIDDEN PHRASES (never use these):
- "We should validate..."  → Instead say: "THIS REQUIRES validation"
- "Consider exploring..."  → Instead say: "CRITICAL GAP: we don't know X"
- "Further analysis..."    → Instead say: "BLOCKED until we have X"
- "Might be worth..."      → Instead say: "IS REQUIRED because..."
- "Perhaps we should..."   → Instead say: "WE MUST do X"
- "Interesting point..."   → Instead say: "YOUR DATA SHOWS..."

### REQUIRED PATTERNS:
- State findings as FACTS, not opinions
- Quantify uncertainty: "70% confident" not "maybe"
- Name blockers explicitly: "BLOCKED ON: missing sales data"
- Challenge weak points directly: "This is unusable without X"
- Assign accountability: "ResearchAgent must provide Y by Z"

### DISAGREEMENT STYLE:
WEAK: "I see your point, but we might want to consider..."
SHARP: "Your data shows X, but that's insufficient because Y. We need Z."

WEAK: "That's interesting, we should explore that."
SHARP: "That gap is a blocker. Until we have X, this analysis is incomplete."

WEAK: "Good discussion, let's validate this further."
SHARP: "Decision: Build X. Kill criteria: <10% engagement in 7 days. Owner: Agent Y."
"""

SHARP_SYNTHESIS_RULES = """
## SYNTHESIS REQUIREMENTS

Your synthesis MUST be decisive. No mush allowed.

### STRUCTURE:
1. VALIDATED: What we proved (with evidence)
2. REJECTED: What we disproved (with reasons)
3. RISKS: Acknowledged uncertainties (quantified)
4. DECISION: The chosen path (one, not multiple)
5. KILL CRITERIA: When to abandon this path
6. ASSIGNMENTS: Who does what by when

### FORBIDDEN IN SYNTHESIS:
- "Productive discussion" → meaningless
- "Good conversation" → doesn't help
- "Further analysis recommended" → non-decision
- "Various options available" → pick one
- "Needs more investigation" → then we're BLOCKED

### REQUIRED IN SYNTHESIS:
- One decisive path forward
- Named owner for next action
- Deadline (specific date)
- Success/failure criteria (measurable)
"""

SHARP_ANALYSIS_RULES = """
## ANALYSIS REQUIREMENTS

Your analysis MUST produce actionable findings.

### FINDINGS FORMAT:
Each finding must include:
1. CLAIM: What you're asserting
2. EVIDENCE: Data that supports it
3. CONFIDENCE: Percentage (not "maybe")
4. IMPLICATION: What this means for decisions
5. ACTION: What should happen as a result

### FORBIDDEN:
- Findings without evidence
- Evidence without implications
- Implications without actions
- Confidence without percentages
"""


def sharpen_prompt(prompt: str) -> str:
    """Apply aggressive sharpening rules to a prompt.

    Transforms hedging language into decisive ALL-CAPS framing. Use
    this on **internal** system prompts (model-facing, never the
    user) — the output is jarring as user-facing copy.

    Returns the sharpened prompt.
    """
    sharpened = prompt
    # Apply replacements (case-insensitive, with word boundaries).
    # Sort by length descending so longer phrases match first.
    sorted_hedges = sorted(SHARPENING_REPLACEMENTS.items(), key=lambda x: -len(x[0]))
    for hedge, sharp in sorted_hedges:
        pattern = re.compile(r"\b" + re.escape(hedge) + r"\b", re.IGNORECASE)
        sharpened = pattern.sub(sharp, sharpened)
    return sharpened


def add_sharpening_rules(prompt: str, rules_type: str = "debate") -> str:
    """Prepend a SHARP_*_RULES block to a prompt. ``rules_type`` is
    one of ``debate`` / ``synthesis`` / ``analysis`` — defaults to
    ``debate``."""
    rules_map = {
        "debate": SHARP_DEBATE_RULES,
        "synthesis": SHARP_SYNTHESIS_RULES,
        "analysis": SHARP_ANALYSIS_RULES,
    }
    rules = rules_map.get(rules_type, SHARP_DEBATE_RULES)
    return f"{rules}\n\n{prompt}"


def check_prompt_sharpness(text: str) -> Dict[str, Any]:
    """Score a piece of text for hedging.

    Returns ``{hedge_count, hedges_found, sharpness_score (0-100),
    is_sharp: bool}``. Useful for post-generation validation.
    """
    text_lower = text.lower()
    hedges_found = []

    for hedge in SHARPENING_REPLACEMENTS.keys():
        if hedge.lower() in text_lower:
            hedges_found.append(hedge)

    hedge_words = [
        "maybe",
        "perhaps",
        "possibly",
        "potentially",
        "might",
        "could",
        "would suggest",
        "consider",
        "interesting",
        "good point",
        "makes sense",
    ]
    for word in hedge_words:
        if word in text_lower and word not in [h.lower() for h in hedges_found]:
            hedges_found.append(word)

    word_count = len(text.split())
    hedge_density = len(hedges_found) / max(word_count / 100, 1)
    sharpness_score = max(0, 100 - (hedge_density * 20))
    return {
        "hedge_count": len(hedges_found),
        "hedges_found": hedges_found,
        "sharpness_score": round(sharpness_score),
        "is_sharp": len(hedges_found) <= 2,
    }


def clean_business_brief(text: str) -> str:
    """Gentle hedge removal for user-typed copy.

    Designed for the spokesperson's ``business_brief`` field. Strips
    generic filler ("honestly", "basically") and softens
    "I think we should probably" → "we" — but preserves the
    operator's voice + casing. Multi-pass: replacement then
    whitespace cleanup.

    Returns the cleaned text. Never adds new content; only removes
    or shortens.
    """
    cleaned = text
    sorted_pairs = sorted(_GENTLE_REPLACEMENTS.items(), key=lambda x: -len(x[0]))
    for hedge, replacement in sorted_pairs:
        pattern = re.compile(r"\b" + re.escape(hedge) + r"\b", re.IGNORECASE)
        cleaned = pattern.sub(replacement, cleaned)

    # Cleanup pass: orphan punctuation first (so the whitespace
    # collapse below doesn't leave "we ," fragments), then runs of
    # spaces, then per-line leading-punctuation orphans.
    cleaned = _ORPHAN_COMMA_RE.sub(",", cleaned)
    cleaned = _ORPHAN_PERIOD_RE.sub(".", cleaned)
    cleaned = _DOUBLE_SPACE_RE.sub(" ", cleaned)
    cleaned = "\n".join(_LEADING_PUNCT_RE.sub("", line).rstrip() for line in cleaned.splitlines())
    return cleaned.strip()
