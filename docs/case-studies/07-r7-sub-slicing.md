# Case Study 07 — R7 sub-slicing (one slice per session)

**Date:** SESSION 149 (R7 sub-slice), SESSION 148 (operator-
imposed one-slice-per-session calibration).
**Systems:** realtime arc scope-lock, R7 (tool dispatch), R7.0
through R7.3.

## Problem

The realtime arc's scope-lock (`docs/design/REALTIME_AVATAR_V1.md`)
originally defined R7 as one slice: "server-side tool dispatch,
approval flow, and both sync and async tool paths". Estimated
by the AI as a two-session slice.

After SESSION 148 shipped in one session, the operator
calibrated on "one slice per session" as a discipline — one
scope-locked contract per session end, with the paired doc
updates and INVENTORY regen at close. R7's original scope
would have burst that budget.

## Evidence

- SESSION 148 shipped R6 (cross-session memory) in one clean
  session end with contract updates + `docs/handoffs/` entry.
- R7 as originally scoped: tool registry + dispatch engine +
  sync executor + async Celery path + approval-state machine
  + REST surface + audit rows + tests → estimated 3 sessions
  minimum.
- Pattern from V-arc (SESSIONS 142-143): V15 was split into
  V15.0-V15.4 for the same reason after operator hit the
  ceiling in one session.

## Root cause

Not a technical failure — a planning failure. AI-drafted scope
locks tend to bundle "related" work into single slices because
the code is topologically connected. But shipping a session
end (doc updates + INVENTORY regen + handoff + tests) has a
fixed overhead that gets amortized worse when a slice runs
long.

The V-arc had already surfaced this pattern; R7 was the first
place it was applied prospectively rather than after the fact.

## Decision

Sub-slice R7 into four sessions:

- **R7.0** — foundation: tool registry, `ToolSpec`,
  `dispatch_tool()` skeleton, first tool (`show_videos_tab`,
  $0 UI-only), migration for `AWAITING_APPROVAL` status.
- **R7.1** — sync tools: `recall_knowledge`,
  `recall_recent_conversations`, `handoff_to_teammate`, plus
  tier-aware filtering infrastructure.
- **R7.2** — async tools + `render_video`: Celery-executed
  invocations, threshold-crossing approval flow exercised
  end-to-end.
- **R7.3** — `attach_memory`: paired with R6.1 widening the
  memory query so mid-session commits flow into next-session
  memory.

Each sub-slice ships in one session with its own contract
update, tests, and handoff.

## Implementation change

Four separate feature commits across SESSIONS 149-152, each
with paired context-kit doc updates:

- `646c492` — R7.0
- `611ae94` — R7.1
- `e8564f9` — R7.2
- `b3f76cb` — R7.3 + R6.1

Test counts progressed monotonically: 596 → 613 → 627 → 641
Django tests over the four sessions.

## Verification

The v1 realtime tool catalog (6 tools) closed clean. Every
sub-slice hit its acceptance test on the session it was
scoped for. No slice re-opened for a follow-up.

Compared to the alternate history where R7 shipped in one
"big" session: the big-session version would have compressed
the approval-state migration, the tier filtering, and the
async Celery wrapper into one review event with no test
diffing between them. Diagnosing a regression in that world
would have required bisecting one massive commit.

## Lasting rule

**Foundation-first, one slice per session, paired with doc
updates in the same commit.** AI-drafted scope locks over-
bundle. The operator's job is to size each slice for a
session-close event and to sub-slice pre-emptively when the
lock is bigger than that.

The `docs/handoffs/` chain (`SESSION_148_...` through
`SESSION_152_...`) documents the sub-slice sequence — each
handoff is a session-close event, not a mid-work snapshot.
