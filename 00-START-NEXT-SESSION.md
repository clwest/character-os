---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` — 845-line canonical
> doc with operator sign-off, imported SESSION 113.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md` —
> feature-complete after SESSION 110.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory`.
> **Last handoff:** `docs/handoffs/SESSION_114_ALLAUTH_HEADLESS.md`.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
**Phase 1 — Django DRF shell scaffold:** DONE (SESSION 107).
**Phase 2 — Media data model migration:** MOSTLY DONE
(campaigns→Django backfill still pending; everything else done).
**Phase 3 — Build new UI:** **STARTED.** Headless auth surface
shipped (SESSION 114); SPA scaffold is the next slice.

What's working end-to-end after SESSION 114:

  - Everything from SESSIONS 107-113.
  - `allauth.headless` mounted at `/_allauth/browser/v1/*`
    (19 JSON routes). Phase 1 auto-Workspace cascade fires
    through it.
  - `python manage.py smoke_headless_auth` — drives the full
    auth-and-cascade pipeline in <1 second.
  - URL inventory bumped 150 → 169.

---

## SESSION 115 — Phase 3 SPA scope-lock

The technical unblockers are all in place. SESSION 115's job is
to **lock the SPA scope** with the same discipline that worked
for Phase 2 (contract → endpoint → wrapper → smoke). The risk
is shipping a sloppy SPA because the temptation is high; the
operator already noted (SESSION 109 calibration entry) a
preference for right-shaping foundations early.

### Recommended scope-lock deliverable for SESSION 115

A `docs/design/SPA_ARCHITECTURE.md` doc (sibling to
`MEDIA_ENGINE_INTERNAL_API.md`) that pins:

1. **Framework + bundler.** Vite + React + TypeScript +
   shadcn/ui is the recurring assumption in references.
   Confirm and lock.
2. **Auth client shape.** How the SPA's data layer talks to
   `/_allauth/browser/v1/*` — `fetch` directly, an auth provider
   wrapper, TanStack Query, whatever. Lock one approach.
3. **API client shape.** Same question for `/api/*` (DRF
   resources). Probably the same client + a thin wrapper per
   resource. Lock the shape.
4. **First three screens.** §5 of `UI_REDESIGN_V2.md` lists 9
   total. Pick the three that exercise the auth surface +
   workspace data flow:
   - **Sign-in / sign-up.** Wraps headless auth.
   - **Workspace dashboard.** Lists spokespeople + recent videos.
   - **Spokesperson detail.** Shows one spokesperson + their
     videos.
5. **Smoke test pattern.** Probably Playwright; needs to drive
   the same headless flow `smoke_headless_auth` does, then
   render the dashboard.
6. **Out of scope explicitly.** Everything else in §5: video
   creation flow, billing screens, account settings, agency
   features. Defer to subsequent SPA slices.

### SESSION 116 onwards (post scope-lock)

Each SPA slice ships as one cross-stack commit (the Phase 2
pattern) — scaffold + first screen + smoke test in one slice,
not three.

### Alternative slices if Phase 3 scope-lock feels premature

- **A — Stuck-row janitor.** `celery beat`-scheduled re-enqueue
  for Video rows in `rendering` longer than 5 min. ~30-line
  slice. Pre-Phase 3 operational hardening.
- **B — Campaigns→Django backfill script.** Pending Phase 2
  deliverable. Half-session. Only useful once SPA renders
  legacy artefacts, so defer-ability is real.
- **C — Real Stripe Checkout / dj-stripe wiring.** Pending
  operator-supplied Stripe credentials.
- **D — Real Google OAuth (headless flow).** Adds Google as a
  `/_allauth/browser/v1/auth/provider/redirect` option. Needs
  operator-supplied OAuth client credentials.

### Out of scope for SESSION 115

- SPA implementation. Locked, not shipped.
- Stripe / Google credentials (operator gates these).
- The activation video series (§4 of design lock). Phase 3
  sub-deliverable but depends on the SPA shipping first.

---

## Queued investigations (priority-ordered)

1. **Phase 3 SPA scope-lock** — recommended SESSION 115 slice.
2. **Phase 3 SPA scaffold + first screen** — SESSION 116+
   after scope-lock.
3. **Stuck-row janitor** — operational hardening.
4. **Campaigns→Django backfill script** — pending Phase 2
   deliverable.
5. **dj-stripe install** — operator gate.
6. **Real Google OAuth** — operator gate; consumes the headless
   socialaccount surface once enabled.
7. **Tag `v-final-pre-migration` on runway-hackathon** — safe
   any time. Recommended now that the design lock has been
   copied across.
8. **Legacy doc rename** (`WHAT_IT_IS_LEGACY.md` →
   `RUNWAY_HACKATHON_WHAT_IT_WAS.md`). Cosmetic.
9. **Numbered handoff gap** (`SESSION_053`) — cosmetic.
10. **Smoke-test helper consolidation** — 4 commands share a
    stub/client pattern now; extract when a fifth lands.
11. **Drift verifier** — `verify_doc_claims --only-drift`.
    Inventory exists; verifier would catch doc-vs-runtime drift.
12. **Find-missing-paths check in `context-kit orient`** — would
    have caught the missing design doc on session 1.

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
python manage.py inventory                # regen the runtime anchor
python manage.py smoke_avatar             # SESSION 108
python manage.py smoke_voice              # SESSION 110
python manage.py smoke_video              # SESSION 109 (needs Celery worker)
python manage.py smoke_headless_auth      # SESSION 114
```

Probe the headless surface manually:

```bash
curl http://127.0.0.1:8000/_allauth/browser/v1/config
curl http://127.0.0.1:8000/_allauth/browser/v1/auth/session
```

---

## AI / assistant context

- Last session: SESSION 114 — `allauth.headless` wired in <1
  hour, smoke test PASSED, all gates clean. Textbook small slice.
- Calibration carried forward: this operator prefers right-
  shaping foundations early. Applies hard to Phase 3 — don't
  ship a "minimal" SPA. Lock scope thoroughly in SESSION 115
  before any frontend code lands.
- Meta-lesson from SESSION 113 still applies: when a reference
  in a handoff or start-here points at a file path, sanity-
  check it exists during the same session. The SPA architecture
  doc proposed for SESSION 115 is a **new** file; don't trust
  any cross-references to it until the doc lands.
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
