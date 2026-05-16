---
title: "Session 160 — K6.4 post-synthesis claim verifier shipped"
date: 2026-05-15
status: complete
session: 160
previous_handoff: ./SESSION_159_DRIFT_PREVENTION_CLOSE.md
---

# Session 160 — K6.4 claim verifier

## TL;DR

**K6.4 shipped.** The post-synthesis claim verifier scope-
locked SESSION 159 ships in this commit with substring-v1
extraction + Warn default. The Donny SESSION 158 hallucination
that motivated the slice (script claimed `trafilatura` and
"Wikipedia is its absolute home turf" from a doc with zero
occurrences of either word) is now caught: replaying Donny's
exact script + chunks through the verifier flags `Wikipedia`.

Test totals: Django **659 → 681 (+22)**. Migration count:
51 → 52. No SPA changes (v1 backend-only; SPA surface is
v1.1 queued for next session).

## What shipped

### `shell/character_os/claim_verifier.py` — new module

The forensics-driven design from SESSION 159's scope-lock:

* **`extract_named_entities(text)`** — pure-regex pass.
  Three extractors:
  - `_MULTIWORD_CAPS_RE` — multi-word capitalized phrases
    (catches `Character OS`, `James Webb Space Telescope`).
  - `_SINGLE_CAP_RE` — single capitalized words 4+ chars
    (catches `Wikipedia`), filtered by
    `_COMMON_PROPER_NOUN_FALSE_POSITIVES` (catches and
    drops `Turns`, `Cleanest`, `Welcome`, etc).
  - `_NUMERIC_RE` — `$X`, `X%`, four-digit years.

  Documented v1 false-negative: lowercase technology names
  (`trafilatura`, `pgvector`). Anchored as a test so the
  upgrade is visible.

* **`build_corpus(chunks, *, spokesperson, operator_prompt,
  extras)`** — concatenates the allow-list sources into one
  big haystack. Sources: chunk_text, spokesperson name +
  business_brief, operator prompt, `KNOWN_PLATFORM_TERMS`
  (currently `("Character OS",)`).

* **`verify_claims(text, *, corpus)`** — pure function.
  Returns `UnsupportedClaim`s for entities in `text` whose
  lowercased form has no substring match in lowercased
  `corpus`.

* **`run_verifier(text, *, corpus, mode=None)`** — adds
  policy. Three modes:
  - `"strict"` — raises `ClaimVerifierError` on any
    unsupported claim. Composition fails before Runway
    fires.
  - `"warn"` (default) — returns the list; caller
    persists.
  - `"off"` — returns empty.

  Mode resolves from explicit arg → `settings.K6_CLAIM_VERIFIER_MODE`
  → `K6_CLAIM_VERIFIER_MODE` env → `"warn"`. Unknown
  mode strings fall back to `"warn"` (defensive — typos
  don't silently disable the verifier).

### `shell/apps/compositions/models.py` — new field

`Composition.verification_warnings: JSONField(default=list,
blank=True)`. Each entry is a dict
`{"claim": str, "kind": str, "position": int}`. Persisted
by the avatar_speech primitive after a knowledge-informed
synthesis. Migration:
`apps/compositions/migrations/0002_k6_4_verification_warnings.py`.

### `shell/character_os/script_synthesis.py` — verifier hook

After `_call_responses_api` returns the synthesized text,
`build_render_brief` runs the verifier via
`run_verifier(final_brief, corpus=build_corpus(...))`. Adds
`ScriptResult.verification_warnings: list[dict]`. The
verifier runs only on the real-synthesis path — degraded /
fallback briefs are operator-typed and trusted by
definition.

### `shell/apps/compositions/primitives/avatar_speech.py` — persistence

`_maybe_synthesize_script` returns 3-tuple instead of 2-tuple
(`brief, chunk_ids, verification_warnings`). The primitive's
`execute()` appends new warnings to
`composition.verification_warnings` and saves. In Strict
mode, the verifier raises in `build_render_brief`; the
primitive catches `ClaimVerifierError` and re-raises as
`PrimitiveError`, which fails the composition cleanly.

### `shell/apps/compositions/tests/test_claim_verifier.py` — new tests

22 tests covering:

* Named-entity extraction on Donny's actual script catches
  Wikipedia + Character OS.
* Common-word stoplist prevents false positives on sentence
  starters (`Turns`, `Cleanest`, `Welcome`, `When`, `Drop`, ...).
* Lowercase trafilatura is *intentionally* missed (locked as
  the v1 limitation test).
* Numeric extraction catches `30%`, `$100 billion`, `2020`.
* `Character OS` allow-listed via `KNOWN_PLATFORM_TERMS`.
* Operator prompt allows terms not in chunks.
* Three mode handling (strict raises, warn returns, off
  empty) + unknown mode falls back to warn.
* End-to-end through `build_render_brief` populating
  `verification_warnings` on the `ScriptResult`.

## Donny regression smoke (live replay against the DB)

Pulled Composition `e485d9f9-e711-4402-8bc5-a543c0315847`'s
step params + Spokesperson `f30b2980-...`'s attached doc
+ all 22 chunks. Ran `run_verifier(script, corpus=...)`
against the actual data:

```
Corpus: 22 chunks from doc "Wikipedia is trafilatura's home turf"
        (https://en.wikipedia.org/wiki/Retrieval-augmented_generation)

K6.4 verifier output: 1 unsupported claim(s)
  ⚠ 'Wikipedia'  (proper_noun, position=151)

✓ REGRESSION CHECK PASSED: Wikipedia flagged (the headline hallucination)
```

The slice catches what motivated it. `Character OS` is
correctly allow-listed via `KNOWN_PLATFORM_TERMS`.
`trafilatura` (lowercase) slips through — documented v1
limitation, queued for v2 with semantic similarity or a
small-model NER pass.

## Mode-default rationale

Shipped Warn-default rather than Strict because:

* **No render regression.** Existing compositions that
  previously rendered cleanly continue to render — warnings
  just accumulate on the row. The operator decides whether
  to escalate.
* **Honest failure mode is asymmetric.** False negatives
  (hallucinations slip through) are familiar from the
  pre-K6.4 status quo. False positives (legitimate renders
  blocked) would be a *new* failure mode. Warn keeps the
  v1 risk surface narrow.
* **Strict is one settings flip away.** Operators who want
  hard enforcement can set
  `K6_CLAIM_VERIFIER_MODE="strict"` per-process or in
  `.env`. Future v1.1: per-recipe defaults so
  `long_form_ad` can opt into Strict while quick
  `talking_head` stays Warn.

## Calibration moments worth carrying

### 1. The substring extractor caught the load-bearing case despite the v1 limitation

The scope-lock acknowledged that lowercase tech names
(`trafilatura`) would slip through v1. The implementation
caught `Wikipedia` — which was the *load-bearing* hallucination
in Donny's script. The trafilatura claim is true about the
product even if not in the doc; the Wikipedia "home turf"
claim is a pure fabrication. Catching the fabrication is the
v1 win; the trafilatura miss is acceptable cost.

**Carry-forward**: when scope-locking a verifier / detector,
identify which failure case is *load-bearing* vs *also-nice-
to-catch*, and let v1 explicitly miss the second class if
catching it would add substantial cost (LLM call,
semantic-similarity index, etc). Anchor the miss as a test
so the upgrade is visible later.

### 2. The stoplist grew during test runs

Two sentence-starter common words (`Cleanest`, `Welcome`)
were absent from the initial stoplist; the first test run
caught both as false positives. Fixing them was a one-line
edit. The test-first discipline saved a session of
operator-mediated debugging where the false positives would
have been blamed on the verifier being "wrong about Donny."

**Carry-forward**: when a detector / classifier ships with
a hand-curated stoplist, drive a few false-positive tests
*before* declaring the stoplist done. The test set is what
makes the stoplist a living list rather than a one-shot
guess. Stoplist coverage is testable; stoplist correctness
isn't until real data exposes the gap.

## Files changed in this commit

* `shell/character_os/claim_verifier.py` — new (~300 lines).
* `shell/character_os/script_synthesis.py` — `ScriptResult`
  field + verifier hook.
* `shell/apps/compositions/models.py` —
  `Composition.verification_warnings` field.
* `shell/apps/compositions/migrations/0002_k6_4_verification_warnings.py`
  — new.
* `shell/apps/compositions/primitives/avatar_speech.py` —
  3-tuple signature + persistence.
* `shell/apps/compositions/tests/test_claim_verifier.py` —
  new (22 tests).
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — K6.4 row marked
  ✓ SHIPPED + ship notes appended.
* `00-START-NEXT-SESSION.md` — overwritten for SESSION 161.
* `docs/handoffs/SESSION_160_K6_4_CLAIM_VERIFIER.md` —
  this file.

## What's next (SESSION 161)

The K6.4 v1 is the smallest shippable thing that caught the
SESSION 158 failure case. Two natural next slices:

* **K6.5 — Conversation synthesis verifier parity.**
  `conversation_synthesis.py` has the same prompt-only
  no-invention contract `script_synthesis.py` had pre-K6.4.
  The `claim_verifier` module is reusable; this is wiring
  + persistence (probably a new
  `ConversationMessage.verification_warnings` field) +
  tests. ~0.5 session.

* **K6.4 SPA toggle (v1.1).** Surface
  `Composition.verification_warnings` in the SPA composition
  detail page; expose the Strict/Warn/Off mode on the
  make-video form. ~1 session.

If neither of those appeals: more real-Runway exposure
(re-bake Donny, polished Sasha, long_form_ad), or any of
the queued backlog items in `00-START-NEXT-SESSION.md`.

---

*Handoff written end-of-SESSION 160. Anchor frontmatter
re-stamped via `context-kit handoff write 160 --project .` —
first slice-level production use of the
discipline shipped SESSION 159.*
