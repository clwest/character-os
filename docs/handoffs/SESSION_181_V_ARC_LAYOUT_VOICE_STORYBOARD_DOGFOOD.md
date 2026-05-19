---
title: "Session 181 — V-arc real-mode dogfood: layout / voice / storyboard families + V17 proposal"
date: 2026-05-18
status: complete
session: 181
previous_handoff: ./SESSION_180_V_ARC_REAL_MODE_DOGFOOD_POLISH.md
---

# Session 181 — V-arc layout / voice / storyboard dogfood

## TL;DR

Eight commits. Continued V-arc real-mode dogfood from
SESSION 180. **Eleven recipes validated end-to-end** —
biggest single-session validation run of the arc — bringing
the V-arc validation count from 5 to **16 of 18**. Surfaced
five production bugs (all fixed inline) plus one architectural
gap that became the V17 proposal.

By session-end:

* **Validated recipes (11):** `reels_format`, `pip_layout`,
  `cohost_layout`, `broll_splice`, `music_bed_pass`,
  `voice_design`, `recut_teaser`, `backdrop_layout`,
  `style_remix_pass`, `multi_lang_dub`, `storyboard_ad`.
  All four composite-video layout kinds (pip / cohost /
  backdrop / broll) now green.
* **Bugs fixed inline (5):**
  - broll concat dim-mismatch + missing setsar on
    pre/post segments
  - style_remix client timeout (60s default → 900s for
    Aleph's chunked path)
  - Aleph chunked-path tail-residual merge (sub-1s chunks
    crashed the batch)
  - gen4_image seed PNG bumped 1×1 → 8×8 (Runway tightened
    minimum to 2×2)
  - V13 `/data/_internal/images/` prefix added to
    `maybe_to_data_uri` (storyboard image-to-video failed
    on local URLs)
* **V17 proposed:** Runway `extend` video + `keyframes`
  capabilities never integrated. Operator-surfaced gap
  during storyboard_ad review (character drift across
  3 shots). Design doc at
  `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`; queued
  as task. Cures the V8 multi-backdrop seam workaround,
  V13 character drift, and V4's 10s ceiling in one slice.
* **Placeholder asset upload pattern emerged:** two recipes
  (music_bed_pass, multi_lang_dub) needed AUDIO assets but
  the SPA has no general audio-upload UI. Shell-side asset-
  row creation was the pragmatic dogfood path. Real fix
  is a separate "asset upload UI" slice not yet scoped.

Tests: Django **428** compositions tests (unchanged, no
Django-side code changes — all SESSION 181 fixes were
media-engine + the V11 style_remix client timeout test).
Media-engine **177** (162 → 177, +15 across the five fix
slices). SPA vitest **95** unchanged.

Real-mode spend this session: **~$3.50** (style_remix
$0.50 + storyboard_ad $0.87 + multi_lang_dub $0.05 +
voice_design $0.10 + plus several $0.01-$0.05 fast recipes
+ a few retried compositions during fix iteration).

V-arc validation status: **16 of 18.** Remaining:
`storyboard_voiced` (10-step, builds on storyboard_ad +
adds voice/audio chain) and `dialogue_scene` (multi-
spokesperson). Both deferred to SESSION 182 — operator
called the session here because storyboard_voiced is the
heaviest remaining slice and would benefit from V17's
keyframe/extend integration before being dogfooded.

## Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended (full text in
`docs/TRUST_CALIBRATION.md`):

1. **Operator "are we using X?" framing surfaces capability
   gaps the dogfood itself wouldn't.** SESSION 181 dogfooded
   11 recipes successfully end-to-end, all "green" — and the
   storyboard_ad output was operator-acceptable. The
   character-drift quality gap got noticed only when the
   operator asked "are we using extend + keyframes?"
   citing recall from another Claude Code session. The
   dogfood loop catches bugs (status codes, broken outputs);
   the operator framing catches missing capabilities. Both
   are necessary; neither substitutes for the other.

2. **Asset upload UI is a recurring gap.** music_bed_pass
   needed an AUDIO music bed; multi_lang_dub needed an
   AUDIO voice extract. Neither had a SPA upload path —
   shell-side `Asset.objects.create` + a generated file on
   disk was the pragmatic dogfood workaround. This came up
   twice in one session; will come up again any time a
   recipe needs an AUDIO or IMAGE input the operator
   doesn't already have in the workspace. Scope target:
   add a generic asset upload flow (drag-drop / file
   picker → media-engine upload endpoint → Asset row) as
   a workspace fabric extension.

3. **External API validation tightens over time — re-dogfood
   periodically.** V13's gen4_image seed PNG was 1×1 when
   shipped (SESSION 143). Runway tightened the API to
   require 2×2+ in the interim; the seed worked when
   committed, fails now. Pattern: APIs that "worked when
   shipped" need re-validation against current upstream
   contracts during periodic dogfood passes — not just
   when a code change touches that path. The V17 proposal
   has a similar shape: Runway capabilities exist that we
   didn't integrate at V-arc-close time.

## What shipped — commit by commit

### `adfa22a` — V7 broll layout probes base dims + setsar

SESSION 181 dogfood of `broll_splice` (1088×704 polished
base + 1280×720 cinematic_visual cutaway) failed with
ffmpeg rc=234 "Could not open encoder before EOF" + "task
finished with error code: -22 (Invalid argument)." Same
shape as the SESSION 180 intro_outro canvas-default bug:
hardcoded 1280:720 scale on the cutaway, no setsar on pre/
post segments.

Two changes:
* Probe base dims with `_probe_dimensions` + thread
  `(canvas_w, canvas_h)` into `_build_broll_filter` so the
  cutaway scales to match the base.
* Add `setsar=1` to v_pre and v_post segments — concat
  requires matching (width, height, SAR) across all
  inputs.

6 new media-engine tests: 4 pure-function (scales / SAR /
window validation / zero-duration guard) + 2 endpoint
integration (mismatched dims → output inherits base dims;
matched-dims regression guard).

### `583e3a3` — V11 style_remix client passes 900s timeout

SESSION 181 dogfood of style_remix_pass failed at the
default 60s `MediaEngineClient.request()` timeout before
Aleph's chunked path could respond. Aleph chunked rendering
routinely takes 3-5+ min (each chunk ~30-60s; multi-chunk
sources serialize the wall-clock wait even with parallel
fan-out).

Fix: `style_remix` client method gains `timeout: float =
900.0` kwarg, passes through to `request()`. Same shape as
V16's remove_avatar_background timeout override (SESSION
179). 1 new V11 test (timeout regression guard).

### `9e569de` — V11 Aleph tail-residual merge

Once the timeout fix unblocked the Aleph call, the chunked
path hit a NEW bug: a 10.04s source split into 5s + 5s +
0.04s, and the 0.04s tail blew up the whole batch with
"Asset duration must be at least 1 seconds." Aleph rejects
sub-1s clips.

Fix: extracted `_merge_sub_min_tail_chunk` helper that
detects sub-1s tail chunks and concats them into the
penultimate chunk via the ffmpeg concat demuxer. 5 new
media-engine tests (tail above min / sub-min merge /
single-chunk pass-through / 2-chunk collapse / exact-at-min
left alone).

My earlier curl test with a different source (exactly-10s
V16 underwater composite) had succeeded because that
source split into 2 even chunks. Different source shape,
same endpoint, completely different outcome — classic
real-mode-only discovery.

### `6e62dba` — V13 gen4_image seed PNG bumped to 8×8

storyboard_ad dogfood failed step 0 with Runway 400:
"Invalid asset dimensions. Height and width must be at
least 2px. Got 1×1." V13 ships a 1×1 neutral-grey PNG as a
no-op reference seed (gen4_image requires at least one
referenceImages entry); Runway tightened the validation
in the interim.

Bumped seed to 8×8 — still a single solid colour so it
doesn't bias generation, sits well inside any future
minimum-size bumps, ~70 bytes of payload. 5 new tests pin
dimensions ≥2×2, payload <1KB, deterministic across calls.

### `5cc0954` — V13 prompt_image rewrites /data/_internal/images/ paths

storyboard_ad dogfood failed step 3 (first image-to-video)
with Runway 400: "Invalid string: must start with
\"https://\"" on `promptImage`. V13's generate_image outputs
land at `/data/_internal/images/<hash>.png`; the V-arc
storyboard chain feeds those into V4's generate_visual_clip
which passes `asset.file_path` straight to Runway.

`maybe_to_data_uri` already handled two legacy local-path
prefixes (`/api/runway/image/...`,
`/api/characters/.../portrait`) but the V13 prefix was
never added. Extended with a third branch: maps
`/data/_internal/images/<file>` to
`<data_path>/_internal/images/<file>` and embeds as a data
URI. Path-traversal guarded. 5 new tests: V13 path rewrite
/ missing-file fall-through / traversal rejection /
external HTTPS pass-through / empty-input pass-through.

The fix unblocked the entire storyboard image-to-video
chain — step 3 was failing on the first reference image, so
steps 4-6 never ran.

### V17 proposal — docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md

Operator surfaced the gap during storyboard_ad review:
"Are we using Extend Video and Keyframes?" Grep confirmed
neither feature has any reference in the codebase. V17
proposal drafted:

* Purpose: cure V8 multi-backdrop seams, V13 character drift,
  V4 10s ceiling — all single concrete gaps tracked back to
  Runway capabilities we never integrated.
* 5 new contract rules layered on V1's existing 9 (extend
  = single asset / keyframes = inputs not steps / opt-in
  backwards-compat / cost surfacing / no DAG).
* 6 slices (V17.0 → V17.5), ~4 sessions of work total.
* 5 open questions to resolve at implementation time.
* Out-of-scope list anchoring it as a focused post-close
  slice, not a V-arc reopen.

Doc is `status: proposed (not yet scope-locked)` — needs
operator review + edit pass before becoming binding.

## State at session-end

**Registry counts (unchanged since SESSION 180):**

```
starters.py:    18 starter functions
recipes.py:     18 RECIPES entries
primitives:     14 (mock × 3 + real × 11)
media-engine:   124 routes
```

**Tests:**

```
Django:        428 compositions tests (unchanged)
Media-engine:  177 (162 → 177, +15 across 5 fix slices)
SPA vitest:     95 (unchanged)
```

**V-arc real-mode validation status (16 of 18):**

* ✓ talking_head — SESSION 158
* ✓ long_form_ad — SESSION 179
* ✓ cinematic_visual — SESSION 179
* ✓ talking_head_with_backdrop — SESSION 179
* ✓ talking_head_polished — SESSION 180
* ✓ reels_format — SESSION 181
* ✓ pip_layout — SESSION 181
* ✓ cohost_layout — SESSION 181
* ✓ broll_splice — SESSION 181 (post fix)
* ✓ music_bed_pass — SESSION 181 (post placeholder)
* ✓ voice_design — SESSION 181
* ✓ recut_teaser — SESSION 181
* ✓ backdrop_layout — SESSION 181
* ✓ style_remix_pass — SESSION 181 (post 2 fixes)
* ✓ multi_lang_dub — SESSION 181 (post placeholder)
* ✓ storyboard_ad — SESSION 181 (post 2 fixes)
* **storyboard_voiced** — deferred (heaviest, benefits from V17)
* **dialogue_scene** — deferred to SESSION 182+

**Running processes at session-close (operator's box):**

```
Django runserver:   pid 19587 (auto-reloads on .py changes)
Media-engine:       pid 21694 (uvicorn --reload, restarted
                    SESSION 180 to clear the textfile= window)
Celery worker:      pid 24687 (restarted SESSION 181 to pick
                    up the style_remix client timeout change;
                    no new primitives this session)
```

**Workspace artifacts created this session:**

* 1 `Composition` (`5b4b5635-...`, `style_remix_pass`,
  completed after 3 retries — anime style transfer on
  underwater backdrop)
* 1 `Composition` (`b9ae048b-...`, `storyboard_ad`,
  completed after 2 retries — 15s Hook/Action/Payoff
  founder narrative)
* 1 `Composition` (each: `reels_format` / `pip_layout` /
  `cohost_layout` / `broll_splice` / `music_bed_pass` /
  `voice_design` / `recut_teaser` / `backdrop_layout` /
  `multi_lang_dub` — all completed first try or after one
  inline fix)
* 1 VOICE asset (Riggs Founder New Voice, voice_id
  `1bc3b784-...`)
* 1 placeholder AUDIO asset (music bed — synth pad, 12s)
* 1 placeholder AUDIO asset (Riggs voice extract for
  dub, 5s)
* 1 dubbed AUDIO asset (Spanish translation of Riggs's
  3-rules script)

## Next session priorities — SESSION 182

Two clear tracks; operator picks:

**Track A — V17 implementation.** V17.0 (media-engine
extend endpoint) is the natural first slice. Roughly ½
session. Then V17.1 (Django extend_visual_clip primitive)
in the same session, leaving V17.2-V17.5 for later. The
V17 proposal at
`docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md` is the
read-first input.

**Track B — Close out the last 2 V-arc recipes.**
`storyboard_voiced` (10-step, heaviest spend ~$2.50) and
`dialogue_scene` (multi-spokesperson, needs ≥2 cast). Both
work today against the V-arc as-shipped — they don't
strictly need V17 to validate, just won't get the
character-drift / seam benefits. Operator deferred both
SESSION 181 close on the framing "no sense doing
storyboard_voiced before extend lands."

My read: **Track A first.** The V17 proposal is sitting
draft; operator review + V17.0 implementation in one
session moves the arc forward more than two more validations
of the as-shipped recipes. If V17.0 lands clean,
storyboard_voiced + dialogue_scene can dogfood against the
improved primitives later.

Expected class of bugs in V17:
* Runway API surface differences vs documented behaviour
  (the same gen4_image / gen4_turbo / Aleph mismatch
  patterns we hit in V11, V13, V16)
* Cost-estimator drift (the extend per-second rate may
  differ subtly from gen4_turbo's per-clip rate)
* Caching strategy for extend chains (Q-v17-4)
