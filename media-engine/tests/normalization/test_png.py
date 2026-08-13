"""Deterministic PNG encode / decode helpers (§10.6 anchor).

The §10.6 byte-for-byte-identical output guarantee rests on
Pillow's PNG writer producing the same bytes for the same
image under the pinned settings in ``png.encode_png``. This
suite asserts that guarantee against three input shapes:

* Synthetic RGBA images built directly in Pillow.
* Real portrait-provider mock output (the smallest real PNG
  the media-engine emits today).
* Round-tripped images (decode → encode) — proving the decode
  boundary normalizes mode without side effects.

If a future Pillow upgrade silently changes a default and one
of these tests starts to flap, the ``png`` module needs an
explicit pin — the pipeline invariant is more important than
the newer Pillow behavior.
"""
from __future__ import annotations

import io

import pytest
from PIL import Image

from app.services.normalization import BadPngError, PngEncodingError
from app.services.normalization.png import decode_png, dimensions_of, encode_png


def _make_rgba(width: int, height: int, rgba: tuple[int, int, int, int]) -> Image.Image:
    return Image.new("RGBA", (width, height), rgba)


def test_encode_png_is_deterministic_across_repeat_invocations() -> None:
    img = _make_rgba(64, 48, (200, 100, 50, 255))
    a = encode_png(img)
    b = encode_png(img)
    assert a == b


def test_encode_png_does_not_write_time_chunk() -> None:
    """PNG's ``tIME`` chunk is one of Pillow's classic drift
    surfaces. Assert it is absent from encoded bytes so a
    future upgrade that flips a default cannot silently break
    determinism.
    """
    img = _make_rgba(32, 32, (10, 20, 30, 255))
    payload = encode_png(img)
    assert b"tIME" not in payload


def test_encode_png_does_not_write_metadata_chunks() -> None:
    """Neither ICC profile, physical density (``pHYs``), gamma
    (``gAMA``), nor text (``tEXt``, ``iTXt``, ``zTXt``) may
    appear. If a source provider embedded any of these, they
    are dropped at the pipeline boundary.
    """
    img = _make_rgba(16, 16, (255, 0, 0, 255))
    payload = encode_png(img)
    for chunk in (b"iCCP", b"pHYs", b"gAMA", b"tEXt", b"iTXt", b"zTXt"):
        assert chunk not in payload, f"unexpected PNG chunk {chunk!r} in output"


def test_encode_png_requires_rgba_mode() -> None:
    img_rgb = Image.new("RGB", (16, 16), (128, 128, 128))
    with pytest.raises(PngEncodingError, match="RGBA"):
        encode_png(img_rgb)


def test_decode_png_normalizes_rgb_source_to_rgba() -> None:
    """The pipeline treats RGBA as the canonical in-memory
    shape. RGB input must be converted at the boundary so
    downstream stages don't need to branch on mode.
    """
    rgb_img = Image.new("RGB", (24, 24), (60, 120, 180))
    buf = io.BytesIO()
    rgb_img.save(buf, format="PNG")
    decoded = decode_png(buf.getvalue())
    assert decoded.mode == "RGBA"


def test_decode_png_preserves_rgba_source() -> None:
    img = _make_rgba(24, 24, (60, 120, 180, 200))
    payload = encode_png(img)
    decoded = decode_png(payload)
    assert decoded.mode == "RGBA"
    assert decoded.size == (24, 24)


def test_decode_encode_round_trip_is_byte_stable() -> None:
    """Decoding an already-encoded image and re-encoding must
    yield identical bytes — proves the decode boundary does
    not introduce state that the encoder later commits to
    metadata.
    """
    img = _make_rgba(48, 48, (50, 150, 250, 255))
    original = encode_png(img)
    once = encode_png(decode_png(original))
    twice = encode_png(decode_png(once))
    assert once == twice


def test_decode_png_empty_bytes_raises() -> None:
    with pytest.raises(BadPngError):
        decode_png(b"")


def test_decode_png_garbage_bytes_raises() -> None:
    with pytest.raises(BadPngError):
        decode_png(b"not a png at all just some ascii")


def test_dimensions_of_empty_raises() -> None:
    with pytest.raises(BadPngError):
        dimensions_of(b"")


def test_dimensions_of_matches_pillow_load() -> None:
    img = _make_rgba(123, 87, (0, 0, 0, 255))
    payload = encode_png(img)
    assert dimensions_of(payload) == (123, 87)


def test_encode_png_deterministic_after_real_mock_portrait_round_trip() -> None:
    """The pipeline will consume real portrait-provider output as
    its raw input. This test uses the smallest realistic mock
    PNG (from the existing MockStillPortraitProvider) to prove
    determinism against a non-synthetic byte source.
    """
    from app.services.portrait_provider import ExecutionMode, PortraitSpec
    from app.services.portrait_provider.mock import synth_mock_portrait_bytes

    spec = PortraitSpec(
        prompt="deterministic-test-prompt",
        aspect_ratio="1:1",
        execution_mode=ExecutionMode.FORCED_MOCK,
        deterministic_seed="pipeline-anchor",
    )
    raw = synth_mock_portrait_bytes(spec)
    decoded = decode_png(raw)
    a = encode_png(decoded)
    b = encode_png(decoded)
    assert a == b
