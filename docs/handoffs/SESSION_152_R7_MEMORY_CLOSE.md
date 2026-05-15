---
title: "Session 152 — R7.3 attach_memory + R6.1 + v1 tool catalog complete"
date: 2026-05-15
status: complete
session: 152
previous_handoff: ./SESSION_151_R7_ASYNC.md
---

# Session 152 — R7.3 attach_memory + R6.1 widen + v1 catalog complete

## TL;DR

Single-slice session shipped two paired changes in one
commit (`b3f76cb`):

1. **R7.3 — `attach_memory` async tool** — mid-session
   memory commit. Pro tier, ~$0.001. Fires the new
   `capture_transcript` helper. Returns
   `{event, asset_id, session_id, status, message}`.

2. **R6.1 — widen R6's query** — dropped the
   `status=ENDED` filter from `compose_session_memory`.
   Any session with a `transcript_asset` now surfaces in
   next-session memory, regardless of status. This is
   the load-bearing change that makes `attach_memory`'s
   mid-session commits visible to the avatar's next
   session.

Plus a quiet refactor: R5's transcript-capture logic
extracted to `apps.realtime.tasks.capture_transcript`
helper, used by both R5's session-end Celery task and
R7.3's mid-session tool. One implementation, one set of
idempotency guarantees.

**The v1 tool catalog is now complete: 6 tools across
starter + pro tiers.** R-arc state: R1-R7 done; R8
(SPA), R9 (cost governance), R10 (provider hardening)
remain. R8 is the operator-visible moment — the
backend is complete, the SPA wires the SDK + cost
forecasting + tool-approval modal against the full v1
catalog.

641 backend tests (+14 from R7.3 + R6.1). No new
migrations, Celery tasks, media-engine routes, or
force-mock flags.

## Drift sweep (per CLAUDE.md, doctor-based)

| Category | Status |
|---|---|
| `context-kit doctor` | 0 blocking, 3 pre-existing warnings — clean |
| Stale processes | None (stack restarted SESSION 151) |
| Pending migrations | 51/51 clean |
| Frontmatter date | `WHAT_IT_IS.md last_revised: 2026-05-15` matches today |
| INVENTORY git_sha | Regenerated at session end against `b3f76cb` |

Clean session-start sweep.

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `b3f76cb` | R7.3 + R6.1 feat — `attach_memory` tool + R6 query widen + `capture_transcript` helper + 14 tests + 1 ALLOWED_FILES addition + design-doc updates |
| 2 | (this commit) | SESSION 152 handoff + start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md updates |

## What R7.3 + R6.1 ship

### R6.1 — widen `compose_session_memory`

```diff
  sessions = list(
      RealtimeSession.objects.filter(
          spokesperson=spokesperson,
-         status=RealtimeSession.Status.ENDED,
          transcript_asset__isnull=False,
      )
      .select_related("transcript_asset")
      .order_by("-ended_at")[:max_sessions]
  )
```

That's the entire R6.1 change in `character_os/realtime_memory.py`.

Rationale: the K0 / R0 contract on transcript memory
says "real conversations worth remembering." The
status check was a proxy — ENDED sessions usually have
real content. But mid-session memory commits (R7.3's
purpose) leave the session in READY status with a
transcript snapshot attached. The transcript Asset is
the actual content signal; status is incidental.

Edge cases:
* A FAILED session with a transcript (rare — usually
  transcript fetch happens at session-end) still
  surfaces. Operator-facing payoff is minor; not worth
  filtering.
* The current LIVE session being created doesn't
  surface in its own R6 call because at session-create
  time the row is in DRAFT with no transcript_asset.
  Self-inclusion is structurally impossible.

R6's prior test
`test_non_ended_sessions_excluded` (asserted READY
sessions are filtered out) inverted to
`test_non_ended_sessions_with_transcript_included`.
New sibling test
`test_sessions_without_transcript_still_excluded`
preserves the asset-gate assertion (the OTHER half
of the filter).

### `capture_transcript` shared helper

Extracted from R5's Celery task body. Lives in
`apps/realtime/tasks.py` as a module-level function.

```python
def capture_transcript(session) -> dict:
    """Fetch + persist as Asset(TRANSCRIPT). Idempotent."""
    if not session.provider_session_id:
        return {status: "empty", ...}
    try:
        result = client.realtime_session_fetch_transcript(...)
    except MediaEngineError as exc:
        return {status: "upstream_error", _retryable: ..., ...}
    if not result.text.strip():
        return {status: "empty", ...}
    # Delete prior transcript_asset if any (idempotent)
    # Create new Asset(TRANSCRIPT)
    # Wire session.transcript_asset
    return {status: "persisted", asset_id, chars}
```

R5's Celery task now wraps it:

```python
@shared_task(...)
def fetch_transcript_for_session(self, session_id):
    session = RealtimeSession.objects.get(pk=session_id)
    result = capture_transcript(session)
    if result["status"] == "upstream_error" and result.pop("_retryable", False):
        raise self.retry(...)
    return result
```

The helper is the source of truth for "how to capture
a transcript." Both code paths (R5 session-end + R7.3
mid-session) inherit the same:
* Idempotency (replaces stale Asset on rerun).
* Workspace anchor (Asset goes to `session.workspace`).
* Privacy (no cross-workspace leak — Asset belongs to
  the session's workspace by construction).
* Failure semantics (`MediaEngineError` → structured
  `upstream_error` payload, never raises).

### `attach_memory` tool

```python
@register_tool(
    name="attach_memory",
    description="Commit the current conversation to memory…",
    cost_micros=1_000,      # ~$0.001
    workspace_scoped=True,
    is_async=True,
    tier_required="pro",
)
def executor(session, args):
    from apps.realtime.tasks import capture_transcript
    result = capture_transcript(session)
    return {
        "event": "memory_committed",
        "session_id": str(session.id),
        "status": result["status"],
        "asset_id": result.get("asset_id"),
        "message": _operator_message(result["status"]),
    }
```

Status-differentiated operator messages:
* `persisted` → "I'll remember this conversation next time we talk."
* `empty` → "Not enough has been recorded yet — try again after we've talked a bit more."
* `upstream_error` → "I couldn't capture the snapshot just now. Don't worry — I'll save it at the end of our session."

The generic Celery task wrapper
(`execute_tool_invocation`) sees `asset_id` in the
return payload and writes it to the invocation row's
`produced_asset` FK. The SPA can pull
`/api/realtime_tool_invocations/<id>/` to render the
result with the linked asset.

**Cost gate**: $0.001 is under the $0.05 default
approval threshold so attach_memory executes inline
(no AWAITING_APPROVAL modal). Operators trigger it via
the avatar's LLM invocation; the SPA shows a "saving…"
toast then the result message.

**Tier gate**: Pro-only. Starter operators get
end-of-session memory automatically via R5 — paying for
the mid-session checkpoint feature is a Pro upgrade.

### Q-r-8 resolution

> Cross-session tool side effects. If `attach_memory`
> runs at the end of session A, it modifies the document
> attached to session B. Race: session B created
> mid-session A's memory composition sees stale state.
> Lean: composition is idempotent + last-write-wins;
> rare in practice but document the race in R6.

Resolved with the architecture above:
* `capture_transcript` is idempotent (replaces stale
  Asset on rerun).
* R6's memory composition is called fresh at every
  session-create — it reads whichever Asset is current
  at that moment.
* The race window is the standard "media-engine
  returned stale data" risk, not a multi-write merge
  problem. Two sessions opening simultaneously +
  `attach_memory` firing between their composes is
  pathologically rare in operator UX (operators don't
  open two sessions in the same second).

## Tool catalog at v1

| Tool | Tier | Cost | Sync/Async | Slice |
|---|---|---|---|---|
| `show_videos_tab` | starter | $0 | sync | R7.0 |
| `recall_knowledge` | starter | ~$0.001 | sync | R7.1 |
| `recall_recent_conversations` | starter | $0 | sync | R7.1 |
| `handoff_to_spokesperson` | pro | $0 | sync | R7.1 |
| `render_video` | starter | $0.08 | async | R7.2 |
| `attach_memory` | pro | ~$0.001 | async | R7.3 |

Starter operators see 4 tools (3 sync + 1 async with
approval). Pro+Agency operators see all 6.

## Tests (14)

| # | Test | Surface |
|---|---|---|
| 1 | `test_capture_transcript_persisted_on_ready_session` | helper (R7.3 load-bearing case) |
| 2 | `test_capture_transcript_empty_upstream_no_asset` | helper |
| 3 | `test_capture_transcript_upstream_error_no_asset` | helper |
| 4 | `test_attach_memory_happy_path_links_produced_asset` | tool end-to-end |
| 5 | `test_attach_memory_idempotent_replaces_stale_asset` | tool (Q-r-8) |
| 6 | `test_attach_memory_empty_upstream_succeeded_no_asset` | tool |
| 7 | `test_attach_memory_upstream_error_succeeded_no_asset` | tool |
| 8 | `test_attach_memory_session_without_provider_id_empty` | tool |
| 9 | `test_attach_memory_starter_tier_blocked_with_403` | tool (tier gate) |
| 10 | `test_attach_memory_cost_below_threshold` | tool sanity |
| 11 | `test_memory_loop_attach_memory_surfaces_in_next_session_r6` | R6.1 + R7.3 integration |
| 12 | `test_memory_loop_does_not_include_session_without_transcript` | R6.1 asset gate |
| 13 | `test_invoke_attach_memory_via_rest` | REST end-to-end |

Plus 1 net new R6 test from splitting
`test_non_ended_sessions_excluded` into two:
* `test_non_ended_sessions_with_transcript_included`
* `test_sessions_without_transcript_still_excluded`

## Contract rule alignment

| Rule | How R7.3 holds it |
|---|---|
| 1 (workspace anchor) | `capture_transcript` creates Asset on `session.workspace`. Never crosses workspaces. |
| 4 (Asset shape) | Reuses `Asset(TRANSCRIPT)` — same shape R5 uses. Zero new persistence shape. |
| 5 (knowledge integration one-way) | R6.1 widens the *read* surface; nothing writes to KnowledgeDocument. |
| 6 (workspace-scoped tools) | Tool's workspace gate flows through the session FK at view-layer; the dispatcher's tier check defends in depth. |
| 9 (mock mode) | Tests use `CELERY_TASK_ALWAYS_EAGER` + `EMBEDDING_FORCE_MOCK`. Production uses real Celery + Runway. |

## Calibration moments worth carrying

### 1. Pairing prerequisite changes with the consumer in one slice

R7.3 was queued as "attach_memory + R6.1 prerequisite"
in SESSION 151's handoff. Shipping them in one commit
(rather than two separate commits) worked well: the
R6.1 widen test is meaningless without an `attach_memory`-
style mid-session transcript, and `attach_memory` is
useless without the R6.1 widen. The slice's *value*
only lands when both ship.

**Carry-forward**: when a feature has a load-bearing
prerequisite that's small and lives in the same codebase,
ship them together. The commit message can name both
changes ("R7.3 + R6.1") rather than two separate slices.
Avoid the temptation to "land the prereq cleanly first" —
it leaves the feature half-shipped.

### 2. Extracting a helper between two code paths is cheap insurance

R5's Celery task body had ~100 lines of media-engine
fetch + Asset persistence + idempotency. R7.3 needed
the same logic. Two options:
* Copy-paste the body into the tool executor.
* Extract a shared helper.

The extraction was ~15 minutes (move body to
`capture_transcript`, leave task as a thin wrapper) and
guarantees future changes to "how transcripts are
captured" stay coherent. Both R5 and R7.3 inherit the
same idempotency, the same workspace anchor, the same
failure semantics.

**Carry-forward**: when two code paths need the same
logic AND the logic is small AND a clean helper
boundary exists (no shared state, no Celery-specific
context), extract immediately. Don't wait for the third
copy.

### 3. The "inverted test" pattern when changing semantics

R6.1 changes the meaning of "what's in the memory
projection" — from "ended sessions" to "sessions with
transcripts." The R6 test
`test_non_ended_sessions_excluded` asserted the OLD
semantic. Rather than deleting it, I inverted it:
`test_non_ended_sessions_with_transcript_included`
asserts the NEW semantic on the same fixture, then a
new test
`test_sessions_without_transcript_still_excluded`
preserves the OTHER half of the filter (the
transcript-asset gate that R6.1 keeps).

**Carry-forward**: when a slice changes a filter or
gate, rewrite the existing test that asserts the OLD
behavior to assert the NEW behavior on the same
fixture. Then add a sibling test for the part of the
gate that didn't change. Avoids losing test coverage +
makes the change visible in the diff.

## Project memories touched this session

None new.

## What's next (SESSION 153)

### Recommendation: R8 (SPA — operator-visible moment)

The realtime backend is now feature-complete at v1.
R8 ships the operator-visible surface:

* New SPA route `/spokespeople/:id/talk`.
* `@runwayml/avatars-react` SDK integration — takes
  `(sessionId, sessionKey)` from the broker's create
  response, renders the WebRTC client.
* Cost forecasting UI before session-start ("~$0.42
  for a 5-min session" — uses R3's tier-limit + a
  per-minute estimate).
* Live cost ticker during the session.
* Tool-approval modal: pops up when a tool's invocation
  returns `awaiting_approval` (today's only such tool is
  `render_video`); operator clicks Approve or Reject.
* `onClientEvent` → POST to `/api/realtime_sessions/<id>/invoke_tool/`
  with `{tool_name, args}`. Dispatch result fed back to
  SDK via `sendClientEvent` so the avatar's LLM can
  narrate the outcome.
* Q-r-2 (rejection narration) fully resolved via the
  client-event roundtrip.
* Q-r-9 (WebRTC fallback) addressed via the SDK's
  error events + a "fall back to recorded video" CTA.

R8 is a bigger slice than R7.x — likely 2-3 sessions
to ship across SPA route + SDK + modal + ticker +
error paths. Worth sub-slicing at proposal time per
the SESSION 149-150 calibration:
* **R8.0** — SPA route + SDK mount + basic session
  lifecycle (start / live indicator / end).
* **R8.1** — Tool-approval modal + cost forecasting UI.
* **R8.2** — Live cost ticker + error paths + WebRTC
  fallback messaging.

### Alternatives

* **R9 (cost governance)** — per-workspace minutes
  budget + live cost ticker. Smaller backend slice,
  but R8 needs the ticker UX anyway. Could ship the
  backend in R9 and the UI in R8.2.
* **R10 (provider hardening)** — drift verifier test.
  Smaller; can ride any session.
* **Drift-prevention backlog item 2 + 3** —
  auto-bump `last_revised` + TRUST_CALIBRATION
  promotion. Small. Worth picking up between slices.
* **F8.1 / K7.x** — non-realtime cleanup slices.

### Recommendation rationale

**R8 next** to bring the realtime arc operator-visible.
The backend has been complete since `attach_memory`
landed; the SPA is what makes the work *demonstrable*
to the operator. Sub-slice R8 at proposal time.

If the operator wants smaller backend wins first
(R9 backend, R10), those can ride between R8 sub-slices.
F8.1 / K7.x are non-realtime palette cleansers.

## Files changed in this commit

* `docs/handoffs/SESSION_152_R7_MEMORY_CLOSE.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten with R7.3
  outcome + R8 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `b3f76cb` SHA into the R7.3 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  git_sha: e8564f9 → b3f76cb. Shell LOC: 38,627 →
  39,278 (+651) in 204 → 206 files (+2: attach_memory.py
  + test_r7_3_attach_memory.py).
* `CLAUDE.md` — Phase 4 realtime-arc row updated for
  R7.3 SHIPPED + R7 closed + R8 next.

---

*Handoff written end-of-SESSION 152, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
