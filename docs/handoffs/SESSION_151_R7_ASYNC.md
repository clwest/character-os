---
title: "Session 151 — R7.2 async tool dispatch + render_video + INVENTORY fix"
date: 2026-05-15
status: complete
session: 151
previous_handoff: ./SESSION_150_R7_SYNC_TOOLS.md
---

# Session 151 — R7.2 async tool dispatch + render_video

## TL;DR

Single-slice session with one bundled bug fix. Three
things shipped under the R7.2 umbrella:

1. **Async tool dispatch** — `QUEUED` status, generic
   `execute_tool_invocation` Celery task, `dispatch_tool`
   + `approve_invocation` enqueueing for `is_async=True`
   tools. R7.0's async branch was a stub; R7.2 fills it.

2. **`render_video` tool** — the first real async tool +
   the threshold-crossing tool (cost $0.08, threshold
   $0.05) that exercises R7.0's approval flow end-to-end
   with a real side effect (creates a Composition, fires
   the V-arc execution chain).

3. **INVENTORY Celery undercount fix** (drift-prevention
   backlog item 5 from SESSION 147). One-line fix —
   `celery_app.loader.import_default_modules()` before
   reading `celery_app.tasks`. Count goes from 5 → 8.

`attach_memory` was originally part of R7.2 but **split
out to R7.3** because it requires R6's query to widen
(R6.1) — an architectural change worth its own slice.

627 backend tests (+14 from R7.2). One new migration
(50 → 51). One new Celery task. No new force-mock
flags.

## Drift sweep (per CLAUDE.md, updated this session)

| Category | Status |
|---|---|
| `context-kit doctor` | 0 blocking, 3 pre-existing warnings — clean |
| Stale processes | Three stale (Django May 14 + Celery May 14 + uvicorn May 15) — **killed + restarted mid-session** at operator's request after the SPA started returning 502s |
| Pending migrations | 50/50 at session start → 51/51 after R7.2's migration applied |
| Frontmatter date | `WHAT_IT_IS.md last_revised: 2026-05-15` matches today |
| INVENTORY git_sha | Regenerated at session end against `e8564f9` |

CLAUDE.md's "Session-start drift sweep" section updated
this session to point at `context-kit doctor` as the
primary tool (operator clarified: "doctor is in place of
drift" — the parallel context-kit agent's work extended
doctor rather than shipping a separate `drift`
subcommand). Manual spot-checks remain for categories
doctor doesn't yet cover (stale processes, INVENTORY
`git_sha` vs `HEAD`).

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `e8564f9` | R7.2 feat — QUEUED status + generic Celery task + dispatcher async wiring + render_video tool + INVENTORY Celery fix + 14 tests + 2 ALLOWED_FILES additions + design-doc updates |
| 2 | (this commit) | SESSION 151 handoff + start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md updates (Phase 4 row + drift-sweep section pointing at doctor) |

## What R7.2 ships

### Schema

`RealtimeToolInvocation.Status` gains `QUEUED =
"queued"` between `AWAITING_APPROVAL` and `SUCCEEDED`.
Migration `0003_r7_2_queued_status` is TextChoices-
metadata-only (no DDL). Status lifecycle for async
tools:

```
                      (over threshold)
                  ┌─→  AWAITING_APPROVAL ─→  rejected
                  │                       └─→  QUEUED (on approve)
   created  ─→ ───┤
                  │
                  └─→  QUEUED (under threshold)
                       │
                       └─→  SUCCEEDED | FAILED  (via Celery)
```

Sync tools skip QUEUED entirely (INVOKED → SUCCEEDED /
FAILED in one step at view-layer time).

### Generic Celery task

`apps/realtime/tasks.py:execute_tool_invocation`. One
task for all async tools — the registry is the source
of truth. Adding a new async tool doesn't add a new
Celery task; you just register with `is_async=True`.

Shape:

1. Load invocation (workspace + spokesperson selected).
2. Idempotency: terminal-state invocations no-op.
3. Look up tool spec; if missing (de-registered race),
   mark FAILED with a clear message.
4. Call executor `(session, args)`.
5. Catch exceptions → mark FAILED with the message.
6. On success: link `produced_composition` /
   `produced_asset` from the executor's return payload
   (executor returns dict with `composition_id` /
   `asset_id` keys; task resolves to the FK).
7. Mark SUCCEEDED + completed_at.

The task NEVER raises — exceptions become FAILED audit
rows so the SPA can always render a structured
response.

### Dispatcher async wiring

R7.0 wired the async branch but never enqueued
anything (left a "TODO R7.2" comment). R7.2 fills in:

- New initial status logic: `AWAITING_APPROVAL` (over
  threshold) > `QUEUED` (async, under threshold) >
  `INVOKED` (sync).
- After creating the invocation row, async path calls
  `_enqueue_async(invocation)` →
  `execute_tool_invocation.delay(str(invocation.id))`.
- Refresh the row + return a `DispatchResult` reflecting
  the post-Celery state. In eager mode (tests +
  `CELERY_TASK_ALWAYS_EAGER`) this returns
  `state="succeeded"`; in production this returns
  `state="queued"` since the Celery task is still
  pending.
- `approve_invocation` flips async invocations to
  `QUEUED` + enqueues; sync stays inline.
- New `_maybe_result(invocation)` helper snapshots
  `produced_composition_id` / `produced_asset_id` into
  the SPA-facing `result` dict for SUCCEEDED async
  invocations (the raw executor return value isn't
  persisted on the row — only the FK links are).

### `render_video` tool

`apps/realtime/tools/render_video.py` — first real async
tool. Cost: $0.08 (80_000 micros) — over the $0.05
default threshold, so the approval flow ALWAYS lands.

Flow:

1. Validate `script` arg (required).
2. Resolve recipe from `args.recipe` (default
   `talking_head`); look up in `RECIPES` registry.
3. Call `check_video_limit(session.workspace)` for the
   per-month tier gate (10 / 30 / unlimited).
4. Build starter kwargs (workspace + spokesperson +
   script + optional name + optional use_knowledge).
5. Call `recipe.starter(...)` → returns a fresh
   Composition.
6. Fire `execute_composition.delay(str(comp.id))` —
   the V-arc's existing execution chain takes over.
7. Return `{event: "render_video_queued",
   composition_id, recipe, message}`.

The generic Celery task wrapper sees `composition_id`
in the result and writes it to the invocation row's
`produced_composition` FK.

### INVENTORY Celery undercount fix

`apps/accounts/management/commands/inventory.py:
_collect_celery_tasks` now calls
`celery_app.loader.import_default_modules()` before
reading `celery_app.tasks`. The root cause was lazy
autodiscovery: Celery's task registry is only populated
when something forces module imports. Management
commands don't trigger this; the worker does at boot.
The fix mirrors what the worker does.

**Count progression**: 5 (with bug) → 8 (after fix + R7.2's
new task). The 8 tasks:

1. `character_os.debug_task` (celery.py)
2. `embeddings.embed_document`
3. `conversations.embed_message`
4. `realtime.fetch_transcript_for_session` (R5)
5. `realtime.execute_tool_invocation` (R7.2 new)
6. `videos.poll_video_until_terminal`
7. Two `apps.compositions.tasks` tasks (V-arc runtime
   + retry)

Drift backlog item 5 resolved.

## Tests (14)

| # | Test | Surface |
|---|---|---|
| 1 | `test_async_under_threshold_executes_via_celery` | dispatch (async) |
| 2 | `test_async_over_threshold_awaits_approval` | dispatch (async) |
| 3 | `test_approve_async_invocation_enqueues_celery` | approval (async) |
| 4 | `test_celery_task_records_failure_on_executor_exception` | Celery task |
| 5 | `test_celery_task_handles_tool_deregistered` | Celery task |
| 6 | `test_celery_task_idempotent_on_terminal_invocation` | Celery task |
| 7 | `test_render_video_happy_path_creates_composition` | render_video (end-to-end) |
| 8 | `test_render_video_missing_script_failed` | render_video |
| 9 | `test_render_video_unknown_recipe_failed` | render_video |
| 10 | `test_render_video_tier_limit_exceeded_failed` | render_video (tier gate) |
| 11 | `test_render_video_cost_is_over_threshold` | render_video (sanity) |
| 12 | `test_render_video_with_recipe_override` | render_video (args.recipe) |
| 13 | `test_full_rest_flow_dispatch_approve_succeed` | REST end-to-end |
| 14 | `test_inventory_celery_task_count_includes_realtime_tasks` | drift fix |

## Contract rule alignment

| Rule | How R7.2 holds it |
|---|---|
| 1 (workspace anchor) | All tools dispatch under the session's workspace. `render_video` calls `check_video_limit(session.workspace)`. The starter's own cross-workspace `clean()` (V0 guard) rejects mismatched spokespeople. |
| 4 (Asset shape) | `produced_composition` / `produced_asset` linkage on the invocation row reuses V1's Asset model — no new persistence shape. |
| 6 (workspace-scoped tools) | View-layer queryset filter drops cross-workspace sessions; tier-defense-in-depth (R7.1) still active. |
| 7 (cost ceilings) | `render_video` exercises both ceiling layers — per-monthly-cap via `check_video_limit` AND per-tool approval threshold via the dispatcher. |
| 9 (mock mode) | Tests use `CELERY_TASK_ALWAYS_EAGER` + `EMBEDDING_FORCE_MOCK` + `RENDER_SCRIPT_FORCE_MOCK`. Production uses real Celery; tools handle their own mock state. |

## Open questions touched

* **Q-r-2 (rejection narration)** — partly resolved
  (server-side R7.0). SPA wiring in R8.
* **Q-r-8 (cross-session tool side effects)** —
  not touched. Deferred to R7.3 alongside
  `attach_memory` (the tool that surfaces this risk).

## Calibration moments worth carrying

### 1. Splitting a scope-locked slice mid-implementation is fine

R7.2 was scope-locked SESSION 142 as "two async tools."
Mid-proposal this session, the `attach_memory` design
hit an architectural snag: R6's `compose_session_memory`
filters by `status=ENDED`, so the in-progress session's
transcript snapshot (which `attach_memory` would commit)
is structurally invisible to the next session's memory
projection. Wiring `attach_memory` end-to-end requires
R6 to widen — that's R6.1, a separate slice. Rather
than force the split implementation in the same session,
shipped `render_video` only and explicitly split R7.2 →
R7.2 (render_video) + R7.3 (attach_memory + R6.1
prerequisite).

**Carry-forward**: when a scope-locked slice's
dependencies surface late, split *with the operator* at
proposal time. Better than half-shipping. The scope
lock is a contract about *what eventually lands*, not
*what lands in one commit*.

### 2. INVENTORY's lazy-autodiscovery bug was easier to fix than it sounded

SESSION 147 deferred the Celery undercount fix as "one
session of work." It was actually ~3 lines of code:
`celery_app.loader.import_default_modules()` before
the registry read. The reason it looked harder is the
audit framed it as two bugs (undercount + dirty flag);
they were *different* bugs that share a generator
module but no logic. Fixing one without the other was
trivial.

**Carry-forward**: when an audit notes "two bugs" in
the same module, ask if they're related before
estimating effort together. Fast bug fixes can ride
along with feature commits when the operator agrees +
the scope is small (today: R7.2 + this fix took one
session).

### 3. The drift-sweep tool is `doctor`, not a separate command

Operator clarified mid-session: "doctor is in place of
drift." Updated CLAUDE.md's "Session-start drift sweep"
section to point at `context-kit doctor` as the
primary tool. The original SESSION 147 backlog item 1
("`context-kit drift` subcommand") evolved during the
parallel agent's implementation — they extended doctor
rather than shipping a separate command. Doctor's
output includes the four drift categories the audit
identified (some are explicit, some are spot-check
recommendations).

**Carry-forward**: when a "scheduled new tool" actually
ships as an extension to an existing one, update the
discipline docs immediately. The CLAUDE.md drift-sweep
section pointed at a phantom `context-kit drift`
command for 3 sessions before this update; that's
exactly the kind of doc drift the SESSION 147 audit
was *about*.

## Drift carryover from SESSION 150

* **Stale processes** at session start: three of them
  (Django 12:34PM-today, Celery + uvicorn from May 14).
  **Fixed mid-session** — operator asked for stack
  restart (SPA was returning 502s). Killed + restarted
  Django + Celery + uvicorn. Verified the new
  endpoints (R7.0 + R7.1 routes) responded correctly
  post-restart.
* **`context-kit drift` subcommand** — superseded by
  doctor (see calibration moment 3).
* **INVENTORY Celery undercount** — fixed in R7.2.

Remaining drift-prevention backlog items 2 + 3 (auto-
bump `last_revised` on handoff write + promote
calibration entries to TRUST_CALIBRATION) still queued.

## Project memories touched this session

None new. The four R7.2 calibration moments (this
handoff + R7.0/R7.1's calibration notes) anchor the
slicing + testing patterns; no memory promotion
warranted yet.

## What's next (SESSION 152)

### Recommendation: R7.3 (attach_memory + R6.1 prerequisite)

Two parts paired in one slice:

**R6.1 — widen R6 to include in-progress sessions**. Two
viable approaches:

Option A — Widen by status. R6's query becomes "any
RealtimeSession for this spokesperson with a
transcript_asset, excluding the current session by
pk." This includes ENDED sessions (the existing case)
+ READY/NOT_READY sessions where `attach_memory` has
committed a partial transcript. Trade-off: a session
that crashed and never reached ENDED still surfaces.

Option B — Add a flag. New `source_spec` field on
`Asset(TRANSCRIPT)` rows: `committed_for_memory:
bool`. R6 looks for "ENDED OR committed_for_memory".
`attach_memory` sets the flag when it commits a
partial transcript. R5's session-end task also sets
it. Trade-off: requires R5 + R6 to coordinate the
flag's source of truth.

Lean: **Option A** for simplicity. Crash-state
sessions surfacing in memory is fine — the worst case
is the avatar references a session that didn't fully
complete, which the operator-facing UI can frame as
"earlier today we started talking about X."

**R7.3 — `attach_memory` tool**:

* Pulls current transcript via
  `fetch_transcript_for_session.delay(session_id)` —
  R5's existing Celery task is idempotent and works
  on non-ENDED sessions.
* Async (cost ~$0.001).
* Pro tier (it's a power-user feature; the broadcast
  use case is "long planning calls where the operator
  wants discrete checkpoints").
* Returns `{event: "memory_committed", asset_id,
  message}`.

Estimated scope: ~10 new tests, no migrations, 1 new
tool, ~20 lines of R6 widen.

### Alternatives

* **R8 (SPA)** — `/spokespeople/:id/talk` route +
  SDK + cost forecasting + tool-approval modal. The
  operator-visible moment. Could ship after R7.3 lands
  the full v1 tool catalog, OR ship now with the 5
  tools we have. Operator's call.
* **R9 (cost governance)** — per-workspace minutes
  budget + live cost ticker. Smaller, isolated.
* **F8.1 / K7.x** — smaller cleanup slices.

### Recommendation rationale

**R7.3 + R6.1 next** to close the tool catalog at v1
spec (6 tools). Then R8 ships the operator-visible
SPA against the complete catalog rather than against
a partial one. R9 + R10 + F8.1 + K7.x can ride
smaller follow-ups.

If the operator wants the realtime arc *visible* now,
R8 directly is viable — the avatar will be missing
`attach_memory` but the other five tools are
demo-ready.

## Files changed in this commit

* `docs/handoffs/SESSION_151_R7_ASYNC.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten with R7.2
  outcome + R7.3 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `e8564f9` SHA into the R7.2 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  git_sha: 611ae94 → e8564f9. Celery tasks: 5 → 8
  (fix landed). Migrations: 50/50 → 51/51. Shell LOC:
  37,777 → 38,627 (+850) in 202 → 204 files (+2:
  render_video.py + test_r7_2_async_tools.py;
  migrations excluded from the count).
* `CLAUDE.md` — Phase 4 realtime-arc row updated for
  R7.2 + R7.3 split. Drift-sweep section updated to
  point at `context-kit doctor`.

---

*Handoff written end-of-SESSION 151, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
