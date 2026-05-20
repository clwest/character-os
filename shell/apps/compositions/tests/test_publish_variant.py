"""D-arc / B14.1 (SESSION 205) — platform catalog + publish_variant starter.

Three test groups:

1. **Platform catalog** — closed enum shape (rule 7). Validates
   the five v1 keys, their target_ratio + max_duration_ms,
   the MAX_PLATFORMS_PER_BUNDLE cap, and the
   PUBLISH_VARIANT_TEMPLATE_KIND constant the cap-exclusion
   reads.
2. **publish_variant starter** — 2-step composition shape;
   duration trim window math; input-validation guards
   (non-CLIP, missing duration_ms, wrong workspace).
3. **Cap exclusion** — get_usage() does NOT count
   publish_variant compositions toward videos_per_month
   (rule 5 + Q-d-4).
"""
from __future__ import annotations

import pytest
from django.contrib.auth import get_user_model

from apps.accounts.models import Workspace
from apps.billing.services import get_usage
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
)
from apps.compositions.platform_catalog import (
    MAX_PLATFORMS_PER_BUNDLE,
    PUBLISH_VARIANT_TEMPLATE_KIND,
    all_platform_keys,
    all_platforms,
    get_platform,
)
from apps.compositions.starters import publish_variant
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
    ws: Workspace, *, duration_ms: int | None = 30_000,
) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.CLIP,
        file_path="/data/_internal/clips/test.mp4",
        duration_ms=duration_ms,
        mime_type="video/mp4",
        size_bytes=1024,
    )


# ---- platform catalog ------------------------------------------


def test_catalog_has_five_v1_platforms() -> None:
    """Q-d-1 lock — Reels / Shorts / TikTok / X / LinkedIn."""
    keys = all_platform_keys()
    assert set(keys) == {"reels", "shorts", "tiktok", "x_twitter", "linkedin"}
    assert len(keys) == 5


def test_catalog_target_ratios_match_reformat_clip_supported() -> None:
    """Every catalog target_ratio must be one of the three
    ratios the existing reformat_clip primitive supports
    (1280:720 / 720:1280 / 960:960). Rule 4."""
    supported = {"1280:720", "720:1280", "960:960"}
    for platform in all_platforms():
        assert platform.target_ratio in supported


def test_catalog_duration_caps_match_v1_lock() -> None:
    """The exact numbers locked at B14.0:
    Reels 60s, Shorts 60s, TikTok 90s, X 140s, LinkedIn 30s."""
    assert get_platform("reels").max_duration_ms == 60_000
    assert get_platform("shorts").max_duration_ms == 60_000
    assert get_platform("tiktok").max_duration_ms == 90_000
    assert get_platform("x_twitter").max_duration_ms == 140_000
    assert get_platform("linkedin").max_duration_ms == 30_000


def test_catalog_linkedin_default_ratio_is_landscape() -> None:
    """Q-d-2 lock — LinkedIn v1 ships 1280:720 (16:9)."""
    assert get_platform("linkedin").target_ratio == "1280:720"


def test_catalog_unknown_key_raises_keyerror() -> None:
    with pytest.raises(KeyError) as exc:
        get_platform("pinterest")
    # Helpful message lists valid keys.
    assert "pinterest" in str(exc.value)
    assert "reels" in str(exc.value)


def test_catalog_max_platforms_per_bundle_is_ten() -> None:
    """Q-d-7 lock — hard cap 10 (catalog size 5 today; defense
    in depth)."""
    assert MAX_PLATFORMS_PER_BUNDLE == 10


def test_catalog_template_kind_constant_is_publish_variant() -> None:
    """The constant the cap exclusion reads. If this drifts,
    apps.billing.services.get_usage() needs to follow."""
    assert PUBLISH_VARIANT_TEMPLATE_KIND == "publish_variant"


# ---- publish_variant starter ------------------------------------


def test_publish_variant_creates_two_step_composition() -> None:
    """Trim (step 0) → reformat (step 1). Always 2 steps for
    state-machine simplicity."""
    _, ws = _make_user_workspace("b141ok@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws, duration_ms=90_000)

    comp = publish_variant(
        workspace=ws, spokesperson=sp, source_clip=clip,
        target_ratio="720:1280", max_duration_ms=60_000,
    )

    assert comp.template_kind == PUBLISH_VARIANT_TEMPLATE_KIND
    assert comp.steps.count() == 2
    steps = list(comp.steps.order_by("position"))
    assert steps[0].primitive == "trim_clip"
    assert steps[1].primitive == "reformat_clip"


def test_publish_variant_caps_trim_at_source_duration() -> None:
    """Short source (5s) on a 60s platform → end_ms = 5000,
    not 60000. ffmpeg's `-to` would silently stop at EOF
    anyway, but the audit row should carry the accurate
    offset."""
    _, ws = _make_user_workspace("b141short@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws, duration_ms=5_000)

    comp = publish_variant(
        workspace=ws, spokesperson=sp, source_clip=clip,
        target_ratio="720:1280", max_duration_ms=60_000,
    )
    trim = comp.steps.get(position=0)
    assert trim.params["start_ms"] == 0
    assert trim.params["end_ms"] == 5_000


def test_publish_variant_caps_trim_at_platform_max() -> None:
    """Long source (90s) on a 60s platform → end_ms = 60000."""
    _, ws = _make_user_workspace("b141long@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws, duration_ms=90_000)

    comp = publish_variant(
        workspace=ws, spokesperson=sp, source_clip=clip,
        target_ratio="720:1280", max_duration_ms=60_000,
    )
    trim = comp.steps.get(position=0)
    assert trim.params["end_ms"] == 60_000


def test_publish_variant_step1_uses_target_ratio() -> None:
    _, ws = _make_user_workspace("b141ratio@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws)

    comp = publish_variant(
        workspace=ws, spokesperson=sp, source_clip=clip,
        target_ratio="1280:720", max_duration_ms=140_000,
    )
    reformat = comp.steps.get(position=1)
    assert reformat.params["target_ratio"] == "1280:720"
    # Step 1 consumes step 0's output.
    assert reformat.inputs == [
        {"slot": "base", "from_step_position": 0},
    ]


def test_publish_variant_step0_consumes_source_asset() -> None:
    _, ws = _make_user_workspace("b141src@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws)

    comp = publish_variant(
        workspace=ws, spokesperson=sp, source_clip=clip,
        target_ratio="720:1280", max_duration_ms=60_000,
    )
    trim = comp.steps.get(position=0)
    assert trim.inputs == [
        {"slot": "base", "asset_id": str(clip.id)},
    ]


def test_publish_variant_rejects_non_clip_source() -> None:
    _, ws = _make_user_workspace("b141srctype@test")
    sp = _make_spokesperson(ws)
    audio = Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/test.mp3", mime_type="audio/mpeg",
        size_bytes=1024,
    )
    with pytest.raises(ValueError) as exc:
        publish_variant(
            workspace=ws, spokesperson=sp, source_clip=audio,
            target_ratio="720:1280", max_duration_ms=60_000,
        )
    assert "CLIP" in str(exc.value)


def test_publish_variant_rejects_clip_without_duration() -> None:
    _, ws = _make_user_workspace("b141nodur@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws, duration_ms=None)
    with pytest.raises(ValueError) as exc:
        publish_variant(
            workspace=ws, spokesperson=sp, source_clip=clip,
            target_ratio="720:1280", max_duration_ms=60_000,
        )
    assert "duration_ms" in str(exc.value)


def test_publish_variant_rejects_cross_workspace_spokesperson() -> None:
    _, ws_a = _make_user_workspace("b141cwa@test")
    _, ws_b = _make_user_workspace("b141cwb@test")
    sp_b = _make_spokesperson(ws_b)  # in workspace B
    clip_a = _make_clip(ws_a)  # in workspace A
    with pytest.raises(ValueError) as exc:
        publish_variant(
            workspace=ws_a, spokesperson=sp_b, source_clip=clip_a,
            target_ratio="720:1280", max_duration_ms=60_000,
        )
    assert "workspace" in str(exc.value).lower()


def test_publish_variant_rejects_zero_max_duration() -> None:
    _, ws = _make_user_workspace("b141zerodur@test")
    sp = _make_spokesperson(ws)
    clip = _make_clip(ws)
    with pytest.raises(ValueError) as exc:
        publish_variant(
            workspace=ws, spokesperson=sp, source_clip=clip,
            target_ratio="720:1280", max_duration_ms=0,
        )
    assert "positive" in str(exc.value).lower()


# ---- cap exclusion (rule 5 + Q-d-4) -----------------------------


def test_get_usage_excludes_publish_variant_compositions() -> None:
    """Rule 5 — variants are ffmpeg-only packaging derivatives;
    the source's Composition already counted at render time.
    Mixing 2 publish_variant + 3 talking_head_polished should
    yield videos_used=3."""
    _, ws = _make_user_workspace("b141cap@test")
    sp = _make_spokesperson(ws)

    # 3 "source render" compositions that count.
    for _ in range(3):
        Composition.objects.create(
            workspace=ws, spokesperson=sp, name="source",
            template_kind="talking_head_polished",
            status=CompositionStatus.COMPLETED,
        )
    # 2 publish_variant compositions that should NOT count.
    for _ in range(2):
        Composition.objects.create(
            workspace=ws, spokesperson=sp, name="variant",
            template_kind=PUBLISH_VARIANT_TEMPLATE_KIND,
            status=CompositionStatus.COMPLETED,
        )

    usage = get_usage(ws)
    assert usage.videos_used == 3


def test_get_usage_excludes_publish_variant_even_when_failed() -> None:
    """Variants in any non-DRAFT terminal state stay excluded
    — failed packaging attempts are still ffmpeg-only,
    operator-level monthly usage shouldn't dock for them."""
    _, ws = _make_user_workspace("b141capfailed@test")
    sp = _make_spokesperson(ws)
    Composition.objects.create(
        workspace=ws, spokesperson=sp, name="failed variant",
        template_kind=PUBLISH_VARIANT_TEMPLATE_KIND,
        status=CompositionStatus.FAILED,
    )
    assert get_usage(ws).videos_used == 0
