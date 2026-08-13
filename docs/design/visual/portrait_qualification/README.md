---
title: "Portrait Qualification — Directory Index"
status: scaffold
generated: 2026-08-06
last_revised: 2026-08-06
companion_docs: ["../PORTRAIT_LANGUAGE_V1_2026-08-06.md", "../PORTRAIT_TERRITORY_STUDY_V1_2026-08-06.md"]
---

# Portrait Qualification

> Empirical evidence layer for the Character OS portrait system.
> Nothing in this directory replaces or overrides the design-lock documents
> in the parent `docs/design/visual/` — this directory is where the
> **evidence that will drive Portrait Territory Study V2 selection** lives.

---

## Why this directory exists

[`PORTRAIT_LANGUAGE_V1_2026-08-06.md`](../PORTRAIT_LANGUAGE_V1_2026-08-06.md)
and
[`PORTRAIT_TERRITORY_STUDY_V1_2026-08-06.md`](../PORTRAIT_TERRITORY_STUDY_V1_2026-08-06.md)
deliberately defer aesthetic-register selection to empirical benchmark.
SESSION 238 (internal handoff, preserved privately)
locked the visual foundation and blocked all downstream visual work
(Typography Study, Color and Light Study, Home Visual Canonical,
Onboarding visual proposal, Default Alex casting) behind that benchmark.

This directory is where:

- The **identity contract** the benchmark rests on lives.
- The **benchmark identity fixtures** live.
- The **evidence artifacts** (still portraits, motion samples, speech
  renders, screenshots, reviewer notes) live once they exist.
- The **evaluation instrument** (scoring schema, reviewer records)
  lives.

If it is not empirical, or not the instrument that produces the
empirical, it does not live here — it lives in the parent design
directory.

---

## Read order

1. [`CANONICAL_IDENTITY_CONTRACT_V1.md`](CANONICAL_IDENTITY_CONTRACT_V1.md)
   — the implementation contract for the durable identity anchor every
   benchmark render must derive from. **First artifact. Read before
   anything else in this directory.**

Everything below is prospective. Sections will be filled as artifacts
land.

---

## Status — 2026-08-06

**Prerequisites complete.** All nine §19.1 prerequisite artifact
groups have landed and validate cleanly. Step 1 of the ratified
implementation sequence (`Spokesperson → Teammate` rename, per
§17.1.b) is **safe to begin** pending operator's separate
authorization.

- Contract: `ratified` (see
  [`CANONICAL_IDENTITY_CONTRACT_V1.md`](CANONICAL_IDENTITY_CONTRACT_V1.md)).
- Prerequisite artifacts: all present, schema-validated,
  cross-references resolve.
- No code, no migration, no rename has been executed yet.
- Runs / bootstrap directories exist under each fixture but are
  empty; they populate during benchmark round one after code
  lands.

## Current structure (§19.1 prerequisites complete)

```
portrait_qualification/
├── README.md                          # this file
├── CANONICAL_IDENTITY_CONTRACT_V1.md  # identity anchor contract
│
├── schemas/                           # declarative configuration
│   ├── human_identity_schema_v1.yaml  # required_for_identity +
│   │                                  # surface_requirements
│   ├── non_human_test_schema_v1.yaml  # non-canonical, per §17.2.b
│   ├── surface_profiles/              # Compact / Presence / Studio
│   │                                  # / Conversation / Team Card
│   ├── purpose_schema_human_v1.yaml   # portrait_reference purposes
│   └── background_family_v1.yaml      # controlled backgrounds §18
│
├── scoring/                           # evaluation instrument
│   ├── SCORING_SCHEMA_V1.md           # human-readable
│   ├── scoring.schema.json            # machine validation
│   └── scoring-template.yaml          # canonical reviewer template
│
├── fixtures/                          # benchmark identity fixtures
│   ├── README.md                      # catalog index (authorship-
│   │                                  # sequence ordering only)
│   ├── FIXTURE_AUTHORING_GUIDE_V1.md
│   ├── fixture_h1/                    # straightforward human
│   │   ├── identity.yaml
│   │   ├── rationale.md
│   │   ├── bootstrap/
│   │   │   └── references/            # approved bootstrap set
│   │   └── runs/
│   │       └── <benchmark_run_id>/
│   │           └── <direction>/
│   │               └── <provider>/
│   │                   ├── raw/
│   │                   ├── normalized/
│   │                   ├── manifests/
│   │                   ├── observations/
│   │                   └── scores/
│   ├── fixture_h2/                    # facial-hair coverage
│   ├── fixture_h3/                    # deliberately difficult case
│   ├── fixture_h4/                    # demographic contrast
│   └── fixture_nh1/                   # non-human substrate exercise
│
└── decisions/                         # ratified outcomes with
    └── PORTRAIT_TERRITORY_STUDY_V2.md # evidence links (eventual)
```

Semantics recorded elsewhere:

- Fixture directory separation (definition / bootstrap references /
  per-run evidence) is ratified in
  `CANONICAL_IDENTITY_CONTRACT_V1.md` §17.8.a Amendment 1.
- Fixture identifiers (`fixture_h1`, `fixture_nh1`, …) are
  canonical and immutable per §17.8.b — no personal names.
- Every benchmark run lives under its own `benchmark_run_id`
  subtree; later rounds do not overwrite earlier evidence.
- Scoring records are append-only and carry immutable metadata
  per §17.7.a.

---

## What does not belong here

- Any visual-design authorship that could invalidate benchmark
  evidence (Typography, Color and Light, Home Visual Canonical,
  Default Alex casting) — blocked per SESSION 238.
- Any marketing material, vendor documentation, or provider
  self-description masquerading as evidence.
- Any cherry-picked "hero" outputs from a provider's public demos —
  the selection discipline in
  SESSION 238 §"Selection discipline" (internal handoff, preserved privately)
  rules these out categorically.

---

## Revision History

**scaffold — 2026-08-06.** Directory created. Only the identity
contract exists so far. All other subdirectories are prospective.
