---
title: "Session 199 — outro_text parity finished across remaining V-arc recipes"
date: 2026-05-19
status: complete
session: 199
previous_handoff: ./SESSION_198_POLISH_TRIPLE.md
---

# Session 199 — outro_text parity FINISHED

## TL;DR

Third quick-wins session in the outro_text parity rollout. Three
small slices ship the same `outro_text` shape to the remaining
V-arc recipes that needed it:

* **Slice A — `cinematic_visual`.** Single-step recipe; outro
  at position 1 chained from the lone `generate_visual_clip`.
* **Slice B — `cinematic_visual_extended`.** Variable position
  based on extend chain length (1 base + N extends → outro at
  position N+1).
* **Slice C — `dialogue_scene`.** Mirrors `long_form_ad`'s
  variable-position logic (multi-line: after concat; single-line
  degenerate: directly after the lone speech step).

Backend tests **1020 → 1027 (+7)**. SPA + media-engine
unchanged. No real-mode spend.

## outro_text parity status across V-arc

After SESSIONS 197 + 198 + 199:

| Recipe | outro_text | Notes |
|---|---|---|
| `storyboard_voiced` | ✓ (SESSION 197) | First recipe; closure-fire validated |
| `talking_head_polished` | ✓ (pre-arc) | Original template |
| `storyboard_ad` | ✓ (SESSION 198) | Sibling of storyboard_voiced |
| `long_form_ad` | ✓ (SESSION 198) | Multi-chunk + single-chunk paths |
| `cinematic_visual` | ✓ (SESSION 199) | Single-step recipe |
| `cinematic_visual_extended` | ✓ (SESSION 199) | Extend chain |
| `dialogue_scene` | ✓ (SESSION 199) | Multi/single-line paths |

**7 recipes** carry `outro_text` now (one pre-existing +
six added across the three quick-wins sessions). The
remaining V-arc recipes either:

* Are pure post-processing (`recut_teaser`, `style_remix_pass`,
  `voice_design`, `multi_lang_dub`, polish family) — outro
  would be an unusual fit; defer.
* Are intermediate primitives never expected to be a final
  deliverable.
* Already produce a polished output where outro fits the
  parent recipe instead (`talking_head` → `talking_head_polished`
  is the canonical pair).

Outro parity rollout effectively **complete** for the
deliverable-shaped V-arc recipes. Remaining polish is the
storyboard extend-chain UX gap (motion seams at 5s/10s
transitions).

## What landed

### Slice A — cinematic_visual

* `recipes.py::cinematic_visual` — adds `outro_text`
  RecipeField. Position between `duration` and `_NAME_FIELD`.
* `starters.py::cinematic_visual` — accepts kwarg; when
  non-empty, appends `add_intro_outro` at position 1
  chained from step 0's `generate_visual_clip`.

### Slice B — cinematic_visual_extended

* `recipes.py::cinematic_visual_extended` — adds
  `outro_text` field positioned after `seed`.
* `starters.py::cinematic_visual_extended` — accepts
  kwarg; outro lands at position `last_chain_position + 1`
  where `last_chain_position = extend_count` (base at 0 +
  N extends 1..N → last is N). All valid target_durations
  (15/20/25/30/40/50) have ≥1 extend, so last_chain_position
  ≥ 1 always.

### Slice C — dialogue_scene

* `recipes.py::dialogue_scene` — adds `outro_text` field
  + `_dialogue_resolver` updated to pass outro_text through
  (the custom resolver was the only thing requiring extra
  wiring; everything else uses the default param map).
* `starters.py::dialogue_scene` — accepts kwarg; mirrors
  `long_form_ad`'s variable-position logic via
  `last_output_position` local that advances past the
  concat when one's laid down. Single-line: outro at
  position 1; multi-line: outro at position
  `len(validated_lines) + 1`.

## Tests added (7)

In `apps/compositions/tests/test_v15_api.py`:

1. `test_cinematic_visual_outro_text_appends_second_step` —
   slice A with-outro produces 2 steps.
2. `test_cinematic_visual_blank_outro_keeps_one_step` —
   backwards-compat.
3. `test_cinematic_visual_extended_outro_text_appends_after_chain` —
   slice B: outro chains to the last extend
   (target_duration=20 → 1 base + 2 extends + 1 outro).
4. `test_cinematic_visual_extended_blank_outro_keeps_chain` —
   backwards-compat (target_duration=15 → 2 steps, no outro).
5. `test_dialogue_scene_outro_text_multi_line_appends_after_concat` —
   slice C multi-line: outro chains to concat.
6. `test_dialogue_scene_outro_text_single_line_chains_to_speech` —
   slice C single-line: outro chains directly to speech (no
   concat).
7. `test_dialogue_scene_outro_text_field_exposed_in_recipe_metadata` —
   custom resolver pass-through wired correctly.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **1027** | +7 (1020 → 1027) |
| - compositions | **596** | +7 (589 → 596) |
| Media-engine | 197 | unchanged |
| SPA vitest | 134 | unchanged |

`pnpm build` clean (no SPA changes — recipe forms are
metadata-driven). Real-mode spend: **$0**.

## Calibration moments worth carrying

No new TRUST_CALIBRATION entries. SESSION 197 documented the
operator-noticed-during-dogfood pattern; SESSION 196
documented the combinator-primitive seam; SESSION 198
documented the variable-position outro pattern (multi-chunk
vs single-chunk). This session applies all three patterns
across the remaining recipes.

The outro_text parity rollout across SESSIONS 197 + 198 +
199 demonstrates the **quick-wins parity pattern** at full
scale:

* SESSION 197: 1 recipe + closure fire (~1 session).
* SESSION 198: 2 recipes + 1 taxonomy follow-up (~½ session).
* SESSION 199: 3 recipes (~½ session).

Cumulative: 6 recipes got outro_text in ~2 sessions of
focused work across 3 sessions. Pattern works because each
slice mirrors a 1:1 template (talking_head_polished), so
each successive slice gets faster.

## Operational notes for SESSION 200

**No arc in flight.** Backlog narrows further with the outro
parity rollout complete.

### Remaining polish / parity follow-ups

* **Storyboard extend-chain.** SESSION 195/197 storyboard
  videos show motion seams at the 5s + 10s shot transitions.
  Mirror V17.5's `use_extend_for_backdrop` pattern for
  storyboard_voiced + storyboard_ad. Closes the last known
  V-arc UX gap.
* **`outro_text` for `talking_head`** — currently only
  `talking_head_polished` has it. Adding to bare
  `talking_head` would duplicate the polished surface;
  scope decision deferred.

### Bigger backlog items (unchanged)

* **Asset upload UI** (1-2 sessions).
* **W12 legacy form retirement** (1 session).
* **K6.4 v3 architectural fix** (1 session).
* **K7.x v3 YouTube oEmbed** (½ session).

### Optional real-mode validation

The new outro flows still haven't been real-mode-fired
across the recipes. Operator could fire any of them with
`outro_text` set (~$0.30-$1.92 depending on the recipe) to
validate end-to-end. Bundle with any content creation flow.

### New-arc candidates (unchanged)

* **B-1 Transcript Miner** (top strategic per memory).
* **B-3 Personalized Video** (biggest revenue unlock).
* **B-14 Multi-Platform Variants** (distribution stickiness).

### Recommended next direction

Three quick-wins sessions in a row is a satisfying cadence
but the small-slice backlog is now thinning. The natural
next moves:

1. **Open a new arc** (B-1 transcript miner is closest to
   shipped infra).
2. **Asset upload UI** (1-2 sessions; the operator-content
   bottleneck).
3. **Storyboard extend-chain** (½-1 session; closes the
   last known V-arc UX gap).
