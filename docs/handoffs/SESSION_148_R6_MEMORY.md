---
title: "Session 148 — R6 cross-session memory shipped"
date: 2026-05-15
status: complete
session: 148
previous_handoff: ./SESSION_147_DRIFT_AUDIT.md
---

# Session 148 — R6 cross-session memory shipped

## TL;DR

Single-slice session. R6 (cross-session memory) shipped
end-to-end in one feat commit + this docs commit.
Avatar now opens warm: prior `Asset(TRANSCRIPT)` rows
from R5 get summarized via gpt-5-mini and projected
into the next session's Runway document as a
`## Recent Conversations` section. Returning-operator
loop closes. 14 new tests; 574 backend pass; no
migrations; no new Celery tasks; zero new persistence.

R-arc state: **R1-R6 done; R7-R10 remain.**

Pre-session drift sweep (the new CLAUDE.md discipline
codified SESSION 147) ran clean operationally —
migrations 49/49, fresh media-engine. Two minor doc
drifts noted (WHAT_IT_IS frontmatter says "SESSION 146"
where the latest handoff is SESSION 147 — same date so
the strict date-comparison rule reads clean; INVENTORY
two docs-only commits behind HEAD). Neither blocking;
both await the `context-kit drift` subcommand (handled
by a parallel agent on context-kit's own repo) before
they get programmatic detection.

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `dbb22e0` | R6 — `realtime_memory.py` + `realtime_document.py` extension + 14 tests + 3 `ALLOWED_FILES` whitelist additions + `REALTIME_AVATAR_V1.md` slice-table + change-log update |
| 2 | (this commit) | SESSION 148 handoff + `00-START-NEXT-SESSION.md` rewrite + back-fill `dbb22e0` SHA in the design doc + CLAUDE.md Phase 4 row bump |

INVENTORY regeneration **intentionally skipped** —
R6 didn't change any model / route / Celery task, so
the CLAUDE.md rule "regen INVENTORY when those change"
doesn't fire. The `git_sha` drift between INVENTORY
and HEAD inherits SESSION 147's deferred-bug situation
(two known inventory-generator bugs); will resolve
when SESSION 147 backlog item 5 lands.

## What R6 ships

### Code

**New** — `shell/character_os/realtime_memory.py` (267
lines). Mirrors `script_synthesis.py` (K6) +
`conversation_synthesis.py` (K9) shape line for line:

* `MemoryResult(body, session_ids, used_synthesis,
  model, tokens_input, tokens_output)` — dataclass
  with `slots=True`.
* `compose_session_memory(spokesperson, *,
  max_sessions=3)` — never raises, returns empty
  result on degradation paths.
* `_is_force_mock()` honors the same env-or-settings
  pattern as RUNWAY / EMBEDDING / RENDER_SCRIPT /
  CONVERSATION_REPLY / SERPER flags.
* `_call_responses_api()` uses
  `client.responses.create` (Responses API, **not**
  chat-completions) per the project memory at
  `~/.claude/projects/.../feedback_openai_gpt5_responses_api.md`.
* `PER_TRANSCRIPT_CHAR_BUDGET = 4_000` caps how much
  of each prior transcript feeds the synthesizer —
  one long session can't blow the input budget.

**Edited** — `shell/character_os/realtime_document.py`:

* Imports `compose_session_memory` at module top.
* `RealtimeDocumentResult` gains
  `memory_session_ids: list[str] = field(default_factory=list)`.
* New memory block assembled between `## About` and
  `## Knowledge`, gated on the 40k budget. The drop
  rule is explicit: if memory candidate length +
  reserved knowledge-header space > `max_chars`,
  log + skip the section.
* Knowledge assembly accounts for memory block in its
  budget tracker (`current_chars` initialization).

### Tests

`shell/apps/realtime/tests/test_r6_session_memory.py`
(388 lines, 14 tests). Coverage matrix:

| Test | Path |
|---|---|
| `test_no_prior_sessions_returns_empty_memory` | empty input |
| `test_force_mock_returns_deterministic_stub` | force-mock |
| `test_single_prior_session_summarized` | real-mode (patched API) |
| `test_multiple_prior_sessions_ordered_newest_first` | ordering |
| `test_max_sessions_cap_respected` | `max_sessions` kwarg |
| `test_ended_session_without_transcript_excluded` | ENDED filter |
| `test_non_ended_sessions_excluded` | status filter |
| `test_missing_openai_key_degrades_to_empty` | no-key path |
| `test_openai_failure_degrades_to_empty` | api-failure path |
| `test_other_workspace_sessions_excluded` | privacy (rule 1) |
| `test_composer_injects_memory_section_when_present` | integration |
| `test_composer_no_memory_section_when_no_history` | integration |
| `test_composer_drops_memory_first_under_budget` | priority order |
| `test_composer_no_knowledge_with_memory` | empty-knowledge case |

Mock approach mirrors K6 — patch
`character_os.realtime_memory._call_responses_api`
rather than the OpenAI SDK directly. Hermetic.

### Whitelist updates

Three cross-arc isolation guards needed
`ALLOWED_FILES` additions for the new test file:

* `apps/realtime/tests/test_isolation.py` —
  RealtimeSession writer guard.
* `apps/compositions/tests/test_isolation.py` —
  Asset writer guard (R6 tests seed
  `Asset(TRANSCRIPT)` rows directly).
* `apps/embeddings/tests/test_retrieval_privacy.py`
  — KnowledgeChunk reader guard (the composer
  integration tests seed chunks).

This matches the cross-arc isolation calibration
moment from SESSION 146's four-failure-mode bundle.
Pattern is intentional — any new test that touches
cross-arc resources is expected to be whitelist-
visible.

## Contract rule alignment

| Rule | How R6 holds it |
|---|---|
| 1 — workspace anchor | Memory query filters by `spokesperson` (carries `workspace_id`); cross-workspace transcripts never enter the projection. Verified by `test_other_workspace_sessions_excluded`. |
| 4 — Asset shape | Reads existing `Asset(TRANSCRIPT)` rows R5 persists. Zero new persistence shape. |
| 5 — knowledge integration one-way | Memory composition reads transcripts (the conversation history surface). It does not write to KnowledgeDocument. |
| 9 — mock mode | `REALTIME_MEMORY_FORCE_MOCK` shape matches the five existing flags. Settings beats env. |

## Open questions resolved this session

* **Q-r-7 (returning-operator threshold).** Set to 1
  — any prior `Asset(TRANSCRIPT)` triggers memory
  projection. No operator opt-out in v1; deferred
  to R8 SPA workspace settings.

Remaining open questions (Q-r-1, Q-r-2, Q-r-3,
Q-r-4, Q-r-5, Q-r-6, Q-r-8, Q-r-9) untouched by R6
— they sit with R3 (auth granularity), R7 (tool
approval UX + tool catalog overrides), R5 (turn
addressability — already resolved), R6 (LLM choice
— resolved to gpt-5-mini in this slice), and R8
(WebRTC fallback).

## Drift carryover (from SESSION 147 backlog)

Two items revisited briefly at session start:

1. **Stale processes**: `runserver` PID 60921 +
   `celery` PID 27253 from May 14 22:22 / 23:41. Both
   predate the latest `shell/` commit (`885508d`,
   SESSION 146 / May 15). Could be stale or just old
   reload children — process-age vs commit-age is
   exactly what the `context-kit drift` subcommand
   will productise. **Not fixed this session** —
   no operational complaint; defer to the drift
   subcommand's first run.

2. **INVENTORY git_sha vs HEAD**: 354ccf5 vs 30ad02a
   at session start (2 commits behind, both
   docs-only). This commit adds a third docs
   commit; INVENTORY will be 4 behind by end of
   session. None of the gap-spanning commits change
   models / routes / Celery tasks, so the CLAUDE.md
   regen rule doesn't trigger. **Operator's
   end-of-session ask: revisit the inventory regen
   after R6 ships** — will run
   `python manage.py inventory` in the next
   immediate step and either commit if the diff is
   useful or note that nothing of substance changed.

## Calibration moments worth carrying

### 1. Cross-arc isolation guards keep paying for themselves

Every new test file that touches multi-arc resources
hits 1-3 isolation guards. SESSION 146 surfaced this
as a "ALLOWED_FILES gap" failure mode; SESSION 148
hit the same gap three times (realtime + compositions
+ embeddings). **The pattern is so reliable it could
be a pre-commit hook** — but only if the gap is the
exception, not the rule. For now: the explicit
failure + whitelist-update flow is correct (high
salience: every test author has to think about which
arcs they're crossing).

**Carry-forward**: when adding a new test file to an
arc, anticipate that it will need to land in 1-3
`ALLOWED_FILES` lists. Budget that into the slice
plan rather than discovering at test-run time. The
slice-plan section of this handoff already does this
implicitly; future slice plans should call it out
explicitly.

### 2. Test budget arithmetic is fiddly; iterate on the actual numbers

`test_composer_drops_memory_first_under_budget` failed
on the first run because I set `max_chars=400`, not
realizing the mock memory body (~260 chars) plus
header + small knowledge chunk all fit. Tightened to
`max_chars=250` after computing the exact byte budget
from the mock-body shape. **The lesson is not
"compute before writing"** (that adds friction); it
is **"iterate on the actual numbers when the test
fails"** — the test was diagnosable from the failure
output (the body shown contained both sections), and
the right fix was three-line tighten not a redesign.

**Carry-forward**: synthetic-budget tests should
land with the smallest budget that still asserts the
drop, not a generously-large one. The smaller the
budget, the less the test depends on incidental mock
body length.

### 3. The handoff discipline + per-slice doc update keeps cost low

CLAUDE.md SESSION 143 codified the doc-with-commit
discipline. This session: ran the discipline
naturally — slice-table marked SHIPPED, change-log
entry added, handoff written same-session as the
feat commit. **The discipline holds when the slice
is single-focus.** When a session ships multiple
slices (SESSION 143 shipped V3-V13 in one extended
session), the per-slice update lapses and the catch-
up cost compounds. Sub-text: **one slice per session
is the natural unit when the discipline is honored.**

**Carry-forward**: when the operator asks "can we
also ship X" mid-session, the answer is generally
"next session" unless X is genuinely small + the
current slice is done. R6 + R7 in one session would
have re-created the SESSION 143 catch-up pattern.

## Project memories touched this session

None new. The OpenAI gpt-5 Responses API memory
(`feedback_openai_gpt5_responses_api.md`) anchored the
LLM call site for R6 — third call site after K6 + K9.
Three is enough to confirm the pattern; no new memory
needed.

## What's next (SESSION 149)

Pick one. R-arc continues; the realtime arc still
needs three feature slices before it surfaces to the
operator.

### Option A — R7 (tool catalog, recommended)

Six workspace-scoped tools the avatar can invoke
mid-session: `recall_knowledge`, `render_video`,
`recall_recent_conversations`, `attach_memory`,
`show_videos_tab`, `handoff_to_spokesperson`.
`RealtimeToolInvocation` row already exists (R1).
R7 ships:

* `apps/realtime/tools/` registry + per-tool
  handlers (workspace-scoped routing).
* WebRTC data-channel event handler in the broker
  (or a media-engine surface — TBD; the SDK shape
  determines which side handles dispatch).
* Approval-threshold modal contract (server-side
  shape only; SPA surface lands in R8).

Resolves Q-r-2 (tool rejection narration) and Q-r-4
(per-workspace tool catalog overrides).

### Option B — R8 (SPA, the "feels real" moment)

`/spokespeople/:id/talk` route + `@runwayml/avatars-
react` integration + cost forecasting UI + tool-
approval modal + live cost ticker. The backend is
fully ready (R1-R6 all done); R8 is where the arc
becomes operator-visible.

R8 without R7 ships a session with no tools — the
avatar can still talk, just can't render videos or
recall knowledge live. Acceptable for an early demo;
the launch-ready version needs R7 first.

### Option C — R9 (cost governance)

Per-workspace minutes budget + live cost ticker.
R3's tier-limit gate (`check_realtime_session_limit`)
already enforces session-count caps; R9 adds the
minutes-budget enforcement + the live ticker (cost
estimation primitives live in V's per-primitive cost
estimators — same shape).

### Option D — F8.1 K10 seed corpus, K7.x YouTube fix

Smaller non-R slices from the queue (
`docs/design/WORKSPACE_FABRIC_V1.md` F8.1 +
`project_youtube_ingest_silent_failure.md`). Each is
30-60 minutes; could ride a half-session if the
operator wants a palette cleanser.

### Recommendation

**R7, then R8.** R7 prepares the tool-approval surface
R8 consumes; landing them in order means R8 ships a
feature-complete realtime experience. R9 can ride a
smaller follow-up — cost ticker isn't gating for an
operator-only beta.

If the operator wants the realtime arc *visible* now
and tolerates "tools come later," **R8 directly** is
viable — the avatar will feel toolless but warm
(R4 + R6 already shipped).

## Files changed in this commit

* `docs/handoffs/SESSION_148_R6_MEMORY.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten with
  SESSION 148 outcome + SESSION 149 menu.
* `docs/design/REALTIME_AVATAR_V1.md` — back-filled
  `dbb22e0` commit ref on the R6 slice-table row.
* `CLAUDE.md` — Phase 4 row bumped to show R6
  shipped.

---

*Handoff written end-of-SESSION 148, paired with the
docs commit per CLAUDE.md doc-with-commit discipline
(codified SESSION 143, reinforced SESSION 147).*
