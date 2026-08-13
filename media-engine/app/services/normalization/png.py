"""Deterministic PNG encode / decode helpers for the pipeline.

The normalization pipeline's load-bearing invariant (§10.6) is
**byte-for-byte identical output** given identical input + spec +
pipeline version. Pillow's PNG writer is deterministic on its
own, but only under a specific configuration — this module
centralizes that configuration so every stage that encodes an
image goes through one path.

What is intentional here:

* **RGBA mode normalization.** Every image the pipeline emits is
  RGBA. Two round-tripped copies of the same visually-equivalent
  RGB image would produce differently-shaped bytes (RGB vs.
  RGBA) which would break the determinism contract for pipelines
  that later add transparency in the background stage (7.c). By
  normalizing at decode time, downstream stages see one shape.

* **No time-based chunks.** Pillow's PNG writer does not emit
  ``tIME`` by default; this module never sets an ``info["tIME"]``
  and never passes a ``PngInfo`` argument to ``save``. A
  ``test_no_time_chunk`` in the accompanying test module asserts
  the invariant against real output bytes so a future upgrade
  that flips a default cannot silently drift.

* **Fixed compression.** ``optimize=False`` + explicit
  ``compress_level=6`` (the zlib default; pinned so a future
  Pillow default change doesn't ripple through). Byte-for-byte
  determinism requires the compression pipeline to be pinned;
  ``optimize=True`` sometimes chooses different filters run to
  run under certain input widths.

* **No ICC / EXIF / text.** Nothing in the write path attaches
  metadata; the load path strips whatever the source PNG
  contained. Provider-injected metadata (Runway timestamps,
  Stability generation UUIDs) never round-trips through the
  pipeline into the normalized artifact.

What is deliberately NOT here:

* Any lossy resampling — that is a per-stage decision, not a
  global helper.
* Format conversion beyond RGBA — the pipeline is PNG-only per
  §17.6.a's surface-profile output specification.
* Progressive / interlaced output — a source of nondeterminism
  under some Pillow builds.
"""
from __future__ import annotations

import io

from PIL import Image, ImageFile


# Pillow's default is 6 (the zlib default); pinned explicitly so a
# future upstream default flip does not silently change output
# bytes and break the §10.6 determinism contract.
_PNG_COMPRESS_LEVEL = 6

# Pillow's ImageFile parser truncates on IO error by default in
# some builds; force strict decoding so a malformed input surfaces
# as ``BadPngError`` rather than silently producing a partial
# image that then round-trips.
ImageFile.LOAD_TRUNCATED_IMAGES = False


class PngError(Exception):
    """Base for PNG helper errors."""


class BadPngError(PngError):
    """Input bytes did not decode as a valid PNG."""


class PngEncodingError(PngError):
    """Pillow refused to encode the image (should be unreachable
    for well-formed RGBA images at reasonable dimensions).
    """


def decode_png(raw: bytes) -> Image.Image:
    """Decode PNG bytes into an in-memory Pillow image normalized
    to RGBA.

    The pipeline treats RGBA as its canonical in-memory shape.
    Non-RGBA sources (RGB from Stability, palette from a
    hypothetical future provider) are converted at the boundary
    so downstream stages never need to branch on mode.

    Raises ``BadPngError`` when the bytes do not decode. Callers
    (the pipeline entry point) catch and re-raise as a
    ``PipelineError``.
    """
    if not raw:
        raise BadPngError("empty PNG bytes")
    try:
        img = Image.open(io.BytesIO(raw), formats=("PNG",))
        # Force decode now so downstream code doesn't fail
        # lazily on an unrelated call site.
        img.load()
    except Exception as exc:  # pragma: no cover — defensive
        raise BadPngError(f"failed to decode PNG: {exc!s}") from exc
    if img.mode == "RGBA":
        return img
    return img.convert("RGBA")


def encode_png(image: Image.Image) -> bytes:
    """Encode a Pillow image as PNG bytes under pinned settings.

    The image's ``info`` dict is intentionally not consulted —
    any timestamps, ICC profiles, or textual chunks a source
    carried are dropped at the pipeline boundary. This is how
    the pipeline guarantees the manifest, not the provider, is
    the sole source of pipeline-time provenance.

    Precondition: ``image.mode == 'RGBA'`` (call ``decode_png``
    first). If a stage manufactures an image internally, it
    must normalize mode before calling this helper.
    """
    if image.mode != "RGBA":
        raise PngEncodingError(
            f"encode_png requires RGBA input; got {image.mode!r}. "
            f"Call decode_png at the pipeline boundary and keep the "
            f"mode stable across stages."
        )
    buf = io.BytesIO()
    try:
        image.save(
            buf,
            format="PNG",
            optimize=False,
            compress_level=_PNG_COMPRESS_LEVEL,
        )
    except Exception as exc:  # pragma: no cover — defensive
        raise PngEncodingError(f"Pillow save failed: {exc!s}") from exc
    return buf.getvalue()


def dimensions_of(raw: bytes) -> tuple[int, int]:
    """Read (width, height) from PNG bytes without a full decode
    into pixel memory. Useful for stages that need to inspect
    dimensions cheaply.
    """
    if not raw:
        raise BadPngError("empty PNG bytes")
    try:
        img = Image.open(io.BytesIO(raw), formats=("PNG",))
        w, h = img.size
    except Exception as exc:  # pragma: no cover — defensive
        raise BadPngError(f"failed to read PNG dimensions: {exc!s}") from exc
    return (int(w), int(h))
