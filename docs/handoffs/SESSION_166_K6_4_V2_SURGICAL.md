---
title: "Session 166 — K6.4 v2 surgical fixes (closes SESSION 158)"
date: 2026-05-15
status: complete
session: 166
previous_handoff: ./SESSION_165_STOPLIST_WATCHDOG.md
---

# Session 166 — K6.4 v2 surgical fixes

## TL;DR

K6.4 v2 closes the canonical SESSION 158 hallucination
case end-to-end. The original Donny script that motivated
this whole arc:

> "the library doing the work is called **trafilatura** —
> and **Wikipedia** is its absolute home turf"

v1 caught `Wikipedia` (mid-sentence proper noun) but
missed `trafilatura` (lowercase — outside the
capitalized-only single-cap regex). v2 catches **both**:

```
Entities extracted (3):
  - "Character OS" (multi_word)
  - "Wikipedia" (proper_noun)
  - "trafilatura" (tech_term)

Unsupported (2):
  ⚠ "Wikipedia"  (proper_noun)
  ⚠ "trafilatura"  (tech_term)
  ✓ CAUGHT: Wikipedia
  ✓ CAUGHT: trafilatura
```

Strict mode would now block Donny's SESSION 158 render
entirely, saving the $0.25 + the operator-facing
hallucination.

Tests: Django **709 → 713** (+4 v2 tests; 1 v1-limitation
test flipped to v2 expected-catch). Migrations + SPA
unchanged.

## What shipped — surgical, no new infrastructure

Three small extractor changes + a stoplist refresh.

### 1. Tighter `_MULTIWORD_CAPS_RE`

Dropped `a` and `an` from the joining-word alternatives:

```python
# Before
r"\b[A-Z][a-zA-Z]+(?:\s+(?:of|and|the|a|an|de|du|von)\s+...)+\b"
# After (v2)
r"\b[A-Z][a-zA-Z]+(?:\s+(?:of|and|the|de|du|von)\s+...)+\b"
```

The SESSION 165 watchdog flagged `"Drop a Wikipedia"`
as a sentence-initial multi-word match — caused by the
regex treating `Drop` (capitalized sentence-start) +
lowercase `a` + `Wikipedia` as one entity. After this
tightening, the same input produces two single-token
claims:

* `Drop` — caught by the stoplist; silently dropped
* `Wikipedia` — retained as the real entity

Genuine multi-word proper nouns
(`Federal Bureau of Investigation`,
`James Webb Space Telescope`) still extract because
`of` / `and` / `the` / `de` / `du` / `von` stay in
the joining set.

### 2. New `KNOWN_TECH_TERMS` extractor

Curated frozenset of ~40 lowercase technology / library
names. New pass over the script extracts them
case-insensitively as `kind="tech_term"` claims.

The v2 set:

* SESSION 158 anchor: `trafilatura`
* Storage / db: `pgvector, postgres, postgresql, sqlite, redis, memcached`
* Web: `django, fastapi, flask, express, react, vite, nextjs`
* ML / AI: `pytorch, tensorflow, huggingface, langchain, llamaindex, haystack, openai, anthropic`
* Tooling: `celery, docker, kubernetes, ffmpeg, ollama, playwright, pytest`
* Models: `gpt, claude, gemini, llama, mistral`
* Benchmarks: `beir`

The set is hand-curated. Operators can extend by editing
the constant. The watchdog will surface candidates the
verifier doesn't catch when the operator wants to roll
new entries.

**Important**: this isn't a "known good" list — it's a
"worth extracting" list. A tech term in `KNOWN_TECH_TERMS`
that appears in the chunks corpus is allowed through;
one that doesn't is flagged. trafilatura makes the list
specifically *because* we want it flagged when the chunks
don't support the claim — same as Wikipedia.

### 3. Lowercase dedupe in the single-cap pass

Single-cap was extracting `PyTorch` and `PYTORCH` as
two separate claims. Now dedupes by lowercase form, so
casing variants collapse to one claim. Matches the
tech-term pass's behavior; both passes can't double-count
the same entity.

### 4. Stoplist refresh (watchdog-surfaced)

Added from prior dogfood data:

```
alright, sure, yeah, yep, yup, nope,
agreed, totally, absolutely, definitely,
exactly, precisely, right,
indeed, certainly, wow, wait
```

`alright` was caught in SESSION 164 dogfood (flagged on
a strict-mode Donny probe); the rest are pre-emptive
adds for the same false-positive class (conversational
sentence-initial affirmations / negations).

## Live regression replay

Composition `e485d9f9-...` (the SESSION 158 Donny
render) pulled from the live DB, replayed through v2:

```
K6.4 v2 — Donny SESSION 158 regression replay
  Source: 22 chunks from "Wikipedia is trafilatura's home turf"

Entities extracted (3):
  - "Character OS" (multi_word, position=28)
  - "Wikipedia" (proper_noun, position=151)
  - "trafilatura" (tech_term, position=204)

Unsupported (2):
  ⚠ "Wikipedia"  (proper_noun)
  ⚠ "trafilatura"  (tech_term)

  ✓ CAUGHT: Wikipedia
  ✓ CAUGHT: trafilatura
```

v1 caught 1 of 2 hallucinations. v2 catches both.
`Character OS` is correctly allow-listed via
`KNOWN_PLATFORM_TERMS`. Under strict mode, this
composition would now fail before Runway is asked
to render — saving the $0.25 + the operator-facing
quality issue.

## Tests added

* `test_extract_now_catches_lowercase_trafilatura_k6_4_v2`
  — flips the v1 limitation test (formerly
  `test_extract_misses_lowercase_trafilatura_known_v1_gap`)
  into an expected-catch.
* `test_known_tech_terms_case_insensitive_k6_4_v2` —
  PyTorch / pytorch / PYTORCH dedupe to one claim.
* `test_multiword_no_longer_greedy_with_lowercase_a_k6_4_v2`
  — `"Drop a Wikipedia"` no longer extracts as one entity.
* `test_multiword_still_catches_genuine_multiword_proper_nouns_k6_4_v2`
  — `"Federal Bureau of Investigation"` still extracts
  (regression check that the tightening didn't break
  legitimate cases).
* `test_stoplist_alright_k6_4_v2` — `Alright` at
  sentence start no longer flags.

## Calibration moments worth carrying

### 1. Curated lists carry implicit semantics — naming them well matters

`KNOWN_TECH_TERMS` looks at first glance like a "known-good"
allow-list (like `KNOWN_PLATFORM_TERMS`). It isn't.
`KNOWN_PLATFORM_TERMS` allows entries through unchecked.
`KNOWN_TECH_TERMS` does the opposite — it *forces*
extraction so the regular substring check can flag them.
The two lists' semantics are nearly inverse; their names
both start with `KNOWN_*` and could mislead a future
reader into thinking they're parallel.

The fix in this commit was the docstring: explicitly
say "this isn't a known-good list — it's a 'worth
extracting' list." A reader who skims and adds
`stripe` thinking they're whitelisting Stripe would
get the opposite outcome. Worth flagging.

**Carry-forward**: when shipping curated lists with
opposite semantics, the naming + docstring carry the
load. Future v3 might rename `KNOWN_TECH_TERMS` to
something like `EXTRACT_FROM_LOWERCASE` or
`MUST_EXTRACT_TERMS` to make the intent
self-documenting. Generalisation: curated
constants in a verifier / classifier stack
accumulate semantically; each new one should
explain its relationship to the existing ones.

### 2. Tests can flip from "documents a gap" to "documents the fix" in one commit

The v1 test `test_extract_misses_lowercase_trafilatura_known_v1_gap`
explicitly asserted that `trafilatura` was NOT in
the extracted claims — locked in as documentation
of a known limitation. v2 closes the limitation;
the test gets renamed to
`test_extract_now_catches_lowercase_trafilatura_k6_4_v2`
and the assertion flips. The test count stays the
same; the test's *intent* shifted from "this is the
v1 ceiling" to "v2 broke through it."

**Carry-forward**: locked-in-limitation tests are
contracts about the current state, not permanent
prohibitions. When the limitation closes, flip the
test rather than delete it — the historical name
+ the assertion shift tells the story of how the
contract evolved. **For this operator specifically**:
this pattern lets a future reader trace
"why does this test exist?" all the way back to
the original calibration event (SESSION 158
fact-check) without consulting git log.

## Files changed in this commit

* `shell/character_os/claim_verifier.py` — three
  changes (multi-word regex, KNOWN_TECH_TERMS,
  stoplist additions) + dedupe fix.
* `shell/apps/compositions/tests/test_claim_verifier.py`
  — +4 v2 tests + 1 v1-test flipped.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — K6.4 v2 ship
  notes.
* `docs/TRUST_CALIBRATION.md` — two new entries.
* `00-START-NEXT-SESSION.md` — overwritten for
  SESSION 167.
* `docs/handoffs/SESSION_166_K6_4_V2_SURGICAL.md` —
  this file.

## What's next (SESSION 167)

The K-arc verifier work has compounded across 7
commits (K6.4 → K6.4.1 → K6.5 → K6.4 v1.1 → K6.4 v1.2
→ K6.4 watchdog → K6.4 v2). The thread is feature-
complete + tooling + audit surface. Open paths:

1. **Real-Runway exposure**. Now's the moment —
   strict mode would catch the original Donny case
   in production. Worth $0.50-$2.00 of credits to
   validate the full stack.
2. **K6.4 v3 — embedding-similarity fallback** for
   paraphrase catching (when a flagged token is
   semantically near a chunk despite missing
   substring). Holds until real-Runway data shows
   specific paraphrase misses worth fixing.
3. **Weekly watchdog runs** —
   `python manage.py stoplist_watchdog --days=14`
   to surface stoplist drift.
4. **Older backlog** — F8.1 (blocked), K7.x
   (YouTube), K6.3 (brief length cap, 15 min),
   K7.1 (cost telemetry), W11.1 (edit-spokesperson
   modal).

---

*Handoff written end-of-SESSION 166. Anchors re-stamped
via `context-kit handoff write 166`. Strict mode left
active in the running services for ongoing dogfooding —
now strict enough to catch the SESSION 158 case.*
