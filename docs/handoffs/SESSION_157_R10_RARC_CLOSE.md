---
title: "Session 157 — R10 + R-arc closes (realtime avatar arc complete)"
date: 2026-05-15
status: complete
session: 157
previous_handoff: ./SESSION_156_R9_COST_GOVERNANCE.md
---

# Session 157 — R10 multi-provider drift verifier + R-arc closes

## TL;DR

Last R slice. **R-arc closes** at this commit
(`0f71889`). All 10 + R6.1 sub-slices shipped across
SESSIONS 142-157. The realtime avatar arc is
feature-complete + cost-governed + drift-verified.

R10 is the smallest R slice: one test file, no new
code. `media-engine/tests/test_r10_provider_drift.py`
(9 tests) guards two drift surfaces:

1. **Protocol method drift** — adding a method to
   `RealtimeProvider` Protocol without implementing
   it on every concrete provider fires the test. AST
   analysis on each method's body rejects bare
   `raise NotImplementedError` stubs.

2. **Registry drift** — adding a new provider module
   (`synthesia.py`, etc.) without registering it in
   the test's `_provider_classes` + `known_modules`
   fires the package-directory test — forcing a
   code-review event before the new provider silently
   goes uncovered.

**Test totals**: Media-engine **108** (99 → 108, +9).
Django unchanged at **659**. SPA vitest unchanged at
**37**.

## Drift sweep

| Category | Status |
|---|---|
| `context-kit doctor` | 0 blocking, 3 pre-existing warnings — clean |
| Stale processes | None new |
| Pending migrations | 51/51 clean |
| Frontmatter date | `WHAT_IT_IS.md last_revised: 2026-05-15 (SESSION 155)` — current |
| INVENTORY git_sha | Regenerated against `0f71889` |

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `0f71889` | R10 feat — 9-test drift verifier + design-doc slice-table update |
| 2 | (this commit) | SESSION 157 handoff + start-here rewrite + SHA backfill + INVENTORY regen + CLAUDE.md row update |

## What R10 ships

### Drift verifier test (`media-engine/tests/test_r10_provider_drift.py`)

**Constants**:
```python
PROTOCOL_METHODS = (
    "create_session",
    "poll_session",
    "attach_documents",
    "create_document",
    "fetch_transcript",
    "end_session",
)
```

These are the 6 methods on the `RealtimeProvider`
Protocol from R2's `__init__.py`. If a future slice
adds a method, the test fails until the constant is
updated — itself an audit event.

**Provider class list**:
```python
def _provider_classes() -> list[type]:
    return [MockRealtimeProvider, RunwayRealtimeProvider]
```

Adding a future provider (Synthesia, HeyGen) is one
import + one row.

### Tests (9)

| # | Test | What it guards |
|---|---|---|
| 1 | `test_protocol_methods_match_expected_set` | Protocol surface; constant ↔ Protocol |
| 2 | `test_provider_implements_every_protocol_method[Mock]` | Mock has every method |
| 3 | `test_provider_implements_every_protocol_method[Runway]` | Runway has every method |
| 4 | `test_provider_methods_are_not_notimplemented_stubs[Mock]` | Mock methods have real bodies |
| 5 | `test_provider_methods_are_not_notimplemented_stubs[Runway]` | Runway methods have real bodies |
| 6 | `test_get_provider_returns_runway_for_known_name` | Registry returns Runway when key present |
| 7 | `test_get_provider_returns_mock_when_runway_mock_is_true` | Mock-mode override (contract rule 9) |
| 8 | `test_get_provider_raises_for_unknown_name` | Unknown names fail fast |
| 9 | `test_provider_package_only_contains_known_files` | Registry drift surface |

### AST-based stub detection

The interesting test is #4 / #5 — verifying that no
Protocol method is a bare `raise NotImplementedError`
stub. The check uses `ast.parse(inspect.getsource(method))`
and walks the function body:

* Strip leading docstring if present.
* Check the remaining body is exactly one statement.
* Check that statement is a `Raise` whose exception
  is `NotImplementedError` (bare class or
  `NotImplementedError(...)` call).

Methods with real logic that happen to raise
`NotImplementedError` deep in a branch are fine —
only bare stubs trip the assertion.

### Why this catches real drift

A real drift class at R3/R4/R5: R2 shipped 4 methods
as `raise NotImplementedError` stubs on Runway (the
scope-lock deferred them to later R-slices). R3
filled in `end_session`, R4 filled in
`attach_documents` + `create_document`, R5 filled in
`fetch_transcript`. The R10 verifier would have fired
on every commit until all four were implemented —
exactly the safety net the contract rule 8 promise
needs.

## R-arc closure summary

**SESSIONS 142-157 — the realtime avatar arc.**

| Sub-slice | Session | Commit | What it shipped |
|---|---|---|---|
| R0 | 142 | `0e01493` | Scope lock |
| R1 | 146 | `9299dcf` | RealtimeSession + RealtimeToolInvocation schema |
| R2 | 146 | `e8eb7d1` | Media-engine provider abstraction |
| R3 | 146 | `26378e9` | Django broker + tier limit gate |
| R4 | 146 | `6521451` | Knowledge → Runway document bridge |
| R5 | 146 | `885508d` | Transcript capture (Asset shape) |
| R6 | 148 | `dbb22e0` | Cross-session memory projection |
| R7.0 | 149 | `646c492` | Tool dispatch foundation |
| R7.1 | 150 | `611ae94` | Three sync tools + tier filtering |
| R7.2 | 151 | `e8564f9` | Async dispatch + render_video + INVENTORY fix |
| R7.3 + R6.1 | 152 | `b3f76cb` | attach_memory + capture_transcript helper + R6 widen |
| R8.0 | 153 | `7669007` | SPA foundation (SDK + API client + TalkRoute) |
| R8.1 | 154 | `aac6ee4` | Tool-approval modal + cost forecasting |
| R8.2 | 155 | `5697269` | SDK native invocation + cost ticker + WebRTC fallback |
| R9 | 156 | `d33b8cf` | Cost governance backend |
| R10 | 157 | `0f71889` | Multi-provider drift verifier — R-arc closes |

**16 commits, 12 sessions, R0 → R10.** The arc shipped
without a single scope-lock revision (other than the
documented R7 + R8 sub-slicings, which were operator-
confirmed at proposal time).

**Operator-visible product**: a fully-configured
spokesperson with workspace knowledge can hold a live
realtime session with:
* Knowledge grounding (R4 document composition).
* Cross-session memory (R6 + R6.1 widened query).
* Six tools the avatar can invoke mid-session (R7.0-
  R7.3): show_videos_tab, recall_knowledge,
  recall_recent_conversations, handoff_to_spokesperson,
  render_video, attach_memory.
* Tool-approval modal for over-threshold tools (R8.1).
* Live cost ticker (R8.2).
* WebRTC fallback messaging (R8.2 — Q-r-9).

**Operational guarantees**:
* Three cost-governance layers all active (R9):
  per-workspace monthly minutes budget, per-session
  length cap, per-tool approval threshold.
* Provider abstraction drift-verified (R10).
* Workspace + tier defense-in-depth at every gate
  (R7.0/R7.1).
* Contract rule 3 (`provider_session_key` never leaks)
  honored end-to-end via two Zod schemas + cache-seed
  stripping (R8.0).
* Mock-mode UX as a first-class surface (SESSION 153
  calibration).

**Open questions resolved**:
| Q-r | Resolution |
|---|---|
| Q-r-1 (session-create auth) | R3 — workspace membership |
| Q-r-2 (rejection narration) | R7.0 server-side; **partial v1**: SDK doesn't expose `sendClientEvent`; v1 narration is operator-mediated (modal decision → operator verbally continues) |
| Q-r-3 (mid-session document refresh) | Out of scope v1 |
| Q-r-4 (per-workspace tool catalog overrides) | R7.1 — tier-based filtering |
| Q-r-5 (transcript turn-level addressability) | R5 ships turn JSON shape |
| Q-r-6 (memory composition LLM) | R6 — gpt-5-mini Responses API |
| Q-r-7 (returning-operator threshold) | R6 — threshold=1 |
| Q-r-8 (cross-session tool side effects) | R7.3 — `capture_transcript` idempotent + last-write-wins |
| Q-r-9 (WebRTC fallback) | R8.2 — "Make a recorded video instead" CTA |

Only Q-r-2 remains "partial" — out of our control without a Runway SDK feature.

## Contract rule alignment (final)

All 10 R-arc contract rules from the R0 scope-lock:

1. **Every RealtimeSession has explicit workspace anchor** — R1 (FK with CASCADE).
2. **Every RealtimeSession has explicit spokesperson anchor** — R1 (FK with PROTECT).
3. **Runway API key never reaches the frontend** — R2 (broker pattern) + R8.0 (two Zod schemas).
4. **Transcripts persist as Asset rows** — R5 + R7.3 (capture_transcript helper).
5. **Knowledge integration one-way** — R4 (compose from KnowledgeDocument; never write back).
6. **Tool invocations workspace-scoped** — R7.0 (view-layer queryset filter) + R7.1 (tier defense-in-depth).
7. **Cost ceilings enforced before session-create** — R3 (session count) + R9 (minutes budget).
8. **Provider abstraction is one named adapter** — R2 (Protocol + registry) + R10 (drift verifier).
9. **Mock mode is a session-level concept** — R2 + R3 + SESSION 153 first-class UX.
10. **Conversation-thread continuity intersects K8/K9** — R1 (nullable FK; pending K-arc thread shape).

Every rule has at least one explicit test asserting it. Most have multiple.

## Calibration moments worth carrying

### 1. The R-arc as a complete case study in slice discipline

Sixteen commits over twelve sessions. Three scope-lock-
acknowledged sub-slicings (R7 → R7.0/R7.1/R7.2/R7.3;
R8 → R8.0/R8.1/R8.2; R6 → R6 + R6.1). Zero
scope-lock revisions. The arc shipped exactly the
shape the SESSION 142 scope-lock described, with
intermediate sub-slicings being adjustments to
*size* rather than *content*.

**Carry-forward**: when an arc closes cleanly like
this, capture the slice-discipline calibration that
enabled it. For R-arc the key calibrations were:
* One-slice-per-session (codified SESSION 148).
* Sub-slice at proposal time when scope-lock predates
  the discipline (SESSION 149-150).
* Pair prerequisites with consumers in one commit
  (SESSION 152's R6.1 + R7.3 pairing).
* Doc-with-commit discipline (codified SESSION 143).
* Mock-mode UX as a first-class surface
  (SESSION 153).
* Match exception payload shape across gates
  (SESSION 156).

This handoff plus `TRUST_CALIBRATION.md` form the
self-documenting "how this arc shipped" record.

### 2. The smallest closing slice has the highest signal-to-effort ratio

R10 is 321 lines (test file + design-doc updates).
Took ~45 minutes. Catches two distinct drift classes
forever. The R0 scope-lock listed R10 as the last
slice; in hindsight it could have shipped *earlier* —
not in R-arc order but as scaffolding alongside R2.
Catches drift in R3-R5 (the NotImplementedError stubs)
would have been deterministic.

**Carry-forward**: when a multi-slice arc has a "drift
verifier" or "audit" slice in the plan, ship it as
*early* scaffolding rather than late closure. The
verifier catches drift in subsequent slices; placing
it at the end means the drift class exists for the
entire intervening period.

### 3. AST-based assertions on source are tractable

The R10 NotImplementedError check uses `ast.parse(
inspect.getsource(method))` + walks the function body
to detect bare-stub pattern. Tractable, deterministic,
no false positives in practice. ~30 lines of code.

**Carry-forward**: when verifying *implementation
shape* across a registry (vs verifying *behavior*),
AST checks beat duck-typed calls. Duck-typing requires
constructing meaningful args + the method might have
real side effects. AST is hermetic.

## Drift carryover

Nothing new.

## Project memories touched this session

None new.

## What's next (SESSION 158)

R-arc closed. Several roughly-equal-priority candidates:

### Highest-value: First marketing video

Flip `RUNWAY_FORCE_MOCK` off on the media-engine.
Walk through a real session with a cast spokesperson
against real Runway. Render Sasha (or Riggs) actually
speaking a real script grounded in attached Character
OS knowledge. Operator-mediated; the AI provides
guidance + the operator executes.

This is the highest-value demonstration output now
that all 9 substantive R-slices are done. The
realtime arc is feature-complete; using it once
end-to-end against real Runway is the next milestone.

### Drift-prevention backlog (small, context-kit)

* **Item 2** — auto-bump `last_revised` on handoff
  write. Half-session of work.
* **Item 3** — promote calibration entries to
  TRUST_CALIBRATION at handoff-write time. Depends on
  item 2.

Both are small context-kit subcommand additions.
Ride a half-session each.

### Non-realtime backlog

* **F8.1 — K10 seed corpus** (blocked on
  operator-authored markdown).
* **K7.x — YouTube ingest fix.**
* **K6.3 / K7.1 / W11.1** — small cleanups.

### Recommendation rationale

**First marketing video** if the operator has time +
real Runway credit budget. The R-arc closure is
operator-visible product complete; exercising it
once end-to-end against real Runway proves it
operationally. Otherwise pick up the drift-prevention
backlog (items 2 + 3 close out SESSION 147's audit
fully).

## Files changed in this commit

* `docs/handoffs/SESSION_157_R10_RARC_CLOSE.md` —
  this file.
* `00-START-NEXT-SESSION.md` — overwritten with
  R-arc-closure framing + SESSION 158 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `0f71889` SHA into the R10 slice-table row.
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated.
  git_sha: d33b8cf → 0f71889. Counters unchanged
  (R10 is media-engine test only).
* `CLAUDE.md` — Phase 4 realtime-arc row updated for
  R10 SHIPPED + R-ARC CLOSES.

---

*Handoff written end-of-SESSION 157, paired with the
docs commit per CLAUDE.md doc-with-commit discipline.*
