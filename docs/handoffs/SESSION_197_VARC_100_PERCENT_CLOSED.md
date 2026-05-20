---
title: "Session 197 — V-arc 100% real-mode closure + storyboard_voiced outro feature"
date: 2026-05-19
status: complete
session: 197
previous_handoff: ./SESSION_196_BOTH_FIX_SLICES.md
arc_close: V_ARC_REAL_MODE
---

# Session 197 — V-arc 100% real-mode CLOSED

## TL;DR

**V-arc is now 18/18 recipes real-mode-validated against real
Runway + Stability.** First time the full V-arc has been fully
end-to-end-validated. Closed via real-mode `storyboard_voiced`
fire ($1.12, 245s, 11/11 steps green) — the last unvalidated
recipe.

Bundled with the closure: a new optional `outro_text` field on
`storyboard_voiced` (operator-noticed UX gap in SESSION 195
dogfood; ~15 min implementation here that rode along with the
closure fire). The branded "Dog Food Coffee House" outro card
appears at the end of the closure composition's final asset.

Backend tests **1011 → 1014 (+3)**. SPA + media-engine
unchanged. Real-mode spend SESSION 197: **$1.12**. Total V-arc
validation arc spend (SESSIONS 195→196→197): **$4.29**.

Two new TRUST_CALIBRATION entries.

## Slice — `outro_text` on `storyboard_voiced`

### Context

SESSION 195 dogfood operator noticed the storyboard ended cold
without any brand mark. SESSION 197 opened with an explicit
request to add "Dog Food Coffee House" branding for the
closure fire. Evaluated three paths:

* **A — Add `outro_text` field to `storyboard_voiced`** (½ slice,
  bundled with the closure fire). Picked.
* B — Fire storyboard_voiced first, then build a separate
  `add_outro_only` recipe later. Defers polish.
* C — New cross-recipe `add_outro_only` recipe. Portable but
  bigger scope.

Option A wins because the field shape mirrors
`talking_head_polished`'s `outro_text` exactly — 1:1 template,
~15-min implementation. Backwards-compat (optional field; blank
keeps the existing 10-step shape).

### What landed

* `apps/compositions/recipes.py::storyboard_voiced` recipe:
  added `outro_text` field (text, optional, 80 char max). Field
  metadata + help text match `talking_head_polished` exactly so
  the operator already knows the shape.
* `apps/compositions/starters.py::storyboard_voiced` starter:
  accepts `outro_text` kwarg. Conditionally appends an
  `add_intro_outro` step at position 10 (after `mix_audio`)
  when `outro_text` is non-empty. Default styling (3s, white
  text on black) matches `talking_head_polished`. Blank /
  whitespace-only = skip the step (existing 10-step shape
  preserved).
* `apps/compositions/tests/test_v15_api.py` — 3 new tests:
  * with-outro → 11 steps, add_intro_outro at position 10,
    correct params, correct from_step_position chain.
  * blank outro_text → 10 steps (backwards-compat).
  * recipe metadata exposes outro_text field with the right
    shape (type=text, required=False, max_chars=80).

### V-arc 100% real-mode closure fire

Composition `1ce4d201-6640-415e-8bba-796e117dad67`:

```
name: V-arc closure — storyboard_voiced + outro (Dog Food Coffee House)
status: completed
mock_mode: False
wall time: 245s (~4 min)
cost_actual_micros: 1_120_270 ($1.12)
produced assets: 11
final_asset: 8abd8a1f
```

Step-by-step:

| Step | Primitive | Elapsed |
|---|---|---|
| 0 | generate_image | 20.1s — Stability Hook frame |
| 1 | generate_image | 14.1s — Stability Action frame |
| 2 | generate_image | 20.3s — Stability Payoff frame |
| 3 | generate_visual_clip | 22.4s — Runway gen4_turbo image-to-video |
| 4 | generate_visual_clip | 22.5s |
| 5 | generate_visual_clip | 20.3s |
| 6 | concat_clips | 1.9s — 15s silent storyboard |
| 7 | generate_avatar_speech | 24.1s — Riggs narration |
| 8 | audio_extract | 0.9s — narration MP3 |
| 9 | **mix_audio** | **0.3s** — SESSION 196 silent-base fix validated |
| 10 | **add_intro_outro** | **0.8s** — Dog Food Coffee House outro card |

**The two critical validations both held:**

1. **Step 9 mix_audio (279ms)** — silent-base path against
   real Runway-produced silent visual concat. SESSION 196
   slice 1 fix structurally validated in real-mode against
   production-shape inputs. The SESSION 195 500 is dead.
2. **Step 10 add_intro_outro (760ms)** — first real-mode test
   of the SESSION 197 outro feature. Brand card appended
   correctly.

Cost came in under forecast ($1.12 vs $1.92 estimate) — gen4_turbo
+ Stability ran cheaper than my prior call.

## V-arc real-mode validation arc — 3-session journey

| Session | Outcome | Spend |
|---|---|---|
| 195 | Set out to close V-arc; 2 production bugs found (mix_audio silent-base + concat_clips role mismatch); 1/2 recipes completed | $3.17 |
| 196 | Both fix slices shipped (media-engine silent-base detection + concat_clips result_role override); no real-mode fires | $0 |
| 197 | V-arc 100% closed via real-mode storyboard_voiced (with bonus outro_text feature bundle) | $1.12 |
| **Total** | **V-arc 18/18 real-mode validated; +2 production bugs fixed; +1 UX feature shipped** | **$4.29** |

## Calibration moments worth carrying

Two new TRUST_CALIBRATION entries appended:

1. **V-arc 100% real-mode closure milestone.** Pattern that
   worked across 5 sessions of layered work (mock-mode tests
   never sufficient; real-mode dogfood is the load-bearing
   gate). Same shape generalizes to future arc closures —
   R-arc closed SESSION 176, A-arc SESSION 193, V-arc
   SESSION 197.

2. **Operator-noticed-during-dogfood → next-session ship +
   re-fire is a high-yield loop.** Criteria for bundling
   UX polish with arc closure fires: small implementation
   (~30 min), mirrors an existing pattern (1:1 template
   available), composition fire is already happening for a
   different reason. SESSION 197's outro_text bundle hit all
   three.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **1014** | +3 (1011 → 1014) |
| - compositions | **583** | +3 (580 → 583) |
| Media-engine | 197 | unchanged |
| SPA vitest | 134 | unchanged |

`pnpm build` clean. Real-mode spend: **$1.12**.

Workspace assets grew **153 → 164 (+11)** from the closure
composition's 11 step outputs.

## State at session close

* All services still up from prior sessions (Django, SPA,
  Celery worker, media-engine).
* V-arc: **18/18 real-mode validated.** First end-to-end
  closure of the full arc.
* Operator now has a branded V-arc deliverable (`8abd8a1f`)
  to dogfood the Asset Library v1 surfaces against.

## Operational notes for SESSION 198

**No arc in flight.** V-arc closed; A-arc closed; R-arc
closed; F-arc closed. Phase 4 + Asset Library v1 +
real-mode validation all complete.

Same backlog as SESSION 196 close minus the V-arc closure:

* **Follow-up taxonomy questions from SESSION 196**: `long_form_ad`
  + `storyboard_ad` concat_clips outputs have similar BACKDROP-vs-
  COMPOSITE_OUTPUT considerations. Each is ~1 line + a test.
* **`outro_text` parity for other V-arc recipes** — operator
  may want the same UX surface on `long_form_ad`, `storyboard_ad`,
  `dialogue_scene`, etc. Each is ~½ slice. Bundle pattern from
  SESSION 197 worked; same operator-noticed → ship + re-fire
  loop applies.
* **Asset upload UI** (1-2 sessions): unblocks the 8 legacy
  needs-review rows + operator-uploaded content.
* **W12 legacy form retirement** (1 session): tech debt cleanup.
* **K7.x v3 YouTube oEmbed** (½ session).
* **K6.4 v3 architectural fix** (1 session).
* **F8.1 K10 seed corpus** — still blocked on operator markdown.
* **B6-B10 brand arc** — deferred SESSION 178.
* **New-arc candidates** from `CONTENT_FORMAT_BACKLOG.md`:
  B-1 (transcript miner — top strategic per memory),
  B-3 (personalized video — biggest revenue unlock),
  B-14 (multi-platform variants — distribution stickiness).

The next session is genuinely greenfield — operator picks
direction with the full V-arc + A-arc + R-arc all closed
and validated.
