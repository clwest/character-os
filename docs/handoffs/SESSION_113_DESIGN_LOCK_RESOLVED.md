---
title: "Session 113 — UI_REDESIGN_V2.md drift resolved"
date: 2026-05-13
status: complete
session: 113
previous_handoff: ./SESSION_112_INVENTORY_GENERATOR.md
---

# Session 113 — Imported the missing design lock + phase status reconciled

## TL;DR

- **What shipped:** The 845-line `UI_REDESIGN_V2.md` design lock
  finally lives in `character-os/docs/design/`. Imported from
  `runway-hackathon/docs/design/` where it had been sitting since
  the migration started — never copied across during the SESSION
  106 context-kit scaffold. Five sessions of handoffs treated it
  as canonical despite the file not existing at the path. Closed.
- **What also shipped:** `CLAUDE.md` phase status section
  reconciled with reality — was still saying "Phase 1 IN
  PROGRESS" when Phase 1 has been DONE since SESSION 107 and
  Phase 2 is mostly done.
- **What's blocking next:** Nothing. Phase 3 (SPA) is now
  un-blocked — the design lock is in place. SESSION 114 can
  scope-lock the SPA work.

---

## What changed (file-by-file)

### `docs/design/UI_REDESIGN_V2.md` (new — imported)

`cp`'d from `runway-hackathon/docs/design/UI_REDESIGN_V2.md`.
845 lines. Authored 2026-05-13 (same day as SESSION 106) by
Claude (Opus 4.7) for chris@donkeybetz.com.

Content is **byte-identical to the source** so the sign-off log
at the bottom (§11) stays intact. Only addition is a small
`<!-- PROVENANCE -->` HTML comment block at the very top
explaining how it got here.

What the doc covers (each section answering a Phase 0 question
that everything downstream depends on):

1. Customer + jobs-to-be-done (solo creators + non-marketer SMBs)
2. Naming + data model (kill Campaign; Workspace → Spokesperson
   → Video)
3. Monetization (three tiers — Starter $29 / Pro $79 / Agency
   $199; no credit math exposed)
4. Activation strategy (avatar-narrated explainer series)
5. Screen inventory (§5 — the 9 screens the SPA needs)
6. Architecture (Django DRF shell + FastAPI media engine, shared
   Postgres+pgvector, Redis broker)
7. Implementation phases (§7 — the 5-phase sequencing)
8. Auth model (Google OAuth primary, email/password backup)
9. Open questions (§8 — Q1-Q7 the operator deferred)
10. Success metrics (§9 — 30-day activation / D1 / conversion
    targets)
11. Sign-off log (§11 — 9 line-items with chris@donkeybetz.com
    sign-off on 2026-05-13)

§7 (phase list) reconciled against actual built state:

| Phase | Doc says | Reality | CLAUDE.md (before) | CLAUDE.md (after) |
|---|---|---|---|---|
| 0 — Pre-flight | This doc + wireframes + Stripe + domain | Design lock ✓; wireframes / Stripe / domain still open | DONE | DONE (load-bearing piece is the doc) |
| 1 — Django shell | Users + workspace + auth + Stripe stub + media-engine client | All shipped SESSION 107 | IN PROGRESS | DONE (SESSION 107) |
| 2 — Media data model | Spokesperson + Video + stateless FastAPI + campaigns backfill | Models + contract done; backfill script still pending | Pending | MOSTLY DONE |
| 3 — Build new UI | SPA + screens + activation videos + marketing | Not started | Pending | Pending |
| 4 — u-d-b feature port | Embeddings + agents + spider + memory | Not started | Pending | Pending |
| 5 — Agency tier UI | Seats + sharing + per-client workspace | Not started | Pending | Pending |

### `CLAUDE.md`

Two small but load-bearing fixes:

1. Phase status table updated (see above).
2. The inventory anchor note no longer says "regenerable once
   the inventory generator is wired up" — that wired up in
   SESSION 112. Now points at the actual command.

### `docs/CHARACTER_OS_WHAT_IT_IS.md`

Closed the "missing UI_REDESIGN_V2.md" entry in the state-
honesty section (struck through, with a "closed in SESSION 113"
note for traceability). Updated `last_revised` and
`covers_sessions` frontmatter to 2026-05-13 (SESSION 113) /
"106-113".

---

## Verification gates

- `python manage.py check` — 0 issues. (No code changes; doc-only
  slice.)
- `python manage.py inventory --dry-run` — emits the same numbers
  as SESSION 112 (no model / route / task changes).
- File-existence smoke check —
  `ls docs/design/UI_REDESIGN_V2.md` returns a real file.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### Five-session drift is concerning, but pattern caught it

`UI_REDESIGN_V2.md` was referenced by `CLAUDE.md`,
`00-START-NEXT-SESSION.md`, and every SESSION 107-112 handoff as
the canonical design lock. None of those references checked the
file existed; the AI just trusted the path. The narrative-anchor
populate in SESSION 111 was the first session that explicitly
tried to read it and noticed the gap. The two-doc anchor pattern
isn't only about quantities — it's also about "hey, this
referenced file doesn't actually exist."

Lesson: when adding a file path to a handoff, the AI should
`Read` or `ls` it during the same session. Cheap pre-commit
hook material if anyone wants to lock this down.

### The design lock validates everything we built

The reassuring outcome: §4 (data model), §6 (architecture), and
§7 (phase list) of the imported doc are an **exact match** for
what SESSIONS 107-112 built. Workspace → Spokesperson → Video,
Django shell + FastAPI media-engine, three-tier pricing, sign-up
auto-Workspace, all of it. The work didn't drift from the
design lock; we just couldn't see the lock.

This means Phase 3 (SPA) can proceed against §5 (screen
inventory) without re-litigating any earlier decisions.

### Phase status was a small but real lie

`CLAUDE.md` claiming "Phase 1 IN PROGRESS" while Phase 1 was
verifiably DONE for five sessions is the kind of doc rot that
makes orient output less useful. Worth catching with a
verifier eventually (the `verify_doc_claims` pattern doc
references this). Manual fix today.

### What this session deliberately didn't do

- Backfill the campaigns→Django migration script. §7 explicitly
  lists this as a Phase 2 deliverable; it's pending. Defer until
  the SPA needs historical artefacts surfacing.
- Write wireframes (§7 Phase 0 sub-item). Operator decision; the
  design lock is the load-bearing piece. Wireframes can be
  Phase 3 prep.
- Touch the runway-hackathon repo (CLAUDE.md hard rule — frozen).

---

## SESSION 114 — entry point

Phase 3 (SPA) is unblocked. The design lock §5 (screen inventory)
gives concrete scope. See `00-START-NEXT-SESSION.md` for the
recommendation.

---

## AI notes

- The fix took ~5 minutes once the file was located. The
  cognitive cost was higher: every previous session had to
  re-discover that the reference was broken. Worth remembering
  next time the AI agrees to "read first" a file in a CLAUDE.md
  preamble — at minimum, sanity-check that the file exists in
  the same session the agreement is made.
- The discovery path: `find /Users/donkeyking/development -name
  "UI_REDESIGN*"` returned the file in `runway-hackathon/` and
  an unrelated `UI_REDESIGN_AUDIT.md` in `character-os/`. Both
  obvious in retrospect; neither obvious from CLAUDE.md alone.
  If we had a "find missing referenced paths" check in
  `context-kit orient`, this would have surfaced session 1.
- The phase status drift in `CLAUDE.md` is more interesting
  than it looks. CLAUDE.md is the **first thing every session
  reads**; if it's lying, every subsequent decision is
  miscalibrated. The two-doc anchor pattern handles narrative
  vs. runtime; we don't currently have a pattern for
  "narrative-of-narratives drift" (CLAUDE.md vs handoffs vs
  start-here). Worth thinking about.
