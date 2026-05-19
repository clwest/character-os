"""Asset Library v1 (SESSION 185, A1) — backfill management
command tests.

Coverage:

* Heuristic table covers every primitive_kind known to the
  codebase (no surprises when a new primitive lands).
* Dry-run is the default; nothing is written.
* ``--commit`` actually applies the plan.
* Known smoke UUIDs (``c21fdeec``, ``89a1ce5f``) map to
  ``EXPERIMENT`` even without primitive_kind.
* Assets with no recognized primitive_kind and no special-case
  UUID stay at ``RAW_UPLOAD`` and surface in the review list.
* Re-running after a partial commit is idempotent (only
  RAW_UPLOAD rows are reconsidered).
* ``--workspace`` scoping limits the operation.
"""
from __future__ import annotations

import uuid
from io import StringIO

import pytest
from django.contrib.auth import get_user_model
from django.core.management import call_command

from apps.accounts.models import Workspace
from apps.compositions.management.commands.backfill_asset_roles import (
    KNOWN_EXPERIMENT_UUID_PREFIXES,
    PRIMITIVE_TO_ROLE,
    derive_role,
)
from apps.compositions.models import Asset, AssetRole, AssetType

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- helpers --------------------------------------------------------


def _make_workspace(email: str, name: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    ws.name = name
    ws.save()
    return ws


def _make_asset(
    ws: Workspace,
    *,
    primitive_kind: str | None,
    asset_type: str = AssetType.CLIP,
    asset_id: uuid.UUID | None = None,
) -> Asset:
    source_spec: dict = {}
    if primitive_kind is not None:
        source_spec["primitive_kind"] = primitive_kind
    kwargs: dict = dict(
        workspace=ws,
        asset_type=asset_type,
        file_path=f"/fake/{primitive_kind or 'unknown'}.bin",
        source_spec=source_spec,
    )
    if asset_id is not None:
        kwargs["id"] = asset_id
    return Asset.objects.create(**kwargs)


def _run(*args: str) -> str:
    buf = StringIO()
    call_command("backfill_asset_roles", *args, stdout=buf)
    return buf.getvalue()


# ---- heuristic-table coverage --------------------------------------


def test_heuristic_table_covers_every_primitive_kind_in_codebase() -> None:
    """Contract rule 20: every primitive in apps.compositions.primitives
    has a registered role. The migration test variant lives in A2;
    this is the A1-level check — the backfill table must include
    every primitive_kind string emitted by the compositions package.

    If a new primitive lands without updating PRIMITIVE_TO_ROLE, this
    test fails loudly. That's the contract.
    """
    # Reading source_spec.primitive_kind values currently emitted:
    expected_primitives = {
        "generate_avatar_speech",
        "remove_avatar_background",
        "generate_visual_clip",
        "extend_visual_clip",
        "concat_clips",
        "composite_video",
        "mix_audio",
        "add_captions",
        "add_intro_outro",
        "trim_clip",
        "reformat_clip",
        "style_remix",
        "generate_image",
        "transcribe",
        "split_script",
        "realtime_transcript",
        "design_voice",
        "dub_audio",
        "audio_extract",
        "smoke_keyframes",
    }
    missing = expected_primitives - set(PRIMITIVE_TO_ROLE)
    assert not missing, (
        f"PRIMITIVE_TO_ROLE missing entries for: {sorted(missing)}. "
        "Add them to apps.compositions.management.commands.backfill_asset_roles."
    )


def test_derive_role_for_each_known_primitive_kind() -> None:
    """Every entry in PRIMITIVE_TO_ROLE returns a valid AssetRole value."""
    valid_values = {v for v, _ in AssetRole.choices}
    for primitive_kind, role_value in PRIMITIVE_TO_ROLE.items():
        assert role_value in valid_values, (
            f"PRIMITIVE_TO_ROLE[{primitive_kind!r}] = {role_value!r} "
            f"is not in AssetRole.choices"
        )


# ---- known smoke UUIDs ---------------------------------------------


def test_known_smoke_uuids_map_to_experiment() -> None:
    """SESSION 184 manually-inserted smoke outputs lack
    primitive_kind. The two known UUID prefixes are hard-coded
    as EXPERIMENT per the design doc §In-scope clarifications."""
    ws = _make_workspace("smokeuuid@test.local", "Smoke UUID WS")
    smoke_uuid = uuid.UUID(KNOWN_EXPERIMENT_UUID_PREFIXES[0] + "-0000-0000-0000-000000000001")
    asset = _make_asset(
        ws,
        primitive_kind=None,
        asset_type=AssetType.CLIP,
        asset_id=smoke_uuid,
    )
    assert derive_role(asset) == AssetRole.EXPERIMENT.value


# ---- dry-run is default --------------------------------------------


def test_dry_run_is_default_and_writes_nothing() -> None:
    ws = _make_workspace("dryrun@test.local", "Dry Run WS")
    asset = _make_asset(ws, primitive_kind="generate_avatar_speech")

    output = _run()  # no --commit

    asset.refresh_from_db()
    assert asset.role == AssetRole.RAW_UPLOAD
    assert "DRY-RUN" in output
    assert "Re-run with --commit to apply" in output


# ---- --commit applies ----------------------------------------------


def test_commit_applies_the_plan() -> None:
    ws = _make_workspace("commit@test.local", "Commit WS")
    head_asset = _make_asset(ws, primitive_kind="generate_avatar_speech")
    backdrop_asset = _make_asset(ws, primitive_kind="generate_visual_clip")
    composite_asset = _make_asset(ws, primitive_kind="composite_video")

    output = _run("--commit")

    head_asset.refresh_from_db()
    backdrop_asset.refresh_from_db()
    composite_asset.refresh_from_db()
    assert head_asset.role == AssetRole.TALKING_HEAD
    assert backdrop_asset.role == AssetRole.BACKDROP
    assert composite_asset.role == AssetRole.COMPOSITE_OUTPUT
    assert "COMMIT" in output


# ---- unrecognized rows surface for review --------------------------


def test_unrecognized_rows_stay_raw_upload_and_surface_for_review() -> None:
    ws = _make_workspace("review@test.local", "Review WS")
    # No primitive_kind; not a known UUID.
    odd = _make_asset(ws, primitive_kind=None)
    # Bogus primitive_kind not in the heuristic table.
    bogus = _make_asset(ws, primitive_kind="some_future_primitive")

    output = _run("--commit")

    odd.refresh_from_db()
    bogus.refresh_from_db()
    assert odd.role == AssetRole.RAW_UPLOAD
    assert bogus.role == AssetRole.RAW_UPLOAD
    assert "Needs operator review" in output


# ---- idempotency ---------------------------------------------------


def test_re_run_after_commit_is_idempotent() -> None:
    """Only RAW_UPLOAD rows are reconsidered. A second --commit
    pass after the first sees zero candidates and produces no
    further updates."""
    ws = _make_workspace("idem@test.local", "Idem WS")
    a = _make_asset(ws, primitive_kind="generate_avatar_speech")

    _run("--commit")
    a.refresh_from_db()
    assert a.role == AssetRole.TALKING_HEAD

    second_output = _run("--commit")
    a.refresh_from_db()
    assert a.role == AssetRole.TALKING_HEAD
    assert "Candidates (Asset.role == RAW_UPLOAD): 0" in second_output


# ---- workspace scoping ---------------------------------------------


def test_workspace_scoping_limits_the_operation() -> None:
    ws_a = _make_workspace("scope-a@test.local", "Scope A")
    ws_b = _make_workspace("scope-b@test.local", "Scope B")
    asset_a = _make_asset(ws_a, primitive_kind="generate_avatar_speech")
    asset_b = _make_asset(ws_b, primitive_kind="generate_avatar_speech")

    _run("--commit", "--workspace", "Scope A")

    asset_a.refresh_from_db()
    asset_b.refresh_from_db()
    assert asset_a.role == AssetRole.TALKING_HEAD
    assert asset_b.role == AssetRole.RAW_UPLOAD


def test_unknown_workspace_raises_command_error() -> None:
    from django.core.management.base import CommandError

    with pytest.raises(CommandError):
        _run("--workspace", "Does Not Exist")
