"""Endpoint surface for ``POST /internal/clips/intro_outro/``.

These cover the three bugs SESSION 180's real-mode dogfood of
``talking_head_polished`` surfaced — each of which had been
latent since V9 shipped SESSION 143 because no real-mode test
exercised the dual-card + non-1280x720 + apostrophe-in-text
combination:

1. **drawtext apostrophe escaping.** The original escape used
   ``\\'`` which closed the single-quoted ffmpeg filter
   argument prematurely. Fixed with POSIX close-escape-reopen
   (``'\\''``). Without the fix, any title card text
   containing an apostrophe fails the whole filter graph.

2. **intro_outro input indexing.** ``len(args) // 2`` counted
   ffmpeg argument PAIRS, not actual ``-i`` occurrences —
   ``-f lavfi -i X`` is 4 args but a single input. Fixed by
   tracking ``input_count`` explicitly. Without the fix, any
   call supplying both intro AND outro produces a filter
   graph referencing nonexistent input indices (the
   ``[3:a]/[5:v]`` foot-gun).

3. **Hardcoded canvas dimensions.** The title cards were
   sized to 1280x720, breaking concat against any clip with
   different dimensions (Runway gwm1_avatars at 1088x704 is
   the canonical failure case). Fixed by probing the body
   clip's dims and matching the lavfi color source.

The pure-function escape test is unit; the dual-card endpoint
test is integration (real ffmpeg + real ffprobe) — kept fast
by generating a tiny 1-second lavfi color source as the body
clip.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.routers.internal import (
    TitleCardSpec,
    _build_card_filter,
    _probe_dimensions,
)


# ---- pure-function: drawtext text escaping ------------------------


def _filter_for(text: str) -> str:
    spec = TitleCardSpec(text=text)
    return _build_card_filter(spec, 1280, 720, "[1:v]", "[intro_v]")


def test_apostrophe_uses_posix_close_escape_reopen() -> None:
    """``Don't`` must escape as ``Don'\\''t`` so the single-
    quoted ffmpeg filter argument parser concatenates the
    adjacent runs back into ``Don't``. The prior backslash-
    only escape closed the quoted run prematurely."""
    out = _filter_for("Don't blink.")
    # Embedded inside the filter, the apostrophe-escape sequence
    # should be the POSIX `'\''` form (close-quote, escape-
    # apostrophe, reopen-quote).
    assert r"Don'\''t" in out
    # And the broken `\\'` form (prior bug) must not be present.
    assert r"Don\\'t" not in out


def test_colons_are_backslash_escaped() -> None:
    """Colons are the ffmpeg filter argument delimiter; raw
    colons in card text would split the drawtext options.
    The escape leaves a backslash-colon in the filter."""
    out = _filter_for("Episode: 1")
    assert r"Episode\: 1" in out


def test_backslashes_are_doubled() -> None:
    """Backslashes in the text must double so a single
    backslash survives the filter parser's own
    backslash-handling."""
    out = _filter_for("path\\to\\file")
    assert r"path\\to\\file" in out


def test_multiple_apostrophes_all_get_escaped() -> None:
    out = _filter_for("It's Riggs's show.")
    # Both apostrophes appear in the close-escape-reopen form.
    assert out.count(r"'\''") == 2


# ---- dimension probe ---------------------------------------------


def test_probe_dimensions_reads_actual_video_dims(
    tmp_path: Path,
) -> None:
    """``_probe_dimensions`` returns the body clip's real
    (width, height), not the 1280x720 fallback. Validates the
    SESSION 180 fix that breaks intro_outro for non-default
    aspect ratios (e.g. Runway gwm1_avatars at 1088x704)."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")

    fixture = tmp_path / "src-1088x704.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", "color=c=red:s=1088x704:r=30:d=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-f", "mp4", str(fixture),
        ],
        check=True, capture_output=True, timeout=30,
    )
    assert fixture.exists()

    w, h = _probe_dimensions(fixture)
    assert (w, h) == (1088, 704)


# ---- end-to-end endpoint with the SESSION 180 trigger payload ----


def _make_body_clip(tmp_path: Path, w: int = 1088, h: int = 704) -> Path:
    """One-second silent body clip with non-1280x720 dims —
    the same shape Runway avatars come out at, so the endpoint
    has to actually probe + match instead of falling through
    to the 1280x720 default."""
    out = tmp_path / f"body-{w}x{h}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=blue:s={w}x{h}:r=30:d=1",
            "-f", "lavfi",
            "-i", "anullsrc=channel_layout=stereo:sample_rate=48000:d=1",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-shortest",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


@pytest.fixture
def real_mode_client(tmp_path: Path):
    """TestClient pinned to a tmp data_path with runway_mock
    OFF so the real ffmpeg pipeline runs."""
    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="present",  # disables runway_mock
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


def test_dual_card_with_apostrophes_on_non_default_size(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Exercises all three SESSION 180 fixes in one shot:
    body clip is 1088x704 (not the 1280x720 default), and both
    intro AND outro are supplied with apostrophe-bearing text.
    The pre-fix endpoint failed three different ways on this
    payload — drawtext quote parse error, then bogus input
    index, then ffmpeg encoder rejecting mismatched dims."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "intro": {"text": "Riggs's Rules.", "duration_s": 1.0},
            "outro": {"text": "Don't blink.", "duration_s": 1.0},
        },
    )
    assert resp.status_code == 200, resp.text
    body_json = resp.json()
    assert body_json["mock_mode"] is False
    assert body_json["output_url"].startswith(
        "/data/_internal/intro_outros/"
    )
    assert body_json["size_bytes"] > 0
    # Composite duration = body + intro + outro = 1 + 1 + 1 = 3s.
    # Endpoint returns it summed (body_dur + intro + outro).
    assert body_json["duration_seconds"] == pytest.approx(3.0, abs=0.1)


def test_intro_only_succeeds_without_outro(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Single-card path — pre-fix worked here, but the input-
    indexing fix touched both branches. Regression guard."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "intro": {"text": "Hello", "duration_s": 1.0},
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["mock_mode"] is False


def test_outro_only_succeeds_without_intro(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Same regression guard for the outro-only path."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {"text": "Bye", "duration_s": 1.0},
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["mock_mode"] is False
