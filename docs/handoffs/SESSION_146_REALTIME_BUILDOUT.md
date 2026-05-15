---
title: "Session 146 — R1 through R5 (realtime arc opens + grounds)"
date: 2026-05-15
status: complete
session: 146
previous_handoff: ./SESSION_145_KNOWLEDGE_ARC_CLOSE.md
---

# Session 146 — R1 through R5: realtime arc opens end-to-end

## TL;DR

Five sequential R-arc slices closed in one extended session.
The realtime avatar arc that scope-locked SESSION 142 now has
its first end-to-end smoke path: live sessions work,
grounded in workspace knowledge, with post-session
transcripts persisted as Assets.

* **R1** (`9299dcf`) — `apps.realtime` schema +
  cross-workspace guards + isolation test.
* **R2** (`e8eb7d1`) — media-engine
  `/internal/realtime_sessions/` (POST + GET + DELETE) +
  provider abstraction package + `MockRealtimeProvider` +
  `RunwayRealtimeProvider` (partial).
* **R3** (`26378e9`) — Django broker
  `/api/realtime_sessions/`, tier-limit gate, state
  machine, media-engine client wrappers, Runway
  `end_session` implemented.
* **R4** (`6521451`) — Knowledge → Runway document
  bridge. `compose_realtime_document` + media-engine
  `/internal/realtime_documents/` + Runway `create_document`
  + `attach_documents` implemented. Broker create flow
  composes → pushes → persists `provider_document_id` +
  `knowledge_chunk_ids`.
* **R5** (`885508d`) — Transcript capture. Runway
  `fetch_transcript` + media-engine
  `GET .../transcript/` + Celery task creates
  `Asset(TRANSCRIPT)` on session end + wires
  `RealtimeSession.transcript_asset`.

**Test counts** (start of session → end):
* Django: 463 → 514 (+51 across R1-R5).
* Media-engine: 0 baseline → 23 (the suite was created
  with R2; R3-R5 added to it).

Every method on `RealtimeProvider` is now implemented for
Runway. No more `NotImplementedError` markers in
`runway.py`. The R-arc has its first end-to-end smoke
path.

## Commit log

| Order | Commit | Slice | What it shipped |
|---|---|---|---|
| 1 | `9299dcf` | **R1** | Schema (`RealtimeSession`, `RealtimeToolInvocation`) + `clean()` + signals + admin + isolation test |
| 2 | `311aa78` | (back-fill) | R1 commit ref |
| 3 | `e8eb7d1` | **R2** | Provider abstraction package, Runway impl (create + poll), mock, two endpoints |
| 4 | `3d8597c` | (back-fill) | R2 commit ref |
| 5 | `26378e9` | **R3** | Broker viewset, tier-limit gate (`check_realtime_session_limit`), state machine, client wrappers, Runway `end_session` |
| 6 | `5b094b6` | (back-fill) | R3 commit ref |
| 7 | `6521451` | **R4** | `compose_realtime_document`, `/internal/realtime_documents/`, Runway `create_document` + `attach_documents`, broker integration |
| 8 | `a744e8d` | (back-fill) | R4 commit ref |
| 9 | `885508d` | **R5** | Runway `fetch_transcript`, transcript GET endpoint, `apps.realtime.tasks.fetch_transcript_for_session`, broker end-flow enqueue |
| 10 | `d28da8a` | (back-fill) | R5 commit ref |

This handoff: latest commit.

## What shipped (concrete)

### R1 — schema slice

* New `apps/realtime` Django app. `RealtimeSession` +
  `RealtimeToolInvocation` models with workspace +
  spokesperson anchors, nullable `ConversationThread` FK
  (K8 intersection — same logical conversation can span
  text + audio), `Provider` enum (defaults to RUNWAY),
  state machine (DRAFT → CREATING → NOT_READY → READY
  → ENDED / FAILED), cost fields, `mock_mode`,
  `transcript_asset` FK to V1's `Asset` (contract rule 4
  — shared persistence, no fork).
* Cross-workspace defense in depth via `clean()` +
  `pre_save` signal on each model. Skips state-only
  updates (status / timestamps / cost) so the R3
  broker's status flips don't re-validate unchanged FKs.
* Admin hides `provider_session_key` (contract rule 9 —
  the SDK JWT-token is never displayed).
* Repo-level isolation test (mirrors V1 / K2 patterns)
  prevents unsanctioned writes to the realtime tables.
* +14 backend tests covering happy path, cross-workspace
  rejection (per FK, via both `clean()` and signal),
  state-only update skip, PROTECT semantics, tool-
  invocation cross-workspace asset / composition checks.

### R2 — provider abstraction + media-engine endpoints

* New `media-engine/app/services/realtime_provider/`
  package:
  - `__init__.py` — `RealtimeProvider` Protocol (6
    methods), 5 dataclasses, `RealtimeProviderError` +
    `RealtimeUnavailableError`, `get_provider(name,
    settings)` registry that short-circuits to
    `MockRealtimeProvider` when `settings.runway_mock`
    is True.
  - `runway.py` — `RunwayRealtimeProvider`. Implements
    `create_session` + `poll_session`. The other 4
    methods raise `NotImplementedError` pointing at
    R3/R4/R5 (filled in across subsequent slices).
    `_redact()` scrubs Bearer / JWT-shaped tokens from
    any upstream response logged. Decoupled from
    Campaign — takes primitives per the scope-lock
    Protocol.
  - `mock.py` — `MockRealtimeProvider` implements all 6
    methods with deterministic stubs. sha256(inputs)
    → stable `session_id` for snapshot-friendly tests.
* Two new endpoints: `POST /internal/realtime_sessions/`
  + `GET /internal/realtime_sessions/<id>/`. Contract
  rule 9 enforced — router logs `session_id` only,
  never `session_key`. The 18 tests include a caplog
  assertion that the key never appears in log records.

### R3 — Django broker

* New `RealtimeSessionViewSet` at
  `/api/realtime_sessions/` — POST + GET + DELETE +
  POST `/end/` action (alternate end for proxies that
  strip DELETE).
* **Tier gate**: new `realtime_sessions_per_month` in
  TIER_LIMITS (starter=5, pro=20, agency=unlimited). New
  `check_realtime_session_limit()` mirrors
  `check_video_limit`. `Usage` dataclass grew
  `realtime_sessions_used` / `realtime_sessions_limit`
  so the F3 dashboard tile picks it up for free.
* **Session state machine**: DRAFT → CREATING (after
  upstream POST) → READY (after poll) → ENDED (on
  DELETE) with FAILED branch on upstream errors.
* **Two serializers** for the same model:
  `RealtimeSessionSerializer` (omits `provider_session_key`
  — default for list / retrieve) and
  `RealtimeSessionWithKeySerializer` (extends with the
  key — used ONLY as the create response). Contract
  rule 9 enforced at four layers: admin hides field,
  serializer omits, only POST returns the key,
  dedicated test asserts retrieve JSON has no key.
* Media-engine client gained 3 new methods
  (`realtime_session_create`, `realtime_session_poll`,
  `realtime_session_end`) + 2 new result dataclasses.
* Runway provider's `end_session` implemented (was
  `NotImplementedError` from R2). Treats 404 / 410 as
  success (already-gone).
* +18 broker tests.

### R4 — knowledge → Runway document bridge

* New `character_os/realtime_document.py:compose_realtime_document`
  builds the Markdown body from K2 retrieval. Anchored
  on `business_brief` (falls back to name) so chunks
  most-related to spokesperson identity float to top.
  Caps at Runway's 40k-char ceiling; tail chunks drop
  on truncation; returns `chunk_ids` for citation.
  Never raises on retrieval failure — degrades to
  business_brief-only doc.
* Runway provider's `create_document` (POSTs to
  `/v1/documents`) + `attach_documents` (POSTs to
  `/v1/avatars/<id>/documents`) implemented.
* New `POST /internal/realtime_documents/` endpoint
  wrapping `provider.create_document`.
* Broker create flow updated — composes doc → pushes
  to media-engine → persists `provider_document_id` +
  `knowledge_chunk_ids` → passes
  `document_ids=[provider_document_id]` into
  `session_create`.
* K0 privacy holds end-to-end — a dedicated R4 test
  confirms workspace A's spokesperson can't see
  workspace B's chunks in the composed doc.
* +10 backend tests covering composer (no knowledge,
  with knowledge, max_chars cap, cross-workspace
  isolation, retrieval-failure degradation) + broker
  integration (persists provider_document_id +
  knowledge_chunk_ids, passes document_ids, works
  with empty knowledge, chunk_ids match composer
  output).

### R5 — transcript capture

* Runway provider's `fetch_transcript` implemented
  (the last NotImplementedError on the Runway side).
  Hits `/v1/avatar_conversations/<id>`; 404 returns
  empty result so operator can re-fetch when Runway
  finishes recording. Normalizes turn shape into
  structured segments + readable text blob.
* New `GET /internal/realtime_sessions/<id>/transcript/`
  endpoint.
* New `apps/realtime/tasks.py:fetch_transcript_for_session`
  Celery task:
  - Fetches via media-engine
  - Creates `Asset(asset_type=TRANSCRIPT)` in
    `session.workspace` with `inline_content=text`,
    `source_spec={primitive_kind, session_id,
    provider_session_id, segments, fetched_at,
    mock_mode}`
  - Wires `session.transcript_asset`
  - Idempotent (replaces stale Asset on rerun)
  - Empty transcripts (Runway 404) skip Asset creation
  - Retries network-y errors via `_is_retryable` filter
* Broker `_end_session` enqueues the task after status
  flips ENDED. Best-effort — enqueue failure logs but
  doesn't block the end response.
* +9 backend tests + 1 media-engine test.

### Per-component test breakdown

| Surface | Tests added | Pattern |
|---|---|---|
| `apps/realtime/tests/test_models.py` | 14 | R1: schema + cross-workspace |
| `apps/realtime/tests/test_isolation.py` | 1 | R1: repo-level grep |
| `media-engine/tests/test_realtime_provider.py` | 23 | R2-R5: provider + endpoints |
| `apps/realtime/tests/test_broker.py` | 18 | R3: broker flow |
| `apps/realtime/tests/test_r4_knowledge_bridge.py` | 10 | R4: composer + broker |
| `apps/realtime/tests/test_r5_transcript_capture.py` | 9 | R5: task + broker |
| **Total** | **75** | |

## Architectural milestones

* **Contract rule 4 landed (R5)**: realtime sessions and
  recorded videos share the persistence surface
  (`Asset`). Transcripts get the same provenance shape
  (`source_spec.primitive_kind="realtime_transcript"`)
  as V1 step outputs. F5 lineage + F6 citations carry
  through for free once R8 surfaces the SPA — transcripts
  can be cited by future compositions and walked via the
  existing asset-lineage panels.
* **Contract rule 8 landed (R2)**: single-provider
  abstraction. Runway is the only implementation in v1;
  adding Synthesia / HeyGen later is one file + a
  registry entry. No code outside `get_provider`
  branches on provider name.
* **Contract rule 9 landed (R2 + R3)**: SDK connect
  token (`provider_session_key`) is treated as a
  secret. Hidden in admin, omitted from list /
  retrieve serializers, scrubbed from upstream log
  output, present only in the POST create response.
  Four-layer enforcement + a caplog test asserts the
  key never appears in log records.
* **K-arc ↔ R-arc intersection (R4)**: Runway document
  corpus and `KnowledgeDocument` corpus stay in sync
  via *derivation*, not replication. K layer is the
  system of record. The Runway doc is rebuilt fresh
  from K2 retrieval at every session-create; knowledge
  changes mid-session don't propagate.

## Calibration moments worth carrying

### 1. TIER_LIMITS edits keep silently failing

Twice this session the `realtime_sessions_per_month`
edit to `apps/billing/models.py` reported success but
didn't take. The recovery was reading the file to
verify state, then re-editing with a slightly different
context window. The pattern looked like Edit's
old_string matched the file's *cached* state from a
prior read rather than disk.

**Carry-forward**: after any Edit on a hot file (one
that other edits have touched in the same turn), read a
small window of the target to confirm the change
actually landed before moving on. The whole-file Edit
is fine; chained edits in the same turn need a confirm
read between them.

### 2. Tests that create rows for OTHER arcs trip the
   isolation tests

R1's test_models.py creates a `Composition` to exercise
the `RealtimeToolInvocation.produced_composition`
cross-workspace check. R5's tests create `Asset`
(TRANSCRIPT) rows via the broker. Both tripped
`apps/compositions/tests/test_isolation.py` until I
added the new test paths to the composition
isolation `ALLOWED_FILES`.

**Carry-forward**: every new test file that creates
rows in a cross-arc model needs an `ALLOWED_FILES`
entry in BOTH the realtime + composition isolation
tests (and embeddings if it touches chunks). The
isolation tests are the right gate — adding the path is
a code-review event with a one-line note explaining
why the file is sanctioned.

### 3. The `(commit TBD)` back-fill habit caught a
   real failure mode

Three slices this session had the back-fill commit
attempt fail because `Edit replace_all=true` matched
*another* "commit TBD" string elsewhere in the doc.
The first replace_all on a doc with multiple TBD
markers replaces them all to the same hash, which is
wrong if they reference different slices.

**Carry-forward**: never use `replace_all=true` for
"commit TBD" back-fills. Use a targeted Edit with a
unique context window per slice.

### 4. The hackathon's `realtime_avatar_client.py`
   (807 lines) stays alongside the new abstraction

R2's provider abstraction is the v2 path the R-arc
consumes. The hackathon's Campaign-coupled
`realtime_avatar_client.py` stays for the legacy
`/api/*` surface. They coexist until Phase 2 retires
the legacy routes (no slice planned yet).

**Carry-forward**: when an arc has a hackathon
implementation worth referencing for HTTP shapes,
**read it for the shape, don't port from it**. The
hackathon code optimized for fewer abstraction
layers; the character-os code optimizes for arc-by-arc
substitution. The same Runway endpoint can have
different consumer code in both, and that's fine.

## Project memories saved this session

None new.

## What's next (SESSION 147)

The R-arc has five slices left:

### Option A — R6 (recommended)

Cross-session memory. Two pieces:

1. Summarize prior `Asset(TRANSCRIPT)` bodies via
   gpt-5-mini (matches K6's `script_synthesis` pattern
   — fifth `*_FORCE_MOCK` flag for dev determinism).
2. Project the summary into the next session's
   `compose_realtime_document` body so the avatar
   opens with "returning operator" warmth instead of
   re-introducing itself.

R5's idempotent transcript persistence + workspace-
scoped Asset shape make R6 a clean composition.

### Option B — R7 (tools)

Tool catalog: 6 workspace-scoped tools the avatar can
invoke mid-session. Workspace check on every
invocation; `RealtimeToolInvocation` audit trail
already exists from R1. R7 ships the tool registry +
the workspace-scoped routing + the approval-threshold
modal for expensive tools (`render_video`,
`capture_clip`).

R7 is bigger than R6 (more surface) but doesn't
require R6 to land first.

### Option C — R8 (SPA)

Operator-facing surface: `/spokespeople/:id/talk`
route + `@runwayml/avatars-react` SDK integration +
cost forecasting UI + tool-approval modal. The
backend is ready for this — every shape R8 needs is
already on `RealtimeSession`. R8 is the slice that
makes the realtime arc visible to the operator.

R8 is the most user-facing but also depends on the
SDK integration which is its own learning curve. R7
unblocks the "tool approval modal" part of R8, so
landing them together (R7 → R8) is sensible.

### Option D — R9 / R10 (cost + provider hardening)

Both small, both load-bearing for production but not
gating other slices.

### Recommendation

**R6**, then R7, then R8. R6 closes the memory loop;
R7 prepares the tool-approval surface R8 consumes; R8
finally surfaces the arc to the operator. R9 + R10 can
ride a smaller follow-up session.

If the operator wants the realtime arc visible *now*,
they can pick R8 directly — but the avatar will feel
cold (no memory) and toolless until R6 + R7 land.

## AI Notes

* **Session pacing**: 5 slices in one extended session
  is the same pace as SESSION 143's V3-V13 buildout
  (11 slices). Both worked because each slice has a
  tight shape and the prior slice's scaffolding makes
  the next one cheap. R1-R5 is the "open the arc + lay
  the foundation" run; R6+ is where each slice has
  bigger per-slice scope.
* **`_FORCE_MOCK` family is now four flags** —
  `RUNWAY_FORCE_MOCK`, `EMBEDDING_FORCE_MOCK`,
  `RENDER_SCRIPT_FORCE_MOCK`,
  `CONVERSATION_REPLY_FORCE_MOCK`. R6 will add a fifth
  (`REALTIME_MEMORY_FORCE_MOCK` or similar) when it
  introduces another LLM synthesis call. The pattern
  is solid; new flags should follow it.
* **`RunwayRealtimeProvider`'s deferred-method
  pattern worked well** — each method raised
  `NotImplementedError("X lands in <slice>")` until
  the slice arrived. Easy to audit ("which methods
  still need work?"), easy to test (each deferred
  method had a matching shape-test). The pattern is
  worth reusing for future provider abstractions.
* **The R5 task lives in `apps.realtime.tasks` (not
  `apps.compositions.tasks`)** — the file split is
  intentional. Realtime owns its own task surface so
  the next R-arc tasks (R6 summarization?) accumulate
  there without polluting the V-arc runtime path.
