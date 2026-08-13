# Case Study 03 — YouTube ingest silently returned nothing

**Date:** SESSION 175 (K7.x v2).
**Systems:** `shell/apps/embeddings/ingestion.py`, knowledge
retrieval.

## Problem

Operator pasted a YouTube URL into the knowledge ingest field.
The ingest returned success, created a `KnowledgeDocument` row,
reported "processed", but subsequent retrievals against that
teammate returned nothing from the video.

## Evidence

- `KnowledgeDocument.status = "processed"`.
- `KnowledgeChunk.count() == 0` for that document.
- No error surfaced to the operator.

## Root cause

The ingest pipeline used `trafilatura` as its universal HTML
extractor. `trafilatura` inspects a page's DOM for
article-shaped content. YouTube's watch page is a JavaScript
shell — no article body, no readable text. `trafilatura`
correctly returned an empty string.

The ingest code treated empty extraction as success. The
`processed` status was truthful about "we ran the pipeline";
it was silent about "we captured nothing".

Two problems, not one:

1. YouTube URLs need a different extractor.
2. Empty extractions should not be silently accepted.

## Decision

Fix both. Add a per-host router to the extractor, and add a
detect-reject at the ingest layer for empty captures.

## Implementation change

- Per-host extractor router in `ingestion.py`:
  - `youtube.com`, `youtu.be` → `youtube-transcript-api`.
  - Everything else → `trafilatura` (unchanged).
- YouTube path fetches the transcript, falls back to
  auto-generated captions if none is available, returns clear
  error when neither exists.
- Ingest layer: if extractor returns empty and there's no
  ingest-side content override, mark the document
  `status = "empty"` and surface a clear operator error rather
  than silent success.

## Verification

Operator ingested a real YouTube video. Transcripts landed as
`KnowledgeChunk` rows. Next K6 script synthesis on that
teammate correctly cited the video content in
`Composition.knowledge_chunk_ids`.

## Lasting rule

**Silence is a bug.** An ingest that says "processed" while
capturing zero bytes is worse than one that says "failed".
Every ingest path now has a positive-content assertion; if the
extractor returns empty, the pipeline surfaces it.

YouTube became a first-class knowledge source rather than an
undocumented failure mode.
