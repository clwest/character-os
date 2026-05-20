---
title: "Session 196 — both SESSION 195 fix slices shipped"
date: 2026-05-19
status: complete
session: 196
previous_handoff: ./SESSION_195_V_ARC_CLOSURE_2_BUGS_FOUND.md
---

# Session 196 — both SESSION 195 fix slices shipped

## TL;DR

Both bugs found at SESSION 195 fixed in one session per the
quick-wins double pattern (matches SESSION 194's shape).

* **Slice 1 — mix_audio silent-base handling (media-engine).**
  `/internal/audio/mix/` ffprobe-detects whether the base has an
  audio stream; branches the filter_complex accordingly.
  Silent-base (storyboard_voiced shape) → overlay becomes the
  only audio output. Audio-base (music_bed_pass shape) → existing
  amix path unchanged. Pathological silent overlay → 422.
* **Slice 2 — combinator-primitive result_role param.**
  `concat_clips` reads `result_role` from step params with
  `BACKDROP` as default. `dialogue_scene` starter passes
  `result_role=composite_output` so its final lands as
  COMPOSITE_OUTPUT instead of polluting the A7 backdrop_clip_id
  picker.

Test totals: **Django 1006 → 1011 (+5)**, **media-engine 194 →
197 (+3)**, **SPA 134 unchanged**. `pnpm build` clean.

Spot-check verified slice 1 against the actual SESSION 195
inputs (silent storyboard concat + audio extract) — output
at `/data/_internal/mixes/caeb55bcc6338cb8.mp4` plays cleanly
with both video + audio streams.

No real-mode spend SESSION 196.

## Slice 1 — `/internal/audio/mix/` silent-base detection

### What landed

`media-engine/app/routers/internal.py` `post_internal_audio_mix`:

* Probes base via existing `_has_audio_stream` helper (added
  SESSION 182 for V17.2 extend chain — reused here).
* Probes overlay too — if overlay lacks audio, returns 422
  with operator-actionable message (pathological — overlay is
  the whole point of the endpoint).
* Branches `filter_complex` construction:
  * **base has audio** → existing `amix` filtergraph (V14
    `music_bed_pass` design preserved exactly).
  * **base is silent** → applies volume + fade processing to
    overlay, exposes as `[outa]`. ffmpeg `-map 0:v -map [outa]`
    works either way (the difference is only in the filter
    source).
* Cache key unchanged. The prior bug always 500'd before
  writing a cached output, so silent-base cache hits after the
  fix are by definition fresh.

### Tests added

`media-engine/tests/test_audio_mix_silent_base.py` — 3 tests:

* Silent base + audio overlay → output has video + audio streams.
* Audio base + audio overlay → existing amix path still works
  (regression guard).
* Silent overlay → 422 with explicit error mentioning
  "audio stream" and "overlay".

Fixtures synthesized via ffmpeg `lavfi` (silent video via
`color` source with `-an`; audio via `sine`; voiced video via
`color`+`anullsrc`). Mirrors `test_broll_composite.py`'s
pattern.

### Spot-check against SESSION 195 inputs

Operator's SESSION 195 partial `storyboard_voiced` composition
left the silent storyboard concat (`/data/_internal/concats/0f4b5d0d16d1ce24.mp4`)
+ Riggs narration audio_extract output
(`/data/_internal/audio_extracts/34858986fced83bf.mp3`) on disk.
Re-firing `/internal/audio/mix/` against those exact inputs
post-fix produced `caeb55bcc6338cb8.mp4`:

```
codec_name=h264|codec_type=video|duration=15.125000
codec_name=aac|codec_type=audio|duration=9.664000
```

Operator opened the file locally to spot-check; both streams
play correctly.

## Slice 2 — combinator-primitive `result_role`

### What landed

`apps/compositions/primitives/concat_clips.py`:

* Reads `result_role` from `step.params` with
  `AssetRole.BACKDROP.value` as backwards-compat default.
* Validates `result_role` is a valid `AssetRole` value
  (defense-in-depth — a typo in starter code raises
  `PrimitiveError` instead of silently writing an invalid role).
* Mock + real-mode branches both use the resolved role.
* `extra_source_spec` records `result_role` so the audit trail
  captures which role was stamped + why.

`apps/compositions/starters.py` `dialogue_scene`:

* Passes `result_role="composite_output"` on its concat step's
  params. The N-line dialogue's final deliverable now lands
  as `role=COMPOSITE_OUTPUT` instead of leaking into the A7
  role-filtered `backdrop_clip_id` picker.

### Scope decision — surgical fix only

SESSION 196 fixed only `concat_clips` + `dialogue_scene`. Three
other concat_clips usages have similar but lower-priority
taxonomy considerations:

| Starter | Concat semantic | Current role | Lower-priority because |
|---|---|---|---|
| `long_form_ad` | N chunked talking-head speeches | BACKDROP (wrong) | No operator-visible bug yet — extended talking-head content; not a backdrop. Should be TALKING_HEAD or COMPOSITE_OUTPUT. |
| `storyboard_ad` | 3 cinematic visual clips | BACKDROP | Defensible — operator may legitimately want to re-use a previous ad's visuals as a backdrop for new avatar speech. Leave as-is until a bug appears. |
| `storyboard_voiced` step 6 | 3 silent visual clips (intermediate) | BACKDROP ✓ | Intermediate that feeds the mix_audio composite. BACKDROP semantically correct — the silent storyboard IS a backdrop for the narration overlay. |

Queued as **follow-up taxonomy questions** for whenever
they surface as operator-visible. Not blocking anything now.

`composite_video` + `mix_audio` audited as part of this work:

* `composite_video` stamps `COMPOSITE_OUTPUT` — semantically
  correct across all V18 / V8 layout recipes (composite IS by
  definition a composite). No change.
* `mix_audio` stamps `COMPOSITE_OUTPUT` — correct for
  music_bed_pass + storyboard_voiced (mix is the final
  deliverable in both). No change.

### Tests added

5 new tests in `apps/compositions/tests/test_v14_dialogue.py`:

* `concat_clips` default role unchanged (BACKDROP — backwards-
  compat for V18 chain + storyboard_voiced step 6 + every
  pre-SESSION-196 caller).
* `concat_clips` honors `result_role` override.
* `concat_clips` raises `PrimitiveError` on invalid role typo.
* `dialogue_scene` starter passes `result_role=composite_output`
  on its concat step.
* End-to-end: dialogue_scene composition completes in mock-mode
  with `final_asset.role == "composite_output"`. Negative case
  confirmed — the final does NOT surface in a `role=backdrop`
  filter query (the A7 picker semantics).

## Tests at session close

| Suite | Count | Delta |
|---|---|---|
| Django | **1011** | +5 (1006 → 1011) |
| - compositions | **580** | +5 (575 → 580) |
| **Media-engine** | **197** | **+3 (194 → 197)** |
| SPA vitest | 134 | unchanged |

Both fix slices verified. `pnpm build` clean. No real-mode
spend.

## Calibration moments worth carrying

No new TRUST_CALIBRATION entries. SESSION 195 already
documented the underlying findings; SESSION 196 just shipped
the fixes. The "quick-wins double" pattern (used SESSION 194
for unrelated calibrations, now SESSION 196 for paired fixes)
continues to work — two ½-session slices bundled cleanly into
one session.

## Operational notes for SESSION 197

* **V-arc status: 17 of 18 recipes validated.**
  `storyboard_voiced` remains pending real-mode validation.
  The blocking bug (mix_audio silent-base) is now fixed; the
  recipe is unblocked. **One real-mode fire of
  `storyboard_voiced` would close the V-arc to 100%.** Cost
  ~$1.92 (3 Stability + 3 Runway visuals + 1 avatar speech)
  + ~$0 for the now-working ffmpeg steps. ETA 3-8 min.
* **All services likely still running** from SESSION 193+195
  background spawns (Django, SPA, Celery worker, media-engine).
  If `ps aux | grep celery` returns empty, restart the Celery
  worker before any composition fires (SESSION 193 hard rule).
* **`long_form_ad` + `storyboard_ad` taxonomy follow-up
  queued** as low-priority. Each is a 1-line starter change
  + a test. Bundle if operator wants the next quick-wins
  pass.
* **Spot-checked silent-base output file** is at
  `/Users/donkeyking/development/character-os/media-engine/data/_internal/mixes/caeb55bcc6338cb8.mp4`.
  Operator can keep or `rm` — not persisted as an Asset row
  (ad-hoc endpoint call, not a full composition run).
