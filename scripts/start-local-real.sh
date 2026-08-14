#!/usr/bin/env bash
#
# start-local-real.sh — the CANONICAL entry point for the functional
# local Character OS stack. Starts every process required for
# composition generation to complete end-to-end:
#
#   1. Postgres + Redis (via docker-compose, if not already up)
#   2. Django DRF shell        (port 8010)
#   3. FastAPI media-engine    (port 8001, real-mode)
#   4. Celery worker           (composition renders, transcript
#                               capture, tool dispatch, embeddings)
#   5. Vite SPA                (port 5174)
#
# Celery was omitted from the pre-SESSION 251 layout of this script.
# The consequence: every ``POST /api/compositions/`` enqueued a task
# that nothing consumed, leaving DRAFT rows visible as "spinning" in
# the SPA activity feed until an operator noticed. Do NOT remove the
# worker from this script.
#
# For explicit mock-mode boots (CI / smoke / no-spend dry-runs), use
# ``scripts/start-local-mock.sh`` instead. That script sets
# ``RUNWAY_FORCE_MOCK=1`` so real providers stay untouched.
#
# Usage:
#   bash scripts/start-local-real.sh
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
  echo "✗ no .env at repo root — copy the template and fill in API keys" >&2
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "✗ no .venv at repo root — run 'python -m venv .venv && pip install -e shell'" >&2
  exit 1
fi
if [ ! -d web/node_modules ]; then
  echo "✗ web/node_modules missing — run 'cd web && pnpm install'" >&2
  exit 1
fi

LOG_DIR="/tmp"
DJANGO_LOG="${LOG_DIR}/character-os-django.log"
MEDIA_LOG="${LOG_DIR}/character-os-media.log"
CELERY_LOG="${LOG_DIR}/character-os-celery.log"
VITE_LOG="${LOG_DIR}/character-os-web.log"

# ---- Kill any prior instances ---------------------------------------
# Match on the full command line so we don't kill unrelated python /
# node processes. Kill Celery before Django so the worker doesn't
# complain about a lost broker mid-shutdown.
pkill -f "celery -A character_os worker" 2>/dev/null || true
pkill -f "manage.py runserver" 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 2

# ---- Load .env once for every child process --------------------------
set -a
# shellcheck disable=SC1091
source .env
set +a

if [ -z "${RUNWAY_API_KEY:-}" ] || [ -z "${OPENAI_API_KEY:-}" ]; then
  echo "⚠️  RUNWAY_API_KEY or OPENAI_API_KEY empty — media-engine will fall back to mock." >&2
  echo "    If mock is intentional, prefer scripts/start-local-mock.sh." >&2
fi

# ---- Bring up infra --------------------------------------------------
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

# ---- FastAPI media-engine (port 8001) -------------------------------
(
  cd media-engine
  nohup ../.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8001 --log-level warning \
    > "${MEDIA_LOG}" 2>&1 &
  echo "$!" > /tmp/character-os-media.pid
)

# ---- Celery worker (composition renders, transcripts, tools) --------
# ``execute_composition`` is CPU-light (mostly I/O to media-engine +
# providers); concurrency=2 is enough for one operator's UI flows.
(
  cd shell
  nohup ../.venv/bin/celery -A character_os worker \
    --loglevel=info --concurrency=2 \
    > "${CELERY_LOG}" 2>&1 &
  echo "$!" > /tmp/character-os-celery.pid
)

# ---- Vite SPA (port 5174) -------------------------------------------
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
echo "── HTTP health probes ────────────────────────────────"
printf "  django       "; curl -sfo /dev/null -w "http=%{http_code}\n" http://localhost:8010/admin/ || echo "not responding"
printf "  media-engine "; curl -sf http://localhost:8001/health | head -c 200; echo
printf "  web (vite)   "; curl -sfo /dev/null -w "http=%{http_code}\n" http://localhost:5174/ || echo "not responding"

echo
echo "── Celery worker probe ───────────────────────────────"
# ``celery inspect ping`` sends a control-channel ping via the broker
# and waits for the worker's reply. Load-bearing gate on this script:
# if the worker cannot reach Redis, or Redis is down, or the worker
# did not fully boot, this fails with a clear message. Retry a few
# times because worker boot lags docker up.
CELERY_OK=""
for attempt in 1 2 3 4 5; do
  if (cd shell && ../.venv/bin/celery -A character_os inspect ping --timeout 3 2>/dev/null | grep -q 'pong'); then
    CELERY_OK="yes"
    break
  fi
  sleep 2
done
if [ -n "${CELERY_OK}" ]; then
  echo "  ✅ worker replied to inspect ping — broker + worker are connected."
else
  echo "  ❌ worker did not respond to inspect ping within ~10s." >&2
  echo "     Tail ${CELERY_LOG} for the underlying reason." >&2
  exit 1
fi

echo
echo "── PIDs ──────────────────────────────────────────────"
pgrep -lf 'manage.py runserver|uvicorn app.main:app|celery -A character_os worker|vite' || true

cat <<NOTE

✅ Character OS booted (real-mode default).
   Django       http://localhost:8010
   Media engine http://localhost:8001
   Web          http://localhost:5174

   Media-engine health JSON above shows runway_mock / image_gen_mock —
   when RUNWAY_API_KEY is set, runway_mock=false and clicks burn credits.

   Celery consumes composition renders + transcript captures + tool
   dispatch. If a composition sits in DRAFT forever, this worker
   died — check ${CELERY_LOG}.

   Stop:  bash scripts/stop-local.sh
   Mock:  bash scripts/start-local-mock.sh   (no real-provider spend)
NOTE
