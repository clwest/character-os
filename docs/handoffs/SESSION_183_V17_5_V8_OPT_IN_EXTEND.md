---
title: "Session 183 — V17.5 V8 opt-in extend (mock-mode validated)"
date: 2026-05-19
status: complete
session: 183
previous_handoff: ./SESSION_182_PART_2_V17_2_REAL_MODE_DOGFOOD.md
---

# Session 183 — V17.5 V8 opt-in extend

## TL;DR

One feature commit. V17.5 lands the
`use_extend_for_backdrop` flag on the V8
`talking_head_with_backdrop` starter, closing the
SESSION 179 multi-backdrop concat seam at the recipe
layer. Mock-mode validated; real-mode dogfood deferred
to SESSION 184 per the human/AI testing split. Slice-
open checklist held cleanly — no new TRUST_CALIBRATION
entries.

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

## What's open

* **Real-mode dogfood.** Mock-mode validated only. Per
  V-arc discipline, slice isn't fully shipped until
  real-mode renders the chain end-to-end. Deferred to
  SESSION 184 per the human/AI testing split — operator
  drives the SPA dogfood, AI tails DB/logs/API.
* **V17.3 (keyframes track) + V17.4 (V13 opt-in
  keyframes).** Independent of the extend track per the
  V17 dependency graph. Pending.

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

None new. SESSION 182's slice-open checklist (string
choice values, `LIVE_RECIPE_KINDS` opt-in, default-
aware submission, fixture shape) bore out cleanly
because V17.5 is a boolean checkbox knob on an already-
live recipe — no string choices to wrangle, V8 already
on the live list, and the SESSION 182 `01ea94d` form-
renderer fix is the single source of truth for the
default-aware submission path. The mock-mode
backwards-compat guard
(`test_extend_default_is_false_concat_path_unchanged`)
caught zero regressions. Worth noting: slice-open
checklists that take 5 minutes to verify on a small
slice are still worth running — they confirm the
discipline, not just the slice.

## Next session

`SESSION_184` — operator-driven real-mode dogfood of
V17.5 + (optional, parallel) open V17.3 keyframes
track. See `00-START-NEXT-SESSION.md` FIRST THING for
the dogfood checklist.
