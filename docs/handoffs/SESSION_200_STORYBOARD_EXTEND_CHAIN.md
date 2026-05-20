---
title: "Session 200 — storyboard extend-chain closes the V-arc UX gap"
date: 2026-05-19
status: complete
session: 200
previous_handoff: ./SESSION_199_OUTRO_PARITY_FINISHED.md
---

# Session 200 — storyboard extend-chain (V-arc UX gap closed)

## TL;DR

The last known V-arc UX gap shipped: hard motion seams between
the 5-second shots of `storyboard_ad` + `storyboard_voiced` are
now addressable from the form, no recipe forks. Operator picks
the trade-off per fire.

Operator picked **Option C** when scoping — combine both
mitigations under one feature so a single render produces a
fully-smoothed storyboard:

* **Per-shot extend chain** (intra-shot smoothness). Each shot
  becomes generate (5s, image-to-video) → extend (5s,
  last-frame-conditioned). Doubles each shot from 5s → 10s and
  removes the visible jolts at the 5-second mark within each
  shot.
* **Inter-shot crossfade** (transition softness). Optional
  ffmpeg `xfade` + `acrossfade` duration between consecutive
  shots at concat time. 0 = hard cuts (default); 250–500ms is a
  tasteful soft blend.

Both are opt-in. The default 7-step `storyboard_ad` and 10-step
`storyboard_voiced` shapes are preserved when the operator
doesn't toggle anything — backwards-compat with SESSIONS
197–199.

Tests: **Django 1027 → 1039 (+12)**, **media-engine 197 → 204
(+7)** (+2 from the post-close intro_outro silent-base fix).
SPA + vitest unchanged. **Real-mode dogfood spend: ~$2.50**
(two fires; the first surfaced 2 bugs, second validated all
SESSION 200 features end-to-end).

## What landed

Four small slices.

### Slice 1 — `crossfade_ms` on `concat_clips`

Three layers updated in lockstep:

* **`media-engine/app/routers/internal.py`**
  * `InternalConcatClipsCreate` gained
    `crossfade_ms: int = Field(default=0, ge=0, le=5000)`. The
    5-second cap matches the per-shot duration ceiling — values
    above that would consume the entire next clip.
  * Cache key extended with `|xfade={body.crossfade_ms}` so an
    operator who fires with then without crossfade gets distinct
    cached outputs.
  * Dispatch branches on `crossfade_ms > 0` →
    `_build_xfade_concat_cmd` (new helper). The existing
    concat-demuxer + `-c copy` fast path stays in place for
    `crossfade_ms == 0` (the SESSION 199 close-out path
    untouched).
  * `_build_xfade_concat_cmd` builds a filter_complex chain:
    normalize each input (`scale=1280:720:force_original_aspect_ratio=decrease,pad=1280:720`,
    `setsar=1`, `fps=30`), ffprobe-detect per-clip durations,
    then chain `xfade(transition=fade)` for video. Audio chain
    branches on whether the inputs carry audio streams —
    `acrossfade` when present, dropped entirely when silent
    (mirrors the silent-base shape from SESSION 196 slice 1).
* **`shell/character_os/clients/media_engine.py`**
  * `MediaEngineClient.concat_clips()` accepts `crossfade_ms`
    kwarg; passes through in the request body. Default 0 keeps
    every existing caller working unchanged.
* **`shell/apps/compositions/primitives/concat_clips.py`**
  * Reads `crossfade_ms` from `step.params`; validates `>= 0`
    + integer-coercible; raises `PrimitiveError` on invalid
    input.
  * Mock-mode duration math shortens the naive sum by
    `(len(clips) - 1) * crossfade_ms` so downstream steps
    (especially `mix_audio`) see realistic numbers.
  * `extra_source_spec` audit row now carries `crossfade_ms`
    + the existing `reencode` / `result_role` fields.

### Slice 2 — `use_extend_for_shots` in storyboard starters

`storyboard_ad` and `storyboard_voiced` starters gained the
kwarg. Step layout shifts when True:

**`storyboard_ad` with `use_extend_for_shots=True`**

| Position | Primitive | Inputs |
|---|---|---|
| 0–2 | `generate_image` (Hook / Action / Payoff) | — |
| 3–5 | `generate_visual_clip` | `reference_image` from 0/1/2 |
| 6–8 | `extend_visual_clip` | `source` from 3/4/5 |
| 9 | `concat_clips` | clips from 6/7/8 |
| 10 | `add_intro_outro` (optional) | base from 9 |

7 → 10 steps without outro; 8 → 11 with outro.

**`storyboard_voiced` with `use_extend_for_shots=True`**

| Position | Primitive | Inputs |
|---|---|---|
| 0–2 | `generate_image` | — |
| 3–5 | `generate_visual_clip` | from 0/1/2 |
| 6–8 | `extend_visual_clip` | from 3/4/5 |
| 9 | `concat_clips` | from 6/7/8 |
| 10 | `generate_avatar_speech` | — |
| 11 | `audio_extract` | base from 10 |
| 12 | `mix_audio` | base from 9, music from 11 |
| 13 | `add_intro_outro` (optional) | base from 12 |

10 → 13 steps without outro; 11 → 14 with outro.

`crossfade_ms` stamps into the concat step's params when set so
the runner forwards it through to the primitive at execute
time.

### Slice 3 — recipe metadata fields

Two new `RecipeField` rows added to both `storyboard_ad` +
`storyboard_voiced` in `apps/compositions/recipes.py`:

* `use_extend_for_shots` (checkbox, default False). Operator
  copy describes the ~3× cost (3 extra Runway renders) so the
  trade-off is explicit.
* `crossfade_ms` (number, default 0, min 0, max 5000). Operator
  copy explains the 250–500ms sweet spot.

No `param_map` entries needed — both fields map 1:1 to starter
kwarg names so the default kwargs builder handles routing.

### Slice 4 — tests

Twelve backend + five media-engine tests added.

Backend (in `apps/compositions/tests/`):

* `test_v5_long_form.py` — 4 new primitive-level tests:
  * `test_concat_clips_mock_mode_crossfade_shortens_duration`
  * `test_concat_clips_real_mode_forwards_crossfade_ms`
  * `test_concat_clips_rejects_negative_crossfade_ms`
  * `test_concat_clips_rejects_non_integer_crossfade_ms`
* `test_v15_api.py` — 8 new starter + metadata tests:
  * `test_storyboard_voiced_use_extend_for_shots_adds_extend_chain`
  * `test_storyboard_voiced_extend_plus_outro_appends_fourteenth_step`
  * `test_storyboard_voiced_crossfade_ms_forwarded_to_concat`
  * `test_storyboard_voiced_recipe_exposes_extend_and_crossfade_fields`
  * `test_storyboard_ad_use_extend_for_shots_adds_extend_chain`
  * `test_storyboard_ad_extend_plus_outro_appends_eleventh_step`
  * `test_storyboard_ad_crossfade_ms_forwarded_to_concat`
  * `test_storyboard_ad_recipe_exposes_extend_and_crossfade_fields`

Media-engine (`tests/test_concat_crossfade.py`, new file):

* `test_concat_silent_clips_with_crossfade_shortens_total_duration`
  — Storyboard shape. Synthesizes 3 silent clips via lavfi,
  fires the endpoint with `crossfade_ms=500`, ffprobes the
  output: video stream present, no audio (matches input
  shape), duration ≈ 14s (15s naive − 2×0.5s overlap).
* `test_concat_audio_clips_with_crossfade_keeps_both_streams`
  — Voiced shape. 3 clips with audio + crossfade ⇒ output
  carries both video + audio streams (acrossfade chain
  actually wired through).
* `test_concat_with_zero_crossfade_uses_existing_fast_path`
  — Backwards-compat: `crossfade_ms=0` keeps the
  concat-demuxer + `-c copy` fast path. Duration is the
  exact naive sum, no overlap.
* `test_concat_crossfade_ms_validation_rejects_negative` —
  422 before any ffmpeg work.
* `test_concat_crossfade_ms_validation_caps_at_five_seconds`
  — 422 above 5000ms.

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **1039** | +12 (1027 → 1039) |
| - compositions | **608** | +12 (596 → 608) |
| Media-engine | **204** | +7 (197 → 204; +5 SESSION 200 features + 2 intro_outro silent-base regression) |
| SPA vitest | 134 | unchanged |

`pnpm build` clean. Real-mode dogfood spend: **~$2.50**.

## Post-close dogfood — bugs found + fixed same session

After SESSION 200's feature commit landed, operator fired
`storyboard_ad(use_extend_for_shots=True, crossfade_ms=500,
outro_text=...)` real-mode. Two bugs surfaced; both fixed
in the same session.

### Bug 1 — `intro_outro` silent-base (fixed, commit `8f6ff6c`)

`/internal/clips/intro_outro/` failed at step 10 with
`Error binding filtergraph inputs/outputs: Invalid argument`.
The filter graph references `[0:a]` (body clip's audio) but
the SESSION 200 silent-base path produces a silent concat
output (storyboard_ad has no narration; extends + generates
are all silent). **Same shape as SESSION 196's mix_audio
silent-base bug.**

**Latency root cause:** SESSION 198 added `outro_text` to
`storyboard_ad` with 3 mock-only tests. The real-mode path
was never exercised because `storyboard_voiced` (similar
shape) had `mix_audio` sitting between concat + intro_outro,
which the SESSION 196 fix gave an audio stream by the time
intro_outro consumed it. `storyboard_ad` has no mix step —
concat → intro_outro directly — so the silent-base invariant
that holds for `storyboard_voiced` never held for
`storyboard_ad` with outro.

**Fix mirrors SESSION 196 slice 1**: ffprobe the body for an
audio stream; when absent, synthesize a silent `anullsrc`
track at the body's duration so the `concat=a=1` contract
holds. Two regression tests (outro-only + dual-card paths
on silent bodies). Media-engine 202 → 204.

### Bug 2 — Celery worker stale (operational; recurring)

The first fire's concat output was 30.25s @ 24fps — the
naive 3 × 10.083s with **no crossfade overlap subtracted**,
despite `step.params` carrying `crossfade_ms: 500`. Root
cause: Celery worker started at 19:03; SESSION 200 feature
commit landed at 21:38; fire at 21:48. Worker was running
SESSION 199 primitive code that didn't know about
`crossfade_ms`. Django runserver auto-reloaded the new
starter (so step.params was written correctly); the OLD
Celery primitive consumed step.params, ignored the unknown
key, called the client with default 0 → demuxer fast path.

**Symptom was silent**: 11/11 steps `succeeded`; only
ffprobe of the output revealed the missing crossfade
(24fps Runway source instead of the 30fps xfade
normalization).

After Celery restart, re-fire produced concat output
**29.27s @ 30fps** — naive 30.249 − 2×0.5s overlap =
29.249s. xfade verified.

**Third hit of "Celery doesn't auto-reload"** (SESSION 18B,
193, 200). Promoted from advisory calibration to pre-fire
check: when last commit against `shell/apps/compositions/primitives/`
is newer than Celery start time, restart Celery first.

## Dogfood validation outcome

Composition `c592dd51` (re-fire after both fixes + Celery
restart):

- **status**: completed ✓
- 235s wall-time, **$1.62 spend** (3 images + 3 generates +
  3 extends + concat + outro)
- 11/11 steps succeeded
- final asset 32.27s @ 30fps; concat at 29.27s @ 30fps
  (xfade applied + normalized)
- outro text "24/7 Global AI" rendered cleanly on silent base

**All three SESSION 200 features validated end-to-end**:

- ✓ `use_extend_for_shots=True` — extends produced 10.083s
  each (5s generate + 5s last-frame extend); 30.249s naive
  pre-crossfade.
- ✓ `crossfade_ms=500` — concat duration 29.27s = naive
  sum − 2×0.5s overlap; framerate normalized 24→30fps.
- ✓ `outro_text` on silent base — survived the silent-base
  fix end-to-end.

Total SESSION 200 real-mode spend: **~$2.50** ($0.88
partial first fire + $1.62 successful re-fire). Wasted
spend attributable to the Celery-stale calibration miss:
~$0.88.

## Calibration moments worth carrying

**Three new TRUST_CALIBRATION entries (28 total)**:

1. **Celery worker doesn't auto-reload — third hit; promote
   to pre-fire checklist.** Previous calibrations caught
   the "worker not running" and "new primitive registration"
   shapes. SESSION 200 caught the **silent stale-code**
   shape: worker running, composition fires, all steps
   succeed, output is semantically wrong. Pre-fire check
   added: compare `shell/apps/compositions/primitives/`
   git mtime vs Celery worker start time.

2. **Mock-mode test coverage hides upstream stream-shape
   drift — fourth hit.** Same shape as V14/V15.4 mix_audio:
   "we assume base has audio" baked into the filtergraph,
   breaks when fed silent input. Forward defense: any ffmpeg
   endpoint referencing `[N:a]` from a downloaded clip
   should ffprobe-detect first. Audit candidates: add_captions,
   composite_video, trim_clip, reformat_clip, style_remix.

3. **SESSION 200 dogfood — two bugs, one fix, one operational
   lesson.** Pattern is now 4-for-4 across SESSIONS 195/197/200
   dogfoods: real-mode finds bugs in every recipe. Post-feature
   real-mode dogfood is load-bearing for any feature touching
   ffmpeg endpoints.

Worth noting (but not new calibration): the per-shot extend
pattern reuses V17.5's `use_extend_for_backdrop` shape almost
exactly. Reusing the same "extend after generate" mental model
across the codebase keeps the operator surface coherent —
operators who learned the V17.5 trade-off (smoother motion,
~3× cost) get the same shape on storyboards without new
explanation.

## What's still queued

V-arc UX work is now exhausted — every known gap closed.

### Remaining polish / parity follow-ups

* **`outro_text` for `talking_head`** — scope decision still
  deferred (would duplicate `talking_head_polished`'s
  surface).
* **2 of 18 V-arc recipes unvalidated against real Runway** —
  `storyboard_voiced` was validated SESSION 197; the unfired
  pair are now the recipes that haven't had a real-mode
  closure fire. Deferrable.

### Bigger backlog items (unchanged)

* **Asset upload UI** (1-2 sessions) — likely the most
  impactful "feature" remaining.
* **W12 legacy form retirement** (1 session).
* **K6.4 v3 architectural fix** (1 session).
* **K7.x v3 YouTube oEmbed** (½ session).

### Optional real-mode validation

The new storyboard extend chain hasn't been real-mode-fired.
Operator could fire either `storyboard_ad` or
`storyboard_voiced` with `use_extend_for_shots=True` to
validate end-to-end — but real-mode cost roughly triples per
shot (3 extra Runway renders), so the prior $1.12 closure fire
becomes ~$3.50 with the full chain on. Optional and
deferrable.

### New-arc candidates (unchanged)

* **B-1 Transcript Miner** (top strategic per memory).
* **B-3 Personalized Video** (biggest revenue unlock).
* **B-14 Multi-Platform Variants** (distribution stickiness).

### Recommended next direction

Same as SESSION 199 — small-slice backlog is thinning. Three
quick-wins-style sessions in a row + one V-arc UX session
covers the polish work. Natural next moves:

1. **Open a new arc** (B-1 transcript miner is closest to
   shipped infra).
2. **Asset upload UI** (1-2 sessions; the operator-content
   bottleneck).
3. **Real-mode validation pass** on the SESSIONS 198–200 new
   surfaces if the operator wants confidence before opening a
   new arc.
