---
title: "Session 142 — Video composition scope lock + pre-K6.5 cleanups + realtime arc confirmed"
date: 2026-05-14
status: complete
session: 142
previous_handoff: ./SESSION_141_K4_DETAIL_AND_RENDER_AUDIT.md
---

# Session 142 — V0 scope lock, K4.2 + K6.2 cleanups, R arc confirmed

## TL;DR

Three outcomes:

1. **Pre-K6.5 cleanups shipped (K4.2 + K6.2).** Soft-deleted
   knowledge documents now restore on re-ingest instead of
   blocking; missing portrait_path on render now fails fast
   with a clear operator message instead of an opaque
   media-engine 400. 102 K-tests pass (3 new). Committed as
   `4321fdb`.

2. **Architecture reframe — K6.5 absorbed into V3.** Mapped
   the runway-hackathon pipeline (15+ output kinds, 5 Runway
   endpoints, ~2,000 lines of dormant composition logic in
   `media-engine/app/services/*`). Discovered the *real*
   blocker isn't one wrong endpoint; it's that every endpoint
   is a *leaf* (input → finished MP4), so combinations like
   "talking-head + backdrop + music bed + captions" can't be
   expressed. Scope-locked `docs/design/VIDEO_COMPOSITION_V1.md`
   (851 lines, 9 contract rules, 16 step primitives, 16 slices
   V0-V15). K6.5 absorbed into V3 — same Runway endpoint
   target (`/v1/avatar_videos`), landing inside the new
   Asset+Composition shape so it's reusable.

3. **Realtime WebRTC confirmed in-scope as a parallel arc
   (R0+).** Operator surfaced mid-session that realtime
   conversation video is a launch requirement, not a v2 nice-
   to-have. Removed from VIDEO_COMPOSITION_V1.md's "out of
   scope"; reframed as a separate scope lock to land after
   V1. Shared dependency: V1's `Asset` shape must support
   realtime-captured artifacts so the two arcs don't fork
   the data model.

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

### `00-START-NEXT-SESSION.md` (overwritten)

- Phase 4 reframed as two parallel arcs (Knowledge K1-K10,
  Video V0-V15) plus a third pending (Realtime R0+).
- Slice table updated: K6.5 row replaced with V0 (done) +
  V1 (next) + V2-V15 (queued). K4.2 + K6.2 marked DONE.
- "Next: K6.5" section replaced with "Next: V1 — Asset +
  Composition schema" plus the R0 parallel-arc note.

### `CLAUDE.md` (amended)

- "Read-first" gains entries 6 (KNOWLEDGE_LAYER.md) + 7
  (VIDEO_COMPOSITION_V1.md).
- Phase 4 status table updated to reflect two parallel arcs
  + pending realtime arc.

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

**V1 — Asset + Composition + CompositionStep schema.**

- New Django app `apps.compositions`.
- Three models per `VIDEO_COMPOSITION_V1.md` §"Data model".
- Cross-workspace reference test
  (`test_step_rejects_cross_workspace_assets`).
- Repo-level isolation test
  (`test_only_composition_module_writes_assets`) — mirrors
  K2's pattern.
- Admin registration.

Zero user-visible value (same discipline as K1). The existing
`Video` model + `apps/videos/views.py` stays untouched; V5 is
the backwards-compat shim, not V1.

After V1: V2 (composition runtime), V3 (first primitive +
absorbs K6.5).

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
