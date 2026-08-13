"""Project package init.

Re-exports the Celery app so the ``@shared_task`` decorator in
``apps/*/tasks.py`` finds the right Celery instance when Django
boots. Django imports this module on startup; importing ``celery_app``
here ensures Celery is fully initialised before any task module
loads.
"""
from .celery import app as celery_app

__all__ = ("celery_app",)
