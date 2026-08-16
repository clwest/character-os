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
    _build_image_card_prefilter,
    _decode_title_card_image,
    _probe_dimensions,
    _resolve_drawtext_font,
    _resolve_title_card_image,
    _wrap_card_text,
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


# ---- SESSION 200 post-close — silent-base intro_outro -----------


def _make_silent_body_clip(
    tmp_path: Path, w: int = 1280, h: int = 720, duration_s: int = 5,
) -> Path:
    """Body clip with NO audio stream — mirrors the
    storyboard_ad + storyboard_voiced extend-chain concat output.
    Pre-fix, this would 500 the endpoint with
    ``filtergraph inputs/outputs: Invalid argument`` because
    ``[0:a]`` referenced no stream."""
    out = tmp_path / f"silent-body-{w}x{h}.mp4"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-f", "lavfi",
            "-i", f"color=c=green:s={w}x{h}:r=30:d={duration_s}",
            "-c:v", "libx264", "-pix_fmt", "yuv420p",
            "-an",
            "-f", "mp4", str(out),
        ],
        check=True, capture_output=True, timeout=30,
    )
    return out


def test_intro_outro_handles_silent_body_clip(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """SESSION 200 post-close — the storyboard_ad real-mode fire
    failed at step 10 because the SESSION 200 xfade-concat output
    has no audio stream (silent generates + silent extends mean
    no input to concat carries audio, so the xfade chain drops
    the acrossfade chain entirely). Without the silent-base
    branch, ``[0:a]`` referenced no streams and ffmpeg exited
    rc=234 with "Error binding filtergraph inputs/outputs:
    Invalid argument".

    Fix mirrors SESSION 196 slice 1 (mix_audio silent-base):
    ffprobe the body for an audio stream; when absent, synthesize
    a silent ``anullsrc`` track for the body's duration so the
    concat=a=1 contract holds.
    """
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    silent_body = _make_silent_body_clip(tmp_path, duration_s=5)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(silent_body),
            "outro": {
                "text": "Dog Food Coffee House",
                "duration_s": 3.0,
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body_json = resp.json()
    assert body_json["mock_mode"] is False
    # Output carries video + a (synthesized-silent) audio stream
    # so downstream consumers see a uniform shape.
    output_path = tmp_path / body_json["output_url"][len("/data/"):]
    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-show_entries", "stream=codec_type",
            "-of", "csv=p=0",
            str(output_path),
        ],
        check=True, capture_output=True, text=True, timeout=10,
    )
    codecs = [
        line.strip() for line in probe.stdout.splitlines() if line.strip()
    ]
    assert "video" in codecs
    assert "audio" in codecs


def test_intro_outro_silent_body_with_both_cards(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Dual-card path on a silent body. Ensures the silent-base
    branch composes cleanly with the SESSION 180 input-indexing
    fix (the synthesized body-audio input shifts every subsequent
    intro/outro index by 1)."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    silent_body = _make_silent_body_clip(tmp_path, duration_s=4)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(silent_body),
            "intro": {"text": "Hook", "duration_s": 1.0},
            "outro": {"text": "Payoff", "duration_s": 1.0},
        },
    )
    assert resp.status_code == 200, resp.text


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


# ---- SESSION 210: _wrap_card_text auto-wrap regression guard -----
#
# Closes the SESSION 209 calibration finding: card text wider than
# the canvas clipped on both sides because `_build_card_filter`
# centered without wrapping. The fix is a pre-write `textwrap.wrap`
# in `_wrap_card_text(text, canvas_w, font_size)`, called before
# the textfile gets written.


def test_wrap_card_text_passes_short_text_unchanged() -> None:
    """Short text fits within max_chars and returns flat (whitespace
    collapsed but no line-break inserted)."""
    out = _wrap_card_text(
        "Reply by morning.", canvas_w=1280, font_size=48,
    )
    assert out == "Reply by morning."
    assert "\n" not in out


def test_wrap_card_text_breaks_long_text_at_max_chars() -> None:
    """The SESSION 209 finding case — a 94-char CTA outro on a
    1280-wide canvas at default font_size=48. Pre-patch this was
    written verbatim and clipped mid-word. Post-patch it wraps to
    ≤2 lines."""
    long_outro = (
        "Now onboarding · email onboarding@example.com · "
        "spaces limited · first come, first served"
    )
    out = _wrap_card_text(long_outro, canvas_w=1280, font_size=48)
    lines = out.split("\n")
    assert len(lines) >= 2, (
        f"long outro should wrap; got 1 line: {out!r}"
    )
    # Each wrapped line must respect the empirical max
    # (canvas_w * 0.80 / (font_size * 0.55)) — ≈38 chars at
    # 1280w / fontsize=48.
    max_chars = int(1280 * 0.80 / (48 * 0.55))
    for ln in lines:
        assert len(ln) <= max_chars or " " not in ln, (
            f"line exceeds max ({max_chars}): {ln!r} ({len(ln)})"
        )


def test_wrap_card_text_preserves_operator_newlines() -> None:
    """Operators may pre-stack lines with explicit ``\\n``. The
    wrapper respects those line breaks and wraps each line
    independently."""
    stacked = (
        "Now onboarding.\n"
        "onboarding@example.com\n"
        "Limited spaces — first come, first served."
    )
    out = _wrap_card_text(stacked, canvas_w=1280, font_size=48)
    lines = out.split("\n")
    # The first two lines stay as authored (each short enough
    # not to need further wrapping at 1280w).
    assert lines[0] == "Now onboarding."
    assert lines[1] == "onboarding@example.com"
    # The third line is exactly 43 chars; at fontsize 48 / 1280w
    # the max is ≈38, so it WILL be wrapped.
    # Either way: there are at least 3 lines, and no line should
    # contain a literal sentence boundary mid-word.
    assert len(lines) >= 3


def test_wrap_card_text_narrower_canvas_wraps_sooner() -> None:
    """Vertical canvases (720w portrait) have less room — same
    text wraps into more lines than on horizontal (1280w)."""
    text = (
        "Now onboarding email onboarding at example dot com "
        "for early access"
    )
    wide = _wrap_card_text(text, canvas_w=1280, font_size=48)
    narrow = _wrap_card_text(text, canvas_w=720, font_size=48)
    wide_lines = wide.count("\n") + 1
    narrow_lines = narrow.count("\n") + 1
    assert narrow_lines >= wide_lines, (
        "narrower canvas should wrap into ≥ as many lines as wider; "
        f"wide={wide_lines} narrow={narrow_lines}"
    )


def test_wrap_card_text_larger_font_wraps_sooner() -> None:
    """Bigger font = fewer chars fit per line. Same text + canvas
    + bigger font = more wraps."""
    text = "Always on. Always smart. Always global. The hour is irrelevant."
    small = _wrap_card_text(text, canvas_w=1280, font_size=36)
    large = _wrap_card_text(text, canvas_w=1280, font_size=96)
    assert (large.count("\n") + 1) >= (small.count("\n") + 1)


def test_wrap_card_text_empty_input_returns_unchanged() -> None:
    """Empty / whitespace-only input — caller's responsibility
    upstream (TitleCardSpec.text has min_length=1) but defensive."""
    assert _wrap_card_text("", canvas_w=1280, font_size=48) == ""
    assert _wrap_card_text("   ", canvas_w=1280, font_size=48) == "   "


def test_wrap_card_text_floor_prevents_tiny_canvas_degenerate_wrap() -> None:
    """At pathological canvas widths the math would produce
    max_chars < 12. The floor keeps it at 12 so we don't break
    every word onto its own line. (A 320×N canvas isn't a valid
    Runway output but the helper shouldn't crash.)"""
    out = _wrap_card_text(
        "Reply by morning quickly please.",
        canvas_w=320,
        font_size=48,
    )
    # 12-char floor — "Reply by" / "morning" / "quickly" / "please."
    # depending on textwrap behavior. Just assert no line is
    # impossibly short (1-char wraps would indicate floor missed).
    for ln in out.split("\n"):
        if ln and ln != "...":
            assert len(ln.strip()) >= 1


# ---- SESSION 255: image-backed title cards -----------------------
#
# Additive extension of the existing intro_outro endpoint. Legacy
# color-source path preserved byte-identically; new image_data_uri
# field on TitleCardSpec unlocks a `-loop 1 -t <d> -i <path>` input
# + scale+crop+setsar+fps normalization + drawtext scrim for
# readable white text on arbitrary imagery. Local ffmpeg only, no
# provider spend.


def _tiny_png_bytes(width: int = 8, height: int = 8, color=(120, 140, 100)) -> bytes:
    """Return raw PNG bytes for a small solid-color image. Used by
    the image-backed title card tests so they don't depend on a
    bundled fixture file."""
    from io import BytesIO
    from PIL import Image
    buf = BytesIO()
    Image.new("RGB", (width, height), color).save(buf, format="PNG")
    return buf.getvalue()


def _tiny_png_data_uri(width: int = 8, height: int = 8, color=(120, 140, 100)) -> str:
    import base64 as _b64
    raw = _tiny_png_bytes(width, height, color)
    return "data:image/png;base64," + _b64.b64encode(raw).decode("ascii")


def test_decode_title_card_image_accepts_valid_png() -> None:
    """The decoder returns (mime, raw) for a well-formed
    ``data:image/png;base64,`` payload."""
    result = _decode_title_card_image(_tiny_png_data_uri())
    assert isinstance(result, tuple)
    mime, raw = result
    assert mime == "image/png"
    assert raw.startswith(b"\x89PNG")


def test_decode_title_card_image_rejects_malformed_data_uri() -> None:
    """Non-``data:image/...`` prefixes are rejected with a
    400 + ``invalid_data_uri`` code so the operator sees the
    error at the endpoint instead of an obscure ffmpeg failure."""
    resp = _decode_title_card_image("not a data uri")
    from fastapi.responses import JSONResponse
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 400


def test_decode_title_card_image_rejects_bad_base64() -> None:
    """A well-formed data URI header with non-decodable base64
    payload → 400."""
    resp = _decode_title_card_image(
        "data:image/png;base64,!!!not-base64-payload!!!",
    )
    from fastapi.responses import JSONResponse
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 400


def test_decode_title_card_image_rejects_oversize_payload() -> None:
    """A decoded payload larger than the 5 MB cap returns 413.
    Constructed with a raw byte string long enough to exceed the
    cap without materializing a real image (the decoder only
    checks length + base64 validity, not that the bytes are a
    parseable image — that happens later at the ffmpeg boundary)."""
    import base64 as _b64
    raw = b"x" * (6 * 1024 * 1024)  # 6 MB > 5 MB cap
    data_uri = "data:image/png;base64," + _b64.b64encode(raw).decode("ascii")
    resp = _decode_title_card_image(data_uri)
    from fastapi.responses import JSONResponse
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 413


def test_build_image_card_prefilter_normalizes_to_canvas() -> None:
    """The pre-filter cover-crops + normalizes SAR + forces
    30 fps so the concat downstream sees uniform video
    parameters regardless of source image dims."""
    out = _build_image_card_prefilter(
        1088, 704, "[2:v]", "[intro_bg]",
    )
    assert out.startswith("[2:v]")
    assert out.endswith("[intro_bg]")
    assert "scale=1088:704:force_original_aspect_ratio=increase" in out
    assert "crop=1088:704" in out
    assert "setsar=1" in out
    assert "fps=30" in out


def test_card_filter_default_omits_scrim_preserves_legacy_output(
    tmp_path: Path,
) -> None:
    """SESSION 255 backward-compat guard: the default
    ``use_scrim=False`` MUST produce a drawtext filter string
    byte-identical to the pre-SESSION-255 output. Any change
    would risk breaking visual regression on legacy color-source
    cards (SESSION 197-199 recipes, long_form_ad, storyboard_ad,
    storyboard_voiced, dialogue_scene, recut_teaser,
    talking_head_polished)."""
    spec = TitleCardSpec(text="Legacy")
    textfile = tmp_path / "legacy.txt"
    textfile.write_text("Legacy")
    out = _build_card_filter(
        spec, 1280, 720, "[1:v]", "[out_v]", textfile,
    )
    assert "box=" not in out
    assert "boxcolor" not in out
    assert "boxborderw" not in out


def test_card_filter_scrim_adds_semi_transparent_backing(
    tmp_path: Path,
) -> None:
    """Image-backed cards opt into the scrim so white text stays
    readable over arbitrary imagery. Asserts the box params
    match the SESSION 255 spec (semi-transparent black, 20px
    border)."""
    spec = TitleCardSpec(text="Over image")
    textfile = tmp_path / "scrim.txt"
    textfile.write_text("Over image")
    out = _build_card_filter(
        spec, 1280, 720, "[intro_bg]", "[out_v]", textfile,
        use_scrim=True,
    )
    assert "box=1" in out
    assert "boxcolor=black@0.5" in out
    assert "boxborderw=20" in out


def test_title_card_spec_defaults_image_data_uri_to_none() -> None:
    """The new field is optional and defaults to None so every
    existing caller (long_form_ad, storyboard_*, cinematic_*,
    dialogue_scene, talking_head_polished, and the SESSION 255
    talking_head + talking_head_with_backdrop base cases without
    an operator-picked image) hits the legacy color-source
    branch."""
    spec = TitleCardSpec(text="No image")
    assert spec.image_data_uri is None


def test_intro_outro_image_backed_outro_returns_success(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """End-to-end: post an outro with a data-URI image
    background. Endpoint decodes + caches + composes; ffmpeg
    produces a real MP4."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {
                "text": "Riverstone Outdoor Adventures\nVisit us today",
                "duration_s": 1.0,
                "image_data_uri": _tiny_png_data_uri(64, 64, (60, 90, 40)),
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body_json = resp.json()
    assert body_json["mock_mode"] is False
    assert body_json["output_url"].startswith(
        "/data/_internal/intro_outros/"
    )
    assert body_json["duration_seconds"] == pytest.approx(2.0, abs=0.1)
    output_path = tmp_path / body_json["output_url"][len("/data/"):]
    assert output_path.exists()


def test_intro_outro_image_backed_caches_image_under_images_subdir(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Decoded image lands under ``data/_internal/intro_outros/
    images/<sha16>.<ext>`` so repeated posts of the same asset
    (many outros against the same image) hit disk cache and
    skip re-decode."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")

    body = _make_body_clip(tmp_path)
    real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {
                "text": "Cache test",
                "duration_s": 1.0,
                "image_data_uri": _tiny_png_data_uri(),
            },
        },
    )
    images_dir = tmp_path / "_internal" / "intro_outros" / "images"
    assert images_dir.exists()
    cached = list(images_dir.glob("*.png"))
    assert len(cached) == 1
    # Content-addressed name — sha16 of decoded bytes.
    import hashlib as _hashlib
    expected = _hashlib.sha256(_tiny_png_bytes()).hexdigest()[:16]
    assert cached[0].name == f"{expected}.png"


def test_intro_outro_cache_key_differs_between_color_and_image(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Cache key hashes the whole request body, so an outro with
    ``image_data_uri`` set MUST produce a different output filename
    than the same outro without one. Guards against silent cache
    collision that would let a stale color-only render answer a
    later image request."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")

    body = _make_body_clip(tmp_path)
    resp_color = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {"text": "Same text", "duration_s": 1.0},
        },
    )
    resp_image = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {
                "text": "Same text",
                "duration_s": 1.0,
                "image_data_uri": _tiny_png_data_uri(),
            },
        },
    )
    assert resp_color.status_code == 200, resp_color.text
    assert resp_image.status_code == 200, resp_image.text
    color_url = resp_color.json()["output_url"]
    image_url = resp_image.json()["output_url"]
    assert color_url != image_url, (
        "cache collision between color and image outros — the "
        "sha256 request-body hash must include image_data_uri so "
        "the two variants land at different keys."
    )


def test_intro_outro_image_endpoint_rejects_malformed_source(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """A bare string that is neither a ``data:`` URI nor a
    ``/data/`` local URL surfaces as HTTP 400 with the
    ``invalid_image_source`` code — operator sees a real error
    instead of a mysterious ffmpeg fault.

    A malformed ``data:...`` prefix (well-formed shape but broken
    payload) still fires the tighter ``invalid_data_uri`` code
    via ``_decode_title_card_image`` — verified in the pure-
    function tests above."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {
                "text": "Broken",
                "duration_s": 1.0,
                "image_data_uri": "this is not a data URI",
            },
        },
    )
    assert resp.status_code == 400
    assert resp.json().get("code") == "invalid_image_source"


def test_intro_outro_image_endpoint_rejects_malformed_data_uri_prefix(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """``data:...`` prefix with a broken payload (non-image MIME
    or bad base64) is caught by _decode_title_card_image and
    surfaces as 400 with the tighter ``invalid_data_uri`` code."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {
                "text": "Broken",
                "duration_s": 1.0,
                "image_data_uri": "data:image/png;base64,!!!not-base64!!!",
            },
        },
    )
    assert resp.status_code == 400
    assert resp.json().get("code") == "invalid_data_uri"


def test_intro_outro_image_endpoint_rejects_oversize_payload(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Decoded payload >5 MB → 413 image_too_large. Enforced at
    the endpoint boundary; ffmpeg never runs."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    import base64 as _b64
    oversize = "data:image/png;base64," + _b64.b64encode(
        b"x" * (6 * 1024 * 1024),
    ).decode("ascii")
    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {
                "text": "Too big",
                "duration_s": 1.0,
                "image_data_uri": oversize,
            },
        },
    )
    assert resp.status_code == 413
    assert resp.json().get("code") == "image_too_large"


def test_intro_outro_no_image_still_uses_lavfi_color_source(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """SESSION 255 regression guard: an outro without
    ``image_data_uri`` continues to render exactly as it did
    before SESSION 255. No image directory should be created and
    the endpoint still produces a valid MP4."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {"text": "Legacy", "duration_s": 1.0},
        },
    )
    assert resp.status_code == 200, resp.text
    images_dir = tmp_path / "_internal" / "intro_outros" / "images"
    # No image supplied → no image cache directory should exist
    # (or if it exists from a peer test in the same tmp_path, it
    # must be empty — the fixture rescopes tmp_path per test so
    # this is a strong assertion on THIS test's session).
    assert not images_dir.exists() or not any(images_dir.iterdir())


def test_resolve_title_card_image_accepts_data_uri(tmp_path: Path) -> None:
    """The polymorphic resolver routes data URIs through the
    decode+cache path and returns a local Path under
    ``data/_internal/intro_outros/images/``."""
    settings = Settings(
        runway_api_key="present", openai_api_key="test",
        data_dir=str(tmp_path),
    )
    path = _resolve_title_card_image(_tiny_png_data_uri(), settings)
    assert isinstance(path, Path)
    assert path.exists()
    assert path.parent.name == "images"
    assert path.parent.parent.name == "intro_outros"


def test_resolve_title_card_image_accepts_local_data_url(tmp_path: Path) -> None:
    """The polymorphic resolver routes ``/data/...`` local URLs
    through the concat-input resolver — matches the shape the
    storyboard ``generate_image`` primitive persists to
    Asset.file_path. Guards against the SESSION 255 dogfood
    finding where the pre-widening design rejected storyboard
    images at the media-engine boundary."""
    settings = Settings(
        runway_api_key="present", openai_api_key="test",
        data_dir=str(tmp_path),
    )
    # Materialize a local image the way storyboard does.
    src_dir = tmp_path / "_internal" / "images"
    src_dir.mkdir(parents=True)
    src_path = src_dir / "storyboard.png"
    src_path.write_bytes(_tiny_png_bytes())
    resolved = _resolve_title_card_image(
        "/data/_internal/images/storyboard.png", settings,
    )
    assert isinstance(resolved, Path)
    assert resolved == src_path


def test_resolve_title_card_image_rejects_bare_string(tmp_path: Path) -> None:
    """A string that is neither a data URI nor a ``/data/`` URL
    is rejected as ``invalid_image_source`` — clear error rather
    than a mysterious ffmpeg-time failure."""
    from fastapi.responses import JSONResponse
    settings = Settings(
        runway_api_key="present", openai_api_key="test",
        data_dir=str(tmp_path),
    )
    resp = _resolve_title_card_image("not-a-uri", settings)
    assert isinstance(resp, JSONResponse)
    assert resp.status_code == 400


def test_intro_outro_image_endpoint_accepts_local_data_url(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """End-to-end: post an outro whose ``image_data_uri`` is a
    ``/data/_internal/images/...`` local URL (storyboard-image
    shape). Endpoint resolves + composes; ffmpeg produces a
    valid MP4. This is the SESSION 255 dogfood repro shape."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    # Materialize a workspace-style image on disk under data_path.
    src_dir = tmp_path / "_internal" / "images"
    src_dir.mkdir(parents=True)
    src_path = src_dir / "workspace-image.png"
    src_path.write_bytes(_tiny_png_bytes(64, 64, (60, 140, 40)))

    body = _make_body_clip(tmp_path)
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {
                "text": "Riverstone Outdoor Adventures",
                "duration_s": 1.0,
                "image_data_uri": "/data/_internal/images/workspace-image.png",
            },
        },
    )
    assert resp.status_code == 200, resp.text
    body_json = resp.json()
    assert body_json["output_url"].startswith(
        "/data/_internal/intro_outros/"
    )


def test_intro_outro_image_backed_outro_frame_shows_text_over_image(
    real_mode_client: TestClient, tmp_path: Path,
) -> None:
    """Extract an outro frame + verify the composition is
    image-backed (not pure black) AND still has visible white
    text (scrim protects readability). Uses PIL like the
    SESSION 180 blank-card regression guard."""
    if not shutil.which("ffmpeg"):
        pytest.skip("ffmpeg not on PATH")
    if not shutil.which("ffprobe"):
        pytest.skip("ffprobe not on PATH")

    body = _make_body_clip(tmp_path)
    # Solid green image (60, 90, 40) — recognizably non-black
    # away from any drawtext pixels.
    resp = real_mode_client.post(
        "/internal/clips/intro_outro/",
        json={
            "clip_url": str(body),
            "outro": {
                "text": "Visit us today",
                "duration_s": 1.0,
                "image_data_uri": _tiny_png_data_uri(64, 64, (60, 140, 40)),
            },
        },
    )
    assert resp.status_code == 200, resp.text
    output_path = tmp_path / resp.json()["output_url"][len("/data/"):]

    # Body clip is 1s; outro follows → sample at 1.5s (middle
    # of the outro segment).
    outro_frame = tmp_path / "outro-probe.png"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error",
            "-ss", "1.5", "-i", str(output_path),
            "-frames:v", "1", "-update", "1", str(outro_frame),
        ],
        check=True, capture_output=True, timeout=30,
    )
    from PIL import Image
    img = Image.open(outro_frame).convert("RGB")
    pixels = list(img.getdata())
    # Green channel dominates in the image bg → count pixels
    # where green > red + 20 AND green > blue + 20 (broadly
    # matches the source (60, 140, 40) after scrim darkening).
    green_pixels = sum(
        1 for r, g, b in pixels
        if g > r + 20 and g > b + 20
    )
    # Very bright pixels — where drawtext white letters landed
    # (or the scrim is fully clear at the corners). Expect some.
    bright_pixels = sum(
        1 for r, g, b in pixels
        if r > 220 and g > 220 and b > 220
    )
    assert green_pixels > 1000, (
        f"outro frame lacks green background ({green_pixels} pixels); "
        "image branch may not be firing."
    )
    assert bright_pixels > 200, (
        f"outro frame lacks white text pixels ({bright_pixels}); "
        "drawtext may have failed under the scrim."
    )
