---
title: "Session 153 — R8.0 SPA realtime foundation lands operator-visible"
date: 2026-05-15
status: complete
session: 153
previous_handoff: ./SESSION_152_R7_MEMORY_CLOSE.md
---

# Session 153 — R8.0 SPA realtime foundation

## TL;DR

Single-slice session shipped R8.0 — the SPA realtime
foundation. The realtime arc is now **operator-visible**:
an authenticated operator with a fully-configured
spokesperson clicks "Talk to {name}" on the detail page,
lands at `/spokespeople/:id/talk`, clicks Start, and goes
through the full lifecycle (creating → ready → live →
ended) against the backend stack that was completed in
SESSIONS 146-152.

In mock-mode (RUNWAY_FORCE_MOCK on the media-engine —
the current local-dev default), the SPA shows a "Live
(demo mode)" pill + a stub panel walking the operator
through the same lifecycle without a real WebRTC
handshake. This is the demo path; real-mode lands when
front-of-customer Runway creds are wired.

R8 was sub-sliced at proposal time per the SESSION
149-150 calibration: R8.0 / R8.1 / R8.2. R8.1 adds the
tool-approval modal + cost forecasting; R8.2 adds the
live cost ticker + WebRTC fallback messaging + tool-
rejection narration. R8.0 is enough to demo the
realtime arc end-to-end (no tool invocation UI yet,
but session lifecycle works).

641 backend tests (unchanged — R8.0 is SPA-only). SPA
vitest: 3 → 10 (+7). 1 new Playwright e2e.

## Drift sweep (per CLAUDE.md, doctor-based)

| Category | Status |
|---|---|
| `context-kit doctor` | 0 blocking, 3 pre-existing warnings — clean |
| Stale processes | None new (stack restart from SESSION 151 still healthy) |
| Pending migrations | 51/51 clean |
| Frontmatter date | `WHAT_IT_IS.md last_revised: 2026-05-15` matches today |
| INVENTORY git_sha | Regenerated at session end against `7669007` |

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `7669007` | R8.0 feat — SDK install + API client + TalkRoute + route registration + Talk CTA + 7 vitest tests + 1 Playwright spec + dev infra (jest-dom matchers wired into vitest) + design-doc updates |
| 2 | (this commit) | SESSION 153 handoff + start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

## What R8.0 ships

### SDK install

`@runwayml/avatars-react@0.16.0` (MIT, official Runway).
Pulls in `@livekit/components-react` +
`livekit-client` as transitive deps (Runway built their
realtime client on top of LiveKit). The SDK exports:

* `<AvatarCall avatarId sessionId sessionKey audio onEnd onError onClientEvent>` —
  the WebRTC handshake component. Takes the
  `(sessionId, sessionKey)` pair from the broker's
  create response.
* `<AvatarVideo>` / `<ControlBar>` / `<UserVideo>` /
  `<PageActions>` — composable surface pieces. R8.0
  only uses `AvatarCall`; R8.1 + R8.2 will compose the
  rest for control UX.
* `useAvatar()` / `useClientEvent(s)` /
  `useTranscript(ion)` — hooks for the inside-of-
  AvatarCall consumer. R8.1+ uses these for the
  tool-invocation surface.

### API client (`web/src/lib/api/realtime.ts`)

Three operations:

```ts
createRealtimeSession({ spokesperson, personality?, start_script?, title? })
  → POST /api/realtime_sessions/
  → returns RealtimeSessionWithKey (includes provider_session_key)

useRealtimeSession(id)
  → GET /api/realtime_sessions/<id>/
  → returns RealtimeSession (NO provider_session_key)
  → polls every 1500ms while status ∈ {creating, not_ready}

endRealtimeSession(id)
  → POST /api/realtime_sessions/<id>/end/
  → returns RealtimeSession (ENDED)
```

Two Zod schemas: `sessionSchema` (standard, no key) and
`sessionWithKeySchema` (extends, with key). The latter
is used ONLY for the create response. **Contract rule 3
honored end-to-end**: the SPA never sees the key from
any endpoint except create, and `useCreateRealtimeSession`
strips the key from the cache seed before storing the
row in React Query's cache.

### TalkRoute (`web/src/routes/spokespeople/talk.tsx`)

Lifecycle state machine:

```
       ┌─────── error (from any state via try/catch)
       │
idle ──▶ creating ──▶ ready ──▶ live (visual state, same as ready)
                        │
                        ▼
                      ended
```

Each lifecycle state has its own panel component:

* **IdlePanel** — "Start session" button + brief
  explanation of what's about to happen.
* **CreatingPanel** — spinner + "Composing the document
  + connecting to Runway…".
* **LivePanel** — live indicator pill (mock or real) +
  End button + either `<AvatarCall>` (real-mode) or
  `MockSessionPanel` (mock-mode) + session metadata.
* **EndedPanel** — duration + "Start another" /
  "Back to spokesperson" CTAs.
* **ErrorPanel** — error message + "Try again" → flips
  back to idle.

### Mock-mode UX (load-bearing for the demo)

When `session.mock_mode === true` (broker returns this
when `RUNWAY_FORCE_MOCK=1` on the media-engine):
* `LiveIndicator` renders the "Live (demo mode)" pill
  (yellow, no pulse) instead of "Live" (emerald,
  pulsing).
* `LivePanel` renders `MockSessionPanel` instead of
  `<AvatarCall>`. The mock panel shows provider session
  id + document id so the operator can verify the
  backend composed everything correctly.
* End flow still works — broker fires R5's transcript
  capture Celery task on the mock provider id; the task
  hits the media-engine which returns a deterministic
  stub transcript; transcript Asset lands in the
  workspace.

This means the realtime arc is **fully demonstrable
end-to-end in mock mode**:
1. Spokesperson + workspace + knowledge attached.
2. Click "Talk to {name}" CTA on detail page.
3. Click Start → backend composes document (R4) +
   memory (R6 / R6.1) + creates session (R3) → SPA
   lands in live mock-mode panel.
4. Click End → broker fires R5 transcript capture →
   transcript Asset persists in workspace.
5. Next session (Start again) → R6 picks up the prior
   transcript → composes memory into the new session's
   grounding document.

### Routing + CTA

`App.tsx`:

```diff
+ <Route path="/spokespeople/:id/talk" element={<RequireAuth><TalkRoute /></RequireAuth>} />
  <Route path="/spokespeople/:id" element={<RequireAuth><SpokespersonDetailRoute /></RequireAuth>} />
```

**Order matters** — `:id/talk` must register BEFORE
`:id` so React Router doesn't swallow `talk` as a UUID
parameter.

Spokesperson detail page gains a `TalkCta` section
between `IdentityPanel` and the videos/setup panels.
Renders ONLY for fully-configured spokespeople (the
`allDone` branch). Why: the broker's create endpoint
(R3) rejects sessions without `runway_avatar_id`;
routing through the CTA guarantees the precondition.
Partially-configured spokespeople still see their
existing setup callouts; no surprise 400 in the talk
route.

## Tests

### Vitest (`web/src/routes/spokespeople/talk.test.tsx`)

| # | Test | What it covers |
|---|---|---|
| 1 | `renders idle state with Start button` | initial render |
| 2 | `transitions to live with mock-mode pill after Start` | mock-mode UX (the load-bearing path) |
| 3 | `mounts the SDK in real (non-mock) mode` | real-mode path (proves the SDK mount happens when expected) |
| 4 | `transitions to ended after End` | end flow |
| 5 | `shows error panel when create fails` | error path |
| 6 | `renders skeleton while spokesperson loads` | loading shell |
| 7 | `renders fatal error when spokesperson 404s` | edge case |

SDK + API client both mocked. `vi.mock("@runwayml/avatars-react", ...)` stubs `AvatarCall` as a tiny `<div data-testid="avatar-call-stub" />` so the tests don't import LiveKit at module load.

### Playwright (`web/e2e/realtime-talk.spec.ts`)

One spec — sign up + navigate to `/spokespeople/<fake-uuid>/talk` → assert `talk-fatal-error` testid is visible. Guards route registration regressions.

Full create-flow Playwright spec deferred: it requires a seeded spokesperson with `runway_avatar_id`, which the wizard-driven flow doesn't expose cleanly to e2e. R8.1 will add a seeded-fixture spec once the broader test fixture surface is in place (likely a small Django management command that seeds a cast member by name).

### Dev infra

Two devDeps + one setup file added to unblock the
testing-library API:

* `@testing-library/user-event@14.6.1` — drives user
  interactions in unit tests (click / type / keyboard).
* `web/vitest.setup.ts` — imports
  `@testing-library/jest-dom/vitest` so matchers like
  `toBeInTheDocument`, `toHaveAttribute`,
  `toHaveTextContent` are available on `expect`.
* `web/vitest.config.ts` — wires the setup file via
  `setupFiles: ["./vitest.setup.ts"]`.

Previously vitest worked only for the existing
`auth.test.ts` (no DOM matchers used). The wider
testing-library API now works for all SPA unit tests.

## Contract rule alignment

| Rule | How R8.0 holds it |
|---|---|
| 3 (provider_session_key never leaks) | Two Zod schemas; `provider_session_key` lives only in the create-response shape. `useCreateRealtimeSession` strips the key from the cache seed. The key lives in React state for the session lifetime; never persisted, never re-fetched. |
| 5 (knowledge integration one-way) | SPA is a read-side consumer for the doc body composition; doesn't write to KnowledgeDocument. |
| 7 (cost ceilings) | Backend's tier-limit gate already enforces session creates against monthly minutes cap (R3). SPA doesn't bypass — it goes through the standard `POST /api/realtime_sessions/`. |
| 9 (mock mode) | Mock-mode UX is the load-bearing demo path. SPA detects via `session.mock_mode` on the create response. |

## Open questions touched

* **Q-r-2 (rejection narration)** — server-side
  resolved R7.0; SPA wiring lands in R8.2.
* **Q-r-9 (WebRTC fallback)** — not touched. R8.0
  surfaces SDK errors via the existing error panel;
  R8.2 adds the "fall back to recorded video" CTA.

## Calibration moments worth carrying

### 1. Mock-mode UX is the demo path

The decision to make mock-mode a **first-class UX
state** (not just "the SDK fails silently") rather
than gating the SPA on real Runway creds turned out
to be load-bearing for the demo. Now: the operator can
walk through the *entire* realtime arc end-to-end
locally — backend create-session, knowledge
composition, memory projection, transcript capture —
without ever touching real Runway. That's the right
shape for a v1 demo where customer signups happen
before customer Runway accounts exist.

**Carry-forward**: when a feature has a real-vs-mock
toggle on the backend (and we have *six* of those:
RUNWAY, EMBEDDING, RENDER_SCRIPT, CONVERSATION_REPLY,
SERPER, REALTIME_MEMORY), the SPA should render
mock-mode as an explicit UX state with its own
indicator. "Demo mode" pill is more honest than
silent fallback + helps the operator audit what's
real vs simulated.

### 2. Route precedence matters before React Router 7's "static beats dynamic"

`react-router-dom@7.1.1` does prefer static segments
over dynamic ones, but only within the same Route
definition. Two sibling Routes — `:id/talk` and `:id` —
need to be registered in the right order or the first
match wins. Lost ~5 minutes to this debugging the
wrong route taking over.

**Carry-forward**: when adding nested-shaped routes
to an existing `:id` parameter, ALWAYS put the more
specific path first. Document this once in
SPA_ARCHITECTURE.md if not already there.

### 3. Vitest setup files are easy to forget until you need them

The repo had `@testing-library/jest-dom` in devDeps
since SESSION 116 but never wired its matchers via a
vitest setup file. The single existing test
(`auth.test.ts`) didn't use any of those matchers, so
the gap stayed invisible. R8.0's tests immediately
exercised the gap — `toBeInTheDocument` is the most
basic testing-library matcher.

**Carry-forward**: when adding a SECOND consumer of a
test framework's plugin surface, audit the setup
config. Vitest + Playwright + RTL share a "works if
configured" problem; one-file consumers paper over the
gap.

## Drift carryover from SESSION 152

Nothing new. All R6/R7-arc questions either
resolved or scheduled (R8.1 / R8.2 absorb the
remaining UI-layer Q-r questions).

## Project memories touched this session

None new.

## What's next (SESSION 154)

### Recommendation: R8.1 (tool-approval modal + cost forecasting)

Two visible pieces:

**Tool-approval modal**:
* When the avatar's LLM invokes a tool that returns
  `state=awaiting_approval` (today: `render_video`),
  the SPA needs to render a modal: "Sasha wants to
  render a 30-second ad — cost ~$0.08. Approve /
  Reject?"
* Approve → POST `/api/realtime_tool_invocations/<id>/approve/` → result feeds back to the avatar via `sendClientEvent`.
* Reject → POST `.../reject/` with optional `reason`
  → result narrated via `sendClientEvent` so the
  avatar's LLM can apologetically pivot.
* The SDK's `useClientEvent` hook is the seam — it
  receives the tool-invocation event from the avatar's
  data channel.

**Cost forecasting**:
* Before session-start: "~$X for a 5-min session" pill
  next to the Start button. Pulls from R3's tier-limit
  surface (`realtime_sessions_per_month` + Runway
  per-minute cost estimate).
* Source-of-truth: the existing
  `apps.billing.services.get_usage(workspace)` Usage
  shape already returns the realtime cap; R9 (cost
  governance backend) refines the per-minute estimate.
  R8.1 can ship with a hardcoded `$0.08/min`
  conservative estimate and refine after R9.

Estimated scope: ~6-8 unit tests + 1-2 Playwright
specs, no backend changes (R7.0's `awaiting_approval`
flow is the contract).

### Alternatives

* **R8.2 (live cost ticker + error paths +
  rejection narration)** — close R8 in one more
  session, then R9 + R10.
* **R9 (cost governance backend)** — per-workspace
  minutes budget enforcement at session-create.
  Could land between R8.1 + R8.2 to feed the
  cost-forecasting UI with real data instead of a
  hardcoded estimate.
* **R10 (provider hardening)** — small.
* **Drift-prevention backlog items 2 + 3** — small.
* **F8.1 / K7.x** — non-realtime palette cleansers.

### Recommendation rationale

**R8.1 next**. The tool-approval modal is the
single highest-value piece of R8 — without it,
`render_video` (the threshold-crossing tool) can't
fire from the SPA. Cost forecasting rides in the
same slice because it shares the modal's billing
data shape.

R9 could land before R8.1 to give the cost forecast
a real number, but the dependency direction is
inverted — R8.1's UI can ship with a placeholder
estimate and gracefully upgrade when R9 lands.
Shipping R8.1 first keeps the operator-visible
arc moving.

## Files changed in this commit

* `docs/handoffs/SESSION_153_R8_SPA_FOUNDATION.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten with R8.0
  outcome + R8.1 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `7669007` SHA into the R8.0 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  git_sha: b3f76cb → 7669007. Backend counters
  unchanged (R8.0 is SPA-only); inventory doesn't
  track web/ LOC.
* `CLAUDE.md` — Phase 4 realtime-arc row updated for
  R8.0 SHIPPED + R8 sub-slice breakdown.

---

*Handoff written end-of-SESSION 153, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
