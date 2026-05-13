"""Smoke-check that the FastAPI media engine is reachable + healthy.

Usage:
    python manage.py ping_media_engine
    python manage.py ping_media_engine --json    # machine-readable output

Exit codes:
    0 — service reachable, status="ok"
    1 — anything else (unreachable, non-2xx, unexpected body shape)

This is the smallest test of the Django↔FastAPI boundary defined in
the design doc §6.2. Running it after a fresh repo checkout (or in CI)
proves the two services are wired correctly without firing any actual
media generation.
"""
from __future__ import annotations

import json
import sys
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from character_os.clients.media_engine import MediaEngineClient, MediaEngineError


class Command(BaseCommand):
    help = "Hit /health on the FastAPI media engine; exit 0 if healthy, 1 otherwise."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--json",
            action="store_true",
            help="Emit a machine-readable JSON payload instead of a human report.",
        )
        parser.add_argument(
            "--timeout",
            type=float,
            default=5.0,
            help="HTTP timeout in seconds (default: 5).",
        )

    def handle(self, *args: Any, **opts: Any) -> None:
        emit_json: bool = opts["json"]
        timeout: float = opts["timeout"]

        try:
            with MediaEngineClient(timeout=timeout) as client:
                health = client.health_check()
        except MediaEngineError as exc:
            payload = {
                "ok": False,
                "error": str(exc),
                "status_code": exc.status_code,
                "response_text": exc.response_text,
            }
            if emit_json:
                self.stdout.write(json.dumps(payload))
            else:
                self.stderr.write(self.style.ERROR(f"media engine UNREACHABLE: {exc}"))
                if exc.status_code is not None:
                    self.stderr.write(f"  status_code = {exc.status_code}")
                if exc.response_text:
                    self.stderr.write(f"  response   = {exc.response_text[:200]}")
            sys.exit(1)

        payload = {
            "ok": health.healthy,
            "status": health.status,
            "service": health.service,
            "openai_mock": health.openai_mock,
            "runway_mock": health.runway_mock,
            "image_gen_mock": health.image_gen_mock,
            "extras": health.extras,
        }
        if emit_json:
            self.stdout.write(json.dumps(payload))
            return

        if not health.healthy:
            self.stderr.write(self.style.WARNING(f"media engine returned status={health.status!r}"))
            raise CommandError(f"media engine reports unhealthy: {payload}")

        self.stdout.write(self.style.SUCCESS(f"✓ {health.service} reachable, status=ok"))
        self.stdout.write(f"  openai_mock    = {health.openai_mock}")
        self.stdout.write(f"  runway_mock    = {health.runway_mock}")
        self.stdout.write(f"  image_gen_mock = {health.image_gen_mock}")
        if health.extras:
            self.stdout.write(f"  extras         = {health.extras}")
