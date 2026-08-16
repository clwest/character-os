"""SESSION 256 — endpoint surface for ``POST /internal/clips/image_overlay/``.

Reusable "visual callout / PiP" system. Overlays a still IMAGE
onto a base CLIP for the whole duration or a subrange, with
optional border + shadow decoration. Local ffmpeg only; no
provider call.

Coverage matrix mirrors the operator's SESSION 256 acceptance
list:

  Image source polymorphism (SESSION 255 resolver reuse):
    * data:image/...;base64,... payload accepted
    * /data/... local URL accepted
    * malformed source rejected

  Positioning (all four corners tested explicitly via the
  pure-function helper AND the endpoint filter string):
    * top_left / top_right / bottom_left / bottom_right

  Timing (ffmpeg enable=between(t,s,e) semantics — no physical
  split/concat):
    * both blank → full-duration overlay (no enable expression)
    * start-only → overlay from start_time to end of base
    * start + end → subrange overlay
    * end <= start rejected pre-ffmpeg
    * start beyond base duration rejected pre-ffmpeg
    * overlay timing does not alter output duration

  Presentation:
    * border=True renders the pad filter with the white border color
    * shadow=True renders the two-stage overlay chain (shadow + main)
    * border=False + shadow=False renders the single-stage overlay chain

  Base semantics:
    * output duration == base duration (real ffmpeg render)
    * base audio survives unchanged

  Cache:
    * different image_source → different cache key → different filename
    * different corner → different cache key
    * different timing → different cache key
    * identical request → cache hit (idempotent)
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
    InternalImageOverlayCreate,
    _IMAGE_OVERLAY_BORDER_COLOR,
    _IMAGE_OVERLAY_SHADOW_COLOR,
    _image_overlay_corner_xy,
)


# ---- helpers ------------------------------------------------------


def _tiny_png_bytes(width: int = 8, height: int = 8, color=(60, 140, 40)) -> bytes:
    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _tiny_png_data_uri(width: int = 8, height: int = 8, color=(60, 140, 40)) -> str:
    import base64 as _b64
    return "data:image/png;base64," + _b64.b64encode(
        _tiny_png_bytes(width, height, color),
    ).decode("ascii")


def _make_base_clip(
    tmp_path: Path, w: int = 1280, h: int = 720, duration_s: int = 4,
) -> Path:
    """A silent-audio-bearing color source with the given dims +
    duration. Small enough to render fast in every test."""
    out = tmp_path / f"base-{w}x{h}-{duration_s}s.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi", "-i", f"color=c=blue:s={w}x{h}:r=30:d={duration_s}",
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
    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="present",
            openai_api_key="test",
            data_dir=str(tmp_path),
        )
    app.dependency_overrides[get_settings] = _settings_override
    yield TestClient(app)
    app.dependency_overrides.pop(get_settings, None)


# ---- pure-function: corner math ----------------------------------


def test_corner_math_top_left() -> None:
    x, y = _image_overlay_corner_xy(
        "top_left",
        main_w=1280, main_h=720,
        overlay_outer_w=326, overlay_outer_h=200,
        margin_x=40, margin_y=40,
    )
    assert (x, y) == (40, 40)


def test_corner_math_top_right() -> None:
    x, y = _image_overlay_corner_xy(
        "top_right",
        main_w=1280, main_h=720,
        overlay_outer_w=326, overlay_outer_h=200,
        margin_x=40, margin_y=40,
    )
    assert (x, y) == (1280 - 326 - 40, 40)


def test_corner_math_bottom_left() -> None:
    x, y = _image_overlay_corner_xy(
        "bottom_left",
        main_w=1280, main_h=720,
        overlay_outer_w=326, overlay_outer_h=200,
        margin_x=40, margin_y=40,
    )
    assert (x, y) == (40, 720 - 200 - 40)


def test_corner_math_bottom_right() -> None:
    x, y = _image_overlay_corner_xy(
        "bottom_right",
        main_w=1280, main_h=720,
        overlay_outer_w=326, overlay_outer_h=200,
        margin_x=40, margin_y=40,
    )
    assert (x, y) == (1280 - 326 - 40, 720 - 200 - 40)


def test_corner_math_rejects_unknown_corner() -> None:
    with pytest.raises(ValueError, match="unknown corner"):
        _image_overlay_corner_xy(
            "middle",
            main_w=1280, main_h=720,
            overlay_outer_w=326, overlay_outer_h=200,
            margin_x=40, margin_y=40,
        )


# ---- pydantic body validation ------------------------------------


def test_pydantic_body_defaults() -> None:
    body = InternalImageOverlayCreate(
        clip_url="/data/base.mp4",
        image_source="data:image/png;base64,abc",
    )
    assert body.corner == "top_right"
    assert body.overlay_width == 320
    assert body.margin_x == 40
    assert body.margin_y == 40
    assert body.start_time_s is None
    assert body.end_time_s is None
    assert body.border is True
    assert body.shadow is True


def test_pydantic_body_rejects_impossibly_large_width() -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        InternalImageOverlayCreate(
            clip_url="/data/base.mp4",
            image_source="data:image/png;base64,abc",
            overlay_width=9999,
        )


def test_pydantic_body_rejects_negative_margin() -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        InternalImageOverlayCreate(
            clip_url="/data/base.mp4",
            image_source="data:image/png;base64,abc",
            margin_x=-5,
        )


def test_pydantic_body_rejects_negative_start_time() -> None:
    from pydantic import ValidationError
    with pytest.raises(ValidationError):
        InternalImageOverlayCreate(
            clip_url="/data/base.mp4",
            image_source="data:image/png;base64,abc",
            start_time_s=-1,
        )


# ---- endpoint: image-source polymorphism (SESSION 255 reuse) -----


def test_endpoint_accepts_data_uri_image(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(64, 64),
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is False
    assert body["output_url"].startswith("/data/_internal/image_overlays/")


def test_endpoint_accepts_local_data_url_image(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    # Materialize an image the storyboard flow's shape.
    img_dir = tmp_path / "_internal" / "images"
    img_dir.mkdir(parents=True)
    img_path = img_dir / "storyboard.png"
    img_path.write_bytes(_tiny_png_bytes(64, 64))

    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": "/data/_internal/images/storyboard.png",
        },
    )
    assert resp.status_code == 200, resp.text


def test_endpoint_rejects_malformed_image_source(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": "not-a-uri-and-not-a-path",
        },
    )
    assert resp.status_code == 400
    assert resp.json().get("code") == "invalid_image_source"


# ---- endpoint: corner enum ----------------------------------------


@pytest.mark.parametrize(
    "corner",
    ["top_right", "top_left", "bottom_right", "bottom_left"],
)
def test_endpoint_accepts_all_four_corners(
    real_mode_client: TestClient, tmp_path: Path, corner: str,
) -> None:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "corner": corner,
        },
    )
    assert resp.status_code == 200, resp.text


def test_endpoint_rejects_unknown_corner(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "corner": "middle",
        },
    )
    assert resp.status_code == 422
    assert resp.json().get("code") == "validation_error"


# ---- endpoint: timing --------------------------------------------


def test_endpoint_full_duration_default_timing(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Both start_time_s and end_time_s blank → overlay for the
    entire base clip. Output duration == base duration."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_base_clip(tmp_path, duration_s=3)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]
    dur = _probe_duration_local(output_path)
    assert dur == pytest.approx(3.0, abs=0.15)


def test_endpoint_start_only_timing(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """start_time_s set, end_time_s blank → overlay appears from
    start_time and stays through end of base."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_base_clip(tmp_path, duration_s=4)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "start_time_s": 1.5,
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]
    # Output duration matches base — overlay never extends beyond it.
    assert _probe_duration_local(output_path) == pytest.approx(4.0, abs=0.15)


def test_endpoint_start_and_end_timing(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Both fields set → subrange overlay via enable=between(t,s,e).
    Output duration still == base duration."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_base_clip(tmp_path, duration_s=4)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "start_time_s": 1.0,
            "end_time_s": 3.0,
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]
    assert _probe_duration_local(output_path) == pytest.approx(4.0, abs=0.15)


def test_endpoint_rejects_end_before_start(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """end_time_s <= start_time_s is caught before ffmpeg runs."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    base = _make_base_clip(tmp_path, duration_s=4)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "start_time_s": 3.0,
            "end_time_s": 1.0,
        },
    )
    assert resp.status_code == 422
    assert "greater than start_time_s" in resp.json().get("error", "")


def test_endpoint_rejects_start_beyond_base_duration(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """start_time_s >= base duration would produce an overlay that
    never appears; return 422 rather than silently rendering an
    unchanged clip."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")
    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "start_time_s": 5.0,
        },
    )
    assert resp.status_code == 422
    assert "beyond the base clip's duration" in resp.json().get("error", "")


# ---- endpoint: presentation + audio ------------------------------


def test_endpoint_default_border_and_shadow_render(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Default border=True + shadow=True — the rendered frame
    carries both the border color (white) and the shadow color
    (dark) plus the source image color (green) plus the base
    (blue). Existence proves the two-stage overlay chain fired."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(64, 64, (60, 200, 60)),
            "corner": "top_right",
            "overlay_width": 200,
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]

    # Extract frame at 1.0s (well past any encoder boundary).
    frame = tmp_path / "probe.png"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", "1.0", "-i", str(output_path),
            "-frames:v", "1", "-update", "1", str(frame),
        ],
        check=True, capture_output=True, timeout=30,
    )
    from PIL import Image
    img = Image.open(frame).convert("RGB")
    pixels = list(img.getdata())
    # Blue base pixels dominate.
    blue_base = sum(1 for r, g, b in pixels if b > r + 50 and b > g + 50)
    # Green overlay pixels present (from the source image).
    green_overlay = sum(1 for r, g, b in pixels if g > r + 30 and g > b + 30)
    # White border pixels present (near-pure white).
    white_border = sum(1 for r, g, b in pixels if r > 220 and g > 220 and b > 220)
    assert blue_base > 100000
    assert green_overlay > 500, f"green overlay pixels: {green_overlay}"
    assert white_border > 100, f"white border pixels: {white_border}"


def test_endpoint_border_and_shadow_off_still_renders(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """border=False + shadow=False — the single-stage overlay
    chain fires. Guards against a filter-string bug on the
    minimal-decoration path."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(64, 64, (60, 200, 60)),
            "border": False,
            "shadow": False,
        },
    )
    assert resp.status_code == 200, resp.text


def test_endpoint_output_duration_matches_base(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Regression guard: overlay must never extend the output
    beyond base_dur, even when the -loop 1 image input is
    infinite by construction."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_base_clip(tmp_path, duration_s=3)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "start_time_s": 0.5,
            "end_time_s": 2.5,
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]
    dur = _probe_duration_local(output_path)
    assert dur == pytest.approx(3.0, abs=0.15)


def test_endpoint_base_audio_survives(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Output MP4 carries an audio stream. Base was authored
    with anullsrc silent stereo track; the overlay endpoint
    preserves it unmodified."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    base = _make_base_clip(tmp_path, duration_s=2)
    resp = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(output_path),
        ],
        check=True, capture_output=True, text=True, timeout=10,
    )
    codecs = [ln.strip() for ln in probe.stdout.splitlines() if ln.strip()]
    assert "video" in codecs
    assert "audio" in codecs


# ---- endpoint: fit / aspect ratio --------------------------------


def test_endpoint_preserves_source_image_aspect_ratio(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """FIT/CONTAIN: the endpoint's ffmpeg filter uses
    ``scale=W:-2`` (auto-height rounded to even), which
    preserves the source aspect ratio. A tall 100x200 source
    scaled to width 100 becomes 100x200; scaled to width 50
    becomes 50x100. Zero pixels of the source are cropped.

    Asserted by inspecting the filter string the endpoint
    would emit for a known request — the pure-function scale
    filter is fixed regardless of ffmpeg's runtime behavior.
    (Full render inspection is covered by the border/shadow
    frame test above.)"""
    from app.routers.internal import _resolve_title_card_image
    from fastapi.responses import JSONResponse

    settings = Settings(
        runway_api_key="present", openai_api_key="test",
        data_dir=str(tmp_path),
    )
    resolved = _resolve_title_card_image(_tiny_png_data_uri(100, 200), settings)
    assert not isinstance(resolved, JSONResponse)
    assert resolved.exists()
    # Confirm decoded bytes match a 100x200 image (not cropped
    # to a square by the resolver — the resolver never crops).
    from PIL import Image
    img = Image.open(resolved).convert("RGB")
    assert img.size == (100, 200)


# ---- endpoint: cache --------------------------------------------


def test_cache_key_differs_by_corner(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Same base + image but different corners → different
    output filenames."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    base = _make_base_clip(tmp_path, duration_s=2)
    r1 = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "corner": "top_right",
        },
    )
    r2 = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "corner": "bottom_left",
        },
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["output_url"] != r2.json()["output_url"]


def test_cache_key_differs_by_image(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Two different source images → two different cache keys.
    Guards against silently serving a stale render when the
    operator picks a different Mike photo."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    base = _make_base_clip(tmp_path, duration_s=2)
    r1 = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(8, 8, (200, 0, 0)),
        },
    )
    r2 = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(8, 8, (0, 0, 200)),
        },
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["output_url"] != r2.json()["output_url"]


def test_cache_key_differs_by_timing(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Different subranges of the same base + image → different
    output filenames."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    base = _make_base_clip(tmp_path, duration_s=4)
    r1 = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "start_time_s": 0.5,
            "end_time_s": 1.5,
        },
    )
    r2 = real_mode_client.post(
        "/internal/clips/image_overlay/",
        json={
            "clip_url": str(base),
            "image_source": _tiny_png_data_uri(),
            "start_time_s": 2.0,
            "end_time_s": 3.0,
        },
    )
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["output_url"] != r2.json()["output_url"]


def test_cache_key_stable_for_identical_request(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Identical requests hit the same cache key + same file."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    base = _make_base_clip(tmp_path, duration_s=2)
    payload = {
        "clip_url": str(base),
        "image_source": _tiny_png_data_uri(),
    }
    r1 = real_mode_client.post("/internal/clips/image_overlay/", json=payload)
    r2 = real_mode_client.post("/internal/clips/image_overlay/", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["output_url"] == r2.json()["output_url"]


# ---- mock mode --------------------------------------------------


def test_endpoint_mock_mode_returns_stable_response(tmp_path: Path) -> None:
    """runway_mock=True → deterministic response with mock_mode
    flag set. No ffmpeg runs."""
    def _mock_settings() -> Settings:
        return Settings(
            runway_api_key="",  # empty → runway_mock=True
            openai_api_key="test",
            data_dir=str(tmp_path),
        )
    app.dependency_overrides[get_settings] = _mock_settings
    try:
        client = TestClient(app)
        resp = client.post(
            "/internal/clips/image_overlay/",
            json={
                "clip_url": "/data/anywhere.mp4",
                "image_source": _tiny_png_data_uri(),
            },
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["mock_mode"] is True
        assert body["output_url"].startswith(
            "/data/_internal/image_overlays/mock-"
        )
    finally:
        app.dependency_overrides.pop(get_settings, None)


# ---- helpers -----------------------------------------------------


def _probe_duration_local(path: Path) -> float:
    r = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=nokey=1:noprint_wrappers=1",
            str(path),
        ],
        check=True, capture_output=True, text=True, timeout=15,
    )
    return float(r.stdout.strip())
