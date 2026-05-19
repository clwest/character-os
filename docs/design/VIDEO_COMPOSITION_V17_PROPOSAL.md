---
title: "V17 — Runway Extend Video + Keyframes integration"
status: locked
generated: 2026-05-18 (SESSION 181)
locked: 2026-05-18 (SESSION 182)
parent_doc: "VIDEO_COMPOSITION_V1.md"
phase: 4
---

# V17 — Extend Video + Keyframes

> **Read first:** `VIDEO_COMPOSITION_V1.md` (the V-arc scope lock
> V17 extends), the V16 "Post-close additions" section (the
> template V17 follows for narrow-scope post-close slices), and
> the SESSION 181 dogfood handoffs (the operator-facing gaps
> this slice addresses).

---

## Purpose

The V-arc shipped 18 starter recipes through V15 and one
post-close polish (V16, `remove_avatar_background`). SESSION 181
dogfood surfaced **two missing Runway capabilities** that show
up as user-visible quality gaps across multiple recipes:

* **Visible motion seams** at clip boundaries in any
  concat-based recipe (V8 multi-backdrop chain — explicitly
  worked around by lengthening the chain; V13 storyboard_ad
  Hook→Action→Payoff transitions; V5 long_form_ad chunk
  boundaries when not masked by avatar speech).
* **Character-identity drift** across image-to-video chains
  (V13 storyboard_ad — same prompt + same seed still produces
  visibly different characters in the three shots).
* **Hard 10s ceiling** on any single cinematic clip (V4
  cinematic_visual — operator has no way to extend a
  generated clip beyond the per-render cap).

Runway's API has shipped two features that directly address
these gaps but the V-arc has never integrated them. V17
brings them in.

---

## The two capabilities

### Extend Video

**Implementation strategy (post Q-v17-1 resolution
SESSION 182):** last-frame-conditioned continuation via
`/v1/image_to_video` (`gen4_turbo`) + ffmpeg concat.

Runway's `/v1/video_to_video` only accepts `gen4_aleph`
(the model V11 style_remix uses); there is no
`gen4_turbo` / `gen4.5` extend mode at that endpoint
today. Q-v17-1 surfaced this against live Runway docs.

The functional outcome — a longer single clip that
visibly continues from where the source left off — is
delivered via:

1. Extract the source clip's last frame via ffmpeg
   (`-sseof -0.1 -vframes 1`).
2. POST `/v1/image_to_video` with `model=gen4_turbo`,
   `promptImage=<last frame data URI>`, and the
   operator-supplied continuation prompt.
3. Poll until SUCCEEDED, download the new 5-10s clip.
4. ffmpeg concat the source + new clip into one output.

The seam is near-pixel-perfect at the boundary (new
clip's frame 0 == source's last frame), and motion
continuity is reasonable because the model conditions
on the same frame the source ended with. Camera-
direction continuity is best-effort — not guaranteed
by the API, but the prompt can steer it.

**Concrete use:**

* V4 `cinematic_visual` — operator clicks "extend by 5s"
  after seeing the initial render. Endpoint takes the cached
  10s output, fires extend with the same prompt (or an
  operator-supplied continuation prompt), returns a 15s clip
  with continuous motion.
* V8 `talking_head_with_backdrop` — instead of laying down N
  separate 10s backdrops + concat'ing them (the SESSION 179
  multi-backdrop chain), lay down ONE 10s backdrop and use
  extend N times to grow it to the target duration. The
  SESSION 179 visible-seam workaround becomes obsolete.
* Any future recipe needing "background plate longer than
  one Runway call's max" — extend is the right primitive.

**Pricing (estimate, pending Q-v17-1):** Same per-second
rate as a fresh gen call appears to apply per Runway's
public pricing. Extending a 10s clip by 5s would be
~$0.50 (gen4_turbo) — same order as the current concat
chain. Confirm against live API docs at V17.0 slice-open.

### Keyframes (multi-image conditioning)

Runway's `/v1/image_to_video` accepts a `keyframes` array —
multiple reference images that condition the motion at
specific moments in the output timeline. First image
typically pins the start frame; last image pins the end
frame; middle entries (when supported) shape the trajectory.
The model interpolates motion between the pinned moments.

**Concrete use:**

* V13 `storyboard_ad` — instead of 3 separate Hook/Action/
  Payoff clips with character drift, render ONE shot with
  the Hook image as start keyframe + the Payoff image as
  end keyframe. The model interpolates the Action moment
  organically. Same character identity holds because the
  same character is in both pinned frames.
* Future: "match-cut" recipes where the operator wants the
  same composition at frame 0 and frame N (subject in same
  position, camera in same location) with motion happening
  between.
* Future: dialogue scenes where Spokesperson A's portrait
  pins the start and Spokesperson B's portrait pins the end,
  with the model rendering a natural cut between them.

**Pricing (estimate, pending V17.3 slice-open):** Same
per-second rate as standard image-to-video appears to
apply, with a slight per-keyframe surcharge per Runway's
public pricing. Confirm against live API docs at V17.3
slice-open.

---

## Contract rules (load-bearing)

These extend V1's nine contract rules. V17 must hold all
nine V1 rules unchanged. **At scope-lock the four V17 rules
below become V1 rules 10-13** (same merge pattern V16 used
for its post-close rules).

1. **The `extend_visual_clip` primitive emits one Asset
   per call.** Step receives one CLIP input + a
   continuation prompt; emits one CLIP output; the source
   asset stays unchanged. Composition runtime sees a
   normal single-step transform. Recipes MAY chain N
   extend calls (V17.5 does); each chained call remains
   one linear step.

2. **Keyframes are inputs to one step, not a DAG.** A
   multi-keyframe image-to-video render is ONE step that
   consumes multiple IMAGE assets in parallel via named
   slots (`start_keyframe`, `end_keyframe`). The
   composition step graph remains linear; V1 rule 5 (no
   DAG) carries through unchanged.

3. **Backwards-compat for V4 / V8 / V13.** Existing
   recipes keep their current behaviour. V17 adds new
   recipes / new optional kwargs; no existing recipe
   changes shape. The V16 template (opt-in default for
   any behaviour change) carries through.

4. **Cost surfaces before render fires.** Extend and
   multi-keyframe both have per-second + per-keyframe
   cost models; the estimators expose them so operators
   see total cost on the recipe form before clicking
   render. Same as V1 contract rule 7.

---

## In-scope clarifications

* **V11 style_remix interaction.** `extend_visual_clip`
  operates on any CLIP-typed asset, including style-
  remixed clips from V11. The cache key still includes
  source clip content hash (Q-v17-4 resolution below),
  so re-extending a freshly remixed source invalidates
  correctly.
* **V17.3 image sources.** Until the asset-upload UI
  arc lands, V17.3's `keyframe_shot` recipe operates on
  IMAGE assets already in the workspace (generated via
  V13 `generate_image` or seeded shell-side). Operator-
  uploaded keyframes are explicitly out-of-scope below.

---

## New / extended media-engine endpoints

* **`POST /internal/clips/extend/`** (new, **synchronous**)
  — takes `{source_clip_url, prompt, duration, ratio, seed?}`.
  Downloads source if remote; extracts last frame via
  ffmpeg; fires `/v1/image_to_video` (gen4_turbo) with the
  last frame + continuation prompt; polls; downloads new
  clip; ffmpeg-concats source + new into final output.
  Returns `{output_url, duration_seconds,
  source_duration_seconds, new_segment_duration_seconds,
  size_bytes, task_id, mock_mode}`. **Mirrors V11's
  `/clips/style_remix/` synchronous contract**, not V4's
  async `/clips/visual/` shape — the long-running ffmpeg +
  Runway round-trip + ffmpeg-concat doesn't fit the
  fire-and-return pattern, and a single sync response
  gives the operator one terminal state per call (same
  reasoning that drove style_remix sync). Q-v17-1
  resolution drove this contract change from the original
  async proposal.
* **`POST /internal/clips/visual/`** (extended) — accepts
  an optional `keyframes: [str]` parameter alongside the
  existing `prompt_image`. When `keyframes` has 2+ entries,
  fire the multi-keyframe code path; otherwise fall back
  to the existing single-image-to-video path. **One
  endpoint, one contract shape.** Backwards-compat by
  construction: a single-element `keyframes` array is
  equivalent to the current `prompt_image` behaviour.

Both endpoints route `prompt_image` / `keyframes` URLs
through `maybe_to_data_uri` (the SESSION 181 V13 path fix
that landed in commit `5cc0954`) so V13 `generate_image`
outputs feed cleanly through.

---

## New / extended primitives

* `extend_visual_clip` — new primitive. CLIP input → CLIP
  output. Same shape as `generate_visual_clip` from the
  runtime's perspective, but calls the new extend endpoint.
* `generate_visual_clip` — extend the existing primitive to
  optionally accept multiple `reference_image` inputs (when
  more than one is present, fire the multi-keyframe code
  path). Backwards-compat: a single reference_image input
  uses the current image-to-video path.

---

## Slice breakdown (proposed)

Same pattern as V15 / V16 — narrow scope, opt-in defaults,
real-mode validation per slice.

| Slice | What ships | Estimated effort | Status |
|---|---|---|---|
| **V17.0** | Media-engine `/internal/clips/extend/` endpoint + tests. No Django changes. | ½ session | **✓ SHIPPED SESSION 182** (`933d4e7`) |
| **V17.1** | Django `extend_visual_clip` primitive + cost estimator + tests. No recipe yet. | ½ session | **✓ SHIPPED SESSION 182** |
| **V17.2** | New `cinematic_visual_extended` recipe (V4 + extend chain) — operator picks target duration > 10s; starter lays down 1 generate_visual_clip + N extend_visual_clip steps. Recipe form + tests + real-mode dogfood. | 1 session | **✓ SHIPPED SESSION 182** (mock + unit tests; real-mode dogfood pending) |
| **V17.3** | Extend `/internal/clips/visual/` to accept `keyframes: [str]` + multi-keyframe support on `generate_visual_clip`. Plus a new `keyframe_shot` recipe (start + end image, single 5-10s shot). Uses existing IMAGE assets until asset-upload UI lands. | 1 session | pending |
| **V17.4** | V13 `storyboard_ad` opt-in flag (`use_keyframes: bool = False`) — when on, swaps the 3-shot chain for a single keyframed shot. Default off; V13 backward-compat holds. | ½ session | pending |
| **V17.5** | V8 `talking_head_with_backdrop` opt-in flag (`use_extend_for_backdrop: bool = False`) — when on, uses extend chain instead of multi-backdrop concat. Resolves the SESSION 179 motion-seam workaround. | ½ session | pending |

Roughly **4 sessions** of work end-to-end. Could compress
to 2-3 if V17.4 / V17.5 ship together as one operator-
facing slice.

**Dependency tree:**

```
V17.0 (extend endpoint)
  └─ V17.1 (extend primitive + cost)
       ├─ V17.2 (cinematic_visual_extended recipe)
       └─ V17.5 (V8 opt-in extend chain)

V17.3 (keyframes on existing endpoint + primitive)
  └─ V17.4 (V13 opt-in keyframes)
```

The keyframes track (V17.3 + V17.4) is independent of
the extend track (V17.0-V17.2 + V17.5) and **MAY
parallelize** if a session has spare capacity (e.g.
extend awaiting Runway API confirmation under Q-v17-1).
Default is linear — validate extend before opening the
second front.

---

## Out of scope

* **DAG composition** (V1 contract rule 5 stands).
* **Real-time WebRTC keyframes** (different code path —
  realtime arc owns avatar/conversation features).
* **Cross-recipe keyframe chaining** (a keyframed shot
  whose start frame is the previous shot's end frame —
  interesting but adds N-recipe coupling we don't need
  yet).
* **Operator-uploaded keyframe images via SPA** (deferred
  to a future "asset upload UI" arc — same gap that
  motivated the SESSION 181 placeholder uploads for
  music_bed_pass and multi_lang_dub).
* **Voice continuity across extended clips** (the extend
  endpoint operates on video only; audio is not regenerated.
  The V8 use case keeps the avatar speech track separate
  from the extended backdrop — no change needed.)

---

## Open questions

Five questions surfaced at proposal time. Three are
resolved inline below; two remain open for slice-open
verification against live Runway APIs.

* **Q-v17-1 (RESOLVED SESSION 182 at V17.0 slice-open):**
  Runway's `/v1/video_to_video` only accepts `gen4_aleph`
  (no `gen4_turbo` or `gen4.5` extend mode at that
  endpoint today). Pivot: V17.0 implements extend as
  last-frame extraction + `/v1/image_to_video` (gen4_turbo)
  + ffmpeg concat. The endpoint becomes **synchronous**
  (mirrors V11 style_remix), not the originally proposed
  async shape. See §"Extend Video" and §"New / extended
  media-engine endpoints" for the updated contracts.
* **Q-v17-2 (RESOLVED at lock):** v1 ships start + end
  keyframes only. Intermediate keyframes deferred until
  Runway documents the support; named slots in the
  primitive are `start_keyframe` + `end_keyframe`, no
  `mid_keyframe_N` surface in v1.
* **Q-v17-3 (RESOLVED at lock):** No `template_kind`
  split. Per rule 2, keyframes are inputs to the
  existing image-to-video step, not a new shape. The
  recipe form differentiates single-ref (simple pose
  anchor) from multi-ref (keyframe interpolation) at
  the recipe layer, not the primitive.
* **Q-v17-4 (RESOLVED at lock):** Cache key MUST
  include the source clip's content hash. This is
  correctness, not preference — re-extending a
  freshly-modified source with a stale cache would
  silently return wrong output.
* **Q-v17-5 (open — resolve at V17.1 / V17.5
  slice-open):** Cost-estimator behaviour when the
  source clip's duration isn't known at recipe-time
  (V8 opt-in case — operator sets target duration;
  avatar speech duration unknown until chain length
  math runs). Likely resolution: estimate from target
  duration, refine post-render.

---

## Verification gates per slice

Every slice ships with the SESSION 181 dogfood pattern:

1. Pure-function unit tests for any new helpers
   (e.g., extend cost estimator, multi-keyframe param
   validator).
2. Endpoint integration tests using lavfi-generated tiny
   fixtures (same shape as
   `tests/test_intro_outro_endpoint.py` etc.).
3. **Real-mode dogfood** before claiming the slice is
   shipped. Pixel-based or duration-based assertions that
   the output actually carries the new capability, not
   just that the endpoint returns 200.

---

## Why this is post-close polish, not arc reopen

V17 follows the V16 template established in `VIDEO_COMPOSITION_V1.md`
§"Post-close additions": narrow scope, focused on one
capability gap, opt-in defaults so existing recipes stay
unchanged, real-mode validated before handoff. The V-arc's
v1 catalogue (18 recipes) closed at V15.4; V16 / V17 / V18+
are addressed extensions of that catalogue, not a reopen of
the original scope.

The decision to add a post-close slice is driven by **operator-
visible gaps surfaced in real-mode dogfood**, not by
"completing the framework" — same circuit-breaker the
SESSION 178 B6 calibration entry codified. SESSION 181's
storyboard_ad output (character drift across 3 shots) is
the concrete trigger; V8's multi-backdrop seam workaround
is the secondary motivation.
