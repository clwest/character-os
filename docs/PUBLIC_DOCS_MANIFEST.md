# Public Docs Manifest

This document lists what's in the public Character OS
distribution and what's preserved privately.

## In the public tree

Top-level:

- `README.md` — 30-second orientation + three canonical flows.
- `ARCHITECTURE.md` — service boundaries, domain model,
  tenancy, cost governance, state machines, provenance,
  provider abstraction, grounding.
- `AI_ASSISTED_DEVELOPMENT.md` — honest disclosure of the
  Chris ÷ Claude Code split with concrete examples.
- `LICENSE` — MIT.

Curated docs:

- `docs/architecture/GOD_FILES.md` — honest documentation of
  four large files, naming compat debt, legacy `Video` shim,
  empty `agents`/`memory` apps.
- `docs/architecture/PROVIDER_MAP.md` — every AI provider with
  SDK, env vars, code paths, mock gates.
- `docs/case-studies/01-stability-portrait-lipsync.md`
- `docs/case-studies/02-personality-vs-brief.md`
- `docs/case-studies/03-youtube-ingest-silent-fail.md`
- `docs/case-studies/04-k6-verifier-stoplist.md`
- `docs/case-studies/05-runtime-truth-doctor.md`
- `docs/case-studies/06-allauth-rate-limits.md`
- `docs/case-studies/07-r7-sub-slicing.md`

Design-lock docs (retained as-is because they are the arc
contracts referenced from code):

- `docs/design/KNOWLEDGE_LAYER.md`
- `docs/design/VIDEO_COMPOSITION_V1.md`
- `docs/design/REALTIME_AVATAR_V1.md`
- `docs/design/WORKSPACE_FABRIC_V1.md`
- `docs/design/IDENTITY_MODEL_V1.md`
- `docs/design/operator-decisions/` — ratified product
  philosophy.

(The historical `docs/design/UI_REDESIGN_V2.md` bootstrap doc
was excluded because its content was too heavily entangled with
migration-from-sibling-project instructions;
`ARCHITECTURE.md` in the repo root now carries the equivalent
architecture summary in a portable form.)

Runtime-truth docs (auto-regenerable):

- `docs/CHARACTER_OS_INVENTORY.md`
- `docs/CHARACTER_OS_WHAT_IT_IS.md`
- `docs/CHARACTER_OS_PIPELINE.md`
- `docs/CHARACTER_OS_BEHAVIOR_LAYER.md`
- `docs/CHARACTER_OS_TRANSLATION_LAYER.md`

## Preserved privately (not in the public tree)

These paths are `.gitignore`d in this distribution. They
remain on the operator's local disk for reference; they do
not go to the public repo.

- `docs/handoffs/` — 253 session handoff files documenting the
  internal engineering history. Contains internal calibration
  notes, dogfood specifics, cost figures, real-mode spend
  receipts, and cross-project topology (sibling private
  projects). Case studies distill the strongest lessons for
  public consumption.
- `docs/production-readiness/` — internal readiness tracking,
  dogfood reports (`dogfood-eb5/`), F-numbered findings, real-
  mode provider runbooks with local infrastructure details.
- `docs/audit-2026-07-21/` — a prior internal audit including
  cross-project bridge analysis (Rigby SaaS + character-os).
- `docs/topics/` — internal topic notes.
- `docs/research/` — internal research notes.
- `docs/design/visual/portrait_qualification/fixtures/` — 336
  generated portrait PNGs (~291 MB) from the visual
  qualification harness. Removed to keep the public repo
  lean; the qualification framework itself remains in the
  design docs.
- `docs/CHARACTER_OS_SESSION_START.md`, `INVENTORY_LEGACY.md`,
  `WHAT_IT_IS_LEGACY.md`,
  `SESSION_249_STEP_9B_ARCHITECTURE_PLAN.md`,
  `CONTEXT_KIT_INVENTORY.md`, `CUSTOMER_ZERO_DOGFOOD.md`,
  `POSTGRES_MIGRATION.md`, `247_GLOBAL_AI_OVERVIEW.md`,
  `TRUST_CALIBRATION.md` — session-boot, legacy, or
  brand-specific docs that don't belong in the public
  portfolio.
- `00-START-NEXT-SESSION.md`, `CLAUDE.md` — session-boot and
  AI pair-programming rules; internal-facing.
- `.claude/` — Claude Code skills scaffolding; the shipped skill
  instructed agents to read internal-only paths, so it is
  incoherent (and unhelpful) in the public tree.
- `docs/docs-pattern/` — a separate project's collaboration
  framework; not part of Character OS itself.
- Historical / hackathon-era scripts under `scripts/` — probes
  and seeders that referenced private topology or hackathon
  demo personas (`probe-video-to-video.py`,
  `probe-character-performance.py`,
  `ingest-udb-spokesperson-corpus.py`, `seed-demo-*.py`,
  `relink-orphan-demo-campaigns.py`, `*-submission-*.py`,
  `finish-dialogue-beats.py`,
  `upload-context-kit-demo-grounding.py`,
  `check-context-kit-drift.sh`).

## Why the split

The public distribution should be readable in 30 minutes by a
hiring manager and expose the strongest engineering signal.
The internal history is preserved because it evidences the
iterative-engineering discipline the case studies distill —
but reading 253 session handoffs is not the fastest path to
understanding what the code does.

Case studies are the public surface of what TRUST_CALIBRATION
and the handoffs privately hold.
