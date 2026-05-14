"""Ingestion orchestrator — operator input → KnowledgeDocument.

SESSION 138 / K3. The orchestrator is the synchronous setup
half of ingestion: normalise the input, compute the content
hash, check dedup, create the ``KnowledgeDocument`` row in
``status='pending'``. The async embedding pass — chunking,
calling the embedding service per chunk, persisting
``KnowledgeChunk`` rows, flipping status to ``processed`` —
lives in ``tasks.embed_document``.

Why the split: a 50-page PDF can take 10-30 s to embed even
with cache hits. Operators see immediate feedback (the
document row exists, status=pending) while the chunks fill
in the background.

Two ingestion paths supported in K3:

* ``ingest_text()``: paste / typed content. Operator supplies
  the raw text + a title + metadata.
* ``ingest_pdf()``: PDF upload. Reads ``pdfminer.six``-extracted
  text, then routes through the same persistence path.

URL ingestion (paste + serper) is K7.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from django.db import IntegrityError, transaction

from apps.accounts.models import Workspace

from . import pdf
from .models import (
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)

if TYPE_CHECKING:
    from apps.spokespeople.models import Spokesperson
    from django.contrib.auth.models import AbstractBaseUser

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class IngestResult:
    """What ``ingest_*`` returns. ``deduped`` is True when the
    same content already existed in the workspace and the
    pre-existing row is being returned."""

    document: KnowledgeDocument
    deduped: bool


def _normalize(text: str) -> str:
    """Trim + collapse Windows line endings + strip trailing
    whitespace on each line. Cheap and conservative — anything
    fancier risks losing intentional formatting in markdown."""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    lines = [line.rstrip() for line in text.split("\n")]
    return "\n".join(lines).strip()


def _content_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _persist(
    workspace: Workspace,
    title: str,
    document_type: DocumentType,
    raw_content: str,
    processed_content: str,
    ingested_via: IngestedVia,
    *,
    source_url: str = "",
    source_metadata: dict | None = None,
    created_by: "AbstractBaseUser | None" = None,
    spokespeople: "list[Spokesperson] | None" = None,
) -> IngestResult:
    """Create-or-return the KnowledgeDocument row. Dedup via
    ``(workspace, content_hash)`` unique constraint."""
    digest = _content_hash(processed_content)

    existing = KnowledgeDocument.objects.filter(
        workspace=workspace, content_hash=digest,
    ).first()
    if existing is not None:
        logger.info(
            "knowledge ingest deduped workspace=%s hash=%s doc=%s",
            workspace.slug, digest[:12], existing.pk,
        )
        return IngestResult(document=existing, deduped=True)

    try:
        with transaction.atomic():
            doc = KnowledgeDocument.objects.create(
                workspace=workspace,
                title=title.strip() or "Untitled",
                document_type=document_type,
                raw_content=raw_content,
                processed_content=processed_content,
                content_hash=digest,
                source_url=source_url,
                source_metadata=source_metadata or {},
                ingested_via=ingested_via,
                status=DocumentStatus.PENDING,
                created_by=created_by,
            )
            if spokespeople:
                # The m2m_changed signal in ``apps.embeddings.signals``
                # vetoes cross-workspace attaches; ``.set()`` raises
                # ``ValidationError`` if any spokesperson belongs to
                # another workspace.
                doc.spokespeople.set(spokespeople)
    except IntegrityError:
        # Race: another worker created the same content_hash
        # between our existence check and the insert. Re-fetch
        # and return it.
        doc = KnowledgeDocument.objects.filter(
            workspace=workspace, content_hash=digest,
        ).first()
        if doc is None:
            raise
        return IngestResult(document=doc, deduped=True)

    return IngestResult(document=doc, deduped=False)


def ingest_text(
    *,
    workspace: Workspace,
    title: str,
    content: str,
    document_type: DocumentType = DocumentType.TEXT,
    ingested_via: IngestedVia = IngestedVia.PASTE,
    created_by: "AbstractBaseUser | None" = None,
    spokespeople: "list[Spokesperson] | None" = None,
    source_metadata: dict | None = None,
) -> IngestResult:
    """Ingest pasted / typed text or markdown.

    The text is normalised then hashed. If a document with that
    hash already exists in the workspace, returns the existing
    row with ``deduped=True`` — re-ingesting the same content
    is idempotent.

    The returned document is ``status='pending'``. Caller
    should enqueue ``apps.embeddings.tasks.embed_document``
    against ``result.document.pk`` to populate the chunks
    (unless ``deduped=True`` — those already have chunks).
    """
    if document_type not in {DocumentType.TEXT, DocumentType.MARKDOWN}:
        raise ValueError(
            f"ingest_text only handles TEXT or MARKDOWN, got {document_type}"
        )

    normalised = _normalize(content)
    if not normalised:
        raise ValueError("Cannot ingest empty content")

    return _persist(
        workspace=workspace,
        title=title,
        document_type=document_type,
        raw_content=content,
        processed_content=normalised,
        ingested_via=ingested_via,
        source_metadata=source_metadata,
        created_by=created_by,
        spokespeople=spokespeople,
    )


def ingest_pdf(
    *,
    workspace: Workspace,
    title: str,
    payload: bytes | Path,
    created_by: "AbstractBaseUser | None" = None,
    spokespeople: "list[Spokesperson] | None" = None,
    source_metadata: dict | None = None,
) -> IngestResult:
    """Ingest an uploaded PDF.

    Extracts text via ``pdfminer.six``, then routes through the
    same persistence path as ``ingest_text``. ``source_metadata``
    is enriched with the PDF page count for operator visibility.

    Raises ``pdf.PdfExtractionError`` if extraction fails
    (most commonly: scanned/image-only PDF — out of scope v1).
    """
    extract = pdf.extract_text(payload)
    normalised = _normalize(extract.text)
    if not normalised:
        raise ValueError("PDF extraction yielded empty text")

    metadata = dict(source_metadata or {})
    metadata["pdf_page_count"] = extract.page_count

    raw_size = len(payload) if isinstance(payload, bytes) else payload.stat().st_size
    metadata["pdf_size_bytes"] = raw_size

    # raw_content stores the extracted text (not the binary
    # PDF) — the binary doesn't survive ingestion. Operators
    # who need the original re-upload from local source.
    return _persist(
        workspace=workspace,
        title=title,
        document_type=DocumentType.PDF,
        raw_content=extract.text,
        processed_content=normalised,
        ingested_via=IngestedVia.UPLOAD,
        source_metadata=metadata,
        created_by=created_by,
        spokespeople=spokespeople,
    )
