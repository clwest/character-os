---
title: "Postgres + pgvector migration (K1)"
status: shipped
date: 2026-05-14 (SESSION 138)
---

# Postgres + pgvector migration

SESSION 138 swapped character-os's local-dev database from
sqlite to Postgres 16 + pgvector. This is K1 of the
knowledge-layer arc — pure infrastructure with zero
user-visible value, but required before K2 can land the
`KnowledgeChunk` model's `VectorField`.

See `docs/design/KNOWLEDGE_LAYER.md` §"Migration: K1 —
Postgres + pgvector" for the scope rationale.

---

## What's in the dev stack now

- `postgres:character_os@localhost:5433` (Postgres 16 with
  pgvector preinstalled via `pgvector/pgvector:pg16` image).
- pgvector extension installed via
  `apps.embeddings.migrations.0001_install_pgvector`.
- Django reads connection details from env vars with
  development-friendly defaults (see below).

## Bringing the stack up

```bash
cd infra && docker compose up -d
# Brings up:
#   - character_os_redis   (Redis 7, host :6381)
#   - character_os_postgres (Postgres 16 + pgvector, host :5433)
```

Both services have healthchecks; `docker compose ps` will
report them as `(healthy)` once ready. Postgres typically
needs ~3–5 seconds on first start, instant on subsequent
starts.

## Connection details

```
ENGINE   django.db.backends.postgresql
NAME     character_os    (override via DB_NAME)
USER     character_os    (override via DB_USER)
PASSWORD character_os_dev (override via DB_PASSWORD)
HOST     localhost       (override via DB_HOST)
PORT     5433            (override via DB_PORT)
```

The defaults match `infra/docker-compose.yml`; no env vars
needed for local dev.

## Things that changed (file-by-file)

- `infra/docker-compose.yml` — added `postgres` service,
  `postgres_data` named volume.
- `shell/pyproject.toml` — uncommented `pgvector>=0.3`.
- `shell/character_os/settings.py` — switched
  `DATABASES['default']` from sqlite to Postgres with env-var
  override support.
- `shell/apps/embeddings/migrations/0001_install_pgvector.py`
  — new migration applying `CREATE EXTENSION vector`.
- `shell/apps/accounts/signals.py` —
  `ensure_default_workspace` now bails on `raw=True` to play
  nice with `loaddata`.
- `shell/apps/billing/signals.py` —
  `ensure_default_subscription` same fix.
- `web/e2e/make-video.spec.ts` — narrowed brittle
  "Make a video" selector to a heading-specific match
  (revealed by Postgres timing differences during e2e).

## The data import path (one-shot, already run)

The sqlite data (499 users / 499 workspaces / 198
spokespeople / 24 videos including the real cast) was
migrated via:

```bash
# While settings still pointed at sqlite:
python manage.py dumpdata --natural-foreign --natural-primary \
  --exclude=contenttypes --exclude=auth.permission \
  --exclude=sessions --indent=2 \
  -o /tmp/character_os_sqlite_dump.json

# After settings.py switched + docker compose up postgres:
python manage.py migrate
python manage.py loaddata /tmp/character_os_sqlite_dump.json
```

The old sqlite file (`shell/db.sqlite3`) is untouched as a
backup. It can be deleted once K2 ships and we're confident
in the new DB.

## What's verified

All gates passed against the new Postgres database before
K1 was declared shipped:

- `python manage.py check` (3 pre-existing allauth
  deprecation warnings, no errors)
- `python manage.py migrate --check` (clean)
- `python manage.py inventory` (regenerated)
- All 5 smoke commands (`smoke_headless_auth`,
  `smoke_avatar`, `smoke_voice`, `smoke_video`,
  `smoke_portrait`)
- `python -m pytest character_os/prompts/` (46 tests)
- `pnpm test` (3 SPA unit tests)
- `pnpm e2e` (30 specs, 49.4s — slightly above the 46s
  sqlite baseline; acceptable)

## Known follow-ups (not in K1)

- **Mass cleanup of e2e detritus.** Postgres now has 495
  e2e-generated workspaces alongside the 4 real ones. Cheap
  to clean (`Workspace.objects.filter(slug__startswith='e2e-').delete()`)
  but explicitly out of K1 scope. The operator will decide
  the cleanup window.
- **K2** lands the actual `KnowledgeDocument` +
  `KnowledgeChunk` schema that uses pgvector.
- **No CI** exists yet, so no CI database setup to worry
  about. When CI does land, it needs a Postgres service.

## If something breaks

1. **Postgres container not running:** `docker compose
   ps` — if `postgres` is exited, `docker compose up -d
   postgres` to restart.
2. **Connection refused:** check the host port (`:5433`,
   not `:5432`) and that no other Postgres is bound to
   that port.
3. **pgvector errors at migration time:** the extension is
   pre-installed in the image; if you see
   `extension "vector" does not exist`, the image is wrong.
   Verify `infra/docker-compose.yml` uses
   `pgvector/pgvector:pg16`.
4. **Need to start over:** `docker compose down -v` to
   wipe the volume, then re-run the migrate + loaddata
   commands above. The sqlite dump at
   `/tmp/character_os_sqlite_dump.json` was a one-shot;
   re-create it from the sqlite file if needed.
