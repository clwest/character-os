---
title: "Session 183 — V17.5 V8 opt-in extend (real-mode validated)"
date: 2026-05-19
status: complete
session: 183
previous_handoff: ./SESSION_182_PART_2_V17_2_REAL_MODE_DOGFOOD.md
---

# Session 183 — V17.5 V8 opt-in extend

## TL;DR

One feature commit plus a real-mode dogfood pass.
V17.5 lands the `use_extend_for_backdrop` flag on the
V8 `talking_head_with_backdrop` starter, closing the
SESSION 179 multi-backdrop concat seam at the recipe
layer. **Real-mode validated end-to-end** across four
renders (Sunset coastline / Underwater school of fish
+ V16 matte / two poker-room flyovers + V16 matte).
Total real-mode spend: **$6.25**. Four new
TRUST_CALIBRATION entries captured. Operator-suggested
direction queued for SESSION 184: a pre-recorded
backdrop library so V8 can compose Riggs over a saved
clip without re-paying $1.25 every render.

## What shipped

* **V17.5 starter knob** —
  `use_extend_for_backdrop: bool = False` on
  `talking_head_with_backdrop`
  (`shell/apps/compositions/starters.py`). Default off
  per V17 contract rule 12 (V13/V8 keep current
  behaviour; new optional kwargs only). When True, the
  backdrop is built as `1 × generate_visual_clip (10s,
  gen4.5)` + `N × extend_visual_clip (5s each, gen4_turbo
  last-frame conditioned)` instead of `N × generate +
  concat`.
* **Chain math helper** —
  `_compute_extend_backdrop_chain_length(script_chars: int)
  → int` returns `ceil(max(0, speech_seconds - 10) / 5)`
  using the existing
  `_estimate_avatar_speech_seconds(script_chars)` helper
  (11 chars/sec + 2s buffer). Clamps to
  `_MAX_BACKDROP_CHAIN_LENGTH - 1` so total chain length
  (base + extends) matches the concat path's safety cap.
* **Recipe form checkbox** added on the
  `talking_head_with_backdrop` recipe entry in
  `shell/apps/compositions/recipes.py`. V8 is already in
  `web/src/lib/api/recipes.ts` `LIVE_RECIPE_KINDS`; the
  form renderer is metadata-driven, so no SPA-side TS
  changes needed.
* **9 new tests** in
  `shell/apps/compositions/tests/test_v8_backdrop.py`:
  * `_compute_extend_backdrop_chain_length` helper
    coverage (0 extends ≤10s speech; ceil math; clamp).
  * Short-script lays down `generate + speech + composite`
    only (no extends, no concat).
  * 22s-script lays down `generate + 3 extends + speech +
    composite` — the motivating SESSION 179 case.
  * Pathological script clamps to
    `_MAX_BACKDROP_CHAIN_LENGTH - 1` extends.
  * `backdrop_ratio` propagates to base + every extend.
  * `backdrop_duration` is ignored on the extend path
    (chain segments are fixed at 10s base + 5s extend per
    the gen4_turbo per-render limit).
  * V16 matting interaction — `remove_avatar_bg=True`
    inserts the matte step between speech and composite
    on the extend path too.
  * End-to-end mock-mode execute path → COMPLETED;
    composite is the final asset.
  * Backwards-compat guard — no `extend_visual_clip` step
    appears anywhere in the chain when the flag is off,
    even on long scripts.

## Real-mode dogfood results (added end-of-session)

Four V8 renders all passing through the V17.5 extend
chain. Total real-mode spend: **$6.25**.

| Render | Extends | V16 matte | Cost | Final dur | Operator verdict |
|---|---|---|---|---|---|
| Sunset coastline 2 | 3 | no | $1.50 | 25.2s | "looks pretty good" — V17.5 win; trailing silent backdrop after Riggs stopped (separate gap, see calibration) |
| Underwater school of fish 2 | 3 | yes | $1.50 | 25.2s | seam-free wave but **fish became "blob of white" at the 11s extend boundary** — gen4.5 → gen4_turbo handoff loses subject identity for complex many-part subjects |
| Poker #1 (Sundown game variety) | **4** | yes | $1.75 | 30.2s | first N=4 chain; flyover-style atmosphere worked |
| Poker #2 (Sundown atmosphere pitch) | 3 | yes | $1.50 | 25.2s | "individuals sitting one and twos at tables and smoking" — prompt-engineering gap (density adjectives missing; "cigarette haze" → literal people-smoking) |

**Key V17.5 finding:** ambient motion / atmospheric
elements (waves, light, smoke, fog) **hold cleanly
across extend boundaries**; discrete-subject identity
(named animals, distinct people) **drifts at every
gen4.5 → gen4_turbo handoff**. Net win vs the concat
path (no visible 10s seam) but operator-visible blur
at boundary for subject-rich scenes. Captured in
TRUST_CALIBRATION as the load-bearing finding for
backdrop-prompt help-text + future V17.3 multi-
keyframe scope.

**Two latent gaps surfaced during dogfood (queued for
SESSION 184), neither V17.5-specific:**

1. **`generate_avatar_speech` primitive doesn't write
   `duration_ms` on its output Asset.** Result:
   `composite_video` can't compare edges for the
   "shorter-edge trim" rule and falls back to backdrop
   length. Operator-visible as Riggs going silent
   before the backdrop ends. One-line fix in the
   primitive.
2. **`composite_video` silently fallbacks** to backdrop
   length when one input's `duration_ms` is null. Should
   error loudly. Pattern fix.

## What's open

* **V17.3 (keyframes track) + V17.4 (V13 opt-in
  keyframes).** Independent of the extend track per
  the V17 dependency graph. Pending. V17.3 is the
  architectural fix for the subject-identity drift —
  pin a reference image at every extend boundary
  instead of relying on single-last-frame inference.
* **Speech-duration + composite trim gaps** (see Real-
  mode dogfood results above).
* **Operator-suggested direction (NEW):** *Record
  backdrop videos first, reuse them across renders.*
  Open the workspace asset library to backdrop CLIPs;
  V8's `backdrop_prompt` field becomes an alternative
  to a `backdrop_clip` asset picker. Cheaper iteration
  on scripts (a backdrop costs $1.25-$1.50; reusing it
  amortizes that), natural home for operator-uploaded
  footage when asset-upload UI lands, and a way to
  curate vetted cinematic stock. Queue placement: post-
  V17 polish or a new V19 slice depending on operator
  priority next session.

## Q-v17-5 resolution (open question closed)

**Resolution at V17.5 slice-open:** the V8 opt-in path
sizes its chain from the existing
`_estimate_avatar_speech_seconds(len(script))` helper;
each step primitive's `estimate_cost()` carries its own
per-second rate
(`generate_visual_clip` $0.05/s × 10s = $0.50 base;
`extend_visual_clip` $0.05/s × 5s = $0.25 per extend),
so `estimate_composition_cost(composition)` sums
correctly across the base + N extends without a chain-
wide helper. Refinement post-render falls out of the
existing per-step `cost_actual_micros` recording.

**Concrete numbers for a 22s-speech V8 render:**

* Concat path: 3 backdrops × $0.50 = $1.50 backdrop
  spend; visible 10s seam at every boundary.
* Extend path: $0.50 base + 3 × $0.25 = $1.25 backdrop
  spend; seam-free.

Cheaper and seam-free — the operator-visible win the
V17.5 design promised.

## Verification gates

```bash
# Backend
cd shell && source .venv/bin/activate
python -m pytest                      # 900 passed (compositions: 469, +9)
python -m pytest apps/compositions/tests/test_v8_backdrop.py
                                      # 29 passed (20 existing + 9 V17.5)

# SPA
cd web && pnpm test                   # 95 passed (unchanged)
pnpm build                            # clean type-check + bundle
```

Doctor at session open: 0 blocking, 3 unrelated warnings
(stale inventory-file-name mismatch, version drift on
pyproject.toml, pre-existing handoff numbering gap for
SESSION 053 + 172).

## Doc-with-commit checklist

* `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md` —
  V17.5 row marked SHIPPED with the helper / test
  counts; Q-v17-5 moved from "open" to "RESOLVED" with
  the resolution captured inline.
* `docs/design/VIDEO_COMPOSITION_V1.md` — no change.
  V17 slice tracking lives in the proposal doc; V1.md's
  change log is reserved for arc-level architectural
  events.
* `00-START-NEXT-SESSION.md` — slice table row added,
  SESSION 183 outcome section prepended, FIRST THING
  pointer flipped to SESSION 184 (real-mode dogfood
  V17.5 + V17.3 keyframes track).
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated via
  `python manage.py inventory`. Test count moved to 900.
* `docs/handoffs/SESSION_183_V17_5_V8_OPT_IN_EXTEND.md` —
  this file.
* `docs/TRUST_CALIBRATION.md` — no new entries.

## Files touched

```
shell/apps/compositions/starters.py        (~+90 lines / -25 refactored)
shell/apps/compositions/recipes.py         (+18 lines, 1 new RecipeField)
shell/apps/compositions/tests/test_v8_backdrop.py  (+250 lines, 9 tests)
docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md  (V17.5 row + Q-v17-5)
docs/CHARACTER_OS_INVENTORY.md             (regen)
00-START-NEXT-SESSION.md                   (SESSION 183 + 184 outlook)
docs/handoffs/SESSION_183_V17_5_V8_OPT_IN_EXTEND.md  (new)
```

## Calibration moments worth carrying

**Four new entries in `docs/TRUST_CALIBRATION.md`**:

1. **V17.5 extend chain holds ambient motion, drifts
   on complex subjects** (gen4.5 → gen4_turbo handoff).
   The design lock anticipated motion continuity but
   scoped subject continuity as "best-effort." Real-
   mode dogfood confirmed: ambient/atmospheric scenes
   chain cleanly; discrete-subject scenes lose
   identity at every boundary. V17.3 multi-keyframe is
   the architectural fix.
2. **Avatar speech asset doesn't record `duration_ms`**
   (composite trim direction wrong). Primitive drops
   the Runway response's duration; composite_video
   can't compare edges and defaults to backdrop length.
3. **Backdrop prompts need density adjectives**;
   "cigarette haze" reads as people smoking. Density
   words sit alongside subject words; atmospheric
   elements must be named as atmosphere, not as their
   physical source.
4. **Default Celery `acks_late=False` means worker
   SIGKILL drops in-flight task without redelivery**.
   `--pool=solo` makes revoke --terminate a no-op; only
   SIGKILL on the worker PID actually stops a long-
   running render. Acks-early is the right default for
   this codebase.

**Slice-open checklist** (codified SESSION 182) bore
out cleanly — V17.5 is a boolean knob on an already-
live recipe, so the four touchpoints were trivial.
Worth running anyway; the discipline confirms the
slice as much as the slice confirms the discipline.

## Next session

`SESSION_184` — three viable directions, operator's
pick:

1. **Quick polish slice:** speech-duration asset gap +
   composite trim direction fix (both surfaced this
   session). Two one-liners + a regression test for
   each. ~½ session.
2. **Backdrop library** (operator-suggested direction):
   pre-record cinematic backdrops as workspace Assets;
   V8 picks a backdrop instead of generating one each
   render. Amortizes the $1.25 backdrop cost across
   script iterations. Likely scope: new `backdrop_clip`
   asset_picker field on V8's recipe + starter branch
   for `backdrop_clip vs backdrop_prompt`. ~1 session.
3. **V17.3 keyframes track:** the architectural fix
   for the subject-identity drift finding. Multi-
   keyframe conditioning at every extend boundary
   instead of single-last-frame. Independent of V17.5
   per the V17 dependency graph; ~1 session.

See `00-START-NEXT-SESSION.md` FIRST THING for the
operator-locked choice.
