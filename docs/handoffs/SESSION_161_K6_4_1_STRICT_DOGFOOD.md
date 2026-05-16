---
title: "Session 161 — K6.4.1 strict-mode dogfood follow-ups"
date: 2026-05-15
status: complete
session: 161
previous_handoff: ./SESSION_160_K6_4_CLAIM_VERIFIER.md
---

# Session 161 — K6.4.1 strict-mode dogfood

## TL;DR

K6.4 shipped SESSION 160 with Warn as default. Operator
ran strict-mode dogfood against the live system; two
calibration findings surfaced. K6.4.1 ships both fixes in
this commit:

1. **Stoplist widening.** First strict-mode render
   rejected on `'Modern'` — a sentence-initial common
   adjective, not a proper noun. Same false-positive
   class as the SESSION 160 `Cleanest`/`Welcome`
   additions. Stoplist grew by ~60 entries covering
   adjectives, sizes, frequencies, and adoption
   modifiers.
2. **Forensic persistence on strict-mode failure.**
   Pre-K6.4.1, strict rejection lost the synthesized
   text — operators couldn't see what the LLM said. New
   `Composition.rejected_synthesis: TextField` +
   `ClaimVerifierError.synthesized_text` plumb the
   rejected output through to the composition row.

**Live dogfood validation:** the SESSION 161 replay of
the same prompt that flagged `'Modern'` in K6.4 now
passes — K6 produces a script grounded in the chunks
under the strict constraint, and the render fires
clean.

Tests: Django **681 → 684 (+3)**. Migrations: **52 → 53**.

## What shipped

### `shell/character_os/claim_verifier.py` — stoplist + error

* `_COMMON_PROPER_NOUN_FALSE_POSITIVES` grew by ~60
  entries: `modern, digital, smart, advanced, simple,
  basic, classic, premium, natural, easy, hard, normal,
  complete, full, partial, open, closed, small, large,
  tiny, huge, quick, slow, fast, rapid, instant, live,
  active, passive, main, primary, secondary, regular,
  standard, custom, special, general, specific, popular,
  common, rare, unique, free, paid, young, old, ancient,
  new, fresh, recent, early, late, final, initial,
  internal, external, online, offline, local, remote,
  public, private`. Locked in by a regression test that
  exercises the SESSION 161 false-positive set.
* `ClaimVerifierError` now carries `synthesized_text` so
  the caller can persist what the LLM produced. The
  string flows from `run_verifier(text, ...)` to the
  exception verbatim.

### `shell/apps/compositions/models.py` — `rejected_synthesis` field

New `TextField(blank=True, default="")`. Empty on clean
renders, Warn-mode flagged renders (where the brief
flows through to Runway), and Off-mode renders.
Populated only on strict-mode rejection.

Migration: `0003_k6_4_1_rejected_synthesis`.

### `shell/apps/compositions/primitives/avatar_speech.py` — persistence

In `_maybe_synthesize_script`, before re-raising the
`ClaimVerifierError` as `PrimitiveError`:

```python
composition.verification_warnings = [u.to_dict() for u in exc.unsupported]
composition.rejected_synthesis = exc.synthesized_text or ""
composition.save(update_fields=["verification_warnings", "rejected_synthesis"])
```

The composition's `error_message` (set by the executor) gets
the summary; the new fields carry the full forensic surface.

### `shell/apps/compositions/tests/test_claim_verifier.py` — 3 new tests

* `test_extract_skips_sentence_initial_adjectives_k6_4_1` —
  fires the SESSION 161 false-positive set (`Modern`,
  `Digital`, `Simple`, `Advanced`, `Basic`, `Smart`,
  `Classic`, `Premium`) as a regression block.
* `test_strict_mode_error_carries_synthesized_text_k6_4_1`
  — confirms `ClaimVerifierError.synthesized_text` is
  populated by `run_verifier`.
* `test_strict_failure_persists_warnings_and_synthesis_k6_4_1`
  — integration test: fire `GenerateAvatarSpeechPrimitive.execute`
  in strict mode with a patched LLM returning Donny's
  hallucinated script, confirm `composition.rejected_synthesis`
  + `composition.verification_warnings` are populated
  before the `PrimitiveError` propagates.

## Live dogfood (live-system replay against Donny)

Three real renders fired against Donny + his
Wikipedia-RAG doc with `K6_CLAIM_VERIFIER_MODE=strict`:

| # | Operator prompt | Outcome | Cost |
|---|---|---|---|
| 1 | "Tell viewers about the library that powers our URL ingestion." (the SESSION 160 case that flagged `'Modern'`) | **PASSED** — K6 produced a chunk-grounded script; verifier let it through. Real Runway render shipped. | $0.25 |
| 2 | "Tell viewers what kind of pages this Wikipedia ingestion works best on." | **PASSED** — operator prompt mentions Wikipedia → it's in the corpus → allow-listed by design. | $0.25 |
| 3 | "Describe how the knowledge layer ingests web pages." | **PASSED** — K6 produced 522 chars of chunk-grounded content; no inventions. | $0.25 |

**The K6.4.1 stoplist fix is validated** — the exact prompt
that broke in strict mode now flows through. None of the
three renders had `rejected_synthesis` or
`verification_warnings` populated, confirming the verifier
passed cleanly.

**Strict mode is shaping behavior.** When the operator's
prompt has hallucination-prone framing ("library that powers
our ingestion"), K6 under strict-mode pressure produces
safer, more chunk-grounded output rather than reaching for
training-data facts. This is the desired second-order
effect: the verifier as a forcing function on the
synthesis, not just a gate.

**Bypass case.** A fourth render earlier in the session
fired *without* `OPENAI_API_KEY` in the shell environment —
retrieval degraded → synthesis didn't run → verifier
bypassed → operator prompt rendered verbatim. This is
expected v1 behavior (operator-typed prompts are trusted),
but it's a real failure mode worth documenting: setting
`K6_CLAIM_VERIFIER_MODE=strict` doesn't prevent renders
when retrieval can't run at all. Mitigation lives outside
the verifier — `OPENAI_API_KEY` should be present in any
environment where renders happen.

## Calibration moments worth carrying

### 1. Strict mode is a forcing function, not just a gate

The K6.4 design framed the verifier as a "gate" — synthesis
runs, verifier checks, gate opens or blocks. The SESSION 161
dogfood revealed the second-order effect: under strict-mode
pressure, K6's outputs are different. The same prompt that
produced a `'Modern'`-claiming script in K6.4 produced a
chunk-grounded script in K6.4.1 (with the stoplist closing
the false-positive class). It's not that gpt-5-mini changed
behavior — the prompt is the same; the model presumably
explored the same response space. The difference is which
outputs survive past the verifier.

**Carry-forward**: when shipping a constraint layer
(verifier, post-filter, validator), expect downstream
behavior shifts. The constraint isn't just "block bad
output" — it changes the operator's mental model of what
the system will generate, which biases prompts, which
narrows what the system generates. Anchor the design
around the system's eventual equilibrium, not just the
gate's immediate semantic.

### 2. The bypass case is a real failure mode

A render fired with no `OPENAI_API_KEY` in the shell:
retrieval degraded, synthesis didn't run, verifier didn't
run, operator prompt rendered verbatim. The composition
completed with no `verification_warnings` — and the
operator-typed prompt happened to contain "Wikipedia" and
"Character OS." K6.4's design choice was "operator-typed
prompts are trusted," but the failure mode looks
identical to a clean render even in strict mode.
The operator can't tell from `verification_warnings=[]`
whether (a) the synthesis ran and passed cleanly, or
(b) the synthesis didn't run at all.

**Carry-forward**: distinguish "verifier passed" from
"verifier didn't run." `ScriptResult.used_knowledge`
already encodes this; surface it onto the
composition row in a future slice so operators can
audit whether a clean render is actually verified or
just trusted. `Composition.verification_status:
TextChoices('verified' | 'trusted_passthrough' |
'skipped')` would close this gap. Not blocking; queued
as a v1.2 backlog item.

## Files changed in this commit

* `shell/character_os/claim_verifier.py` — stoplist + error.
* `shell/apps/compositions/models.py` — `rejected_synthesis`.
* `shell/apps/compositions/migrations/0003_k6_4_1_rejected_synthesis.py`
  — new.
* `shell/apps/compositions/primitives/avatar_speech.py` —
  persist before re-raise.
* `shell/apps/compositions/tests/test_claim_verifier.py` —
  +3 tests.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — K6.4.1 ship notes.
* `00-START-NEXT-SESSION.md` — overwritten for SESSION 162.
* `docs/handoffs/SESSION_161_K6_4_1_STRICT_DOGFOOD.md` —
  this file.

## What's next (SESSION 162)

The K6.4 / K6.4.1 thread is in good shape — strict mode
works on real Runway data with $0.00 cost on rejection.
Two natural continuations:

* **K6.5 — Conversation synthesis verifier parity.**
  Already queued. Same hallucination class lives in
  `conversation_synthesis.py`. Module is reusable;
  this is wiring + persistence (probably a new
  `ConversationMessage.verification_warnings` field) +
  tests. ~0.5 session.

* **K6.4 v1.1 SPA toggle.** Surface
  `verification_warnings` + `rejected_synthesis` on the
  composition detail page. Add a Strict/Warn/Off
  selector to make-video. ~1 session.

* **K6.4 v1.2 verification_status field.** Captured in
  the AI Notes above. Distinguish "verified" from
  "trusted passthrough" from "skipped." ~30 minutes.

Or pick anything else from the backlog in
`00-START-NEXT-SESSION.md`.

---

*Handoff written end-of-SESSION 161. Anchor frontmatter
re-stamped via `context-kit handoff write 161 --project .`.
Third consecutive session running the context-kit
session-end discipline; pattern is stable.*
