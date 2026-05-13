---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` — **still missing.**
> Referenced everywhere but doesn't exist at that path. SESSION 111
> surfaced this; SESSION 112 carried it forward. **Operator input
> required.**
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md` —
> feature-complete after SESSION 110.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md` —
> populated SESSION 111, refined SESSION 112 to defer to the
> inventory for hard numbers.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> **regeneratable** as of SESSION 112 via
> `python manage.py inventory`.
> **Last handoff:**
> `docs/handoffs/SESSION_112_INVENTORY_GENERATOR.md`.

---

## Read first (SESSION 113 specifically)

**Top of queue: the missing design doc.** This has been carried
forward two sessions now. Three possible answers:

1. **It exists somewhere off-path** (e.g. `~/Documents/` or a
   sibling repo). Move it to `docs/design/UI_REDESIGN_V2.md`.
2. **It was never written.** Phase 0 was marked DONE based on
   verbal alignment, not a checked-in document. If so, write what
   needs to exist for Phase 3 to start (customer, pricing, screen
   inventory, naming, data model).
3. **It's not needed.** The design is small enough that the
   handoffs + the narrative anchor are enough. If so, remove the
   stale references in `CLAUDE.md` and the start-here.

Whatever the answer, **Phase 3 (SPA) is blocked on this.** The
SPA is design-led work; without a design lock you're guessing.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE-ISH (see above).
**Phase 1 — Django shell scaffold + monetization:** DONE.
**Phase 2 — Media-engine data model migration:** DONE for the
core contract; queued operational work (janitor, additional
video kinds) is optional.
**Context-kit anchor pattern:** DONE. Both narrative and runtime
anchors now exist with real content + a regenerator.

What's working end-to-end after SESSION 112:

  - Everything from SESSIONS 107-111.
  - `python manage.py inventory` regenerates the runtime anchor
    from live state. Probes the media-engine via `/openapi.json`;
    falls back gracefully when it's not running.
  - Real numbers in the inventory:
    - 6 project-owned models / 5 apps
    - 35 `/api/*` Django routes / 26 `/accounts/*` / 89 admin
    - 93 user-defined FastAPI routes (88 legacy + 4 `/internal/*` + health)
    - 2 Celery tasks
    - 40/40 migrations
    - ~30K LOC total

---

## SESSION 113 — Recommendation: resolve the design-doc drift

Two-session pivot point. Either:

### A — Locate / write / retire `UI_REDESIGN_V2.md`

The unblocking move. Quick path: 5-minute file move if the doc
already exists somewhere. Slow path: multi-hour write if it
doesn't. Either way, the next session shouldn't be starting Phase
3 work without knowing.

### B — Phase 3 SPA kickoff (blocked on A)

Needs scope lock first. Likely shape:
- Framework + bundler decision (Vite + React + shadcn/ui is the
  default per scattered references).
- Auth flow: `allauth.headless` for JSON signup/login.
- First screen: Workspace dashboard listing spokespeople +
  videos.
- Wire `MediaEngineClient` calls through the SPA's data layer.

Don't start B without A resolved. The risk: building a SPA
against an invented design is more expensive than building it
against a real one.

### C — Stuck-row janitor (parallel-safe)

If A turns out to be slow (operator deciding what the design
should be), the janitor is a clean 30-min slice that doesn't
touch design:
- `celery beat` schedule entry: every 60 seconds, scan for
  Videos in `rendering` older than 5 min, re-enqueue
  `poll_video_until_terminal`.
- Tiny code, real operational hardening. Worth landing before
  Phase 3 stress-tests the polling pipeline.

### Recommendation: **A first, then either B (if design exists)
or C (if design takes a session to write).**

### Out of scope for SESSION 113

- The other three video kinds. Defer until SPA renders them.
- dj-stripe + real Google OAuth + `allauth.headless` — all
  pending credentials/config from operator.
- Legacy doc rename (`WHAT_IT_IS_LEGACY.md` →
  `RUNWAY_HACKATHON_WHAT_IT_WAS.md`). Cosmetic; defer.

---

## Queued investigations (priority-ordered)

1. **Missing `docs/design/UI_REDESIGN_V2.md`** — see above.
2. **Stuck-row janitor** — operational hardening before Phase 3
   load lands.
3. **`allauth.headless`** — required for Phase 3 SPA auth.
4. **Legacy doc rename** — cosmetic.
5. **dj-stripe install** — when operator has Stripe credentials.
6. **Real Google OAuth** — when operator creates the client.
7. **Tag `v-final-pre-migration` on runway-hackathon** — safe
   any time.
8. **Numbered handoff gap** (`SESSION_053`) — cosmetic.
9. **Smoke-test helper consolidation** — three commands share a
   stub-request pattern. Extract when a fourth lands.
10. **Drift verifier** — `verify_doc_claims --only-drift`. The
    inventory now exists; the verifier would diff doc-claimed
    numbers against the inventory. Pattern doc reference,
    nothing wired.

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

- Last session: SESSION 112 — inventory generator. Closed the
  seven-session gap where the runtime anchor was a stub.
  Surfaced a real discrepancy: narrative said 106 FastAPI
  routes, inventory says 93. The narrative deferred to the
  inventory. Two-doc pattern earning its keep.
- Calibration carried forward: this operator prefers right-
  shaping foundations early. When the AI offers "smallest thing
  now" vs. "real foundation now," default to the foundation if
  it'll be needed within 1-3 sessions.
- Real drift carried forward: `docs/design/UI_REDESIGN_V2.md`
  doesn't exist. Two sessions of "flag this on session start"
  hasn't resolved it. **SESSION 113 should ask the operator
  directly, before any code lands.**
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
