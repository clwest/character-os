---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` — **CAUTION:
> this file is referenced everywhere but doesn't actually exist
> at that path.** SESSION 111 surfaced this drift; operator
> clarification needed.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md` —
> feature-complete after SESSION 110.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md` —
> populated in SESSION 111, covers sessions 106-110.
> **Last handoff:**
> `docs/handoffs/SESSION_111_PYRIGHT_CONFIG_AND_CONTEXT_KIT_MAINTENANCE.md`.

---

## Read first (SESSION 112 specifically)

Two real drift items SESSION 111 documented but didn't fix —
either or both might need attention before SESSION 112's recommended
slice lands:

1. **`docs/design/UI_REDESIGN_V2.md` is missing.** CLAUDE.md,
   handoffs, and this very doc treat it as the canonical design
   lock. `ls docs/design/` shows only `MEDIA_ENGINE_INTERNAL_API.md`.
   Did the file never get copied during the context-kit scaffold,
   or does it live somewhere else? Operator decision: recreate,
   restore, or move on without it.
2. **`CHARACTER_OS_INVENTORY.md` is still a stub** because the
   generator (`python manage.py inventory`) hasn't been written.
   The narrative anchor (now populated) compensates with hand-
   maintained scale numbers, but the runtime half of the two-doc
   anchor pattern only works when it's actually regenerated. The
   recommended SESSION 112 slice closes this gap.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE (subject to the
UI_REDESIGN_V2.md drift question above).
**Phase 1 — Django shell scaffold + monetization:** DONE.
**Phase 2 — Media-engine data model migration:** MOSTLY DONE.
Three of three core verbs (avatars, voices, videos) live.

What's working end-to-end after SESSION 111:

  - Everything from SESSIONS 107-110.
  - Pyright noise quieted (`shell/pyrightconfig.json` configured).
  - Narrative anchor `CHARACTER_OS_WHAT_IT_IS.md` reflects real
    state instead of scaffold stubs.
  - `TRUST_CALIBRATION.md` has its first real entry (the SESSION
    109 Celery decision).
  - All three smoke commands still pass in mock mode:
    - `python manage.py smoke_avatar` (~1 s)
    - `python manage.py smoke_voice` (~1 s)
    - `python manage.py smoke_video` (~13 s, needs Celery worker)

---

## SESSION 112 — Recommendation: build the inventory generator

Half-session-sized slice that closes the last anchor gap.

### Scope

`shell/apps/_core/management/commands/inventory.py` (or wherever
the natural home is — possibly directly in `character_os/`).
Emits `docs/CHARACTER_OS_INVENTORY.md` from runtime introspection:

1. **Django models** — count, names, FK relationships. Pull from
   `apps.get_models()`.
2. **DRF endpoints** — count + paths. Pull from
   `rest_framework.routers.DefaultRouter().get_routes()` or walk
   `urls.py` via Django's URL resolver.
3. **Celery tasks** — registered task names. Pull from
   `celery_app.tasks`.
4. **FastAPI routes** — call the media-engine's `/health` (and
   optionally a new `/internal/_meta/routes` if we want
   introspection-as-a-service) and count routes.
5. **Migrations** — count applied vs pending.
6. **Code stats** — LOC per service via `wc -l` on `.py` files.

Output: the actual `docs/CHARACTER_OS_INVENTORY.md` file with
the same frontmatter (`status: regenerated`, `generated:
<ISO datetime>`, command:`python manage.py inventory`) and real
tables under each section. Hand-edit warnings as the header.

### Why this slice

- `context-kit orient` has flagged inventory freshness as a
  warning every session.
- The narrative anchor populated in SESSION 111 carries
  scale numbers that **will** drift. Without a regenerator,
  every future session is back to handwritten claims.
- Phase 3 (SPA) starts smoother with a runtime-truth doc to
  point operators at.

### Out of scope for SESSION 112

- The drift-verifier piece (`verify_doc_claims`) — pattern docs
  describe it; separate slice.
- Hooking the generator into pre-commit / CI — separate slice.
- The missing `UI_REDESIGN_V2.md` decision — operator call.

---

## Alternative slices (operator picks if not inventory)

### A — Resolve the UI_REDESIGN_V2.md drift

If the design lock either exists somewhere off-path or needs
recreating, untangle that before Phase 3 starts. Could be a
5-minute file move or a multi-hour rewrite — depends entirely
on what the operator wants from that doc.

### B — Phase 3 kickoff (SPA scaffolding)

Multi-session. Requires scope lock first:
- Framework + bundler (likely Vite + React + shadcn/ui).
- Auth flow (`allauth.headless` JSON signup/login).
- First screen (Workspace dashboard listing spokespeople +
  videos).

Hard to do well without a design lock; see Alternative A.

### C — Stuck-row janitor (operational hardening)

`celery beat`-scheduled re-enqueue for Video rows stuck in
`rendering` longer than ~5 min. ~30-line slice. Worth landing
before real-mode video traffic creates the actual pressure.

### D — Additional video kinds

`cinematic_video`, `dialogue_scene`, `long_ad`. Defer until the
SPA tells us which kind matters first.

---

## Queued investigations (priority-ordered)

1. **Missing `docs/design/UI_REDESIGN_V2.md`** — real drift,
   surfaced this session. Operator decision.
2. **Inventory generator** — see SESSION 112 recommendation
   above.
3. **`allauth.headless`** — JSON signup/login for the SPA. Lands
   when Phase 3 starts.
4. **Stuck-row janitor** — operational hardening.
5. **Legacy doc rename** — `WHAT_IT_IS_LEGACY.md` and
   `INVENTORY_LEGACY.md` are runway-hackathon predecessor docs;
   names imply staleness rather than predecessor-product.
   Cosmetic.
6. **dj-stripe install** — when operator has Stripe credentials.
7. **Real Google OAuth** — when operator creates the client.
8. **Tag `v-final-pre-migration` on runway-hackathon** — operator
   decision. SESSION 108-111 didn't touch the legacy `/api/*`
   surface; tag remains safe to apply.
9. **Numbered handoff gap** (`SESSION_053`) — cosmetic;
   `context-kit orient` warning.
10. **Smoke-test helper consolidation** — three commands now
    share a stub-request pattern. Extract when a fourth lands.

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

Smoke checks after each change:

```bash
cd shell && source .venv/bin/activate
python manage.py smoke_avatar    # SESSION 108
python manage.py smoke_voice     # SESSION 110
python manage.py smoke_video     # SESSION 109 (needs Celery worker)
```

---

## AI / assistant context

- Last session: SESSION 111 — quiet pyright, populate narrative
  anchor, record the SESSION 109 calibration event.
- Calibration carried forward (from `TRUST_CALIBRATION.md`):
  this operator prefers right-shaping foundations early. When
  the AI offers "smallest thing now" vs. "real foundation now,"
  default to the foundation if it'll be needed within 1-3
  sessions.
- Real drift surfaced this session that needs operator input:
  the `docs/design/UI_REDESIGN_V2.md` file is referenced
  everywhere but doesn't exist. Flag this on session start.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
