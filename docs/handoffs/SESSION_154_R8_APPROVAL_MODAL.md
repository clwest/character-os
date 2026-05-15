---
title: "Session 154 — R8.1 tool-approval modal + cost forecasting UI"
date: 2026-05-15
status: complete
session: 154
previous_handoff: ./SESSION_153_R8_SPA_FOUNDATION.md
---

# Session 154 — R8.1 tool-approval modal + cost forecasting

## TL;DR

Single-slice session shipped R8.1. The realtime arc's
**threshold-crossing tool (`render_video`) is now
demonstrable end-to-end from the SPA**: operator opens
a session → fires the mock-mode debug button → modal
pops → Approve → backend executes the Composition →
result lands in the tool-result panel.

R8.2 is the last R8 piece — replaces the manual debug
buttons with the SDK's `useClientEvent` hook for native
avatar invocation, adds the live cost ticker, and
wires the `sendClientEvent` narration path for Q-r-2.

22 SPA vitest pass (10 → 22, +12). Backend unchanged
at 641. SPA build clean.

## Drift sweep

| Category | Status |
|---|---|
| `context-kit doctor` | 0 blocking, 3 pre-existing warnings — clean |
| Stale processes | None new |
| Pending migrations | 51/51 clean |
| Frontmatter date | matches today |
| INVENTORY git_sha | Regenerated at session end against `aac6ee4` |

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `aac6ee4` | R8.1 feat — API client hooks + ToolApprovalModal + TalkRoute extensions + cost forecast pill + mock-mode debug buttons + tsconfig types fix + 12 tests + design-doc updates |
| 2 | (this commit) | SESSION 154 handoff + start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

## What R8.1 ships

### Tool dispatch surface

Three new hooks in `web/src/lib/api/realtime.ts`:

```ts
useInvokeTool()
  → POST /api/realtime_sessions/<id>/invoke_tool/
  → returns DispatchResult { state, invocation_id, tool_name, cost_micros, result?, error_message?, reason? }

useApproveInvocation()
  → POST /api/realtime_tool_invocations/<id>/approve/
  → returns DispatchResult

useRejectInvocation()
  → POST /api/realtime_tool_invocations/<id>/reject/  body: { reason? }
  → returns DispatchResult
```

The `dispatchResultSchema` (Zod) mirrors the server-side
`_serialize_dispatch_result` shape exactly. State values:
`succeeded | awaiting_approval | failed | queued | rejected`.

### ToolApprovalModal

`web/src/components/tool-approval-modal.tsx` (220 lines).
Minimal inline modal — no Radix dependency. Fixed-
positioned with `bg-background/80 backdrop-blur-sm`
overlay + card centered.

Renders:
* **Headline** in spokesperson's first person — tool name
  translated via `formatToolLabel`: `render_video` →
  "render a video for you", `attach_memory` → "save this
  conversation to memory". Generic fallback: "run the
  {tool_name} action".
* **Cost in dollars** — `cost_micros / 1_000_000` to 2
  decimal places.
* **Args dict** (if present) — per-key/value rows,
  truncated to 80 chars/value for sanity.
* **Optional reason textarea** — pre-filled empty;
  trimmed value passed to reject endpoint or omitted
  if empty.
* **Approve / Reject buttons** — disabled during async
  op (don't strand operator mid-decision).

Dismiss via:
* Esc (only when no async op in flight)
* Backdrop click (only when no async op in flight)
* Explicit X button

### TalkRoute extensions

New state slots:
* `pendingInvocation: PendingInvocation | null` — set to
  the modal-pending invocation; null otherwise.
* `lastToolResult: DispatchResult | null` — surfaces the
  final state of the last invocation below the live
  panel.

New callbacks:
* `handleInvokeTool(toolName, args)` — POSTs via
  `useInvokeTool`; routes by result.state:
  `awaiting_approval` → sets `pendingInvocation` → modal
  opens. Everything else → sets `lastToolResult` →
  `ToolResultPanel` renders.
* `handleApprovalResolved(result)` — clears
  `pendingInvocation`, sets `lastToolResult`.
* `handleApprovalDismiss()` — clears
  `pendingInvocation` only (server-side state
  unchanged; the audit row stays AWAITING_APPROVAL).

### Mock-mode debug buttons

`MockSessionPanel` gains a "Test tool dispatch" section:

* **"Fire `render_video`"** button — invokes with
  `{ script: "Pitch the spring sale to my audience." }`.
  Over $0.05 threshold → modal opens.
* **"Fire `show_videos_tab`"** button — invokes with
  empty args. $0 cost → executes inline → result lands
  in `ToolResultPanel`.

R8.2 will replace these buttons with the SDK's
`useClientEvent` hook so the avatar's LLM fires tools
natively. Until then the debug buttons let operators
exercise the full approval / inline-execute paths
end-to-end without a real avatar.

### Cost forecast pill

`IdlePanel` gains a pill next to the Start button:

```
"~$0.40 for 5 min"
```

Hardcoded placeholder constants at the top of
`talk.tsx`:

```ts
const ESTIMATED_COST_PER_MINUTE_MICROS = 80_000; // ~$0.08/min
const PROVIDER_MAX_SESSION_MINUTES = 5;
```

R9 (cost governance backend) ships per-provider
micros-per-second lookups; R8.1's UI gracefully
upgrades when those constants get replaced with a
backend-fetched estimate.

### ToolResultPanel

Color-coded by result state:
* `succeeded` → emerald
* `queued` → blue
* `rejected` → yellow
* `failed` → destructive

Pulls a short summary from the result payload:
* `composition_id` → "composition: comp_..."
* `asset_id` → "asset: asset_..."
* `event` → "event: render_video_queued"
* fallback → "(succeeded)"

### Dev infra

`tsconfig.app.json` types extended:
```diff
- "types": ["vite/client"],
+ "types": ["vite/client", "vitest/globals", "@testing-library/jest-dom"],
```

R8.0 wired jest-dom matchers into vitest at runtime
(via `vitest.setup.ts`) but didn't tell tsc about them.
SPA build worked because tsc didn't traverse the one
test file that used `toBeInTheDocument`. R8.1's additional
matcher calls would have broken the build; the tsconfig
fix unblocks it.

## Tests (12)

### `tool-approval-modal.test.tsx` (8)

| # | Test |
|---|---|
| 1 | renders headline with spokesperson + tool + cost |
| 2 | renders args dict when present |
| 3 | approve fires `useApproveInvocation` + `onResolved` |
| 4 | reject without reason fires `useRejectInvocation` with undefined reason |
| 5 | reject with trimmed reason passes the reason |
| 6 | dismiss button fires `onDismiss` |
| 7 | Esc dismisses when idle |
| 8 | error message renders on approve failure (modal stays open) |

### `talk.test.tsx` (4 new; 11 total)

| # | Test |
|---|---|
| 1 | idle panel renders cost forecast pill (R8.1) |
| 2 | mock-mode session exposes tool dispatch buttons (R8.1) |
| 3 | firing an over-threshold tool opens the approval modal (R8.1) |
| 4 | firing an under-threshold tool surfaces success in tool-result panel (R8.1) |

SDK + API client hooks all mocked; the modal +
TalkRoute lifecycle stays hermetic.

## Contract rule alignment

| Rule | How R8.1 holds it |
|---|---|
| 6 (workspace-scoped tools) | SPA POSTs to `/invoke_tool/` which goes through the dispatcher's existing workspace + tier defense-in-depth. |
| 7 (cost ceilings) | Exercised end-to-end: `render_video`'s $0.08 cost > $0.05 threshold triggers approval modal; operator's decision is the gating signal. |
| 9 (mock mode) | Preserved. Mock-mode UX is the load-bearing demo path. SPA detects via `session.mock_mode` + exposes debug buttons. |

## Open questions touched

* **Q-r-2 (rejection narration)** — server-side done
  R7.0; UI capture done R8.1 (reason recorded
  server-side via `error_message`); the SPA →
  avatar `sendClientEvent` piece lands in R8.2.
* **Q-r-9 (WebRTC fallback)** — not touched (R8.2).

## Calibration moments worth carrying

### 1. Type system + runtime config drift on testing-library

R8.0 wired `@testing-library/jest-dom/vitest` into the
vitest setup file and tests passed. The SPA build also
passed — because tsc didn't traverse the one test that
used `toBeInTheDocument`. R8.1's additional matcher
calls broke the build immediately. The fix (`types` in
`tsconfig.app.json`) is one line, but the gap had been
latent for a full session.

**Carry-forward**: when wiring a test framework plugin
at runtime, also wire it at type-check time. The fix
is the same pattern as vitest's setup file — once per
project, not per test.

### 2. Voiced UI copy matters for in-conversation modals

The first draft had the modal say "Approve tool
`render_video`?" with the tool name as a code span.
Felt off — the avatar's voice + the SPA's modal
should sound aligned. Switched to "Sasha wants to
render a video for you" (per-tool human translation
in `formatToolLabel`). Costs 5 lines for a switch
statement; the SPA now reads as one voice instead of
two.

**Carry-forward**: when the SPA surfaces something the
avatar would "do," voice the copy in first person from
the spokesperson's perspective. Tool names are
debugging fields, not operator-facing strings.

### 3. Don't strand the operator mid-decision

First draft let Esc / backdrop click dismiss the modal
even while an approve / reject HTTP call was in flight.
Realized this could leave the operator confused
("did my click register?") + the audit row in an
ambiguous state. Now: dismiss is gated on
`pendingMode === "idle"` — once the operator commits,
the modal blocks until the response lands.

**Carry-forward**: modal dismissal during async ops is
almost always wrong. Disabled buttons + a "...ing"
label give the operator confidence the system received
their input. Race-y dismiss surfaces hurt audit
clarity for low UX gain.

## Drift carryover

Nothing new.

## Project memories touched this session

None new.

## What's next (SESSION 155)

### Recommendation: R8.2 (cost ticker + SDK wiring + rejection narration)

Three load-bearing pieces remaining to close R8:

**SDK inner-component wiring** — replace the mock-mode
debug buttons with the avatar SDK's native invocation
surface:

* The `useClientEvent` hook (consumed inside
  `<AvatarCall>`) receives tool-invocation events from
  the avatar's data channel.
* Inner component dispatches to the backend via the
  R8.1 `useInvokeTool` hook.
* On `awaiting_approval` → parent's `pendingInvocation`
  state opens the modal (R8.1 surface stays unchanged).
* On `succeeded` / `failed` / `rejected` →
  `sendClientEvent` to the avatar so the LLM can
  narrate the outcome in-character. **Q-r-2 fully
  resolved.**

**Live cost ticker** — runs during the session,
displays elapsed time × per-minute estimate. Updates
on a 1-second interval. Drives operator awareness
when sessions approach the 5-minute cap.

**WebRTC fallback messaging** — when `<AvatarCall>`'s
`onError` fires, show a clear error panel + "fall
back to recorded video" CTA. **Q-r-9 resolved.**

Estimated scope: ~6-10 unit tests + 1 Playwright spec
that drives a fake `useClientEvent` event through the
flow. No backend changes.

### Alternatives

* **R9 (cost governance backend)** — could land before
  R8.2 to feed the cost ticker real data. But R8.2's
  ticker can ship against the hardcoded placeholder
  and graceful-upgrade when R9 ships. Order doesn't
  matter materially.
* **R10 (provider hardening)** — small.
* **Drift-prevention backlog items 2 + 3** — small.
* **F8.1 / K7.x** — non-realtime cleanup.

### Recommendation rationale

**R8.2 next** to close R8 fully. The arc becomes
fully demoable to a real avatar at that point; R9
and R10 are operational polish. The current arc gap
is "the avatar can't fire tools yet" — that's R8.2's
load-bearing change.

## Files changed in this commit

* `docs/handoffs/SESSION_154_R8_APPROVAL_MODAL.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten with R8.1
  outcome + R8.2 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `aac6ee4` SHA into the R8.1 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  git_sha: 7669007 → aac6ee4. Backend counters
  unchanged (R8.1 is SPA-only).
* `CLAUDE.md` — Phase 4 realtime-arc row updated for
  R8.1 SHIPPED + the full sub-slice detail.

---

*Handoff written end-of-SESSION 154, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
