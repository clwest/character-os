---
title: "Session 149 — R7.0 tool dispatch foundation"
date: 2026-05-15
status: complete
session: 149
previous_handoff: ./SESSION_148_R6_MEMORY.md
---

# Session 149 — R7.0 tool dispatch foundation

## TL;DR

Single-slice session. R7 was scope-locked as one slice
("Tool catalog (6 tools, workspace-scoped) +
RealtimeToolInvocation audit + approval-threshold modal")
but proved too big for one session under the
SESSION 148 one-slice-per-session discipline. Sub-sliced
into R7.0 / R7.1 / R7.2 (foundation / sync tools / async
tools) mirroring V15.0-V15.4. R7.0 shipped end-to-end
with one feat commit + this docs commit.

Avatar's LLM can now invoke tools mid-session via WebRTC
data-channel events; the SPA POSTs to a dispatch
endpoint; the server resolves from a registry, gates on
cost threshold, creates an audit row, and either
executes inline or returns `awaiting_approval`. First
tool — `show_videos_tab` (UI-only nav event) — proves
the round trip. R7.1 + R7.2 add the five remaining tools
on top of this foundation.

596 backend tests (+22 from R7.0). One new migration
(50/50). No new Celery tasks (R7.2 adds those). No new
media-engine routes.

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `646c492` | R7.0 feat — `tools/` registry + `show_videos_tab` tool + `dispatch.py` + viewset action + new invocation viewset + `AWAITING_APPROVAL` status + migration + 22 tests + 2 `ALLOWED_FILES` additions + design-doc slice-table split + change-log entry |
| 2 | (this commit) | SESSION 149 handoff + `00-START-NEXT-SESSION.md` rewrite + backfilled `646c492` SHA in design doc + regenerated INVENTORY (50/50 migrations, +1,327 shell LOC) + CLAUDE.md Phase 4 row bump |

## What R7.0 ships

### Registry (`apps/realtime/tools/`)

```python
from . import register_tool

@register_tool(
    name="show_videos_tab",
    description="...",
    cost_micros=0,
    workspace_scoped=False,
    is_async=False,
)
def executor(session, args: dict) -> dict:
    return {"event": "show_videos_tab", "spokesperson_id": ...}
```

Adding a new tool: one new file in `apps/realtime/tools/`
+ one decorated function. The package `__init__.py`
imports each tool module at the bottom (side-effect
import triggers the decorator). `get_workspace_tools(
workspace)` is the seam R7.1 fills with tier-aware
filtering (Q-r-4 resolution).

### Dispatcher (`apps/realtime/dispatch.py`)

```python
dispatch_tool(session, tool_name, args, *, user) -> DispatchResult
approve_invocation(invocation) -> DispatchResult
reject_invocation(invocation, *, reason="") -> DispatchResult
```

* Resolves tool by name (`DispatchError` 400 on unknown).
* Workspace-scope guard — every workspace_scoped tool
  dispatches under the session's workspace; cross-
  workspace invocations are structurally impossible at
  view-layer (queryset filter on session) + the
  existing R1 `clean()` guard on
  `produced_asset` / `produced_composition`.
* Cost-vs-threshold gate via
  `getattr(settings, "REALTIME_TOOL_APPROVAL_THRESHOLD_MICROS", 50_000)`.
  Over → `awaiting_approval` state, no executor call.
  Under → execute inline (sync) or queue Celery (async,
  R7.2).
* Audit row always created. Executor exceptions caught
  + recorded as FAILED so the endpoint never returns
  5xx for tool failures (SPA gets a structured 200
  with `state=failed` + `error_message`).
* `approve_invocation` is idempotent on resolved
  invocations; if the tool de-registered between
  dispatch and approval, recorded as FAILED with a
  clear message.
* `reject_invocation` records the optional `reason` on
  `error_message` so the SPA can narrate it back via
  the WebRTC data channel (resolves Q-r-2 server-side;
  SPA wiring lands in R8).

### REST surface

```
POST /api/realtime_sessions/<id>/invoke_tool/
  body: {tool_name, args}
  → 200 {state: "succeeded", result, invocation_id, ...}
  → 202 {state: "awaiting_approval", invocation_id, cost_micros, reason}
  → 200 {state: "failed", invocation_id, error_message}
  → 400 {detail: "unknown tool"}
  → 403/404 cross-workspace (queryset filter drops it)

POST /api/realtime_tool_invocations/<id>/approve/
  → 200 {state: "succeeded", result, ...}

POST /api/realtime_tool_invocations/<id>/reject/
  body: {reason}  (optional)
  → 200 {state: "rejected", reason}

GET /api/realtime_tool_invocations/?session=<uuid>
GET /api/realtime_tool_invocations/<id>/
```

### Model + migration

* `RealtimeToolInvocation.Status` adds
  `AWAITING_APPROVAL`. Migration
  `0002_r7_awaiting_approval_status` (TextChoices
  metadata only — no DDL change). Migration count
  49 → 50.
* `RealtimeToolInvocation` gains a `workspace`
  property surfacing `self.session.workspace` — keeps
  the shared `IsWorkspaceMember._workspace_of`
  resolver stable without traversing the indirect FK
  chain at permission-check time.

### First tool

`show_videos_tab` — UI-only nav event. The avatar invokes
it when the operator asks to see recorded videos; the
SPA receives `{event: "show_videos_tab", spokesperson_id: ...}`
and flips routes. $0 cost, workspace_scoped=False.
Proves the round trip end-to-end without depending on K-
or V-arc subsystems.

## Tests (22)

| # | Test | Surface |
|---|---|---|
| 1 | `test_registry_has_show_videos_tab` | registry |
| 2 | `test_registry_unknown_raises_keyerror` | registry |
| 3 | `test_list_tools_includes_show_videos_tab` | registry |
| 4 | `test_get_workspace_tools_returns_full_catalog` | registry |
| 5 | `test_dispatch_unknown_tool_raises` | dispatch (Python) |
| 6 | `test_dispatch_show_videos_tab_executes_inline` | dispatch (Python) |
| 7 | `test_dispatch_above_threshold_awaits_approval` | dispatch (Python) |
| 8 | `test_dispatch_executor_failure_recorded` | dispatch (Python) |
| 9 | `test_dispatch_args_persisted_on_audit_row` | dispatch (Python) |
| 10 | `test_approve_executes_deferred_tool` | approval flow |
| 11 | `test_approve_idempotent_on_resolved_invocation` | approval flow |
| 12 | `test_approve_after_deregister_marks_failed` | approval flow |
| 13 | `test_reject_records_reason` | approval flow |
| 14 | `test_reject_idempotent` | approval flow |
| 15 | `test_invoke_tool_endpoint_inline_execution` | REST |
| 16 | `test_invoke_tool_endpoint_above_threshold_returns_202` | REST |
| 17 | `test_invoke_tool_endpoint_unknown_tool_returns_400` | REST |
| 18 | `test_invoke_tool_endpoint_cross_workspace_session_404` | REST |
| 19 | `test_approve_endpoint` | REST |
| 20 | `test_reject_endpoint` | REST |
| 21 | `test_list_invocations_filters_by_session` | REST |
| 22 | `test_list_invocations_workspace_scoped` | REST |

## Contract rule alignment

| Rule | How R7.0 holds it |
|---|---|
| 1 (workspace anchor) | Sessions remain workspace-anchored (unchanged from R1). Invocations inherit via the session FK + the new `workspace` property. |
| 6 (workspace-scoped tools) | View-layer queryset filter drops cross-workspace sessions before dispatch fires; existing R1 `clean()` guard on the audit row rejects cross-workspace `produced_*` refs. Verified by `test_invoke_tool_endpoint_cross_workspace_session_404`. |
| 9 (mock mode) | Dispatcher is provider-agnostic. R7.1+ tools that call external services (`recall_knowledge`, `attach_memory`) will check their respective `*_FORCE_MOCK` flags internally. |

## Open questions resolved (partial)

* **Q-r-2 (tool rejection narration).** Server-side
  shape done: reject endpoint accepts an optional
  `reason`, stores it on the audit row's
  `error_message`. The SPA in R8 will pull this from
  the retrieve endpoint or from the reject response and
  forward via the SDK's `sendClientEvent` so the
  avatar's LLM can narrate "I can't do that right now"
  in-character.
* **Q-r-4 (per-workspace tool catalog overrides).**
  Seam in place — `get_workspace_tools(workspace)` is
  the function R7.1 fills with tier-based filtering.
  v1 returns the full catalog; v2 (post-R7.2) can layer
  workspace-configurable overrides.

Remaining R-arc open questions (Q-r-1, Q-r-3, Q-r-5,
Q-r-6, Q-r-8, Q-r-9) are not touched by R7.0.

## Drift sweep (per SESSION 147 discipline)

| Category | Status |
|---|---|
| Stale processes | Same processes from SESSION 148 still running. Not blocking. |
| Pending migrations | 0001+0002 applied this session. 50/50 clean. |
| Frontmatter date | `WHAT_IT_IS.md last_revised: 2026-05-15` matches today's handoff date. Clean. |
| INVENTORY git_sha | Regenerated this session against `646c492`. Clean. |

## Calibration moments worth carrying

### 1. Sub-slicing the over-scope-locked

R7 was scope-locked at SESSION 142 as one big slice.
SESSION 148 calibrated that one slice per session is the
natural unit. SESSION 149 honored the calibration by
sub-slicing R7 → R7.0 / R7.1 / R7.2 at proposal time,
*before* writing code. The scope-lock can be wrong about
slice size; the discipline is to notice + sub-slice
explicitly + update the slice table in the same commit.

**Carry-forward:** when an R/V/K slice scope-lock
predates the one-slice-per-session calibration, audit
its size at proposal time. If it's >2 file-categories or
>1 model migration, sub-slice in the design doc + tell
the operator. SESSION 149's sub-slicing came up in
proposal cleanly; the operator confirmed; the cost was
zero. The cost of *not* sub-slicing is a SESSION 143-
style catch-up pass.

### 2. Test fixture restore matters more than register-clear

The first iteration of `reset_registry` cleared the
registry on teardown then tried to repopulate via
module-reload tricks. It didn't actually restore. Two
subsequent unrelated tests (test_invoke_tool_endpoint_inline_execution,
test_list_invocations_filters_by_session) failed because
the production catalog was empty. Single-test runs
passed because the registry was fresh.

Fixed by switching to **snapshot at fixture entry +
clear-and-update on teardown** — the obvious pattern.
Module reload is a code smell in a teardown; if you
think you need it, you're probably restoring the wrong
state.

**Carry-forward:** fixtures that touch in-memory
singletons (registries, caches, settings) should
snapshot + restore the actual state, not reload the
defining module. Module-level side-effect imports
(`from . import show_videos_tab` triggering
`@register_tool`) are stable on first import but don't
re-fire on `importlib.reload` in the way the cleanup
expected.

### 3. Pyright noise vs real signal

R7.0's Pyright diagnostics included ~15 false positives:
unused `_u`/`_ua` tuple discards (intentional), `args is
not accessed` in `show_videos_tab.executor` (signature
must conform to the Protocol), DRF `get_queryset`
return-type narrowing complaints, `create_user` on
UserManager, FK auto-attributes (`session_id`,
`workspace_id` etc) the Django stubs don't define. None
of these are real.

The two diagnostics worth investigating: import
resolution failures (Pyright didn't resolve
`apps.realtime.dispatch` / `apps.realtime.tools`).
Probably a stubs / path issue not worth fixing here.

**Carry-forward:** Pyright in this repo is noisy on
Django patterns. Filter for novel diagnostics (not seen
in pre-existing code). When in doubt, run the test
suite — tests are the ground truth.

## Drift carryover from SESSION 148

* **Stale processes:** still there. The deferred
  `context-kit drift` subcommand (parallel agent) is the
  programmatic resolution. Not blocking R-arc.
* **Inventory generator bugs (Celery undercount + dirty
  flag):** still there. Celery count reads 5; real
  registered is 7+. Deferred to SESSION 147 backlog
  item 5; R7.2 will likely make this more visible when
  it adds at least one new Celery task (`render_video`'s
  async path).

## Project memories touched this session

None new. The cross-arc isolation calibration moment
from SESSION 146 + the one-slice-per-session calibration
from SESSION 148 both anchored this session's decisions.

## What's next (SESSION 150)

### Recommendation: R7.1 (sync tools)

Three sync tools on top of the R7.0 foundation:

* **`recall_knowledge`** — RAG against K2. The avatar
  calls it with a query string; the dispatcher runs
  `retrieve_for_spokesperson(spokesperson, query, top_k=3)`,
  returns the top hits as a structured payload the
  SPA can render. Cost: ~$0.001 (one embedding +
  one DB query); well under threshold; sync.
* **`recall_recent_conversations`** — read prior
  `Asset(TRANSCRIPT)` rows for this spokesperson.
  Mirrors R6's session memory query but returns
  individual transcript summaries instead of a
  composed projection. Cost: $0; sync.
* **`handoff_to_spokesperson`** — cross-spokesperson
  event in the same workspace. Returns a structured
  hint the SPA dispatches on (similar shape to
  `show_videos_tab`). Cross-workspace handoff rejected
  via workspace-scope check in the executor. Cost: $0;
  sync.

R7.1 also adds tier-aware filtering in
`get_workspace_tools(workspace)` (resolves Q-r-4): the
function will use `workspace.tier` (or equivalent)
to filter the catalog. Each tool gets a
`tier_required` attribute (or a default of "starter").

Estimated test count: ~15 new tests (3-4 per tool +
filter tests). Total after R7.1: ~611.

### Alternative: R7.2 (async tools)

If the operator wants to land the higher-value tools
sooner:

* **`render_video`** — Celery-driven; fires a
  composition starter (`talking_head` by default).
  The threshold-crossing tool that exercises the
  approval modal end-to-end. Cost: ~$0.05-0.50
  depending on starter + duration.
* **`attach_memory`** — pulls partial transcript
  mid-session, composes via R6's
  `compose_session_memory`, pushes as a fresh Runway
  document, attaches to spokesperson. Cost: ~$0.001
  (LLM call + Runway document push).

R7.2 is more invasive — adds Celery tasks, exercises
the `queued` dispatch state R7.0 wired but couldn't
test end-to-end. Could ship after R7.1 or in parallel
to it (no inter-dependency).

### Alternative: R8 (SPA — operator visibility)

Skip R7.1 + R7.2 for now and ship the SPA route +
SDK integration. R8 will work with just
`show_videos_tab` (R7.0's tool) — the avatar will be
toolless beyond UI nav but the live conversation +
memory loop will be operator-visible. Worth
considering if the operator wants to *see* R1-R6 +
R7.0 working before adding more tools.

### Recommendation rationale

**R7.1 next.** Sync tools are smaller surface area
than R7.2's Celery-driven ones, and `recall_knowledge`
is the most operator-facing tool in the catalog (an
avatar that can pull up the relevant doc mid-
conversation is the demo moment R6's "warm opener"
sets up). R7.2 + R8 follow R7.1 in either order.

## Files changed in this commit

* `docs/handoffs/SESSION_149_R7_FOUNDATION.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten with R7.0
  outcome + R7.1 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `646c492` SHA into the R7.0 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  50/50 migrations, +1,327 shell LOC, +4 files.
* `CLAUDE.md` — Phase 4 realtime-arc row bumped to
  document R7.0 shipped + the sub-slicing.

---

*Handoff written end-of-SESSION 149, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
