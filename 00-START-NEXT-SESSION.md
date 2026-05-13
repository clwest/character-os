---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` is canonical for
> what we're building.
> **Last handoff:** `docs/handoffs/SESSION_107_PHASE_1_DJANGO_SHELL.md`
> — Phase 1 substantively complete (5 slices: data model, media-engine
> client, DRF API, auth, billing).

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
**Phase 1 — Django shell scaffold + monetization layer:** DONE.

What's working end-to-end after SESSION 107:

  - `python manage.py runserver` boots cleanly on `:8000`.
  - `python manage.py ping_media_engine` smoke-tests the
    Django↔FastAPI boundary (FastAPI runs on `:8001`).
  - Email/password signup at `POST /accounts/signup/` creates a User,
    auto-creates `"$Email's workspace"` + owner Membership +
    Starter+trialing Subscription in one transaction.
  - 24 REST endpoints under `/api/` covering Workspace / Membership /
    Spokesperson / Video / ConversationThread CRUD + custom
    `/workspaces/{id}/members/` action + `/me/` identity endpoint +
    `/billing/subscription/` (auth) + `/billing/tiers/` (public).
  - Multi-tenant isolation enforced by permission class + queryset
    scoping — bob can't see / read / modify any of alice's resources.
  - Tier-limit gating returns HTTP 402 with a structured payload
    (code, current_tier, suggested_tier, message) at every cap:
    Starter (10 videos / 1 spokesperson), Pro (30/3), Agency
    (unlimited).

**Phase 2 — Media-engine data model migration:** NEXT.

---

## SESSION 108 — Phase 2 entry point

The shell now speaks the new mental model (Workspace → Spokesperson →
Video). The FastAPI media-engine still speaks the legacy model
(Campaign → Character → OutputRecord) with its own JSON-file storage
and 102 endpoints. Phase 2 closes the gap.

### Two equally valid starting points — pick first

The operator decides:

**Option A — Contract first.** Design the new media-engine internal
API (what the Django shell will call), then refactor the existing
FastAPI service to expose that contract while keeping the legacy
endpoints alive during transition. *Recommended.* Lets the Django
side keep building without waiting on data migration.

**Option B — Data first.** Write the one-shot migration script
(`scripts/migrate-campaigns-to-django.py`) that walks every
`backend/data/campaigns.json` entry from runway-hackathon, promotes
the campaign's `business`/`product`/`audience`/`tone` fields onto
the matching Spokesperson, and creates Django `Video` records for
each `OutputRecord` with the campaign's selected_concept as the
brief. Lower risk; gets the historical artefacts surfacing in the
new shell sooner.

### Recommended scope for SESSION 108 (assumes Option A)

1. **Internal API contract spec** at `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
   Lists the verbs Django needs:
   - `POST /internal/avatars/` — create a Runway avatar from a
     spokesperson's portrait + voice settings.
   - `GET /internal/avatars/{id}/` — poll status.
   - `POST /internal/videos/` — generate a video given a kind
     (spokesperson_ad / cinematic_video / dialogue_scene / ...), an
     avatar id, a script or brief, and any per-kind options.
   - `GET /internal/videos/{task_id}/` — poll status, return
     output_url when ready.
   - `POST /internal/voices/` — clone a voice from an audio sample.
   - Pure JSON in/out; no state held by media-engine across calls;
     all persistence lives in the Django shell.

2. **One real wrapper method on `MediaEngineClient`.** Pick the
   simplest endpoint to validate the contract end-to-end. Strong
   candidate: `create_avatar(portrait_path, voice_id)` since
   spokesperson creation is the first user action.

3. **One real endpoint on the media-engine** matching the contract.
   `POST /internal/avatars/` that creates a Runway avatar and returns
   a task id. Implement it alongside (not replacing) the legacy
   `/api/campaigns/.../avatar` endpoint.

4. **Wire the Django side.** Override `SpokespersonViewSet.create` so
   that after the DB row lands, an async-or-sync job fires the
   media-engine call and updates `runway_avatar_id` +
   `runway_avatar_status` when it completes.

5. **Smoke test** — POST `/api/spokespeople/` from Django, watch
   the media-engine task fire (mock mode is fine), confirm
   `runway_avatar_id` populates.

### Out of scope for SESSION 108

- Migrating all 102 legacy endpoints. Add new ones one at a time as
  each Django feature needs them.
- Real Runway calls — mock mode is the right path until the contract
  shape is locked.
- Frontend / SPA work (Phase 3).
- Celery — start with `django.utils.async_to_sync` or a simple
  background thread; bring Celery in when there's a real throughput
  reason.

---

## Queued investigations (not blocking SESSION 108)

- **dj-stripe install** — when operator has Stripe credentials, swap
  the placeholder `Subscription` model's `stripe_customer_id` +
  `stripe_subscription_id` into the dj-stripe-managed flow.
- **Real Google OAuth** — create a Google Cloud OAuth client, add
  the `SocialApp` row via admin or env. `/accounts/google/login/`
  will work after that.
- **`allauth.headless`** — JSON signup/login endpoints for the SPA.
  Defer until Phase 3 starts.
- **`shell/pyrightconfig.json`** — quiets cross-app import warnings.
  2-line slice.
- **Inventory generator** (`python manage.py inventory`) — emits
  runtime truth as JSON for `docs/CHARACTER_OS_INVENTORY.md`.
- **Tag `v-final-pre-migration` on runway-hackathon** (Q6 of design
  doc). Operator decision; recommended once SESSION 108 confirms the
  media-engine refactor path works.

---

## AI / assistant context

- Last session: SESSION 107 — Phase 1 substantively complete in
  five slices (1b80ebf, 6fe96f1, 45b36de, 7d6279b, 9f28b78).
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
- `docs/TRUST_CALIBRATION.md` still empty — first real calibration
  event ready to land.
