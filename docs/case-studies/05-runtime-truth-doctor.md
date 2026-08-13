# Case Study 05 — Runtime-truth doctor

**Date:** SESSION 147 (drift audit), SESSION 159 (context-kit
`handoff write`), SESSION 222 (`manage.py doctor`).
**Systems:** anchor docs, `CHARACTER_OS_INVENTORY.md`, CI.

## Problem

Character OS has anchor docs — `CHARACTER_OS_INVENTORY.md`,
`CHARACTER_OS_PIPELINE.md`, `CHARACTER_OS_BEHAVIOR_LAYER.md`,
and others — that describe runtime state. Each was intended to
be re-stamped per session so it stayed current with the code.

A SESSION 147 drift audit found that only one of the five
anchor docs had been consistently restamped across the
preceding 50+ sessions. The others sat at `generated:
2026-05-13` — three months stale — while the code they
described had moved on substantially.

## Evidence

- Manual inspection of anchor doc frontmatter.
- Comparison of doc-claimed model counts vs actual
  `python manage.py inventory` output — divergence of 40+
  models across three docs.
- Handoff prose in some sessions cited stale doc snapshots,
  propagating the drift into decision-making.

## Root cause

No programmatic check for anchor-doc freshness. The discipline
of "restamp at session end" was a manual habit that only one
doc had inherited; the others were forgotten because nothing
enforced them.

## Decision

Don't rely on the operator to remember. Build a doctor.

Two doctors, in fact — one at the operator layer, one at the
project layer:

1. **context-kit `handoff write` CLI subcommand** (SESSION 159,
   built in the sibling `context-kit` tool repo) — auto-scans
   anchor docs at session close and restamps their frontmatter
   dates.
2. **`python manage.py doctor`** (SESSION 222) — the in-repo
   runtime-truth check. Any doc that carries
   `status: regenerated` + `git_sha` + `generated_at`
   frontmatter is picked up. SHA equality is clean. SHA
   mismatch with fresh `generated_at` is advisory. SHA
   mismatch beyond `--max-stale-age-days` blocks.

## Implementation change

- `shell/apps/accounts/management/commands/doctor.py` — the
  runtime-truth doctor.
- Anchor docs given `status: regenerated` + `git_sha`
  frontmatter that their generator commands stamp.
- `CHARACTER_OS_INVENTORY.md` was the first consumer; its
  generator is `python manage.py inventory`.
- CI workflow `.github/workflows/verify-doc-claims.yml` gates
  merges on `scripts/verify_doc_claims.py --fail-on-drift`.

## Verification

Post-SESSION 222, session-boot workflow starts with `python
manage.py doctor` (in-repo) followed by `context-kit doctor`
(wider surface). Drift is caught before slice work begins;
regenerating the reported doc is a one-command fix.

## Lasting rule

**Every doc that claims runtime facts must own a generator and
be checked programmatically.** Manual restamp discipline
decays. SHA-stamped frontmatter + a doctor turns doc-code drift
into a build failure instead of a Trust me, it's current bet.

This pattern generalizes — the SESSION 221 assessment framed
the doctor as a project-general capability, not an INVENTORY-
specific hack. New runtime-mirror docs opt in by adding the
frontmatter fields.
