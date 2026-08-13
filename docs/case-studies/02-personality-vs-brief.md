# Case Study 02 — Personality ÷ business_brief

**Date:** SESSION 175.
**Systems:** `Teammate` model, K6 script synthesis, wizard,
edit modal.

## Problem

A single `personality` field on the `Teammate` model was doing
two jobs. Operators couldn't swap the business description
without also touching voice/tone — a common workflow (rename
the product, keep the same spokesperson voice) was clumsy.

## Evidence

Dogfood pattern: operator wanted to reuse Marcus (mascot,
motivational-coach voice) for a second business. Every attempt
required editing the combined field and re-baking the K6 script
because the tone drifted with the business rewrite.

Operator insight during a SESSION 174 voice-telemetry
follow-up: *"they should be treated differently."*

## Root cause

The `personality` field conflated:

- **HOW the teammate speaks** — voice, mannerisms, cadence,
  archetype.
- **WHAT the business is about** — product, audience, offer,
  positioning.

The K6 script synthesis prompt was pulling both from one field,
so any business rewrite silently reshaped the voice.

## Decision

Split into two fields. `personality` becomes tone-only.
`business_brief` becomes the substantive product/business
description. K6's prompt fences them separately.

## Implementation change

- Migration added `business_brief` field on `Teammate`, backfilled
  from existing `personality` where the content was substantive.
- K6 system prompt updated:
  `personality` → "voice guidance, do not restate facts";
  `business_brief` → "product/business substance for grounded
  synthesis".
- Wizard split into two labeled inputs.
- Edit modal split.
- SPA labels updated ("Personality" → "How they speak";
  "Business brief" → "What they do").

## Verification

Operator exercised the split on Marcus post-SESSION 175 —
swapped business_brief without re-baking voice; K6 output
stayed on-tone with the new business substance.

## Lasting rule

**Watch for fields doing two jobs.** When an operator's mental
model splits a concept that the code has fused, the code is
wrong. Migration cost is one session; the friction of a fused
field is every future edit forever.

The compat mirror on the canonical Identity substrate (SESSION
241+) keeps both fields threaded through the new world.
