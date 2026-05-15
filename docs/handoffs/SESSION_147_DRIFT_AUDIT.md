---
title: "Session 147 — context-kit drift audit + boot fixes"
date: 2026-05-15
status: complete
session: 147
previous_handoff: ./SESSION_146_REALTIME_BUILDOUT.md
---

# Session 147 — context-kit drift audit + boot fixes

## TL;DR

Pre-session housekeeping pass. Operator opened SESSION 147
asking for a context-kit drift audit before opening R6. The
audit found **5 drift items** — 2 operational, 3 documentation.
All 5 closed in this session. No feature work; no slice
landings. A 6th outcome: a **5-item drift-prevention
backlog** for future tooling so this class of drift doesn't
recur.

| Item | Class | Fix |
|---|---|---|
| Stale media-engine PID 15420 | operational | killed; fresh uvicorn now serves 25 `/internal/` routes (was 5 stale) |
| Pending `realtime/0001_initial` | operational | applied; migrations 48/49 → 49/49 |
| `WHAT_IT_IS.md` frontmatter / TL;DR | docs | `last_revised` 143 → 146; `covers_sessions` 106-143 → 106-146; TL;DR numbers redirected to INVENTORY |
| `TRUST_CALIBRATION.md` gap | docs | 3 entries appended for SESSIONS 144 / 145 / 146 calibration moments |
| Inventory `git_sha` / route count drift | docs | regenerated against fresh media-engine + applied migration |

Single commit: `ac59aa9` (docs: SESSION 147 boot —
context-kit drift audit fixes).

## Commit log

| Order | Commit | What it shipped |
|---|---|---|
| 1 | `ac59aa9` | `WHAT_IT_IS.md` frontmatter bump + TL;DR softening; 3 `TRUST_CALIBRATION.md` entries; regenerated `INVENTORY.md` |
| 2 | (pending) | `docs/handoffs/SESSION_147_DRIFT_AUDIT.md` + `00-START-NEXT-SESSION.md` bump (this commit) |

## What the audit found

### Drift item 1 — stale media-engine process

`PID 15420` was alive since `Thu May 14 14:47` — before any
R-arc commit. The OpenAPI spec served by that process only
exposed **5 `/internal/*` routes**, missing R2's
`realtime_sessions/`, R4's `realtime_documents/`, and R5's
`transcript/` endpoints. The live source code had **25**.
Fresh uvicorn (PID 43509) now correctly serves all 25.

Inventory's `/internal/` count is one of the canonical
numbers used by anything reading INVENTORY as runtime
truth. The stale process meant INVENTORY was *also* lying
about scale until this session.

### Drift item 2 — unapplied realtime migration

`apps.realtime.migrations.0001_initial` was created during
R1 (SESSION 146 `9299dcf`) but never applied to the dev DB.
The R-arc test suite ran on a fresh test DB each pytest
run, so the gap stayed invisible until any operator hit
`/api/realtime_sessions/` in the browser → 500 on missing
`realtime_realtimesession` table.

Applied this session. Migrations 49/49 now.

### Drift item 3 — narrative anchor stale by 3 sessions

`docs/CHARACTER_OS_WHAT_IT_IS.md`'s frontmatter said
`last_revised: 2026-05-14 (SESSION 143)`; `covers_sessions:
"106-143"`. The TL;DR paragraph hard-coded SESSION 132 era
numbers (40 `/api/*`, 94 FastAPI, 31K LOC). The fabric arc
(F0-F10), the K-arc close (K8 + K9), and the R-arc open
(R1-R5) were all invisible to anyone reading just the
anchor.

Bumped frontmatter to SESSION 146; softened TL;DR to point
at INVENTORY for the canonical shape rather than quoting
stale absolute numbers.

### Drift item 4 — TRUST_CALIBRATION ledger 3 sessions behind

`docs/TRUST_CALIBRATION.md` ended at SESSION 143's
doc-discipline catch-up entry. Three sessions of calibration
moments lived only inside their respective handoffs:

* **S144** — operator's "brief mode" insight reshaped F4
  mid-slice from preview-only to preview-plus-brief.
* **S145** — K8 was discovered to be partly-shipped during
  K2; the scope-lock had over-counted.
* **S146** — four-failure-mode session (TIER_LIMITS edit
  shadowing on hot files, cross-arc isolation
  `ALLOWED_FILES` gap, `replace_all=true` back-fill hazard,
  hackathon-client coexistence rule).

Three structured entries appended.

### Drift item 5 — INVENTORY out of date with HEAD

`INVENTORY.md`'s `git_sha` lagged `HEAD` by 1 commit (the
S146 handoff commit); the `/internal/` count was wrong (5
served-stale vs 25 actual); migrations were 48/49 (now
49/49). Regenerated mid-session via `python manage.py
inventory` after the media-engine restart + migration
apply.

Two known inventory bugs **deferred to a future slice**:
the Celery-task counter undercounts (reads 5; real
registered count is 7) and the working-tree-dirty flag is
on by design but reads as drift unless the regenerator
commits the result. Both are inventory-generator bugs,
not state drift.

## Calibration moments worth carrying

### 1. Drift compounds silently between sessions

Each of the 5 items individually was the kind of thing the
operator would catch fast in a normal slice. The audit
caught all 5 only because the operator explicitly asked
for an audit. Without that ask, SESSION 147 would have
opened R6 — at which point the stale media-engine would
have given R6's local development the wrong realtime
provider surface, the realtime migration would have 500'd
the first `/api/realtime_sessions/` request, and three
sessions of calibration moments would have stayed
write-only-in-handoffs.

**Carry-forward**: every session-start should run a drift
sweep, not just a slice scope. The 4 categories that
caught us here are all programmatically detectable
(process age vs commit age, pending migrations, frontmatter
date vs latest handoff date, INVENTORY `git_sha` vs `HEAD`).
The first slice of SESSION 148 productises this as a
`context-kit drift` subcommand.

### 2. INVENTORY's runtime authority depends on regeneration freshness

CLAUDE.md says "runtime wins" — but INVENTORY is only
runtime-true at regeneration time. Between regenerations
it's just a doc, and a stale process serving the wrong
routes will *write the wrong numbers into INVENTORY* on
the next regeneration, propagating the drift forward. The
fix is to make the regeneration verify against a fresh
process state, or to make stale-process detection part of
the regeneration command itself.

**Carry-forward**: any "single source of truth" doc that
gets regenerated needs a verifier as part of the
regeneration step, not as a separate audit. The S148
drift subcommand is the seam where this lands.

## Drift-prevention backlog (the real next-session menu)

The audit's 5 fixes closed the immediate drift. The
**recurrence prevention** is a 5-item backlog. Ordered
cost-to-value:

### 1. `context-kit drift` subcommand (cheapest win)

A read-only subcommand that surfaces exactly the 4 classes
of drift this audit found:

* **Stale processes** — parse `ps` for known service
  patterns (uvicorn, runserver, celery worker); flag any
  whose `lstart` predates the most recent commit touching
  that service's directory.
* **Pending migrations** — `python manage.py
  showmigrations --plan | grep '\[ \]'` from `shell/`.
* **Frontmatter date drift** — `last_revised` field in
  `*_WHAT_IT_IS.md` vs the `date:` field of the latest
  `docs/handoffs/SESSION_*.md`.
* **INVENTORY `git_sha` vs `HEAD`** — flag when INVENTORY
  is N commits behind HEAD.

Wire it into `orient` so every session-start surfaces drift
before the AI proposes a slice. Exit 0 on clean; exit 1 on
drift (so CI / pre-commit can adopt it).

**Estimated cost**: one session. Same shape as
`context-kit doctor` (read-only environment checks). The 4
detections are 20-40 lines each.

### 2. Auto-bump `last_revised` on handoff write

Today's pattern: writing `SESSION_NNN_*.md` is manual;
updating `WHAT_IT_IS.md` frontmatter is also manual but
easy to forget (we forgot 3 sessions running, which is
*the entire reason this audit existed*). Tooling: a
`context-kit handoff write` subcommand that takes the
session number, writes the skeleton handoff *and*
re-stamps every `last_revised: ... (SESSION NNN)` field
across anchor docs in one shot.

Removes the forgetting surface entirely. The handoff
writer is the natural single-touchpoint for "what
SESSION are we ending."

**Estimated cost**: half a session.

### 3. Promote calibration entries from handoffs to TRUST_CALIBRATION at handoff-write time

Today: calibration text lives in both the handoff (rich)
and TRUST_CALIBRATION (structured) — and SESSIONS 144 /
145 / 146 wrote only the rich half. Tooling: the
handoff-write subcommand from (2) greps the new handoff
for the `## Calibration moments worth carrying` heading,
extracts each subsection, and appends a structured entry
to TRUST_CALIBRATION with the operator confirming the
headline date/type on each.

One source of truth (handoff narrative); one auto-derived
ledger.

**Estimated cost**: half a session, after (2) lands.

### 4. Codify "session-start drift sweep" in CLAUDE.md doc-discipline

Add a 4-step checklist the AI runs first on every session
boot before claiming the next slice:

1. Run `context-kit drift` (from (1) above).
2. Resolve every flagged item before opening any slice.
3. If drift requires fixes, commit them as a `docs:
   SESSION NNN boot — drift sweep` commit before the
   first feature commit.
4. Note in the handoff if a drift sweep was run; the
   absence of the note is the failure mode.

With (1) in place, the sweep is one command. Without (1),
it's still the same 4 checks done manually.

**Estimated cost**: 10 minutes of CLAUDE.md editing.
Lands with or after (1).

### 5. Inventory's two known bugs

The Celery-task counter undercounts (reads 5; real
registered count is 7 after R5 added
`fetch_transcript_for_session` + K3's `embed_document` +
K8's `embed_message`); the working-tree-dirty flag stays
on for any in-progress regeneration. Both live in
`shell/apps/accounts/management/commands/inventory.py`.

Defer-able — but every wrong number in INVENTORY teaches
the AI to second-guess INVENTORY, which corrodes the
"runtime wins" invariant context-kit depends on.

**Estimated cost**: one session.

## What shipped (concrete)

### Operational

* Killed `PID 15420` (stale media-engine); started fresh
  uvicorn (`PID 43509`). Health check: `{"status":"ok"}`.
  `/internal/` route count: 5 → 25.
* Applied `realtime.0001_initial` via `python manage.py
  migrate`. Migration count: 48/49 → 49/49.

### Files changed (commit `ac59aa9`)

* `docs/CHARACTER_OS_WHAT_IT_IS.md` — frontmatter bumped;
  TL;DR softened.
* `docs/TRUST_CALIBRATION.md` — 3 entries appended (144
  brief-mode, 145 K8-partly-shipped, 146 four-failure-
  mode bundle).
* `docs/CHARACTER_OS_INVENTORY.md` — regenerated;
  `/internal/` count corrects to 25; migration count
  49/49.

### Files changed (this commit)

* `docs/handoffs/SESSION_147_DRIFT_AUDIT.md` — this file.
* `00-START-NEXT-SESSION.md` — overwritten; SESSION 147
  outcome block; SESSION 148 named first thing
  (`context-kit drift` subcommand).
* `CLAUDE.md` — Phase 4 row gains SESSION 147 entry
  noting the audit + the prevention backlog.

## Project memories saved this session

None new. The drift-prevention backlog lives in this
handoff + the next-session start doc; promoting any of it
to project memory is premature until the first item ships
(at which point context-kit gains the subcommand and the
memory becomes "context-kit ships drift detection — use
it at session start").

## What's next (SESSION 148)

**Recommendation: backlog item 1 — implement `context-kit
drift` subcommand.** The cheapest and highest-value of the
five. Single session of work. Read-only. Wires into
`orient`. Once it exists, items (2)-(4) become easier
to land in any order.

Alternative: open **R6** (cross-session memory) per the
original SESSION 146 handoff. R6 is feature work; (1) is
tooling. The operator's framing this morning ("the tools
only work if we use them the correct way") points at the
tooling first.

**Don't do both in one session.** The drift-prevention
work is meta-tooling on context-kit itself; mixing it
with feature work would split focus and produce two
half-done slices. Pick one; the other is on the menu
next session.

---

*Handoff written end-of-SESSION 147, before any SESSION
148 work begins. Per the doc-with-commit discipline
codified in CLAUDE.md.*
