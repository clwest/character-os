---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V1.md` —
> editorial-warm, locked SESSION 117.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_117_DASHBOARD_AND_BRAND_IDENTITY.md`.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3 — Build new UI:** Slice 1 + Slice 2 SHIPPED.
  Slice 3 (spokesperson detail, S-10) next.

What's working end-to-end after SESSION 117:

  - Everything from SESSIONS 107-116.
  - Editorial-warm aesthetic locked + applied across auth + dashboard.
  - Real workspace dashboard at `/dashboard`: masthead, primary
    action panel, spokespeople grid + usage meter, recent renders
    list. All loading skeletons + empty states populated.
  - Five parallel TanStack Query calls (`me`, `subscription`,
    `spokespeople`, `videos`, `session`) compose the dashboard.
  - 4 Playwright e2e specs pass (auth × 2 + dashboard × 2).

---

## SESSION 118 — Slice 3: spokesperson detail (S-10)

Per SPA_ARCHITECTURE.md §"First three screens" → Slice 3. The
detail view for one spokesperson + their videos. First surface
where the avatar/voice status pills actually do work (rendering /
ready / failed).

### Recommended scope

1. **`src/lib/api/spokespeople.ts`** — add `getSpokesperson(id)` +
   `useSpokesperson(id)`. zod-parsed; reuses the existing schema.
2. **`src/routes/spokespeople/$id.tsx`** — new route. Sections:
   - **Identity panel** — portrait + name + business_brief + status
     pills (avatar status, voice status).
   - **Videos library** — the same `VideoRow` component reused, but
     filtered to this spokesperson via `useVideos({spokesperson: id})`.
   - **Empty / setup callouts** — when avatar/voice aren't set up,
     surface them (placeholder CTAs for future S-06 / clone-voice
     slices).
3. **Wire from dashboard** — make each `SpokespersonCard` clickable
   (wrap with `<Link to={"/spokespeople/" + id}>`). Hover state
   should signal interactivity.
4. **`src/routes/spokespeople/$id.test`** — vitest unit for the
   route-level loading/error states (if the slice grows that direction;
   optional for the first cut).
5. **`web/e2e/spokesperson.spec.ts`** — Playwright spec. Signup →
   seed a spokesperson via the backend `smoke_avatar` command (or
   via the existing API; whichever is simpler) → navigate to
   `/spokespeople/{id}` → assert identity panel renders + status
   pill is correct.

### Critical constraints

- Stay strict-mode TypeScript. No `any` without comment.
- All responses zod-parsed before TQ cache.
- Status pills reuse the existing token palette
  (`bg-primary/10 text-primary` for ready, etc.). Defined in
  spokesperson-card.tsx and the dashboard's `StatusBadge` —
  consider extracting `components/status-badge.tsx` if a third
  consumer lands.
- Empty states keep the editorial copy approach: explain WHAT
  needs to happen + WHY, not just "nothing here."

### Out of scope for SESSION 118

- Make-a-video flow (S-12; later slice).
- Create-spokesperson flow (S-06).
- Voice clone UI (S-10 sub-action; reuses backend `clone-voice`
  endpoint but its own slice).
- Video detail page (S-11).

---

## Recommended parallel slice (still queued from SESSION 116)

**Custom email-as-PK User model.** The SESSION 116
`WorkspaceAccountAdapter` band-aid still ships in prod-shape
code. The proper fix is an `apps.accounts.User` model with email
as `USERNAME_FIELD`, no username column. Parallel-safe with
SESSION 118 since it doesn't touch the SPA. ~1 model + migration
+ adapter deletion.

When to land: before SPA goes to real customers. Could be
SESSION 118, 119, or a sibling slice.

---

## Alternative slices

- **Stuck-row janitor** (`celery beat`). Operational hardening.
- **Real Google OAuth** (operator gate).
- **dj-stripe** (operator gate).
- **Status badge extraction** — if SESSION 118 introduces a third
  status-pill use, extract `components/status-badge.tsx` and have
  spokesperson-card + video-row reuse it.

---

## Queued investigations (priority-ordered)

1. **Custom email-as-PK User model** — overdue band-aid replacement.
2. **Phase 3 Slice 3** — spokesperson detail (SESSION 118).
3. **Phase 3 Slice 4+** — create-spokesperson (S-06), make-a-video
   (S-12), video detail (S-11). Each its own slice.
4. **Stuck-row janitor** — operational hardening.
5. **Real Google OAuth + dj-stripe** — operator gates.
6. **Status badge extraction** — if third use lands.
7. **Tag `v-final-pre-migration` on runway-hackathon** — safe any
   time.
8. **Smoke-test helper consolidation** — 5 backend smokes + 4
   Playwright specs share patterns; extract if pain shows up.
9. **Drift verifier** — `verify_doc_claims --only-drift`.
10. **Brand Identity v2 + dark mode** — when user-testing or a
    real brand-design pass happens.
11. **Numbered handoff gap** (`SESSION_053`) — cosmetic.

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

# (new terminal — SPA)
cd web && pnpm dev                          # :5174, proxies to :8000
```

Smoke checks (backend):

```bash
cd shell && source .venv/bin/activate
python manage.py inventory
python manage.py smoke_avatar
python manage.py smoke_voice
python manage.py smoke_video
python manage.py smoke_headless_auth
```

SPA tests:

```bash
cd web
pnpm test
pnpm e2e            # needs Django up
```

---

## AI / assistant context

- Last session: SESSION 117 — Slice 2 + Brand Identity v1.
  Editorial-warm landed cleanly. The frontend-design plugin's
  guidance was directly load-bearing — invoke it again on any
  future SPA slice that introduces new UI patterns.
- Calibration: this operator prefers right-shaping foundations
  early. BRAND_IDENTITY_V1 was the foundation pass for the SPA's
  visual identity; SESSION 118 should inherit cleanly without
  inventing new color or font choices.
- For SESSION 118 specifically: the spokesperson detail route is
  smaller than the dashboard — reuse VideoRow, follow the same
  panel patterns (`PanelHeader`, `EmptyState`, skeleton matching
  final layout). Resist the temptation to add new design surface
  area.
- Collaboration conventions: AI drafts, human edits. Handoff
  `## AI Notes` section required at session end.
