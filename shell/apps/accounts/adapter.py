"""Custom allauth account adapter.

The launch product uses email as the primary login identifier
(``ACCOUNT_USER_MODEL_USERNAME_FIELD = None``) but still relies on
Django's stock ``auth.User`` model, which has ``unique=True`` on
``username``. With allauth's default adapter, signups land with
``username=""`` — fine for the first user, fails the UNIQUE
constraint for every subsequent one.

Surfaced SESSION 116 by the Playwright e2e suite: backend smoke
(``smoke_headless_auth``) only ever creates one user at a time +
cleans it up, so the collision never landed. Playwright keeps test
rows around, which exposed it.

Fix: populate ``username`` from a stable hash of the email at save
time so the column has a unique value per user. Display + login
still happen via email; the username column is just satisfying
Django's UNIQUE invariant. When we migrate to a custom email-as-PK
User model (queued investigation), this adapter goes away.
"""
from __future__ import annotations

import hashlib

from allauth.account.adapter import DefaultAccountAdapter


def _username_from_email(email: str) -> str:
    """Stable, deterministic, ≤30 chars (Django's default
    ``User.username`` max length). Prefix ``u_`` makes them
    immediately identifiable as auto-derived in the admin."""
    digest = hashlib.sha256((email or "").encode("utf-8")).hexdigest()
    return ("u_" + digest)[:30]


class WorkspaceAccountAdapter(DefaultAccountAdapter):
    """Adapter that backfills ``username`` so multiple email-only
    signups don't collide on Django's stock ``auth.User`` UNIQUE
    constraint."""

    def save_user(self, request, user, form, commit=True):
        user = super().save_user(request, user, form, commit=False)
        if not user.username and user.email:
            user.username = _username_from_email(user.email)
        if commit:
            user.save()
        return user
