---
title: "V17 Proposal — Runway Extend Video + Keyframes integration"
status: proposed (not yet scope-locked)
generated: 2026-05-18 (SESSION 181)
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

Runway's `/v1/video_to_video` extend mode (gen4_turbo /
gen4.5). Takes an existing rendered clip + a continuation
prompt; generates new content that flows from the source's
tail frame as one coherent motion. Result: a longer single
clip with no concat seam.

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

**Pricing:** Same per-second rate as a fresh gen call.
Extending a 10s clip by 5s = ~$0.50 (gen4_turbo). No worse
than the current chain.

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

**Pricing:** Same per-second rate as standard image-to-video
(slight surcharge per additional keyframe per Runway's
public pricing — needs verification at implementation time).

---

## Contract rules (load-bearing)

These extend V1's nine contract rules. V17 must hold all
nine V1 rules unchanged.

1. **Extend Video produces a single Asset, not a chain.**
   The extend output IS the new asset; the source asset
   stays unchanged. Step receives one CLIP input + a
   continuation prompt; emits one CLIP output. Composition
   runtime sees a normal single-step transform, not a chain.

2. **Keyframes are inputs, not steps.** A multi-keyframe
   image-to-video render is ONE step that consumes multiple
   IMAGE assets via named slots (`start_keyframe`,
   `end_keyframe`, optional `mid_keyframe_N`). Not a
   composition of N steps.

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

5. **No DAG.** V1 rule 5 stands — V17's keyframes
   primitive consumes multiple inputs in parallel but the
   composition step graph remains linear.

---

## New media-engine endpoints

* `POST /internal/clips/extend/` — takes
  `{source_clip_url, prompt, duration_s, seed?}`, fires
  Runway extend, polls task, returns standard
  `InternalVisualClipCreateResponse` shape. Mirrors the
  existing `/internal/clips/visual/` contract.
* (Possibly) extend the existing `/internal/clips/visual/`
  to accept a `keyframes: [str]` parameter instead of
  (or in addition to) the single `prompt_image`. Cleaner
  than a separate endpoint — keyframes are an extension
  of the image-to-video flow, not a new shape.

Both endpoints route their `prompt_image` / `keyframes`
URLs through `maybe_to_data_uri` (the SESSION 181 V13 path
fix that landed in commit `5cc0954`) so V13 `generate_image`
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

| Slice | What ships | Estimated effort |
|---|---|---|
| **V17.0** | Media-engine `/internal/clips/extend/` endpoint + tests. No Django changes. | ½ session |
| **V17.1** | Django `extend_visual_clip` primitive + cost estimator + tests. No recipe yet. | ½ session |
| **V17.2** | New `cinematic_visual_extended` recipe (V4 + extend chain) — operator picks target duration > 10s; starter lays down 1 generate_visual_clip + N extend_visual_clip steps. Recipe form + tests + real-mode dogfood. | 1 session |
| **V17.3** | Multi-keyframe support on `generate_visual_clip` + media-engine `/internal/clips/visual/`. Plus a new `keyframe_shot` recipe (start + end image, single 5-10s shot). | 1 session |
| **V17.4** | V13 `storyboard_ad` opt-in flag (`use_keyframes: bool = False`) — when on, swaps the 3-shot chain for a single keyframed shot. Default off; V13 backward-compat holds. | ½ session |
| **V17.5** | V8 `talking_head_with_backdrop` opt-in flag (`use_extend_for_backdrop: bool = False`) — when on, uses extend chain instead of multi-backdrop concat. Resolves the SESSION 179 motion-seam workaround. | ½ session |

Roughly **4 sessions** of work end-to-end. Could compress
to 2-3 if V17.4 / V17.5 ship together as one operator-
facing slice.

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

## Open questions (resolve in implementation slices)

* **Q-v17-1:** Does Runway's extend endpoint accept the
  same `prompt` semantics as gen4_turbo, or does it require
  a continuation-specific prompt schema? Confirm against
  the live API docs at slice-open time.
* **Q-v17-2:** How many keyframes does gen4_turbo accept in
  one call? Two (start + end) is documented; intermediate
  keyframes may or may not be supported. v1 ships start +
  end only and defers mid-keyframes until Runway documents
  the support.
* **Q-v17-3:** Should the existing `generate_visual_clip`
  multi-reference path produce a different `template_kind`
  or stay the same? Argument for staying: composition runtime
  sees one primitive either way. Argument for splitting: the
  recipe form needs to differentiate (single ref = simple
  pose anchor; multi-ref = keyframe interpolation). Resolve
  in V17.3.
* **Q-v17-4:** Caching strategy for extend chains. Should
  the cache key include the SOURCE clip's hash (so re-extending
  the same source with the same prompt hits cache) or treat
  every extend as a fresh fire? Probably former; confirm.
* **Q-v17-5:** Cost-estimator behaviour when the source clip's
  duration isn't known at recipe-time (V8 opt-in case —
  operator sets target duration, but the avatar speech
  duration isn't known until V8 runs the chain length math).
  Likely resolution: cost estimate based on target duration,
  refined post-render.

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
