"""Celery application for the Django shell.

Phase 2 (SESSION 109) — landed early to support the fire-then-poll
media-engine video pipeline. Real-mode Runway video generation
takes 60-120 s; we can't hold an HTTP request open for that, so
``POST /api/videos/`` returns ``201 {status: "pending"}``
immediately and enqueues ``poll_video_until_terminal`` here. The
worker polls the media-engine on a bounded loop and writes back
``status`` / ``output_path`` / ``duration_seconds`` /
``error_message`` to the ``Video`` row.

Broker + result backend both ride on Redis (single dependency).
Auto-discovery scans every ``apps/*/tasks.py`` so individual apps
own their task implementations.

Worker entry point (local dev):

    cd shell && source .venv/bin/activate
    celery -A character_os worker --loglevel=INFO

Ping smoke check:

    celery -A character_os inspect ping
"""
from __future__ import annotations

import os

from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "character_os.settings")

app = Celery("character_os")

# Pull Celery config from Django settings — anything namespaced
# CELERY_* (e.g. CELERY_BROKER_URL) becomes the corresponding Celery
# config key. Keeps secrets + tuning in one place (settings.py /
# environment).
app.config_from_object("django.conf:settings", namespace="CELERY")

# Auto-discover ``tasks.py`` in every installed app. apps/videos/tasks.py
# is the first consumer; apps/spokespeople/, apps/conversations/, etc.
# will register here as they grow.
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self) -> None:
    """Smoke task used by ``celery -A character_os inspect ping`` and
    by the worker boot probe. No side effects."""
    print(f"celery debug_task fired: request={self.request!r}")
