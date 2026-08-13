"""Endpoint surface for ``POST /internal/clips/composite/``
with ``layout_spec.kind=broll``.

SESSION 181 dogfood of `broll_splice` (1088x704 polished base +
1280x720 cinematic_visual cutaway) failed with ffmpeg rc=234
"Could not open encoder before EOF" / "task finished with error
code: -22 (Invalid argument)" — the concat filter rejected the
mismatched dimensions silently. Same shape as the SESSION 180
intro_outro canvas-default bug: a hardcoded 1280:720 scale on
the cutaway, no setsar on the pre/post segments, no probe of
the actual base dims.

This test exercises the fix end-to-end: a non-default-sized
base (1088x704, the Runway gwm1_avatars output shape) plus a
gen4.5-default-sized cutaway (1280x720). The pre-fix endpoint
emitted a filter graph whose three concat segments had
incompatible (width, height, SAR) tuples; the post-fix endpoint
probes the base dims and threads them into the cutaway scale
+ adds setsar=1 to every segment.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.routers.internal import _build_broll_filter


# ---- pure-function: broll filter threads canvas dims through -----


def test_broll_filter_scales_cutaway_to_supplied_canvas_dims() -> None:
    """``_build_broll_filter`` produces a filter graph that scales
    the cutaway to the operator-supplied canvas dims, not the
    1280x720 default. Regression guard against the SESSION 181
    hardcoded-scale bug."""
    f = _build_broll_filter(
        {"cutaway_start_s": 1.0, "cutaway_end_s": 3.0},
        base_dur=10.0,
        canvas_w=1088,
        canvas_h=704,
    )
    # Cutaway segment scales to 1088x704, not the prior
    # 1280x720 hardcode.
    assert "scale=1088:704" in f
    assert "crop=1088:704" in f
    assert "scale=1280:720" not in f


def test_broll_filter_sets_sar_on_all_three_concat_segments() -> None:
    """concat requires matching SAR (sample aspect ratio) across
    inputs. Without ``setsar=1`` on the pre + post segments,
    different SARs across the three segments crash the encoder.
    Pre-fix only the cutaway had setsar=1."""
    f = _build_broll_filter(
        {"cutaway_start_s": 1.0, "cutaway_end_s": 3.0},
        base_dur=10.0,
        canvas_w=1280,
        canvas_h=720,
    )
    # One setsar=1 per segment (v_pre, v_cut, v_post) = 3 total.
    assert f.count("setsar=1") == 3


def test_broll_filter_rejects_cutaway_outside_base() -> None:
    """Operator-supplied cutaway window must lie inside the
    base clip's timeline. Out-of-bounds rejects with ValueError
    (route handler converts to 400)."""
    with pytest.raises(ValueError, match="must be inside base"):
        _build_broll_filter(
            {"cutaway_start_s": 5.0, "cutaway_end_s": 15.0},
            base_dur=10.0,
            canvas_w=1280, canvas_h=720,
        )


def test_broll_filter_rejects_zero_or_negative_duration() -> None:
    with pytest.raises(ValueError, match="must be inside base"):
        _build_broll_filter(
            {"cutaway_start_s": 5.0, "cutaway_end_s": 5.0},
            base_dur=10.0,
            canvas_w=1280, canvas_h=720,
        )


# ---- end-to-end endpoint with the SESSION 181 trigger payload ----


def _make_clip(
    tmp_path: Path,
    name: str,
    w: int,
    h: int,
    color: str = "blue",
    duration_s: int = 10,
) -> Path:
    out = tmp_path / f"{name}-{w}x{h}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c={color}:s={w}x{h}:r=30:d={duration_s}",
            "-f", "lavfi",
            "-i", f"anullsrc=channel_layout=stereo:sample_rate=48000:d={duration_s}",
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
            runway_api_key="present",
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


def test_broll_splice_on_mismatched_base_and_cutaway_dims(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """The SESSION 181 trigger: base at 1088x704 (Runway avatar
    output shape) + cutaway at 1280x720 (gen4.5 default). The
    pre-fix endpoint returned a 500 with ffmpeg rc=234. The
    post-fix endpoint produces a clean concat at base dims."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_clip(tmp_path, "base", 1088, 704, "navy", duration_s=10)
    broll = _make_clip(tmp_path, "broll", 1280, 720, "orange", duration_s=5)

    resp = real_mode_client.post(
        "/internal/clips/composite/",
        json={
            "clip_urls": [str(base), str(broll)],
            "layout_spec": {
                "kind": "broll",
                "options": {"cutaway_start_s": 3.0, "cutaway_end_s": 6.0},
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is False
    assert body["output_url"].startswith("/data/_internal/composites/broll-")

    # Output must inherit base dims (1088x704), not the cutaway's.
    output_rel = body["output_url"][len("/data/"):]
    output_path = tmp_path / output_rel
    assert output_path.exists()
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "v:0",
            "-show_entries", "stream=width,height",
            "-of", "csv=s=x:p=0",
            str(output_path),
        ],
        capture_output=True, text=True, timeout=10,
    )
    assert probe.stdout.strip() == "1088x704"


def test_broll_splice_matched_dims_still_works(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Regression guard that the dim-probe fix didn't break the
    matched-dimensions path (where pre-fix accidentally worked)."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_clip(tmp_path, "base", 1280, 720, "navy", duration_s=10)
    broll = _make_clip(tmp_path, "broll", 1280, 720, "orange", duration_s=5)

    resp = real_mode_client.post(
        "/internal/clips/composite/",
        json={
            "clip_urls": [str(base), str(broll)],
            "layout_spec": {
                "kind": "broll",
                "options": {"cutaway_start_s": 2.0, "cutaway_end_s": 4.0},
            },
        },
    )
    assert resp.status_code == 200, resp.text
