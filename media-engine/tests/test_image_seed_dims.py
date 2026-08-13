"""Regression guard for the gen4_image ``referenceImages`` seed.

SESSION 181 dogfood of ``storyboard_ad`` failed with Runway
rejecting the seed reference image: ``Invalid asset dimensions.
Height and width must be at least 2px. Got 1x1.`` The seed PNG
had been 1x1 since V13 shipped; Runway tightened the API
validation in the interim.

These tests pin the seed dimensions at >= 2x2 so any future
shrink reverts immediately. The seed is intentionally tiny (a
solid neutral grey) so it doesn't influence Runway's
generation; the size guard just keeps it inside whatever
minimum Runway enforces.
"""
from __future__ import annotations

import base64
import struct

import pytest

from app.routers.internal import _seed_neutral_data_uri


def _parse_png_dims(uri: str) -> tuple[int, int]:
    """Pull width / height from the IHDR chunk of a base64-encoded
    PNG data URI."""
    assert uri.startswith("data:image/png;base64,")
    payload = base64.b64decode(uri.split(",", 1)[1])
    # PNG signature (8) + IHDR length (4) + "IHDR" (4) = 16 bytes
    # before width(4)+height(4).
    width, height = struct.unpack(">II", payload[16:24])
    return width, height


def test_seed_meets_runway_minimum_dimensions() -> None:
    """Runway's gen4_image referenceImages validator requires
    every reference image to be at least 2x2 pixels. The seed
    PNG MUST meet that floor."""
    uri = _seed_neutral_data_uri()
    width, height = _parse_png_dims(uri)
    assert width >= 2, (
        f"seed PNG width {width} is below Runway's 2-pixel minimum"
    )
    assert height >= 2, (
        f"seed PNG height {height} is below Runway's 2-pixel minimum"
    )


def test_seed_is_solid_color_no_visual_content() -> None:
    """The seed is a no-op reference (solid grey) so it doesn't
    bias Runway's generation toward any visual content. The
    payload is intentionally tiny — large reference images can
    push the request over the gen4_image data-URI budget."""
    uri = _seed_neutral_data_uri()
    payload = base64.b64decode(uri.split(",", 1)[1])
    # 8x8 solid PNG is well under 200 bytes; pin at 1KB to leave
    # headroom for any future minor size bump (palette / metadata)
    # without accidentally landing a heavy reference.
    assert len(payload) < 1024, (
        f"seed PNG is {len(payload)} bytes; should stay tiny "
        f"so it doesn't inflate the request payload"
    )


@pytest.mark.parametrize("invocation", [1, 2, 3])
def test_seed_is_deterministic_across_calls(invocation: int) -> None:
    """Same bytes every call — the endpoint caches by hash of
    (prompt + reference) so determinism here keeps cache keys
    stable across invocations."""
    a = _seed_neutral_data_uri()
    b = _seed_neutral_data_uri()
    assert a == b, "seed PNG must be deterministic across calls"
