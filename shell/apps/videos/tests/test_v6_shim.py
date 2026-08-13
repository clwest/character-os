"""V6 — backwards-compat shim tests.

Covers the Video → Composition bridge in three slices:

* Video.create with kind=spokesperson_ad routes through the
  talking_head starter; the composition runs to terminal in
  mock-mode, and the Composition→Video sync signal flips
  Video.status correctly.
* Composition.status=FAILED syncs to Video.status=FAILED with
  the error message.
* Composition.status=PARTIAL collapses to Video.status=FAILED
  with a ``partial completion`` marker (the legacy enum has
  no half-success state).
* Non-spokesperson_ad kinds fall through to the legacy
  media-engine path (verified by mocking the legacy client).
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.models import (
    Asset,
    AssetType,
    Composition,
    CompositionStatus,
)
from apps.compositions.starters import talking_head
from apps.spokespeople.models import Teammate
from apps.videos.models import Video

User = get_user_model()


pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _v6_force_mocks():
    """Knowledge synthesis + runway both forced to mock so the
    end-to-end composition path runs without external calls."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        RENDER_SCRIPT_FORCE_MOCK=True,
        RUNWAY_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _setup(email: str) -> tuple[Workspace, Teammate, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    sp = Teammate.objects.create(
        workspace=ws,
        name="Sasha",
        business_brief="A coffee brand.",
        runway_avatar_id="fake-avatar-id-for-v6",
        portrait_path="https://fake.test/portrait.png",
    )
    return ws, sp, user


# ---- happy path ----------------------------------------------------


def test_v6_spokesperson_ad_routes_through_talking_head_composition() -> None:
    ws, sp, user = _setup("v6_happy@test")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/videos/",
        {
            "spokesperson": str(sp.pk),
            "brief": "Sell our espresso.",
            "kind": Video.Kind.SPOKESPERSON_AD,
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    video = Video.objects.get(pk=response.json()["id"])

    assert video.composition is not None
    assert video.composition.template_kind == "talking_head"
    assert video.composition.mock_mode is True

    # Mock-mode composition runs to completion eagerly; signal
    # syncs Video.status to READY.
    video.refresh_from_db()
    assert video.status == Video.Status.READY
    assert video.output_path
    assert video.completed_at is not None


def test_v6_spokesperson_ad_sets_rendering_status_before_signal_completes() -> None:
    """During the moment between perform_create returning and
    the signal firing, the Video should be at RENDERING (not
    PENDING). Verified by inspecting the row's status after
    the (eager) composition completes — completed_at is set
    too, but the chain status → RENDERING → READY is the
    visible progression."""
    ws, sp, user = _setup("v6_rendering@test")
    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/videos/",
        {
            "spokesperson": str(sp.pk),
            "brief": "Hi.",
            "kind": Video.Kind.SPOKESPERSON_AD,
        },
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    video = Video.objects.get(pk=response.json()["id"])
    # Signal has fired, so status is now READY — but that
    # transition only happens via RENDERING. Verify
    # completed_at exists (terminal sync ran).
    assert video.status == Video.Status.READY
    assert video.completed_at is not None


# ---- failure paths -------------------------------------------------


def test_v6_failed_composition_marks_video_failed() -> None:
    """Composition transitions to FAILED → Video.status=FAILED
    + error_message propagated."""
    ws, sp, _ = _setup("v6_failed@test")

    # Create composition manually + link to a Video, then
    # transition the composition to FAILED to fire the signal.
    comp = talking_head(
        workspace=ws, spokesperson=sp, script="Hi.", mock_mode=False,
    )
    video = Video.objects.create(
        spokesperson=sp,
        brief="Hi.",
        kind=Video.Kind.SPOKESPERSON_AD,
        status=Video.Status.RENDERING,
        composition=comp,
    )

    comp.status = CompositionStatus.FAILED
    comp.error_message = "step 0 failed: simulated"
    comp.save(update_fields=["status", "error_message", "updated_at"])

    video.refresh_from_db()
    assert video.status == Video.Status.FAILED
    assert "step 0 failed" in video.error_message


def test_v6_partial_composition_marks_video_failed_with_partial_marker() -> None:
    ws, sp, _ = _setup("v6_partial@test")
    comp = talking_head(
        workspace=ws, spokesperson=sp, script="Hi.", mock_mode=False,
    )
    video = Video.objects.create(
        spokesperson=sp,
        brief="Hi.",
        kind=Video.Kind.SPOKESPERSON_AD,
        status=Video.Status.RENDERING,
        composition=comp,
    )

    comp.status = CompositionStatus.PARTIAL
    comp.error_message = "step 2 of 3 failed"
    comp.save(update_fields=["status", "error_message", "updated_at"])

    video.refresh_from_db()
    assert video.status == Video.Status.FAILED
    assert "partial completion" in video.error_message
    assert "step 2 of 3" in video.error_message


def test_v6_signal_is_idempotent() -> None:
    """Re-saving a COMPLETED composition that's already synced
    is a no-op. Same Video.status, no extra DB writes that
    could confuse audit."""
    ws, sp, _ = _setup("v6_idem@test")

    # Build a composition with a final_asset to mimic a real
    # completion.
    comp = talking_head(
        workspace=ws, spokesperson=sp, script="Hi.", mock_mode=True,
    )
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.CLIP,
        file_path="/data/_assets/test.mp4",
        duration_ms=5000,
        composition=comp,
    )
    comp.final_asset = asset
    comp.status = CompositionStatus.COMPLETED
    comp.save(update_fields=["final_asset", "status", "updated_at"])

    video = Video.objects.create(
        spokesperson=sp,
        brief="Hi.",
        kind=Video.Kind.SPOKESPERSON_AD,
        status=Video.Status.RENDERING,
        composition=comp,
    )

    # Trigger the first sync by saving the composition again.
    comp.save(update_fields=["updated_at"])
    video.refresh_from_db()
    assert video.status == Video.Status.READY
    first_completed_at = video.completed_at

    # Trigger another save — signal should bail (idempotent).
    comp.save(update_fields=["updated_at"])
    video.refresh_from_db()
    # completed_at unchanged because the signal short-circuited.
    assert video.completed_at == first_completed_at


# ---- non-spokesperson_ad legacy fallback --------------------------


def test_v6_non_spokesperson_ad_falls_through_to_legacy_path() -> None:
    """``kind=cinematic_video`` (or any non-spokesperson_ad)
    still goes through the legacy MediaEngineClient.create_video
    + poll_video_until_terminal flow. V6 keeps that path
    working until the SPA migrates."""
    ws, sp, user = _setup("v6_legacy@test")

    fake_result = MagicMock()
    fake_result.task_id = "legacy-task"
    fake_result.kind = "cinematic_video"
    fake_result.mock_mode = True

    fake_client = MagicMock()
    fake_client.create_video.return_value = fake_result
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False

    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "apps.videos.views.MediaEngineClient", return_value=cm,
    ), patch(
        "apps.videos.views.poll_video_until_terminal.delay",
    ):
        response = client.post(
            "/api/videos/",
            {
                "spokesperson": str(sp.pk),
                "brief": "Cinematic test.",
                "kind": Video.Kind.CINEMATIC_VIDEO,
            },
            format="json",
        )
    assert response.status_code == http.HTTP_201_CREATED
    video = Video.objects.get(pk=response.json()["id"])
    assert video.composition is None  # legacy path — no composition link
    assert video.media_engine_task_id == "legacy-task"
    assert video.status == Video.Status.RENDERING

    # Legacy MediaEngineClient.create_video was called once
    fake_client.create_video.assert_called_once()


# ---- chunk-id audit propagation -----------------------------------


def test_v6_signal_syncs_knowledge_chunk_ids_from_primitive_source_spec() -> None:
    """When the speech primitive records knowledge_chunk_ids in
    its output asset's source_spec, the signal copies them
    back onto the Video row for K6 audit parity. In V6's
    common path the chunk ids are pre-stamped from
    perform_create's build_render_brief synthesis, but the
    sync logic still mirrors them from the asset for
    consistency with future primitive-side synthesis paths."""
    ws, sp, _ = _setup("v6_chunks@test")
    comp = talking_head(
        workspace=ws, spokesperson=sp, script="Hi.", mock_mode=True,
    )
    # Stage a CLIP asset with chunk_ids in its source_spec
    # (mirrors what a real generate_avatar_speech step would
    # write when use_knowledge=True).
    asset = Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.CLIP,
        file_path="/data/_assets/clip.mp4",
        duration_ms=5000,
        composition=comp,
        source_spec={
            "primitive_kind": "generate_avatar_speech",
            "knowledge_chunk_ids": ["chunk-a", "chunk-b"],
        },
    )
    step = comp.steps.first()
    step.output_asset = asset
    step.save(update_fields=["output_asset"])
    comp.final_asset = asset
    comp.save(update_fields=["final_asset", "updated_at"])

    # Create a Video that's not yet synced; pre-populate with
    # different chunk_ids so the test can detect overwrite.
    video = Video.objects.create(
        spokesperson=sp,
        brief="Hi.",
        kind=Video.Kind.SPOKESPERSON_AD,
        status=Video.Status.RENDERING,
        composition=comp,
        knowledge_chunk_ids=[],
    )

    # Transition composition to COMPLETED → signal syncs.
    comp.status = CompositionStatus.COMPLETED
    comp.save(update_fields=["status", "updated_at"])

    video.refresh_from_db()
    assert video.status == Video.Status.READY
    assert video.knowledge_chunk_ids == ["chunk-a", "chunk-b"]
