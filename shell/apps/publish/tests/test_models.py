"""B14.2 — PublishBundle + PublishVariant model tests.

Seven concerns:

1. Happy-path saves with realistic FK shape.
2. Status enum coverage matches scope-lock state machines.
3. source_clip MUST be asset_type=CLIP.
4. Cross-workspace source_clip rejected (clean + signal).
5. Cross-workspace produced_composition rejected.
6. UniqueConstraint: one variant per (bundle, platform_key).
7. recipient.workspace property surfaces bundle.workspace.
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db.utils import IntegrityError

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType, Composition
from apps.publish.models import PublishBundle, PublishVariant
from apps.spokespeople.models import Spokesperson

User = get_user_model()

pytestmark = pytest.mark.django_db


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _make_spokesperson(ws: Workspace, name: str = "Marcus") -> Spokesperson:
    return Spokesperson.objects.create(
        workspace=ws, name=name, runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test.",
    )


def _make_clip(
    ws: Workspace, *, duration_ms: int = 30_000,
) -> Asset:
    return Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/_internal/clips/test.mp4",
        duration_ms=duration_ms,
        mime_type="video/mp4", size_bytes=1024,
    )


def _make_composition(ws: Workspace, sp: Spokesperson) -> Composition:
    return Composition.objects.create(
        workspace=ws, spokesperson=sp,
        name="test comp", template_kind="publish_variant",
    )


# ---- happy path -------------------------------------------------


def test_bundle_persists_with_realistic_fields() -> None:
    _, ws = _make_user_workspace("b142hp@test")
    clip = _make_clip(ws)
    b = PublishBundle.objects.create(
        workspace=ws,
        source_clip=clip,
        name="Q3 launch",
        selected_platforms=["reels", "shorts", "tiktok"],
    )
    assert b.id is not None
    assert b.status == PublishBundle.Status.DRAFT
    assert b.launched_at is None
    assert b.completed_at is None
    assert b.selected_platforms == ["reels", "shorts", "tiktok"]


def test_variant_persists_with_snapshotted_platform_params() -> None:
    _, ws = _make_user_workspace("b142vhp@test")
    clip = _make_clip(ws)
    b = PublishBundle.objects.create(
        workspace=ws, source_clip=clip, name="x",
        selected_platforms=["reels"],
    )
    v = PublishVariant.objects.create(
        bundle=b,
        platform_key="reels",
        target_ratio="720:1280",
        max_duration_ms=60_000,
    )
    assert v.id is not None
    assert v.status == PublishVariant.Status.PENDING
    assert v.workspace == ws  # property surface
    assert v.produced_composition is None
    assert v.target_ratio == "720:1280"
    assert v.max_duration_ms == 60_000


# ---- enum coverage ---------------------------------------------


def test_bundle_status_enum_matches_scope_lock() -> None:
    """v1 ships exactly six bundle statuses per the state
    machine in PUBLISH_BUNDLE_V1.md."""
    expected = {
        "draft", "launching", "in_flight",
        "completed", "partial", "failed",
    }
    actual = {choice for choice, _ in PublishBundle.Status.choices}
    assert actual == expected


def test_variant_status_enum_matches_scope_lock() -> None:
    """v1 ships exactly five variant statuses."""
    expected = {"pending", "queued", "running", "completed", "failed"}
    actual = {choice for choice, _ in PublishVariant.Status.choices}
    assert actual == expected


# ---- source_clip type validation -------------------------------


def test_non_clip_source_rejected_at_clean() -> None:
    _, ws = _make_user_workspace("b142type@test")
    audio = Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/test.mp3",
        mime_type="audio/mpeg", size_bytes=1024,
    )
    b = PublishBundle(
        workspace=ws, source_clip=audio,
        name="x", selected_platforms=["reels"],
    )
    with pytest.raises(ValidationError) as exc:
        b.full_clean()
    assert "CLIP" in str(exc.value)


# ---- workspace isolation ---------------------------------------


def test_cross_workspace_source_clip_rejected_at_clean() -> None:
    _, ws_a = _make_user_workspace("b142iso_a@test")
    _, ws_b = _make_user_workspace("b142iso_b@test")
    clip_b = _make_clip(ws_b)

    b = PublishBundle(
        workspace=ws_a, source_clip=clip_b,
        name="x", selected_platforms=["reels"],
    )
    with pytest.raises(ValidationError) as exc:
        b.full_clean()
    assert "different workspace" in str(exc.value)


def test_cross_workspace_source_clip_rejected_at_signal() -> None:
    """The pre_save signal catches the raw .save() path that
    skips clean()."""
    _, ws_a = _make_user_workspace("b142sig_a@test")
    _, ws_b = _make_user_workspace("b142sig_b@test")
    clip_b = _make_clip(ws_b)

    b = PublishBundle(
        workspace=ws_a, source_clip=clip_b,
        name="x", selected_platforms=["reels"],
    )
    with pytest.raises(ValidationError):
        b.save()


def test_same_workspace_save_succeeds() -> None:
    _, ws = _make_user_workspace("b142ok@test")
    clip = _make_clip(ws)
    b = PublishBundle(
        workspace=ws, source_clip=clip,
        name="x", selected_platforms=["reels"],
    )
    b.full_clean()
    b.save()
    assert b.pk is not None


def test_cross_workspace_produced_composition_on_variant_rejected() -> None:
    _, ws_a = _make_user_workspace("b142vca@test")
    _, ws_b = _make_user_workspace("b142vcb@test")
    sp_a = _make_spokesperson(ws_a, name="A")
    sp_b = _make_spokesperson(ws_b, name="B")
    clip_a = _make_clip(ws_a)

    bundle_a = PublishBundle.objects.create(
        workspace=ws_a, source_clip=clip_a,
        name="x", selected_platforms=["reels"],
    )
    comp_b = _make_composition(ws_b, sp_b)

    v = PublishVariant(
        bundle=bundle_a,
        platform_key="reels",
        target_ratio="720:1280", max_duration_ms=60_000,
        status=PublishVariant.Status.QUEUED,
        produced_composition=comp_b,
    )
    with pytest.raises(ValidationError) as exc:
        v.full_clean()
    assert "different workspace" in str(exc.value)


def test_variant_workspace_property_resolves_to_bundle_workspace() -> None:
    """The .workspace property is what
    character_os.permissions._workspace_of() reads to enforce
    IsWorkspaceMember on detail routes."""
    _, ws = _make_user_workspace("b142wsprop@test")
    clip = _make_clip(ws)
    b = PublishBundle.objects.create(
        workspace=ws, source_clip=clip,
        name="x", selected_platforms=["reels"],
    )
    v = PublishVariant.objects.create(
        bundle=b, platform_key="reels",
        target_ratio="720:1280", max_duration_ms=60_000,
    )
    assert v.workspace == ws


# ---- uniqueness constraint -------------------------------------


def test_one_variant_per_platform_per_bundle() -> None:
    """UniqueConstraint prevents two TikTok variants in the
    same bundle. Operator can't accidentally double up."""
    _, ws = _make_user_workspace("b142unique@test")
    clip = _make_clip(ws)
    b = PublishBundle.objects.create(
        workspace=ws, source_clip=clip,
        name="x", selected_platforms=["tiktok"],
    )
    PublishVariant.objects.create(
        bundle=b, platform_key="tiktok",
        target_ratio="720:1280", max_duration_ms=90_000,
    )
    with pytest.raises(IntegrityError):
        PublishVariant.objects.create(
            bundle=b, platform_key="tiktok",
            target_ratio="720:1280", max_duration_ms=90_000,
        )


def test_same_platform_in_different_bundles_is_fine() -> None:
    """Uniqueness is per-bundle; two different bundles can
    each have a reels variant."""
    _, ws = _make_user_workspace("b142twobundles@test")
    clip = _make_clip(ws)
    b1 = PublishBundle.objects.create(
        workspace=ws, source_clip=clip,
        name="b1", selected_platforms=["reels"],
    )
    b2 = PublishBundle.objects.create(
        workspace=ws, source_clip=clip,
        name="b2", selected_platforms=["reels"],
    )
    PublishVariant.objects.create(
        bundle=b1, platform_key="reels",
        target_ratio="720:1280", max_duration_ms=60_000,
    )
    PublishVariant.objects.create(
        bundle=b2, platform_key="reels",
        target_ratio="720:1280", max_duration_ms=60_000,
    )
    # No raise.
