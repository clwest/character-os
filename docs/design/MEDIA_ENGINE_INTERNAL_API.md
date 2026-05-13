---
title: "Media Engine — Internal API contract (Phase 2)"
status: active
generated: 2026-05-13
companion_docs:
  - "UI_REDESIGN_V2.md"
  - "../CHARACTER_OS_PIPELINE.md"
phase: 2
---

# Media Engine — Internal API contract

> **Read first:** `docs/design/UI_REDESIGN_V2.md` §6 (architecture) and §7
> (phase list). This doc covers Phase 2 specifically — closing the gap
> between the new Django data model (Workspace → Spokesperson → Video)
> and the FastAPI media-engine's legacy surface (Campaign → Character →
> OutputRecord).

---

## Purpose

The Django shell needs a **small, stable, stateless** HTTP surface on
the FastAPI media-engine that it can call to do the four media-side
verbs the launch product cares about:

1. Build an avatar (Runway character) from a portrait + voice settings.
2. Generate a video from an avatar + script + per-kind options.
3. Clone a voice from an audio sample.
4. Poll any of the above to completion and pick up the artefact URL.

Everything else the media-engine already exposes (102 legacy routes
under `/api/*`) stays put during the transition. The Django shell
**only** calls into `/internal/*`. The legacy `/api/*` surface remains
until the SPA migration in Phase 3 retires its consumers.

## Contract rules (load-bearing)

1. **Pure JSON in, pure JSON out.** Every body is `application/json`.
   Binary payloads (portraits, audio, video references) ride as
   `data:` URIs inside the JSON body. No multipart upload to
   `/internal/*` endpoints.
2. **Stateless across calls.** The media-engine does not own
   spokespeople, videos, threads, or any "what does this user own"
   state. It holds only:
   - Transient task state inside Runway / OpenAI providers (out of
     our control).
   - Generated artefact files cached under `media-engine/data/`
     (write-once, read-anywhere — Django can stream them back
     through itself if it wants to gate them).
   All persistence lives in the Django shell.
3. **Idempotent where possible.** Mock-mode short-circuits derive
   ids deterministically from input so re-calls with the same body
   produce the same id (handy for tests). Real-mode is not
   idempotent — Runway assigns the id.
4. **Errors normalise to one shape.** All non-2xx responses return:
   ```json
   {"error": "human-readable message", "code": "stable-machine-readable-code"}
   ```
   Codes that Django needs to branch on are listed per endpoint.
   Transport / 5xx / unreachable are all collapsed at the Django
   side into `MediaEngineError(status_code=...)`.
5. **Mock mode is a first-class output.** Every response carries
   `mock_mode: bool`. Django shows this in the workspace as a "demo
   mode" pill. Mock-mode avatars return real-looking ids prefixed
   `mock_` so they never collide with real Runway ids.

## URL surface

All internal endpoints live under `/internal/` and are versionless —
the contract evolves through additive changes only. Breaking changes
require renaming (e.g. `/internal/v2/avatars/`) and a deprecation
window of at least one full phase.

| Method | Path                                | Purpose                                      | Status |
|--------|-------------------------------------|----------------------------------------------|--------|
| POST   | `/internal/avatars/`                | Create a Runway avatar from a portrait        | **SESSION 108** |
| GET    | `/internal/avatars/{avatar_id}/`    | Poll avatar status                            | Planned |
| POST   | `/internal/voices/`                 | Clone a voice from an audio sample            | Planned |
| GET    | `/internal/voices/{voice_id}/`      | Poll voice clone status                       | Planned |
| POST   | `/internal/videos/`                 | Generate a video (kind-discriminated body)    | Planned |
| GET    | `/internal/videos/{task_id}/`       | Poll video task status, get `output_url`      | Planned |

The SESSION 108 slice implements **only** `POST /internal/avatars/`.
Everything else lands in subsequent sessions as Django features
need them — adding one endpoint at a time keeps the diff reviewable
and the contract honest.

---

## POST /internal/avatars/

Create a Runway avatar from a portrait image.

### Request body

```json
{
  "name": "Casey",
  "portrait_data_uri": "data:image/png;base64,iVBORw0K...",
  "voice_preset": "vincent",
  "personality": "Optional one-paragraph cue"
}
```

| Field               | Type   | Required | Notes |
|---------------------|--------|----------|-------|
| `name`              | string | yes      | Display name. ≤ 80 chars. Used for logging + Runway metadata only — Django keeps the canonical name. |
| `portrait_data_uri` | string | yes      | `data:image/{png,jpeg,webp};base64,...`. Cap: 5 MB decoded. |
| `voice_preset`      | string | no       | One of the Runway preset ids (e.g. `vincent`, `marina`). Defaults to `vincent` server-side. |
| `personality`       | string | no       | ≤ 600 chars. Optional system-prompt cue baked into the avatar. |

### Response — 200 OK

```json
{
  "avatar_id": "runway_avatar_abc123",
  "status": "ready",
  "thumbnail_url": "/api/runway/image/abc123",
  "mock_mode": false
}
```

| Field            | Type   | Notes |
|------------------|--------|-------|
| `avatar_id`      | string | Persist on `Spokesperson.runway_avatar_id`. |
| `status`         | enum   | `ready` (real-mode success) \| `mock` (mock-mode success) \| `failed`. |
| `thumbnail_url`  | string \| null | Optional preview URL. Always relative to the media-engine's base URL. Django can proxy it through itself if it wants to gate. |
| `mock_mode`      | bool   | True when the service ran without a Runway key. |

### Error codes

| HTTP | `code`                  | When |
|------|-------------------------|------|
| 400  | `invalid_data_uri`      | `portrait_data_uri` missing, malformed, or not a supported mime type. |
| 413  | `portrait_too_large`    | Decoded portrait > 5 MB. |
| 400  | `unsupported_voice`     | `voice_preset` not in the supported set. |
| 502  | `upstream_runway_error` | Runway upstream rejection; `error` carries the upstream message. |
| 500  | `internal_error`        | Bug. Operator-visible only via logs. |

### Stateless contract

The media-engine writes the decoded portrait to a temp file under
`media-engine/data/_internal/` (gitignored), calls Runway, returns
the result, and **does not retain** a CharacterStore record for the
spokesperson. Django is the only system of record.

### Mock-mode behaviour

When `RUNWAY_MOCK=1` (the operator hasn't set `RUNWAY_API_KEY`), the
endpoint returns immediately with `status: "mock"` and a derived id
of the form `mock_avatar_<sha256(name + portrait_bytes)[:12]>`. Same
inputs → same id, so smoke tests stay deterministic.

---

## Relationship to the legacy `/api/*` surface

The internal endpoints do **not** replace the legacy
`/api/characters/{id}/create-avatar` route. The legacy route:

- Reads from the media-engine's local `CharacterStore` (JSON-file
  persistence under `media-engine/data/characters/`).
- Is consumed by the runway-hackathon SPA via `/api/characters/*`.
- Stays untouched during Phase 2 — the old SPA keeps working.

The internal route:

- Takes the portrait inline (stateless).
- Is consumed by the Django shell via `MediaEngineClient`.
- Persists nothing on the media-engine side beyond the temp file
  cache.

When the Phase 3 SPA replaces the runway-hackathon UI, the legacy
`/api/*` surface can be retired in chunks — each chunk gated on a
matching `/internal/*` endpoint shipping first.

---

## Django side — `MediaEngineClient` wrapper shape

```python
from character_os.clients.media_engine import MediaEngineClient

with MediaEngineClient() as client:
    result = client.create_avatar(
        name="Casey",
        portrait_data_uri=portrait_data_uri,
        voice_preset="vincent",
    )
# result.avatar_id, result.status, result.thumbnail_url, result.mock_mode
```

`MediaEngineError` is raised on transport failure, non-2xx response,
or malformed JSON. Callers inspect `.status_code` (None means
"service unreachable") to decide whether to retry or surface to the
operator.

---

## Open questions (resolve before adding each new endpoint)

- **Video generation kinds.** The launch product covers four
  (`spokesperson_ad`, `cinematic_video`, `dialogue_scene`,
  `long_ad`). Each has different required inputs. Resolve as we add
  `POST /internal/videos/`.
- **Async vs sync.** Today `POST /internal/avatars/` polls Runway
  inline and returns when terminal. Video generation can take 90+
  seconds — likely needs a fire-then-poll shape (`POST` returns
  `{task_id, status: "pending"}`, separate `GET` polls). Confirm
  when wiring video.
- **Auth.** Internal endpoints are currently unprotected (both
  services bind to localhost). When we deploy off the operator's
  machine, the internal surface needs a shared-secret header.
  Out of scope for SESSION 108.

---

## Change log

- 2026-05-13 (SESSION 108) — Initial draft + `POST /internal/avatars/`.
