# Case Study 03 — YouTube ingest silently returned nothing

> **CORRECTION — 2026-08-31.** The account below is wrong about the
> mechanic, and the correction is kept in place rather than rewritten so
> the error stays visible.
>
> trafilatura did **not** return an empty string, and no document was
> stored with zero chunks. It returned YouTube's navigation boilerplate
> ("About Press Copyright Contact us Creators Advertise Developers
> Terms…") as "main content". That text was chunked, embedded and
> stored successfully. The damage was not a missing document — it was a
> single short generic chunk sitting at distance ~0.85 from almost any
> query, degrading retrieval across the whole workspace.
>
> Primary sources, all three of which disagree with this write-up:
> the module docstring in `shell/apps/embeddings/url_fetch.py` (K7.x,
> SESSION 174), the module docstring in
> `shell/apps/embeddings/youtube_extractor.py` (K7.x v2, SESSION 175),
> and the live boilerplate-signature regex between them.
>
> Everything in "Decision" and "Implementation change" below is
> substantially right; the per-host router and the post-extraction
> boilerplate check are what actually shipped. Only the diagnosis is
> wrong.
>
> Probable cause of the error: SESSION 174 described its own work as
> closing "the silent-failure surface", and this write-up was
> reconstructed later from that label rather than from the behaviour.
> The name outlived the facts.
>
> No verifier here would have caught this. It contains no stale number
> — it is a coherent, confident, wrong story. See
> `career/writing/FACT_CHECK_2026-08-31.md`.

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

**Silence is a bug** — as originally written. The truer rule, given
what actually happened: **a plausible answer is worse than an empty
one**, because an empty result is loud and a well-formed wrong one is
invisible. An ingest that says "processed" while
capturing zero bytes is worse than one that says "failed".
Every ingest path now has a positive-content assertion; if the
extractor returns empty, the pipeline surfaces it.

YouTube became a first-class knowledge source rather than an
undocumented failure mode.
