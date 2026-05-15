---
title: "Session 155 — R8.2 + R8 closes (operator-visible product story complete)"
date: 2026-05-15
status: complete
session: 155
previous_handoff: ./SESSION_154_R8_APPROVAL_MODAL.md
---

# Session 155 — R8.2 + R8 closes

## TL;DR

Single-slice session shipped R8.2. **R-arc state: R1-R8
done.** The operator-visible product story for the
realtime arc is feature-complete. R9 (cost governance
backend) + R10 (multi-provider drift verifier) remain
as operational polish; everything an operator can
experience in the SPA ships at this milestone.

Three small components compose the R8.2 close-out:

1. **`AvatarSessionInner`** — child of `<AvatarCall>`
   that consumes the SDK's `useClientEvents` hook.
   Receives tool-invocation events from the avatar's
   data channel and dispatches via the same
   `onToolInvocation` callback the mock-mode debug
   buttons use. Production tool-dispatch is now one
   path regardless of trigger source.

2. **`CostTicker`** — runs while live. 1-second
   interval. Tone shifts as the session approaches
   the 5-minute cap. Mock mode tagged so operators
   don't conflate mock cost with real spend.

3. **WebRTC fallback messaging** — `<AvatarCall
   onError>` routes to the error panel; new "Make
   a recorded video instead" CTA links to `/recipes`.
   Q-r-9 resolved.

**Q-r-2 partial resolution** (the documented gap):
Runway's SDK doesn't expose a `sendClientEvent` for
server-pushed narration. v1 narration is
operator-mediated — modal decision → operator verbally
continues. Audit row's `error_message` captures the
operator's reason server-side. In-conversation
rejection narration via a backend-pushed channel is a
v2 concern OR a Runway SDK feature request.

641 backend tests pass (unchanged). 35 SPA tests pass
(22 → 35, +13). SPA build clean.

## Drift sweep

| Category | Status |
|---|---|
| `context-kit doctor` | 0 blocking, 3 pre-existing warnings — clean |
| Stale processes | None new |
| Pending migrations | 51/51 clean |
| Frontmatter date | matches today |
| INVENTORY git_sha | Regenerated at session end against `5697269` |

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `5697269` | R8.2 feat — AvatarSessionInner + CostTicker + WebRTC fallback panel + SDK mock update for tests + 13 vitest tests + design-doc updates |
| 2 | (this commit) | SESSION 155 handoff + start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

## What R8.2 ships

### `AvatarSessionInner`

`web/src/components/avatar-session-inner.tsx`. Lives
inside `<AvatarCall>` so it can use the SDK's
`useClientEvents` hook (the hook errors if used
outside the AvatarCall provider tree).

```tsx
<AvatarCall avatarId={...} sessionId={...} sessionKey={...} audio onError={...}>
  <AvatarSessionInner onToolInvocation={handleInvokeTool} />
</AvatarCall>
```

Filters events for `type === 'client_event'` + non-empty
tool name. Normalizes `args` to a plain object (handles
null / non-object payloads from the SDK gracefully).
Calls back into the parent's `onToolInvocation(toolName,
args)` — the same callback the mock-mode debug buttons
fire. The production tool-dispatch path is now one
shared surface; the only difference between mock-mode
and real-mode is the trigger source.

### `CostTicker`

`web/src/components/cost-ticker.tsx`. Props:

```ts
{
  startedAt: string | null;     // ISO timestamp
  costPerMinuteMicros: number;  // matches IdlePanel forecast
  maxMinutes: number;           // 5 for Runway
  mockMode: boolean;            // (demo) tag in mock
}
```

`useEffect` arms `setInterval(1000)` when `startedAt`
is set; cleanup on unmount. `Date.now() - startedAt`
is the elapsed basis. Display:

```
0:30 · $0.04 (demo)
4:30 remaining
```

Tone via `data-tone`:
- **muted** (< 3 min) — neutral border / muted bg
- **amber** (3-4 min) — yellow border / yellow-50 bg
- **destructive** (4-5 min) — destructive border / destructive/10 bg

Caps at `maxMinutes * 60` seconds; displays "session
cap reached" past it (the operator should end the
session and reconnect).

Cost source: same hardcoded `$0.08/min` placeholder
R8.1's IdlePanel forecast uses. R9 plugs in real
per-provider micros-per-second lookups; the ticker
upgrades cleanly when the constant becomes
dynamic.

### WebRTC fallback panel

`ErrorPanel` (in `talk.tsx`) extended:
- New copy explains network / VPN / mic-permission
  failure modes typical of WebRTC errors.
- Two buttons:
  - **"Try again"** (existing) → flips back to `idle`.
  - **"Make a recorded video instead"** (new) → links
    to `/recipes`. Same spokesperson, same knowledge,
    no WebRTC.

`<AvatarCall onError={onSdkError}>` is now wired in
`LivePanel`. The callback bubbles up to TalkRoute,
which flips lifecycle to `{ kind: "error", message: ... }`.

**Q-r-9 resolved.**

### Q-r-2 v1 reality (the documented gap)

Tried to find `sendClientEvent` in the SDK. It's not
in the public API — the `ClientEvent` shape is
strictly avatar → SPA, not SPA → avatar.
`onClientEvent` and `useClientEvent(s)` are both
listeners. There's `clientTool(...)` for tool
definitions but its handler return value doesn't
appear to surface back as narration to the avatar's
LLM.

**v1 narration is therefore operator-mediated**:
- Avatar fires `render_video` over the data channel
- SPA's `AvatarSessionInner` catches the event
- Modal pops; operator clicks Approve or Reject
- Operator verbally continues ("go ahead" / "no")
- The audit row's `error_message` captures the
  operator's reason for retrospective review

This works because the operator is in the loop. The
modal is the audit gate; the conversation is the
narration. In-conversation backend-pushed narration is
a v2 concern (or a Runway SDK feature request — the
shape they'd need is documented in the
`AvatarSessionInner` module comment).

### Test infrastructure update

The vitest mock for `@runwayml/avatars-react` was updated
to honor `children` + `onError` props so R8.2's render
paths can be exercised hermetically:

```ts
vi.mock("@runwayml/avatars-react", () => ({
  AvatarCall: ({ children, onError: _onError }) => (
    <div data-testid="avatar-call-stub">{children}</div>
  ),
  useClientEvents: () => undefined,
}));
```

Tests can now exercise the `<AvatarCall><AvatarSessionInner/></AvatarCall>`
shape without LiveKit imports.

## Tests (13 new)

### `cost-ticker.test.tsx` (7)

| # | Test | What it covers |
|---|---|---|
| 1 | renders 0:00 + $0.00 when just started | initial render |
| 2 | advances every second | interval mechanics + dollar math |
| 3 | flips to amber 3 minutes in | tone boundary |
| 4 | flips to destructive in the last minute | tone boundary |
| 5 | caps elapsed at maxMinutes | overflow handling |
| 6 | renders (demo) tag when mockMode is true | demo indicator |
| 7 | handles null startedAt by rendering 0:00 + no interval | edge case |

Drives fake timers via `vi.useFakeTimers()` +
`vi.advanceTimersByTime(...)`. `setSystemTime` was the
gotcha — fake timers control `Date.now`, so
`advanceTimersByTime` alone is the cleaner pattern
(see calibration note #1).

### `avatar-session-inner.test.tsx` (4)

| # | Test |
|---|---|
| 1 | dispatches tool invocations to the parent |
| 2 | ignores non-client_event payloads |
| 3 | ignores events with missing tool name |
| 4 | normalizes non-object args to empty {} |

Mocks `useClientEvents` to capture the handler the
component registers, then drives synthetic payloads
through it.

### `talk.test.tsx` (2 new)

| # | Test |
|---|---|
| 1 | renders cost ticker while live (R8.2) |
| 2 | renders WebRTC fallback CTA when error panel shows (R8.2) |

## Contract rule alignment

| Rule | How R8.2 holds it |
|---|---|
| 3 (provider_session_key never leaks) | Preserved. `AvatarSessionInner` doesn't touch the key; it consumes events post-WebRTC handshake. |
| 6 (workspace-scoped tools) | Preserved. The native invocation path dispatches via the same `useInvokeTool` → backend dispatcher; workspace + tier defense-in-depth still active. |
| 7 (cost ceilings) | Cost ticker visualizes per-session minutes spend; R8.1's $0.05 per-tool approval threshold continues to gate `render_video`. |
| 9 (mock mode) | Preserved. CostTicker tags mock-mode "(demo)"; the SDK doesn't mount in mock-mode (R8.0 design); the mock debug buttons remain operative as a parallel test surface. |

## Open questions touched

* **Q-r-2 (rejection narration)** — **partial v1
  resolution**. Server-side audit (R7.0) + SPA modal
  capture (R8.1) stand. In-conversation
  backend-pushed narration deferred to v2 or a
  Runway SDK feature request (no `sendClientEvent`
  in the public API).
* **Q-r-9 (WebRTC fallback)** — **resolved**.
  `<AvatarCall onError>` callback + the "Make a
  recorded video instead" CTA on the error panel.

## Calibration moments worth carrying

### 1. Fake timers + `setSystemTime` double-count

First draft of the cost-ticker tests used both
`vi.setSystemTime(new Date(ANCHOR + 30_000))` AND
`vi.advanceTimersByTime(1000)`. Vitest fake timers
control `Date.now`; `advanceTimersByTime` ALSO
advances the clock. So at interval-fire time, the
clock read 31s elapsed instead of 30. Off-by-one
that initially looked like a state-management bug.

**Carry-forward**: when using `vi.useFakeTimers()`,
pick ONE: either `setSystemTime` for arbitrary time
jumps OR `advanceTimersByTime` for "elapse N ms +
fire any intervals that fall in the window." Mixing
them double-counts.

### 2. SDK constraints surface only when you try to use them

R7.0/R8.0/R8.1 all assumed `sendClientEvent` existed
(based on the scope-lock §"SDK contract" section).
R8.2 was the first slice that actually tried to use
it — and it doesn't exist. The narration loop story
shifted from "wire `sendClientEvent` to the resolve
callback" to "v1 narration is operator-mediated."

**Carry-forward**: when an SDK feature is named in a
scope-lock but never actually exercised by code,
treat it as a *hypothesis* rather than a *contract*.
Verify the API exists before relying on it for downstream
scope. Doesn't invalidate the scope-lock; just means
the feature is "documented intent" not "tested
reality."

### 3. Mock test surfaces that parallel production paths

Mock-mode debug buttons (R8.1) and SDK-native
invocation (R8.2) feed the SAME `onToolInvocation`
callback. The mock buttons aren't a parallel UX
universe; they're a deterministic test surface for
the same production logic. Result: every R8.1 test
indirectly exercises the R8.2 path too.

**Carry-forward**: when adding a mock UX for testing
purposes, route it through the same callback /
reducer / state machine as the production trigger.
Splitting the paths means tests on the mock path
don't catch regressions in the production path.

## Drift carryover

Nothing new.

## Project memories touched this session

None new.

## What's next (SESSION 156)

The operator-visible product story is complete at R8
close. Two operational-polish slices remain to close
R-arc; everything else is non-R cleanup or polish.

### Recommendation: R9 (cost governance backend)

R8.1's IdlePanel forecast + R8.2's CostTicker both
use hardcoded `$0.08/min × 5 min = $0.40` placeholder
constants. R9 ships:

* **Per-provider micros-per-second lookups** in
  `apps/billing/services.py` (or a new
  `apps/realtime/cost.py`). Same shape as V's
  per-primitive cost estimators (V Q-v-4).
* **Per-workspace minutes-budget enforcement** at
  session-create — already partially done by R3's
  `check_realtime_session_limit` (counts sessions per
  month), but R9 adds per-minute live tracking +
  enforcement at session-end (or via a beat task).
* **Cost-actual updates** to
  `RealtimeSession.cost_actual_micros` (currently
  always 0) from the same per-minute table the
  ticker consumes.
* **SPA hook** for the cost-forecast value — replaces
  the hardcoded constants with a backend-fetched
  estimate.

Estimated scope: ~10 backend tests + ~3 SPA tests for
the new hook. Possibly a migration if we want to
track `realtime_minutes_used` on the Subscription
shape (or compute on the fly).

### Alternatives

* **R10 (multi-provider drift verifier)** —
  smallest remaining R slice. One test that imports
  the provider registry + asserts every method is
  implemented for Runway + the mock provider.
* **Drift-prevention backlog items 2 + 3** —
  auto-bump `last_revised` on handoff write +
  TRUST_CALIBRATION promotion. Small. Pure context-
  kit / docs work.
* **F8.1 — K10 seed corpus** — blocked on
  operator-authored markdown.
* **K7.x — YouTube ingest fix** — small.
* **First marketing video** — exercise the
  whole stack end-to-end against real Runway.
  Highest-value "demo" output; needs operator to
  flip RUNWAY_FORCE_MOCK off + sit through real
  render times.
* **W11.1, K6.3, K7.1** — small backlog cleanups.

### Recommendation rationale

**R9 next** because R8.1 + R8.2 left hardcoded cost
constants in two places (IdlePanel forecast + ticker)
with explicit "R9 will upgrade this" comments. The
upgrade is the natural next step; R10 is smaller and
can ride any session, but R9 closes the cost
governance story.

If the operator wants to *flex the system end-to-end*
before more polish, **first marketing video** is the
right alternative — flips RUNWAY_FORCE_MOCK off and
walks through a real session with one of the cast
spokespeople.

## Files changed in this commit

* `docs/handoffs/SESSION_155_R8_CLOSE.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten with R8
  closure framing + SESSION 156 menu (R9 recommended).
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `5697269` SHA into the R8.2 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  git_sha: aac6ee4 → 5697269. Backend counters
  unchanged.
* `CLAUDE.md` — Phase 4 realtime-arc row updated for
  R8.2 SHIPPED + R8 closure + R-arc state R1-R8 done.

---

*Handoff written end-of-SESSION 155, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
