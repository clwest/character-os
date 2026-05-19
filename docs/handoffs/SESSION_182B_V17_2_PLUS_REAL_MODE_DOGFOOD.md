---
title: "Session 182 (part 2) — V17.2 ship + first end-to-end V17 real-mode pass"
date: 2026-05-18
status: complete
session: 182
part: 2
previous_handoff: ./SESSION_182_V17_SCOPE_LOCK_PLUS_V17_0_AND_V17_1.md
---

# Session 182 (part 2) — V17.2 + real-mode dogfood

## TL;DR

Six commits since the SESSION 182 part-1 close
(`0a82bbb`). V17.2 (`cinematic_visual_extended` recipe)
shipped + real-mode validated end-to-end. **First operator-
visible V17 capability is live in the product.** Four
dogfood-surfaced bugs fixed inline.

* **`02f9f70` — feat(V17.2):** `cinematic_visual_extended`
  recipe chains 1 × `generate_visual_clip` (10s gen4.5
  text-to-video base) + N × `extend_visual_clip` steps. N =
  (target − 10) / 5. target ∈ {15, 20, 25, 30, 40, 50}.
  Recipe registered in V15 gallery; 18 new Django tests
  (chain math, step composition, validation, recipe
  registry).
* **`bfbbe55` — fix(V17.2):** target_duration choice values
  must be STRINGS per SPA Zod schema; backend coerces.
* **`1ce6788` — fix(V17.2):** opt
  `cinematic_visual_extended` into `LIVE_RECIPE_KINDS` so
  the card renders live (not "coming soon").
* **`01ea94d` — fix(recipes):** **latent bug across all
  recipes** — the form-renderer shows defaults but the
  submission path drops them when the operator never
  touches the field. V17.2's `target_duration` was the
  first required-AND-default field; all prior recipes had
  required-without-default OR optional-with-default,
  neither of which triggered the trap. Fix applies the
  default at submission-time symmetric with render-time.
* **`9fac2b3` — fix(V17.0):** ffmpeg concat exit 234 on
  silent-input case. Runway's `gen4_turbo` + `gen4.5`
  outputs are silent MP4s; the pre-fix filter requested
  `a=1` on the output from two silent inputs and exited.
  Fixed: probe both inputs with ffprobe, take a video-only
  filter branch when neither has audio. 4 new regression
  tests.
* **(this handoff doc commit)** — V17 proposal table
  updated to mark V17.2 SHIPPED + real-mode validated.
  Four TRUST_CALIBRATION entries appended for the dogfood
  findings. INVENTORY regen.

### The end-to-end real-mode pass

```
comp 4d3670dd-ae83-408e-95ba-cf8f2a3a5ca9 → completed
  step 0 generate_visual_clip → SUCCEEDED (10s Runway gen4.5)
  step 1 extend_visual_clip   → SUCCEEDED
    output: /data/_internal/extends/ac5d402a34935b5e.mp4
    duration: 15.08s (10.04 source + 5 new)
    size: 1,763,415 bytes
    runway task: e016bebc-c525-440d-b496-f223377bee37
cost_actual: $0.75 ($0.50 base + $0.25 extend)
```

Prompt: *"steam rising slowly from a ceramic coffee cup on
a sunlit windowsill, soft morning light, locked-off camera"*.
Operator visual eye-test on the output is what closes the
loop — the unit-test layer can verify "the chain produces a
playable 15s file with the summed duration" but only the
operator can verify "the seam visually flows."

**Q-v17-1 pivot validated end-to-end.** The last-frame
extraction + `/v1/image_to_video` + ffmpeg concat path
works as a real product feature, not just as code.

### Test totals at session-end (cumulative SESSION 182)

```
Django:        891 (compositions: 460; +20 from V17.2 +
                   +2 from coercion tests)
Media-engine:  194 (177 → 190 V17.0 → 194 silent-concat
                   regression tests)
SPA vitest:     95 unchanged (V17.2 SPA changes use
                   existing renderer)
```

Real-mode spend across both parts: **$0.75** (failed
attempt's step 0 succeeded but didn't bill since the
Runway task completed before the concat failure — only
the successful retry billed). Cheaper than the $1.50
worst-case ceiling I'd been forecasting.

### Four calibration moments worth carrying

Three are dogfood-specific (V17.2 SPA + V17.0 silent-input)
and one is a latent-bug-class (form-renderer). All four
appended to `docs/TRUST_CALIBRATION.md`:

1. **Recipe choice values must be strings per SPA Zod
   schema.** First load of `/recipes` 500'd on Zod parse
   when V17.2 shipped int choices. Add to slice-open
   checklist for any recipe with non-text choices.

2. **New recipes need three SPA touchpoints, not one.**
   Backend recipe entry + (a) string choice values + (b)
   `LIVE_RECIPE_KINDS` opt-in + (c) verify
   required-with-default fields submit. None visible from
   backend tests; all surface at SPA load.

3. **Form-renderer renders defaults but drops them on
   submission.** Latent bug class across the entire
   form-renderer; V17.2's required-with-default was the
   first to trigger it. Pattern to carry: default in
   render = default in submit, no exceptions.

4. **Unit test fixtures must mirror provider output
   shape.** V17.0's 13 unit tests used lavfi clips
   *with* audio; Runway outputs are silent; the concat
   case never exercised in unit tests until real-mode
   dogfood fired it. Spending 5 minutes downloading a
   real Runway output and stripping audio would have
   caught this before ship. Pattern to carry: fixtures
   shaped after a SAMPLE of the API's actual output,
   not the easiest construct.

## State at session-end (part 2)

**V17 slice status:**

```
V17.0  ✓ SHIPPED SESSION 182 part 1 (933d4e7) — endpoint
V17.1  ✓ SHIPPED SESSION 182 part 1 (cfc2854) — primitive
V17.2  ✓ SHIPPED + REAL-MODE VALIDATED SESSION 182 part 2
       (02f9f70 + 4 dogfood fix commits)
V17.3  pending — keyframes on /clips/visual/ + keyframe_shot recipe
V17.4  pending — V13 storyboard_ad use_keyframes opt-in
V17.5  pending — V8 talking_head_with_backdrop use_extend opt-in
```

**V-arc status (unchanged from SESSION 181):**

- 16 of 18 original V-arc recipes validated.
- 2 deferred (storyboard_voiced, dialogue_scene).
- V17.2 added a 19th recipe (`cinematic_visual_extended`)
  to the gallery — also validated this session.

**Registry counts:**

```
starters.py:    19 starter functions (18 → 19, +cinematic_visual_extended)
recipes.py:     19 RECIPES entries (18 → 19)
primitives:     15 (mock × 3 + real × 12 — unchanged since V17.1)
media-engine:   136 routes (unchanged; /clips/extend/ shipped part 1)
```

**Workspace artifacts created this session (part 2):**

* 2 `Composition` rows of kind `cinematic_visual_extended`:
  - `cd72ebd5...` — first attempt, status=`partial` (step 0
    succeeded, step 1 failed at concat). Useful as a
    forensic record of the silent-input bug.
  - `4d3670dd...` — retry, status=`completed`. First
    end-to-end V17 real-mode success.
* 2 CLIP Assets:
  - The Runway CDN URL for the base 10s clip
    (`d24c7ea7-6a49-4792-a443-35bb559607ae.mp4`).
  - The local merged 15s clip
    (`/data/_internal/extends/ac5d402a34935b5e.mp4`).

**Running processes at session-close (operator's box):**

```
Django runserver:   pid 32199 (auto-reloads on .py changes)
Media-engine:       pid 21694 (uvicorn --reload)
Celery worker:      pid <fresh from this session>
                    (restarted by AI at part-2 dogfood prep
                    to pick up V17.1 + V17.2 primitive +
                    recipe registrations)
```

## Q-v17-x resolution table (final after part 2)

```
Q-v17-1  RESOLVED SESSION 182 — gen4_turbo + image_to_video,
         sync shape. Real-mode validated SESSION 182 part 2.
Q-v17-2  RESOLVED at lock — v1 start + end keyframes only
Q-v17-3  RESOLVED at lock — single endpoint
Q-v17-4  RESOLVED at lock — cache key includes source clip hash
Q-v17-5  open — resolves at V17.5 slice-open (cost estimator
         with unknown source duration)
```

## Next session priorities — SESSION 183

Two natural tracks; operator picks. Both depend on
SESSION 182 part-2's validation that V17.0 + V17.1 work
end-to-end.

**Track A — V17.5 (talking_head_with_backdrop opt-in
extend).** Highest operator value of the remaining slices.
SESSION 179's multi-backdrop concat seam workaround
becomes obsolete when the backdrop is grown via extend
chain instead of N separate 10s renders. ~½ session.
Lower-risk since V17.0 + V17.1 are now validated; the
only new code is the V8 starter branch.

**Track B — V17.3 (keyframes track).** Independent of the
extend track per the dependency graph. ~1 session.
Operator-facing payoff is V17.4 (V13 storyboard_ad
keyframes) which addresses the character drift gap.
Higher-risk since we haven't real-mode tested
keyframes API behavior yet — likely surfaces its own
Q-v17-style finding.

**Recommendation: A.** V17.5 closes the SESSION 179 seam
workaround that's been carrying through real-mode renders
for ~3 sessions. Concrete operator-visible win. V17.3 +
V17.4 can come after.

**Alternative — defer V17 + work other queue items.** The
F8.1 K10 seed corpus + asset upload UI gap are both still
queued from SESSION 181.

## SESSION 183 stack-up notes

* **Celery worker** was restarted SESSION 182 part 2 to
  pick up the V17.1 + V17.2 primitive + recipe
  registrations. The new fresh worker pid will need
  restarting again if SESSION 183 touches
  `apps/compositions/primitives/` OR
  `apps/*/tasks.py`.
* The `cd72ebd5...` partial composition is harmless but
  visible in admin / lineage queries. Can be left as a
  forensic record of the silent-input bug, or deleted.
* The Q-v17-1 finding suggests a slice-open checklist
  item worth codifying:
    1. Live-doc check the API surface this slice depends on.
    2. (If a new recipe) verify the three SPA touchpoints
       (string choices, LIVE_RECIPE_KINDS, default-aware
       submission).
    3. (If wrapping a provider call) make sure unit
       fixtures match the provider's actual output shape.
