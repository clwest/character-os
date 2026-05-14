---
title: "Session 119 — Custom email-as-PK User model"
date: 2026-05-13
status: complete
session: 119
previous_handoff: ./SESSION_118_SPOKESPERSON_DETAIL.md
---

# Session 119 — Replace the SESSION 116 band-aid with a real User model

## TL;DR

- **What shipped:** `apps.accounts.User` — custom email-as-PK User
  model replacing Django's stock `auth.User`. No username column.
  `AUTH_USER_MODEL = "accounts.User"` in settings. The SESSION 116
  `WorkspaceAccountAdapter` band-aid is deleted. Migrations + DB
  wiped + regenerated cleanly. **All 5 Playwright specs pass + all
  4 backend smokes pass** against the new model with effectively
  zero SPA changes.
- **What's blocking next:** Nothing. Option B (S-06 create-spokesperson
  flow) is the natural next slice.
- **What's in a weird state:** Three `ACCOUNT_*` legacy settings
  (`ACCOUNT_AUTHENTICATION_METHOD`, `ACCOUNT_USERNAME_REQUIRED`,
  `ACCOUNT_EMAIL_REQUIRED`) emit deprecation warnings but are
  **required** for allauth's `runserver`-time system check to pass.
  Their newer counterparts (`ACCOUNT_LOGIN_METHODS`,
  `ACCOUNT_SIGNUP_FIELDS`) are also set. Both must coexist until
  allauth removes the legacy keys.

---

## What changed (file-by-file)

### `shell/apps/accounts/models.py`

The headline addition. New `User` model:

- Subclasses `AbstractBaseUser + PermissionsMixin`. Stock Django
  user pieces minus the username field.
- `email = models.EmailField(unique=True)`. The only identifier.
- `is_staff`, `is_active`, `date_joined` for Django admin
  compatibility.
- `USERNAME_FIELD = "email"`, `REQUIRED_FIELDS = []`.
- Custom `UserManager` with `_create_user` / `create_user` /
  `create_superuser` (the stock Django pattern but keyed on email).
- `get_full_name()` returns the email — allauth's serializer reads
  this for its `display` field. `get_short_name()` returns the
  email prefix.

`default_workspace_for(user: User) -> Workspace | None` got a type
annotation upgrade.

### `shell/character_os/settings.py`

Three changes:

1. **`AUTH_USER_MODEL = "accounts.User"`** — the load-bearing
   switch.
2. **`ACCOUNT_USER_MODEL_EMAIL_FIELD = "email"`** — tells allauth
   where to find the email on our custom model.
3. **Legacy allauth settings restored** with a comment. Required
   because allauth's `runserver`-time check evaluates the legacy
   defaults (which assume username) even when the newer keys
   override behaviour. The newer keys (`LOGIN_METHODS`,
   `SIGNUP_FIELDS`) are also set. Both must coexist until allauth
   drops the legacy keys.
4. **`ACCOUNT_ADAPTER = "...WorkspaceAccountAdapter"` removed** —
   the band-aid is gone.

### `shell/apps/accounts/adapter.py` (deleted)

The SESSION 116 band-aid that populated `username` from
`sha256(email)[:24]`. No longer needed; deleted.

### `shell/apps/accounts/admin.py`

Registers the custom User in the Django admin via Django's stock
`UserAdmin` subclass. Email-keyed; password change form works
through the admin. Workspace + Membership admin search_fields
updated from `*__username` to `*__email`.

### `shell/apps/accounts/serializers.py`

`MembershipSerializer.user_username` → `user_email`.
`WorkspaceSerializer.owner_username` → `owner_email`. Same field
name change in `fields` + `read_only_fields`.

### `shell/apps/accounts/views.py`

`me` view drops `user.username` from the response. (The SPA's zod
schema dropped the matching field — see `web/src/lib/api/workspaces.ts`.)

### `shell/apps/accounts/signals.py`

`_suggested_workspace_name` drops the `user.username` fallback
branch — there is no username on the custom model. Email-prefix
remains the only naming source.

### `shell/apps/accounts/management/commands/smoke_headless_auth.py`

Tolerates both `login_methods` (newer config response key) and
`authentication_method` (older key allauth emits when
`ACCOUNT_AUTHENTICATION_METHOD` is set). Useful drift hedge.

### `shell/pyrightconfig.json`

Added `reportIncompatibleVariableOverride: "none"` and
`reportAttributeAccessIssue: "warning"`. Same class of
cross-stack ORM noise we've been silencing throughout the
project — `User.REQUIRED_FIELDS` override of `AbstractBaseUser`'s
type, reverse-relation attribute access (`user.owned_workspaces`,
`user.memberships`).

### `web/src/lib/api/workspaces.ts`

`meSchema` drops the `username` field. The SPA didn't render it
anywhere; only the schema needed updating.

### `apps/*/migrations/0001_initial.py` (all regenerated)

Full migration reset. The original migrations FK-referenced
`AUTH_USER_MODEL` which resolved to `auth.User`. Swapping
`AUTH_USER_MODEL` mid-project requires either careful
hand-ordered migrations OR a clean DB + regenerated history. The
project is pre-launch / 0-customer / local-only, so the clean
path is correct.

What got regenerated (all 5 apps):
- `accounts.0001_initial` — `User` + `Workspace` + `Membership`
  + FK + unique_together
- `billing.0001_initial` — `Subscription`
- `conversations.0001_initial` — `ConversationThread`
- `spokespeople.0001_initial` — `Spokesperson`
- `videos.0001_initial` — `Video`

### `shell/db.sqlite3` (recreated)

Fresh DB. All previous test users / spokespeople / videos gone.
This is fine — there were 0 real users.

---

## Verification gates

- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — clean.
- `python manage.py smoke_headless_auth` — PASS. **The Phase 1
  cascade still fires** (User + Workspace + Membership +
  Subscription auto-created on signup).
- `python manage.py smoke_avatar` — PASS.
- `python manage.py smoke_voice` — PASS.
- `python manage.py smoke_video` — PASS (~13 s in mock mode,
  Celery worker required).
- `pnpm build` — clean.
- `pnpm test` — 3 vitest passes.
- `pnpm e2e` — **5 passes** (2 auth + 2 dashboard + 1 spokesperson).
- `python manage.py inventory` — regen clean.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The band-aid removal was the entire point

`WorkspaceAccountAdapter` (SESSION 116) papered over a real Django
model invariant: `auth_user.username` is `UNIQUE`, but allauth
signed everyone up with `username=""`. The first signup worked;
the second collided. The band-aid populated `username` from a
hash of the email so multiple email-only users could coexist.

The proper fix is what SESSION 119 did: a custom User model
where email is the only identifier and there's no username column
at all. Total LOC change: model definition (+92), settings (+2,
-7), adapter file (-58), signals (-4), admin (+27 reformatted),
serializers (~12 renamed), views (-1), tests (-1). Net ~+50 lines
of source vs. the band-aid; net **-1 latent product bug**.

### "Cleanest path" is sometimes "wipe the DB"

Django's docs explicitly warn against swapping `AUTH_USER_MODEL`
mid-project. The recommended migration paths are all complex
(hand-ordered migrations + data migration + careful
constraint juggling). For a pre-launch project with 0 customers
and 0 real data, **the cleanest path is to wipe DB + migrations
+ regenerate**. The whole operation took ~30 seconds. Production
would require a different playbook; for v1 dev work, this is the
right move.

### Allauth's legacy/new setting overlap is real

`ACCOUNT_LOGIN_METHODS` (newer) and `ACCOUNT_AUTHENTICATION_METHOD`
(older) are supposed to be equivalent. They're not, in practice:

- `manage.py check` evaluates only the newer key when both are
  set, ignoring the older default.
- `manage.py runserver` evaluates both, and the older key's
  default ("username_email") fails when there's no username
  field.

The fix: set both, accept the deprecation warnings. Remove the
older ones when allauth drops them entirely (probably 1-2 major
versions out).

### SPA needed effectively zero changes

The only SPA change was dropping `username: z.string()` from the
`meSchema` in `web/src/lib/api/workspaces.ts`. Everything else —
the dashboard, the detail page, the auth flow, the API wrappers —
worked through the new model unchanged. That's the **boundary
discipline** the contract docs lock in paying off: backend can
swap its user model entirely and the SPA inherits cleanly.

### The Phase 1 cascade is structurally portable

`apps/accounts/signals.py::ensure_default_workspace` listens to
`post_save(settings.AUTH_USER_MODEL)`. When the User model
changed, the signal handler kept working because it never
depended on `auth.User` specifically — it reads `instance.email`
+ falls through to "My workspace". This was SESSION 107's design
discipline paying off four sessions later.

---

## SESSION 120 — entry point

See `00-START-NEXT-SESSION.md`. The recommended next slice is
**Option B: S-06 create-spokesperson flow**, now unblocked by the
User model cleanup. The form needs the SESSION 116 backend
(already supports `portrait_data_uri`); on submit it redirects to
the SESSION 118 spokesperson detail route.

---

## AI notes

- The "wipe migrations + DB" path is destructive but reversible
  (local-only, all in source control). The operator's explicit
  green-light in the start-here doc made the decision easy. Future
  similar operations should also be documented in advance.
- The `ACCOUNT_AUTHENTICATION_METHOD` deprecation dance was the
  only real friction point. Worth flagging in the AI notes for
  next session: **don't try to clean up allauth deprecations
  during a User-model migration**; the legacy/new settings overlap
  is not load-bearing for the migration itself but causes
  intermittent system-check failures that make the work feel
  broken.
- The `smoke_voice` auto-create-spokesperson persists rows across
  runs (auto-create is outside the transaction.atomic block in
  smoke_voice.py — different from smoke_avatar.py's pattern).
  Pre-existing ergonomic issue, not new. Worth flagging in the
  queued investigations.
- Five sessions of "Phase 1 cascade fires through every auth
  surface" assertion paid off here. The signal handler was the
  one piece of pre-existing infrastructure I most worried about
  breaking; it didn't.
- Watching the back-and-forth of "remove legacy settings → check
  passes → runserver fails" was instructive. The lesson is:
  `manage.py check` and `manage.py runserver`'s check pass differ
  for some Django apps. Don't trust one without the other when
  doing settings cleanups.
