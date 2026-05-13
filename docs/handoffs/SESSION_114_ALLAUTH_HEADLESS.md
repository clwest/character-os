---
title: "Session 114 — allauth.headless wired + auth surface JSON-ready"
date: 2026-05-13
status: complete
session: 114
previous_handoff: ./SESSION_113_DESIGN_LOCK_RESOLVED.md
---

# Session 114 — `allauth.headless` end-to-end

## TL;DR

- **What shipped:** `allauth.headless` mounted at `/_allauth/`,
  configured for the `browser` client (session-cookie auth — the
  shape the Phase 3 SPA needs). 19 new JSON-API routes registered.
  Phase 1's auto-Workspace + Membership + Subscription cascade
  fires through the headless flow exactly the same way it fires
  through the HTML one — load-bearing assertion verified by smoke
  test. The legacy `/accounts/` HTML surface stays alive so the
  Django admin + the old-style pages keep working.
- **What's blocking next:** Nothing. SPA scope-lock is the next
  natural step now that the auth surface speaks JSON.
- **What's in a weird state:** None this session. Two pyright
  warnings (one in inventory.py, one residual from earlier) are
  the same residual-by-design noise the SESSION 111
  pyrightconfig accepted at warning level.

---

## What changed (file-by-file)

### `shell/character_os/settings.py`

Three additions, totalling ~25 lines:

1. `INSTALLED_APPS` — added `"allauth.headless"` between
   `"allauth.account"` and `"allauth.socialaccount"`.
2. `HEADLESS_ONLY = False` — keep both surfaces alive during the
   Phase 3 SPA transition. Once the SPA fully replaces the HTML
   admin-facing pages (probably Phase 4 or later), flip to True.
3. `HEADLESS_CLIENTS = ("browser",)` — only enable session-cookie
   auth today. The `app` client (token-based, for mobile) defers
   indefinitely; design lock §6 says native apps are deferred.
4. `HEADLESS_FRONTEND_URLS = {...}` — where allauth redirects
   after email-verify / password-reset / account-confirm. Points
   at SPA routes that don't exist yet (the SPA isn't built);
   the JSON API still works regardless. The SPA wires these
   routes when Phase 3 lands.

### `shell/character_os/urls.py`

One new line: `path("_allauth/", include("allauth.headless.urls"))`.
Mounts the entire headless router under `/_allauth/`. Allauth
itself splits sub-paths by client type:

- `/_allauth/browser/v1/config` — public auth config
- `/_allauth/browser/v1/auth/session` — current session state
- `/_allauth/browser/v1/auth/login` — JSON login
- `/_allauth/browser/v1/auth/signup` — JSON signup
- `/_allauth/browser/v1/auth/password/...` — password flows
- `/_allauth/browser/v1/account/email` — email verification
- ...etc, 19 routes total

### `shell/apps/accounts/management/commands/inventory.py`

Tiny extension: added `_allauth/` to the URL prefix bucketing so
the inventory shows the count under its own row instead of
"other". Same one-line pattern as the other prefixes.

### `shell/apps/accounts/management/commands/smoke_headless_auth.py` (new)

`python manage.py smoke_headless_auth`. The first SPA-facing
smoke test. Uses Django's `Client` (no live server needed)
because the headless surface is pure JSON over HTTP — `Client`
is the right transport. Exercises:

1. `GET /_allauth/browser/v1/config` — public auth config; asserts
   `is_open_for_signup=True` and `login_methods=["email"]`.
2. `GET /_allauth/browser/v1/auth/session` — unauthenticated;
   asserts 401 with flows `["login", "signup"]`.
3. `POST /_allauth/browser/v1/auth/signup` — JSON signup;
   asserts 200 and the email-verification message lands on the
   console (`EmailBackend = console.EmailBackend` in dev).
4. **Phase 1 cascade verification** — the load-bearing
   assertion. Confirms the post_save signal handlers fired:
   - `User` row exists
   - `Workspace` auto-created with the user as owner
   - `Membership` row with `role="owner"`
   - `Subscription` row with `tier="starter"`, `status="trialing"`
5. `GET /_allauth/browser/v1/auth/session` again — now
   authenticated; asserts 200 and `is_authenticated=True`.

Cleanup runs CASCADE-delete on the Workspace (clears Membership
+ Subscription) and the User, unless `--keep`.

### `docs/CHARACTER_OS_INVENTORY.md`

Regenerated. URL count 150 → 169 (the 19 new headless routes).
The new `_allauth/` prefix appears in the buckets table. Total
LOC bumped slightly (smoke command + inventory tweak).

---

## Verification gates

- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — exit 0.
- `python manage.py inventory` (with media-engine reachable) —
  emits 5.4 KB Markdown, FastAPI routes still at 93, URL routes
  now 169 with `_allauth/` bucketed cleanly.
- `python manage.py smoke_headless_auth` — PASSED end-to-end:
  config + 401 unauth + 200 signup + cascade verified + 200 auth.
- Hygiene scan — clean.

---

## Architectural notes worth remembering

### The Phase 1 signal handler is the foundation

The reassuring result of this session: SESSION 107's
`apps.accounts.signals.ensure_default_workspace` (and the matching
billing signal handler) fire **regardless of which auth surface
created the user**. HTML signup, JSON signup, Django admin, a
shell-typed `User.objects.create()` — all routes through
`post_save(User)` and all get the workspace cascade. Headless
inheriting this for free is the entire point of building on
allauth: the auth library is a transport, our domain logic isn't.

This is what "Phase 1 done" actually buys us — every future auth
surface gets the cascade automatically.

### The `_allauth/` prefix is deliberate

Three considerations:

1. **Namespace separation.** `/accounts/` stays the HTML surface
   (Django admin + legacy pages). `/api/` stays the DRF-managed
   resource surface (workspaces, spokespeople, videos). `/_allauth/`
   is its own thing — JSON auth, owned by allauth, mounted under
   a leading-underscore prefix to mark "internal plumbing the SPA
   uses."
2. **Future-proof for the app client.** When mobile lands, it'll
   mount under `/_allauth/app/` automatically — no URL change
   needed, just `HEADLESS_CLIENTS = ("browser", "app")`.
3. **Reads well in CORS audit.** When CORS opens up to the SPA's
   origin, the allowed paths are obviously `/_allauth/*` +
   `/api/*` and nothing else. Less surface to misconfigure than
   exposing `/accounts/` to a non-Django origin.

### Email-verification redirect URLs are scaffolded, not load-bearing

The `HEADLESS_FRONTEND_URLS` config points at SPA routes
(`/account/verify-email/{key}` etc.) that won't exist until
Phase 3. That's fine — they're only used **when allauth sends a
verification email** with a link. Since `ACCOUNT_EMAIL_VERIFICATION
= "optional"` in dev, the link doesn't have to resolve for the
sign-up flow to complete. The smoke test confirms this — signup
returns 200 even though the verification email points at a
non-existent SPA route.

When Phase 3 starts shipping SPA routes, these targets get
real implementations. Until then, they're documentation.

### The `_allauth/` count is going to grow

19 routes today. When we enable Google OAuth via allauth.headless
(probably alongside `dj-stripe` install once credentials arrive),
the `socialaccount` headless module activates and adds more.
Same for MFA when that lands (deferred). The inventory tracks
this automatically.

---

## SESSION 115 — entry point

`00-START-NEXT-SESSION.md` recommends Phase 3 SPA scope-lock as
the next natural slice. The auth surface is now JSON-ready; the
design lock is in place; the contract is feature-complete.
Everything technical is unblocked. The remaining question is
scope discipline.

---

## AI notes

- This session was textbook: small change, clear contract, real
  smoke test, all gates clean, no surprises. Roughly 45 minutes
  start-to-finish.
- The pyright NoReturn cleanup on `_fail` was a nice example of
  the pyrightconfig working as intended — real type errors
  (Optional access on `.first()` results) surfaced as warnings,
  I tightened the code, warnings cleared. That's the **right**
  pyright signal-to-noise; SESSION 111's config didn't silence
  truth, just silenced repeated false alarms.
- The `--keep` option on the smoke commands is becoming a real
  pattern (4 commands now). Worth canonicalising into a shared
  helper when a fifth lands, per the SESSION 110 note.
- The "Phase 1 cascade fired" assertion is the most important
  thing this smoke does — and the one a future test framework
  must keep. Auth surfaces change; the cascade is the
  multi-tenant invariant.
