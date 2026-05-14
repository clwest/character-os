"""End-to-end smoke test for the SESSION 114 headless auth surface.

Exercises:

    GET  /_allauth/browser/v1/config        → public auth config
    GET  /_allauth/browser/v1/auth/session  → 401 (unauthenticated)
    POST /_allauth/browser/v1/auth/signup   → 200 + creates User
    → Phase 1 signal handler auto-creates Workspace + Membership
    → Phase 1 billing handler creates Subscription (Starter+trialing)

Hits the running Django dev server via HTTP (uses Django's test
client so no live server is needed). The full sign-up code path runs
including the post_save signal handlers, which is what we actually
care about — the JSON surface is one transport; the cascade is the
real behaviour.

Usage:
    python manage.py smoke_headless_auth
    python manage.py smoke_headless_auth --email custom@example.com
    python manage.py smoke_headless_auth --keep

Exit codes:
    0 — signup returned 200 + User + Workspace + Membership +
        Subscription all landed on the fresh row
    1 — anything else
"""
from __future__ import annotations

import json
import sys
import uuid
from typing import Any, NoReturn

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.test import Client

User = get_user_model()


class Command(BaseCommand):
    help = (
        "Smoke-test the allauth.headless surface end-to-end: GET config, "
        "GET unauth session, POST signup, assert User + Workspace + "
        "Membership + Subscription all land."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--email",
            default=None,
            help=(
                "Email to register. Defaults to "
                "`smoke-headless-<uuid8>@character-os.test`."
            ),
        )
        parser.add_argument(
            "--keep",
            action="store_true",
            help="Keep the test user + workspace (default: delete on exit).",
        )

    def handle(self, *_, **opts: Any) -> None:
        client = Client()
        email = opts["email"] or f"smoke-headless-{uuid.uuid4().hex[:8]}@character-os.test"
        password = "smoke-test-pw-x4q9z!"

        # 1 — public config endpoint. No auth, no CSRF, just JSON.
        resp = client.get("/_allauth/browser/v1/config")
        if resp.status_code != 200:
            self._fail(f"GET /_allauth/browser/v1/config returned {resp.status_code}")
        config = resp.json()
        account_cfg = config["data"]["account"]
        # allauth emits either `login_methods` (when ACCOUNT_LOGIN_METHODS
        # is the canonical setting) or `authentication_method` (when
        # ACCOUNT_AUTHENTICATION_METHOD is set). Tolerate both.
        auth_methods = account_cfg.get("login_methods") or [
            account_cfg.get("authentication_method")
        ]
        self.stdout.write(
            f"  ✓ /_allauth/browser/v1/config "
            f"(auth_methods={auth_methods}, "
            f"signup_open={account_cfg['is_open_for_signup']})"
        )

        # 2 — anonymous session probe should return 401 with the
        # available flows. Important assertion: the flows list tells
        # the SPA what auth surface is wired (login + signup at
        # minimum).
        resp = client.get("/_allauth/browser/v1/auth/session")
        if resp.status_code != 401:
            self._fail(
                f"GET /_allauth/browser/v1/auth/session returned "
                f"{resp.status_code}, expected 401"
            )
        session = resp.json()
        flow_ids = sorted(f.get("id") for f in session.get("data", {}).get("flows", []))
        self.stdout.write(
            f"  ✓ /_allauth/browser/v1/auth/session unauth → 401 "
            f"with flows={flow_ids}"
        )

        # 3 — POST signup. allauth.headless follows the same flow
        # the HTML form does — the only difference is JSON in / JSON
        # out. The Phase 1 post_save signal handlers must still fire,
        # which is the load-bearing assertion of this whole smoke.
        signup_body = {
            "email": email,
            "password": password,
        }
        resp = client.post(
            "/_allauth/browser/v1/auth/signup",
            data=json.dumps(signup_body),
            content_type="application/json",
        )
        if resp.status_code not in {200, 401}:
            # 401 is what allauth returns when email verification is
            # required + the session is held pending verification.
            # 200 is what it returns when verification is optional
            # (our scaffold setting) and the user is authenticated
            # straight through.
            self._fail(
                f"POST /_allauth/browser/v1/auth/signup returned "
                f"{resp.status_code}: {resp.content!r}"
            )
        self.stdout.write(
            f"  ✓ /_allauth/browser/v1/auth/signup → {resp.status_code} "
            f"(email={email})"
        )

        # 4 — Assert the Phase 1 cascade fired. The signal handler in
        # apps.accounts.signals creates a Workspace + Membership; the
        # billing handler in apps.billing creates a Subscription.
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            self._fail(
                f"signup returned 2xx but no User row for email={email!r}"
            )
        from apps.accounts.models import Membership, Workspace

        workspace = Workspace.objects.filter(owner=user).first()
        if workspace is None:
            self._fail(
                f"User {user.pk} created but no Workspace auto-bootstrapped "
                "— check apps.accounts.signals"
            )

        membership = Membership.objects.filter(user=user, workspace=workspace).first()
        if membership is None:
            self._fail(
                f"Workspace {workspace.slug} exists but no owner-Membership "
                "for the user — check apps.accounts.signals"
            )

        from apps.billing.models import Subscription
        subscription = Subscription.objects.filter(workspace=workspace).first()
        if subscription is None:
            self._fail(
                f"Workspace {workspace.slug} exists but no Subscription "
                "bootstrapped — check apps.billing signal handler"
            )

        self.stdout.write(
            f"  ✓ Phase 1 cascade fired "
            f"(user={user.pk}, workspace='{workspace.slug}', "
            f"role={membership.role}, "
            f"tier={subscription.tier}, status={subscription.status})"
        )

        # 5 — Authenticated session probe (cookies were set on the
        # signup response). Should now return 200 instead of 401.
        resp = client.get("/_allauth/browser/v1/auth/session")
        if resp.status_code != 200:
            self._fail(
                f"GET /_allauth/browser/v1/auth/session post-signup returned "
                f"{resp.status_code}, expected 200"
            )
        session = resp.json()
        is_authed = session.get("meta", {}).get("is_authenticated")
        self.stdout.write(
            f"  ✓ /_allauth/browser/v1/auth/session auth → 200 "
            f"(is_authenticated={is_authed})"
        )

        # Cleanup.
        if not opts["keep"]:
            workspace.delete()  # CASCADE clears Membership + Subscription
            user.delete()
            self.stdout.write(f"  ✓ cleaned up test user + workspace")
        else:
            self.stdout.write(
                self.style.WARNING(
                    f"  ! keeping user {user.pk} + workspace '{workspace.slug}'"
                )
            )

        self.stdout.write(self.style.SUCCESS("✓ smoke test PASSED"))

    def _fail(self, message: str) -> NoReturn:
        self.stderr.write(self.style.ERROR(f"✗ {message}"))
        sys.exit(1)
