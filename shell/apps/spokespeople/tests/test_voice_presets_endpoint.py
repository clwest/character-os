"""``GET /api/spokespeople/voice-presets/`` disk-truth behavior.

SESSION 231 slice 1b — the endpoint now returns ``sample_url: null``
for any preset whose MP3 has not been baked into
``web/public/voice-samples/``. Prior behavior always returned
``/voice-samples/{name}.mp3`` even when the file was missing, which
would show up in the SPA as a broken ``<audio>`` element.
"""
from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from apps.spokespeople import views as spokespeople_views

User = get_user_model()

pytestmark = pytest.mark.django_db


def _auth_client() -> APIClient:
    user = User.objects.create_user(
        email="voice-presets-test@example.com", password="x",
    )
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def test_voice_presets_returns_disk_truth(tmp_path: Path) -> None:
    """Presets with a baked MP3 get a real URL; missing ones get null."""
    # Bake two of the known presets into a temp dir; leave the rest
    # missing.
    for name in ("adam", "clara"):
        (tmp_path / f"{name}.mp3").write_bytes(b"ID3\x04\x00fake-mp3")

    with patch.object(
        spokespeople_views, "_voice_samples_dir", return_value=tmp_path,
    ):
        resp = _auth_client().get("/api/spokespeople/voice-presets/")

    assert resp.status_code == 200
    presets = resp.data["presets"]
    by_name = {row["name"]: row for row in presets}

    # All 30 known presets are still enumerated — shape stays stable.
    assert len(presets) == len(spokespeople_views.SUPPORTED_VOICE_PRESETS)

    # Baked → real URL.
    assert by_name["adam"]["sample_url"] == "/voice-samples/adam.mp3"
    assert by_name["clara"]["sample_url"] == "/voice-samples/clara.mp3"

    # Not baked → explicit null (not an empty string, not a hopeful URL).
    assert by_name["victoria"]["sample_url"] is None
    assert by_name["luna"]["sample_url"] is None


def test_voice_presets_all_null_when_dir_empty(tmp_path: Path) -> None:
    """Empty samples dir → every preset returns ``sample_url: null``."""
    with patch.object(
        spokespeople_views, "_voice_samples_dir", return_value=tmp_path,
    ):
        resp = _auth_client().get("/api/spokespeople/voice-presets/")

    assert resp.status_code == 200
    presets = resp.data["presets"]
    assert len(presets) == len(spokespeople_views.SUPPORTED_VOICE_PRESETS)
    assert all(row["sample_url"] is None for row in presets)
