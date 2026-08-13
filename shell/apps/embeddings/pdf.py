"""PDF text extraction via ``pdfminer.six``.

SESSION 138 / K3 — text-based PDFs only. Scanned PDFs / OCR
is explicitly out of scope (scope-lock §"Out of scope").

The single public entry point is ``extract_text(payload)``
which accepts either a bytes payload (in-memory PDF) or a
``Path`` to a file. Returns the extracted text + page count.
Raises ``PdfExtractionError`` on parser failures so callers
can surface a clean error to the operator.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class PdfExtractResult:
    text: str
    page_count: int


class PdfExtractionError(Exception):
    """Raised when pdfminer can't extract text from the input."""


def extract_text(payload: bytes | Path) -> PdfExtractResult:
    """Return the text content of a PDF.

    Args:
        payload: either raw PDF bytes or a path to a PDF file
            on disk.

    Returns:
        ``PdfExtractResult`` with the extracted text and the
        page count.

    Raises:
        ``PdfExtractionError`` if pdfminer fails or the result
        contains no text (likely a scanned / image-only PDF).
    """
    # Imported lazily — pdfminer is heavy and not every call
    # path needs it.
    from pdfminer.high_level import extract_text as pdfminer_extract
    from pdfminer.pdfdocument import PDFDocument
    from pdfminer.pdfparser import PDFParser
    from pdfminer.pdftypes import resolve1

    if isinstance(payload, Path):
        source = payload.read_bytes()
    else:
        source = payload

    if not source:
        raise PdfExtractionError("Empty PDF payload")

    try:
        text = pdfminer_extract(io.BytesIO(source)) or ""
    except Exception as exc:
        logger.exception("pdfminer failed to extract text")
        raise PdfExtractionError(f"pdfminer error: {exc}") from exc

    if not text.strip():
        raise PdfExtractionError(
            "PDF extracted to empty text — likely a scanned / "
            "image-only document. OCR is out of scope for v1."
        )

    # Page count via the parser — cheap, useful for source_metadata.
    page_count = 0
    try:
        parser = PDFParser(io.BytesIO(source))
        doc = PDFDocument(parser)
        catalog = resolve1(doc.catalog["Pages"])
        page_count = int(catalog.get("Count", 0))
    except Exception:
        # Page-count failure shouldn't sink a successful extract;
        # we already have the text. Log and continue.
        logger.warning("pdfminer page-count probe failed; continuing")

    return PdfExtractResult(text=text, page_count=page_count)
