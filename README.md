# character-os

> Working name — the customer-facing product name may differ. Repo
> rename can happen later without disturbing the directory layout.

The unified monorepo for Character OS — the Django DRF shell, the
FastAPI media engine, and the customer-facing SPA.

## What this is

Character OS turns a one-paragraph business description into real
spokesperson video ads — talking avatars with a voice, a backdrop,
a script, and the variants you need to actually post (vertical,
captioned, dubbed, remixed). The audience is solo creators and
small-business owners who don't think of themselves as marketers.

## Repo layout

```
character-os/
├── shell/                # Django DRF — customer-facing service (auth, billing, models, admin)
├── media-engine/         # FastAPI — internal media pipeline (Runway, ffmpeg, voice, realtime)
├── web/                  # React + Vite — new customer-facing SPA
├── infra/                # docker-compose, deploy configs, env templates
├── docs/                 # design docs, handoffs, research
├── scripts/              # bootstrap, dev, smoke, migration scripts
├── CLAUDE.md             # project rules for AI pair-programming sessions
└── README.md
```

## Architecture in one sentence

Django owns persistence + customer-facing surface; FastAPI owns the
async media pipeline; they talk over an internal HTTP API; shared
Postgres + pgvector.

Full design is in `docs/design/UI_REDESIGN_V2.md`.

## Status

Pre-launch scaffold. Phase 1 of the implementation plan in
`docs/design/UI_REDESIGN_V2.md` §7.

## How to run (placeholders — wired up as Phase 1 proceeds)

```bash
# Django shell (port 8000)
cd shell && python manage.py runserver

# FastAPI media engine (port 8001)
cd media-engine && python -m app.main

# Web SPA (port 5173)
cd web && npm run dev
```

## Provenance

- The `media-engine/` directory imports the original
  `runway-hackathon` backend with full git history preserved (via
  `git subtree`). Every commit there explains why the code exists.
- The new repo replaces `runway-hackathon` as the launch product.
  The old repo stays frozen as the historical record + emergency
  fallback.
- `unified-donkey-betz` is a *donor* repo for selective agent +
  embedding + memory module ports (see design doc §6.7.4). Not
  merged in bulk.
