---
title: "Session 109 — Video pipeline (fire-then-poll) + Celery/Redis"
date: 2026-05-13
status: complete
session: 109
previous_handoff: ./SESSION_108_MEDIA_ENGINE_INTERNAL_API_AVATAR_SLICE.md
---

# Session 109 — Slice A end-to-end: video pipeline + async foundation

## TL;DR

- **What shipped:** Phase 2 Slice A end-to-end. The fire-then-poll
  video pipeline is live: `POST /api/videos/` returns
  `{status: "rendering", task_id}` immediately after firing
  `POST /internal/videos/` on the media-engine; a Celery worker
  polls `GET /internal/videos/{task_id}/` until terminal and writes
  `status` / `output_path` / `error_message` / `completed_at` back
  to the `Video` row. Smoke test (`python manage.py smoke_video`)
  passes against a mock-mode media-engine in ~13 s.
- **What also shipped (foundational, pulled in early):** Celery +
  Redis. Phase 4 originally owned this; landed in Phase 2 because
  video generation can't hold an HTTP request for 60-120 s. Redis
  runs in Docker on `:6381` (collision-free with two other dev
  Redis instances on this machine). Broker + result backend both
  ride on Redis.
- **What's blocking next:** Nothing. Slice A is complete. Three
  natural follow-ups, in priority order: voice clone
  (`POST /internal/voices/`), additional video kinds (cinematic /
  dialogue / long_ad), and a stuck-row janitor for the case where
  a Celery worker dies mid-poll.

---

## What changed (file-by-file)

### `infra/docker-compose.yml` (new)

Single-service Redis 7-alpine on host port `6381` (host-side shift
to dodge collisions with two other Redis instances already on this
machine: `session1115-redis` on 6379 and `unified-redis-verify` on
6380). Append-only persistence + 256 MB LRU cap so the cache stays
bounded on dev machines.

### `shell/pyproject.toml`

Uncommented `celery>=5.4` + `redis>=5.0`. The comment used to say
"Phase 4 — spider/agent port"; updated to "landed early (Phase 2 /
SESSION 109) because the media-engine video pipeline needs fire-
then-poll for 60-120 s Runway tasks." The decision is the same
decision the docs already flagged; just earlier than planned.

### `shell/character_os/celery.py` (new)

Standard Django/Celery wiring: project-named app, settings driven
by `CELERY_*` namespace, autodiscovery on `apps/*/tasks.py`.
Includes a `debug_task` for `celery -A character_os inspect ping`
smoke checks.

### `shell/character_os/__init__.py`

Re-exports the Celery app so Django's autodiscovery wires
`@shared_task` correctly when the project loads.

### `shell/character_os/settings.py`

Added the `Celery / Redis` block. Broker on Redis DB 0, result
backend on DB 1 (separate keyspaces so a `FLUSHDB` on one doesn't
take out the other). 15-minute hard task time limit, 14-minute
soft. JSON serialiser only. Defaults override-able via env so
deploys point at managed Redis without code changes.

### `docs/design/MEDIA_ENGINE_INTERNAL_API.md`

Added the `POST /internal/videos/` + `GET /internal/videos/{task_id}/`
sections. Locked the fire-then-poll shape, documented the status
state machine (`pending → rendering → ready | failed`), and pinned
the Django-side Celery polling pattern as part of the contract so
the next session doesn't reinvent it. Updated the status table and
open questions.

### `media-engine/app/routers/internal.py`

Added `POST /internal/videos/` + `GET /internal/videos/{task_id}/`.
Wraps the existing `runway_client.create_task` / `get_task` so
Runway-side behaviour matches the legacy `/api/runway/generate`
route. Status mapping (`PENDING` → `pending`, `RUNNING` →
`rendering`, `SUCCEEDED` → `ready`, `FAILED`/`CANCELED` →
`failed`) lives only in this file — Runway speaks uppercase, the
contract speaks lowercase.

SESSION 109 ships `kind="spokesperson_ad"` only; the other three
kinds (`cinematic_video`, `dialogue_scene`, `long_ad`) return
`400 unsupported_kind`.

### `shell/character_os/clients/media_engine.py`

Added `VideoCreateResult` + `VideoPollResult` dataclasses +
`MediaEngineClient.create_video(...)` + `poll_video(task_id)`.
Same error-normalisation pattern as `create_avatar` — transport /
non-2xx / shape mismatches all collapse to `MediaEngineError`.

### `shell/apps/videos/tasks.py` (new)

`poll_video_until_terminal(video_id)` Celery task. 2 s poll
cadence, 10-minute deadline. Idempotent (re-run against terminal
rows is a no-op) and resilient (auto-retries on `MediaEngineError`
with exponential backoff up to 5 attempts). Persists
`status` / `output_path` / `duration_seconds` / `error_message` /
`completed_at` in a single update on terminal.

The task only writes intermediate `RENDERING` status on
transition + on >10 % progress jumps to keep DB chatter
proportional to actual progress, not poll cadence.

### `shell/apps/videos/views.py`

Rewritten `perform_create`. After the row lands:

1. Validate the spokesperson has an avatar (404-style error
   message persisted as `status=failed` if not).
2. Pick the brief from the request or fall back to the
   spokesperson's `business_brief`.
3. Call `MediaEngineClient.create_video`.
4. Persist `media_engine_task_id` + `status=rendering`.
5. Enqueue `poll_video_until_terminal.delay(video_id)`.

Any failure (no avatar, no brief, media-engine error, broker
error) writes `status=failed` + a useful `error_message` rather
than rolling back the row. That keeps the SPA's retry flow simple
— the row exists, the operator can edit + retry.

### `shell/apps/videos/management/commands/smoke_video.py` (new)

`python manage.py smoke_video` — full pipeline test. Auto-creates
a spokesperson with a mock avatar if the workspace doesn't have
one, fires the video, waits up to 25 s (configurable via `--wait`)
for the Celery worker to mark the row terminal, asserts
`status=ready` + populated `output_path`. Cleans up the test row
unless `--keep`.

Run output from SESSION 109's verification:

```
  ✓ media engine reachable (runway_mock=True)
  ! no spokesperson with avatar in this workspace — creating one
  ✓ using spokesperson 'Smoke Test Spokesperson' (avatar_id=mock_avatar_785b172fdd3d)
  ✓ video row id=6e8ac3c9-... status=Video.Status.RENDERING task_id='mock_2dd510e4b8'
    status → 'ready' (t+13.1s)
  → final status='ready' output_path='https://download.samplelib.com/mp4/sample-5s.mp4'
  ✓ cleaned up Video row id=6e8ac3c9-...
✓ smoke test PASSED
```

---

## Verification gates

- `python manage.py check` — 0 issues.
- `python manage.py migrate --check` — exit 0 (no schema changes).
- FastAPI route count — 103 → 105 (added `POST /internal/videos/`
  + `GET /internal/videos/{task_id}/`).
- `celery -A character_os inspect ping` — pong.
- `celery -A character_os inspect registered` — both tasks
  registered (`apps.videos.tasks.poll_video_until_terminal` +
  `character_os.celery.debug_task`).
- `python manage.py smoke_video` — PASSED in 13 s.
- Hygiene scan — clean.

---

## How to run the full stack locally

Three processes, plus Redis in Docker:

```bash
# Redis (one-time, leaves running)
cd infra && docker compose up -d

# Terminal 1 — FastAPI media-engine
cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

# Terminal 2 — Django
cd shell && source .venv/bin/activate
python manage.py runserver

# Terminal 3 — Celery worker
cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo
```

Smoke check: `python manage.py smoke_video` (in any shell with the
Django venv activated).

`--pool=solo` is the right choice for local dev — single-threaded,
debuggable, no fork. Production wants `--pool=prefork` (default) or
gevent.

---

## Architectural notes worth remembering

### Celery landed early, on purpose

Phase 4's "spider/agent port" was the planned home for Celery. The
moment video generation joined the stack, that planning broke —
real-mode Runway tasks run 60-120 s, which is too long for an
inline HTTP hold. The middle path (thread-helper) had a real
weakness (not crash-safe — Django restart loses the polling
thread). Celery + Redis is the right shape; pulling it in once
costs less than retrofitting later.

The cost was real but contained: Redis container + 2 new Python
deps + ~80 lines of Celery config and task code. The contract was
already shaped for fire-then-poll (SESSION 108 left that as an
open question that needed resolving when video landed), so the
work was anticipated.

### Stuck rows are accepted, not solved

When a Celery worker dies mid-poll the Video row stays in
`rendering` indefinitely. SESSION 109 accepts this failure mode.
Phase 3 needs a `celery beat`-scheduled janitor that re-enqueues
polls for rows in `rendering` older than N minutes. Notes left in
the contract doc.

### Status vocabulary is one-way mapped

Runway speaks `PENDING/RUNNING/SUCCEEDED/FAILED/CANCELED`. The
contract speaks `pending/rendering/ready/failed`. The mapping
lives in **exactly one place** (`media-engine/app/routers/internal.py`
::`_RUNWAY_TO_CONTRACT_STATUS`). The Django side never sees Runway
status strings. If Runway adds a new status code (e.g. `QUEUED`),
the mapping is the only thing that needs to change.

### Port collision was a real lesson

Three other dev projects on this machine were already using
`:6379` and `:6380` for Redis. `docker compose up` failed, then
succeeded after shifting our host port to `:6381`. Worth assuming
similar collisions for future infra services (Postgres on `:5432`
is already taken by `unified-postgres`).

---

## SESSION 110 — entry point

See `00-START-NEXT-SESSION.md` for the recommended slice.

---

## AI notes

- Spent the first ~10 minutes confirming whether Celery already
  existed in any form before deciding scope. The `pyproject.toml`
  flag ("Phase 4 — spider/agent port") was the load-bearing
  signal that this was anticipated; if it had been "we don't
  want Celery", that would have been a different conversation.
- The user explicitly said "bring it in now, it'll merge as the
  project grows" — that's a higher-confidence decision than "do
  the smallest thing" would have produced. Worth remembering as
  a calibration signal: this operator prefers right-shaping
  foundations early over deferring.
- Pyright noise increased again (`from .tasks import ...`,
  `get_queryset` Never return). Same cross-stack class flagged
  three sessions in a row now; `pyrightconfig.json` is the
  obvious follow-up.
