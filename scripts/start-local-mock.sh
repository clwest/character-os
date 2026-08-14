#!/usr/bin/env bash
#
# start-local-mock.sh — boot the canonical Character OS stack in
# **mock mode** (no real Runway / OpenAI / ElevenLabs / Stability
# spend). Every provider on the media-engine side resolves to the
# deterministic mock branch via ``RUNWAY_FORCE_MOCK=1`` +
# ``OPENAI_FORCE_MOCK=1``. Django still uses its real ``OPENAI_API_KEY``
# for embeddings unless that variable is set — see the note below.
#
# Same 4-service topology as ``start-local-real.sh``; only the env
# flags differ. Keep the two scripts in sync when adding services.
#
# Usage:
#   bash scripts/start-local-mock.sh
#
# Stop:
#   bash scripts/stop-local.sh

set -eu

REPO_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || true)"
if [ -z "${REPO_ROOT}" ]; then
  echo "✗ not a git repo" >&2
  exit 1
fi
cd "${REPO_ROOT}"

if [ ! -f .env ]; then
  echo "✗ no .env at repo root" >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "✗ no .venv at repo root" >&2
  exit 1
fi
if [ ! -d web/node_modules ]; then
  echo "✗ web/node_modules missing — run 'cd web && pnpm install'" >&2
  exit 1
fi

LOG_DIR="/tmp"
DJANGO_LOG="${LOG_DIR}/character-os-django-mock.log"
MEDIA_LOG="${LOG_DIR}/character-os-media-mock.log"
CELERY_LOG="${LOG_DIR}/character-os-celery-mock.log"
VITE_LOG="${LOG_DIR}/character-os-web-mock.log"

pkill -f "celery -A character_os worker" 2>/dev/null || true
pkill -f "manage.py runserver" 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2

# Load .env first, THEN override with mock flags so the media-engine
# stays hermetic even if the operator's .env has real keys.
set -a
# shellcheck disable=SC1091
source .env
set +a

# Force every media-engine provider to mock. These are read by
# ``media-engine/app/config.py``.
export RUNWAY_FORCE_MOCK=1
export OPENAI_FORCE_MOCK=1
export IMAGE_GEN_MOCK=1

# ---- Infra -----------------------------------------------------------
if ! docker ps --format '{{.Names}}' | grep -q '^character_os_postgres$'; then
  echo "── docker-compose: starting infra (postgres + redis) ──"
  docker compose -f infra/docker-compose.yml up -d
  sleep 4
fi

# ---- Django (port 8010) ---------------------------------------------
(
  cd shell
  nohup ../.venv/bin/python manage.py runserver 0.0.0.0:8010 \
    > "${DJANGO_LOG}" 2>&1 &
  echo "$!" > /tmp/character-os-django.pid
)

# ---- FastAPI media-engine (port 8001, mock-forced) ------------------
(
  cd media-engine
  nohup ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level warning \
    > "${MEDIA_LOG}" 2>&1 &
  echo "$!" > /tmp/character-os-media.pid
)

# ---- Celery worker --------------------------------------------------
(
  cd shell
  nohup ../.venv/bin/celery -A character_os worker \
    --loglevel=info --concurrency=2 \
    > "${CELERY_LOG}" 2>&1 &
  echo "$!" > /tmp/character-os-celery.pid
)

# ---- Vite SPA -------------------------------------------------------
(
  cd web
  nohup pnpm dev > "${VITE_LOG}" 2>&1 &
  echo "$!" > /tmp/character-os-web.pid
)

sleep 6

echo
echo "── Boot logs ─────────────────────────────────────────"
echo "  django       → ${DJANGO_LOG}"
echo "  media-engine → ${MEDIA_LOG}"
echo "  celery       → ${CELERY_LOG}"
echo "  web (vite)   → ${VITE_LOG}"

echo
echo "── HTTP health probes (expect any_mock=true) ────────"
printf "  django       "; curl -sfo /dev/null -w "http=%{http_code}\n" http://localhost:8010/admin/ || echo "not responding"
printf "  media-engine "; curl -sf http://localhost:8001/health | head -c 200; echo
printf "  web (vite)   "; curl -sfo /dev/null -w "http=%{http_code}\n" http://localhost:5174/ || echo "not responding"

echo
echo "── Celery worker probe ───────────────────────────────"
CELERY_OK=""
for attempt in 1 2 3 4 5; do
  if (cd shell && ../.venv/bin/celery -A character_os inspect ping --timeout 3 2>/dev/null | grep -q 'pong'); then
    CELERY_OK="yes"
    break
  fi
  sleep 2
done
if [ -n "${CELERY_OK}" ]; then
  echo "  ✅ worker replied to inspect ping."
else
  echo "  ❌ worker did not respond to inspect ping within ~10s." >&2
  exit 1
fi

echo
echo "── PIDs ──────────────────────────────────────────────"
pgrep -lf 'manage.py runserver|uvicorn app.main:app|celery -A character_os worker|vite' || true

cat <<NOTE

✅ Character OS booted (MOCK mode — NO real API calls will fire).
   Django       http://localhost:8010
   Media engine http://localhost:8001
   Web          http://localhost:5174

   Use this mode for:
     - Playwright smoke (cd web && npx playwright test)
     - CI runs
     - Safe dry-runs of unfinished UI flows

   Stop: bash scripts/stop-local.sh
   Real: bash scripts/start-local-real.sh
NOTE
