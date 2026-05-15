---
title: "Session 144 — V14 + V15 buildout + workspace fabric arc"
date: 2026-05-14
status: complete
session: 144
previous_handoff: ./SESSION_143_VIDEO_COMPOSITION_BUILDOUT.md
---

# Session 144 — V14 + V-arc closure + workspace fabric arc F0-F10

## TL;DR

Three sequential arcs closed in one extended session:

1. **V14** — `dialogue_scene` + `audio_extract` (first slice
   exercising the new doc-with-commit discipline from
   SESSION 143's retro).
2. **V15.0-V15.4** — V-arc closure. SPA recipe gallery,
   metadata-driven forms across 18 starter recipes, all 18
   live, legacy `MakeVideoRoute` CTAs retired. The
   architectural payoff is in the change log: V15.3
   shipped six recipes with a one-line constant change
   because V15.0-V15.2 invested in the metadata-driven
   form renderer + asset_picker.
3. **F0-F10** — workspace fabric arc, scope-locked +
   shipped in the same session. Three SPA islands
   (Spokespeople, Knowledge, Recipes) collapsed into one
   workspace experience without adding any persistence.

The session ran from V14 (last V-arc work) → V15.0-V15.4
(V-arc close) → F0 scope lock → F1-F9 → F10 closure.
Backend test count: 339 → 438 (+99). SPA: zero new
models added across the fabric arc — every cross-section
surface is a read-only view of existing data.

## Commit log (by arc)

### V14 (1 slice + back-fill)

| Commit | What it shipped |
|---|---|
| `6f61e4b` | `dialogue_scene` starter + `audio_extract` primitive — first paired-doc commit |
| `38a5730` | Commit-ref back-fill (`(commit TBD)` → `6f61e4b`) |

### V15.0-V15.4 (V-arc closure, 5 slices)

| Commit | Slice | What it shipped |
|---|---|---|
| `1781cb1` | **V15.0** | Recipe registry (17 entries) + REST surface (`/api/recipes/`, `/api/compositions/`) |
| `e50d768` | (back-fill) | V15.0 commit ref |
| `74a70d7` | **V15.1** | SPA gallery shell + 3 live recipes + composition status page |
| `71bc05b` | (back-fill) | V15.1 commit ref |
| `c9a5d8c` | **V15.2** | Layout family forms (7 recipes) + `GET /api/assets/` + asset_picker |
| `3a79304` | (back-fill) | V15.2 commit ref |
| `8530a08` | **V15.3** | Voice / style / long-form / storyboard / recut forms (6 recipes) |
| `4d2a0f5` | (back-fill) | V15.3 commit ref |
| `68ab5d2` | **V15.4** | Dialogue form + storyboard_voiced bonus + legacy CTA retirement (V-ARC CLOSE) |
| `970ded7` | (back-fill) | V15.4 commit ref |

V-arc closed with **18 starter recipes / 13 step primitives /
123 media-engine routes / 393 backend tests**. See
`docs/design/VIDEO_COMPOSITION_V1.md` §"V-arc closure" for
the full summary.

### F0-F10 (workspace fabric arc, 10 slices)

| Commit | Slice | What it shipped |
|---|---|---|
| `825e0b9` | **F0** | Scope lock (9 contract rules, F0-F10 breakdown) |
| `3f9c057` | **F1** | Per-spokesperson recipe entry via URL hint |
| `a4744ab` | (back-fill) | F1 commit ref |
| `bcc8914` | **F2** | Persistent nav rail (Dashboard / Spokespeople / Knowledge / Recipes) |
| `3f6be1c` | (back-fill) | F2 commit ref |
| `59e5fdc` | **F3** | Workspace overview dashboard (activity feed + knowledge corpus + spokesperson badges + squarer cards) |
| `2c82d20` | (back-fill) | F3 commit ref |
| `0122f26` | **F4** | Knowledge preview + brief-mode helper on recipe forms (operator-prompted scope expansion) |
| `50523a3` | (hook fix) | Hoist `useDebounced` + `useKnowledgePreview` above early returns |
| `882baa4` | (back-fill) | F4 commit ref |
| `f50ba2b` | **F5** | Asset lineage panels (Derived from / Used by) |
| `4ba65df` | (back-fill) | F5 commit ref |
| `7980de7` | **F6** | Knowledge citations on composition status (no new endpoint) |
| `9a90c83` | (back-fill) | F6 commit ref |
| `0b6be9d` | **F7** | Knowledge doc → compositions reverse panel |
| `5ee86e0` | (back-fill) | F7 commit ref |
| `d23bc8c` | **F8** | Onboarding tour banner (split from K10 seed) |
| `274c60f` | (back-fill) | F8 commit ref |
| `73e011d` | **F9** | Delete legacy single-form SPA route |
| `6925a88` | (back-fill) | F9 commit ref |

F10 closure docs + this handoff: latest commit.

## What shipped (concrete)

### V14 — dialogue + audio_extract

* `dialogue_scene(workspace, primary_spokesperson, lines,
  ...)` starter — N speech turns + 1 concat, single-line
  optimization, per-line spokesperson via the V3
  primitive's existing `spokesperson_avatar_id` knob.
* `AudioExtractPrimitive` — CLIP → AUDIO via ffmpeg `-vn`
  through new `/internal/audio/extract/` media-engine
  route. Supports mp3 / aac / wav.
* Unblocks `storyboard_voiced` (shipped V15.4 as bonus).

### V15.0-V15.4 — SPA recipe gallery + V-arc closure

* `apps/compositions/recipes.py` — 18-recipe metadata
  registry. Each entry: kind, display_name, family,
  description, fields list (7 field types).
* `/api/recipes/` + `/api/compositions/` + `/api/assets/`
  REST surface.
* SPA: `/recipes` gallery + `/recipes/:kind` form +
  `/compositions/:id` status page. Metadata-driven form
  renderer covers all 18 recipes including
  `dialogue_scene`'s dynamic line list.
* `storyboard_voiced` bonus recipe (V14 audio_extract
  unblocked it) — 10-step pipeline: 3 images + 3 clips +
  concat + speech + audio_extract + mix_audio.
* Spokesperson detail "Make a video" CTA flipped to
  `/recipes`; legacy `MakeVideoRoute` deleted in F9.

### F0-F10 — workspace fabric arc

* **F0** — `docs/design/WORKSPACE_FABRIC_V1.md` scope
  lock. 9 contract rules. Zero new persistence.
* **F1** — `/recipes?spokesperson=<id>` hint propagation;
  spokesperson detail CTA carries it through.
* **F2** — Persistent nav rail
  (`web/src/components/nav-rail.tsx`). Vertical at >=md,
  horizontal tabs at sm. Four sections.
* **F3** — Workspace overview dashboard. New
  `GET /api/workspace/overview/` cross-cut endpoint.
  Activity feed + knowledge corpus tile + spokesperson
  card badges. SpokespersonCard rebalanced to aspect-[4/3]
  per operator squareness feedback.
* **F4** — Knowledge preview panel on recipe forms +
  brief-mode helper. Operator-prompted scope expansion
  added the brief-mode explainer because the SPA was
  hiding K6's already-shipped LLM script synthesis.
  Surfaces preview via new
  `POST /api/knowledge/preview/` endpoint.
* **F5** — Asset lineage panels on
  `/compositions/:id` — "Derived from" + "Used by"
  shapes via `GET /api/compositions/<id>/lineage/`.
* **F6** — Knowledge citations on `/compositions/:id`.
  No new endpoint — `CompositionSerializer` resolves
  `knowledge_chunk_ids` to a doc-level
  `knowledge_docs_used` field via a new sanctioned
  `resolve_chunk_ids_to_docs` helper in
  `retrieval.py` (K0 rule 2 stays intact).
* **F7** — Reverse panel on
  `/workspace/knowledge/:id`. New
  `GET /api/knowledge/<id>/compositions/` (scope-lock
  said "SPA-only" but the inverse query needed a real
  endpoint — F0 rule 1 still honored, just an honesty
  correction noted in the design lock change log).
* **F8** — Onboarding tour banner on `/dashboard`. State
  derived from workspace data (not stored progress).
  Three steps; dismissal persists via localStorage.
  Split from K10 seed corpus per F0 rule 9.
* **F8.1 — K10 seed corpus** — queued, awaiting
  operator-authored markdown in
  `docs/seeds/character_os/*.md`.
* **F9** — Deleted `web/src/routes/spokespeople/render.tsx`.
  V6 backend shim + `/api/videos/` endpoint stay
  intact. -373 lines / +31 lines net.
* **F10** — This handoff + the closure summary in the
  fabric design lock.

### Backend test progression across the session

| Milestone | Tests |
|---|---|
| Start (SESSION 143 handoff) | 339 |
| V14 close | 358 |
| V15.0 close | 382 |
| V15.2 close | 387 |
| V15.3 close | 391 |
| V15.4 close (V-arc close) | 393 |
| F3 close | 406 |
| F4 close | 416 |
| F5 close | 426 |
| F6 close | 431 |
| F7 close | 438 |
| F9 close (F-arc close) | 438 (F8 + F9 SPA-only) |

**99 new backend tests** across the session. **0 SPA unit
tests added** beyond playwright specs (per project
convention — e2e covers SPA flow, backend pytest covers
contracts).

## Calibration moments worth carrying

### 1. The hook-order regression caught at F4

F4's preview + debounce hooks landed below the recipe
form's early-return branches, which made React's hook
order diverge between renders. The console error fired
on first paint. Fix: hoist hooks above all returns and
let the `enabled` flag on `useQuery` gate the actual
network call.

**Carry-forward**: every new hook in a route component
goes above all conditional returns. The `enabled` flag
is the gate, not control flow.

### 2. The operator's "brief mode" insight at F4

Mid-F4 scoping, operator asked "are we using the LLM
to write the script? Can I just say 'Create a 60-sec
ad about X'?" The answer: yes, K6 already does that —
but the SPA was labelling the field "Script — what the
avatar will say," which hid the capability.

F4 expanded from preview-only to also include a
brief-mode helper. Without the operator's question,
F4 would have shipped a useful but smaller surface.

**Carry-forward**: ask the operator what they think a
field does, not what the model thinks. Mismatches
between intent + implementation hide in plain sight.

### 3. The F7 scope-lock optimism

F0 called F7 "SPA-only" thinking the reverse query
could be done client-side. In reality the SPA can't
intersect `Composition.knowledge_chunk_ids` JSON
across all workspace compositions efficiently —
needed a backend endpoint with the chunk-id filter.
F0 rule 1 still held (no new models), but the doc was
optimistic.

**Carry-forward**: scope locks that say "SPA-only"
should be re-checked when the slice actually starts.
The intent is "no new persistence"; the literal
phrasing is more restrictive than the contract rule.

### 4. The F8 scope split

F8 in the original lock conflated the tour UI with
the K10 seed corpus. Per F0 rule 9 (one journey per
slice) these are two journeys, and the seed corpus
is operator-authored content. Splitting kept F8
shippable in one session.

**Carry-forward**: F0 rule 9 is the right granularity.
Split before building if a slice has two distinct
journeys.

### 5. Operator-flagged K7 YouTube ingest bug

Mid-fabric arc the operator noticed K7 ingestion
reports YouTube URLs as "processed" but captures
nothing — trafilatura sees the SPA shell, not the
content. Memory saved at
`project_youtube_ingest_silent_failure.md`. Two-layer
fix queued: detect-reject silent-failure shape +
per-host extractors (starting with youtube-transcript-api).

**Carry-forward**: ingest success isn't a passed
content check. Bugs that look like "feature gap" are
sometimes real failures masked by lenient success
shape.

## Project memories saved this session

* `project_workspace_fabric_merge.md` — operator's
  mid-V15.2 product-seam observation that motivated
  the fabric arc.
* `project_youtube_ingest_silent_failure.md` — K7
  ingest false-success on JS-rendered pages.

## What's next (SESSION 145)

Three viable next arcs, all unblocked:

### Option A — K8-K10 conversation pipeline

* **K8** — `ConversationMessage` + `ConversationEmbedding`
  models + `retrieve_for_thread()`. Schema slice;
  mirrors K2.
* **K9** — Conversation REST + SPA. POST messages,
  thread view, spokesperson detail "Conversations" tab.
* **K10** — Now subsumed by F8.1. Awaits
  operator-authored corpus.

This is the "ConversationThread shell finally gets a
body" arc. Heaviest single-arc work in the queue but
the most user-facing capability remaining.

### Option B — R1+ realtime avatar

* **R1** — `RealtimeSession` + `RealtimeToolInvocation`
  schema. Schema-only mirror of V1.
* **R2** — media-engine `/internal/realtime_sessions/`
  + provider abstraction.
* **R3-R10** — broker, knowledge bridge, transcript
  persistence, memory, tools, SPA, cost governance.

This is the live two-way WebRTC arc. R0 scope-locked
SESSION 142.

### Option C — K7.x YouTube ingest fix

Small slice. Two-layer fix: detect-reject silent
trafilatura failures + add a per-host YouTube
transcript extractor. Memory at
`project_youtube_ingest_silent_failure.md` has the
investigation starting points.

### Option D — F8.1 K10 seed corpus

Blocked until operator authors curated markdown in
`docs/seeds/character_os/*.md`. Once those land, F8.1
wires migration + signal + Celery task + tests —
small slice on the AI side.

### Recommendation

If the operator wants the platform to feel "complete"
next, **K8-K9** unlocks the conversation arc which is
the only top-level capability the SPA doesn't expose
today. If they want to unlock new product surface,
**R1** opens realtime which is qualitatively different
from anything else.

K7.x and F8.1 are smaller follow-ups that don't need
to own a session.

## AI Notes

* Session 144 ran four roughly-equal-sized phases:
  V14 → V15.* → F0-F4 → F5-F9. Each phase had its own
  scope check-in with the operator. The pacing pattern
  (commit-then-check) worked.

* The new doc-with-commit discipline (codified end of
  SESSION 143) held cleanly across this session.
  Every slice's design-lock entry, slice-table mark,
  and back-fill commit landed inline. No catch-up
  pass needed.

* The fabric arc is the first arc that adds zero new
  persistence. The contract held — every fabric
  surface is a cross-cut of existing data. F0 rule 1
  is a good filter for future "lightweight" slices
  that don't deserve their own model.

* Two scope-lock corrections (F7 endpoint, F8 split)
  were caught early in their respective slices.
  Operator pushback on F4 was the highest-leverage
  scope expansion of the session. Future scope locks
  should keep the same "lockable, but correctable"
  shape — locked rules + a willingness to renegotiate
  specific slice scope mid-arc.

* Push approval pattern: operator authorized one push
  ("push everything to origin main") then implicitly
  allowed continuous push ("while I test"). Process
  call-out was made at F5; thereafter pushes continued
  per the implicit cadence. Going-forward: if the
  operator's testing pace matches the AI's slice pace,
  per-slice pushes are useful; otherwise pause and
  ask.
