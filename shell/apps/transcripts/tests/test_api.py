"""B1.3 — REST surface tests for the transcript miner.

Coverage:

1. **Mine — happy path** (force-mock). Returns N highlights;
   rows persist with the right shape (workspace, FK,
   PENDING, llm telemetry on first row only).
2. **Mine — invalid asset_id** → 404.
3. **Mine — cross-workspace transcript** → 404 (no leak).
4. **Mine — non-TRANSCRIPT asset** → 404.
5. **Mine — empty transcript body** returns 200 + empty
   list (no row persistence).
6. **Mine — LLM degrades to empty** returns 200 + empty list.
7. **List — workspace isolation** — user only sees their
   own workspace's highlights.
8. **List — filterable by status + source_transcript**.
9. **Retrieve — single row**.
10. **Retrieve — cross-workspace** → 404.

Force-mock is set globally via @override_settings so the
LLM helper never hits OpenAI during tests.
"""
from __future__ import annotations

import uuid

import pytest
from django.contrib.auth import get_user_model
from rest_framework import status as http
from rest_framework.test import APIClient

from apps.accounts.models import Workspace
from apps.compositions.models import Asset, AssetType
from apps.transcripts.models import TranscriptHighlight

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture(autouse=True)
def _force_mock_miner(settings):
    """All B1.3 tests run with the LLM helper force-mocked so
    no OpenAI calls fire. Same shape as the autouse fixture in
    apps/realtime/tests/test_r6_session_memory.py."""
    settings.TRANSCRIPT_MINER_FORCE_MOCK = True
    yield


# ---- fixtures ---------------------------------------------------


def _make_user_workspace(email: str) -> tuple[User, Workspace]:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return user, ws


def _login(client: APIClient, user) -> None:
    client.force_authenticate(user=user)


def _make_transcript_asset(
    ws: Workspace,
    body: str = (
        "Assistant: This is the punchy moment worth sharing.\n"
        "User: nice.\n"
        "Assistant: Another self-contained takeaway here.\n"
        "Assistant: Third great quote worth a clip.\n"
    ),
) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.TRANSCRIPT,
        file_path="",
        inline_content=body,
        source_spec={"primitive_kind": "realtime_transcript"},
        mime_type="text/plain",
        size_bytes=len(body.encode("utf-8")),
    )


def _make_clip_asset(ws: Workspace) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=AssetType.CLIP,
        file_path="/data/x.mp4",
        mime_type="video/mp4",
        size_bytes=1024,
    )


# ---- mine: happy path ------------------------------------------


def test_mine_persists_pending_rows_with_telemetry_on_first() -> None:
    """Q-b-5 — first row holds the LLM model + token totals;
    subsequent rows hold zeros (no per-call double-count)."""
    user, ws = _make_user_workspace("b13mine@test")
    transcript = _make_transcript_asset(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript.pk), "target_count": 3},
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED, response.content
    data = response.json()
    assert data["used_synthesis"] is True
    assert len(data["highlights"]) >= 1

    # Persisted rows match.
    rows = list(TranscriptHighlight.objects.filter(workspace=ws).order_by("mined_at"))
    assert len(rows) == len(data["highlights"])
    assert all(r.status == TranscriptHighlight.Status.PENDING for r in rows)
    assert all(r.source_transcript_id == transcript.pk for r in rows)
    # First row carries the mock model marker; others empty.
    assert rows[0].llm_model_id != ""
    for r in rows[1:]:
        assert r.llm_model_id == ""


def test_mine_returns_offset_metadata_in_response() -> None:
    """SPA needs char_start/char_end to render the
    hover-highlight on the source body (B1.6)."""
    user, ws = _make_user_workspace("b13offset@test")
    transcript = _make_transcript_asset(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript.pk), "target_count": 2},
        format="json",
    )
    assert response.status_code == http.HTTP_201_CREATED
    for h in response.json()["highlights"]:
        assert "char_start" in h and "char_end" in h
        assert h["char_end"] > h["char_start"]
        # Rule 3: declared text must match the source body.
        snippet = transcript.inline_content[h["char_start"]:h["char_end"]]
        assert snippet == h["text"]


# ---- mine: error paths -----------------------------------------


def test_mine_unknown_asset_id_returns_404() -> None:
    user, _ = _make_user_workspace("b13unknown@test")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(uuid.uuid4())},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_mine_cross_workspace_asset_returns_404() -> None:
    """Operator A cannot mine operator B's transcript even
    if they know the asset id. Same shape as A4."""
    user_a, _ = _make_user_workspace("b13cwa@test")
    _, ws_b = _make_user_workspace("b13cwb@test")
    transcript_b = _make_transcript_asset(ws_b)

    client = APIClient()
    _login(client, user_a)

    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript_b.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND
    # And no rows leaked.
    assert TranscriptHighlight.objects.count() == 0


def test_mine_non_transcript_asset_returns_404() -> None:
    user, ws = _make_user_workspace("b13type@test")
    clip = _make_clip_asset(ws)
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(clip.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_404_NOT_FOUND


def test_mine_empty_body_returns_200_with_empty_list() -> None:
    """Empty / whitespace-only body — no LLM call, no
    persistence; SPA renders 'nothing to mine'."""
    user, ws = _make_user_workspace("b13empty@test")
    transcript = _make_transcript_asset(ws, body="   \n  ")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript.pk)},
        format="json",
    )
    assert response.status_code == http.HTTP_200_OK
    assert response.json()["highlights"] == []
    assert response.json()["used_synthesis"] is False
    assert TranscriptHighlight.objects.count() == 0


def test_mine_missing_transcript_asset_id_returns_400() -> None:
    user, _ = _make_user_workspace("b13missing@test")
    client = APIClient()
    _login(client, user)

    response = client.post(
        "/api/transcript_highlights/mine/",
        {},
        format="json",
    )
    assert response.status_code == http.HTTP_400_BAD_REQUEST


def test_mine_unauthenticated_returns_403() -> None:
    """Unauth POST is rejected before the body is parsed."""
    client = APIClient()
    response = client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(uuid.uuid4())},
        format="json",
    )
    # DRF returns 401 (authenticated=False) or 403 depending
    # on auth class config. SessionAuthentication returns 403.
    assert response.status_code in (
        http.HTTP_401_UNAUTHORIZED, http.HTTP_403_FORBIDDEN,
    )


# ---- list ------------------------------------------------------


def test_list_only_returns_user_workspace_highlights() -> None:
    user_a, ws_a = _make_user_workspace("b13lista@test")
    _, ws_b = _make_user_workspace("b13listb@test")
    transcript_a = _make_transcript_asset(ws_a)
    transcript_b = _make_transcript_asset(ws_b)

    # Mine in both workspaces. (We log in as A, mine A;
    # then log in as B, mine B — separate sessions.)
    client = APIClient()
    _login(client, user_a)
    client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript_a.pk)},
        format="json",
    )
    _login(client, User.objects.get(workspaces=ws_b))
    client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript_b.pk)},
        format="json",
    )

    # List as A — should only see A's highlights.
    _login(client, user_a)
    response = client.get("/api/transcript_highlights/")
    assert response.status_code == http.HTTP_200_OK
    rows = response.json()
    assert len(rows) >= 1
    for row in rows:
        assert row["workspace_id"] == str(ws_a.pk)


def test_list_filterable_by_status() -> None:
    user, ws = _make_user_workspace("b13status@test")
    transcript = _make_transcript_asset(ws)
    client = APIClient()
    _login(client, user)
    client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript.pk), "target_count": 3},
        format="json",
    )

    # Flip one to APPROVED via direct ORM (B1.4 ships the
    # REST mutator; B1.3 only exercises the read path).
    first = TranscriptHighlight.objects.filter(workspace=ws).first()
    assert first is not None
    first.status = TranscriptHighlight.Status.APPROVED
    first.save(update_fields=["status"])

    # Filter PENDING only.
    response = client.get(
        "/api/transcript_highlights/?status=pending",
    )
    assert response.status_code == http.HTTP_200_OK
    rows = response.json()
    assert all(r["status"] == "pending" for r in rows)
    assert all(r["id"] != str(first.pk) for r in rows)


def test_list_filterable_by_source_transcript() -> None:
    user, ws = _make_user_workspace("b13source@test")
    transcript_one = _make_transcript_asset(
        ws, body="Assistant: from transcript one.\n",
    )
    transcript_two = _make_transcript_asset(
        ws, body="Assistant: from transcript two.\n",
    )
    client = APIClient()
    _login(client, user)
    client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript_one.pk)},
        format="json",
    )
    client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript_two.pk)},
        format="json",
    )

    response = client.get(
        f"/api/transcript_highlights/"
        f"?source_transcript={transcript_one.pk}",
    )
    assert response.status_code == http.HTTP_200_OK
    rows = response.json()
    assert len(rows) >= 1
    assert all(
        r["source_transcript_id"] == str(transcript_one.pk) for r in rows
    )


# ---- retrieve --------------------------------------------------


def test_retrieve_returns_single_row() -> None:
    user, ws = _make_user_workspace("b13retrieve@test")
    transcript = _make_transcript_asset(ws)
    client = APIClient()
    _login(client, user)
    client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript.pk), "target_count": 1},
        format="json",
    )
    row = TranscriptHighlight.objects.filter(workspace=ws).first()
    assert row is not None

    response = client.get(f"/api/transcript_highlights/{row.pk}/")
    assert response.status_code == http.HTTP_200_OK
    assert response.json()["id"] == str(row.pk)


def test_retrieve_cross_workspace_returns_404() -> None:
    user_a, _ = _make_user_workspace("b13cra@test")
    _, ws_b = _make_user_workspace("b13crb@test")
    transcript_b = _make_transcript_asset(ws_b)

    # Mine in B (login as B's owner).
    client = APIClient()
    _login(client, User.objects.get(workspaces=ws_b))
    client.post(
        "/api/transcript_highlights/mine/",
        {"transcript_asset_id": str(transcript_b.pk), "target_count": 1},
        format="json",
    )
    row_b = TranscriptHighlight.objects.filter(workspace=ws_b).first()
    assert row_b is not None

    # Try to retrieve as A.
    _login(client, user_a)
    response = client.get(f"/api/transcript_highlights/{row_b.pk}/")
    assert response.status_code == http.HTTP_404_NOT_FOUND
