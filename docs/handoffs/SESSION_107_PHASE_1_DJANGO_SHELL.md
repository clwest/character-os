---
title: "Session 107 — Phase 1 Django shell substantively complete"
date: 2026-05-13
status: complete
session: 107
previous_handoff: ./SESSION_106_CHARACTER_OS_REPO_BOOTSTRAP.md
---

# Session 107 — Phase 1 Django shell substantively complete

## TL;DR

- **What shipped:** Five Phase-1 slices in one session — core data
  model, Django↔FastAPI media-engine client, DRF API surface,
  email/password auth + auto-Workspace + `/api/me/`, and the
  tier-based billing layer with 402-Payment-Required gating on the
  Video + Spokesperson endpoints. Phase 1 of the design doc §7 is
  substantively done.
- **What's blocking next:** Nothing. Phase 2 (media-engine data
  model migration to make the FastAPI service stateless) is the
  clear next priority. Detailed start-here in
  `00-START-NEXT-SESSION.md`.
- **What's in a weird state:** Pyright warnings about
  `apps.* could not be resolved` are noise — runtime imports work
  fine, `python manage.py check` is clean every time, and Django
  loads every model. A `shell/pyrightconfig.json` would silence them
  (parked as a follow-up); not blocking anything functional.

---

## What Shipped

### Slice 1 — Core data model (commit `1b80ebf`)

The schema for the new mental model:

  - `apps.accounts.Workspace` — UUID id, name, slug (auto-from-name
    on save with dedup), owner (FK to `auth.User`, `on_delete=PROTECT`),
    members (M2M through `Membership`), timestamps.
  - `apps.accounts.Membership` — User ↔ Workspace through-model with
    `Role` enum (`owner`/`admin`/`editor`/`viewer`). v1 always uses
    `owner`; the other roles exist for Agency tier (design doc §6.6).
  - `apps.accounts.default_workspace_for(user)` — helper that returns
    the user's primary workspace (owned first, oldest membership as
    fallback).
  - `apps.spokespeople.Spokesperson` — UUID id, workspace FK, name,
    `business_brief` (TextField — promoted up from the legacy
    per-campaign `brief_prompt` per design doc §4.3), `Status` enum,
    media-engine placeholders (`runway_avatar_id`,
    `runway_avatar_status`, `portrait_path`, `voice_id` — empty
    until Phase 2 wires the avatar pipeline). Unique
    `(workspace, name)`.
  - `apps.videos.Video` — UUID id, spokesperson FK, title, brief
    (one-line override of spokesperson default per §4.4), `Kind` enum
    covering all 19 output shapes carried forward from the legacy
    `OutputKind`, `Status` enum, output_path, duration_seconds,
    `tags` JSONField (hidden in v1 UI per §4.4), media-engine task id,
    error_message, completed_at. Indexed on (spokesperson,
    -created_at) and status.
  - `apps.conversations.ConversationThread` — UUID id, spokesperson
    FK, title, timestamps. v1 stub; transcript/message model is a
    follow-up slice.

Admin registered for all four models. Migrations applied:
`accounts.0001`, `spokespeople.0001`, `videos.0001`,
`conversations.0001`.

Smoke gate — interactive shell traversal:
`User → owns → Workspace → has → Spokesperson → has → Video / Thread`
chain resolves cleanly; auto-slug works (`"Donkey Betz Coffee"` →
`"donkey-betz-coffee"`); `default_workspace_for(user)` returns the
owned workspace.

### Slice 2 — Internal Django→FastAPI client (commit `6fe96f1`)

Architectural boundary between Django shell and FastAPI media engine
(design doc §6.2). No imports cross the line; only HTTP/JSON.

  - `character_os/clients/media_engine.py` — `MediaEngineClient` wraps
    `httpx.Client`, reads `MEDIA_ENGINE_BASE_URL` from settings,
    context-manager safe. `health_check()` returns a `HealthStatus`
    dataclass parsing `/health` (status, service, mock flags, extras).
    `request()` normalizes timeout / connect / 4xx / 5xx / non-JSON
    failures into `MediaEngineError(message, status_code, response_text)`.
  - `apps.spokespeople.management.commands.ping_media_engine` —
    `python manage.py ping_media_engine` (human or `--json`), exit 0
    on healthy, exit 1 on anything else. Lives in spokespeople (most
    natural consumer) because Django requires `management/commands/`
    inside an `INSTALLED_APPS` app, not at the project root.

Smoke gate (both directions verified):

```bash
# FastAPI offline
python manage.py ping_media_engine
→ "media engine UNREACHABLE: unable to reach media engine at http://localhost:8001"
→ exit 1

# FastAPI live (uvicorn app.main:app --port 8001 in mock mode)
python manage.py ping_media_engine
→ "✓ adspark-studio reachable, status=ok"
   openai_mock = True, runway_mock = True, ...
→ exit 0

python manage.py ping_media_engine --json
→ {"ok": true, "status": "ok", "service": "adspark-studio", ...}
```

### Slice 3 — DRF API for the core models (commit `45b36de`)

Six viewsets exposing the workspace-scoped REST surface.

  - `character_os/permissions.py` — `IsWorkspaceMember` resolves the
    workspace an object belongs to (direct FK for Workspace +
    Spokesperson; through `spokesperson.workspace` for Video + Thread)
    and gates by Membership role. Read = any role; write = owner only.
  - `character_os/urls.py` — wires the four app routers under `/api/`.
  - `character_os/settings.py` — adds testserver/localhost/127.0.0.1
    to `ALLOWED_HOSTS` so APIClient + dev server work.
  - Per-app `serializers.py` + `views.py` + `urls.py`:
    - `WorkspaceViewSet` (full CRUD; `perform_create` auto-creates
      owner Membership atomically; `.members` custom action lists
      memberships)
    - `MembershipViewSet` (read-only, scoped to requesting user)
    - `SpokespersonViewSet` (full CRUD; `validate_workspace` rejects
      non-members)
    - `VideoViewSet` (full CRUD; `validate_spokesperson` rejects
      cross-workspace)
    - `ConversationThreadViewSet` (same pattern)

Mounted endpoints (24 surface-level URL patterns):

```
GET    POST   PUT   PATCH  DELETE  /api/workspaces/[{id}/]
GET                                /api/workspaces/{id}/members/
GET                                /api/memberships/[{id}/]
GET    POST   PUT   PATCH  DELETE  /api/spokespeople/[{id}/]
GET    POST   PUT   PATCH  DELETE  /api/videos/[{id}/]
GET    POST   PUT   PATCH  DELETE  /api/conversations/[{id}/]
```

Smoke gate — two users, two workspaces, cross-tenant isolation:

  - alice POST `/api/workspaces/` → 201, owner Membership auto-created,
    role="owner" surfaces in response.
  - bob GET `/api/workspaces/` → only sees his own.
  - bob POST `/api/spokespeople/` with `workspace=alice_ws` → 400.
  - bob GET `/api/spokespeople|videos|conversations/` → all empty.
  - bob GET `/api/workspaces/{alice_ws}/` → 404 (queryset filtered).
  - unauthenticated → 403.
  - alice PATCH her spokesperson → 200, bob PATCH alice's → 404.

### Slice 4 — Auth (commit `7d6279b`)

Real authentication via `django-allauth`. Email/password works
end-to-end; Google OAuth scaffolded but inactive.

  - `django-allauth[socialaccount]` installed in `shell/.venv`.
  - settings wires `SITE_ID=1`, `AccountMiddleware`, dual auth
    backends (ModelBackend + allauth), `ACCOUNT_LOGIN_METHODS={"email"}`
    (no usernames — non-marketer audience per §1.2),
    `ACCOUNT_SIGNUP_FIELDS=[email*, password1*, password2*]`,
    `ACCOUNT_EMAIL_VERIFICATION="optional"` (tighten before launch).
  - `SOCIALACCOUNT_PROVIDERS["google"]` scaffolded with PKCE on. Will
    function once a `SocialApp` row exists with real credentials.
  - `LOGIN_REDIRECT_URL = "/api/me/"`. Dev `EMAIL_BACKEND` is console.
  - `urls.py` mounts `/accounts/` at `allauth.urls`.
  - `apps.accounts.signals.ensure_default_workspace` — `post_save` on
    `AUTH_USER_MODEL`. Any path that creates a user (ORM, allauth
    signup, OAuth, admin) auto-creates `"$Email's workspace"` +
    owner Membership in one transaction. Idempotent.
  - `apps.accounts.views.me` — DRF function view, `GET /api/me/`,
    returns current user + `default_workspace: {id, name, slug, role}`.
    The SPA's first call after auth.

Smoke gate — five auth paths exercised:

  1. `User.objects.create_user(...)` → Workspace auto-created.
  2. POST `/accounts/signup/` with email+password → 302, email
     printed to console, Workspace auto-created.
  3. Unauthenticated GET `/api/me/` → 403.
  4. Authenticated GET `/api/me/` → `{email, default_workspace:
     {id, name, slug, role: "owner"}}`.
  5. POST `/accounts/logout/` → 302.

### Slice 5 — Tier-based billing (commit `9f28b78`)

Subscription model + tier-limit middleware + 402-on-cap gating.

Scope decision: deferred `dj-stripe` install. The architecture (a
Subscription model with Stripe-shaped landing fields, tier limit
enforcement, usage-meter API) is what makes the rest of the system
"monetization-aware." Real Stripe wiring is a follow-up slice once
credentials are available.

  - `apps.billing.models.Subscription` — OneToOne workspace, Tier
    enum (`starter`/`pro`/`agency`), Status enum (`trialing`/
    `active`/`past_due`/`canceled`/`unpaid`), period dates,
    `stripe_customer_id` + `stripe_subscription_id` (empty —
    dj-stripe will fill).
  - `apps.billing.models.TIER_LIMITS` — canonical pricing table:
    Starter $29 (10 vids / 1 spoke / 1 seat), Pro $79 (30/3/1),
    Agency $199 (unlim / unlim / 5).
  - `apps.billing.signals.ensure_default_subscription` — `post_save`
    on Workspace creates a Starter+trialing Subscription. Wired via
    `BillingConfig.ready()`.
  - `apps.billing.services` — `get_usage(workspace) → Usage` and
    `check_video_limit / check_spokesperson_limit` raising
    `TierLimitExceeded` with `{code, current_tier, suggested_tier,
    message, ...}` payload.
  - `apps.videos.VideoViewSet.create` + `apps.spokespeople.
    SpokespersonViewSet.create` — override DRF default to call the
    check first, return 402 with the payload before serializer
    validation runs. Avoids burning media-engine credits on
    over-limit requests.
  - `apps.billing.views`:
    - `GET /api/billing/subscription/?workspace=<uuid>` (auth) —
      returns workspace + tier + usage. Defaults to user's primary
      workspace.
    - `GET /api/billing/tiers/` (no auth) — returns the public
      pricing table. Powers the marketing site's pricing page.
  - `apps.billing.urls` wired into `/api/`.

Smoke gate — full lifecycle through the API:

  - Starter (10 vid / 1 spoke):
    - 10 videos: all 201.
    - 11th video: 402, `code=video_limit_reached`,
      `suggested_tier=pro`, `message="You've used all 10 videos in
      your Starter plan this month."`
    - 2nd spokesperson: 402, `code=spokesperson_limit_reached`.
  - Upgrade to Pro (30/3/1):
    - 11th video: 201.
    - 2nd + 3rd spokesperson: 201.
    - 4th spokesperson: 402.
  - Upgrade to Agency (unlimited):
    - 4th + 5th + 6th spokesperson: all 201.
    - Final usage: `tier=agency, videos=11/None, spokes=6/None`.

---

## What Didn't (and Why)

### dj-stripe install — deferred to a follow-up slice

- **Attempted:** start integrating `dj-stripe>=2.9` as the source of
  truth for Stripe Customer + Subscription objects.
- **Why it didn't go in:** dj-stripe requires real Stripe credentials
  (test or live secret keys) at install time to be useful, and it
  pulls in a substantial migration set + webhook surface. The
  architecture we built (`Subscription` with `stripe_*` landing-zone
  fields, the `TIER_LIMITS` table, the `check_*_limit` services) is
  already monetization-aware — `dj-stripe` slots in cleanly when
  credentials land.
- **Next attempt:** when the operator has a Stripe account (test
  mode is fine), install dj-stripe, add `STRIPE_TEST_PUBLIC_KEY`,
  `STRIPE_TEST_SECRET_KEY`, `DJSTRIPE_WEBHOOK_SECRET` to env, point
  `dj-stripe` at the existing `Subscription` model via the
  `stripe_subscription_id` field. Webhook handler updates the local
  Subscription rows from Stripe events.

### Pyright noise — not addressed, parked

- **What:** every `from apps.<other_app>.models import ...` triggers
  a Pyright "Import could not be resolved" warning. So does
  `from character_os.permissions import IsWorkspaceMember`. Plus
  DRF's `get_queryset` return-type complaints from `BasePermission`
  + `GenericAPIView` having `Never`/`Literal[True]` declared return
  types.
- **Why it doesn't matter:** runtime imports work in every smoke
  test, every Django + DRF view loads, every signal fires, every
  migration runs. Pyright is missing the Django path config that
  tells it `shell/` is on `sys.path`.
- **Fix:** drop a `shell/pyrightconfig.json` with
  `{"include": ["."], "extraPaths": ["."]}`. ~2-line slice. Parked.

### Real Google OAuth — needs credentials

- **What:** `SOCIALACCOUNT_PROVIDERS["google"]` is configured but
  `/accounts/google/login/` will 500 until a `SocialApp` row exists
  with a real `client_id` + `client_secret` from
  `https://console.cloud.google.com/`.
- **When:** once the operator wants to test signup-with-Google. Test
  credentials are free; takes ~5 min to set up an OAuth consent
  screen + create the credentials. The structure of `allauth.urls` +
  `SOCIALACCOUNT_PROVIDERS` + the auto-Workspace signal already
  handles Google-driven user creation correctly — the only piece
  missing is the credentials.

### allauth.headless — JSON-only signup/login for the SPA

- **What:** `/accounts/signup/` and `/accounts/login/` currently
  render allauth's built-in HTML templates. The SPA wants JSON
  endpoints that return a session cookie + user payload.
- **When to wire:** Phase 3 when the SPA work starts. allauth 65+
  ships `allauth.headless` which provides JSON endpoints
  (`/_allauth/browser/v1/auth/signup/`,
  `/_allauth/browser/v1/auth/login/`) configured by adding
  `"allauth.headless"` to `INSTALLED_APPS` and including
  `allauth.headless.urls` in `urls.py`. ~3-line change.

---

## AI Notes

This session was a five-slice marathon — data model → media-engine
boundary → DRF API → auth → billing — landed in one push because
each slice is small and they stack cleanly. The operator's "keep
going" directive let me chain them; if any had been blocked I'd
have stopped, but the boundaries were natural.

A few judgment calls worth flagging for the trust calibration log:

  1. **Skipped dj-stripe** even though `pyproject.toml` lists it as
     a dep. Reasoning: installing it without real Stripe credentials
     adds migrations + webhook surface for no observable functionality.
     The tier-gating logic stands alone. Operator can push back if
     they wanted the dj-stripe rows present even as no-ops.
  2. **HTTP 402 (Payment Required)** for tier-limit responses,
     instead of 403 (Forbidden) or 400 (Bad Request). Reasoning: 402
     is the semantically correct status — RFC 9110 reserves it for
     exactly this case. Some frontends choke on 402; if SPA tooling
     has trouble, swap to 403 + `code: tier_limit_reached` and the
     payload shape stays identical.
  3. **`apps.spokespeople.management.commands.ping_media_engine`**
     instead of a dedicated `apps.core` app for project-level
     commands. Reasoning: spokespeople is the most natural consumer
     of the media-engine client (avatars + videos eventually run
     through there). If we add more project-level commands, an
     `apps.core` is the right home; until then this is fine.
  4. **Console email backend** in dev. Real email backends
     (Mailgun/Postmark/SES) wire as a settings change pre-launch.

Phase 1 is substantively done. The shell can:
  - sign up a user, auto-create their workspace, attach them as
    owner, default them to Starter tier
  - serve a workspace-scoped REST API with multi-tenant isolation
  - gate video + spokesperson creation by tier with a structured
    upgrade payload
  - reach the FastAPI media-engine over HTTP with normalized errors
  - present a usage meter via `/api/billing/subscription/`

For SESSION 108 / Phase 2, the work shifts from "Django shell" to
"FastAPI media-engine refactor." The big question is whether the
operator wants to start with the data migration (campaigns.json →
Django records) or with the media-engine API contract redesign
(stateless job-spec endpoints). Recommendation: contract first.
Once the new contract is locked, the data migration is a one-shot
script.
