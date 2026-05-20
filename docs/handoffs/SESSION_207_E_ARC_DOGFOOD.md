---
title: "Session 207 — E-arc B2.6 dogfood + arc close"
date: 2026-05-20
status: complete
session: 207
previous_handoff: ./SESSION_206_E_ARC_LANDS.md
---

# Session 207 — B-2 / E-arc B2.6: real-mode dogfood + arc close

## TL;DR

The E-arc closes. B2.6 dogfood ran end-to-end against
Marcus with the "Five Good Emperors and the Antonine
peace" topic — a knowledge-aligned happy-path test.
**Cost: $0.25 actual, exactly matching the predicted
cost.** Lineage validated end-to-end: Script.draft_text
≡ Composition.synthesized_brief byte-identical; chunk_ids
match 5/5; Composition.verification_status =
`trusted_passthrough` confirms rule 7 holds (no double
K6 synthesis).

The dogfood surfaced **seven findings in one fire**.
One operator-visible SPA bug patched in-session
(Script-detail verifier panel was hiding K6's
informational warnings on `verified` status); six v2
findings filed; one calibration entry on Marcus's rig.

**Real-mode-finds-bugs streak: 7-for-7.** Pattern is
now the design default.

## What landed

* **B2.6 dogfood** — real Runway render against Marcus.
  Topic: "explain the Five Good Emperors and why their
  reign is called the Antonine peace." 596-char script,
  54.2s mp4, 76-second wall time, $0.25 actual cost.
  Composition `fbfb8cf6-5913-4cfe-9c30-abb56a7c0044`.
  Asset `62d8397c-cfbf-4477-84bb-d03f76df7ff8`.

* **One in-session bug-fix patch** — Script-detail SPA
  verifier panel was gated on `verification_status ∈
  {warned, blocked}` and hid the 2 informational
  warnings K6 produces on `verified` status. Patch
  relaxes the gate to `warnings.length > 0` and adds a
  third neutral `info` tone alongside existing `warned`
  (amber) + `blocked` (destructive). ~15 LOC change to
  `web/src/routes/workspace/scripts.$id.tsx`.

* **Six v2 findings filed** (see AUTO_SCRIPTING_V1.md
  change log + below).

* **Two TRUST_CALIBRATION entries appended** —
  real-mode 7-for-7 streak + Marcus rig portrait
  quality.

## Lineage validation

| Layer | Value | Match |
|---|---|---|
| Script.knowledge_chunk_ids | 5 ids | ≡ Composition.knowledge_chunk_ids (set match) |
| Script.draft_text (596 chars) | "Today we're tackling…" | ≡ Composition.synthesized_brief (byte-identical) |
| Composition.verification_status | `trusted_passthrough` | rule 7 honored — K6 in-primitive skipped |
| Asset.composition (FK) | `fbfb8cf6-…` | back-link present |
| Composition.cost_actual_micros | 250000 | $0.25 actual |
| F-arc brief-mode panel | "1 doc · 5 chunks · Nerva–Antonine dynasty - Wikipedia" | renders correctly on Composition detail |

## Findings (10 total)

### Patched in-session (1)

1. **Script-detail verifier panel was gated on status,
   not warnings.** K6 produces informational warnings
   on `verified` status — below the `warned` threshold.
   The SPA hid them because the panel only rendered for
   `warned` or `blocked`. Patch: relax gate to
   `warnings.length > 0` + add neutral `info` tone for
   `verified`/`skipped`/`trusted_passthrough` with
   warnings. New heading: "Verifier noted N
   informational flag(s)" with a non-alarming sub-hint
   that the draft is approve-ready.

### v2 findings (6)

2. **Cross-surface inconsistency** — Composition
   detail page renders the same `verification_warnings`
   JSON as "Warn — 2 flags" even though
   `Composition.verification_status =
   trusted_passthrough`. Same bug class as Script-
   detail (resolved above), opposite framing direction.
   Polish slice — ~10 LOC in
   `web/src/routes/compositions/$id.tsx`.

3. **K6.4 false positive** — `Curious?` flagged as
   `proper_noun`. Rhetorical English word, not a name.
   Upstream K6 issue, not B-2 surface.

4. **`Asset.spokesperson = None`** — Marcus is not
   back-linked from the rendered Asset row. Lookups
   by spokesperson would miss this. Either
   `auto_script` starter should set it or downstream
   Asset-build path should propagate.

5. **`Asset.width / height / size_bytes = None`** —
   Runway response fields not captured. Cosmetic;
   Asset Library may show "?×?" dimensions.

6. **`Composition.cost_estimate_micros = 0`** —
   estimation didn't run for the `auto_script` starter.
   Actual was $0.25 so this didn't matter here, but
   other starters populate the estimate.

7. **`Asset.source_spec` doesn't carry
   `knowledge_chunk_ids` directly** — lineage flows
   through `Asset → composition_id →
   Composition.knowledge_chunk_ids`. B2.6 plan in
   start-here said the chunk_ids would be on
   `source_spec` directly; actual architecture is
   cleaner but doc text needs aligning.

### Calibration (2)

8. **Marcus avatar rig portrait quality.** Operator's
   playback assessment: "there's some issues with the
   mouth but I believe that we have noted it as a bad
   image, the rest seems just fine." Re-bake candidate.
   Adds a third axis to avatar rig quality variance
   alongside SESSION 158's voice × lip-sync axis: now
   also (1) source portrait quality, (2) voice × lip-
   sync compatibility, (3) script-persona fit.

9. **Real-mode-finds-bugs streak: 7-for-7.** Every
   dogfood across SESSIONS 195/197/200/202/203/205/
   **207** has surfaced at least one finding. Pattern
   is now the design default — schedule a real-mode
   dogfood at the close of every arc, no exceptions.
   If the dogfood finishes "clean," the calibration
   prior is now *something was missed*, not *nothing
   was wrong*.

### Win (1)

10. **K6.4 strict-mode value confirmed.** Verifier
    correctly flagged `Machiavelli and Gibbon` as
    `multi_word`. Gibbon IS in chunk [7] (substantive
    claim), but "Machiavelli" only appears in the
    Wikipedia source's bibliography (Strauss's
    *Thoughts on Machiavelli* — citation metadata,
    not substantive claim). The draft asserting
    Machiavelli "praised" the era is weakly grounded.
    Strict-mode would have blocked at $0.001 cost;
    warn-mode let it ride and surfaced the flag for
    operator review. Rule 4 working as designed.

## Tests at close

| Suite | Count | Delta |
|---|---|---|
| Django | 1320 | unchanged (no backend changes) |
| Media-engine | 214 | unchanged |
| SPA vitest | 405 | unchanged (vitest for the patch deferred to a v2 polish slice) |

## Commits

* `<TBD>` — `fix(B2.6): script detail verifier panel surfaces informational warnings`
* `<TBD>` — `docs: SESSION 207 close — E-arc B2.6 dogfood + arc close`

## Strategic state after this session

**Five strategic-axis arcs landed in consecutive scope-
lock blocks**: A (Asset Library, SESSIONS 185-192) → B
(Transcript Miner, SESSION 202) → C (Personalized
Video, SESSION 203) → D (Publish Bundle, SESSION 205) →
**E (Auto-Scripting, SESSIONS 206-207)**. Each arc
closed with real-mode validation. Scope-lock cadence
is now 5-for-5.

The auto-scripting layer is the first surface where K6
synthesis happens *before* render commitment. Operators
can now type a topic, review the draft + citations +
verifier flags, and approve before any Runway spend.
Combined with B-3 (personalize per recipient), the
production pipeline now has a real *script-first* shape:
topic → draft → approve → personalize → render.

## SESSION 208 candidates (operator picks)

Per the start-here doc + this session's findings:

1. **B-2 v2 polish slice** (~½ session) — fix the
   Composition-detail verifier panel inconsistency
   (finding 2 above), add Script-detail vitest for
   the patched panel, write a v2 entry in
   AUTO_SCRIPTING_V1.md.

2. **B-14 v2 `offset_x` knob** (½ session) —
   SESSION 205 dogfood finding while still fresh.

3. **Asset upload UI** (1-2 sessions) — unblocks B-1
   v2 + the operator-content bottleneck.

4. **B-2 ↔ B-3 composition** (1-2 sessions) — Script
   becomes `PersonalizedCampaign.template`. Composes
   E-arc with C-arc; "composition is the moat"
   framing.

5. **B-1 v2 slices** — external transcript ingestion,
   batch mining, highlight chaining.

6. **`auto_script_polished` + `auto_script_cinematic`
   variants** — deferred from B2.4. Each ~½ session.

7. **Marcus rig re-bake** — cosmetic, but the
   "production-ready Marcus" workflow is part of
   the operator-onboarding story; could pair with
   a small Asset upload UI slice.

## Calibration moments worth carrying

* **Real-mode dogfood is not optional.** 7-for-7 says
  every arc's dogfood will find something. Treat
  "clean" runs as a calibration prior of "something
  was missed," not "nothing was wrong."

* **Mock-mode and real-mode test different things.**
  Mock-mode exercises code paths; real-mode exercises
  integration *shapes* — what the verifier emits when
  the corpus is small, what the SPA does when status
  doesn't escalate, how Asset fields get populated
  from third-party responses, what citation rendering
  looks like across surfaces.

* **Cross-surface UI consistency is a recurring gap.**
  Script-detail and Composition-detail both render the
  same `verification_warnings` JSON with different
  framings. Future work that adds a "verifier panel"
  to a new surface should template against a shared
  component, not re-implement the gating logic.

* **Avatar rig quality has at least three axes** —
  source portrait, voice × lip-sync, script-persona
  fit. Validate the portrait before locking the rig,
  not just the first render.

## What's still pending in the E-arc

Nothing in v1. B2.0-B2.6 all shipped. Two v2-track
items queued:

* `auto_script_polished` + `auto_script_cinematic`
  variants (deferred from B2.4 per scope-lock "if
  scope permits").
* Composition-detail verifier panel polish (finding 2
  this session).
