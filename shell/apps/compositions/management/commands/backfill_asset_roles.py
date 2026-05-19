"""Asset Library v1 (SESSION 185, slice A1) — backfill management command.

Maps existing Asset rows from their default ``RAW_UPLOAD`` role
(set by the A0 migration) to a primitive_kind-derived role using
the heuristics in ``docs/design/ASSET_LIBRARY_V1.md`` §Taxonomy.

Behavior:

* **Dry-run is the default.** Prints a per-role summary plus the
  full list of assets that would change. Nothing is written.
* **``--commit`` actually applies the plan.** No silent backfills
  (Q-a-2, contract rule 17). Operator reviews the dry-run report,
  then re-runs with ``--commit``.
* **``--workspace <slug>`` scopes to one workspace** by name. Useful
  for staged rollout. Defaults to all workspaces.
* **Idempotent.** Only processes rows where ``role == RAW_UPLOAD``.
  Re-running after a partial commit picks up only the still-default
  rows.

Heuristic table (primitive_kind → AssetRole):

* generate_avatar_speech / remove_avatar_background → TALKING_HEAD
* generate_visual_clip / extend_visual_clip / concat_clips → BACKDROP
* composite_video / mix_audio → COMPOSITE_OUTPUT
* add_captions / add_intro_outro / trim_clip / reformat_clip /
  style_remix → POLISH_OUTPUT
* generate_image → REFERENCE_IMAGE
* transcribe / split_script / realtime_transcript → TRANSCRIPT
* design_voice / dub_audio / audio_extract → AUDIO_TRACK
* smoke_keyframes → EXPERIMENT

Plus the two known smoke-emitted asset UUIDs from SESSION 184
(``c21fdeec...`` veo3.1_fast, ``89a1ce5f...`` gen3a_turbo) which
were backfilled manually via Django shell with no primitive_kind
— they're hard-coded as EXPERIMENT.

Assets that match no heuristic are listed as **needs review** in
the report and left at ``RAW_UPLOAD``.
"""
from __future__ import annotations

from collections import defaultdict

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetRole


# Heuristic table: source_spec.primitive_kind → target role.
# Add a row here when a new primitive lands (contract rule 20 —
# no new primitive emits without a role).
PRIMITIVE_TO_ROLE: dict[str, str] = {
    # Avatar foreground
    "generate_avatar_speech": AssetRole.TALKING_HEAD.value,
    "remove_avatar_background": AssetRole.TALKING_HEAD.value,
    # Scene / backdrop
    "generate_visual_clip": AssetRole.BACKDROP.value,
    "extend_visual_clip": AssetRole.BACKDROP.value,
    "concat_clips": AssetRole.BACKDROP.value,
    # Composite combiners
    "composite_video": AssetRole.COMPOSITE_OUTPUT.value,
    "mix_audio": AssetRole.COMPOSITE_OUTPUT.value,
    # Polish / post-composite refinement
    "add_captions": AssetRole.POLISH_OUTPUT.value,
    "add_intro_outro": AssetRole.POLISH_OUTPUT.value,
    "trim_clip": AssetRole.POLISH_OUTPUT.value,
    "reformat_clip": AssetRole.POLISH_OUTPUT.value,
    "style_remix": AssetRole.POLISH_OUTPUT.value,
    # Image (for keyframes / reference)
    "generate_image": AssetRole.REFERENCE_IMAGE.value,
    # Text / transcript
    "transcribe": AssetRole.TRANSCRIPT.value,
    "split_script": AssetRole.TRANSCRIPT.value,
    "realtime_transcript": AssetRole.TRANSCRIPT.value,
    # Standalone audio
    "design_voice": AssetRole.AUDIO_TRACK.value,
    "dub_audio": AssetRole.AUDIO_TRACK.value,
    "audio_extract": AssetRole.AUDIO_TRACK.value,
    # Sandbox / experimental
    "smoke_keyframes": AssetRole.EXPERIMENT.value,
}


# SESSION 184 manually-inserted smoke outputs that lack
# primitive_kind. Hard-coded per ASSET_LIBRARY_V1.md
# §In-scope clarifications.
KNOWN_EXPERIMENT_UUID_PREFIXES: tuple[str, ...] = (
    "c21fdeec",  # veo3.1_fast smoke output
    "89a1ce5f",  # gen3a_turbo smoke output
)


def derive_role(asset: Asset) -> str | None:
    """Return the target role for ``asset``, or ``None`` if no
    heuristic matches (operator review required)."""
    asset_uuid = str(asset.id)
    for prefix in KNOWN_EXPERIMENT_UUID_PREFIXES:
        if asset_uuid.startswith(prefix):
            return AssetRole.EXPERIMENT.value

    source_spec = asset.source_spec or {}
    primitive_kind = source_spec.get("primitive_kind")
    if primitive_kind and primitive_kind in PRIMITIVE_TO_ROLE:
        return PRIMITIVE_TO_ROLE[primitive_kind]

    return None


class Command(BaseCommand):
    help = (
        "Backfill Asset.role from source_spec.primitive_kind. "
        "Dry-run by default; pass --commit to apply."
    )

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--commit",
            action="store_true",
            help=(
                "Apply the backfill plan. Without this flag the command "
                "only prints a report. Q-a-2 / rule 17."
            ),
        )
        parser.add_argument(
            "--workspace",
            metavar="NAME",
            help=(
                "Scope to a single workspace by name. Defaults to all "
                "workspaces."
            ),
        )

    def handle(self, *args, **options) -> None:
        commit: bool = options["commit"]
        workspace_name: str | None = options["workspace"]

        qs = Asset.objects.filter(role=AssetRole.RAW_UPLOAD)
        if workspace_name:
            try:
                ws = Workspace.objects.get(name=workspace_name)
            except Workspace.DoesNotExist as exc:
                raise CommandError(
                    f"workspace not found: {workspace_name!r}"
                ) from exc
            qs = qs.filter(workspace=ws)

        plan: dict[str, list[Asset]] = defaultdict(list)
        review: list[Asset] = []

        for asset in qs.iterator():
            target = derive_role(asset)
            if target is None:
                review.append(asset)
            else:
                plan[target].append(asset)

        self._print_report(plan, review, commit=commit)

        if not commit:
            return

        self._apply(plan)

    # ---- internal helpers --------------------------------------------

    def _print_report(
        self,
        plan: dict[str, list[Asset]],
        review: list[Asset],
        *,
        commit: bool,
    ) -> None:
        mode = "COMMIT" if commit else "DRY-RUN"
        total_planned = sum(len(rows) for rows in plan.values())
        total_review = len(review)
        total = total_planned + total_review

        self.stdout.write(f"backfill_asset_roles ({mode})")
        self.stdout.write("=" * 60)
        self.stdout.write(
            f"Candidates (Asset.role == RAW_UPLOAD): {total}"
        )
        self.stdout.write(
            f"  Mappable via heuristic:  {total_planned}"
        )
        self.stdout.write(
            f"  Needs operator review:   {total_review}"
        )
        self.stdout.write("")

        if plan:
            self.stdout.write("Per-role plan:")
            for role_value in sorted(plan):
                rows = plan[role_value]
                self.stdout.write(
                    f"  {role_value:>16} : {len(rows)} asset(s)"
                )
            self.stdout.write("")

        if review:
            self.stdout.write(
                "Needs operator review (no primitive_kind match, "
                "no known special-case UUID):"
            )
            for asset in review[:20]:
                self.stdout.write(
                    f"  {asset.id} "
                    f"asset_type={asset.asset_type} "
                    f"workspace={asset.workspace.name!r}"
                )
            remaining = len(review) - 20
            if remaining > 0:
                self.stdout.write(
                    f"  ... and {remaining} more (truncated)"
                )
            self.stdout.write("")

        if not commit:
            self.stdout.write(
                "DRY-RUN complete. Re-run with --commit to apply."
            )
        else:
            self.stdout.write("COMMIT mode — applying changes ...")

    def _apply(self, plan: dict[str, list[Asset]]) -> None:
        with transaction.atomic():
            for role_value, rows in plan.items():
                pks = [a.pk for a in rows]
                updated = Asset.objects.filter(pk__in=pks).update(
                    role=role_value
                )
                self.stdout.write(
                    f"  {role_value:>16} : {updated} row(s) updated"
                )
        self.stdout.write("done.")


# Re-exported for tests
__all__ = [
    "Command",
    "PRIMITIVE_TO_ROLE",
    "KNOWN_EXPERIMENT_UUID_PREFIXES",
    "derive_role",
]
