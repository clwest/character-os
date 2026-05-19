---
title: "Session 184 — polish + V18 backdrop library + Q-v17-3 surfaced + Asset Library scope proposal"
date: 2026-05-19
status: complete
session: 184
previous_handoff: ./SESSION_183_V17_5_V8_OPT_IN_EXTEND.md
---

# Session 184 — polish + V18 + Q-v17-3 + Asset Library

## TL;DR

Three slices planned (#1 polish, #2 V18 backdrop library,
#3 V17.3 keyframes). Slices 1 + 2 shipped + real-mode
validated. Slice 3 surfaced a Q-v17-1-shape API
mismatch at the slice-open live-doc check and got
**DEFERRED** with the trade-off matrix documented. The
deferral pivot triggered an operator-driven scope-lock
proposal for a new arc — **Asset Library** — to address
the structural categorization gap that became visible
during the V18 dogfood (workspace had 119 CLIPs with no
way to tell backdrops from talking-heads in the recipe
asset_picker).

Six feature commits + one design doc + V17 proposal
update + this handoff. Real-mode spend this session:
**~$2.50** (smoke comparison + V18 dogfood).

---

## What shipped

### Slice 1 — polish (`7045270`)

Two surgical fixes from the SESSION 183 "Sunset 2"
trailing-silent-backdrop finding:

* **`generate_avatar_speech` duration_ms fallback.**
  Runway's `/v1/avatar_videos` poll doesn't surface
  `duration_seconds`; the media-engine forwards `None`
  (`internal.py:760`). When the primitive sees `None`,
  it now estimates from script length (11 chars/sec,
  5000ms floor) and stamps
  `extra_source_spec.duration_estimated=True` for audit.
  **Real-mode validated** in the V18 dogfood — the
  picked-clip composition's step 0 output Asset shows
  `duration_estimated: True` with an 8818ms estimate.
* **`composite_video` null-duration guard.** The
  primitive now refuses inputs with `duration_ms=None`
  before dispatching to the media-engine. Symmetric
  mock + real-path check. Error message names the
  upstream primitive class so the operator gets an
  actionable hint instead of a downstream symptom.

**Tests:** Django 904 (compositions 473, +4: 2
avatar_speech fallback + 2 composite null-duration).

### Slice 2 — V18 pre-recorded backdrop library (`b935acd`)

V8's third backdrop path. When the operator picks an
existing workspace CLIP as the backdrop, both the V8
concat chain AND the V17.5 extend chain are skipped —
the picked Asset wires straight into the composite as
the background slot.

* **Recipe** (`talking_head_with_backdrop`) — new
  optional `asset_picker` field `backdrop_clip_id`
  (`AssetType.CLIP`) plus
  `param_map={backdrop_clip_id: backdrop_clip}`.
  `backdrop_prompt` flipped to `required=False`; XOR
  enforcement (exactly one of prompt or clip) lives in
  the starter, not the schema. Server-driven schema
  means no SPA TS changes were needed — V15.2-V15.3
  asset_picker renderer already covers the UI.
* **Starter** — new `backdrop_clip: Asset | None = None`
  kwarg. Defensive validation (workspace match, CLIP
  type, `duration_ms` non-null) runs BEFORE Composition
  rows are created. When set, short-circuits past the
  concat / extend dispatch and builds:
  ```
  step 0: generate_avatar_speech
  step 1 (optional, V16): remove_avatar_background
  step N: composite_video, background = Asset(asset_id), foreground = step N-1
  ```
* **Precedence** — when both `backdrop_prompt` and
  `backdrop_clip` are supplied, `backdrop_clip` wins
  (the operator's explicit pick is the intent).
* No schema migration — `CompositionStep.inputs`
  already accepts the `{slot, asset_id}` shape used by
  pip/cohost/broll starters.

**Tests:** Django 915 (compositions 484, +11: V18
picked-clip happy path, V18 + V16 matte composition,
prompt-vs-clip precedence, extend-flag suppressed by
picked clip, end-to-end mock-mode runtime, XOR
rejection, non-CLIP rejection, null-duration rejection,
cross-workspace rejection, concat-path backwards-compat
regression, recipe-form metadata shape).

### Slice 3 — V17.3 keyframes: surfaced, deferred

The third planned slice opened with a slice-open
live-doc check against Runway's auto-generated Python
SDK
(`runwayml/types/image_to_video_create_params.py`). The
V17 proposal's claim of "keyframes on `gen4_turbo`"
turned out to be wrong:

* **No `keyframes` array exists.** The conditioning
  shape is `promptImage: str | Iterable[{position,
  uri}]` with `position ∈ {"first", "last"}`.
* **`gen4_turbo` only accepts `position: "first"`.**
  The V17.3 motivating use case (Hook + Payoff
  keyframes on `gen4_turbo`) is not implementable as
  written.
* Models that DO support both first+last in the
  Runway API: `gen3a_turbo` (ratio cliff to 768:1280
  / 1280:768) and `veo3.1_fast` / `veo3.1` (Google
  Veo brokered through Runway; supports 1280:720;
  4/6/8s clips; per-call cost unknown).

Two pivot options were surfaced to the operator
(stay on Runway accessible models per the 40K credit
constraint):

* **A — `veo3.1_fast`** — modern, supports 1280:720,
  Veo via Vertex AI brokered through Runway.
* **B — `gen3a_turbo`** — stays in Runway native;
  ratio cliff.

Operator picked **dogfood both** before deciding.

### Smoke command + dogfood (`c10e311`, `2daef87`)

* **`shell/apps/compositions/management/commands/smoke_keyframes.py`** —
  one-off Django management command that fires the
  same Hook + Payoff keyframe pair through both
  models so the operator can eyeball the comparison
  before V17.3 design lock. Direct httpx calls, no
  media-engine, no DB writes (later backfilled —
  see below).
* **Extension** (`2daef87`) — `--hook-asset-id` /
  `--payoff-asset-id` flags. Workspace Asset
  lookup + base64-encode local PNG → inline
  `data:image/png;base64,...` URI in the
  `promptImage.uri` slot (mirrors media-engine's
  SESSION 181 `5cc0954` `maybe_to_data_uri` pattern
  for gen4_turbo).
* **Smoke result (real-mode, ~$1.50-$3 spend, both
  succeeded):**
  - `veo3.1_fast` @ 1280:720 / 6s — ~40-50s render
    time, accepted 1.75MB inline data URI body.
  - `gen3a_turbo` @ 1280:768 / 5s — ~6-9s render
    time (5-7× faster), accepted same body.
  - **Both models accept `data:` URIs** — removes
    that risk from any future V17.3 design.
  - **gen3a_turbo identity drift was severe** on
    human-portrait keyframes — operator observed
    "two different randomly AI generated people"
    across the 5s clip, the exact drift V17.3 was
    supposed to fix.

### V18 real-mode dogfood (composition `b2188dcf` "Riggs-pre-background")

Picked the gen3a_turbo smoke output (`89a1ce5f`) as
`backdrop_clip` to validate V18 end-to-end. Composition
completed; Riggs (top-right tile) sat over the gen3a_turbo
"founder-drifting" backdrop. Three findings landed:

1. **Slice 1 fix #1 confirmed in real-mode** — step 0
   output Asset has `duration_estimated: True`,
   `duration_ms: 8818` (estimated from script length).
   The fallback fired as designed; without it, V18's
   composite would have failed slice 1's null-duration
   guard.
2. **V18 picked-clip path works** — 2 steps emitted,
   correct asset_id-shaped background input, composite
   produced final asset.
3. **NEW V18 finding (queue for next polish slice):**
   composite trimmed to the SHORTER input (5s
   backdrop), cutting Riggs's 9s speech off
   mid-sentence. Opposite shape of the SESSION 183
   Sunset 2 finding. V18 needs a starter-time
   warning when `backdrop_clip.duration_ms <
   estimated_speech_duration`.

### Smoke asset backfill + worker restart

* Backfilled both smoke outputs as workspace CLIP
  Assets (`c21fdeec` veo3.1_fast, `89a1ce5f`
  gen3a_turbo). Source_spec carries the audit trail
  (model, task_id, hook/payoff asset ids, prompt,
  session). Operator-visible in the V18 backdrop_clip
  asset_picker.
* Celery worker discovered to be stopped — composition
  sat in `status=draft` / step 0 `pending` for 8.5
  minutes before AI noticed. Restarted via background
  bash. Worker boot picked up today's slice 1 + slice
  2 code changes cleanly (the SESSION 179 calibration
  "worker doesn't auto-reload" applies — cold start
  was the right shape).

---

## Q-v17-3 / V17.3 deferral

V17.3 marked **DEFERRED** in
`VIDEO_COMPOSITION_V17_PROPOSAL.md` with Q-v17-6
documenting the API mismatch + the smoke trade-off
matrix. **Re-open criteria:**

* Runway adds first+last keyframe support to
  `gen4_turbo` or `gen4.5` (monitor SDK regen), OR
* Operator decides to adopt `veo3.1_fast` as a primary
  model for a new "cinematic shorts" arc — would need
  its own scope-lock separate from V-arc.

Until either trigger fires, the subject-identity drift
problem (SESSION 183 Underwater fish / Poker people)
remains an open architectural gap. Workarounds: shorter
clips (drift accumulates over time), seed propagation
across extends (cosmetic only — seed is determinism,
not continuity), or accept the drift on subject-rich
backdrops and use V18 picked-clips for high-stakes
renders.

**Live-doc-check discipline: 2-for-2 hit rate.** Q-v17-1
(SESSION 182) and Q-v17-3 (SESSION 184) both surfaced
API claim mismatches at slice-open that would have
caused multi-session rewrites. Codifies the rule from
SESSION 182's slice-open checklist: "live-doc check the
API surface the slice depends on" is non-optional for
third-party-wrapping slices.

---

## Asset Library scope proposal

New arc proposed: `docs/design/ASSET_LIBRARY_V1.md`
(`status: proposed`). Triggered by the V18 dogfood
realization that the workspace's 119 CLIPs + 9 IMAGE +
others have no role-level filtering — operator picks a
backdrop_clip from a flat list of EVERY clip, not a
filtered list of "scenes."

* **9-role closed enum** (`TALKING_HEAD` / `BACKDROP` /
  `COMPOSITE_OUTPUT` / `POLISH_OUTPUT` /
  `REFERENCE_IMAGE` / `B_ROLL` / `TRANSCRIPT` /
  `AUDIO_TRACK` / `RAW_UPLOAD`) stamped at
  primitive-emit time.
* **9 contract rules** (carry V1's 9 unchanged).
* **8 slices A0-A8** (~5-6 sessions): role enum →
  backfill → primitive stamping → storage-health helper
  → browse REST → SPA list → SPA detail → asset_picker
  role filter → F-arc lineage cross-link.
* **6 open questions** Q-a-1 through Q-a-6.
* **Out of scope v1:** asset upload UI (separate
  queued arc), asset deletion / archival, free-form
  tags, Avatar/Voice/Portrait as first-class Assets.

**Status: proposed; pending operator review next
session.**

---

## Calibration moments worth carrying

Six entries for `docs/TRUST_CALIBRATION.md`:

1. **Live-doc-check discipline is now 2-for-2 on
   V17.** Both Q-v17-1 (SESSION 182, `/v1/video_to_video`
   model constraint) and Q-v17-6 (SESSION 184,
   keyframes API shape) would have been multi-session
   rewrites if the slice had opened straight into
   code. The discipline rule: third-party-wrapping
   slices MUST live-doc-check the API surface before
   writing code. No exceptions.
2. **V18 picked-clip + duration mismatch is a real UX
   issue.** When backdrop_clip is shorter than the
   estimated speech duration, composite trims the
   speech — operator-visible as cut-off mid-sentence.
   Add a starter-time warning in the next V18 polish.
   Pattern: any time a recipe consumes a duration-
   bearing input, the recipe should validate against
   the speech/script estimate at starter-time.
3. **Asset taxonomy gap is structural.** 119 CLIPs in
   one workspace with no role-level filtering = the
   asset_picker becomes a guessing game. Triggered the
   Asset Library scope proposal. Pattern: when a
   metadata field categorizes by production method but
   the operator filters by intended use, the
   categorization is wrong shape.
4. **Smoke commands without --save-assets produce
   orphans.** The `smoke_keyframes` command was
   designed "no DB writes" for minimum-footprint; in
   practice the operator wanted to see the smoke
   outputs in the UI. Manual backfill worked but
   future smokes should default to creating CLIP
   Asset rows (with a `--no-save-assets` opt-out).
5. **Celery worker stop-state is silent.** A
   composition was queued via `execute_composition.delay()`
   but sat in draft for 8.5 minutes because no worker
   was consuming. The runtime gave no signal. Pattern:
   the SPA / admin should surface "queued but no
   worker available" as an operator-visible state, or
   the health-monitor should treat zero workers as a
   critical alert. Today's behaviour: nothing.
6. **Re-using smoke outputs as backdrops is a
   testing-shape mismatch.** The gen3a_turbo smoke
   output was a person-interpolation, not a scene.
   Using it as V18's backdrop_clip wired
   keyframe-drift into V18's output. The "two random
   people" finding wasn't a V18 bug; it was the
   operator picking unsuitable material. Asset role
   filtering (Asset Library A7) is the structural
   fix; meanwhile the lesson is "pick backdrops with
   intent."

---

## Final state at session close

| Surface | Status |
|---|---|
| Slice 1 (polish — duration fallback + null guard) | DONE + REAL-MODE VALIDATED |
| Slice 2 (V18 backdrop_clip on V8) | DONE + REAL-MODE VALIDATED |
| Slice 3 (V17.3 keyframes) | DEFERRED — Q-v17-6 documented |
| `smoke_keyframes` command + extension | DONE + REAL-MODE VALIDATED |
| Asset Library scope proposal | DRAFTED — pending operator review |

**Tests:** Django **915** (compositions **484**).
Media-engine **194** (unchanged). SPA vitest **95**
(unchanged). All gates clean: `pnpm build`, `pnpm
test`, `python -m pytest`.

**Real-mode spend this session:** ~$2.50 (smoke
comparison ~$1.50-$3 + V18 dogfood ~$0.50 avatar
speech).

**Cast roster unchanged.** Riggs still the
most-validated avatar. The "Riggs as random person"
concern operator raised mid-session resolved: the
portrait URL renders Riggs the Donkey correctly; the
"two random people" were the gen3a_turbo smoke
backdrop's keyframe interpolation drift, not the
spokesperson overlay.

**Commits (in order):**

* `7045270` fix(polish): avatar_speech duration_ms
  fallback + composite null-duration guard
* `b935acd` feat(V18): pre-recorded backdrop library
  — backdrop_clip on talking_head_with_backdrop
* `c10e311` chore(V17.3): smoke_keyframes management
  command — Q-v17-3 model comparison
* `2daef87` chore(V17.3): smoke_keyframes accepts
  asset-id keyframes + data: URIs
* (handoff + design doc commit pending session close)

---

## FIRST THING (SESSION 185)

**Operator review of Asset Library v1 scope.**

Path A — lock the arc:

1. Read `docs/design/ASSET_LIBRARY_V1.md` end-to-end.
2. Resolve or defer Q-a-1 through Q-a-6 (taxonomy
   choice, backfill strategy, storage-health caching,
   detail-view shape, picker filter mechanism,
   Avatar/Voice/Portrait modeling).
3. Lock — flip `status: proposed` → `status: locked`,
   merge contract rules into V1 as rules 14-22.
4. Open slice A0 (Asset.role migration).

Path B — pivot:

* Different taxonomy approach (free-form tags? hybrid?).
* Asset upload UI first (it's a queued SESSION 181
  gap that intersects).
* Cast rebuild first (fresh Riggs/Sasha/Donny avatars
  via `gen4_image`) — narrower dogfood task, doesn't
  require the new arc.

Path C — defer entirely:

* Close out the V-arc's two unvalidated recipes
  (`storyboard_voiced`, `dialogue_scene`) since V17
  is now deferred.
* Or progress F8.1 (K10 seed corpus, queued).
* Or pick up Asset upload UI (queued SESSION 181).

Recommended sequence (AI's pick, operator's call):
**Path A** — the Asset Library gap is the most-recent
operator-visible friction, and the design doc is
already drafted. A0 + A1 ship cleanly inside one
session (½ session each).

Alternative if you want a low-cost win: **V18 polish
slice** — add the starter-time duration-mismatch
warning + maybe filter the backdrop_clip picker to
duration-≥-speech-estimate candidates. ~½ session,
addresses the surfaced UX gap from today.
