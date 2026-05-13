---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` — **imported
> SESSION 113.** 845-line canonical design lock with chris@donkeybetz.com
> sign-off; covers customer + naming + data model + monetization +
> architecture + phase list + screen inventory.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md` —
> feature-complete after SESSION 110.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md` —
> covers SESSIONS 106-113.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory`.
> **Last handoff:** `docs/handoffs/SESSION_113_DESIGN_LOCK_RESOLVED.md`.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
**Phase 1 — Django DRF shell scaffold:** DONE (SESSION 107).
**Phase 2 — Media data model migration:** MOSTLY DONE.
Core contract feature-complete; only the campaigns→Django
backfill script is pending.
**Phase 3 — Build new UI:** **NEXT.** Now unblocked — design lock
in place.

What's working end-to-end after SESSION 113:

  - Everything from SESSIONS 107-112.
  - Design lock now lives in `docs/design/UI_REDESIGN_V2.md`.
  - `CLAUDE.md` phase status is accurate.
  - `CHARACTER_OS_WHAT_IT_IS.md` state-honesty section has one
    fewer flagged drift (the missing design lock is closed).

---

## SESSION 114 — Phase 3 scope lock

Phase 3 is multi-session. Today's job is to **scope-lock the first
slice**, not to ship a full SPA. The design lock's §5 (screen
inventory) gives 9 screens; §7 says Phase 3 needs "wireframes →
components → screens per §5" + auth + activation videos +
landing/pricing. That's a lot.

### Recommended first Phase 3 slice — auth + dashboard skeleton

The smallest thing that exercises the full stack:

1. **`allauth.headless` setup** — JSON signup/login/logout
   endpoints (already queued investigation). One-slice deliverable.
2. **SPA scaffold** — Vite + React + TypeScript + shadcn/ui per
   the scattered references. Just enough to:
   - Sign up (calls Django headless auth).
   - Sign in.
   - See a Workspace dashboard.
   - Sign out.
3. **Workspace dashboard screen** — lists the user's spokespeople
   (via `GET /api/spokespeople/`) and most recent videos (via
   `GET /api/videos/?limit=10`). Empty state when both are
   empty.
4. **One end-to-end test** — Playwright or Cypress, sign-up →
   dashboard. Hermetic against the dev stack.

This is roughly two sessions of work. Don't try to land it in
SESSION 114; **scope-lock it in SESSION 114** with the same
"contract → endpoint → wrapper → smoke" pattern that worked for
Phase 2.

### Alternative first slices (smaller scope)

- **A — Just `allauth.headless`.** Backend-only. ~30-line
  settings change + a smoke test that the endpoints respond.
  Unblocks the SPA without committing to the SPA shape.
- **B — Stuck-row janitor.** SESSION 109's known failure mode.
  ~30-min slice. `celery beat` schedule + re-enqueue logic.
- **C — Campaigns→Django backfill script.** The pending Phase 2
  deliverable. ~half-session. Walks
  `runway-hackathon/backend/data/campaigns.json` and creates
  Django Video records. Only useful once SPA renders them, so
  defer-ability is real.

### Recommendation: **A (just headless auth), then Phase 3 scope lock in SESSION 115.**

Reasoning: Phase 3 is the biggest scope expansion in the project
to date. Locking it without first proving the auth layer can talk
to a JSON-API client is premature. A is a 30-line slice that
makes the actual scope-lock conversation in SESSION 115 grounded
in real running code.

### Out of scope for SESSION 114

- The full SPA. Locked, not shipped, in SESSION 114.
- Real Stripe Checkout integration. Pending dj-stripe credentials.
- Real Google OAuth. Pending client credentials.
- The activation video series (§4 of design lock). Phase 3 sub-
  deliverable but depends on the SPA existing first.
- Marketing site / landing page (also §5 / §7). Same — depends on
  SPA.

---

## Queued investigations (priority-ordered)

1. **`allauth.headless`** — bumped to recommended first slice
   above. JSON signup/login for the SPA.
2. **Phase 3 SPA scope lock** — multi-session; needs SESSION 114
   prep work first.
3. **Stuck-row janitor** — operational hardening.
4. **Campaigns→Django backfill script** — pending Phase 2
   deliverable.
5. **dj-stripe install** — when operator has Stripe credentials.
6. **Real Google OAuth** — when operator creates the client.
7. **Tag `v-final-pre-migration` on runway-hackathon** — safe
   any time. Worth doing now that the design lock has been
   copied across.
8. **Legacy doc rename** (`WHAT_IT_IS_LEGACY.md` →
   `RUNWAY_HACKATHON_WHAT_IT_WAS.md`). Cosmetic.
9. **Numbered handoff gap** (`SESSION_053`) — cosmetic.
10. **Smoke-test helper consolidation** — three commands share a
    stub-request pattern.
11. **Drift verifier** — `verify_doc_claims --only-drift`. The
    inventory now exists; verifier would diff doc-claimed numbers
    against runtime truth. Would have caught the
    `UI_REDESIGN_V2.md` missing-file drift on session 1.
12. **Find-missing-paths check in context-kit orient** — would
    have caught the missing design doc immediately. Pattern-
    level upgrade; cheap to add.

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# (new terminal)
cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

# (new terminal — only for video pipeline)
cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo
```

Smoke checks + runtime refresh:

```bash
cd shell && source .venv/bin/activate
python manage.py inventory          # regen the runtime anchor
python manage.py smoke_avatar       # SESSION 108
python manage.py smoke_voice        # SESSION 110
python manage.py smoke_video        # SESSION 109 (needs Celery worker)
```

---

## AI / assistant context

- Last session: SESSION 113 — resolved a five-session drift by
  importing the design lock from `runway-hackathon/`. Reconciled
  `CLAUDE.md` phase status. Closed one flagged drift in the
  narrative anchor.
- Calibration carried forward: this operator prefers right-shaping
  foundations early. Applies when scoping Phase 3 — don't ship a
  "minimal" SPA if the real one is one cleanup pass away.
- Meta-lesson from this session: when CLAUDE.md or the start-here
  doc references a file path, sanity-check the file exists during
  the same session the reference is made. Five sessions of
  reliance on a non-existent doc could have been five seconds of
  `ls`. **For SESSION 114: if scope-locking SPA work, verify each
  referenced design-doc section is actually in `UI_REDESIGN_V2.md`
  before treating it as canonical.**
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
