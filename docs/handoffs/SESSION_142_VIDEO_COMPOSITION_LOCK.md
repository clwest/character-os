---
title: "Session 142 — Cleanups, V0+V1 video composition, R0 realtime scope lock"
date: 2026-05-14
status: complete
session: 142
previous_handoff: ./SESSION_141_K4_DETAIL_AND_RENDER_AUDIT.md
---

# Session 142 — Cleanups + V0/V1 video composition + R0 realtime scope lock

## TL;DR

Five outcomes — the largest session since the K-arc scope
lock:

1. **Pre-K6.5 cleanups shipped (K4.2 + K6.2).** Soft-deleted
   knowledge documents now restore on re-ingest instead of
   blocking; missing portrait_path on render now fails fast
   with a clear operator message instead of an opaque
   media-engine 400. 3 new K-tests. Committed as `4321fdb`.

2. **V0 — Video composition scope lock shipped.** Mapped the
   runway-hackathon pipeline (15+ output kinds, 5 Runway
   endpoints, ~2,000 lines of dormant composition logic in
   `media-engine/app/services/*`). Discovered the *real*
   blocker isn't one wrong endpoint; it's that every endpoint
   is a *leaf* (input → finished MP4), so combinations like
   "talking-head + backdrop + music bed + captions" can't be
   expressed. Scope-locked `docs/design/VIDEO_COMPOSITION_V1.md`
   (851 lines, 9 contract rules, 16 step primitives, 16 slices
   V0-V15). K6.5 absorbed into V3 — same Runway endpoint
   target (`/v1/avatar_videos`), landing inside the new
   Asset+Composition shape so it's reusable. Committed as
   `ab3610c` alongside CLAUDE.md + start-here updates.

3. **V1 — Asset + Composition + CompositionStep schema
   shipped.** New `apps.compositions` Django app. Three
   models matching `VIDEO_COMPOSITION_V1.md` §"Data model"
   exactly. Cross-workspace validation enforced two ways
   (pre_save signal + `clean()`) — defense in depth. Admin
   registration with inline steps. 13 V-tests pass
   (12 model tests + 1 repo-level isolation test mirroring
   K2's pattern). 115 backend tests total. Existing `Video`
   model is untouched per the scope lock; V5 introduces the
   backwards-compat shim. Committed as `68561fd`.

4. **R0 — Realtime avatar scope lock shipped.** Operator
   pulled realtime WebRTC into Phase 4 mid-session. Scope-
   locked `docs/design/REALTIME_AVATAR_V1.md` (818 lines, 10
   contract rules, R0-R10 slice breakdown). Two-table data
   model (`RealtimeSession` + `RealtimeToolInvocation`)
   shares V1's `Asset` shape for transcript persistence —
   the two arcs don't fork the data model. Provider
   abstraction registry pattern locked. Knowledge layer
   one-way bridge (Runway documents composed from
   `KnowledgeDocument` rows via K2's `retrieve_for_spokesperson`
   surface). Tool catalog narrowed from hackathon's 9 to 6,
   each workspace-scoped with operator-approval thresholds
   for expensive tools. To commit alongside this handoff.

5. **Three parallel arcs locked in Phase 4.** Knowledge
   (K1-K10, 7 shipped), Video composition (V0-V15, V1
   shipped), Realtime avatar (R0-R10, R0 shipped). Each has
   its own scope-lock doc + slice plan. K6.5 dissolved
   completely; the "additional video kinds" queue items
   dissolved completely; realtime added to Phase 4 rather
   than punted to v2. The shape that supports all three:
   one shared `Asset` table, one shared workspace anchor
   pattern, one shared cross-workspace-rejection discipline.

## What shipped (code)

### K4.2 — Dedup-restore bug fix

`shell/apps/embeddings/ingestion.py:75-122`

`_persist()` now detects soft-deleted matches (`is_active=False`)
and restores them — flip active, reset status to PENDING,
clear `error_message`, update title (if a new one supplied) —
then returns `deduped=False` so the serializer re-fires
`embed_document.delay()`. `embed_document` is already
idempotent (wipes stale chunks before re-running) so the
re-embed is safe.

Two new tests in `apps/embeddings/tests/test_ingestion.py`:

- `test_ingest_text_restores_soft_deleted_row` — verifies the
  restore flow end-to-end.
- `test_ingest_text_restore_preserves_title_when_new_is_blank`
  — guards the URL-ingest path that passes title="" when no
  title was supplied.

### K6.2 — Pre-render portrait validation

`shell/apps/videos/views.py:70-101`

`VideoViewSet.perform_create` now fails fast on missing
`portrait_path` alongside the existing `runway_avatar_id`
check. Real-mode media-engine returned an opaque 400
("prompt_image is required") for the missing-portrait case;
now shell sets `status=FAILED` with a clear operator-facing
message that points at the wizard / `seed_cast`.

Avatar-missing error message also tightened to mention
`seed_cast` as a second route to fixing it.

One new test:
`test_video_create_with_no_portrait_fails_fast_and_skips_synthesis`.

### Test counts after cleanups

- Embeddings tests: 90 (88 prior + 2 K4.2)
- Videos tests: 12 (11 prior + 1 K6.2)
- **Combined K-tests: 102** (all pass)
- Plus 46 prompts pytest = **148 backend tests**
- E2e specs unchanged at 38 (cleanups had no SPA changes)

Commit: `4321fdb` — `fix: K4.2 dedup-restore + K6.2 portrait validation`.

## What shipped (docs)

### `docs/design/VIDEO_COMPOSITION_V1.md` (NEW — 851 lines)

The architecture scope lock for the video composition arc.
Same shape as `KNOWLEDGE_LAYER.md`. Section breakdown:

- **Purpose** — what's broken (terminal-endpoint problem) and
  what this fixes (Asset + Composition + Step primitives).
- **9 contract rules** — workspace anchors on every Asset +
  Composition, cross-workspace reference rejection, linear
  ordering, partial-failure resume, cost-before-fire, knowledge
  one-way, mock-mode at composition level.
- **Framing corrections** — "additional video kinds" dissolves,
  K6.5 becomes V3, MoviePy rejected.
- **Data model** — three Django models (Asset / Composition /
  CompositionStep) with full field definitions.
- **Step primitives** — 16 primitives, table maps each to its
  Runway endpoint + hackathon service file source.
- **Composition execution** — Celery task, state machine,
  partial-failure resume, cost estimation.
- **Starter compositions** — 17 ports of hackathon kinds + 7
  new compositions the terminal-endpoint model couldn't
  express.
- **Media-engine `/internal/*` extensions** — ~12 per-primitive
  routes sequenced through the slice plan.
- **Slice breakdown V0-V15** — 16 slices, ~12-18 sessions.
- **Out of scope** — DAG, marketplace, custom primitives,
  DaVinci, per-frame editing, AI-cuts-without-approval.
- **Open questions** — 9 questions resolved per-slice.
- **Verification tests** — 4 must-pass tests before V6 closes.

Cross-workspace reference rejection, knowledge-layer one-way
integration, and cost transparency are the three architectural
guarantees worth re-reading before any V-slice implementation.

### `docs/design/REALTIME_AVATAR_V1.md` (NEW — 818 lines)

The architecture scope lock for the realtime avatar arc.
Same shape as VIDEO_COMPOSITION_V1.md + KNOWLEDGE_LAYER.md.
Section breakdown:

- **Purpose** — why realtime is in launch scope (operators
  + customers talking to spokespeople), three constraints
  hackathon didn't carry (multi-tenant, knowledge
  integration, asset-shape persistence).
- **10 contract rules** — workspace anchors, Runway API key
  never reaches frontend, transcripts persist as Assets,
  knowledge one-way, workspace-scoped tools, cost ceilings
  enforced pre-create, provider-abstraction registry,
  mock-mode at session-level, K8/K9 thread continuity.
- **Framing corrections** — realtime is launch product,
  realtime is composable, WebRTC is the easy part.
- **Data model** — `RealtimeSession` +
  `RealtimeToolInvocation`, both sharing V1's `Asset` for
  transcript persistence.
- **Provider abstraction** — single named adapter pattern;
  adding Synthesia/HeyGen is a single-file change.
- **Knowledge integration (R4 — the bridge)** — Runway
  documents composed from `retrieve_for_spokesperson` top-30
  chunks + business_brief + transcript history; 40k char cap.
- **Tools surface** — 6-tool v1 catalog (down from
  hackathon's 9), operator-approval threshold for expensive
  tools.
- **Cost governance** — three layers (per-workspace minutes
  budget + per-session length cap + per-tool approval).
- **SPA integration** — `@runwayml/avatars-react`
  `<AvatarCall>` SDK handles WebRTC; cost forecasting UI;
  tool-approval modal.
- **Slice breakdown R0-R10** — 11 slices, ~10-14 sessions.
- **Out of scope** — operator-defined tools, multi-spokesperson
  live conversations, customer-facing sessions, session
  recording, autonomous tool calling.
- **9 open questions** — resolved per-slice.
- **6 verification tests** — must pass before R8 closes.

### `shell/apps/compositions/` (NEW — 1,368 lines across 11 files)

The V1 schema implementation. Files:

- `__init__.py`, `apps.py` (AppConfig with signals wired in
  `ready()`).
- `models.py` — Asset (5 type choices), Composition (6
  status choices, 2 anchors workspace+spokesperson), CompositionStep
  (5 status choices, UniqueConstraint on position).
- `signals.py` — pre_save validator rejecting cross-workspace
  asset references in `inputs` + `output_asset`.
- `admin.py` — all three models registered with inline
  CompositionStep on Composition pages.
- `migrations/0001_initial.py` — auto-generated.
- `tests/test_models.py` — 12 model tests covering all 9
  contract rules touched by V1.
- `tests/test_isolation.py` — 1 repo-level grep test
  mirroring `apps/embeddings/tests/test_retrieval_privacy.py`.

### `shell/character_os/settings.py`

`apps.compositions` added to `INSTALLED_APPS`.

### `00-START-NEXT-SESSION.md` (overwritten)

- Phase 4 reframed as three parallel arcs (Knowledge K1-K10,
  Video V0-V15, Realtime R0-R10).
- Slice table updated: K6.5 row dissolved into V3; V0 + V1
  + R0 marked DONE; V2 + R1 added as candidate next slices.
  K4.2 + K6.2 marked DONE.
- "Next: K6.5" section replaced with "Next: V2 (recommended)
  OR R1" plus reasoning for the recommendation (V2 unlocks
  V3-V15; sequencing two consecutive infra slices is wasteful).

### `CLAUDE.md` (amended)

- "Read-first" now has 8 entries (added 6: KNOWLEDGE_LAYER.md,
  7: VIDEO_COMPOSITION_V1.md, 8: REALTIME_AVATAR_V1.md).
- Phase 4 status table updated to reflect three parallel
  arcs, V1 shipped, R0 shipped.

## The architecture reframe — what changed about the problem

**SESSION 141 audit said:** K6 routes to the wrong Runway
endpoint; rewire `kind=spokesperson_ad` to hit
`/v1/avatar_videos` instead of `gen4_turbo`. ~one session of work.

**SESSION 142 mapping said:** runway-hackathon shipped 15+
output kinds and 5 Runway endpoints; every one is a terminal
operation (input → finished MP4). The reason "talking-head +
backdrop + music + captions" can't be built is not that the
primitives are missing — it's that the data model has no
concept of one render being an input to the next. K6.5 as
"swap an endpoint" papers over that. K6.5 as "land the first
primitive in the new shape" is the same delivery with better
ground.

**Two framings the start-here used that this session
supersedes:**

- "Additional video kinds — cinematic / dialogue / long_ad /
  lesson" is no longer a queue of new enum values. Under
  V0-V15, no kinds get added — only step primitives. Every
  existing "kind" becomes a starter composition. The queue
  items dissolve.

- "K6.5 — talking-head render rewire" is no longer a single
  rewire. Same Runway endpoint target, but lands as **V3**
  in the new slice sequence, behind a single-step
  composition.

## The realtime reframe — what got pulled in mid-session

Operator pushed back on the VIDEO_COMPOSITION_V1.md "out of
scope" entry that ruled real-time WebRTC out. Reframed
immediately: realtime is in scope, just not in *this* arc.
The realtime work has its own scope lock to land (R0):

1. Port `runway-hackathon/backend/app/services/realtime_avatar_client.py`
   (WebRTC session orchestration + tool injection).
2. Port `runway-hackathon/backend/app/services/documents_client.py`
   (RAG documents for avatar conversations — bridges to K
   arc).
3. Expose `/v1/realtime_sessions` through media-engine.
4. Shell-side `ConversationThread` integration (intersects
   K8/K9).
5. SPA realtime client (Phase 3 work).

**Shared boundary with V1:** Asset shape must accept
realtime-captured artifacts (transcripts, snippets,
generated clips) so the two arcs don't fork the data model.
V1 lands first, R0 locks against the V1 shape.

## What's next (SESSION 143)

V1 shipped this session — V2 (composition runtime) is the
recommended next slice. R1 (realtime schema) is also unblocked
and could ship in parallel, but my recommendation is V2 first
so two consecutive schema-only slices don't stack.

**V2 — Composition runtime.**

- `execute_composition` Celery task in `apps/compositions/tasks.py`.
- Per-step state machine: PENDING → RUNNING → SUCCEEDED |
  FAILED. Composition status: DRAFT → PLANNING → RUNNING →
  COMPLETED | PARTIAL | FAILED.
- Partial-failure resume — operator retries from failed step
  without re-running prior successes.
- Per-step cost estimator skeleton
  (`apps/compositions/cost.py`) — concrete per-primitive
  estimators land starting V3.
- Mock primitive (`apps/compositions/primitives/mock.py`) so
  runtime can be exercised end-to-end without Runway credits.
- 4-5 new tests covering state machine + resume + cost
  aggregation.

V2 ships with no production Runway calls — V3 is the first
real primitive (`generate_avatar_speech`, absorbing K6.5).
V2 + mock primitive is enough to exercise the runtime in
tests + give V3 stable ground.

After V2: V3 (`generate_avatar_speech` — K6.5 absorbed),
V4 (`generate_visual_clip`), V5 (Video backwards-compat
shim), V6 (`talking_head_with_backdrop` — first new
capability).

### Alternative next slice: R1

If preferred, R1 (`RealtimeSession` schema, mirrors V1's
shape) is fully unblocked. Same pattern: `apps.realtime`
app, two models, cross-workspace signal + `clean()`, admin,
isolation test. 12-15 tests. Schema only; broker is R3.

## Calibration carried forward

- **The reframe pattern repeats.** Three times now —
  cost-cap math, Maya tutor-mode framing, gpt-5 vs
  gpt-4o-mini, now "K6.5 is one endpoint swap" — the
  operator caught a framing that was too narrow. The fix
  isn't "be more cautious"; it's **map the predecessor before
  scoping**. SESSION 142's first 30 minutes was a runway-
  hackathon pipeline audit that surfaced the architecture
  gap. That audit should be the default first step on any
  cross-system work, not a debugging tool.

- **"Out of scope" is a working hypothesis, not a contract.**
  Mid-session realtime reframe shows what happens when the
  doc author and the operator have different mental models
  of what's "v1 product" vs "v2 nice-to-have." Lock the
  contract rules; let the scope list be negotiated.

- **The "additional video kinds" framing was wrong all
  along.** Every "kind" should have been a composition from
  day 1. The hackathon shipped enum entries because that's
  what frameworks make easy — but the right unit was
  always "a recipe of primitives." This is the same shape
  problem as the K0 "per-spokesperson vs per-workspace vs
  hybrid" framing that the knowledge layer scope lock
  collapsed to one shape (workspace + M2M).

## AI Notes

- Two design-lock docs now have the same shape (`KNOWLEDGE_LAYER.md`
  → `VIDEO_COMPOSITION_V1.md`): purpose → contract rules →
  framing corrections → data model → primitives → execution →
  slice breakdown → out of scope → open questions → verification.
  Future scope locks (R0) should match this shape — it's the
  proven container for "lock the contract, not the
  implementation."

- The two pre-K6.5 cleanups (K4.2, K6.2) shipped *before* the
  architectural reframe. That ordering was right: they were
  small enough to land cleanly, they cleared real bugs the
  operator was hitting, and they validate that the cleanup
  discipline (test → fix → test → commit) still produces tight
  diffs even when the larger arc is mid-replan. K6.3/K6.4/K7.1
  are still queued; K6.4 is likely deprecated by V8 (trim +
  reformat primitives) but K6.3 + K7.1 stand.

- The runway-hackathon pipeline map (SESSION 142 mid-session
  Explore call) is worth keeping as a reference artifact. It
  found 15+ output kinds, 5 Runway endpoints, 30+ campaign
  router endpoints, all the ffmpeg subprocess patterns, and
  the realtime client. Consider committing it as
  `docs/RUNWAY_HACKATHON_PIPELINE_MAP.md` for future
  reference — V3+ implementation slices will repeatedly need
  to reference "which hackathon service does this primitive
  port from."
