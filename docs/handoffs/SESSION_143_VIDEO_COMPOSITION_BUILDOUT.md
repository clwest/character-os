---
title: "Session 143 — Video composition arc V3-V13 buildout"
date: 2026-05-14
status: complete
session: 143
previous_handoff: ./SESSION_142_VIDEO_COMPOSITION_LOCK.md
---

# Session 143 — V3 through V13 shipped + V9→V7 reorder

## TL;DR

Eleven capability slices shipped in one extended session, plus
one mid-session reorder commit. The video composition arc that
was scope-locked in SESSION 142 (V0-V15, ~12-18 sessions
estimated) collapsed eleven of those slices into a single
session run — V3 through V13 inclusive. Test count more than
doubled (133 → 339); media-engine surface area grew from 109
to 122 routes with 13 new `/internal/*` endpoints.

The last slice (V13) is the third hackathon-shipped capability
the operator confirmed live production usage for, alongside
V10 (29-language dubbing) and V11 (Aleph style remix). V12
(`transcribe` + `recut_teaser`) is the **first net-new
capability beyond what the hackathon shipped** — OpenAI
Whisper transcription unlocks the "take a 60-second ad → auto-
pick the strongest sentence → output a 15-second vertical
teaser" recipe.

`storyboard_voiced` deferred to V14+: needs an `audio_extract`
primitive that we haven't built yet.

## Commit log

Twelve commits, all on `main`, none pushed:

| Order | Commit | Slice | What it shipped |
|---|---|---|---|
| 1 | `54032c2` | **V3** | `generate_avatar_speech` + `talking_head` (closes K6.5) |
| 2 | `1251def` | **V4** | `generate_visual_clip` + `cinematic_visual` |
| 3 | `c2c4ba2` | **V5** | `split_script` + `concat_clips` + `long_form_ad` (launch differentiator; promoted from V7 in SESSION 142) |
| 4 | `7c968a5` | **V6** | Video backwards-compat shim (Composition→Video sync signal) |
| 5 | `7782c34` | (reorder) | V9 → V7 reorder docs (composite ahead of `talking_head_with_backdrop`) |
| 6 | `3af1c28` | **V7** | `composite_video` + `mix_audio` + 5 layout starters |
| 7 | `545f991` | **V8** | `talking_head_with_backdrop` (first multi-step recipe) |
| 8 | `ec130a9` | **V9** | captions / intro_outro / trim / reformat + 2 starters |
| 9 | `f237ac7` | **V10** | `design_voice` + `dub_audio` + 2 starters (29-lang dubbing restored) |
| 10 | `cfe9214` | **V11** | `style_remix` (Aleph, chunked path) + `style_remix_pass` |
| 11 | `8b24465` | **V12** | `transcribe` (Whisper) + `add_captions` auto + `recut_teaser` (**first net-new**) |
| 12 | `43be57b` | **V13** | `generate_image` + `storyboard_ad` (storyboard_voiced deferred) |

## What shipped (concrete)

### 8 new step primitives registered (V3-V13)

* `generate_avatar_speech` (V3) — Runway `/v1/avatar_videos` `gwm1_avatars`
* `generate_visual_clip` (V4) — Runway `gen4_turbo` / `gen4.5`
* `split_script` + `concat_clips` (V5) — gpt-5-mini chunker + ffmpeg concat
* `composite_video` + `mix_audio` (V7) — ffmpeg filter_complex overlay
  (4 layout kinds) + music_bed audio mix
* `add_captions` + `add_intro_outro` + `trim_clip` + `reformat_clip` (V9) —
  ffmpeg polish operations
* `design_voice` + `dub_audio` (V10) — Runway `eleven_multilingual_ttv_v2` +
  `eleven_voice_dubbing` (29 languages)
* `style_remix` (V11) — Runway `gen4_aleph` with chunked path support
* `transcribe` (V12) — OpenAI Whisper `whisper-1`
* `generate_image` (V13) — Runway `gen4_image`

Plus the three V2 mock primitives still in the registry. Total
registry size: 12 entries.

### 12 starter compositions live

| Starter | Slice | Steps | Purpose |
|---|---|---|---|
| `talking_head` | V3 | 1 | Single avatar speech |
| `cinematic_visual` | V4 | 1 | Silent visual clip |
| `long_form_ad` | V5 | N+1 | Multi-minute talking-head via stitched chunks |
| `pip_layout` | V7 | 1 | Picture-in-picture composite |
| `backdrop_layout` | V7 | 1 | Avatar over cinematic backdrop (V8 building block) |
| `cohost_layout` | V7 | 1 | Main + cohost overlay |
| `broll_splice` | V7 | 1 | Cinematic cutaway window in avatar timeline |
| `music_bed_pass` | V7 | 1 | Music mixed under voice |
| `talking_head_with_backdrop` | V8 | 3 | First multi-step recipe combining V3+V4+V7 |
| `talking_head_polished` | V9 | 1-3 | Speech + optional captions + optional intro/outro |
| `reels_format` | V9 | 1 | 9:16 vertical conversion |
| `voice_design` | V10 | 1 | Custom brand voice creation |
| `multi_lang_dub` | V10 | 1 | Audio dubbing to one of 29 languages |
| `style_remix_pass` | V11 | 1 | Aleph visual transform (5 presets) |
| `recut_teaser` | V12 | 2 | Auto-pick strongest sentence + reformat to Reels |
| `storyboard_ad` | V13 | 7 | 3-shot Hook/Action/Payoff with reference-image coherence |

Total: 16 starters (counting all V7 layout modifiers individually).

### 14 new media-engine `/internal/*` endpoints

* V3: `POST /internal/clips/avatar_speech/`,
  `GET /internal/tasks/{task_id}/` (generalised poll)
* V4: `POST /internal/clips/visual/`
* V5: `POST /internal/clips/concat/`
* V7: `POST /internal/clips/composite/`, `POST /internal/audio/mix/`
* V9: `POST /internal/clips/captions/`,
  `POST /internal/clips/intro_outro/`,
  `POST /internal/clips/trim/`,
  `POST /internal/clips/reformat/`
* V10: `POST /internal/voices/design/`, `POST /internal/audio/dub/`
* V11: `POST /internal/clips/style_remix/`
* V12: `POST /internal/transcribe/`
* V13: `POST /internal/images/`

### Test progression

| At end of | Tests | Δ |
|---|---|---|
| Session start (V2 done) | 133 | — |
| V3 shipped | 145 | +12 |
| V4 shipped | 161 | +16 |
| V5 shipped | 192 | +31 (13 splitter + 18 long-form) |
| V6 shipped | 199 | +7 |
| V7 shipped | 222 | +23 |
| V8 shipped | 233 | +11 |
| V9 shipped | 257 | +24 |
| V10 shipped | 276 | +19 |
| V11 shipped | 293 | +17 |
| V12 shipped | 318 | +25 |
| V13 shipped | 339 | +21 |

**+206 tests across the session run.** Test isolation
`ALLOWED_FILES` updated 11 times to accept the per-slice test
files that construct Composition / Asset rows directly.

## The reorders that surfaced

Two slice reorders happened across V0-V13, both because a
prior slice's data shape revealed a latent dependency:

1. **V5 promoted from V7** (SESSION 142, end-of-session).
   Trigger: operator's research that no AI video provider
   ships single-call >20s output; long-form is therefore the
   launch-differentiating capability, not a v2 nice-to-have.
   Effect: `long_form_ad` shipped as the third capability
   slice instead of the seventh.

2. **V9 promoted to V7** (SESSION 143, after V6). Trigger:
   `talking_head_with_backdrop` (originally V7) structurally
   requires `composite_video`, which was scheduled for V9 in
   the original V0 design. The V5 promotion exposed this gap
   by removing intermediate slices. Effect: composite
   primitives shipped before `talking_head_with_backdrop`;
   polish primitives demoted to V9.

After two reorders, the calibration moment crystallizes:
**when locking the next slice's scope, check it against the
dependency graph of every prior slice's data shape — not
just the immediate predecessor.** The V0 design did this for
the load-bearing slices (V1 schema, V2 runtime) but missed it
for the recipe slices (V7's hidden V9 dependency).

## "We already had this" — restoration framing

Three slices the V0 doc framed as "ports" of hackathon code,
but which the operator confirmed live production usage for:

* **V10 — 29-language dubbing.** The operator: *"I used this
  at the hackathon."* SUPPORTED_DUB_LANGS frozenset matches
  the hackathon's tuple byte-for-byte; Runway anchors
  (`eleven_multilingual_ttv_v2` + `eleven_voice_dubbing`)
  identical so billing + behavior stay consistent.
* **V11 — Aleph style remix.** The operator: *"we used the
  noir preset live."* ALEPH_STYLE_PRESETS dict prompts ported
  verbatim. Chunked path (full Option B implementation per
  operator's explicit ask) covers sources >5.5s.
* **V13 — storyboard.** The operator used the 3-shot
  Hook/Action/Payoff pattern at the hackathon. The
  `reference_image` chain from gen4_image → gen4_turbo
  matches the visual-coherence trick from
  `storyboard_service.py`.

The correct framing for these slices: **restoration of
shipped capability under the new Asset+Composition
architecture**, not "first-time net-new feature."

## The first net-new capability — V12

V12 (`transcribe` + `recut_teaser`) is the first slice that
ships a capability the hackathon didn't have:

* **OpenAI Whisper transcription** — first non-Runway provider
  in the media engine. CLIPs are ffmpeg-extracted to MP3
  server-side then sent to `whisper-1`'s verbose_json
  endpoint for segment-level timing.
* **AI editorial cuts** — gpt-5-mini picks the most
  hook-worthy line from a transcript via the
  `pick_strongest_segment("hook")` helper. Graceful fallback
  to "longest" when the API key is missing or the LLM call
  fails (same K6 pattern).
* **`recut_teaser` composition** — synchronous Whisper +
  sentence-pick at composition-create time, then a
  deterministic 2-step composition (trim + reformat) with
  the picked timing baked in. Same pre-computation pattern
  as V5's `long_form_ad`.

V12 also extends V9's `AddCaptionsPrimitive` to accept a
TRANSCRIPT input slot (auto mode) — operator-supplied caption
lists still take precedence when both are available.

## Deferred from V-arc

* **`storyboard_voiced`** — the V0 design listed it under
  V13, but implementing it requires extracting the audio
  track from a `generate_avatar_speech` CLIP so it can be
  mixed under the storyboard via `mix_audio`. We don't have
  an `audio_extract` primitive yet. The V13 commit message
  + `storyboard_ad` docstring both flag the deferral; V14+
  picks it up.

## Doc discipline gap caught at end of session

V3-V13 shipped eleven feature commits without paired
context-kit refreshes. The operator caught this and asked
two questions:
1. Is documentation being updated per slice?
2. How do we ensure future slices don't drift the same way?

**Resolution (this handoff is part of):**
* Catch-up pass: regenerate inventory, update slice table +
  change log + start-here + CLAUDE.md + WHAT_IT_IS, write
  this handoff, append calibration events.
* Going-forward discipline codified in CLAUDE.md: feature
  commits MUST include or be immediately followed by a
  doc commit. End-of-session handoff aggregates.

See CLAUDE.md §"Doc-with-commit discipline" for the rule.

## What's next (SESSION 144)

**V14 — `dialogue_scene` + optional `audio_extract`.**

* **`dialogue_scene` starter** — ports the hackathon's
  `dialogue_service.py`. Multi-character skit: N
  `generate_avatar_speech` calls alternating across the
  cast, concat'd in script order. Pre-computation pattern
  mirrors V5's `long_form_ad` — split the script into
  lines at starter creation time, lay down N speech +
  1 concat steps.
* **`audio_extract` primitive** (optional V14 extension) —
  CLIP → AUDIO via ffmpeg `-vn`. Small primitive, unlocks
  the deferred `storyboard_voiced` starter.

After V14, only V15 (SPA recipe gallery) remains in the
V-arc.

Alternative parallel slice: **R1 — RealtimeSession schema**.
Unblocked since V1 shipped. Mirrors V1's pattern.

## Calibration carried into session memory

* **"Map the predecessor before scoping" repeats.** V5
  promotion + V9 promotion both surfaced the same pattern.
  This is now the rule, not the exception.
* **"We already had this" is the most valuable operator
  signal.** Three slices (V10, V11, V13) reframed
  mid-session from "v2 nice-to-have" to "restore shipped
  capability" because the operator confirmed live production
  use.
* **Doc discipline ties to commits.** Feature commits
  without context-kit updates ship the bits but leave the
  next session starting from stale guidance. Catch this
  early next time.

## AI Notes

* The slice count this session (11 capability slices in one
  run) is unusual. The V0 design lock estimated V0-V15 at
  ~12-18 sessions; V3-V13 alone closed in one. Two factors:
  (1) the V2 runtime was load-bearing — every subsequent
  slice is "wrap one hackathon service as a primitive +
  register it" which is small. (2) the operator's "we
  already had this" reframing turned what looked like new
  features into ports.
* Every V3-V13 slice followed the same shape: media-engine
  endpoint → shell client method → primitive class →
  starter helper → 15-25 tests → commit. That shape worked.
  V14 should follow it.
* If V14 ships `audio_extract`, that's a small primitive
  worth bundling with `dialogue_scene` rather than its own
  slice. Going-forward discipline note: bundle small
  primitives that share an arc rather than fragment them.

* Per-slice context-kit updates aren't expensive — they're
  one slice-table mark + one change-log line + one Status
  column update. The expense is forgetting to do them.
  CLAUDE.md's new "Doc-with-commit discipline" rule
  externalizes the reminder.
