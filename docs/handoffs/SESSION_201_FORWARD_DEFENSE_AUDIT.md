---
title: "Session 201 — forward-defense audit of ffmpeg silent-base assumptions"
date: 2026-05-19
status: complete
session: 201
previous_handoff: ./SESSION_200_STORYBOARD_EXTEND_CHAIN.md
---

# Session 201 — forward-defense audit (preempting the next silent-base bug)

## TL;DR

SESSION 200's calibration entries called out three already-shipped
silent-base bugs (mix_audio / extend_concat / intro_outro) and
recommended a forward-defense audit of the remaining ffmpeg
endpoints. This session executed that audit + fixed two latent
bugs before any real-mode hit.

Three ffmpeg paths were already safe (`composite_video` uses
`-map N:a?`, `add_captions` + `trim_clip` + `reformat_clip` use
`-c:a copy` which silently no-ops on missing audio,
`_extend_concat` already had the `_has_audio_stream` guard from
V17).

**Two paths were at risk and got fixed:**

* `_build_reencode_cmd` — unconditionally referenced `[N:a]`
  for every input. Reachable via `concat_clips(reencode=True)`.
  Long-form ad's `reencode_concat=True` knob has always been
  pointed at speech clips (audio present), so the silent-base
  shape was never exercised — but the contract was the same
  fragile shape as SESSION 196 / 200.
* `_aleph_split_into_chunks` — unconditional `-c:a aac` +
  `-map 0`. Reachable via `style_remix` on a source >5s.
  Today's caller (`talking_head_polished`) always has audio,
  so silent-source style_remix would have surfaced this.

Both fixes use the same `_has_audio_stream` helper as the
prior three fixes. Five callers of that helper now —
the pattern is robust.

Tests: **media-engine 204 → 209 (+5)**. Django + SPA
unchanged. No real-mode spend. No new bugs surfaced.

## Audit table

| Endpoint | Audio handling | Pre-audit risk | Post-audit |
|---|---|---|---|
| `composite_video` (pip/backdrop/cohost/broll) | `-map N:a?` optional mapping | None | ✓ unchanged |
| `add_captions` | `-c:a copy` silent → silent | None | ✓ unchanged |
| `trim_clip` | `-c copy` no filtergraph | None | ✓ unchanged |
| `reformat_clip` | `-c:a copy` silent → silent | None | ✓ unchanged |
| `_extend_concat` | `_has_audio_stream` guarded (V17) | None | ✓ unchanged |
| `_build_reencode_cmd` | unconditional `[N:a]aresample` + `concat=a=1` | **silent-base 500** | ✓ ffprobe-branched (Slice 1) |
| `_aleph_split_into_chunks` | unconditional `-c:a aac` + `-map 0` | **segmenter error** | ✓ ffprobe-branched (Slice 2) |

## What landed

### Slice 1 — `_build_reencode_cmd` silent-base branch

`media-engine/app/routers/internal.py`:

* Probe each input via `_has_audio_stream`.
* When ALL inputs have audio: existing behavior (preserve audio
  through the concat).
* When ANY input is silent: drop the audio chain entirely; emit
  `concat=...:a=0[outv]`; skip the `-c:a aac` codec args.

The "any silent → video-only" simplification mirrors
`_extend_concat`'s v1 contract — intentionally drops audio from
audio-carrying inputs in mixed-shape requests rather than
synthesizing silence per silent input. Callers needing audio
preserved must ensure uniform-audio inputs upstream.

Tests in new file `tests/test_concat_reencode_silent.py`:

* `test_concat_reencode_with_all_silent_inputs_emits_video_only`
* `test_concat_reencode_with_mixed_audio_silent_inputs_drops_audio`
* `test_concat_reencode_with_all_audio_inputs_preserves_audio` (regression guard)

### Slice 2 — `_aleph_split_into_chunks` audio-aware mapping

`media-engine/app/routers/internal.py`:

* ffprobe the source for an audio stream once upfront.
* When silent: drop `-c:a aac -b:a 128k`; switch `-map 0` to
  `-map 0:v` so the segmenter explicitly targets only video.
* When audio present: existing args.

Tests appended to `tests/test_aleph_chunk_split.py`:

* `test_split_silent_source_emits_video_only_chunks`
* `test_split_audio_source_preserves_audio_in_chunks` (regression guard)

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | 1039 | unchanged |
| - compositions | 608 | unchanged |
| Media-engine | **209** | +5 (204 → 209: +3 reencode silent +2 aleph silent) |
| SPA vitest | 134 | unchanged |

No real-mode spend.

## Calibration moments worth carrying

**One new TRUST_CALIBRATION entry (29 total)**:

* **Forward-defense audits surface latent bugs cheaply.** The
  SESSION 200 dogfood pattern ("real-mode finds bugs in EVERY
  recipe") generalizes: when one bug surfaces, audit every
  endpoint with the same shape. SESSION 201 found 2 latent
  bugs in 5 endpoints reviewed (40% hit rate) at zero real-mode
  spend. Same `_has_audio_stream` helper, same branching
  pattern; total cost ~30 minutes including tests. Worth
  repeating after the next dogfood discovery.

## What's still queued

V-arc UX + forward-defense audit complete. Backlog is now
genuinely arc-shaped — small-slice candidates are depleted.

### Real-mode validation candidates

* SESSIONS 198/199 outro flows on long_form_ad,
  cinematic_visual, cinematic_visual_extended, dialogue_scene
  still haven't been real-mode-fired with outros. $0.50–$1.50
  per fire depending on recipe.
* The SESSION 201 forward-defense paths are covered by tests
  — no real-mode dogfood needed (mock-then-pattern-spotted is
  the explicit calibration).

### Bigger backlog items (unchanged)

* **Asset upload UI** (1-2 sessions) — operator-content
  bottleneck.
* **W12 legacy form retirement** (1 session).
* **K6.4 v3 architectural fix** (1 session).
* **K7.x v3 YouTube oEmbed** (½ session).

### New-arc candidates (unchanged)

* **B-1 Transcript Miner** — top strategic; closest to shipped
  infra. 6-8 slices.
* **B-3 Personalized Video** — biggest revenue unlock. 10+ slices.
* **B-14 Multi-Platform Variants** — distribution stickiness. 5-6 slices.

### Recommended next direction

Forward-defense audit closes the SESSION 200 calibration loop.
The "what to do next" question now points squarely at the
strategic axes — a new arc, the Asset upload UI bottleneck, or
the deferred K6.4/W12/K7.x slices. Pick the arc with the
clearest customer story.
