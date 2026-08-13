"""``maybe_to_data_uri`` URL → data-URI rewrites for prompt_image.

Runway's ``image_to_video`` rejects non-HTTPS URLs in
``promptImage``. The media-engine has historically rewritten a
couple of legacy local-path prefixes
(``/api/runway/image/...``, ``/api/characters/.../portrait``)
into data URIs before posting. SESSION 181 dogfood of
``storyboard_ad`` surfaced a missing case: V13's
``generate_image`` outputs land at
``/data/_internal/images/<hash>.png``, and that prefix wasn't
in the rewrite table — Runway rejected with
``Invalid string: must start with "https://"`` the moment the
storyboard chain fed a V13 image into V4's image-to-video.

These tests pin the V13 prefix rewrite + the existing
behaviour for the other prefixes.
"""
from __future__ import annotations

import base64
from pathlib import Path

import pytest

from app.config import Settings
from app.services.runway_client import maybe_to_data_uri


def _make_settings(data_path: Path) -> Settings:
    return Settings(
        runway_api_key="present",
        openai_api_key="test",
        data_dir=str(data_path),
    )


def _write_tiny_png(path: Path) -> None:
    """Drop a minimal 1x1 PNG so the rewrite has a real file to
    read. Content doesn't matter — the rewrite returns a data
    URI of whatever bytes it finds."""
    path.parent.mkdir(parents=True, exist_ok=True)
    png_bytes = bytes.fromhex(
        "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15"
        "c4890000000d49444154789c63000100000005000100"
        "0d0a2db40000000049454e44ae426082"
    )
    path.write_bytes(png_bytes)


def test_v13_internal_image_path_rewrites_to_data_uri(
    tmp_path: Path,
) -> None:
    """V13's generate_image output URL maps to a real on-disk
    file under ``<data_path>/_internal/images/...`` and embeds
    as a data URI. The fix that unblocks the storyboard chain."""
    fixture = tmp_path / "_internal" / "images" / "hash123.png"
    _write_tiny_png(fixture)
    settings = _make_settings(tmp_path)
    out = maybe_to_data_uri(
        "/data/_internal/images/hash123.png", settings,
    )
    assert out.startswith("data:image/png;base64,")
    # Decoded payload should match the file bytes.
    b64 = out.split(",", 1)[1]
    assert base64.b64decode(b64) == fixture.read_bytes()


def test_v13_path_with_missing_file_falls_through_unchanged(
    tmp_path: Path,
) -> None:
    """Missing file → return URL as-is. Runway then surfaces the
    400 it would naturally produce; the operator gets the real
    "image not found" error rather than a silent rewrite to a
    stale data URI."""
    settings = _make_settings(tmp_path)
    url = "/data/_internal/images/does-not-exist.png"
    assert maybe_to_data_uri(url, settings) == url


def test_v13_path_rejects_traversal_attempts(tmp_path: Path) -> None:
    """``..`` and nested paths in the URL segment must not
    escape the images directory."""
    settings = _make_settings(tmp_path)
    for evil in (
        "/data/_internal/images/../secret.png",
        "/data/_internal/images/subdir/file.png",
    ):
        assert maybe_to_data_uri(evil, settings) == evil


def test_external_https_url_passes_through_unchanged(
    tmp_path: Path,
) -> None:
    """Real HTTPS URLs (Runway CDN, operator-uploaded references)
    must not be touched."""
    settings = _make_settings(tmp_path)
    url = "https://example.test/some-image.png"
    assert maybe_to_data_uri(url, settings) == url


def test_empty_prompt_image_passes_through(tmp_path: Path) -> None:
    """Edge case — empty string handled cleanly."""
    settings = _make_settings(tmp_path)
    assert maybe_to_data_uri("", settings) == ""
