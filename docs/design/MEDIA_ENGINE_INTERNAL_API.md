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
| POST   | `/internal/voices/`                 | Clone a voice from an audio sample            | **SESSION 110** |
| GET    | `/internal/voices/{voice_id}/`      | Poll voice clone status                       | Planned |
| POST   | `/internal/videos/`                 | Generate a video (kind-discriminated body)    | **SESSION 109** |
| GET    | `/internal/videos/{task_id}/`       | Poll video task status, get `output_url`      | **SESSION 109** |

Endpoints are added one at a time as Django features need them, to
keep the diff reviewable and the contract honest.

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

## POST /internal/voices/

Clone a voice from an audio sample. Inline / synchronous — Runway's
voice clone API returns in <10 s in real mode and a fraction of a
second in mock mode, so there's no value in fire-then-poll for this
endpoint. The Django side blocks on the response.

### Request body

```json
{
  "audio_data_uri": "data:audio/wav;base64,UklGRiQAAABXQVZF...",
  "name": "Casey — founder voice"
}
```

| Field            | Type   | Required | Notes |
|------------------|--------|----------|-------|
| `audio_data_uri` | string | yes      | `data:audio/{mp3,wav,m4a,webm,ogg,aac};base64,...`. Decoded cap: 15 MB. Runway documents a 10 MB hard limit — we accept up to 15 MB locally so an oversized upload fails with a friendly 413 instead of a wire truncation. |
| `name`           | string | no       | Display name for the voice resource. ≤ 80 chars. Defaults to `"Custom Voice"` server-side. Logging + Runway metadata only; Django holds the canonical name. |

### Supported audio mime types

`audio/mpeg`, `audio/mp3`, `audio/wav`, `audio/x-wav`, `audio/wave`,
`audio/m4a`, `audio/mp4`, `audio/x-m4a`, `audio/aac`, `audio/webm`,
`audio/ogg`.

### Response — 200 OK

```json
{
  "voice_id": "runway_voice_abc123",
  "status": "ready",
  "preview_url": "https://runway.example/voices/abc123/preview.mp3",
  "mock_mode": false
}
```

| Field         | Type             | Notes |
|---------------|------------------|-------|
| `voice_id`    | string           | Persist on `Spokesperson.voice_id`. |
| `status`      | enum             | `ready` (real-mode success) \| `mock` (mock-mode success) \| `failed`. |
| `preview_url` | string \| null   | Optional Runway-hosted preview MP3. `null` in mock mode and when Runway's poll didn't surface one before timeout. The SPA renders an `<audio>` element when present. |
| `mock_mode`   | bool             | True when the service ran without a Runway key. |

### Error codes

| HTTP | `code`                  | When |
|------|-------------------------|------|
| 400  | `invalid_data_uri`      | `audio_data_uri` missing, malformed, or not a supported mime type. |
| 413  | `audio_too_large`       | Decoded audio > 15 MB. |
| 422  | `empty_audio`           | Data URI decoded to zero bytes. |
| 502  | `upstream_runway_error` | Runway upstream rejection; `error` carries the upstream message. |
| 500  | `internal_error`        | Bug. Operator-visible only via logs. |

### Stateless contract

The media-engine does **not** persist the voice locally. The
decoded audio is held in memory just long enough to be forwarded to
Runway (real mode) or hashed for the mock id (mock mode). No
`data/_internal/voices/` directory — voices are cheap to re-clone,
unlike portraits whose Runway upload latency makes the local cache
worthwhile.

### Mock-mode behaviour

When `RUNWAY_MOCK=1` (the operator hasn't set `RUNWAY_API_KEY`),
the endpoint returns immediately with `status: "mock"`,
`voice_id: "mock_voice_<sha256(name + audio_bytes)[:16]>"`, and
`preview_url: null`. Deterministic — same inputs yield the same
id so smoke tests stay hermetic.

---

## POST /internal/videos/

Fire a video render. Returns immediately with a `task_id` — does
**not** wait for Runway to finish. Caller polls
`GET /internal/videos/{task_id}/` for terminal state.

### Request body

```json
{
  "kind": "spokesperson_ad",
  "spokesperson_avatar_id": "runway_avatar_abc123",
  "brief": "Black Friday sale — 30 % off everything.",
  "ratio": "1280:720",
  "duration": 5,
  "prompt_image": "/api/runway/image/abc123"
}
```

| Field                    | Type   | Required | Notes |
|--------------------------|--------|----------|-------|
| `kind`                   | enum   | yes      | One of `spokesperson_ad`, `cinematic_video`, `dialogue_scene`, `long_ad`. SESSION 109 ships `spokesperson_ad` only; other kinds 400 until landed. |
| `spokesperson_avatar_id` | string | yes      | The avatar id returned by `POST /internal/avatars/`. Mock-mode avatars (prefix `mock_avatar_`) drive mock-mode video. |
| `brief`                  | string | yes      | The campaign brief / script seed. ≤ 2000 chars. |
| `ratio`                  | string | no       | `1280:720` \| `720:1280` \| `960:960`. Defaults to `1280:720`. |
| `duration`               | int    | no       | Seconds. Per-model policy enforced server-side (5 / 8 / 10 for `gen4.5`). Defaults to 5. |
| `prompt_image`           | string | no       | Optional starting frame. Same shape as the legacy `/api/runway/generate` `prompt_image`. |

### Response — 200 OK

```json
{
  "task_id": "runway_task_xyz789",
  "status": "pending",
  "kind": "spokesperson_ad",
  "mock_mode": false
}
```

`status` is one of `pending` / `rendering` — never terminal on the
create call. Terminal state lives on the GET.

### Error codes

| HTTP | `code`                  | When |
|------|-------------------------|------|
| 400  | `unsupported_kind`      | `kind` not in the supported set. |
| 400  | `invalid_settings`      | ratio / duration combination rejected by the per-model policy. |
| 422  | `validation_error`      | Body shape mismatch. |
| 502  | `upstream_runway_error` | Runway upstream rejection. |

---

## GET /internal/videos/{task_id}/

Poll the task. Idempotent and cheap; safe to call on a tight loop
from the Celery worker.

### Response — 200 OK (terminal — ready)

```json
{
  "task_id": "runway_task_xyz789",
  "status": "ready",
  "output_url": "/data/_internal/videos/abc.mp4",
  "duration_seconds": 5.0,
  "mock_mode": false
}
```

### Response — 200 OK (still running)

```json
{
  "task_id": "runway_task_xyz789",
  "status": "rendering",
  "progress": 0.42,
  "mock_mode": false
}
```

### Response — 200 OK (terminal — failed)

```json
{
  "task_id": "runway_task_xyz789",
  "status": "failed",
  "error": "human-readable Runway failure message",
  "failure_code": "BAD_OUTPUT",
  "mock_mode": false
}
```

### Status state machine

```
pending ──► rendering ──► ready    (terminal)
                     └──► failed   (terminal)
```

Terminal states (`ready`, `failed`) never transition further; once
the worker observes one, it can stop polling.

### Mock-mode behaviour

The mock task store inside `runway_client._MOCK_STORE` simulates a
12-second render. The first ~3 polls return `rendering` with a
climbing progress value; subsequent polls return `ready` with a
canned sample-MP4 URL. Deterministic enough to write Celery state-
machine assertions against without burning Runway credits.

---

## Django-side polling pattern (Celery)

The Django shell uses Celery (broker: Redis on `:6381` for local
dev, env-overridable for deploys) to drive the poll loop. The
pattern:

1. `VideoViewSet.perform_create` saves the row and calls
   `MediaEngineClient.create_video(...)`.
2. The row gets `media_engine_task_id` + `status="rendering"`
   persisted.
3. `poll_video_until_terminal.delay(video_id)` enqueues a Celery
   task on the `default` queue.
4. The worker polls `GET /internal/videos/{task_id}/` on a 2-second
   loop (configurable per call) up to a 10-minute deadline.
5. On terminal state the worker writes `status`, `output_path`,
   `duration_seconds`, `error_message`, `completed_at` to the row
   and stops.
6. If the worker dies mid-poll, the row stays in `rendering` until
   either a janitor re-enqueues the task or the operator retries
   from the SPA. (Janitor is Phase 3 scope; SESSION 109 accepts
   the "stuck row" failure mode.)

The poll task is idempotent — re-running it against the same
`media_engine_task_id` is safe; it picks up the latest terminal
state and writes it back (no-op if the row is already terminal).

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

- **Other video kinds.** SESSION 109 ships only `spokesperson_ad`.
  The other three (`cinematic_video`, `dialogue_scene`, `long_ad`)
  each have different required inputs (e.g. dialogue takes two
  avatars, long_ad takes a multi-scene script). Resolve as each one
  lands.
- **Voice clone poll.** SESSION 110 ships `POST /internal/voices/`
  synchronously. A future `GET /internal/voices/{voice_id}/` would
  let the SPA re-fetch the preview URL after Runway eventually
  populates it (Runway's voice preview URL sometimes lands after
  the create call returns). Defer until the SPA has a real
  "preview unavailable, retry" UX.
- **Auth.** Internal endpoints are currently unprotected (both
  services bind to localhost). When we deploy off the operator's
  machine, the internal surface needs a shared-secret header.
  Out of scope for SESSION 109.
- **Stuck-row janitor.** When a Celery worker dies mid-poll the
  Video row stays in `rendering` forever. Phase 3 needs a
  scheduled task (`celery beat`) that re-enqueues polls for rows
  in `rendering` older than N minutes.

---

## Change log

- 2026-05-13 (SESSION 108) — Initial draft + `POST /internal/avatars/`.
- 2026-05-13 (SESSION 109) — Added `POST /internal/videos/` +
  `GET /internal/videos/{task_id}/`. Pinned the fire-then-poll
  shape and documented the Django-side Celery polling pattern.
- 2026-05-13 (SESSION 110) — Added `POST /internal/voices/`.
  Inline / synchronous; no polling needed.
