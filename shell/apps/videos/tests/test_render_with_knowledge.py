"""SESSION 139 / K6 — render flow integration test.

The unit tests in ``test_script_synthesis.py`` cover
``build_render_brief`` in isolation. This file covers the
wired-through path: POST /api/videos/ → ``perform_create`` →
``build_render_brief`` → ``MediaEngineClient.create_video`` →
``poll_video_until_terminal``.

Assertions:

* ``Video.knowledge_chunk_ids`` persists the citation list on
  the row.
* The synthesized brief (not the operator's raw brief) is what
  gets handed to ``MediaEngineClient.create_video``.
* When no knowledge is visible, ``knowledge_chunk_ids`` is
  empty and the operator brief flows through unchanged.
"""
from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from django.test import override_settings
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.embeddings.ingestion import ingest_text
from apps.embeddings.tasks import embed_document
from apps.spokespeople.models import Teammate
from apps.videos.models import Video
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mocks():
    """All four mocks: embeddings, render-script synthesis,
    runway (so V6 builds composition with mock_mode=True),
    and Celery eager. ``RUNWAY_FORCE_MOCK=True`` propagates
    into the talking_head starter so the V3
    GenerateAvatarSpeechPrimitive short-circuits to
    deterministic stubs — no media-engine call needed.
    """
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        RENDER_SCRIPT_FORCE_MOCK=True,
        RUNWAY_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _setup(email: str, sp_name: str, sp_brief: str = "Brief.") -> tuple[Workspace, Teammate, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    sp = Teammate.objects.create(
        workspace=ws,
        name=sp_name,
        business_brief=sp_brief,
        # The viewset short-circuits to FAILED when there's no
        # runway_avatar_id or portrait_path (K6.2). Set fakes so
        # the render path runs.
        runway_avatar_id="fake-avatar-id-for-test",
        portrait_path="https://fake.test/portrait.png",
    )
    return ws, sp, user


def _fake_media_engine_result():
    result = MagicMock()
    result.task_id = "fake-task-id"
    result.kind = "spokesperson_ad"
    result.mock_mode = True
    return result


def _patched_client_ctx(fake_result, calls_capture):
    """Build a context manager that returns a MagicMock client whose
    create_video records its kwargs into ``calls_capture`` and
    returns ``fake_result``."""
    fake_client = MagicMock()

    def _create_video(**kwargs):
        calls_capture.append(kwargs)
        return fake_result

    fake_client.create_video.side_effect = _create_video
    cm = MagicMock()
    cm.__enter__.return_value = fake_client
    cm.__exit__.return_value = False
    return cm


def test_video_create_with_knowledge_persists_citation_ids() -> None:
    """V6: the synthesized brief lands as the talking_head
    composition's first step's ``script`` param. ``RUNWAY_FORCE_MOCK``
    makes the composition run in mock-mode so no real Runway
    call is needed — composition reaches COMPLETED and the
    sync signal flips Video.status to READY."""
    ws, sp, user = _setup("k6i_int@test", "K6 Riggs", sp_brief="Sell bicycle bells.")
    res = ingest_text(
        workspace=ws,
        title="bell-facts",
        content="Our brass bells are 110 dB. We ship same day.",
        # SESSION 276 Slice 20 — attach directly so audience = CHARACTER.
        spokespeople=[sp],
    )
    embed_document.apply(args=[str(res.document.pk)])

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/videos/",
        {
            "spokesperson": str(sp.pk),
            "brief": "Tell viewers about our bells.",
            "kind": Video.Kind.SPOKESPERSON_AD,
        },
        format="json",
    )

    assert response.status_code == http.HTTP_201_CREATED, response.content
    video_id = response.json()["id"]
    video = Video.objects.get(pk=video_id)

    # Citation persisted on the row + linked to the composition
    assert len(video.knowledge_chunk_ids) >= 1
    assert video.composition is not None
    assert video.composition.template_kind == "talking_head"
    assert list(video.composition.knowledge_chunk_ids) == list(video.knowledge_chunk_ids)

    # The brief landed as the speech step's script param
    step = video.composition.steps.first()
    assert step is not None
    assert step.primitive == "generate_avatar_speech"
    sent_script = step.params["script"]
    assert "[knowledge:" in sent_script
    assert video.knowledge_chunk_ids[0] in sent_script
    assert "Tell viewers about our bells." in sent_script

    # Composition runs mock-mode to COMPLETED → signal syncs
    # Video.status to READY.
    video.composition.refresh_from_db()
    assert video.composition.status == "completed"
    assert video.status == Video.Status.READY
    assert video.output_path  # final asset's file_path


def test_video_create_without_knowledge_has_empty_citations() -> None:
    """Contract rule 6 — graceful degradation when no knowledge
    is visible to the spokesperson."""
    _, sp, user = _setup("k6j_int@test", "Empty SP", sp_brief="A brief.")
    # No ingestion → no chunks → degraded path.

    client = APIClient()
    client.force_authenticate(user=user)

    response = client.post(
        "/api/videos/",
        {
            "spokesperson": str(sp.pk),
            "brief": "Just say hello.",
            "kind": Video.Kind.SPOKESPERSON_AD,
        },
        format="json",
    )

    assert response.status_code == http.HTTP_201_CREATED
    video = Video.objects.get(pk=response.json()["id"])
    assert video.knowledge_chunk_ids == []
    assert video.composition is not None

    # The script param is the mock-synthesis output even without
    # knowledge — "[knowledge: 0 chunks: ]" is its empty-citation
    # marker.
    step = video.composition.steps.first()
    sent_script = step.params["script"]
    assert "[knowledge: 0 chunks: ]" in sent_script
    assert "Just say hello." in sent_script

    # Composition completes in mock-mode → Video synced to READY.
    assert video.status == Video.Status.READY


def test_video_create_with_no_avatar_fails_fast_and_skips_synthesis() -> None:
    """If the spokesperson lacks an avatar, the existing pre-K6
    failure path still fires — synthesis isn't even invoked."""
    ws, _, user = _setup("k6k_int@test", "TempSp")
    # Replace the auto-created spokesperson with one that has
    # no avatar id (the path the SETUP_NEEDED enum captures).
    sp = Teammate.objects.create(
        workspace=ws, name="No Avatar", business_brief="brief.",
    )

    client = APIClient()
    client.force_authenticate(user=user)

    with patch("apps.videos.views.MediaEngineClient") as mc:
        response = client.post(
            "/api/videos/",
            {
                "spokesperson": str(sp.pk),
                "brief": "Anything.",
                "kind": Video.Kind.SPOKESPERSON_AD,
            },
            format="json",
        )

    assert response.status_code == http.HTTP_201_CREATED
    video = Video.objects.get(pk=response.json()["id"])
    assert video.status == Video.Status.FAILED
    assert "avatar" in video.error_message
    # Media-engine never called → synthesis is skipped
    mc.assert_not_called()
    assert video.knowledge_chunk_ids == []


def test_video_create_with_no_portrait_fails_fast_and_skips_synthesis() -> None:
    """K6.2 — if the spokesperson has an avatar but no portrait,
    real-mode media-engine would 400 opaquely on missing
    ``prompt_image``. Shell catches this and fails fast with a
    clear operator-facing message instead."""
    ws, _, user = _setup("k62_portrait@test", "TempSp")
    sp = Teammate.objects.create(
        workspace=ws,
        name="No Portrait",
        business_brief="brief.",
        runway_avatar_id="has-avatar-but-no-portrait",
        # portrait_path intentionally left blank.
    )

    client = APIClient()
    client.force_authenticate(user=user)

    with patch("apps.videos.views.MediaEngineClient") as mc:
        response = client.post(
            "/api/videos/",
            {
                "spokesperson": str(sp.pk),
                "brief": "Anything.",
                "kind": Video.Kind.SPOKESPERSON_AD,
            },
            format="json",
        )

    assert response.status_code == http.HTTP_201_CREATED
    video = Video.objects.get(pk=response.json()["id"])
    assert video.status == Video.Status.FAILED
    assert "portrait" in video.error_message
    mc.assert_not_called()
    assert video.knowledge_chunk_ids == []
