"""Asset Library v1 (SESSION 187, A3) — storage-health helper tests.

Covers all seven :class:`StorageHealth` states plus JWT parsing edge
cases. Tests are pure-function — no Django DB required for the helper
itself; the few that build an Asset use the standard helper from
test_models so workspace anchor + signal validation still fire.
"""
from __future__ import annotations

import base64
import json
import time
from pathlib import Path

import pytest
from django.contrib.auth import get_user_model
from django.test import override_settings

from apps.accounts.models import Workspace
from apps.compositions.assets import (
    StorageHealth,
    compute_storage_health,
    parse_jwt_exp,
)
from apps.compositions.models import Asset, AssetType

User = get_user_model()
pytestmark = pytest.mark.django_db


# ---- JWT fixture helpers --------------------------------------------


def _b64url_encode(payload: dict) -> str:
    raw = json.dumps(payload).encode("utf-8")
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _make_jwt(exp_seconds: int) -> str:
    """Build a JWT with the given exp. Header + signature are placeholders;
    the parser only reads the payload."""
    header = _b64url_encode({"alg": "HS256", "typ": "JWT"})
    payload = _b64url_encode(
        {"keyHash": "x", "bucket": "runway-task-artifacts", "exp": exp_seconds}
    )
    signature = "fake_signature_does_not_validate"
    return f"{header}.{payload}.{signature}"


def _cdn_url(exp_seconds: int) -> str:
    return (
        f"https://dnznrvs05pmza.cloudfront.net/abc.mp4?_jwt={_make_jwt(exp_seconds)}"
    )


# ---- Workspace + asset helpers --------------------------------------


def _make_workspace(email: str) -> Workspace:
    user = User.objects.create_user(email=email, password="x")
    ws = Workspace.objects.filter(owner=user).first()
    assert ws is not None
    return ws


def _make_asset(ws: Workspace, file_path: str, **kwargs) -> Asset:
    return Asset.objects.create(
        workspace=ws,
        asset_type=kwargs.pop("asset_type", AssetType.CLIP),
        file_path=file_path,
        **kwargs,
    )


# ---- HTTPS branch ---------------------------------------------------


def test_https_live_when_jwt_exp_far_future() -> None:
    ws = _make_workspace("a3live@test.local")
    far_future = int(time.time()) + 7 * 24 * 3600  # 7 days out
    asset = _make_asset(ws, file_path=_cdn_url(far_future))
    assert compute_storage_health(asset) == StorageHealth.HTTPS_LIVE


def test_https_expiring_soon_when_jwt_exp_within_24h() -> None:
    ws = _make_workspace("a3expiring@test.local")
    soon = int(time.time()) + 6 * 3600  # 6 hours out
    asset = _make_asset(ws, file_path=_cdn_url(soon))
    assert compute_storage_health(asset) == StorageHealth.HTTPS_EXPIRING_SOON


def test_https_expired_when_jwt_exp_past() -> None:
    ws = _make_workspace("a3expired@test.local")
    past = int(time.time()) - 3600  # 1 hour ago
    asset = _make_asset(ws, file_path=_cdn_url(past))
    assert compute_storage_health(asset) == StorageHealth.HTTPS_EXPIRED


def test_https_live_when_no_jwt_query_param() -> None:
    """Non-Runway HTTPS URLs (and Runway URLs that have already had the
    JWT stripped) fall through to LIVE — we don't have a signal to say
    otherwise without a network round-trip."""
    ws = _make_workspace("a3nojwt@test.local")
    asset = _make_asset(
        ws, file_path="https://example.com/some/clip.mp4"
    )
    assert compute_storage_health(asset) == StorageHealth.HTTPS_LIVE


def test_https_live_when_jwt_payload_malformed() -> None:
    """Malformed JWT (corrupt base64, non-JSON payload, missing exp,
    non-numeric exp) falls back to LIVE rather than crashing."""
    ws = _make_workspace("a3badjwt@test.local")
    asset = _make_asset(
        ws, file_path="https://cdn/clip.mp4?_jwt=not-a-real-jwt"
    )
    assert compute_storage_health(asset) == StorageHealth.HTTPS_LIVE


def test_https_live_when_jwt_missing_exp_field() -> None:
    ws = _make_workspace("a3noexp@test.local")
    header = _b64url_encode({"alg": "HS256", "typ": "JWT"})
    payload = _b64url_encode({"keyHash": "x", "bucket": "b"})  # no exp
    asset = _make_asset(
        ws,
        file_path=f"https://cdn/clip.mp4?_jwt={header}.{payload}.sig",
    )
    assert compute_storage_health(asset) == StorageHealth.HTTPS_LIVE


def test_https_live_when_jwt_exp_is_non_numeric() -> None:
    ws = _make_workspace("a3strexp@test.local")
    header = _b64url_encode({"alg": "HS256", "typ": "JWT"})
    payload = _b64url_encode({"exp": "tomorrow"})  # not a number
    asset = _make_asset(
        ws,
        file_path=f"https://cdn/clip.mp4?_jwt={header}.{payload}.sig",
    )
    assert compute_storage_health(asset) == StorageHealth.HTTPS_LIVE


# ---- DATA_URI branch ------------------------------------------------


def test_data_uri_classified() -> None:
    ws = _make_workspace("a3datauri@test.local")
    asset = _make_asset(
        ws,
        asset_type=AssetType.IMAGE,
        file_path="data:image/png;base64,iVBORw0KGgoAAAA...",
    )
    assert compute_storage_health(asset) == StorageHealth.DATA_URI


# ---- LOCAL branch ---------------------------------------------------


def test_local_present_when_filesystem_path_exists(tmp_path: Path) -> None:
    """``Asset.file_path`` like ``/data/_internal/foo.mp4`` resolves
    against ``settings.MEDIA_ENGINE_DATA_ROOT``; existence check fires
    against the real filesystem."""
    ws = _make_workspace("a3localok@test.local")
    fake_file = tmp_path / "data" / "_internal" / "present.mp4"
    fake_file.parent.mkdir(parents=True)
    fake_file.write_bytes(b"\x00\x00")
    asset = _make_asset(ws, file_path="/data/_internal/present.mp4")
    with override_settings(MEDIA_ENGINE_DATA_ROOT=str(tmp_path)):
        assert compute_storage_health(asset) == StorageHealth.LOCAL_PRESENT


def test_local_missing_when_filesystem_path_absent(tmp_path: Path) -> None:
    ws = _make_workspace("a3localgone@test.local")
    asset = _make_asset(ws, file_path="/data/_internal/never_existed.mp4")
    with override_settings(MEDIA_ENGINE_DATA_ROOT=str(tmp_path)):
        assert compute_storage_health(asset) == StorageHealth.LOCAL_MISSING


def test_local_missing_when_path_resolves_to_directory(tmp_path: Path) -> None:
    """Defensive: if the resolved path points at a directory, treat as
    missing — the Asset expects a file."""
    ws = _make_workspace("a3localdir@test.local")
    (tmp_path / "data" / "_internal").mkdir(parents=True)
    asset = _make_asset(ws, file_path="/data/_internal")  # dir, not file
    with override_settings(MEDIA_ENGINE_DATA_ROOT=str(tmp_path)):
        assert compute_storage_health(asset) == StorageHealth.LOCAL_MISSING


# ---- UPLOAD_PENDING / fallthroughs ----------------------------------


def test_upload_pending_when_file_path_empty() -> None:
    """TRANSCRIPT Assets often have empty file_path (content lives in
    inline_content). The future upload-UI placeholder shape is also
    empty file_path."""
    ws = _make_workspace("a3empty@test.local")
    asset = _make_asset(
        ws,
        asset_type=AssetType.TRANSCRIPT,
        file_path="",
        inline_content='{"segments":[]}',
    )
    assert compute_storage_health(asset) == StorageHealth.UPLOAD_PENDING


def test_upload_pending_for_unknown_scheme() -> None:
    """A file_path with neither a recognized scheme nor a leading
    slash falls through to UPLOAD_PENDING. Operator can sort out by
    hand."""
    ws = _make_workspace("a3weird@test.local")
    asset = _make_asset(ws, file_path="s3://bucket/key")
    assert compute_storage_health(asset) == StorageHealth.UPLOAD_PENDING


def test_upload_pending_when_file_path_is_whitespace() -> None:
    ws = _make_workspace("a3whitespace@test.local")
    asset = _make_asset(ws, file_path="   ")
    assert compute_storage_health(asset) == StorageHealth.UPLOAD_PENDING


# ---- parse_jwt_exp direct surface -----------------------------------


def test_parse_jwt_exp_returns_int_for_valid_jwt() -> None:
    exp = int(time.time()) + 3600
    assert parse_jwt_exp(_cdn_url(exp)) == exp


def test_parse_jwt_exp_returns_none_for_url_without_jwt() -> None:
    assert parse_jwt_exp("https://example.com/clip.mp4") is None


def test_parse_jwt_exp_returns_none_for_empty_url() -> None:
    assert parse_jwt_exp("") is None


def test_parse_jwt_exp_returns_none_for_malformed_jwt() -> None:
    assert parse_jwt_exp("https://cdn/x?_jwt=not.really.jwt.here") is None


def test_parse_jwt_exp_handles_jwt_with_two_parts_only() -> None:
    """JWT must have exactly 3 dot-separated parts."""
    assert parse_jwt_exp("https://cdn/x?_jwt=onlytwo.parts") is None


# ---- StorageHealth.all() ------------------------------------------


def test_all_returns_seven_unique_values() -> None:
    values = StorageHealth.all()
    assert len(values) == 7
    assert len(set(values)) == 7
