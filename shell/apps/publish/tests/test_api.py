"""B14.3 — REST surface tests for the D-arc publish-bundle.

Three groups:

1. **CRUD** — create / list / retrieve / destroy.
2. **Forecast** — happy path + each blocking_reason code.
3. **Launch + retry + completion signal** — atomic fan-out;
   per-variant starter failures don't block; Celery enqueue;
   completion signal flips variants + rolls up bundle;
   retry creates new composition, flips bundle back to
   IN_FLIGHT.
"""
from __future__ import annotations

import uuid
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
    CompositionStep,
)
from apps.publish.models import PublishBundle, PublishVariant
from apps.spokespeople.models import Teammate

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _no_celery_dispatch():
    """All tests patch execute_composition.delay so no real
    broker is needed. Completion signal tests directly
    simulate the terminal-status save."""
    with patch("apps.compositions.tasks.execute_composition.delay") as p:
        yield p


def _make_user_workspace(email: str) -> tuple:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_teammate(ws: Workspace, name: str = "Marcus") -> Teammate:
    return Teammate.objects.create(
        workspace=ws, name=name, runway_avatar_id=f"av_{name.lower()}",
        portrait_path="/data/_internal/avatar_portraits/test.jpg",
        business_brief="Test.",
    )


def _make_clip(
    ws: Workspace,
    sp: Teammate | None = None,
    *,
    duration_ms: int = 30_000,
) -> Asset:
    """Create a CLIP asset. When ``sp`` is provided, also wire
    the lineage so _resolve_source_spokesperson finds it."""
    asset = Asset.objects.create(
        workspace=ws, asset_type=AssetType.CLIP,
        file_path="/data/_internal/clips/test.mp4",
        duration_ms=duration_ms,
        mime_type="video/mp4", size_bytes=1024,
    )
    if sp is not None:
        comp = Composition.objects.create(
            workspace=ws, spokesperson=sp,
            name="source", template_kind="talking_head",
            status=CompositionStatus.COMPLETED,
        )
        CompositionStep.objects.create(
            composition=comp, position=0,
            primitive="generate_avatar_speech",
            output_asset=asset,
        )
    return asset


def _create_bundle_via_api(
    client: APIClient, clip: Asset,
    platforms: list[str] | None = None,
):
    response = client.post(
        "/api/publish_bundles/",
        {
            "source_clip_id": str(clip.pk),
            "name": "Q3 launch",
            "selected_platforms": platforms or ["reels", "tiktok"],
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    return response.json()


# ---- create -----------------------------------------------------


def test_create_persists_draft_with_one_variant_per_platform() -> None:
    user, ws = _make_user_workspace("b143c@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)

    data = _create_bundle_via_api(client, clip, ["reels", "tiktok", "linkedin"])
    assert data["status"] == "draft"
    assert data["source_clip_id"] == str(clip.pk)
    assert data["selected_platforms"] == ["reels", "tiktok", "linkedin"]
    assert data["variant_counts"]["total"] == 3
    assert data["variant_counts"]["pending"] == 3

    # Variants snapshotted catalog values.
    bundle = PublishBundle.objects.get(pk=data["id"])
    variants = {v.platform_key: v for v in bundle.variants.all()}
    assert variants["reels"].target_ratio == "720:1280"
    assert variants["reels"].max_duration_ms == 60_000
    assert variants["tiktok"].max_duration_ms == 90_000
    assert variants["linkedin"].target_ratio == "1280:720"


def test_create_unknown_platform_returns_400() -> None:
    user, ws = _make_user_workspace("b143unkplat@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/publish_bundles/",
        {
            "source_clip_id": str(clip.pk),
            "name": "x",
            "selected_platforms": ["reels", "pinterest"],
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST
    assert "pinterest" in str(response.content).lower()


def test_create_duplicate_platforms_returns_400() -> None:
    user, ws = _make_user_workspace("b143dup@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/publish_bundles/",
        {
            "source_clip_id": str(clip.pk),
            "name": "x",
            "selected_platforms": ["reels", "reels"],
        },
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_create_non_clip_source_returns_404() -> None:
    user, ws = _make_user_workspace("b143nonclip@test")
    audio = Asset.objects.create(
        workspace=ws, asset_type=AssetType.AUDIO,
        file_path="/data/test.mp3", mime_type="audio/mpeg",
        size_bytes=1024,
    )
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/publish_bundles/",
        {
            "source_clip_id": str(audio.pk),
            "name": "x",
            "selected_platforms": ["reels"],
        },
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_create_cross_workspace_clip_returns_404() -> None:
    user_a, _ = _make_user_workspace("b143cwa@test")
    _, ws_b = _make_user_workspace("b143cwb@test")
    sp_b = _make_teammate(ws_b)
    clip_b = _make_clip(ws_b, sp_b)
    client = APIClient()
    _login(client, user_a)

    response = client.post(
        "/api/publish_bundles/",
        {
            "source_clip_id": str(clip_b.pk),
            "name": "x",
            "selected_platforms": ["reels"],
        },
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_create_unauth_returns_401_or_403() -> None:
    response = APIClient().post(
        "/api/publish_bundles/", {}, format="json",
    )
    assert response.status_code in (
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    )


# ---- list / retrieve / destroy --------------------------------


def test_list_only_returns_user_workspace_bundles() -> None:
    user_a, ws_a = _make_user_workspace("b143la@test")
    user_b, ws_b = _make_user_workspace("b143lb@test")
    sp_a = _make_teammate(ws_a)
    sp_b = _make_teammate(ws_b)
    clip_a = _make_clip(ws_a, sp_a)
    clip_b = _make_clip(ws_b, sp_b)

    client = APIClient()
    _login(client, user_a)
    _create_bundle_via_api(client, clip_a)
    _login(client, user_b)
    _create_bundle_via_api(client, clip_b)

    _login(client, user_a)
    response = client.get("/api/publish_bundles/")
    rows = response.json()
    assert all(r["workspace_id"] == str(ws_a.pk) for r in rows)


def test_retrieve_cross_workspace_returns_404() -> None:
    user_a, _ = _make_user_workspace("b143ra@test")
    user_b, ws_b = _make_user_workspace("b143rb@test")
    sp_b = _make_teammate(ws_b)
    clip_b = _make_clip(ws_b, sp_b)
    client = APIClient()
    _login(client, user_b)
    data = _create_bundle_via_api(client, clip_b)

    _login(client, user_a)
    response = client.get(f"/api/publish_bundles/{data['id']}/")
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_destroy_draft_succeeds() -> None:
    user, ws = _make_user_workspace("b143del@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip)

    response = client.delete(f"/api/publish_bundles/{data['id']}/")
    assert response.status_code == http.HTTP_204_NO_CONTENT
    assert PublishBundle.objects.filter(pk=data["id"]).count() == 0


def test_destroy_in_flight_returns_409() -> None:
    user, ws = _make_user_workspace("b143delfly@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip)

    bundle = PublishBundle.objects.get(pk=data["id"])
    bundle.status = PublishBundle.Status.IN_FLIGHT
    bundle.save(update_fields=["status"])

    response = client.delete(f"/api/publish_bundles/{data['id']}/")
    assert response.status_code == http.HTTP_409_CONFLICT


# ---- forecast --------------------------------------------------


def test_forecast_happy_path() -> None:
    user, ws = _make_user_workspace("b143fc@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip, ["reels", "tiktok", "linkedin"])

    response = client.get(f"/api/publish_bundles/{data['id']}/forecast/")
    body = response.json()
    assert body["variant_count"] == 3
    assert body["projected_cost_micros"] == 0  # rule 5
    assert body["estimated_wall_time_s"] == 15  # 3 × 5s
    assert body["ready_to_launch"] is True
    assert body["blocking_reason"] is None


def test_forecast_non_draft_blocks() -> None:
    user, ws = _make_user_workspace("b143fcnd@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip)
    bundle = PublishBundle.objects.get(pk=data["id"])
    bundle.status = PublishBundle.Status.IN_FLIGHT
    bundle.save(update_fields=["status"])

    response = client.get(f"/api/publish_bundles/{data['id']}/forecast/")
    body = response.json()
    assert body["ready_to_launch"] is False
    assert body["blocking_reason"]["code"] == "bundle_not_draft"


def test_forecast_no_variants_blocks() -> None:
    user, ws = _make_user_workspace("b143fcnov@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip)
    # Delete the variants to simulate a no-variants state.
    PublishBundle.objects.get(pk=data["id"]).variants.all().delete()

    response = client.get(f"/api/publish_bundles/{data['id']}/forecast/")
    body = response.json()
    assert body["ready_to_launch"] is False
    assert body["blocking_reason"]["code"] == "no_variants"


# ---- launch ----------------------------------------------------


def test_launch_happy_path_creates_compositions_and_enqueues(
    _no_celery_dispatch,
) -> None:
    user, ws = _make_user_workspace("b143lh@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp, duration_ms=30_000)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip, ["reels", "tiktok"])

    response = client.post(f"/api/publish_bundles/{data['id']}/launch/")
    assert response.status_code == http.HTTP_200_OK, response.content
    body = response.json()
    assert body["queued_count"] == 2
    assert body["failed_at_start_count"] == 0
    assert body["bundle"]["status"] == "in_flight"

    bundle = PublishBundle.objects.get(pk=data["id"])
    assert bundle.launched_at is not None
    variants = list(bundle.variants.order_by("platform_key"))
    assert all(v.status == PublishVariant.Status.QUEUED for v in variants)
    assert all(v.produced_composition_id is not None for v in variants)
    # Composition uses publish_variant template_kind (so it
    # doesn't count against videos_per_month).
    for v in variants:
        assert v.produced_composition.template_kind == "publish_variant"

    # Celery enqueued once per variant.
    assert _no_celery_dispatch.call_count == 2


def test_launch_composition_name_carries_provenance(
    _no_celery_dispatch,
) -> None:
    """Rule 8 — composition.name = `{bundle.name} — {display}`."""
    user, ws = _make_user_workspace("b143name@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip, ["reels", "tiktok"])

    client.post(f"/api/publish_bundles/{data['id']}/launch/")
    bundle = PublishBundle.objects.get(pk=data["id"])
    names = sorted(v.produced_composition.name for v in bundle.variants.all())
    assert any("Instagram Reels" in n for n in names)
    assert any("TikTok" in n for n in names)
    assert all(n.startswith("Q3 launch — ") for n in names)


def test_launch_non_draft_returns_409(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b143lhnd@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip)
    bundle = PublishBundle.objects.get(pk=data["id"])
    bundle.status = PublishBundle.Status.IN_FLIGHT
    bundle.save(update_fields=["status"])

    response = client.post(f"/api/publish_bundles/{data['id']}/launch/")
    assert response.status_code == http.HTTP_409_CONFLICT
    _no_celery_dispatch.assert_not_called()


def test_launch_cross_workspace_returns_404(_no_celery_dispatch) -> None:
    user_a, _ = _make_user_workspace("b143lha@test")
    user_b, ws_b = _make_user_workspace("b143lhb@test")
    sp_b = _make_teammate(ws_b)
    clip_b = _make_clip(ws_b, sp_b)
    client = APIClient()
    _login(client, user_b)
    data = _create_bundle_via_api(client, clip_b)
    _login(client, user_a)
    response = client.post(f"/api/publish_bundles/{data['id']}/launch/")
    assert response.status_code == http.HTTP_404_NOT_FOUND
    _no_celery_dispatch.assert_not_called()


# ---- completion signal -----------------------------------------


def test_composition_completed_flips_variant_and_rolls_up_bundle(
    _no_celery_dispatch,
) -> None:
    """End-to-end signal validation: 2 variants → both
    compositions reach COMPLETED → both variants flip →
    bundle rolls up to COMPLETED."""
    user, ws = _make_user_workspace("b143sig@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip, ["reels", "tiktok"])
    client.post(f"/api/publish_bundles/{data['id']}/launch/")

    bundle = PublishBundle.objects.get(pk=data["id"])
    for v in bundle.variants.all():
        v.produced_composition.status = CompositionStatus.COMPLETED
        v.produced_composition.save(update_fields=["status"])

    bundle.refresh_from_db()
    assert bundle.status == PublishBundle.Status.COMPLETED
    assert bundle.completed_at is not None
    for v in bundle.variants.all():
        assert v.status == PublishVariant.Status.COMPLETED


def test_composition_failed_flips_to_partial_when_some_succeed(
    _no_celery_dispatch,
) -> None:
    user, ws = _make_user_workspace("b143sigp@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip, ["reels", "tiktok"])
    client.post(f"/api/publish_bundles/{data['id']}/launch/")

    bundle = PublishBundle.objects.get(pk=data["id"])
    variants = list(bundle.variants.order_by("platform_key"))
    # reels succeeds, tiktok fails
    variants[0].produced_composition.status = CompositionStatus.COMPLETED
    variants[0].produced_composition.save(update_fields=["status"])
    variants[1].produced_composition.status = CompositionStatus.FAILED
    variants[1].produced_composition.error_message = "Runway 500"
    variants[1].produced_composition.save(update_fields=["status", "error_message"])

    bundle.refresh_from_db()
    assert bundle.status == PublishBundle.Status.PARTIAL
    variants[1].refresh_from_db()
    assert variants[1].status == PublishVariant.Status.FAILED
    assert "Runway 500" in variants[1].error_message


# ---- retry_variant ---------------------------------------------


def test_retry_failed_variant_creates_new_composition(
    _no_celery_dispatch,
) -> None:
    user, ws = _make_user_workspace("b143retry@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip, ["reels"])
    client.post(f"/api/publish_bundles/{data['id']}/launch/")

    bundle = PublishBundle.objects.get(pk=data["id"])
    variant = bundle.variants.first()
    failed_comp = variant.produced_composition
    failed_comp.status = CompositionStatus.FAILED
    failed_comp.save(update_fields=["status"])
    variant.refresh_from_db()
    bundle.refresh_from_db()
    assert variant.status == PublishVariant.Status.FAILED
    assert bundle.status == PublishBundle.Status.FAILED

    _no_celery_dispatch.reset_mock()
    response = client.post(
        f"/api/publish_bundles/{bundle.pk}/retry_variant/",
        {"variant_id": str(variant.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK, response.content

    variant.refresh_from_db()
    bundle.refresh_from_db()
    assert variant.status == PublishVariant.Status.QUEUED
    assert variant.produced_composition_id != failed_comp.pk
    # Failed composition stays for audit.
    assert Composition.objects.filter(pk=failed_comp.pk).exists()
    # Bundle flipped back to IN_FLIGHT from terminal.
    assert bundle.status == PublishBundle.Status.IN_FLIGHT
    assert bundle.completed_at is None
    _no_celery_dispatch.assert_called_once()


def test_retry_non_failed_variant_returns_400(
    _no_celery_dispatch,
) -> None:
    user, ws = _make_user_workspace("b143nofail@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip)
    bundle = PublishBundle.objects.get(pk=data["id"])
    variant = bundle.variants.first()
    # PENDING — not retryable.
    response = client.post(
        f"/api/publish_bundles/{bundle.pk}/retry_variant/",
        {"variant_id": str(variant.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_retry_missing_variant_id_returns_400(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b143noid@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip)
    response = client.post(
        f"/api/publish_bundles/{data['id']}/retry_variant/",
        {},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_retry_unknown_variant_returns_404(_no_celery_dispatch) -> None:
    user, ws = _make_user_workspace("b143unkv@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip)
    response = client.post(
        f"/api/publish_bundles/{data['id']}/retry_variant/",
        {"variant_id": str(uuid.uuid4())},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


# ---- variants sub-list -----------------------------------------


def test_variants_sub_list_returns_platform_ordered() -> None:
    user, ws = _make_user_workspace("b143subl@test")
    sp = _make_teammate(ws)
    clip = _make_clip(ws, sp)
    client = APIClient()
    _login(client, user)
    data = _create_bundle_via_api(client, clip, ["tiktok", "reels", "linkedin"])

    response = client.get(f"/api/publish_bundles/{data['id']}/variants/")
    rows = response.json()
    assert len(rows) == 3
    # Ordered by platform_key alphabetically.
    assert [r["platform_key"] for r in rows] == ["linkedin", "reels", "tiktok"]
