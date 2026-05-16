---
title: "Session 165 — K6.4 stoplist watchdog"
date: 2026-05-15
status: complete
session: 165
previous_handoff: ./SESSION_164_K6_4_V1_2_VERIFICATION_STATUS.md
---

# Session 165 — K6.4 stoplist watchdog

## TL;DR

K6.4's `_COMMON_PROPER_NOUN_FALSE_POSITIVES` stoplist is
hand-curated. Across SESSIONS 160-164 the operator surfaced
`Cleanest`, `Welcome`, `Modern`, `Short`, `Alright` one at
a time via live dogfood. SESSION 165 closes that discovery
loop with a scripted reporter:

```bash
python manage.py stoplist_watchdog [--days=N] [--limit=N] [--workspace=<slug>]
```

Scans `Composition.verification_warnings` +
`ConversationMessage.verification_warnings` over a
configurable window, classifies each flag as sentence-
initial / mid-sentence / no-text-context, and emits a
copy-pasteable Python set literal of stoplist suggestions.

Tests: Django **697 → 709** (+12: 7 sentence-initial helper
+ 5 watchdog command tests). Migrations unchanged at 56.

## What shipped

### `character_os/claim_verifier.py` — `is_sentence_initial`

New pure helper. Returns True when a position in a string
is at the start of a new sentence:

* `position == 0`, OR
* the prior non-whitespace character is one of `.!?:`.

Reusable beyond the watchdog; future v2 (semantic-match
upgrade) can use it to score flag confidence
(sentence-initial flags are mostly false positives; mid-
sentence flags are mostly real).

### `apps/compositions/management/commands/stoplist_watchdog.py`

New management command. Reads-only over the verifier
event tables. Four output buckets:

1. **Sentence-initial candidates** — the stoplist
   suggestions. Renders a table + a copy-pasteable
   Python set literal of lowercased tokens for direct
   insertion into `_COMMON_PROPER_NOUN_FALSE_POSITIVES`.
2. **Mid-sentence flags** — the verifier doing its job;
   surfaced for awareness, not action.
3. **Warn-mode composition flags (no text context)** —
   Warn-mode renders don't persist the synthesized
   brief, so the position field is meaningless without
   the source text. We still tally the claim so it's
   visible.
4. **Regressions** — tokens already in the stoplist
   but flagging again (casing / inflection variant).

CLI flags:
* `--days=N` (default 30) — window
* `--limit=N` (default 20) — top N per bucket
* `--workspace=<slug>` — restrict to a workspace

### Tests

`apps/compositions/tests/test_claim_verifier.py` (+7):
* `is_sentence_initial` at position 0
* after period + space
* after question mark
* mid-sentence returns false
* leading-whitespace position counts as initial
* negative position safely returns false
* out-of-range position safely returns false

`apps/compositions/tests/test_stoplist_watchdog.py` (+5):
* empty DB renders healthy state
* sentence-initial flag surfaces with stoplist suggestion
* mid-sentence flag lands in "doing its job" bucket
* warn-mode composition flag (empty rejected_synthesis)
  surfaces in no-text-context bucket
* `--days` window excludes older events

Isolation allowlist (`test_only_composition_module_writes_composition_tables`)
extended to permit the new test file's seed writes.

## Live watchdog run

Scanned the current DB for the last 30 days:

```
K6.4 stoplist watchdog — scanned 2 verifier-flagged event(s)
  window:    last 30 day(s) (since 2026-04-16)
  workspace: (all)

=== SENTENCE-INITIAL CANDIDATES (stoplist suggestions) ===

  TOKEN                     COUNT  LAST SEEN
  ------------------------ ------  ---------
  Drop a Wikipedia              1  2026-05-16

=== MID-SENTENCE FLAGS (verifier doing its job) ===

  TOKEN                     COUNT  LAST SEEN
  ------------------------ ------  ---------
  Wikipedia                     1  2026-05-16

Suggested additions to _COMMON_PROPER_NOUN_FALSE_POSITIVES:
  {"drop a wikipedia"}
```

Two events surfaced from SESSION 163's HTTP API dogfood
(`ConversationMessage` flagged inside the strict-mode 422
test path):

* `Wikipedia` mid-sentence — the actual hallucination
  the verifier exists to catch. Verifier doing its job ✓.
* `Drop a Wikipedia` sentence-initial — a v2 calibration
  finding (see §"Calibration moments"). The watchdog
  surfaced it cleanly; the suggested stoplist literal
  flags it as a multi-word phrase the simple stoplist
  can't actually fix.

Low event count is expected: most prior dogfood used
`pytest.mark.django_db` rollback so the warnings never
persisted; the 2 events that survived are from the
non-rollback `python manage.py shell` probes.

## Calibration moments worth carrying

### 1. The watchdog surfaced a multi-word matcher bug, not a stoplist gap

`Drop a Wikipedia` got flagged because the multi-word
regex (`_MULTIWORD_CAPS_RE`) includes `a` as a joining
word. So `"Drop"` (capitalized sentence start) + `"a"`
(joining word) + `"Wikipedia"` (capitalized) parses as
a single multi-word entity. That entity isn't in the
corpus → flagged.

The watchdog suggested adding `"drop a wikipedia"` to the
stoplist, but `_COMMON_PROPER_NOUN_FALSE_POSITIVES` is a
single-word set — multi-word entries don't match the
extractor's per-token check. The real fix is upstream:
either (a) drop `a` from the joining words list (too
common in English), or (b) when a multi-word phrase is
extracted, ALSO extract its parts as separate claims so
the stoplist can suppress `Drop` independently.

**Carry-forward**: when a scripted reporter recommends a
fix that the receiving subsystem can't actually apply, the
report is correctly identifying a problem but in the wrong
layer. The recommendation is signal that the matcher needs
tightening, not that the stoplist needs widening.
**Generalisation**: classifier/filter pipelines have
multiple layers; an event flagged by one layer may be
fixable only at a different layer. Surface the event +
let the operator decide which layer to touch.

### 2. Test isolation has a stoplist of its own (the ALLOWED_FILES set)

The new watchdog test file seeds `Composition` rows to
exercise the warn-mode "no text context" branch. That
tripped the V1 isolation guard
(`test_only_composition_module_writes_composition_tables`)
which restricts who can call `Composition.objects.create`.
Fix was one line: add the new test file to `ALLOWED_FILES`
with a code-review note.

**Carry-forward**: V1's privacy-anchor contract has an
allowlist that mirrors the stoplist pattern — both are
hand-curated guards against accidental boundary
violations. The cost of adding to the allowlist is a
one-line code-review-style edit; the cost of forgetting
is a CI failure that explains itself. Healthy
arrangement.

## Files changed in this commit

* `shell/character_os/claim_verifier.py` —
  `is_sentence_initial` helper.
* `shell/apps/compositions/management/__init__.py` — new.
* `shell/apps/compositions/management/commands/__init__.py` — new.
* `shell/apps/compositions/management/commands/stoplist_watchdog.py` — new.
* `shell/apps/compositions/tests/test_claim_verifier.py`
  — +7 sentence-initial tests.
* `shell/apps/compositions/tests/test_stoplist_watchdog.py` — new.
* `shell/apps/compositions/tests/test_isolation.py` —
  watchdog test file added to `ALLOWED_FILES`.
* `docs/CHARACTER_OS_INVENTORY.md` — regen.
* `docs/design/KNOWLEDGE_LAYER.md` — watchdog ship notes.
* `docs/TRUST_CALIBRATION.md` — two new entries.
* `00-START-NEXT-SESSION.md` — overwritten for SESSION 166.
* `docs/handoffs/SESSION_165_STOPLIST_WATCHDOG.md` —
  this file.

## What's next (SESSION 166)

K-arc verifier thread feature-complete + tooling.
Remaining queue:

* **Real-Runway exposure** — the verifier work has been
  validated against mock LLMs + synthesizer probes but
  not against production Runway loads. Worth a
  $0.50-$2.00 spend to exercise the full v1.x stack
  under real generation conditions.
* **K6.4 v2 — semantic-match upgrade.** Documented
  limitations: lowercase tech names slip the substring
  matcher; multi-word regex over-matches via `a`; short
  common-adjective false positives still surface (the
  watchdog will help catch these). v2 candidates:
  small-model NER, embedding-similarity, joining-words
  list tightening. ~1-2 sessions.
* **Older backlog**: F8.1 (blocked on operator markdown),
  K7.x (YouTube ingest silent failure), K6.3 (brief
  length cap), K7.1 (cost telemetry surface), W11.1
  (edit-spokesperson modal).

---

*Handoff written end-of-SESSION 165. Anchors re-stamped
via `context-kit handoff write 165`. Strict mode left
active in the running services for ongoing dogfooding.*
