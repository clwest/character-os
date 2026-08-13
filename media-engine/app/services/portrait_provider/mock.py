"""MockStillPortraitProvider — §19 Step 5.a (SESSION 244).

Deterministic PNG synthesis for tests, contract testing, and
adapter mock routing (5.b/5.c reuse ``synth_mock_portrait_bytes``
so force-mock inside a real adapter produces identical bytes to
this adapter for the same spec).

CRITICAL — SESSION 244 constraint 7: this is qualification
plumbing, never qualification evidence. Records stamped
``provider=MOCK`` and records with ``execution_mode_actual=MOCK``
are BOTH non-qualifying. Two orthogonal filters — both must be
applied when isolating qualification-quality evidence. Tests
in this package assert the distinction is preserved.
"""
from __future__ import annotations

import hashlib
import struct
import time
import zlib

from . import (
    ExecutionMode,
    ExecutionModeActual,
    PortraitProviderName,
    PortraitResult,
    PortraitSpec,
    ProviderCapabilities,
    ProviderUnavailableError,
    UnsupportedAspectRatioError,
    UnsupportedModelError,
)


_MOCK_MODEL = "deterministic-solid"
_SUPPORTED_MODELS: tuple[str, ...] = (_MOCK_MODEL,)
# Kept broad on purpose: the Mock adapter is used in tests that
# also exercise Stability/Runway spec shapes. Real adapters
# constrain their own supported set (Runway is 1280:720-only in
# current shipped code).
_SUPPORTED_ASPECT_RATIOS: tuple[str, ...] = (
    "1:1",
    "16:9",
    "9:16",
    "4:3",
    "3:4",
    "1280:720",
)


def synth_mock_portrait_bytes(spec: PortraitSpec) -> bytes:
    """Deterministic PNG bytes from a PortraitSpec.

    Public in this module so 5.b/5.c adapters call the same
    synthesis when routing to mock. Cross-adapter byte
    equality for identical specs is a determinism test
    landing in 5.d.

    Not exported from the package ``__all__`` — consumers who
    want mock bytes should use the MockStillPortraitProvider
    adapter so provenance is stamped correctly.
    """
    width, height = _aspect_to_dims(spec.aspect_ratio)
    color = _mock_color(spec)
    return _solid_png(width, height, color)


class MockStillPortraitProvider:
    """PortraitProvider returning deterministic solid PNG bytes.
    Never touches an external API. Emits ``provider=MOCK``.
    """

    def generate_still_portrait(self, spec: PortraitSpec) -> PortraitResult:
        _validate_spec(spec, _SUPPORTED_MODELS, _SUPPORTED_ASPECT_RATIOS)
        if spec.execution_mode == ExecutionMode.REAL_REQUIRED:
            raise ProviderUnavailableError(
                "MockStillPortraitProvider cannot satisfy "
                "REAL_REQUIRED — it has no real provider. Callers "
                "requesting real portraits must pick a real adapter."
            )
        start = time.monotonic()
        image_bytes = synth_mock_portrait_bytes(spec)
        elapsed_ms = int((time.monotonic() - start) * 1000)
        return PortraitResult(
            image_bytes=image_bytes,
            provider=PortraitProviderName.MOCK,
            provider_model=spec.provider_model or _MOCK_MODEL,
            execution_mode_actual=ExecutionModeActual.MOCK,
            prompt_snapshot={
                "prompt": spec.prompt,
                "aspect_ratio": spec.aspect_ratio,
                "deterministic_seed": spec.deterministic_seed,
                "requested_execution_mode": spec.execution_mode.value,
            },
            elapsed_ms=elapsed_ms,
        )

    def capabilities(self) -> ProviderCapabilities:
        return ProviderCapabilities(
            provider_name=PortraitProviderName.MOCK,
            provider_model=_MOCK_MODEL,
            supported_models=_SUPPORTED_MODELS,
            supported_aspect_ratios=_SUPPORTED_ASPECT_RATIOS,
            max_prompt_length=None,
            is_deterministic=True,
            execution_modes_supported=frozenset(
                {ExecutionMode.FORCED_MOCK, ExecutionMode.AUTO},
            ),
        )

    def provider_name(self) -> PortraitProviderName:
        return PortraitProviderName.MOCK


def _validate_spec(
    spec: PortraitSpec,
    supported_models: tuple[str, ...],
    supported_aspect_ratios: tuple[str, ...],
) -> None:
    """Shared adapter-input validation. Errors are the same
    regardless of ``execution_mode`` — if the adapter can't
    accept the input for real, it can't accept it for mock
    either (mock represents what the real path would return).
    """
    if spec.execution_mode == ExecutionMode.UNAVAILABLE:
        raise ValueError(
            "PortraitSpec.execution_mode=UNAVAILABLE is invalid on "
            "input. Callers use REAL_REQUIRED, AUTO, or "
            "FORCED_MOCK to describe the request."
        )
    if spec.provider_model is not None and spec.provider_model not in supported_models:
        raise UnsupportedModelError(
            f"provider_model={spec.provider_model!r} not in "
            f"supported_models={list(supported_models)}. Unknown "
            f"models fail loudly per SESSION 244 constraint 6."
        )
    if spec.aspect_ratio not in supported_aspect_ratios:
        raise UnsupportedAspectRatioError(
            f"aspect_ratio={spec.aspect_ratio!r} not in "
            f"supported_aspect_ratios={list(supported_aspect_ratios)}."
        )


def _aspect_to_dims(aspect_ratio: str) -> tuple[int, int]:
    """Map aspect ratio strings to concrete (width, height).
    Same output for the same input — determinism anchor.
    """
    table = {
        "1:1": (256, 256),
        "16:9": (320, 180),
        "9:16": (180, 320),
        "4:3": (288, 216),
        "3:4": (216, 288),
        "1280:720": (320, 180),
    }
    if aspect_ratio not in table:
        raise AssertionError(
            f"aspect_ratio {aspect_ratio!r} passed spec validation "
            f"but has no dim mapping — table + _SUPPORTED_ASPECT_RATIOS drifted."
        )
    return table[aspect_ratio]


def _mock_color(spec: PortraitSpec) -> tuple[int, int, int]:
    """Derive a stable RGB color from the spec. Same spec →
    same color.
    """
    seed = (
        spec.prompt
        + "|" + spec.aspect_ratio
        + "|" + (spec.deterministic_seed or "")
        + "|" + (spec.provider_model or "")
    ).encode("utf-8")
    digest = hashlib.blake2s(seed, digest_size=3).digest()
    return (digest[0], digest[1], digest[2])


def _solid_png(width: int, height: int, color: tuple[int, int, int]) -> bytes:
    """Minimal valid PNG bytes filled with one RGB color.

    Zero-dependency implementation so mock tests do not pull in
    Pillow / numpy. Byte-for-byte deterministic when width /
    height / color are stable.
    """
    r, g, b = color
    scanline = bytes([0]) + bytes([r, g, b]) * width
    raw = scanline * height
    compressed = zlib.compress(raw, level=9)

    def _chunk(chunk_type: bytes, data: bytes) -> bytes:
        length = struct.pack(">I", len(data))
        crc = struct.pack(">I", zlib.crc32(chunk_type + data) & 0xFFFFFFFF)
        return length + chunk_type + data + crc

    signature = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(
        ">IIBBBBB",
        width,
        height,
        8,  # bit depth
        2,  # color type = RGB
        0,  # compression
        0,  # filter
        0,  # interlace
    )
    return (
        signature
        + _chunk(b"IHDR", ihdr)
        + _chunk(b"IDAT", compressed)
        + _chunk(b"IEND", b"")
    )
