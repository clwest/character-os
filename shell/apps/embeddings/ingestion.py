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

from . import pdf, url_fetch
from .models import (
    AudienceScope,
    DeactivationReason,
    DocumentStatus,
    DocumentType,
    IngestedVia,
    KnowledgeDocument,
)


class OrphanRevivalRejected(Exception):
    """SESSION 275 — raised by ``_persist`` when dedup would revive
    a KnowledgeDocument that was archived because its last assigned
    spokesperson was deleted, and the current ingestion call does
    not supply an explicit new spokesperson set.

    Reactivating such a KD into ``is_active=True`` with an empty
    spokespeople M2M would silently broadcast its content to every
    eligible teammate — the exact audience-widening hazard the
    ``pre_delete`` signal on ``Teammate`` was introduced to prevent.
    See ``docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md``
    §23, §29.

    The serializer catches this specifically and converts it to a
    clean 400 for the operator (per-path, alongside the existing
    ``pdf.PdfExtractionError`` / ``url_fetch.UrlFetchError`` handlers).
    """

if TYPE_CHECKING:
    from apps.spokespeople.models import Teammate
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
    spokespeople: "list[Teammate] | None" = None,
    universe=None,
) -> IngestResult:
    """Create-or-return the KnowledgeDocument row. Dedup via
    ``(workspace, content_hash)`` unique constraint.

    SESSION 142 / K4.2: if the matching row is soft-deleted
    (``is_active=False``), restore it — flip active, reset to
    PENDING, clear the error message, update the title, and
    return ``deduped=False`` so the caller re-fires the
    embedding task. Otherwise an operator who deletes a doc
    then re-ingests the same content is stuck: dedup hands back
    a row they can't see and never re-fires embeds.
    """
    digest = _content_hash(processed_content)

    existing = KnowledgeDocument.objects.filter(
        workspace=workspace, content_hash=digest,
    ).first()
    if existing is not None:
        if existing.is_active:
            logger.info(
                "knowledge ingest deduped workspace=%s hash=%s doc=%s",
                workspace.slug, digest[:12], existing.pk,
            )
            return IngestResult(document=existing, deduped=True)

        # SESSION 275 — safe-revival gate. A KD archived by the
        # ``pre_delete`` signal on ``Teammate`` (because its sole
        # spokesperson was deleted) has ``spokespeople=∅``. Reviving
        # it into ``is_active=True`` while leaving that M2M empty
        # would flip the KD to broadcast-eligible under the retrieval
        # predicate's ``Q(spokespeople__isnull=True)`` fallback — the
        # exact audience-widening hazard the signal was introduced
        # to prevent (audit doc §23). Require the caller to supply
        # a non-empty explicit spokespeople set; otherwise reject.
        # Operator-deleted rows (``OPERATOR_DELETE`` or legacy blank)
        # revive unchanged — their prior M2M is preserved if the
        # caller supplies nothing, or replaced if they supply new
        # spokespeople.
        is_orphan_revival = existing.deactivated_reason == (
            DeactivationReason.ORPHANED_BY_TEAMMATE_DELETE
        )
        if is_orphan_revival:
            if not spokespeople:
                raise OrphanRevivalRejected(
                    "This content matches a knowledge document that was "
                    "archived when its assigned character was deleted. "
                    "Reactivating it without an explicit character "
                    "assignment would silently broaden its audience to "
                    "every eligible teammate. Re-ingest with a specific "
                    "character selected, or contact an admin to restore "
                    "and reassign it manually."
                )

        # Soft-deleted row with the same content: restore +
        # re-embed. embed_document is idempotent — it wipes
        # stale chunks before re-running, so calling it on a
        # previously-processed doc is safe.
        #
        # SESSION 276 Slice 9 / Delta Stage 3B-1 — the revival branch
        # is now wrapped in ``transaction.atomic()`` so the audience
        # + M2M writes commit together. Previously (SESSION 275)
        # ``existing.save()`` and ``existing.spokespeople.set(...)``
        # ran outside a transaction; a race or a ``m2m_changed``
        # signal veto between the two could leave an active row with
        # empty M2M. Wrapping both in a single savepoint closes that
        # hole for both orphan revival (which now stamps CHARACTER)
        # and operator-delete revival (which preserves prior audience).
        with transaction.atomic():
            existing.is_active = True
            existing.status = DocumentStatus.PENDING
            existing.error_message = ""
            # SESSION 275 — revival clears the deactivation reason.
            # ``OPERATOR_DELETE`` reason no longer applies (the row is
            # active again). For ``ORPHANED_BY_TEAMMATE_DELETE`` we
            # only reach here when the caller supplied spokespeople
            # (gate above), so the audience is bounded by that
            # explicit set — safe to clear.
            existing.deactivated_reason = ""
            new_title = title.strip()
            if new_title:
                existing.title = new_title

            update_fields = [
                "is_active", "status", "error_message",
                "deactivated_reason", "title", "updated_at",
            ]

            # SESSION 276 Slice 9 / Delta Stage 3B-1 (Q-276-23) —
            # orphan revival lands directly at
            # ``audience_scope=CHARACTER``. The gate above guarantees
            # ``spokespeople`` is non-empty, so the resulting row is
            # a coherent Delta CHARACTER shape immediately — no
            # transitional NONE / NULL state persists. Operator-
            # deleted revival (``is_orphan_revival=False``) does NOT
            # touch ``audience_scope`` — the operator's prior audience
            # (Slice 2 §22 refinement) is preserved unchanged.
            if is_orphan_revival:
                existing.audience_scope = AudienceScope.CHARACTER
                update_fields.append("audience_scope")

            existing.save(update_fields=update_fields)
            if spokespeople:
                existing.spokespeople.set(spokespeople)

        logger.info(
            "knowledge ingest restored workspace=%s hash=%s doc=%s "
            "orphan_revival=%s",
            workspace.slug, digest[:12], existing.pk, is_orphan_revival,
        )
        return IngestResult(document=existing, deduped=False)

    try:
        with transaction.atomic():
            # SESSION 276 Slice 10 / Delta Stage 3B-2 (Q-276-24) — when
            # the caller supplies one or more explicit spokespeople, the
            # new KD is a character-scoped row by construction. Stamp
            # ``audience_scope=CHARACTER`` at creation time so the row
            # is Delta-coherent immediately, with no transitional NULL
            # bridge state.
            #
            # No spokespeople → leave ``audience_scope`` unset (NULL).
            # UNIVERSE-shared and WORKSPACE-shared fresh-create
            # inference are deferred to Q-276-25 because "absence of
            # characters" is exactly the semantic boundary that caused
            # the original audience-broadening bug class and needs its
            # own explicit-intent evidence before positive stamping.
            #
            # Atomicity: the surrounding ``transaction.atomic()`` block
            # already covers ``KnowledgeDocument.objects.create()`` +
            # ``doc.spokespeople.set(...)``. If M2M assignment fails
            # (e.g. cross-workspace or cross-Universe signal veto), the
            # whole KD row rolls back — no ``CHARACTER + empty M2M``
            # malformed shape can persist.
            create_audience_scope = (
                AudienceScope.CHARACTER if spokespeople else None
            )
            doc = KnowledgeDocument.objects.create(
                workspace=workspace,
                # SESSION 261 — Universe scope passthrough. NULL
                # preserves the pre-Universe legacy semantics; a
                # supplied Universe scopes the doc to that world.
                universe=universe,
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
                audience_scope=create_audience_scope,
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
    spokespeople: "list[Teammate] | None" = None,
    source_metadata: dict | None = None,
    universe=None,
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
        universe=universe,
    )


def ingest_pdf(
    *,
    workspace: Workspace,
    title: str,
    payload: bytes | Path,
    created_by: "AbstractBaseUser | None" = None,
    spokespeople: "list[Teammate] | None" = None,
    source_metadata: dict | None = None,
    universe=None,
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
        universe=universe,
    )


def ingest_url(
    *,
    workspace: Workspace,
    url: str,
    title: str = "",
    created_by: "AbstractBaseUser | None" = None,
    spokespeople: "list[Teammate] | None" = None,
    source_metadata: dict | None = None,
    ingested_via: IngestedVia = IngestedVia.PASTE,
    universe=None,
) -> IngestResult:
    """Ingest a URL.

    Fetches via ``url_fetch.fetch_url`` (httpx + trafilatura
    main-content extraction), then routes through the same
    persistence path as ``ingest_text``. ``source_url`` is
    populated on the resulting row; the title falls back to
    the page's ``<title>`` if the caller didn't supply one.

    Args:
        workspace: anchor workspace.
        url: an http(s) URL.
        title: optional title override; defaults to extracted
            page title or hostname.
        ingested_via: ``PASTE`` when operator typed the URL,
            ``SERPER`` when it came from search discovery.
            Both flow through the same fetch+extract pipeline.

    Raises:
        ``url_fetch.UrlFetchError`` for any fetch / extract
        failure. Callers (the serializer) turn that into a
        clean 400 for the operator.
    """
    extract = url_fetch.fetch_url(url)
    normalised = _normalize(extract.text)
    if not normalised:
        raise ValueError("URL extraction yielded empty text")

    metadata = dict(source_metadata or {})
    metadata.update(extract.metadata)
    metadata.setdefault("source_url", url)

    final_title = title.strip() or extract.title or url

    return _persist(
        workspace=workspace,
        title=final_title,
        document_type=DocumentType.URL,
        raw_content=extract.text,
        processed_content=normalised,
        ingested_via=ingested_via,
        source_url=url,
        source_metadata=metadata,
        created_by=created_by,
        spokespeople=spokespeople,
        universe=universe,
    )
