# Case Study 04 — K6.4 claim-verifier false-positive stoplist

**Date:** SESSION 173, refined SESSION 175.
**Systems:** `shell/character_os/claim_verifier.py`, K6 script
synthesis.

## Problem

The K6.4 claim verifier scans post-synthesis output for claims
that don't map to the retrieved knowledge chunks. Its precision
matters — false positives make operators distrust the whole
verifier, false negatives let hallucinations through.

Dogfood on Donny (a spokesperson with a technical-brand
personality) produced a flagged claim: `"Respect HTML"`.
SESSION 173 had produced a similar false positive: `"Think
Antoninus"`.

Both were CTA verbs + common action objects — imperative
sentence openers, not knowledge claims.

## Evidence

- Verifier flagged both fragments as ungrounded.
- Retrieved chunks contained neither the exact fragment nor
  the concept — because the fragment wasn't a concept.
- Operator's read of the output: the sentence was a call to
  action; there was nothing to verify.

## Root cause

The verifier's sentence-parser split on periods and treated
each sentence-opener noun phrase as a claim candidate.
Imperative openers (`Respect ...`, `Think ...`, `Consider ...`,
`Remember ...`) are not claims — they are directive verbs.

The verifier had a partial stoplist, but it was incomplete for
CTAs paired with common objects like `HTML`, `Antoninus`,
`the customer`.

## Decision

Do not lower the verifier's precision by weakening its
threshold. Extend the stoplist. Make it an append-only
calibration surface so new false-positive patterns feed in
without a re-deploy or verifier redesign.

## Implementation change

- Expanded sentence-opener stoplist in `claim_verifier.py`:
  added `respect`, `think`, `consider`, `remember`, `imagine`,
  and other imperative verbs to the stop-pattern set.
- Stoplist externalized as an append-only module-level list.
- Documented the pattern: when a new false positive shows up,
  add the opener + shape to the stoplist; don't tune the
  scoring.

## Verification

Re-ran Donny K6 dogfeed → `Respect HTML` cleared without
weakening the verifier. Same knowledge chunks, same output,
one fewer false warning.

## Lasting rule

**Calibration is code, not a threshold knob.** Every LLM
verification layer accumulates a calibration ledger — patterns
that look like the thing you're catching but aren't. Treating
the ledger as append-only, code-shaped state (not a runtime
config) means each finding is a permanent, testable delta.

TRUST_CALIBRATION.md is the operator-facing surface of this
same pattern for AI-model miscalibrations more broadly.
