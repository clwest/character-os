---
title: "Session 156 — R9 cost governance backend (closes hardcoded-constants gap)"
date: 2026-05-15
status: complete
session: 156
previous_handoff: ./SESSION_155_R8_CLOSE.md
---

# Session 156 — R9 cost governance backend

## TL;DR

Two-phase session:

**Phase 1 — milestone-level doc refresh** (commit
`a632aef`). After R8 closed in SESSION 155, the
narrative anchor (`WHAT_IT_IS.md`) was 9 sessions stale
and TRUST_CALIBRATION ended at SESSION 147's drift
audit. Refreshed both — `WHAT_IT_IS.md` now reflects the
4-arc state (3 complete, R-arc operator-visible) and
points at INVENTORY + start-here as canonical sources
for per-slice detail. 4 new TRUST_CALIBRATION entries
promoted from per-session handoffs (R7/R8 sub-slicing
discipline, `sendClientEvent`-doesn't-exist, jest-dom
type-vs-runtime drift, fake-timer double-count).

**Phase 2 — R9 cost governance backend** (commit
`d33b8cf`). Three layers of cost governance from the
scope-lock now all active:

1. **Per-workspace monthly minutes budget** (this
   slice). `check_realtime_minutes_budget` fires
   alongside R3's session-count gate.
2. **Per-session length cap** (provider-enforced;
   CostTicker visualizes).
3. **Per-tool approval threshold** (R7.0).

R8.1's IdlePanel cost forecast + R8.2's CostTicker no
longer use hardcoded constants — both pull from the new
`GET /api/realtime_sessions/cost_estimate/` endpoint
via the `useRealtimeCostEstimate` hook.

659 backend tests pass (641 → 659, +18 R9). 37 SPA
vitest tests pass (35 → 37, +2 R9). SPA build clean.

**R-arc state: R1-R9 done.** R10 (multi-provider drift
verifier) is the last R slice — small one-test
follow-up.

## Drift sweep

| Category | Status |
|---|---|
| `context-kit doctor` | 0 blocking, 3 pre-existing warnings — clean |
| Stale processes | None new |
| Pending migrations | 51/51 clean |
| Frontmatter date | `WHAT_IT_IS.md last_revised: 2026-05-15 (SESSION 155)` — bumped this session |
| INVENTORY git_sha | Regenerated at session end against `d33b8cf` |

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `a632aef` | docs: refresh `WHAT_IT_IS.md` for SESSIONS 148-155 (frontmatter, four-arc framing, per-arc state) + 4 new TRUST_CALIBRATION entries |
| 2 | `d33b8cf` | R9 feat — `apps/realtime/cost.py` + TIER_LIMITS `realtime_minutes_per_month` + `check_realtime_minutes_budget` + broker cost stamps + cost_estimate endpoint + SPA hook + IdlePanel/LivePanel wiring + 18 backend tests + 2 SPA tests |
| 3 | (this commit) | SESSION 156 handoff + start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

## What R9 ships

### Backend

**`apps/realtime/cost.py`** — new module:

```python
def cost_per_minute_micros(provider: str) -> int       # default 80_000 for runway
def estimate_session_cost_micros(provider, minutes=5) -> int
def actual_session_cost_micros(session) -> int          # from session.duration_seconds
PROVIDER_MAX_SESSION_MINUTES = 5
```

Per-provider rate table (`_PROVIDER_RATES`) — one entry
for `runway` at $0.08/min today. Adding a future
provider (Synthesia, HeyGen) is one row here; the
broker + SPA stay stable. Defensive default for
unknown providers matches the rate (no
free-tier-by-mistake on misconfigured workspace).

**TIER_LIMITS** in `apps/billing/models.py`:

| Tier | sessions/mo | **minutes/mo (R9)** |
|---|---|---|
| starter | 5 | **30** |
| pro | 20 | **120** |
| agency | unlimited | **unlimited** |

The session-count gate stays for coarse abuse
prevention; the minutes gate catches long-talkers that
session-count would miss.

**`Usage` shape** in `apps/billing/services.py`:

New fields: `realtime_minutes_used` (sums
`RealtimeSession.duration_seconds` across the period,
rounds up to whole minutes) + `realtime_minutes_limit`.
Surfaced in `to_dict()`.

**`check_realtime_minutes_budget(workspace,
requested_minutes=5)`** — new gate. Fires alongside
`check_realtime_session_limit` in the broker's create
flow. Either can independently veto with 402.
Raises `TierLimitExceeded` with
`code='realtime_minutes_limit_reached'` payload
including current usage + cap + suggested upgrade
tier.

**Broker create** (`apps/realtime/views.py`):
* After successful media-engine create, stamps
  `session.cost_estimate_micros =
  estimate_session_cost_micros(provider)` — full
  session cap × per-minute rate.
* Calls `check_realtime_minutes_budget` alongside the
  existing `check_realtime_session_limit`.

**Broker `_end_session`**:
* Stamps `session.cost_actual_micros =
  actual_session_cost_micros(session)` from the final
  `duration_seconds`.

**`GET /api/realtime_sessions/cost_estimate/`** — new
`@action(detail=False)` on `RealtimeSessionViewSet`.
Query params: `workspace` (optional UUID) + `provider`
(optional). Response shape:

```json
{
  "provider": "runway",
  "cost_per_minute_micros": 80000,
  "max_session_minutes": 5,
  "monthly_minutes_used": 12,
  "monthly_minutes_limit": 30,
  "monthly_minutes_remaining": 18,
  "tier": "starter"
}
```

Cross-workspace access → 404 (don't leak workspace
existence).

### SPA

**`useRealtimeCostEstimate`** hook in
`web/src/lib/api/realtime.ts`:

```ts
const cost = useRealtimeCostEstimate({ workspaceId });
// cost.data: RealtimeCostEstimate (Zod-validated)
```

`staleTime: 60s` — cost data rarely changes
intra-session; refetch on workspace switch or page
reload.

**TalkRoute** — pulls the hook value, passes
`costPerMinuteMicros` + `maxSessionMinutes` +
`minutesRemaining` + `minutesLimit` into IdlePanel +
LivePanel.

**IdlePanel** — replaces the hardcoded
`ESTIMATED_COST_PER_MINUTE_MICROS` /
`PROVIDER_MAX_SESSION_MINUTES` with the hook values.
New "X of Y min left this month" hint pill
(`data-testid="minutes-remaining"`) renders only for
capped tiers. Falls back to `FALLBACK_*` constants
when the hook hasn't resolved or errored — don't
strand UX on a transient billing endpoint failure.

**LivePanel + CostTicker** — `costPerMinuteMicros` +
`maxSessionMinutes` now come from the hook. The
ticker's per-second math uses real backend rates.

### Test totals

* **Backend**: 641 → 659 (+18). New file
  `apps/realtime/tests/test_r9_cost.py`. ALLOWED_FILES
  whitelist addition.
* **SPA**: 35 → 37 (+2). Tests in
  `talk.test.tsx` cover the hook path (backend cost
  visible) + the unlimited-tier path (no hint).
* SPA build clean (1774 modules).

## Contract rule alignment

| Rule | How R9 holds it |
|---|---|
| 7 (cost ceilings) | **Now fully load-bearing**. All three layers active: per-workspace minutes budget (this slice) + per-session length cap (provider) + per-tool approval threshold (R7.0). |
| 1 (workspace anchor) | Preserved. Cost rates per-provider; usage scoped per-workspace via the spokesperson → workspace FK chain. |
| 9 (mock mode) | Preserved. Cost stamps land regardless of mock vs real; the rate is what matters for the math, and `RUNWAY_FORCE_MOCK` doesn't change pricing semantics. |

## Open questions touched

* **Q-r-7 (returning-operator threshold)** — resolved
  R6 (threshold = 1). R9 doesn't touch this.
* No other Q-r questions touched.

## Calibration moments worth carrying

### 1. Milestone-level doc refresh has its own cadence

R8 close (SESSION 155) was a logical milestone, not
just another slice. The per-slice doc-with-commit
discipline (codified SESSION 143) handled
`REALTIME_AVATAR_V1.md` + `INVENTORY` + start-here +
handoffs at slice granularity, but `WHAT_IT_IS.md` and
`TRUST_CALIBRATION.md` were drifting — 9 sessions stale
each.

**Carry-forward**: at arc closures (R-arc done, V-arc
done, K-arc done...), pair the slice-close commit with
a milestone-level refresh of the narrative anchor + the
calibration ledger. The narrative anchor is the
"orient" doc; the ledger is the "what did we learn"
doc. Neither lives on the per-slice cadence.

### 2. Backend gates with structured exit payloads pay UI dividends later

R3's `check_realtime_session_limit` shipped a
structured `TierLimitExceeded` payload (code +
message + current + limit + suggested_tier). R9's
`check_realtime_minutes_budget` mirrored the shape
exactly. Same surface, two gates, one error contract.
The SPA's existing handling (R3 era) needs zero
changes to also surface the new gate's failures.

**Carry-forward**: when adding a gate to an existing
gate's surface (same view, same response semantics),
match the existing exception payload's shape literally.
The cost of consistency at the boundary is low; the
cost of UI divergence later is high. Verified twice
this session — the broker + the SPA both treat the
two gates identically because the payloads agree.

### 3. Hardcoded UI constants that match a backend default are a smell

R8.1 shipped `ESTIMATED_COST_PER_MINUTE_MICROS =
80_000` as a placeholder, with an explicit "R9 will
ship the real value" comment. R8.2 shipped the
CostTicker against the same constant. By R9 there were
two SPA consumers of the same magic number — drift
risk. R9 replaced both with a backend-fetched value +
left `FALLBACK_*` constants for the transient-error
case.

**Carry-forward**: when a placeholder constant lands
in the SPA with a "next slice will replace this"
comment, treat it as a TODO not a contract. The
backend endpoint that supplies the real value should
have shipped before the second consumer of the
constant. Counter-example: the FALLBACK_* pattern is
fine if the constant is explicitly the
graceful-degradation path; the smell is
"hardcoded-because-we-haven't-built-it-yet."

## Drift carryover

Nothing new.

## Project memories touched this session

None new.

## What's next (SESSION 157)

### Recommendation: R10 (multi-provider drift verifier)

The last R slice. One-test slice. Verifies the
provider abstraction (scope-lock §"Provider
abstraction" + R2's `RealtimeProvider` Protocol)
stays honored as new providers land.

Implementation shape:
* New `apps/realtime/tests/test_r10_provider_drift.py`
  — imports the provider registry from
  `media-engine/app/services/realtime_provider/`,
  asserts every method on the Protocol is implemented
  by Runway + the mock provider. Fails the test if
  a new method lands on the Protocol without a Runway
  implementation, OR if a future provider lands
  without all methods.
* No new code beyond the test.

Estimated scope: ~30 minutes. Closes R-arc fully.

### Alternatives

* **First marketing video** — flips RUNWAY_FORCE_MOCK
  off, walks through a real session with a cast
  spokesperson against real Runway. Operator-mediated.
  Highest-value "demonstration output" remaining; needs
  the operator to sit through real render times.
* **Drift-prevention backlog items 2 + 3** —
  auto-bump `last_revised` on handoff write +
  TRUST_CALIBRATION promotion at handoff-write.
  Context-kit work; small.
* **F8.1 — K10 seed corpus** — blocked on operator
  markdown.
* **K7.x — YouTube ingest fix**.
* **K6.3 / K7.1 / W11.1** — small cleanups.

### Recommendation rationale

**R10 next** to close R-arc fully. After R10, the
realtime arc is done across all 10 slices in the
scope-lock. R10 is small; ride it solo or bundle with
one of the backlog cleanup items (item 2 + 3 are
similar "small context-kit work" shape).

If the operator wants a *demonstrable real Runway
session* now that all 9 substantive R-slices are done,
**first marketing video** is the right next move
operationally. R10 doesn't block that.

## Files changed in this commit

* `docs/handoffs/SESSION_156_R9_COST_GOVERNANCE.md` —
  this file.
* `00-START-NEXT-SESSION.md` — overwritten with R9
  outcome + R10 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `d33b8cf` SHA into the R9 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  git_sha: 5697269 → d33b8cf. Shell LOC: 39,278 →
  39,949 (+671) in 206 → 208 files (+2: cost.py +
  test_r9_cost.py).
* `CLAUDE.md` — Phase 4 realtime-arc row updated for
  R9 SHIPPED + the three-cost-layer framing + R-arc
  state R1-R9 done.

---

*Handoff written end-of-SESSION 156, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
