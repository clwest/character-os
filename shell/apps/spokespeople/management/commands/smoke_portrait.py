"""End-to-end smoke test for SESSION 125 — wizard slice 2.

Drives ``POST /internal/portrait/`` for each of the four inherited
``PORTRAIT_TEMPLATES`` (mascot / founder / coach / local_guide).
Asserts each response data URI starts with the expected MIME
prefix + has a non-trivial payload.

Mock-mode only — no Runway credits burned. With a real
``RUNWAY_API_KEY`` set, the same command exercises the real Runway
gen4_image path and is correspondingly slower (10-20 s per
template).

Run with the FastAPI media-engine listening on :8001.

Usage:
    python manage.py smoke_portrait
    python manage.py smoke_portrait --template mascot
    python manage.py smoke_portrait --subject "armored battle unicorn warrior"

Exit codes:
    0 — every template returned a data URI with the right shape
    1 — anything else (media-engine unreachable, template unknown,
        empty payload, etc.)
"""
from __future__ import annotations

import sys
from typing import Any

from django.core.management.base import BaseCommand

from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)

_DEFAULT_TEMPLATES: tuple[str, ...] = ("mascot", "founder", "coach", "local_guide")
_EXPECTED_PREFIX = "data:image/png;base64,"


class Command(BaseCommand):
    help = (
        "Smoke-test the SESSION 125 portrait endpoint: POST /internal/portrait/ "
        "for each of the inherited PORTRAIT_TEMPLATES, assert the response "
        "data URI shape."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--template",
            default=None,
            help=(
                "Only exercise the given template. Defaults to running all four "
                f"({', '.join(_DEFAULT_TEMPLATES)})."
            ),
        )
        parser.add_argument(
            "--subject",
            default=None,
            help="Override the per-template default subject.",
        )
        parser.add_argument(
            "--style",
            default=None,
            help="Optional style hint (free-form text or chip names).",
        )

    def handle(self, *_, **opts: Any) -> None:
        # 1 — media-engine reachable? Fail fast.
        try:
            with MediaEngineClient() as client:
                health = client.health_check()
        except MediaEngineError as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"media engine unreachable — start it on :8001 first ({exc})"
                )
            )
            sys.exit(1)
        self.stdout.write(
            f"  ✓ media engine reachable (runway_mock={health.runway_mock})"
        )

        # 2 — pick which templates to exercise.
        if opts["template"]:
            templates = (opts["template"],)
        else:
            templates = _DEFAULT_TEMPLATES

        # 3 — generate one portrait per template + assert shape.
        with MediaEngineClient() as client:
            for template in templates:
                try:
                    result = client.create_portrait(
                        template=template,
                        subject=opts["subject"],
                        style=opts["style"],
                    )
                except MediaEngineError as exc:
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ✗ {template}: create_portrait failed — {exc}"
                        )
                    )
                    sys.exit(1)

                if not result.portrait_data_uri.startswith(_EXPECTED_PREFIX):
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ✗ {template}: data URI doesn't start with "
                            f"{_EXPECTED_PREFIX!r} (got {result.portrait_data_uri[:40]!r})"
                        )
                    )
                    sys.exit(1)

                # Strip the prefix to inspect payload size — guard
                # against zero-byte responses that pass the prefix
                # check but are otherwise useless.
                payload_b64 = result.portrait_data_uri[len(_EXPECTED_PREFIX):]
                if len(payload_b64) < 32:
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ✗ {template}: payload too small ({len(payload_b64)} chars)"
                        )
                    )
                    sys.exit(1)

                self.stdout.write(
                    f"  ✓ {template}: data_uri={len(payload_b64):,} chars · "
                    f"prompt_len={len(result.prompt)} · "
                    f"mock={result.mock_mode}"
                )

        self.stdout.write(self.style.SUCCESS("✓ smoke test PASSED"))
