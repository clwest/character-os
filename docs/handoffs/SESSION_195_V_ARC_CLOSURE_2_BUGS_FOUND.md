---
title: "Session 195 — V-arc closure attempt: 1/2 recipes validated, 2 production bugs surfaced"
date: 2026-05-19
status: complete
session: 195
previous_handoff: ./SESSION_194_V18_POLISH_DOUBLE.md
arc_validation: V_ARC_2_LAST_RECIPES
---

# Session 195 — V-arc closure attempt + 2 production bugs

## TL;DR

Set out to close the V-arc to 100% by real-mode validating the
last 2 unvalidated recipes (`storyboard_voiced` + `dialogue_scene`).
**One recipe completed end-to-end; the other partial. Two distinct
production bugs surfaced in 2 recipes attempted.**

The SESSION 158 calibration "real-mode dogfood finds bugs in
every recipe" is now confirmed 2-for-2 — promoting from
"high-yield" to "expected behavior" in TRUST_CALIBRATION.

No code shipped this session (real-mode validation only). Three
new TRUST_CALIBRATION entries. Two follow-up fix slices queued
for SESSION 196. Real-mode spend: **~$3.17**.

## Real-mode fire 1 — `storyboard_voiced` (V15.4 bonus, 10 steps)

### Setup

* Spokesperson: Riggs (`06bf999f`)
* Theme: small-business founder origin story (3 storyboard frames
  + 15s narration)
* Shared image_seed=42 across the 3 shots for visual coherence
* Real-mode (mock_mode=false)

### Result

`composition.status = partial`. **8 of 10 steps succeeded**:

| Step | Primitive | Status | Notes |
|---|---|---|---|
| 0 | generate_image | ✓ | 20.7s — Stability Hook frame |
| 1 | generate_image | ✓ | 22s — Stability Action frame |
| 2 | generate_image | ✓ | 22s — Stability Payoff frame |
| 3 | generate_visual_clip | ✓ | Runway gen4_turbo image-to-video |
| 4 | generate_visual_clip | ✓ | (silent video) |
| 5 | generate_visual_clip | ✓ | (silent video) |
| 6 | concat_clips | ✓ | 2.6s — 15s composite at `/data/_internal/concats/0f4b5d0d16d1ce24.mp4` |
| 7 | generate_avatar_speech | ✓ | 28.5s — Riggs narration, 11.6s Cloudfront MP4 |
| 8 | audio_extract | ✓ | 0.8s — 11.6s MP3 at `/data/_internal/audio_extracts/34858986fced83bf.mp3` |
| 9 | **mix_audio** | **✗** | 500 from `/internal/audio/mix/` in 60ms |

### Bug 1 — `mix_audio` filtergraph fails on silent base

**Exact ffmpeg error** (reproduced via direct probe to
`/internal/audio/mix/`):

```
ffmpeg rc=234: Stream specifier ':a' in filtergraph description
[1:a]volume=0.0dB,afade=t=in:st=0:d=0.00,afade=t=out:st=999999:d=0.00[bed];
[0:a][bed]amix=inputs=2:duration=first:normalize=0[outa]
matches no streams.
Error binding filtergraph inputs/outputs: Invalid argument
```

**Root cause**: `mix_audio`'s filtergraph references `[0:a]` (the
base's audio stream), but in `storyboard_voiced` the base is the
silent visual concat — `generate_visual_clip` outputs are
video-only. ffmpeg fails fast.

V14 `mix_audio` was designed for `music_bed_pass` (base = avatar
speech WITH audio + overlay = music track → `amix`). V15.4's
storyboard_voiced bonus added the audio_extract + mix_audio
chain assuming the same semantics — but storyboard_voiced wants
audio REPLACEMENT (`-map 1:a` from overlay), not audio MIXING.

**Fix slice (operator-picked at SESSION 195 close):**
Media-engine `/internal/audio/mix/` detects missing base audio
stream + falls through to `-map 1:a` filtergraph. Same endpoint,
smarter behavior. No recipe change. **~½ session.** Queued for
SESSION 196.

### Spend on this partial: ~$1.92 lost

3 Stability image gens (~$0.12) + 3 Runway gen4_turbo
image-to-video (~$1.50) + 1 Runway avatar_speech (~$0.30) +
ffmpeg work ($0). The upstream outputs are still browseable in
the Asset Library v1 — they didn't disappear with the
composition's partial status. The 15s silent storyboard concat
is at `f106500b` (visible at `/workspace/assets/f106500b...`).

## Real-mode fire 2 — `dialogue_scene` (V14, multi-character)

### Setup

* Primary spokesperson: Riggs (`06bf999f`)
* 4 turns: Riggs ↔ Sasha brand-collab meet-cute
* Operator added a spontaneous 5th line ("I got added randomly")
  via the dialogue_lines editor — proves the editor is usable
  on the fly
* Real-mode

### Result

`composition.status = completed` ✓. **5 generate_avatar_speech +
1 concat_clips. 145s wall-time. $1.25 actual spend.**

| Step | Primitive | Elapsed | Output |
|---|---|---|---|
| 0 | generate_avatar_speech | 19.1s | Riggs talking head 5s |
| 1 | generate_avatar_speech | 19.3s | Sasha talking head 5s |
| 2 | generate_avatar_speech | 17.1s | Riggs talking head 5s |
| 3 | generate_avatar_speech | 21.6s | Sasha talking head 5s |
| 4 | generate_avatar_speech | 16.8s | Riggs talking head 5s (operator's bonus line) |
| 5 | concat_clips | 2.8s | 25s composite (final_asset) |

Per-line avatar identity stays consistent across turns (Riggs
on 0/2/4, Sasha on 1/3). Concat seam is a hard cut between
talking heads as expected for V14 (no crossfade — queued as
future polish if operator wants it).

### Bug 2 — `concat_clips` role semantics mismatch

**Observation**: the concat output `fe769db3` was stamped
`role=BACKDROP` by the A2 emit-time logic. Wrong semantics for
a dialogue scene's final deliverable.

**Root cause**: `apps.compositions.primitives.concat_clips`
unconditionally sets `role=AssetRole.BACKDROP.value` on its
PrimitiveResult (introduced SESSION 186 A2). The static
`primitive_kind → role` mapping breaks down because `concat_clips`
serves multiple recipes with different semantic intents:

| Recipe | What's concat'd | Right role |
|---|---|---|
| `talking_head_with_backdrop` (V18 backdrop chain) | 3+ backdrop frames | BACKDROP ✓ |
| `storyboard_voiced` | 3 silent visual clips | BACKDROP ✓ |
| `dialogue_scene` | N talking heads → final | **COMPOSITE_OUTPUT ✗ stamped BACKDROP** |

**Operator-visible consequence**: A7 role-filtered
`backdrop_clip_id` picker (currently 42 BACKDROP clips) would
now offer this dialogue scene's 25-second final as a valid
"backdrop." Picking it would produce a nonsensical V18 render
(avatars-over-avatars).

**Fix slice (operator-picked at SESSION 195 close):**
Add `result_role` param to combinator primitives (`concat_clips`
first; `composite_video` + `mix_audio` likely too). Recipe
starter passes `result_role` in the step's params; primitive
reads + stamps. Backwards-compat default keeps existing
V18/storyboard_voiced BACKDROP behavior; recipe overrides per
use. **~½ session.** Queued for SESSION 196.

## Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended at SESSION 195
close:

1. **mix_audio assumes base clip has audio.** V14/V15.4 design
   oversight; mock primitives don't decode media streams so the
   bug stayed latent across 30+ sessions of test coverage.
2. **concat_clips role semantics are recipe-dependent.** A2's
   unconditional BACKDROP stamp is wrong for dialogue_scene.
   Combinator primitives need a per-recipe role override seam.
3. **Real-mode dogfood finds bugs in EVERY recipe — confirmed
   2-for-2.** The SESSION 158 calibration is now promoted from
   "high-yield" to "expected behavior." Two corollaries:
   * Mock test coverage is necessary but not sufficient.
   * Recipes that landed pre-A2 (V14, V15.4) are highest-risk;
     each validated will likely surface ≥1 bug.

   The A-arc growth template now needs a 9th step: **arc-close
   ceremony must include a real-mode validation pass for every
   recipe affected by the arc.** A-arc closure at SESSION 193
   ran one composition (mock_mode); A7's role-filter behavior
   across other recipes wasn't validated, and we paid for it at
   SESSION 195 with the concat_clips finding.

## Tests at session close

No code changes; suites unchanged from SESSION 194:

| Suite | Count |
|---|---|
| Django | 1006 |
| - compositions | 575 |
| Media-engine | 194 |
| SPA vitest | 134 |

Workspace asset count grew **138 → 153 (+15)** from the two
real-mode fires (9 from storyboard_voiced partial — 3 images
+ 3 visual clips + 1 concat + 1 avatar speech + 1 audio
extract; 6 from dialogue_scene complete — 5 talking heads +
1 concat).

## State at session close

* Django + SPA + Celery worker + media-engine — all still
  running in background.
* Real-mode spend: **~$3.17** total ($1.92 storyboard_voiced
  partial + $1.25 dialogue_scene complete).
* V-arc status: **17 of 18 recipes validated** (dialogue_scene
  closed today; storyboard_voiced remains partial pending
  mix_audio fix).

## FIRST THING (SESSION 196): two fix slices

Both surfaced this session; both half-session-sized; both
operator-picked at close.

### Slice 1 — mix_audio silent-base handling (media-engine)

Detect missing base audio stream in `/internal/audio/mix/` +
fall through to `-map 1:a` filtergraph. Backwards-compat with
existing music_bed_pass behavior (base has audio → amix as
today). New test fixture for the silent-base shape.

When this lands, re-fire `storyboard_voiced` against the same
inputs to close the V-arc to 100%. The 8 successful upstream
outputs from SESSION 195 are still browseable + the
composition `ffe9132b` can be re-rendered cheaply (only the
last 2 ffmpeg steps need to fire — ~$0 of additional spend if
we re-use the upstream outputs).

### Slice 2 — combinator-primitive role override

Add `result_role` param to `concat_clips` (and likely
`composite_video` + `mix_audio` too). Recipe starter passes
`result_role` per step; primitive reads + stamps. Backwards-
compat default keeps current BACKDROP stamp. Update the
A-arc PRIMITIVE_TO_ROLE mapping table to document that
combinator primitives have recipe-dependent role.

Apply the override to:
* `dialogue_scene.concat_clips` → `COMPOSITE_OUTPUT`
* Other combinator step calls reviewed per recipe (`composite_video`
  in V18 / V8 layouts; `mix_audio` in music_bed_pass — likely
  correct as-is, but explicit review).

### After both fix slices

Re-fire `storyboard_voiced` real-mode → V-arc 100% closure
(was the SESSION 195 goal). Spend probably ~$0 if we reuse the
upstream outputs from the partial composition, or ~$1.92 if
we fire from scratch.

## Operational notes for SESSION 196

* **All services still up** from SESSION 193 (Django, SPA,
  Celery worker) + SESSION 195 (media-engine bootted real-
  mode). No restart needed unless operator wants to reset.
* **No real-mode FORCE_MOCK overrides** in .env. Real-mode
  remains hot for the SESSION 196 slices' tests if needed
  (most won't need it — fix slices are mock-mode testable).
* **Asset Library v1 surface validates the findings.** Open
  `/workspace/assets` and the concat_clips bug is browseable
  — the dialogue_scene final at `fe769db3` shows up under
  `role=backdrop` despite being a dialogue deliverable.
