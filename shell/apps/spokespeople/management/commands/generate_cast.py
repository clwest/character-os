"""Generate portraits for Character OS's marketing cast.

Loops through ``character_os.templates.TEMPLATES`` (Riggs / Sasha /
Donny / Maya), fires ``MediaEngineClient.create_portrait()`` against
each character's ``visual_template`` + ``visual_subject``, and saves
the resulting PNG to ``shell/data/cast/<key>.png`` for the operator
to review.

Mock-mode produces deterministic placeholder PNGs (a solid color
keyed off a hash of the prompt) — useful to confirm the pipeline is
live, but not the actual character portrait. Set ``RUNWAY_API_KEY``
in the media-engine env to generate real gen4_image portraits.

Usage::

    python manage.py generate_cast
    python manage.py generate_cast --key maya
    python manage.py generate_cast --output-dir /tmp/cast

The output directory defaults to ``<shell>/data/cast/`` (gitignored).
Once you're happy with a portrait, you can seed the matching
Spokesperson row via the wizard at /spokespeople/new (or any other
ingestion path) and use the PNG as the avatar's portrait_data_uri.

Exit codes:
    0 — every requested template generated cleanly.
    1 — media-engine unreachable, unknown --key, or unexpected
        data-URI shape from the upstream.
"""
from __future__ import annotations

import base64
import sys
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand

from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.templates import TEMPLATES, get_template

_EXPECTED_PREFIX = "data:image/png;base64,"


class Command(BaseCommand):
    help = (
        "Generate the four Character OS marketing cast portraits via "
        "the media-engine's /internal/portrait/ endpoint and save each "
        "PNG to data/cast/<key>.png for operator review."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--key",
            default=None,
            help=(
                "Generate just one cast member (e.g. 'maya'). Defaults "
                "to all four templates."
            ),
        )
        parser.add_argument(
            "--output-dir",
            default=None,
            help=(
                "Override the default output directory "
                "(shell/data/cast/)."
            ),
        )

    def handle(self, *_, **opts: Any) -> None:
        # 1 — resolve which template(s) to generate.
        if opts["key"]:
            t = get_template(opts["key"])
            if t is None:
                self.stderr.write(
                    self.style.ERROR(
                        f"unknown template key: {opts['key']!r}. "
                        f"Valid keys: {', '.join(x.key for x in TEMPLATES)}."
                    )
                )
                sys.exit(1)
            targets = (t,)
        else:
            targets = TEMPLATES

        # 2 — resolve output dir + create if missing.
        if opts["output_dir"]:
            output_dir = Path(opts["output_dir"]).expanduser().resolve()
        else:
            output_dir = Path(settings.BASE_DIR) / "data" / "cast"
        output_dir.mkdir(parents=True, exist_ok=True)
        self.stdout.write(f"  → output dir: {output_dir}")

        # 3 — probe the media-engine. Warn loudly on mock mode so the
        #     operator knows the resulting PNGs are placeholders.
        try:
            with MediaEngineClient() as client:
                health = client.health_check()
        except MediaEngineError as exc:
            self.stderr.write(
                self.style.ERROR(
                    f"media engine unreachable — start it on :8001 "
                    f"first ({exc})"
                )
            )
            sys.exit(1)
        if health.runway_mock:
            self.stdout.write(
                self.style.WARNING(
                    "  ! Runway mock-mode is on. The output PNGs will "
                    "be deterministic placeholder colours, not real "
                    "gen4_image portraits. Set RUNWAY_API_KEY in the "
                    "media-engine env to generate the actual cast."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "  ✓ Runway live mode — generating real portraits."
                )
            )

        # 4 — generate + save each.
        with MediaEngineClient() as client:
            for t in targets:
                try:
                    result = client.create_portrait(
                        template=t.visual_template,
                        subject=t.visual_subject,
                    )
                except MediaEngineError as exc:
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ✗ {t.key}: create_portrait failed — {exc}"
                        )
                    )
                    sys.exit(1)

                if not result.portrait_data_uri.startswith(_EXPECTED_PREFIX):
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ✗ {t.key}: unexpected data URI prefix "
                            f"(got {result.portrait_data_uri[:40]!r})"
                        )
                    )
                    sys.exit(1)
                png_bytes = base64.b64decode(
                    result.portrait_data_uri[len(_EXPECTED_PREFIX):]
                )

                out_path = output_dir / f"{t.key}.png"
                out_path.write_bytes(png_bytes)
                self.stdout.write(
                    f"  ✓ {t.key:6s} ({t.name}) → {out_path.name}  "
                    f"[{len(png_bytes):,} B · prompt={len(result.prompt)}c · "
                    f"mock={result.mock_mode}]"
                )

        self.stdout.write(self.style.SUCCESS("\n✓ cast generation complete"))
