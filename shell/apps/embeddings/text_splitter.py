"""Paragraph-aware text chunking for embedding.

SESSION 138 / K3 — ported from u-d-b's
``content/embeddings.py:TextSplitter``, with the v1 chunk
shape locked at 1000-char chunks with 200-char overlap (the
defaults that lived in u-d-b's
``RAGSystem.process_document_for_rag`` call). Ported with
type hints + a smaller surface — character-os doesn't
currently need the YouTube-transcript variant.

The algorithm prefers paragraph boundaries first (split on
``\\n\\n``), falls back to sentence boundaries (split on ``.``)
inside paragraphs that exceed ``chunk_size`` on their own.
Overlap is taken from the tail of the previous chunk at a
word boundary when possible.
"""
from __future__ import annotations

from dataclasses import dataclass


# Locked defaults (scope-lock §"Ingestion pipeline").
DEFAULT_CHUNK_SIZE = 1000
DEFAULT_CHUNK_OVERLAP = 200


@dataclass(slots=True)
class TextChunk:
    """One chunk of split text — index + content + size."""

    index: int
    text: str
    size: int  # ``len(text)``


class TextSplitter:
    """Split text into overlapping chunks for embedding.

    Args:
        chunk_size: Maximum characters per chunk. Soft limit —
            sentences inside oversized paragraphs are kept whole
            when possible.
        chunk_overlap: Characters of overlap between adjacent
            chunks. Helps the embedding capture context across
            chunk boundaries.
    """

    def __init__(
        self,
        chunk_size: int = DEFAULT_CHUNK_SIZE,
        chunk_overlap: int = DEFAULT_CHUNK_OVERLAP,
    ) -> None:
        if chunk_size <= 0:
            raise ValueError("chunk_size must be positive")
        if chunk_overlap < 0 or chunk_overlap >= chunk_size:
            raise ValueError("chunk_overlap must be >= 0 and < chunk_size")
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(self, text: str) -> list[TextChunk]:
        if not text.strip():
            return []

        chunks: list[TextChunk] = []
        paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]

        current = ""
        index = 0

        for paragraph in paragraphs:
            if len(paragraph) > self.chunk_size:
                # The paragraph itself is too big — flush whatever
                # we've built up, then split the paragraph at
                # sentence boundaries.
                if current.strip():
                    chunks.append(TextChunk(index, current.strip(), len(current)))
                    index += 1
                    current = ""
                for sub in self._split_large_paragraph(paragraph):
                    chunks.append(TextChunk(index, sub.strip(), len(sub)))
                    index += 1
                continue

            # Would adding this paragraph overflow the current chunk?
            if current and len(current) + len(paragraph) > self.chunk_size:
                chunks.append(TextChunk(index, current.strip(), len(current)))
                index += 1
                overlap = self._tail_overlap(current)
                current = overlap + paragraph if overlap else paragraph
                continue

            current = paragraph if not current else f"{current}\n\n{paragraph}"

        if current.strip():
            chunks.append(TextChunk(index, current.strip(), len(current)))

        return chunks

    def _split_large_paragraph(self, paragraph: str) -> list[str]:
        """Split an oversized paragraph along sentence boundaries
        (period-delimited). Keeps each sub-chunk under
        ``chunk_size`` where possible; sentences longer than
        ``chunk_size`` get emitted whole — better to over-shoot
        than to mid-sentence-truncate."""
        sentences = [s.strip() for s in paragraph.split(".") if s.strip()]

        sub_chunks: list[str] = []
        current = ""
        for sentence in sentences:
            piece = sentence + "."
            if current and len(current) + len(piece) > self.chunk_size:
                sub_chunks.append(current.strip())
                overlap = self._tail_overlap(current)
                current = (overlap + piece) if overlap else piece
            else:
                current = f"{current}{piece}" if current else piece
        if current.strip():
            sub_chunks.append(current.strip())
        return sub_chunks

    def _tail_overlap(self, text: str) -> str:
        """Return the last ``chunk_overlap`` chars of ``text``,
        snapped to a word boundary when possible. Returns the
        empty string when ``chunk_overlap`` is 0 (caller wants
        no overlap)."""
        if self.chunk_overlap == 0:
            return ""
        if len(text) <= self.chunk_overlap:
            return text + " "

        tail = text[-self.chunk_overlap :]
        space = tail.find(" ")
        if space > 0:
            tail = tail[space:].lstrip()
        return tail + " " if tail else ""
