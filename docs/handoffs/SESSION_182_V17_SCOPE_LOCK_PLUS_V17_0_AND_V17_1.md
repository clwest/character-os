---
title: "Session 182 — V17 scope-lock + V17.0 (extend endpoint) + V17.1 (Django primitive)"
date: 2026-05-18
status: complete
session: 182
previous_handoff: ./SESSION_181_V_ARC_LAYOUT_VOICE_STORYBOARD_DOGFOOD.md
---

# Session 182 — V17 scope-lock + V17.0 + V17.1

## TL;DR

Two feature commits. V17 (extend video + keyframes) went from
SESSION 181's `status: proposed` draft to `status: locked` with
four contract rules merged into V1 as rules 10-13, and the first
two slices shipped:

* **V17.0** (`933d4e7`) — media-engine `POST /internal/clips/extend/`
  endpoint, 13 tests.
* **V17.1** (`cfc2854`) — Django `extend_visual_clip` primitive +
  cost estimator, 19 tests.

**Q-v17-1 surfaced + resolved mid-slice.** Live Runway API check
during V17.0 slice-open found that `/v1/video_to_video` only
accepts `gen4_aleph` (the V11 style-remix model). The V17
proposal's original framing (gen4_turbo/gen4.5 extend mode at
that endpoint) was wrong. Pivoted to **last-frame extraction +
`/v1/image_to_video` (gen4_turbo) + ffmpeg concat**, all on the
media-engine side — operator-facing capability unchanged, the
implementation strategy changed. Endpoint became synchronous
(mirrors V11 style_remix) instead of async (the original
proposal mirrored V4 visual_clip).

By session-end:

* V17 scope locked with **13 contract rules total** (V1's 9 + V17's 4
  merged as rules 10-13).
* `/internal/clips/extend/` endpoint live + tested (mock + 4 ffmpeg
  helpers + cache + validation).
* `extend_visual_clip` primitive registered + tested (mock +
  validation + real-mode dispatch via mocked client).
* V17 proposal slice table marks V17.0 + V17.1 ✓ SHIPPED.
* V17.2-V17.5 queued; **storyboard_voiced + dialogue_scene
  still deferred** until V17 lands enough for the keyframes
  track (V17.3-V17.4).

Tests this session:

```
Django:         871 total / 421 → 440 compositions (+19, all V17.1)
Media-engine:   177 → 190 (+13, all V17.0)
SPA vitest:      95 unchanged (no SPA surface this session)
```

Real-mode spend this session: **$0** — Q-v17-1 surfaced before
any Runway calls fired; subsequent work was scope + mock-mode
implementation + unit tests.

## What landed — by commit

### `933d4e7` — feat(V17.0): /internal/clips/extend/ endpoint + scope-lock

Combined commit that did three things in one drop:

1. **V17 scope-lock.** Frontmatter on
   `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md` flipped to
   `status: locked`; "locked: 2026-05-18 (SESSION 182)" added.
2. **Rules merge.** Four V17 rules appended to V1 as rules
   10-13:
   * 10 — `extend_visual_clip` primitive emits one Asset per
     call (recipes MAY chain N at the recipe layer)
   * 11 — keyframes are inputs to one step, not a DAG
   * 12 — backwards-compat for V4/V8/V13 under V17 (opt-in
     defaults)
   * 13 — cost surfaces before render fires (extend +
     keyframes share the same shape as V1 rule 7)
3. **V17.0 implementation.** New
   `POST /internal/clips/extend/` endpoint + four helpers
   (`_extract_last_frame` / `_extend_poll_task` /
   `_extend_download` / `_extend_concat`). Reuses
   `runway_create_task`, `runway_get_task`,
   `_download_concat_input`, `_probe_duration` from existing
   infra. Cached by `hash(source_clip_url + prompt + duration
   + ratio + seed)`.

13 new media-engine tests covering: pure-function last-frame
extraction (incl. end-color verification against `-sseof`
regression), mock-mode endpoint shape, cache-key variance
(prompt + source), validation errors (model policy + Pydantic
schema), ffmpeg concat (summed duration + mismatched-dim loud
failure), gen4_turbo model pin.

### `cfc2854` — feat(V17.1): extend_visual_clip Django primitive + cost estimator

The Django seam to V17.0's media-engine endpoint.

* `ExtendClipResult` dataclass + `MediaEngineClient.extend_clip()`
  method (360s timeout — covers download + ffmpeg + Runway 90s
  + ffmpeg concat with headroom).
* `ExtendVisualClipPrimitive` — one CLIP input + `{prompt,
  duration?, ratio?, seed?}` → one CLIP Asset whose
  `duration_ms` is source + new segment.
* Cost estimator: new-segment seconds × $0.05/sec, floor 5s.
  Charges ONLY the new segment — source isn't re-rendered.
* Registry entry `"extend_visual_clip"` in
  `apps/compositions/primitives/__init__.py`.
* `test_isolation.py` allowlist updated for the new test file.

19 new Django tests: registry + cost (5), mock-mode (3),
input validation (7), real-mode dispatch (3).

## Q-v17-1 — the surfaced finding worth carrying

The V17 proposal (SESSION 181) was written from skim of Runway's
public docs + UI behavior + prior experience. It assumed Runway's
extend video capability lived at `/v1/video_to_video` with a
`gen4_turbo` or `gen4.5` model. Live API check at slice-open
(WebFetch against `docs.dev.runwayml.com/guides/models/`) found:

* `gen4_turbo` → `/v1/image_to_video` only
* `gen4.5` → `/v1/image_to_video` only
* `gen4_aleph` → `/v1/video_to_video` (style remix; V11)

There is no extend mode at `video_to_video` today. Runway's own
product UI ships "extend video" — but it implements it
client-side by extracting the last frame + firing
`image_to_video` with that frame as the prompt image. The
external observation (user sees a longer continuous clip) is
the same; the API mechanism is different.

Three options surfaced to the operator (A — pivot to last-frame
extraction, B — try aleph as extend, C — defer V17). **A was
chosen**, doc + implementation pivoted, no Runway credits spent
on a wrong-shape API call.

This is the third recent calibration entry on "verify API
claims against live docs before locking scope". SESSION 175
KW + SESSION 181's gen4_image-min-dim drift were the previous
two. The pattern: **a confident API claim in a design doc is a
hypothesis, not a fact, until live-doc verified.**

## Calibration moments worth carrying

Three new entries appended to `docs/TRUST_CALIBRATION.md`:

1. **Pre-implementation pause when a finding shifts scope.**
   When Q-v17-1 surfaced (Runway API not what proposal said),
   I stopped before writing endpoint code, surfaced three
   options to the operator, waited for direction. The
   operator confirmed A explicitly. Right shape vs barging
   ahead with a guess. The cost of stopping for ~5 minutes
   of operator review was much smaller than committing
   wrong-shape code + having to rip it out.

2. **Sync vs async endpoint contract is a design-time
   decision.** V17.0 originally proposed mirroring `/clips/visual/`'s
   async fire-and-poll shape. The pivot to V11's synchronous
   shape was forced by: ffmpeg + Runway + ffmpeg is a
   long-running chain that doesn't fit async semantics (the
   caller would have to manage state across multiple polls
   against a non-existent task). Synchronous gives the
   operator one terminal state per call. **Mirror the
   nearest existing endpoint with the same architectural
   shape**, not the nearest endpoint in the same conceptual
   family.

3. **API docs from skim can mislead even when they read
   right.** The V17 proposal's "Runway's `/v1/video_to_video`
   extend mode (gen4_turbo / gen4.5)" line read confidently —
   it referenced the right endpoint family and plausible
   model names. The fact that those specific model+endpoint
   combinations don't exist in Runway's API surfaces only at
   live-doc check. **Treat API references in design docs as
   load-bearing only after live verification.** First slice-
   open against a new external API capability is the right
   moment to confirm.

## State at session-end

**Tests:**

```
Django:        871 total (843+ baseline + 28: 19 V17.1 + 9 other slice-unrelated growth between SESSIONS 181-182)
               of which 440 are compositions tests (421 → 440 = +19, all V17.1)
Media-engine:  190 (177 → 190 = +13, all V17.0)
SPA vitest:     95 unchanged
```

**Registry counts:**

```
starters.py:    18 starter functions (unchanged)
recipes.py:     18 RECIPES entries (unchanged)
primitives:     15 (mock × 3 + real × 12 — V17.1 added
                  extend_visual_clip)
media-engine:   136 routes (135 → 136, +1 = /internal/clips/extend/)
```

**V-arc real-mode validation status (unchanged from SESSION 181):**

16 of 18 recipes validated. Two deferred:
* **storyboard_voiced** — operator-deferred until V17.3-V17.4
  land (keyframes will improve V13-as-sub-recipe)
* **dialogue_scene** — operator-deferred until V17 closes

**V17 slice status:**

```
V17.0  ✓ SHIPPED SESSION 182 (933d4e7)
V17.1  ✓ SHIPPED SESSION 182 (cfc2854)
V17.2  pending — cinematic_visual_extended recipe (V4 chain)
V17.3  pending — keyframes on /clips/visual/ + keyframe_shot
V17.4  pending — V13 storyboard_ad use_keyframes opt-in
V17.5  pending — V8 talking_head_with_backdrop use_extend opt-in
```

**Workspace artifacts created this session:** none. All work was
mock-mode + unit tests; no Compositions / Assets / VOICE / AUDIO
rows persisted.

**Q-v17-x resolution table:**

```
Q-v17-1  RESOLVED SESSION 182 — gen4_turbo + image_to_video, sync shape
Q-v17-2  RESOLVED at lock — v1 start + end keyframes only
Q-v17-3  RESOLVED at lock — single endpoint, no template_kind split
Q-v17-4  RESOLVED at lock — cache key includes source clip hash
Q-v17-5  open — cost estimator with unknown source duration; resolve V17.5
```

## Next session priorities — SESSION 183

**Track A — V17.2 (cinematic_visual_extended recipe).** Most
operator-facing next slice. ~1 session. Recipe takes a target
duration > 10s, lays down 1 generate_visual_clip + N
extend_visual_clip steps (N = ceil((target - 10) / 5)). Recipe
form + tests + real-mode dogfood. Real-mode dogfood at this
slice is the first time V17.0's actual `/v1/image_to_video`
flow fires in anger — Q-v17-1's pivot lives or dies here.

**Track B — V17.3 in parallel.** Per the V17 doc's dependency
tree, V17.3 (keyframes on /clips/visual/) is independent of
the V17.0-V17.2 extend track. ~1 session. Could run alongside
V17.2 if the operator wants to open two fronts; default per
locked doc is linear.

**Track C — Defer V17 + work other queue items.** Still on the
table:
* F8.1 K10 seed corpus (blocked on operator-authored markdown)
* K7.x v3 YouTube oEmbed
* K6.4 v3 architectural fix
* Thruman stale spokesperson cleanup
* W12 legacy form retirement
* Asset upload UI (operator-flagged SESSION 181)

Recommendation: **A**. The extend track is the more important
operator-visible capability (V4 10s ceiling + V8 seam are real
production gaps). V17.2 also stress-tests V17.0 + V17.1 in
real mode — if Q-v17-1's pivot has hidden gaps, V17.2 dogfood
surfaces them. Defer V17.3-V17.5 until V17.2 closes cleanly.

**First action SESSION 183:** read this handoff + run `context-kit
orient` + open V17.2 by reading the V17 proposal's V17.2 row + the
existing `cinematic_visual` starter to understand the V4 shape
we're chaining from.
