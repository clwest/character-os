---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` is canonical for
> what we're building. Read it before writing any model code.
> **Last handoff:** `docs/handoffs/SESSION_106_CHARACTER_OS_REPO_BOOTSTRAP.md`
> — the scaffold session that created this repo.
> **Runtime truth:** `docs/CHARACTER_OS_INVENTORY.md` (regenerable
> when the inventory generator is wired up — that's a SESSION 107+
> task, not blocking the model work itself).

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
**Phase 1 — Django shell scaffold:** STARTED in SESSION 106.

What landed:
- New repo at `/Users/donkeyking/development/character-os/` (94 commits).
- FastAPI media engine imported via `git subtree` with 89 commits of
  history preserved at `media-engine/`.
- Django shell at `shell/` boots clean (`python manage.py check` →
  0 issues; built-in migrations applied to SQLite).
- 8 empty Django app modules ready for content: `accounts`,
  `spokespeople`, `videos`, `conversations`, `memory`, `billing`,
  `agents`, `embeddings`.
- Context-kit anchors + handoffs + research carried over.

What's left in Phase 1:
1. Core data model (this session).
2. Google OAuth + email/password auth.
3. Stripe Subscriptions + tier middleware.
4. Admin views beyond Django's default.
5. Internal API client for Django→FastAPI media-engine calls.
6. Inventory generator (`shell/manage.py inventory`) for the
   context-kit drift loop.
7. Tag `v-final-pre-migration` on the old `runway-hackathon` repo
   once SESSION 107+ confirms character-os is operational
   end-to-end.

---

## SESSION 107 — Core data model

**Goal:** lock the schema for the new mental model
(`Workspace → Spokesperson → Video`, with `Membership` as the
through-table) before any auth, billing, or media work goes on top.

### Scope (single slice)

1. **`apps.accounts`** — User extension + Workspace + Membership.
   - Stick with Django's built-in `auth.User` for v1; reach for
     a custom user model only if we hit a real limitation. The
     audience doesn't need username/email customization beyond
     what django-allauth gives later.
   - `Workspace` model — id, name, slug, owner (FK to User),
     created_at, updated_at. No subscription FK yet (lands in the
     billing slice).
   - `Membership` through-model — User ↔ Workspace with a `role`
     field (`owner` / `admin` / `editor` / `viewer`). In v1 every
     workspace has exactly one membership and it's the owner; the
     table exists for forward-compatibility with Agency tier.
   - Manager method on User → `default_workspace` helper.

2. **`apps.spokespeople`** — Spokesperson stub.
   - id (UUID), workspace (FK), name, business_brief (TextField),
     status (`setup_needed` / `ready` / `archived` enum), created_at,
     updated_at.
   - Placeholders for media-engine integration: `runway_avatar_id`
     (nullable CharField), `runway_avatar_status` (nullable),
     `portrait_path` (nullable), `voice_id` (nullable).
     Not wired to FastAPI yet — just the schema landing pad.

3. **`apps.videos`** — Video stub.
   - id (UUID), spokesperson (FK), title (nullable CharField),
     brief (TextField — the one-line override of spokesperson
     default), kind (CharField — `spokesperson_ad`, `dialogue_scene`,
     `cinematic_video`, etc.), status (`pending` / `rendering` /
     `ready` / `failed`), output_path (nullable),
     duration_seconds (nullable FloatField), tags (JSONField,
     default `[]` — hidden in v1 UI per design doc §4.4).
   - Created_at, updated_at, completed_at (nullable).

4. **`apps.conversations`** — Thread stub.
   - id (UUID), spokesperson (FK), title (nullable), created_at,
     last_activity_at. No message/transcript model yet — that's a
     follow-up slice.

5. **Admin registration** for all four models so we can poke at
   the schema in the Django admin without writing views.

6. **Migrations applied** + `python manage.py check` clean.

7. **End-of-session smoke test** — interactive shell:
   ```python
   python manage.py shell
   >>> from django.contrib.auth.models import User
   >>> from apps.accounts.models import Workspace, Membership
   >>> from apps.spokespeople.models import Spokesperson
   >>> from apps.videos.models import Video
   >>> u = User.objects.create_user("test", "test@example.com", "x")
   >>> w = Workspace.objects.create(name="Test", slug="test", owner=u)
   >>> m = Membership.objects.create(user=u, workspace=w, role="owner")
   >>> s = Spokesperson.objects.create(workspace=w, name="Riggs",
   ...                                 business_brief="Coffee shop in Denver.")
   >>> v = Video.objects.create(spokesperson=s, brief="Holiday promo",
   ...                          kind="spokesperson_ad", status="pending")
   >>> v.id, v.spokesperson.name, v.spokesperson.workspace.owner.username
   ```
   All chains traverse cleanly → schema is correct.

### Out of scope for SESSION 107

- Google OAuth wiring — that's its own slice.
- Stripe + tier middleware — its own slice.
- DRF viewsets / serializers / endpoints — write models first, then
  expose them.
- Internal media-engine client — needs Spokesperson + Video to exist
  first; comes next.
- Migration from the legacy `campaigns.json` — Phase 2 territory.

### Open decisions to flag mid-session (not blocking start)

- **UUID primary keys vs. BigAutoField?** Recommended: UUIDs for
  Spokesperson + Video + ConversationThread + Workspace (anything
  URL-exposed or shared across tenants); BigAutoField for
  Membership (internal join). UUIDs help with workspace-isolation
  guarantees and look better in URLs/exports.
- **`Workspace.slug` — auto-generated or user-chosen?** v1 suggestion:
  auto from name on save; allow override later.

---

## Queued investigations

- **Inventory generator** (`shell/manage.py inventory`). Emits the
  Django route count, model count, app inventory as JSON so
  `docs/CHARACTER_OS_INVENTORY.md` becomes regenerable. Wire in
  SESSION 107 after the models land, or defer to SESSION 108.
- **Design doc §6.7.5 step 3 correction.** The subtree command
  written in the design doc is slightly wrong (would import all
  of runway-hackathon, not just `backend/`). Actual fix used
  `git subtree split` first. Worth a small edit to the design doc.

---

## AI / assistant context

- Last session: SESSION 106 — repo bootstrap + scaffold.
- Phase 0 + Phase 1 (scaffold half) complete. Now starting Phase 1
  (data model half).
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
- `docs/TRUST_CALIBRATION.md` still empty.
