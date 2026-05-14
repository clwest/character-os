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
from apps.spokespeople.models import Spokesperson
from apps.videos.models import Video
from django.contrib.auth import get_user_model

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mocks():
    """All three mocks: embeddings, render-script synthesis,
    Celery eager. The media-engine call itself is patched
    per-test so we can inspect the brief argument it received."""
    with override_settings(
        EMBEDDING_FORCE_MOCK=True,
        RENDER_SCRIPT_FORCE_MOCK=True,
        CELERY_TASK_ALWAYS_EAGER=True,
        CELERY_TASK_EAGER_PROPAGATES=True,
    ):
        yield


def _setup(email: str, sp_name: str, sp_brief: str = "Brief.") -> tuple[Workspace, Spokesperson, User]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    sp = Spokesperson.objects.create(
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
    ws, sp, user = _setup("k6i_int@test", "K6 Riggs", sp_brief="Sell bicycle bells.")
    res = ingest_text(
        workspace=ws,
        title="bell-facts",
        content="Our brass bells are 110 dB. We ship same day.",
    )
    embed_document.apply(args=[str(res.document.pk)])

    calls: list[dict] = []
    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "apps.videos.views.MediaEngineClient",
        return_value=_patched_client_ctx(_fake_media_engine_result(), calls),
    ), patch(
        # Suppress the eager poll task — we're testing the create
        # path, not the polling path. The fake task id won't be
        # recognised by the media-engine poll endpoint.
        "apps.videos.views.poll_video_until_terminal.delay",
    ):
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

    # Citation persisted on the row
    assert len(video.knowledge_chunk_ids) >= 1
    # The brief that hit media-engine includes the chunk-ids
    # marker from the mock synthesis (see _mock_brief in
    # script_synthesis.py — "[knowledge: N chunks: <ids>]")
    assert len(calls) == 1
    sent_brief = calls[0]["brief"]
    assert "[knowledge:" in sent_brief
    assert video.knowledge_chunk_ids[0] in sent_brief
    # Operator's typed brief carried through too
    assert "Tell viewers about our bells." in sent_brief
    # Status flipped to rendering after the media-engine call
    assert video.status == Video.Status.RENDERING


def test_video_create_without_knowledge_has_empty_citations() -> None:
    """Contract rule 6 — graceful degradation when no knowledge
    is visible to the spokesperson."""
    _, sp, user = _setup("k6j_int@test", "Empty SP", sp_brief="A brief.")
    # No ingestion → no chunks → degraded path.

    calls: list[dict] = []
    client = APIClient()
    client.force_authenticate(user=user)

    with patch(
        "apps.videos.views.MediaEngineClient",
        return_value=_patched_client_ctx(_fake_media_engine_result(), calls),
    ), patch(
        # Suppress the eager poll task — we're testing the create
        # path, not the polling path. The fake task id won't be
        # recognised by the media-engine poll endpoint.
        "apps.videos.views.poll_video_until_terminal.delay",
    ):
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
    # The brief that hit media-engine is still the mock-shape
    # string (force-mock is on for this test); empty citation
    # block on the end.
    sent = calls[0]["brief"]
    assert "[knowledge: 0 chunks: ]" in sent
    assert "Just say hello." in sent


def test_video_create_with_no_avatar_fails_fast_and_skips_synthesis() -> None:
    """If the spokesperson lacks an avatar, the existing pre-K6
    failure path still fires — synthesis isn't even invoked."""
    ws, _, user = _setup("k6k_int@test", "TempSp")
    # Replace the auto-created spokesperson with one that has
    # no avatar id (the path the SETUP_NEEDED enum captures).
    sp = Spokesperson.objects.create(
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
    sp = Spokesperson.objects.create(
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
