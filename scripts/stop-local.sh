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

# Order: kill Celery first so it doesn't complain about a lost broker
# when its Redis client is torn down.
pkill -f "celery -A character_os worker" 2>/dev/null || true
pkill -f "manage.py runserver" 2>/dev/null || true
pkill -f "uvicorn app.main:app" 2>/dev/null || true
pkill -f "vite" 2>/dev/null || true
sleep 1

REMAINING="$(pgrep -lf 'manage.py runserver|uvicorn app.main:app|celery -A character_os worker|vite' || true)"
if [ -n "${REMAINING}" ]; then
  echo "⚠️  some processes still alive:"
  echo "${REMAINING}"
  exit 1
fi
echo "✅ Character OS processes stopped (docker infra left up)."
