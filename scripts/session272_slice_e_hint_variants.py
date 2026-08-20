"""SESSION 272 Slice E — frozen corrective-hint text variants.

Three variants under test. Frozen BEFORE trials begin; never edited
after Slice E authorization. Each is a drop-in replacement for
`character_os.duration_contract._expansion_hint` under a reversible
monkey-patch.

Variant A — BASELINE
  Production `_expansion_hint`. Not defined here; imported at runtime
  by the runner. Kept for reference only.

Variant B — NO-KNOWLEDGE-REF-HINT
  Removes ALL references to "knowledge chunks" and the misleading
  "REWRITE THE SAME NARRATIVE ABOVE" clause. Preserves character-count
  math, arc/narrator preservation, factual-grounding requirement
  (rephrased character-agnostically), no-restart, no-second-CTA, and
  the no-invent-facts prohibition. Isolates hypothesis A (hint wording
  drives lexical copying from knowledge chunks).

Variant C — CORRECT-ANCHOR-HINT
  Production hint verbatim EXCEPT the misleading "REWRITE THE SAME
  NARRATIVE ABOVE" clause is replaced with "EXPAND YOUR SCRIPT". All
  four references to "knowledge chunks" are retained. Isolates
  hypothesis E1 (false-anchor mis-directs to §1 Factual Basis).

Both variants have the identical positional/keyword-argument signature
as production `_expansion_hint` so they can be dropped in place.
"""
from __future__ import annotations


def _no_knowledge_ref_hint(
    *,
    actual_chars: int,
    actual_words: int,
    actual_seconds: int,
    target_duration_seconds: int,
    effective_ideal: int,
    effective_min: int,
    effective_max: int,
) -> str:
    shortfall_chars = effective_min - actual_chars
    return (
        f"Your previous draft was {actual_chars} characters "
        f"({actual_words} words, estimated ~{actual_seconds}s of "
        f"speech). Target is {target_duration_seconds}s.\n"
        f"EXPAND THE SCRIPT TO AT LEAST {effective_min} CHARACTERS "
        f"(aim for ~{effective_ideal}, do not exceed {effective_max}). "
        f"You currently need at least {shortfall_chars} more characters "
        f"to meet the minimum.\n"
        f"Preserve the central arc (opening → development → payoff → "
        f"single closing invitation), the narrator perspective, and "
        f"the factual grounding already established. Do NOT restart "
        f"with a new opening. Do NOT add a second call to action. Do "
        f"NOT invent facts."
    )


def _correct_anchor_hint(
    *,
    actual_chars: int,
    actual_words: int,
    actual_seconds: int,
    target_duration_seconds: int,
    effective_ideal: int,
    effective_min: int,
    effective_max: int,
) -> str:
    shortfall_chars = effective_min - actual_chars
    return (
        f"Your previous draft was {actual_chars} characters "
        f"({actual_words} words, estimated ~{actual_seconds}s of "
        f"speech). Target is {target_duration_seconds}s.\n"
        f"EXPAND YOUR SCRIPT TO AT LEAST {effective_min} CHARACTERS "
        f"(aim for ~{effective_ideal}, do not exceed {effective_max}). "
        f"You currently need at least {shortfall_chars} more characters "
        f"to meet the minimum.\n"
        f"Preserve the central arc (opening → development → payoff → "
        f"single closing invitation), the narrator perspective, and "
        f"the factual grounding from the knowledge chunks. Expand "
        f"secondary detail from the knowledge chunks — describe more "
        f"of the sensory / emotional beats already implied. Do NOT "
        f"restart with a new opening. Do NOT add a second call to "
        f"action. Do NOT invent facts not present in the knowledge "
        f"chunks."
    )


# Frozen exemplar renders — SHA-256 of the exact prose the runner emits.
# Used by the runner to prove the hint variant did not drift between
# freeze-time and execute-time.
def frozen_exemplars() -> dict:
    """Render each variant with the same illustrative argument tuple
    Slice B trial 1 saw. Returns {name: {text, sha256}}."""
    import hashlib

    args = dict(
        actual_chars=568,
        actual_words=100,
        actual_seconds=39,
        target_duration_seconds=81,
        effective_ideal=1215,
        effective_min=972,
        effective_max=1458,
    )
    variants = {
        "NO_KNOWLEDGE_REF": _no_knowledge_ref_hint(**args),
        "CORRECT_ANCHOR": _correct_anchor_hint(**args),
    }
    return {
        name: {
            "text": text,
            "sha256": hashlib.sha256(text.encode()).hexdigest(),
        }
        for name, text in variants.items()
    }


if __name__ == "__main__":
    import json

    exemplars = frozen_exemplars()
    print(json.dumps(exemplars, indent=2))
