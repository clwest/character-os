"""V17.0 — ``POST /internal/clips/extend/`` endpoint surface.

SESSION 182 / V17.0. Operator-visible capability: extend a
rendered clip beyond Runway's per-render 10s ceiling via last-
frame-conditioned continuation.

Q-v17-1 surfaced during this slice (see
``VIDEO_COMPOSITION_V17_PROPOSAL.md`` §"Extend Video"): Runway's
``/v1/video_to_video`` only accepts ``gen4_aleph``. The V17
proposal's original framing (extend at video_to_video with
gen4_turbo / gen4.5) is not the API shape today. Pivot:
last-frame extraction + ``/v1/image_to_video`` gen4_turbo +
ffmpeg concat. This test file pins the pivoted shape.

Three test surfaces:

1. **Pure-function** — ``_extract_last_frame`` extracts a
   non-blank PNG from the source's tail. Uses lavfi-generated
   fixtures to stay fast.
2. **Mock-mode endpoint** — response shape + cache behaviour +
   validation errors.
3. **ffmpeg concat helper** — ``_extend_concat`` re-encodes
   source + new into one playable MP4 of the expected total
   duration.

Real-mode integration (Runway round-trip) is intentionally
omitted from the standard test pass — operator dogfood
validates it (same pattern V11 style_remix and V16
remove_background follow).
"""
from __future__ import annotations

import shutil
import subprocess
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import Settings, get_settings
from app.main import app
from app.routers.internal import (
    _EXTEND_MODEL,
    _extend_concat,
    _extract_last_frame,
    _has_audio_stream,
)


# ---- pure-function: last-frame extraction ------------------------


def _make_lavfi_clip(
    target: Path, *, duration_s: int = 3, color: str = "red",
    width: int = 1280, height: int = 720,
    with_audio: bool = True,
) -> Path:
    """Generate a tiny lavfi color clip.

    ``with_audio`` defaults True (anullsrc padded) so tests that
    don't care about the audio path don't have to think about
    it. **Pass ``with_audio=False`` to mirror Runway's actual
    output shape** — gen4_turbo and gen4.5 outputs are silent
    MP4s, so V17.2's concat chain hits two-silent-input
    territory in production. SESSION 182 V17.2 first-dogfood
    failed at ffmpeg exit 234 because the original silent-
    output case wasn't covered by any unit test."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    args = [
        "ffmpeg", "-y", "-loglevel", "error",
        "-f", "lavfi",
        "-i", f"color=c={color}:s={width}x{height}:r=30:d={duration_s}",
    ]
    if with_audio:
        args.extend([
            "-f", "lavfi",
            "-i", (
                f"anullsrc=channel_layout=stereo:sample_rate=48000:"
                f"d={duration_s}"
            ),
        ])
    args.extend([
        "-c:v", "libx264", "-pix_fmt", "yuv420p",
    ])
    if with_audio:
        args.extend(["-c:a", "aac", "-shortest"])
    args.extend(["-f", "mp4", str(target)])
    subprocess.run(args, check=True, capture_output=True, timeout=30)
    return target


def test_extract_last_frame_writes_png(tmp_path: Path) -> None:
    """Happy path: the helper produces a non-empty PNG file."""
    src = _make_lavfi_clip(tmp_path / "src.mp4")
    out = tmp_path / "last.png"
    _extract_last_frame(src, out)
    assert out.exists()
    assert out.stat().st_size > 0


def test_extract_last_frame_grabs_actual_end_color(
    tmp_path: Path,
) -> None:
    """The extracted frame must come from the END of the clip,
    not the beginning. Generate a clip whose second half is a
    distinct color (via concat of two single-color halves) and
    assert the extracted frame matches the END color.

    Regression guard: ``-sseof`` is the load-bearing flag — if
    it ever silently degrades to a positive ``-ss`` we'd grab
    the start frame instead, and the chain would condition on
    the wrong frame."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")

    first = _make_lavfi_clip(
        tmp_path / "first.mp4", color="red", duration_s=1,
    )
    second = _make_lavfi_clip(
        tmp_path / "second.mp4", color="blue", duration_s=1,
    )
    concat_list = tmp_path / "concat.txt"
    concat_list.write_text(
        f"file '{first.resolve()}'\nfile '{second.resolve()}'\n"
    )
    combined = tmp_path / "combined.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "concat", "-safe", "0",
            "-i", str(concat_list),
            "-c", "copy",
            str(combined),
        ],
        check=True, capture_output=True, timeout=30,
    )

    last_frame = tmp_path / "last.png"
    _extract_last_frame(combined, last_frame)

    from PIL import Image
    img = Image.open(last_frame).convert("RGB")
    # Center pixel: should be solid blue (the END color), not red.
    cx, cy = img.width // 2, img.height // 2
    pixel = img.getpixel((cx, cy))
    assert isinstance(pixel, tuple) and len(pixel) == 3
    r, g, b = pixel
    assert b > 100 and r < 80, (
        f"last frame center pixel is RGB=({r},{g},{b}); expected "
        "blue-dominant. ``-sseof`` likely degraded to ``-ss`` and "
        "grabbed the start frame."
    )


def test_extract_last_frame_raises_on_missing_source(
    tmp_path: Path,
) -> None:
    """A nonexistent source path surfaces ffmpeg's non-zero
    exit (CalledProcessError). The caller (the endpoint)
    catches it and returns 502."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    missing = tmp_path / "does-not-exist.mp4"
    out = tmp_path / "last.png"
    with pytest.raises(subprocess.CalledProcessError):
        _extract_last_frame(missing, out)


# ---- mock-mode endpoint ------------------------------------------


@pytest.fixture
def mock_client(tmp_path: Path) -> Iterator[TestClient]:
    """TestClient with runway_mock=True so the endpoint skips
    ffmpeg / Runway entirely and returns the synthetic shape."""
    def _settings_override() -> Settings:
        return Settings(
            runway_api_key="",  # blank → runway_mock=True
            openai_api_key="test",
            data_dir=str(tmp_path),
        )

    app.dependency_overrides[get_settings] = _settings_override
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_settings, None)


def test_mock_endpoint_returns_synthetic_shape(
    mock_client: TestClient,
) -> None:
    """Mock-mode response is deterministic + carries the new
    duration math (source + new segment). The shape contract is
    what V17.1's Django primitive will deserialize against."""
    resp = mock_client.post(
        "/internal/clips/extend/",
        json={
            "source_clip_url": "https://example.test/source.mp4",
            "prompt": "continuing the conversation outdoors",
            "duration": 5,
        },
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["mock_mode"] is True
    assert body["output_url"].startswith(
        "/data/_internal/extends/mock-"
    )
    assert body["output_url"].endswith(".mp4")
    assert body["source_duration_seconds"] == 10.0
    assert body["new_segment_duration_seconds"] == 5.0
    # Total = source + new — drives operator-facing cost forecasting
    # in V17.1's cost estimator.
    assert body["duration_seconds"] == 15.0
    assert body["task_id"].startswith("mock_extend_")
    assert body["size_bytes"] > 0


def test_mock_endpoint_cache_key_is_deterministic(
    mock_client: TestClient,
) -> None:
    """Same request twice → same cache key → same output_url.
    The cache key feeds idempotency in the real-mode path
    (operator retries don't pay Runway twice) so getting it
    right in mock mode is the early signal."""
    payload = {
        "source_clip_url": "https://example.test/source.mp4",
        "prompt": "same continuation",
        "duration": 5,
        "seed": 42,
    }
    r1 = mock_client.post("/internal/clips/extend/", json=payload)
    r2 = mock_client.post("/internal/clips/extend/", json=payload)
    assert r1.status_code == 200
    assert r2.status_code == 200
    assert r1.json()["output_url"] == r2.json()["output_url"]
    assert r1.json()["task_id"] == r2.json()["task_id"]


def test_mock_endpoint_cache_key_changes_with_prompt(
    mock_client: TestClient,
) -> None:
    """Different prompt → different cache key → different
    output_url. The cache MUST include prompt content; a
    cache hit on different prompts would silently return the
    wrong extended clip."""
    base = {
        "source_clip_url": "https://example.test/source.mp4",
        "duration": 5,
    }
    r1 = mock_client.post(
        "/internal/clips/extend/", json={**base, "prompt": "outdoors"},
    )
    r2 = mock_client.post(
        "/internal/clips/extend/", json={**base, "prompt": "indoors"},
    )
    assert r1.json()["output_url"] != r2.json()["output_url"]


def test_mock_endpoint_cache_key_changes_with_source(
    mock_client: TestClient,
) -> None:
    """Different source_clip_url → different cache key. This is
    the Q-v17-4 resolution at the implementation layer: cache
    MUST be source-aware or a fresh source with stale cache
    silently returns the wrong extended clip."""
    base = {"prompt": "anything", "duration": 5}
    r1 = mock_client.post(
        "/internal/clips/extend/",
        json={**base, "source_clip_url": "https://example.test/a.mp4"},
    )
    r2 = mock_client.post(
        "/internal/clips/extend/",
        json={**base, "source_clip_url": "https://example.test/b.mp4"},
    )
    assert r1.json()["output_url"] != r2.json()["output_url"]


def test_endpoint_rejects_invalid_duration(
    mock_client: TestClient,
) -> None:
    """Per-model policy (gen4_turbo: 5s only) is enforced before
    Runway sees the request. The validator runs in mock mode
    too — bad requests fail fast regardless of env."""
    resp = mock_client.post(
        "/internal/clips/extend/",
        json={
            "source_clip_url": "https://example.test/source.mp4",
            "prompt": "continuing",
            "duration": 8,  # gen4_turbo only accepts 5s
        },
    )
    # Pydantic accepts 5-10 (the schema's bounds); the model
    # policy then rejects 8s for gen4_turbo. The contract error
    # shape uses ``code`` for the machine-readable identifier
    # and ``error`` for the human message (see ``_error()``
    # helper in internal.py).
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "invalid_settings"


def test_endpoint_rejects_invalid_ratio(
    mock_client: TestClient,
) -> None:
    """gen4_turbo accepts 1280:720, 720:1280, 960:960 only."""
    resp = mock_client.post(
        "/internal/clips/extend/",
        json={
            "source_clip_url": "https://example.test/source.mp4",
            "prompt": "continuing",
            "duration": 5,
            "ratio": "1920:1080",  # not in gen4_turbo policy
        },
    )
    assert resp.status_code == 400, resp.text
    assert resp.json()["code"] == "invalid_settings"


def test_endpoint_pydantic_rejects_oversize_duration(
    mock_client: TestClient,
) -> None:
    """Schema bound enforces 5 ≤ duration ≤ 10. Pydantic 422
    fires before the policy validator. Defense in depth."""
    resp = mock_client.post(
        "/internal/clips/extend/",
        json={
            "source_clip_url": "https://example.test/source.mp4",
            "prompt": "continuing",
            "duration": 30,  # past the schema ceiling
        },
    )
    assert resp.status_code == 422


# ---- ffmpeg concat helper ----------------------------------------


def test_extend_concat_produces_summed_duration(
    tmp_path: Path,
) -> None:
    """``_extend_concat`` welds source + new into one MP4 whose
    duration is the sum of the inputs. ffprobe confirms.

    Re-encode (not -c copy) is load-bearing — Runway output's
    codec params drift from local source params often enough
    that copy-mode concat fails opaquely. The re-encode keeps
    the operator's experience predictable at the cost of one
    extra ffmpeg pass."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    source = _make_lavfi_clip(tmp_path / "source.mp4", duration_s=2)
    new = _make_lavfi_clip(tmp_path / "new.mp4", duration_s=3)
    out = tmp_path / "combined.mp4"

    _extend_concat(source, new, out)

    assert out.exists()
    assert out.stat().st_size > 0

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(out),
        ],
        capture_output=True, text=True, timeout=15,
    )
    total = float(probe.stdout.strip())
    # 2s + 3s = 5s — allow a small margin for encoder rounding.
    assert 4.8 <= total <= 5.2, (
        f"concatenated duration {total:.2f}s is not ~5s; "
        "the concat filter may have dropped a stream."
    )


def test_extend_concat_handles_mismatched_source_dims(
    tmp_path: Path,
) -> None:
    """Real-world failure mode: the source is whatever the
    operator rendered earlier (might be 1088x704 from a Runway
    avatar) and the new clip from gen4_turbo is 1280x720. The
    concat filter handles dim mismatch by re-encoding both
    through the same pipeline. Validates the seam doesn't
    fall through into copy-mode concat where mismatched dims
    explode."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    source = _make_lavfi_clip(
        tmp_path / "source.mp4", duration_s=2, width=1088, height=704,
    )
    new = _make_lavfi_clip(
        tmp_path / "new.mp4", duration_s=2, width=1280, height=720,
    )
    out = tmp_path / "combined.mp4"

    # ffmpeg's concat filter requires matched dims; the helper
    # handles this either by re-encoding both inputs through the
    # same filter chain (current implementation) or by failing
    # loudly. Either is acceptable — silently producing a broken
    # MP4 is not.
    try:
        _extend_concat(source, new, out)
    except subprocess.CalledProcessError as exc:
        # Loud failure is acceptable behaviour for this v1 of the
        # concat helper. V17.2 (cinematic_visual_extended recipe)
        # will tighten this by enforcing same-dim sources before
        # the concat fires.
        stderr = exc.stderr or ""
        # ffmpeg's actual error string for the dim mismatch:
        # ``parameters (size WxH ...) do not match the
        # corresponding output link in0:v0 parameters``. Any
        # variation on "parameters do not match" / "size" /
        # "Width and height" / "same" is a recognisable
        # dim-mismatch signature.
        assert any(
            signal in stderr
            for signal in (
                "do not match",
                "Width and height",
                "same",
            )
        ), (
            f"concat failed for a non-dim reason — investigate: "
            f"{stderr[:300]}"
        )
        return

    # If it succeeded (current implementation does), the output
    # must be a valid playable MP4 with the summed duration.
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(out),
        ],
        capture_output=True, text=True, timeout=15,
    )
    total = float(probe.stdout.strip())
    assert 3.8 <= total <= 4.2


# ---- audio probe + silent-input concat (V17.2 dogfood regression)


def test_has_audio_stream_detects_audio_clip(tmp_path: Path) -> None:
    """Sanity — the helper finds audio when it's there."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")
    clip = _make_lavfi_clip(
        tmp_path / "with-audio.mp4", duration_s=1, with_audio=True,
    )
    assert _has_audio_stream(clip) is True


def test_has_audio_stream_detects_silent_clip(tmp_path: Path) -> None:
    """The Runway production case — gen4_turbo + gen4.5 outputs
    are silent MP4s. The probe must return False so the
    concat path takes the video-only branch.

    Regression guard: SESSION 182 V17.2 first-dogfood failed
    here. Both inputs were silent (Runway-generated), the
    pre-fix concat filter requested ``a=1`` on the output, and
    ffmpeg exited 234 because no input stream could feed the
    audio output."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")
    clip = _make_lavfi_clip(
        tmp_path / "silent.mp4", duration_s=1, with_audio=False,
    )
    assert _has_audio_stream(clip) is False


def test_extend_concat_handles_two_silent_inputs(tmp_path: Path) -> None:
    """**The dogfood-surfaced case.** V17.2 in production hits
    this every time: source and new clip both come from Runway
    (silent). Concat must succeed and produce a playable MP4
    of the summed duration. The pre-SESSION-182-fix concat
    filter requested ``a=1`` from two silent inputs and
    blew up with ffmpeg exit 234. The fix probes audio and
    takes the video-only branch when neither input has it."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")

    source = _make_lavfi_clip(
        tmp_path / "src-silent.mp4", duration_s=2, with_audio=False,
    )
    new = _make_lavfi_clip(
        tmp_path / "new-silent.mp4", duration_s=3, with_audio=False,
    )
    out = tmp_path / "combined.mp4"
    _extend_concat(source, new, out)

    assert out.exists()
    assert out.stat().st_size > 0
    # Output must be playable video; ffprobe should report ~5s.
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            str(out),
        ],
        capture_output=True, text=True, timeout=15,
    )
    total = float(probe.stdout.strip())
    assert 4.8 <= total <= 5.2, (
        f"silent-input concat produced {total:.2f}s output; expected ~5s"
    )
    # And there should be NO audio stream on the output (we asked
    # for video-only).
    assert _has_audio_stream(out) is False


def test_extend_concat_drops_audio_on_mismatched_inputs(
    tmp_path: Path,
) -> None:
    """Defensive: if the source has audio but the new clip
    doesn't (or vice versa), the concat falls into video-only
    mode rather than failing. This is the V17.5 forward path —
    extending a talking-head clip (audio) with a Runway visual
    extend (silent). v1 drops audio rather than padding with
    anullsrc; richer audio handling can come later."""
    if not shutil.which("ffmpeg") or not shutil.which("ffprobe"):
        pytest.skip("ffmpeg/ffprobe not on PATH")

    source_with_audio = _make_lavfi_clip(
        tmp_path / "src-audio.mp4", duration_s=2, with_audio=True,
    )
    new_silent = _make_lavfi_clip(
        tmp_path / "new-silent.mp4", duration_s=2, with_audio=False,
    )
    out = tmp_path / "combined.mp4"
    _extend_concat(source_with_audio, new_silent, out)

    assert out.exists()
    # No audio on the output — v1 simplification.
    assert _has_audio_stream(out) is False


# ---- contract pin ------------------------------------------------


def test_extend_model_pinned_to_gen4_turbo() -> None:
    """Pin the model choice to gen4_turbo. Pivot from the
    original V17 proposal (which guessed video_to_video with
    gen4_turbo / gen4.5 — Q-v17-1 surfaced that endpoint only
    accepts gen4_aleph). The implementation lives at
    image_to_video; the model MUST be gen4_turbo so the
    per-model policy validator (5s only, image_required=True)
    matches what the endpoint actually sends."""
    assert _EXTEND_MODEL == "gen4_turbo"
