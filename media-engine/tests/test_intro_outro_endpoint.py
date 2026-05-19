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
    _DRAWTEXT_FONT_CANDIDATES,
    _build_card_filter,
    _probe_dimensions,
    _resolve_drawtext_font,
)


# ---- pure-function: filter graph references textfile -------------


def _filter_for(text: str, textfile: Path) -> str:
    """Helper — write text to file, build the filter that
    references it. Card text never enters the filter string
    directly any more (the textfile= pattern sidesteps the
    apostrophe / colon / backslash escape footguns drawtext's
    in-filter parser introduces)."""
    textfile.write_text(text, encoding="utf-8")
    spec = TitleCardSpec(text=text)
    return _build_card_filter(
        spec, 1280, 720, "[1:v]", "[intro_v]", textfile,
    )


def test_filter_uses_textfile_not_text_argument(
    tmp_path: Path,
) -> None:
    """The filter references the on-disk text path via
    ``textfile=`` — drawtext reads literal bytes and doesn't
    apply its in-filter text-escape rules. Card text with
    apostrophes / colons / quotes flows through unscathed.

    Regression guard: SESSION 180 dogfood produced four
    successive escape attempts (POSIX close-escape-reopen,
    octal, backslash, plain) — all of which silently rendered
    blank cards once fontfile= was added to the same filter.
    ``textfile=`` is the only escape-immune option."""
    out = _filter_for(
        "Riggs's Rules.", tmp_path / "intro.txt",
    )
    assert "textfile=" in out
    # The raw card text MUST NOT appear in the filter string —
    # if it did, we'd be back in the escape-game that SESSION
    # 180 spent four attempts trying to win.
    assert "Riggs" not in out


def test_filter_textfile_path_escapes_colons(
    tmp_path: Path,
) -> None:
    """Filter-argument-level escaping still applies to the
    textfile PATH (colons split filter options); the path
    must be backslash-escaped even though the text inside the
    file is left alone."""
    fixture_dir = tmp_path / "weird:dir"
    fixture_dir.mkdir()
    fixture = fixture_dir / "intro.txt"
    out = _filter_for("Whatever", fixture)
    # Backslash-escaped colon survives in the produced filter.
    assert r"weird\:dir" in out


def test_textfile_can_hold_apostrophes_and_colons_unchanged(
    tmp_path: Path,
) -> None:
    """The literal text written to disk is exactly what the
    operator supplied — drawtext's ``textfile=`` reads it
    verbatim. This is the *whole point* of the textfile path:
    no escape rules apply to the content."""
    fixture = tmp_path / "intro.txt"
    _filter_for("Don't: \"break\" me\\now", fixture)
    assert fixture.read_text() == "Don't: \"break\" me\\now"


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


# ---- drawtext font resolver --------------------------------------


def test_font_resolver_returns_existing_path(monkeypatch) -> None:
    """At least one candidate exists on the dev box; the
    resolver returns it. Tests that ship in CI environments
    without any candidate font would need to install one or
    set the env override."""
    monkeypatch.delenv("MEDIA_ENGINE_DRAWTEXT_FONT", raising=False)
    path = _resolve_drawtext_font()
    assert Path(path).exists()
    assert path in _DRAWTEXT_FONT_CANDIDATES


def test_font_resolver_honors_env_override(
    monkeypatch, tmp_path: Path,
) -> None:
    """Operators in containers / non-standard environments
    point ``MEDIA_ENGINE_DRAWTEXT_FONT`` at their own font."""
    custom = tmp_path / "custom-font.ttf"
    custom.write_bytes(b"\x00")
    monkeypatch.setenv("MEDIA_ENGINE_DRAWTEXT_FONT", str(custom))
    assert _resolve_drawtext_font() == str(custom)


def test_font_resolver_ignores_nonexistent_env_override(
    monkeypatch, tmp_path: Path,
) -> None:
    """A misconfigured env var (pointing at nothing) shouldn't
    poison the resolver — fall through to the candidate list."""
    monkeypatch.setenv(
        "MEDIA_ENGINE_DRAWTEXT_FONT",
        str(tmp_path / "does-not-exist.ttf"),
    )
    path = _resolve_drawtext_font()
    assert Path(path).exists()  # falls through to candidates


def test_font_resolver_raises_when_nothing_found(monkeypatch) -> None:
    """Fail loud rather than silently render blank cards.
    SESSION 180 trigger: pre-fix, drawtext-without-fontfile
    produced pure-black output and the endpoint returned 200
    — the operator only discovered the issue on playback."""
    monkeypatch.delenv("MEDIA_ENGINE_DRAWTEXT_FONT", raising=False)
    monkeypatch.setattr(
        "app.routers.internal._DRAWTEXT_FONT_CANDIDATES",
        (),
    )
    with pytest.raises(RuntimeError, match="no usable font found"):
        _resolve_drawtext_font()


def test_card_filter_embeds_resolved_fontfile(
    tmp_path: Path,
) -> None:
    """``fontfile=`` is non-optional in the produced filter
    string. Without it, drawtext silently renders nothing on
    most builds even when libfreetype + libfontconfig are
    linked."""
    spec = TitleCardSpec(text="Hi")
    textfile = tmp_path / "intro.txt"
    textfile.write_text("Hi")
    out = _build_card_filter(
        spec, 1280, 720, "[1:v]", "[intro_v]", textfile,
    )
    assert "fontfile=" in out


# ---- end-to-end: rendered text is actually visible ---------------


def test_intro_frame_has_visible_text_not_pure_black(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Regression guard against the SESSION 180 blank-card bug.
    Uses the OPERATOR-REPORTED payload shape: apostrophe-bearing
    text on a non-default-sized body clip. The dual-card path
    returned 200 + reasonable byte counts at multiple iterations
    of escape attempts (POSIX close-escape-reopen / octal /
    backslash) — but in every case the actual rendered intro
    frame was pure black until the implementation switched to
    drawtext ``textfile=``. Probe a real frame and require
    visible bright pixels."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            # Apostrophe-bearing text — the exact failure mode
            # SESSION 180's operator dogfood surfaced.
            "intro": {"text": "Riggs's Rules.", "duration_s": 1.0},
            "outro": {"text": "Don't blink.", "duration_s": 1.0},
        },
    )
    assert resp.status_code == 200, resp.text
    output_url = resp.json()["output_url"]
    output_rel = output_url[len("/data/"):]
    output_path = tmp_path / output_rel
    assert output_path.exists()

    # Extract a frame from the intro segment (0.5s — middle of
    # the 1-second intro card so we miss any encoder boundary
    # artifact at t=0).
    intro_frame = tmp_path / "intro-probe.png"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", "0.5", "-i", str(output_path),
            "-frames:v", "1", "-update", "1", str(intro_frame),
        ],
        check=True, capture_output=True, timeout=30,
    )

    from PIL import Image
    img = Image.open(intro_frame).convert("RGB")
    pixels = img.getdata()
    # White-text-on-black: count pixels brighter than mid-grey
    # in any channel. A pure-black frame has zero; any rendered
    # text contributes thousands.
    bright = sum(
        1 for r, g, b in pixels
        if max(r, g, b) > 128
    )
    assert bright > 500, (
        f"intro frame appears blank ({bright} bright pixels); "
        "drawtext likely failed to render text. Most common "
        "cause: text= reverted from textfile= (apostrophe + "
        "fontfile in the same filter is a known dead end)."
    )
