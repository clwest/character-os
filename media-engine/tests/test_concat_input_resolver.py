"""Local-path resolution for ``_download_concat_input``.

The concat / composite / mix endpoints all share one URL→Path
resolver. It accepts three shapes:

1. ``http(s)://...`` — downloaded over HTTP (Runway CDN URLs).
2. ``/data/<rest>`` — the public StaticFiles mount path that the
   SPA uses to play assets; maps to ``<data_path>/<rest>``. This
   is what intermediate Composition assets (concat / composite /
   mix outputs) carry as ``Asset.file_path``.
3. ``<rest>`` (relative) — operator-supplied paths relative to
   ``settings.data_path``.

The ``/data/...`` rewrite landed SESSION 179 after a real-mode
``talking_head_with_backdrop`` run blew up on a 400: the concat
step produced ``/data/_internal/concats/x.mp4`` as
``Asset.file_path``, the composite step passed that path to
media-engine, and the resolver tried to read the literal
``/data/_internal/...`` on the host filesystem — which doesn't
exist outside a container — and raised FileNotFoundError.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.config import Settings
from app.routers.internal import _download_concat_input


def _make_settings(data_path: Path) -> Settings:
    return Settings(
        runway_api_key="test",
        openai_api_key="test",
        data_dir=str(data_path),
    )


def test_resolves_data_mount_path(tmp_path: Path) -> None:
    """A ``/data/...`` URL maps to ``<data_path>/<rest>``."""
    fixture = tmp_path / "_internal" / "concats" / "x.mp4"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"")
    settings = _make_settings(tmp_path)
    resolved = _download_concat_input(
        "/data/_internal/concats/x.mp4",
        tmp_path / "sources",
        settings,
    )
    assert resolved == fixture


def test_resolves_relative_path(tmp_path: Path) -> None:
    """Relative paths resolve under ``settings.data_path``."""
    fixture = tmp_path / "_internal" / "sources" / "y.mp4"
    fixture.parent.mkdir(parents=True)
    fixture.write_bytes(b"")
    settings = _make_settings(tmp_path)
    resolved = _download_concat_input(
        "_internal/sources/y.mp4",
        tmp_path / "sources",
        settings,
    )
    assert resolved == fixture


def test_missing_data_mount_path_raises_filenotfound(tmp_path: Path) -> None:
    """When the rewritten path doesn't exist, raise — the route
    catches FileNotFoundError and returns a 400."""
    settings = _make_settings(tmp_path)
    with pytest.raises(FileNotFoundError):
        _download_concat_input(
            "/data/_internal/concats/does-not-exist.mp4",
            tmp_path / "sources",
            settings,
        )


def test_arbitrary_absolute_path_not_under_data_path_raises(
    tmp_path: Path,
) -> None:
    """A true absolute filesystem path that isn't under data_path
    is still rejected — the resolver only honors the ``/data/...``
    convention, not arbitrary host paths."""
    settings = _make_settings(tmp_path)
    with pytest.raises(FileNotFoundError):
        _download_concat_input(
            "/etc/definitely-not-a-clip.mp4",
            tmp_path / "sources",
            settings,
        )
