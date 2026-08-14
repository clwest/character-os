#!/usr/bin/env bash
#
# stop-local.sh — kill every Character OS process started by
# ``start-local-real.sh`` or ``start-local-mock.sh``. Kept in sync
# with the process set those scripts spawn.
#
# Does NOT stop docker-compose infra (Postgres + Redis) so subsequent
# starts are fast and pgvector state survives. Use
# ``docker compose -f infra/docker-compose.yml down`` for that.
#
# Usage:
#   bash scripts/stop-local.sh

set -u

PATTERN='manage.py runserver|uvicorn app.main:app|celery -A character_os worker|vite'

# Order: kill Celery first so it doesn't complain about a lost broker
# when its Redis client is torn down. SIGTERM first (default) so
# Celery does its warm-shutdown (finishes in-flight tasks); if a
# task is in-flight this may take a few seconds.
pkill -f "celery -A character_os worker" 2>/dev/null || true
pkill -f "manage.py runserver" 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true

# Wait up to ~8s for graceful shutdown to complete. Celery's
# multiprocessing pool teardown can take 3-5s even on an idle
# worker (SESSION 251 caught this — a 1s wait exit-1'd on a
# healthy shutdown). Poll rather than sleep-and-hope.
for i in 1 2 3 4 5 6 7 8; do
  if ! pgrep -f "${PATTERN}" > /dev/null 2>&1; then
    echo "✅ Character OS processes stopped (docker infra left up)."
    exit 0
  fi
  sleep 1
done

# Anything still alive at this point is stuck — force-kill and
# report so the operator knows an ungraceful shutdown happened.
STUCK="$(pgrep -lf "${PATTERN}" || true)"
if [ -n "${STUCK}" ]; then
  echo "⚠️  processes did not exit cleanly within 8s — sending SIGKILL:"
  echo "${STUCK}"
  pkill -9 -f "${PATTERN}" 2>/dev/null || true
  sleep 1
fi

REMAINING="$(pgrep -lf "${PATTERN}" || true)"
if [ -n "${REMAINING}" ]; then
  echo "❌ processes survived SIGKILL — manual intervention needed:"
  echo "${REMAINING}"
  exit 1
fi
echo "✅ Character OS processes stopped (docker infra left up)."
