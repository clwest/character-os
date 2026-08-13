"""Seed Character OS's marketing cast as real Teammate rows.

The companion to ``generate_cast``. Where ``generate_cast`` writes
PNG files to disk for operator preview, ``seed_cast`` runs the
full create-spokesperson pipeline end-to-end for each of the four
cast members — generates the portrait via /internal/portrait/,
creates the Teammate row, binds the Runway avatar via
/internal/avatars/, and persists ``voice_id`` from the template's
``voice_preset``. Result: four ready-to-render Teammate rows
in the target workspace.

Mirrors the wizard's submit orchestration (SESSION 132's
``SpokespersonWizard.onSubmit`` → ``useCreateSpokesperson`` →
backend's ``perform_create``) but skips the SPA and runs as a
single CLI invocation.

Usage::

    python manage.py seed_cast
    python manage.py seed_cast --workspace-slug acme
    python manage.py seed_cast --key maya
    python manage.py seed_cast --force         # recreate existing

Mock-mode is fine for verifying the pipeline (each row binds a
mock avatar with ``runway_avatar_status="mock"``). Real-mode
(``RUNWAY_API_KEY`` set) creates the actual cast against Runway.

Exit codes:
    0 — every requested template seeded cleanly.
    1 — media-engine unreachable, no workspace, unknown --key,
        or a fatal create-portrait / create-avatar failure.

Skips already-existing rows (matched by ``(workspace, name)`` —
the unique constraint that would have rejected the insert anyway)
unless ``--force`` is passed, in which case the existing row is
deleted and recreated.
"""
from __future__ import annotations

import sys
from typing import Any

from django.core.management.base import BaseCommand

from apps.accounts.models import Workspace
from apps.identity import services as identity_services
from apps.identity.models import (
    ExecutionMode,
    ExecutionModeActual,
    GenerationProvider,
    PrequalificationSourceCall,
)
from apps.identity.prequalification import (
    PortraitRepresentation,
    RealtimeRepresentation,
    VoiceRepresentation,
)
from apps.spokespeople.models import Teammate
from character_os.clients.media_engine import (
    MediaEngineClient,
    MediaEngineError,
)
from character_os.templates import TEMPLATES, get_template


class Command(BaseCommand):
    help = (
        "Seed the four Character OS marketing cast templates "
        "(Riggs / Sasha / Donny / Maya) as real Teammate rows "
        "with bound Runway avatars + voice presets."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--workspace-slug",
            default=None,
            help=(
                "Pick a target workspace by slug. Defaults to the "
                "first workspace by created_at."
            ),
        )
        parser.add_argument(
            "--key",
            default=None,
            help=(
                "Seed just one cast member (e.g. 'maya'). Defaults "
                "to all four."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help=(
                "Delete + recreate existing cast rows. Default: "
                "skip rows that already exist (by name)."
            ),
        )

    def handle(self, *_, **opts: Any) -> None:
        # 1 — resolve which template(s) to seed.
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

        # 2 — resolve target workspace.
        workspace = self._pick_workspace(opts["workspace_slug"])
        if workspace is None:
            self.stderr.write(
                self.style.ERROR(
                    "no Workspace rows match. Create a user (which "
                    "auto-creates a workspace via the Phase 1 cascade) "
                    "first, or pass --workspace-slug explicitly."
                )
            )
            sys.exit(1)
        self.stdout.write(
            f"  → workspace: {workspace.name!r} (slug={workspace.slug!r})"
        )

        # 3 — probe the media-engine.
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
                    "  ! Runway mock-mode is on. Rows will land with "
                    "runway_avatar_status='mock'. Set RUNWAY_API_KEY "
                    "in the media-engine env for real avatars."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    "  ✓ Runway live mode — binding real avatars."
                )
            )

        # 4 — generate + seed each.
        force = bool(opts["force"])
        seeded = 0
        skipped = 0

        with MediaEngineClient() as client:
            for t in targets:
                existing = Teammate.objects.filter(
                    workspace=workspace, name=t.name
                ).first()
                if existing and not force:
                    self.stdout.write(
                        self.style.WARNING(
                            f"  ↷ {t.key:6s} ({t.name}) already exists "
                            f"(id={existing.pk}) — skipping. Use --force "
                            f"to recreate."
                        )
                    )
                    skipped += 1
                    continue
                if existing and force:
                    existing.delete()
                    self.stdout.write(
                        f"  ↻ {t.key:6s} ({t.name}) deleted existing row"
                    )

                # 4a — generate portrait.
                try:
                    portrait = client.create_portrait(
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

                # 4b — create the Teammate row.
                spokesperson = Teammate.objects.create(
                    workspace=workspace,
                    name=t.name,
                    business_brief=t.business_brief,
                    tone_archetype=t.tone_archetype,
                    visual_subject=t.visual_subject,
                )

                # 4c — bind the Runway avatar. Mirrors
                #      TeammateViewSet.perform_create's path.
                try:
                    avatar = client.create_avatar(
                        name=spokesperson.name,
                        portrait_data_uri=portrait.portrait_data_uri,
                        voice_preset=t.voice_preset,
                    )
                except MediaEngineError as exc:
                    # Match the wizard's calibration: row stays, status
                    # flips to "failed". Operator can retry from the
                    # detail page once the issue is resolved.
                    # §19 Step 4.d — voice_id is no longer written on
                    # the bake-failure path. A requested voice tied to
                    # a failed bake is not treated as successfully-
                    # authored identity state (matches rebake_avatar
                    # D2 discipline).
                    self.stderr.write(
                        self.style.WARNING(
                            f"  ⚠ {t.key}: avatar bind failed — {exc}. "
                            f"Row created with runway_avatar_status='failed'."
                        )
                    )
                    spokesperson.runway_avatar_status = "failed"
                    spokesperson.save(
                        update_fields=[
                            "runway_avatar_status",
                            "updated_at",
                        ]
                    )
                    seeded += 1
                    continue

                # 4d — canonical write for the three mirrors.
                # thumbnail_url is the Runway CDN URL (real mode) or
                # a base64 data URI (mock mode); either flavor renders
                # directly in <img src=...>.
                # §19 Step 4.d — persistence flows through
                # ``record_prequalification_representation``. The
                # media-engine call above is unchanged; only its
                # result landing point changes.
                is_mock = avatar.mock_mode
                exec_mode = (
                    ExecutionMode.FORCED_MOCK if is_mock
                    else ExecutionMode.REAL_REQUIRED
                )
                exec_actual = (
                    ExecutionModeActual.MOCK if is_mock
                    else ExecutionModeActual.REAL
                )
                bake_provider = (
                    GenerationProvider.MOCK if is_mock
                    else GenerationProvider.RUNWAY_AVATAR
                )
                try:
                    identity_services.record_prequalification_representation(
                        spokesperson,
                        source_call=PrequalificationSourceCall.SEED_CAST,
                        author=None,  # management command; no user
                        portrait=PortraitRepresentation(
                            portrait_uri=avatar.thumbnail_url or "",
                            provider=bake_provider,
                            provider_model="",
                            execution_mode=exec_mode,
                            execution_mode_actual=exec_actual,
                            mock_mode=is_mock,
                            provider_response={
                                "avatar_id": avatar.avatar_id,
                                "status": avatar.status,
                                "thumbnail_url": avatar.thumbnail_url,
                            },
                        ),
                        voice=VoiceRepresentation(
                            provider_voice_id=t.voice_preset,
                            provider=GenerationProvider.RUNWAY_TTS,
                            provider_model="",
                            execution_mode=ExecutionMode.REAL_REQUIRED,
                            execution_mode_actual=ExecutionModeActual.REAL,
                            mock_mode=is_mock,
                            voice_kind="preset",
                            provider_response={},
                        ),
                        realtime=RealtimeRepresentation(
                            provider_realtime_id=avatar.avatar_id,
                            provider=bake_provider,
                            provider_model="",
                            execution_mode=exec_mode,
                            execution_mode_actual=exec_actual,
                            mock_mode=is_mock,
                            provider_response={
                                "status": avatar.status,
                                "thumbnail_url": avatar.thumbnail_url,
                            },
                        ),
                    )
                except identity_services.BundleApprovalError as exc:
                    self.stderr.write(
                        self.style.ERROR(
                            f"  ✗ {t.key}: canonical write failed — "
                            f"{exc.code} — {exc}"
                        )
                    )
                    sys.exit(1)

                # Non-mirror fields: refresh so sync's mirror writes
                # are visible, then persist runway_avatar_status +
                # status.
                spokesperson.refresh_from_db()
                spokesperson.runway_avatar_status = avatar.status
                if avatar.ok:
                    spokesperson.status = Teammate.Status.READY
                spokesperson.save(
                    update_fields=[
                        "runway_avatar_status",
                        "status",
                        "updated_at",
                    ]
                )
                seeded += 1
                self.stdout.write(
                    f"  ✓ {t.key:6s} ({t.name}) → id={spokesperson.pk} · "
                    f"avatar={avatar.avatar_id} · status={avatar.status} · "
                    f"voice={t.voice_preset}"
                )

        # 5 — summary.
        self.stdout.write(
            self.style.SUCCESS(
                f"\n✓ seeded {seeded} / {len(targets)} cast members "
                f"({skipped} skipped) in workspace {workspace.slug!r}"
            )
        )

    @staticmethod
    def _pick_workspace(slug: str | None) -> Workspace | None:
        qs = Workspace.objects.all().order_by("created_at")
        if slug:
            return qs.filter(slug=slug).first()
        return qs.first()
