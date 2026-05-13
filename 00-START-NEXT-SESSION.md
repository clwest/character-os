---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md` is canonical for
> what we're building.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md` is
> canonical for Phase 2's Django↔FastAPI boundary.
> **Last handoff:**
> `docs/handoffs/SESSION_108_MEDIA_ENGINE_INTERNAL_API_AVATAR_SLICE.md`
> — Phase 2 contract locked + `POST /internal/avatars/` shipped.

---

## Where we are

**Phase 0 — Pre-flight (design lock):** DONE.
**Phase 1 — Django shell scaffold + monetization layer:** DONE.
**Phase 2 — Media-engine data model migration:** IN PROGRESS.

What's working end-to-end after SESSION 108:

  - Everything from SESSION 107 (24 REST endpoints, signup → workspace
    → tier-gated CRUD).
  - `POST /internal/avatars/` on the FastAPI media-engine (route 103)
    — pure JSON in/out, stateless, mock-mode safe.
  - `MediaEngineClient.create_avatar(...)` on the Django shell —
    typed result, errors normalised through `MediaEngineError`.
  - `POST /api/spokespeople/` with an optional `portrait_data_uri`
    field — the viewset fires the avatar create inline and persists
    `runway_avatar_id` + `runway_avatar_status` onto the row.
  - `python manage.py smoke_avatar` — end-to-end pipeline test,
    passes in <2 s against a mock-mode media-engine.

---

## SESSION 109 — Phase 2 continuation

The contract is the lever. Five rules (locked in
`docs/design/MEDIA_ENGINE_INTERNAL_API.md`) bind every new endpoint:
JSON-only, stateless, idempotent in mock mode, errors as
`{error, code}`, mock mode as a first-class output. New endpoints
that compromise these compromise the deploy story.

Three equally valid next slices — operator picks first:

### Slice A — `POST /internal/videos/` (recommended)

The highest-leverage next endpoint. Unlocks the rest of the
Spokesperson workflow: once the avatar exists, the operator wants
to render an ad. Forces a design decision the contract has been
deferring — **fire-then-poll vs synchronous**. Real-mode Runway
video calls run 60-120 s, which is too long for an inline HTTP
hold, so:

  1. `POST /internal/videos/` returns `{task_id, status: "pending"}`
     immediately after firing Runway.
  2. `GET /internal/videos/{task_id}/` is the matching poll
     endpoint. Returns `{status, output_url?}` — `output_url` is
     populated only on `status: "ready"` / `mock`.
  3. Django side adds an async-or-sync polling helper on
     `MediaEngineClient` and a `Video` row state machine
     (`pending` → `ready` | `failed`).

Implementation order: contract → media-engine endpoint → client
wrapper → `VideoViewSet.create` wires it → smoke test. Same
five-step pattern SESSION 108 used.

**Open question for slice A:** does the Django side poll in-process
(simple, but the HTTP request hangs for ~60-120 s — bad UX) or
queue a Celery task (real fix, but pulls Celery into the build
ahead of where Phase 2's scope wanted it)? The middle path is a
small `polling.py` thread helper that writes back to the Video row
asynchronously after returning a `201 Created` with `status:
"pending"` to the client; the SPA polls `GET /api/videos/{id}/`.
Worth pinning down before writing code.

### Slice B — `POST /internal/voices/` (voice clone)

Lower-stakes endpoint. Maps to the legacy
`POST /api/characters/{id}/clone-voice` flow but stateless. Needed
for the Pro / Agency tiers; not needed for the Starter happy path.
Same shape as the avatar slice: accepts an audio sample as a
`data:audio/...;base64,...` URI, returns a `voice_id`. Skip if
Slice A goes first.

### Slice C — Avatar status poll (`GET /internal/avatars/{id}/`)

Documented in the contract but unshipped because SESSION 108's
synchronous create returns terminal already. Becomes load-bearing
when create needs to go async — which happens the moment video
joins this surface, since the same polling infrastructure should
work for both. Better to land it as part of Slice A.

### Recommended scope for SESSION 109 (assumes Slice A)

1. **Pin the fire-then-poll design.** Update
   `docs/design/MEDIA_ENGINE_INTERNAL_API.md` §`POST /internal/videos/`
   with the chosen poll strategy.
2. **`POST /internal/videos/`** on media-engine. Discriminate on
   `kind` (`spokesperson_ad` for now). Wraps existing service code
   so Runway-side behaviour matches the legacy route.
3. **`GET /internal/videos/{task_id}/`** matching poll endpoint.
4. **`MediaEngineClient.create_video(...)`** + `poll_video(task_id)`.
5. **`VideoViewSet.create`** wires it. Persists `runway_task_id` +
   `runway_task_status` + `output_url` (when ready) on the `Video`
   row.
6. **Smoke test** — `python manage.py smoke_video`. Mock mode runs
   inline; tests assert the polling state machine transitions
   correctly.

### Out of scope for SESSION 109

- All four video kinds (`spokesperson_ad`, `cinematic_video`,
  `dialogue_scene`, `long_ad`). Land one (`spokesperson_ad`) first;
  add the others as the SPA needs them.
- Celery — see open question above. The thread-helper middle path
  defers Celery to Phase 3.
- Real Runway calls — mock mode is the right path until the polling
  shape is locked.
- Frontend / SPA work (Phase 3).
- The campaigns-to-django migration script. Still pending; equally
  valid alternative to slice A if the operator wants legacy
  artefacts surfacing in the new shell sooner.

---

## Queued investigations (not blocking SESSION 109)

- **`shell/pyrightconfig.json`** — silences the cross-app import +
  `GenericAPIView.get_queryset` "Never" return warnings. 2-line
  slice; pre-existing noise the SESSION 107 + 108 handoffs both
  flagged. Should land soon.
- **Inventory generator** (`python manage.py inventory`) — emits
  runtime truth as JSON for `docs/CHARACTER_OS_INVENTORY.md`. Still
  the right project memory upgrade once Phase 2 stabilises.
- **dj-stripe install** — when operator has Stripe credentials.
- **Real Google OAuth** — when operator creates the OAuth client.
- **`allauth.headless`** — JSON signup/login for the SPA. Defer
  until Phase 3 starts.
- **Tag `v-final-pre-migration` on runway-hackathon** (Q6 of design
  doc). Operator decision; the SESSION 108 work didn't touch the
  legacy `/api/*` surface so the tag remains safe to apply.
- **Numbered handoff gap** — `SESSION_053` is missing from
  `docs/handoffs/`. `context-kit orient` flags this. Non-blocking;
  drop a placeholder when the operator wants the warning gone.

---

## AI / assistant context

- Last session: SESSION 108 — Phase 2 contract locked +
  `POST /internal/avatars/` shipped end-to-end.
- Collaboration conventions: AI drafts, human edits.
- Handoff `## AI Notes` section required at session end.
- `docs/TRUST_CALIBRATION.md` still empty — no calibration events
  in this session either.
