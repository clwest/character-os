---
title: "Session 179 — V-arc real-mode dogfood + V16 remove_avatar_background"
date: 2026-05-18
status: complete
session: 179
previous_handoff: ./SESSION_178_B_ARC_BRAND_PIVOT.md
---

# Session 179 — V-arc real-mode dogfood + V16

## TL;DR

Six commits. Mixed real-mode dogfood + bug-fix + first-post-
close V-slice. SESSION 178 closed flagging "17 of 18 V-arc
recipes never real-mode validated" as the SESSION 179 focus.
This session validated three of them end-to-end with real
Runway credits (`long_form_ad`, `cinematic_visual`,
`talking_head_with_backdrop`), surfaced four production bugs
that mock-mode tests couldn't catch, fixed every one, and shipped
**V16 (`remove_avatar_background`)** as the V-arc's first post-
close addition to solve the cinematic-backdrop white-frame
problem the dogfood exposed.

By session-end:

* `talking_head_with_backdrop` produces clean cinematic
  composites with the avatar silhouetted over arbitrary
  backdrops (no Runway-baked white square framing the tile)
* The composition runtime correctly handles long avatar
  speech over short backdrops via the multi-backdrop chain
  (N=ceil(speech_seconds / 10), capped at 6)
* The media-engine `_download_concat_input` resolver honors
  `/data/`-prefixed SPA mount paths so intermediate
  Composition assets (concat / composite / mix outputs) can
  flow as inputs into downstream steps
* `cinematic_visual` text-only path correctly routes to
  gen4.5 instead of failing 400 on gen4_turbo's
  reference-image requirement
* The SPA can play back media-engine-hosted concat /
  composite / mix assets via the new Vite `/data` proxy +
  FastAPI StaticFiles mount

Three TRUST_CALIBRATION entries added (Celery-stale-on-
primitive-add, ffmpeg-can't-infer-muxer-from-tempfile-suffix,
real-mode-dogfood-three-for-three-finds-bugs).

Tests: Django **843** (816 → 843, +27 — V8 multi-backdrop +
V16 primitive + V16 starter wiring + isolation allowlist).
Media-engine **143** (133 → 143, +10 — concat resolver +
remove_background endpoint). SPA vitest **95** unchanged.

Real-mode spend this session: **~$3.50** across four
compositions (the multi-backdrop fix re-fire, the
cinematic_visual validation, the V16-broken first dogfood,
and the V16 successful retry).

## Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended (full text in
`docs/TRUST_CALIBRATION.md`):

1. **Celery worker doesn't auto-reload on new primitive
   registrations.** Django runserver auto-reloads on file
   changes; Celery doesn't. SESSION 179's V16 dogfood failed
   the first attempt with `UnknownPrimitiveError: No primitive
   registered for 'remove_avatar_background'` because the
   worker had been running since before V16's
   `apps/compositions/primitives/__init__.py` was modified.
   Same gotcha as the SESSION 147 drift audit's "stale running
   processes" item. **Pattern**: every commit touching
   `apps/compositions/primitives/` OR `apps/*/tasks.py` OR
   `apps/*/signals.py` needs a Celery worker restart on the
   operator's box. The cheap insurance is `ps aux | grep
   "celery -A"` at session start (already in the boot drift
   sweep) PLUS at any moment a new primitive / task / signal
   ships.

2. **ffmpeg can't infer output muxer from `.webm.tmp`
   tempfile suffix.** V16's media-engine endpoint wrote to
   `output_path.with_suffix(".webm.tmp")` and ffmpeg exited
   immediately with "Unable to choose an output format" —
   propagating as a BrokenPipeError when the rembg-frame
   writer hit the closed stdin. **Fix**: pin the muxer
   explicitly with `-f webm`. **Pattern**: when shelling out
   to ffmpeg with double-extension tempfile names (`.webm.tmp`,
   `.mp4.tmp`, etc.), always pair the temp suffix with an
   explicit `-f <muxer>` flag. The default behavior of "infer
   from extension" is silently lost the moment the extension
   isn't a single recognized format. Secondary lesson: the
   raw BrokenPipeError surfaced as a 500 with no diagnostic;
   the streaming write loop now drains ffmpeg's stderr on
   broken-pipe so operators see "ffmpeg rc=N (closed stdin
   after frame X): <real error>" instead.

3. **Real-mode dogfood found a bug in every recipe it
   touched.** The SESSION 176 R-arc hardening calibration
   warned that mock-only test coverage hides upstream drift;
   the V-arc proved it true at scale. Three real-mode runs
   yielded four production bugs:
   - `talking_head_with_backdrop` real-mode → visible 3-second
     backdrop loop seam during a 22s avatar speech (V8 single-
     backdrop limitation, never surfaced by mock tests because
     mock-mode doesn't render motion).
   - `cinematic_visual` real-mode → 400 because text-only
     prompts defaulted to `gen4_turbo` which requires a
     reference image (model selection inverted vs. the user's
     intent).
   - `talking_head_with_backdrop` multi-backdrop real-mode →
     500 on composite step because the concat output's
     `/data/_internal/...` path couldn't be resolved as an
     absolute filesystem path on the media-engine side.
   - V16 first real-mode dogfood → 500 because ffmpeg
     couldn't infer the output format from `.webm.tmp`.

   Three-for-three: every real-mode dogfood found a bug. Mock-
   mode test coverage is necessary but insufficient.
   **Pattern**: at least one real-mode dogfood per operator-
   facing slice before claiming "shipped." Budget the
   ~$0.50-$2.00 of Runway spend per validation as the cost of
   not shipping broken recipes. The V-arc's "17 of 18 recipes
   never real-mode validated" backlog still has 14
   uninspected recipes — high probability of hidden bugs in
   each. SESSION 180 priority.

## What shipped — commit by commit

### `f9f000e` — SPA playback for media-engine concat / composite / mix assets

Two-line infrastructure change unblocking SPA playback of
intermediate Composition assets:

* **`media-engine/app/main.py`**: `app.mount("/data", StaticFiles(directory=settings.data_path, check_dir=False), name="data")`
  exposes the media-engine filesystem at `/data/*` HTTP routes.
  Without this, `<video src="/data/_internal/concats/x.mp4">`
  404s because the file exists on disk but no route serves it.

* **`web/vite.config.ts`**: new `/data` proxy entry forwarding
  `localhost:5174/data/*` to `localhost:8001/data/*`. SPA
  pages can now render concat / composite / mix outputs by
  their canonical SPA-facing URL.

Production deploy needs a parallel reverse-proxy entry (or a
Django streaming proxy view) so `<spa-origin>/data/*` resolves
to the media-engine filesystem.

### `9db31c3` — cinematic_visual text-only path uses gen4.5

Real-mode dogfood of `cinematic_visual` with a text prompt
(no reference image) failed 400. `resolve_model(None, ...)`
defaulted to `gen4_turbo` which requires `prompt_image`. Fix
in `media-engine/app/routers/internal.py` `post_internal_visual_clip`:

```python
has_image = bool(body.prompt_image and body.prompt_image.strip())
if has_image:
    model = resolve_model(None, settings)
else:
    model = "gen4.5"
```

Routes text-only prompts to `gen4.5` (text-to-video) and
image-prompted ones to the existing model picker.

### `077c349` — V8 multi-backdrop chain for talking_head_with_backdrop

Operator-driven from a SESSION 179 dogfood observation:
"The entire video was like 22 seconds but the visual clip
only moved for like 3 seconds, can we increase that somehow
without it looking like its just repeating the same thing
over and over."

Root cause: gen4.5 caps cinematic backdrops at 10s/clip. V8's
v1 starter laid down a single backdrop and `composite_video`
looped it to match the avatar's speech length — a 22s speech
over a 5s backdrop produced a visible ~3s motion seam
repeating ~4x.

Fix lays down N backdrops sized so `concat(N) >= estimated
speech duration`. The composite primitive trims the long
edge, so a slightly over-provisioned chain is free.

**New step layout** (`talking_head_with_backdrop`):
* Steps 0..N-1 — N × `generate_visual_clip` (same prompt + duration)
* Step N — `generate_avatar_speech`
* Step N+1 — `concat_clips` (skipped when N==1; preserves the
  legacy 3-step layout for short scripts)
* Step N+(1|2) — `composite_video`, background = concat (or
  step 0 when N==1), foreground = speech

**Sizing math**:
* `_estimate_avatar_speech_seconds(chars) = max(5,
  int(chars / 11) + 2)` — 11 chars/sec + 2s buffer, 5s floor
* `_compute_backdrop_chain_length(chars, dur) =
  max(1, min(ceil(speech / dur), _MAX_BACKDROP_CHAIN_LENGTH))`
  — clamped to 6 backdrops so a pathological script can't
  spin up runaway Runway calls (max ~$0.50/composition vs
  ~$0.08 for the v1 single-backdrop path)

Backdrop duration param always present (default 10s = gen4.5
max) so the chain-length math has a deterministic per-clip
ceiling. Existing operator override (`backdrop_duration`
kwarg) flows through to every clip in the chain.

Six new V8 tests (17 total) cover single-backdrop legacy
layout, 5-backdrop chain (500-char script → 8 steps), the
pathological-clamp case (25_000 chars → MAX=6), custom
backdrop_duration knob, and direct helper coverage for both
new pure functions. One test renamed in prep
(`test_starter_omits_optional_backdrop_params_when_unset` →
`test_starter_omits_optional_backdrop_ratio_when_unset`)
since `duration` is now always set, only `ratio` is optional.

### `04fcdb0` — composite/concat resolver honors /data/ SPA-mount prefix

First real-mode multi-backdrop chain run blew up on the
composite step (the resolver bug that 077c349 exposed). The
concat step produced
`Asset.file_path=/data/_internal/concats/x.mp4`; the
composite primitive passed that through to media-engine; the
`_download_concat_input` resolver tried to read the literal
`/data/_internal/...` on the host filesystem and raised
FileNotFoundError → surfaced as a 400.

Fix in `media-engine/app/routers/internal.py
_download_concat_input`: rewrite `/data/<rest>` to
`<settings.data_path>/<rest>` before the existence check —
the same mapping the StaticFiles mount in main.py uses on
the read side. Relative paths and http(s):// URLs unchanged.

Four new tests in `test_concat_input_resolver.py` cover the
four URL shapes the resolver sees in the wild (data-mount,
relative, missing-under-data-mount, arbitrary-absolute).

### `57c2530` — V16 remove_avatar_background primitive + opt-in V8 wiring

Operator's chosen fix for Runway's baked-in white background
behind every gwm1_avatars talking head. Three pieces in one
commit (Django ↔ media-engine cross-service convention).

**Media-engine** — new `POST /internal/clips/remove_background/`:
* Pipeline: ffmpeg-decode → opencv frame loop → rembg
  (u2net_human_seg ONNX) → ffmpeg-encode (libvpx-vp9 /
  yuva420p alpha). Audio muxed from the original file as
  input #1.
* Cached at `data/_internal/matted/<hash>.webm` keyed off
  (clip_url + model).
* Strict model allowlist (v1 ships `u2net_human_seg` only).
* Sync; heavy on CPU — ~3.7 fps through rembg on M-series;
  ~2.4 min for a 22s 24fps clip. Composition runtime already
  async via Celery so no request blocks.
* Three new deps: `rembg==2.0.75`, `onnxruntime==1.26.0`,
  `opencv-python-headless==4.13.0.92`. First call downloads
  the ~176MB u2net_human_seg.onnx model to `~/.u2net/`.
* 6 endpoint tests cover mock-mode, validation, cache short-
  circuit, model allowlist.

**Django primitive** `remove_avatar_background`:
* Single CLIP input → single CLIP output (chained matting
  loses edge detail; strict single-input rule guards
  against it).
* 10 primitive tests covering registry / cost / mock-mode /
  input shape / model allowlist / failure propagation.
* `MediaEngineClient.request()` gained a per-call `timeout`
  override so this slow endpoint can sit on a 900s budget
  without bumping the global default.

**Starter wiring** for `talking_head_with_backdrop`:
* New `remove_avatar_bg: bool = False` kwarg inserts the
  matting step between speech and composite when on;
  composite's foreground rewires to the matted clip.
* Default OFF so existing V8 tests (including the SESSION
  179 multi-backdrop chain) stay green.
* 3 new starter tests cover both single-backdrop and
  5-backdrop chain layouts with the flag on.
* Recipe registry surfaces the flag as a labeled checkbox
  so the SPA gallery exposes it directly.

Cost note: matting is CPU work on media-engine, not a Runway
spend. The cost estimator returns a token 200 micros so the
SPA shows the step on the cost preview without overstating
the dollar impact — the real cost is wall-clock latency.

### `88b341e` — V16 muxer fix + broken-pipe stderr capture

First real-mode V16 dogfood hit a 500. Standalone repro
showed ffmpeg dying immediately with "Unable to choose an
output format for '<file>.webm.tmp'" — the muxer couldn't
be inferred from our double-extension tempfile name. Added
`-f webm` to the ffmpeg cmd to pin the muxer explicitly.

Also hardened the streaming write loop: a BrokenPipeError on
`proc.stdin.write` now snapshots how far we got, drains
ffmpeg's stderr, and surfaces a `_RemoveBackgroundError` with
the real ffmpeg diagnostic — instead of letting the
BrokenPipeError bubble up as a generic 500. Operators get
"ffmpeg rc=1 (ffmpeg closed stdin after frame N): <stderr>"
which is actionable.

Verified end-to-end on a real 3.4s avatar clip (the live
avatar speech from the failed dogfood): produces 643KB
matted WebM in ~1s. Six endpoint tests still pass.

Successful retry of the failed composition via `retry_step`
on the matting step (no Runway re-spend on the already-
succeeded backdrop + speech). Final asset: 1.8MB / 10s
composite at `/data/_internal/composites/backdrop-c873d7757844b6af.mp4`,
total cost $0.75.

### `9a05865` — V16 design doc + CLAUDE.md updates

Doc-with-commit discipline satisfied for V16.

* `docs/design/VIDEO_COMPOSITION_V1.md` slice table: V16 row
  added after V15.4 with shipped commit refs.
* `VIDEO_COMPOSITION_V1.md` change log: detailed V16 entry
  covering all three pieces, the SESSION 179 dogfood trigger,
  the worker-stale + ffmpeg-muxer calibration events, and
  updated registry counts (14 primitives, 124 media-engine
  routes).
* `VIDEO_COMPOSITION_V1.md` new "Post-close additions"
  section codifies the V17+ template (narrow scope, one
  primitive + one knob + one endpoint, opt-in default).
* `CLAUDE.md` phase-4 V-arc bullet: registry bumped 13 → 14;
  media-engine route count 123 → 124; V16 post-close note.

## State at session-end

**Registry counts after V16:**

```
starters.py:    18 starter functions (unchanged since V15.4)
recipes.py:     18 RECIPES entries (unchanged since V15.4)
primitives:     14 (mock × 3 + real × 11 — added
                remove_avatar_background)
media-engine:   124 routes (123 → 124, +1 for
                /internal/clips/remove_background/)
```

**Tests** (regenerated counts):

```
Django:        843 (816 → 843, +27)
Media-engine:  143 (133 → 143, +10)
SPA vitest:     95 (unchanged)
```

**V-arc real-mode validation status:**

* ✓ `long_form_ad` — validated this session (SESSION 175
  + 179 work)
* ✓ `cinematic_visual` — validated this session
* ✓ `talking_head_with_backdrop` — validated this session
  (single-backdrop, multi-backdrop chain, AND
  remove_avatar_bg matting all real-mode green)
* ✓ `talking_head` — validated earlier (SESSION 158 first
  real-mode marketing video)
* **14 recipes remain unvalidated.** SESSION 180 priority.

**Running processes at session-close (operator's box):**

```
Django runserver:  pid 14769 (auto-reloads on .py changes)
Media-engine:      pid 65244 (uvicorn --reload, auto-reloads
                   on .py changes)
Celery worker:     pid 18279 (restarted SESSION 179 after V16
                   primitive registry change — does NOT
                   auto-reload; restart needed for any future
                   primitives / tasks / signals)
```

**Operator-visible UI state**: V8 backdrop recipe form now
includes a "Remove avatar background (slower)" checkbox below
"Use workspace knowledge." Default off — flip it for any
recipe where the white frame matters.

## Next session priorities — SESSION 180

Continuing the V-arc real-mode dogfood. 14 recipes remain
unvalidated:

* **Polish family** — `talking_head_polished`, `reels_format`
* **Layout family** — `pip_layout`, `cohost_layout`,
  `broll_splice`, `music_bed_pass`
* **Voice family** — `voice_design`, `multi_lang_dub`
* **Style family** — `style_remix_pass`
* **Storyboard family** — `storyboard_ad`, `storyboard_voiced`
* **Dialogue family** — `dialogue_scene`
* **Recut family** — `recut_teaser`
* **Backdrop bonus** — `backdrop_layout` (the standalone
  starter, distinct from V8's full talking_head_with_backdrop
  flow)

Pattern that worked SESSION 179: one short script + simple
prompts → fire from SPA → AI tails logs + DB via Monitor →
fix surfaced bugs inline → re-fire with `retry_step` where
possible to avoid double-spend.

Expected class of bugs (priors from SESSION 179 four-for-
four):
* Model selection drift between mock-mode default and real-
  mode endpoint expectations
* Resolver / URL-shape bugs in cross-step input passing
* ffmpeg muxer / codec issues with intermediate formats
* Runway API contract drift surfaced only by real requests
