---
title: "Session 108 — Media-engine internal API contract + avatar slice"
date: 2026-05-13
status: complete
session: 108
previous_handoff: ./SESSION_107_PHASE_1_DJANGO_SHELL.md
---

# Session 108 — Phase 2 contract lock + first internal endpoint

## TL;DR

- **What shipped:** Phase 2 Option A (contract first). The internal
  API contract is locked in
  `docs/design/MEDIA_ENGINE_INTERNAL_API.md`, the first endpoint
  (`POST /internal/avatars/`) is live on the FastAPI media-engine,
  the Django shell talks to it via a new
  `MediaEngineClient.create_avatar(...)` wrapper, and
  `SpokespersonViewSet.create` fires the call inline when a portrait
  data URI is in the payload. End-to-end smoke test (`python
  manage.py smoke_avatar`) passes against the mock-mode media-engine
  — avatar id and status persist back onto the Spokesperson row.
- **What's blocking next:** Nothing. The next slice can be any of
  the planned `/internal/*` verbs (voice clone, video generation, or
  the avatar status poll). See "SESSION 109 entry point" below.
- **What's in a weird state:** Two pyright warnings on `views.py` /
  `serializers.py` — DRF `GenericAPIView.get_queryset` "Never" return
  drift, and the cross-app `obj.videos` reverse-FK pyright can't
  resolve. Both are the same flavour of pre-existing noise the
  SESSION 107 handoff flagged; runtime is clean.

---

## What changed (file-by-file)

### `docs/design/MEDIA_ENGINE_INTERNAL_API.md` (new)

The full Phase 2 contract: pure JSON in/out, stateless service,
versionless URL surface, normalised error shape (`{error, code}`),
mock-mode behaviour, relationship to the legacy `/api/*` surface
during the transition. Lists the six planned `/internal/*` verbs
(avatars × 2, voices × 2, videos × 2); SESSION 108 implements just
`POST /internal/avatars/`. Future endpoints land one at a time as
Django features need them.

The contract's load-bearing rules — these are the constraints to
preserve when adding new endpoints:

1. JSON only at the boundary. Binary payloads ride as `data:` URIs.
2. Media-engine holds no state across calls (Django is the system of
   record).
3. Mock mode is a first-class output (every response carries
   `mock_mode: bool`).
4. Errors normalise to `{error, code}`.
5. Idempotent in mock mode, not in real mode (Runway assigns ids).

### `media-engine/app/routers/internal.py` (new)

`POST /internal/avatars/` — accepts `{name, portrait_data_uri,
voice_preset?, personality?}`, decodes + validates the portrait
(mime allow-list, 5 MB cap), caches it under
`media-engine/data/_internal/avatars/<sha256>.png` (gitignored), and
either:

- **Mock mode (no Runway key):** Returns a deterministic
  `mock_avatar_<sha256(name+bytes)[:12]>` and a data-URI thumbnail.
- **Real mode:** Calls `_create_avatar_real` from the existing
  `character_studio_client` service so Runway-side behaviour stays
  identical to the legacy `/api/characters/{id}/create-avatar`
  route.

Errors land as 4xx/5xx with the contract's `{error, code}` shape.

### `media-engine/app/main.py`

Imports + `include_router(internal_router)`. Route count went 102 →
103.

### `shell/character_os/clients/media_engine.py`

Added `AvatarCreateResult` dataclass + `MediaEngineClient.create_avatar(
name, portrait_data_uri, voice_preset?, personality?
)`. Errors normalise through the existing `MediaEngineError`. Strict
response-shape parsing so contract drift fails loud.

### `shell/apps/spokespeople/serializers.py`

Added two write-only fields to `SpokespersonSerializer`:
`portrait_data_uri` (up to ~10 MB raw payload — the media-engine
side enforces the real 5 MB decoded cap) and `voice_preset`. Neither
hits the model; the viewset pops them out of `validated_data`
before save.

### `shell/apps/spokespeople/views.py`

Rewritten `perform_create` so that after `serializer.save()` lands
the row, if `portrait_data_uri` was supplied we call
`MediaEngineClient.create_avatar` synchronously and persist
`runway_avatar_id` / `runway_avatar_status` / `voice_id` /
`status="ready"` onto the instance. Failures persist
`runway_avatar_status="failed"` but never roll back the row — the
operator can retry from the UI later (Phase 3) without re-creating
the spokesperson.

Inline call is fine for SESSION 108. The mock-mode path is <50 ms
and the real-mode path is bounded by Runway's avatar creation (~20
s on the legacy route). Celery enters the picture only when video
generation joins this surface — long tasks need a fire-then-poll
shape, which the contract already accommodates via
`GET /internal/videos/{task_id}/`.

### `shell/apps/spokespeople/management/commands/smoke_avatar.py` (new)

`python manage.py smoke_avatar` — exercises the full pipeline
(viewset → client → media-engine → studio service → back through
the wire → persisted state). Defaults to a 1×1 transparent PNG so
the test is hermetic. Wraps the work in a `transaction.atomic()`
block that rolls back unless `--keep` is passed. Exits 0 on
ready/mock + populated `runway_avatar_id`; exits 1 on anything else.

Run output from SESSION 108's verification:

```
  ✓ media engine reachable (runway_mock=True)
  ✓ using workspace 'alices-workspace' (id=ba04d386-...)
  ✓ spokesperson row created id=a3095cb3-...
    runway_avatar_id     = 'mock_avatar_785b172fdd3d'
    runway_avatar_status = 'mock'
    status               = Spokesperson.Status.READY
✓ smoke test PASSED (row rolled back)
```

---

## Verification gates

- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — exit 0 (no schema changes;
  the new fields are write-only on the serializer).
- `python -c "from app.main import app; print(len(app.routes))"` —
  103 routes (was 102; new `/internal/avatars/` accounts for the
  delta).
- `python manage.py smoke_avatar` — PASSED.
- Hygiene scan — clean (no .env / media / mp4 / mp3 / png in tracked
  files).

---

## Architectural notes worth remembering

### The contract is the lever

The point of Option A wasn't "ship one endpoint" — it was "lock the
contract so every subsequent endpoint inherits the same
constraints." The five rules in
`docs/design/MEDIA_ENGINE_INTERNAL_API.md` §"Contract rules" are
load-bearing. New endpoints that break them (e.g. multipart upload
to `/internal/*`, state held across calls) compromise the
stateless-service property and make the Phase 3 deploy story harder
than it needs to be.

### Legacy `/api/*` surface stays untouched

The internal endpoints sit alongside the legacy 102 routes, not
on top of them. The runway-hackathon SPA keeps working through
Phase 2. When the Phase 3 SPA replaces it, legacy routes can be
retired in chunks — each gated on a matching `/internal/*` endpoint
shipping first. This is what makes Phase 2 ↔ Phase 3 a smooth
transition rather than a big-bang rewrite.

### Pyright noise is structural, not actionable

`shell/pyrightconfig.json` is the queued fix (still in the SESSION
107 "Queued investigations" list). The two new warnings in this
session (`get_queryset` Never return, `obj.videos` reverse-FK) are
the same class of cross-stack drift — fix when the pyrightconfig
slice lands, not piecemeal.

---

## SESSION 109 — entry point

`00-START-NEXT-SESSION.md` covers this in detail. Three equally
valid next slices:

1. **`POST /internal/videos/`** — the highest-leverage next endpoint.
   Unlocks the rest of the Spokesperson workflow (render an ad once
   the avatar exists). Needs a fire-then-poll shape since real-mode
   Runway video calls run 60-120 s.
2. **`POST /internal/voices/`** — voice clone. Lower stakes; needed
   for Pro / Agency tiers but not for the Starter happy path.
3. **`GET /internal/avatars/{id}/` poll** — the contract documents
   it but SESSION 108 didn't ship it because the synchronous create
   path returns terminal already. Worth adding when the create path
   needs to go async (which won't happen until video joins this
   surface).

Recommendation: **slice 1 (video)**. The fire-then-poll pattern is
the design decision the contract has been deferring; landing one
implementation forces the question and unblocks the other long-task
endpoints downstream.

---

## AI notes

- The contract spec absorbed about 60% of the session's wall-clock
  time and is the load-bearing artefact. Implementation reuses
  proven service code (`_create_avatar_real`) so the diff is small
  enough to audit by eye.
- The smoke test deliberately wraps everything in a `transaction.
  atomic()` + rollback sentinel so re-running it on a developer
  machine doesn't accumulate test rows. The `--keep` flag exists
  for the case where the operator wants to follow up by hand
  (admin UI, API probe).
- Pushed back zero times this session — the start-here doc's
  scope was already calibrated tightly, and Option A was the right
  call (confirmed during contract drafting; the JSON-only constraint
  surfaced a design question about how Django sends the portrait
  that the user wasn't asked but was implicit in the "stateless"
  framing).
