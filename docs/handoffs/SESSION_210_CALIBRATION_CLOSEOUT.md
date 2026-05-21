---
title: "Session 210 — SESSION 209 calibration closeout (6 ½-slices)"
date: 2026-05-21
status: complete
session: 210
previous_handoff: ./SESSION_209_PIVOT_AND_BRAND_V3.md
---

# Session 210 — Calibration closeout

## TL;DR

SESSION 209 ended with **four operational calibration
findings** stacked on the queue and zero of them fixed.
SESSION 210 closed all four — plus the operator-facing
companion to the last one — in **six ½-slices, all in one
session**.

The pattern was the same one B2.5 / BC4 / V3.5 already
proved: when the work decomposes into small, well-scoped
units with clean acceptance criteria, you can stack them
without re-orienting between each. No subagent dispatched
this session; everything ran inline.

| # | Commit | Slice | Closes |
|---|---|---|---|
| 1 | `e2af47f` | aggregate `knowledge_chunk_ids` at completion | Finding #1 (broadened) |
| 2 | `e48d07f` | media-engine intro/outro card auto-wrap | Finding #4 |
| 3 | `d0adf76` | recipe form "Topic" relabel + tighter helper copy | Finding #2 |
| 4 | `7e20e31` | storage-health badge on Videos library rows | Finding #3 (visibility half) |
| 5 | `562e16d` | hourly expired-asset Beat sweep | Finding #3 (auto-fix half) |
| 6 | `000dd94` | operator-facing `sweep_expired_assets` command | Operator manual trigger |

All 4 SESSION 209 calibration findings → **closed**. The
expired-asset story is now complete end-to-end: badge
(operator sees), Beat (auto-fixes hourly at :07), command
(operator fixes immediately).

## Test deltas

| Suite | Pre-session | Post-session | Delta |
|---|---|---|---|
| Django | 1343 | 1364 | +21 (chunk_ids aggregator 8 · sweep 11 · v15_api row 1 · v15_api storage_health 1) |
| Media-engine | 214 | 221 | +7 (intro/outro card wrap tests) |
| SPA vitest | 455 | 456 | +1 (storage-health badge test) |
| **Total** | **2012** | **2041** | **+29** |

## Per-slice notes

### Slice 1 — `_aggregate_knowledge_chunk_ids` (commit `e2af47f`)

The SESSION 209 finding said only `talking_head` was
affected, but inspection broadened scope: **every
`use_knowledge=True` render not anchored in a Script-row
lineage** was writing chunks to `Asset.source_spec.
knowledge_chunk_ids` and never aggregating to
`Composition.knowledge_chunk_ids`. F-arc brief-mode panel,
BC4 lineage, K6.4 verifier panel — all broken on single-step
+ multi-step recipes alike (talking_head, talking_head_polished,
long_form_ad, storyboard_voiced).

Fix: post-completion aggregator in `apps/compositions/tasks.py`
that walks `composition.produced_assets`, unions every
asset's `source_spec.knowledge_chunk_ids`, dedupes, and
writes to `Composition.knowledge_chunk_ids`. Stable
ordering (existing entries first → newly-discovered ids
sorted) preserves BC2 Script-lineage carry-up.

8 tests in `test_chunk_id_aggregator.py`. Sanctioned write
to composition tables → `test_isolation.py` whitelisted.

**Calibration:** the finding's original scope was
under-inclusive. Once you find one render variant with a
data-flow bug, audit *every* variant that writes to the
same target.

### Slice 2 — Intro/outro card auto-wrap (commit `e48d07f`)

The SESSION 209 finding: a single long line "Now accepting
briefs, email jessica@247globalai.com — spaces are limited,
first come first serve" clipped horizontally on the V8
canvas. Operator workaround during the dogfood was manual
`\n` injection; doesn't scale.

Fix: `media-engine/app/routers/internal.py` gains
`_wrap_card_text(text, canvas_w, font_size) -> str` that
pre-wraps the operator-supplied string using `textwrap` with
a per-canvas character budget (`int(canvas_w * 0.80 /
(0.55 * font_size))`). Applied to both the intro and outro
write sites. Preserves operator newlines verbatim (multi-line
input gets re-wrapped line-by-line, not joined-then-wrapped).

7 new tests in `test_intro_outro_endpoint.py`: short text
unchanged, long text wraps, operator newlines preserved,
narrower canvas wraps sooner, larger font wraps sooner,
empty input unchanged, 12-char floor.

### Slice 3 — "Topic" relabel + tighter helper (commit `d0adf76`)

The SESSION 209 finding: when knowledge mode is on, the
operator types a "Script" but K6 throws their text away and
re-synthesizes from retrieved chunks. The label said
"Script" — operators got blindsided when their words didn't
appear in the render.

Fix: in `web/src/routes/recipes/$kind.tsx`, the form's
`FieldRenderer` checks `briefModeHelper`; when on,
`displayLabel` becomes `"Topic"` with a `— knowledge mode`
inline tag (italic gold), and the help text leads with
"**This is a topic, not a script.** When knowledge mode is
on, gpt-5-mini reads the workspace docs and writes the
spoken lines for you…" so the contract is impossible to miss.

Pure SPA. +1 vitest. Brief-mode helper testid preserved for
the existing test.

### Slice 4 — Storage-health badge (commit `7e20e31`)

The SESSION 209 finding: operators have no way to see in the
Videos library which renders' Runway CDN URLs have expired
until they click in and 404. The list page should surface
it.

Fix: `CompositionListSerializer` gains a
`final_asset_storage_health` `SerializerMethodField` that
calls `compute_storage_health(composition.final_asset)` and
returns one of `https_live / https_expiring_soon /
https_expired / local_present / local_missing / data_uri /
upload_pending` or null. Front-end Zod schema mirrors via
`STORAGE_HEALTH_VALUES` enum. New `StorageHealthBadge`
component on the Videos library row renders **only for
unhealthy states** (no noise on every row): `expiring soon`
(amber), `expired` (red), `missing` (red), `no media`
(muted).

1 new vitest covering 5 health states (3 unhealthy → 3
badges, 2 healthy/null → 0 badges). Backend list-row test
in `test_v15_api.py` extends to verify the new field shape.

### Slice 5 — Expired-asset Beat sweep (commit `562e16d`)

The SESSION 209 finding's auto-fix half. Runway-signed
Cloudfront URLs carry a 24h JWT `exp`; once past, the
Composition row still claims to have a deliverable, but
clicking it 404s.

Fix: `apps/compositions/tasks.py` gains
`sweep_expired_assets()` Celery task — walks
`Asset.objects.filter(file_path__startswith="https://")`,
classifies each row via `compute_storage_health`, and for
every `HTTPS_EXPIRED` it SET_NULLs every Composition's
`final_asset` FK pointing at the row. Asset row itself is
preserved (cost provenance + Asset Library "expired" badge
stays).

First entry in `CELERY_BEAT_SCHEDULE` — fires hourly at
:07. The project had no Beat schedule before this slice.
Beat needs its own process locally (`celery -A character_os
beat`).

8 new tests in `test_expired_asset_sweep.py` covering live /
expired / expiring-soon / no-asset / local / idempotency /
mixed-pass / asset-preservation paths. Sanctioned write →
whitelisted.

### Slice 6 — Operator-facing `sweep_expired_assets` command (commit `000dd94`)

The Beat task fires at :07. If the operator spots an expired
row at :30, they shouldn't wait 37 minutes. Companion
management command lets them clean up now.

Refactored `sweep_expired_assets` Celery task into a thin
wrapper around `run_expired_asset_sweep(commit=True)`. The
new `commit` kwarg defaults `True` for the Beat path; the
new management command at `apps/compositions/management/
commands/sweep_expired_assets.py` calls
`run_expired_asset_sweep(commit=options["commit"])` so
behavior parity is structural.

Defaults to **dry-run** (mirrors `backfill_asset_roles`
discipline — no silent writes). `--commit` applies. Prints
`DRY-RUN` / `COMMIT` banner + scanned/expired/detached + a
capped 20-row preview of asset IDs.

3 new tests covering core dry-run path, command default,
command `--commit`. Verified against the real DB: 10 HTTPS
assets scanned, 0 currently expired (operator did the
manual cleanup earlier in SESSION 209).

## What didn't happen

- **VO-arc scope lock** — still queued. Was Candidate C in
  the SESSION 210 start-here doc; preferred to close the
  Candidate A + Candidate B stack first.
- **Asset upload UI** — still queued.
- **Tier 2 ingest for PD + DF** — still blocked on source
  docs.
- **Keeper rename + profile setup** — operator-driven; no
  AI action this session.
- **Light mode (Q-v3-2)** — V3 deferral still queued.

## What's next (SESSION 211 candidates)

The SESSION 209 findings queue is now empty. The next FIRST
THING is operator pick. Three options weighted by impact:

1. **VO-arc scope lock** (½ session) — post-hoc voiceover
   insertion at specific time offsets. Unblocks ad recipes
   that need a different speaker for the CTA line. Doc-only,
   no code. Recommended next if no other strong signal.

2. **Asset upload UI** (1-2 sessions) — biggest unblocker.
   Once operators can upload their own clips/audio/images,
   several v2 recipes become viable.

3. **Light mode** (1 session) — Q-v3-2 from the V3 arc. Pure
   token / data-brand swap; small risk because V3
   architected this in.

## Calibration moments worth carrying

- **"Real-mode finds bugs in every arc" streak: 10-for-10.**
  SESSION 209's dogfood surfaced 4 findings; SESSION 210
  closed all 4. The streak isn't just "real-mode finds bugs";
  it's "the next session can close them in stacked ½-slices
  if the findings are well-scoped." The SESSION 209 handoff
  did half the SESSION 210 work by writing the findings as
  fix-shaped candidates rather than as bug reports.

- **A single-render finding usually has broader scope.**
  Slice 1's chunk_ids fix was originally scoped to
  `talking_head`; inspection broadened it to every
  `use_knowledge=True` recipe. Pattern: when you find a
  data-flow bug, audit every code path that writes to the
  same target before fixing.

- **Doc-discipline pays off mid-session, not just at end.**
  Per-slice handoff updates in the start-here doc kept
  SESSION 210 from spiraling — every "keep going" had a
  clearly-defined next item to grab. The handoff was the
  work plan.

- **Operator + Beat + manual command is the right shape for
  background reconciliation.** The expired-asset story shows
  the pattern: a *visibility* surface (badge), a *recurring
  fix* (Beat hourly), and a *manual override* (management
  command). Each piece independently shippable; together
  they cover every operator scenario.

- **First Celery Beat schedule entry in the project.** Worth
  carrying forward as a precedent — Beat is now part of the
  local-dev surface, and `infra/docker-compose.yml` plus the
  ops runbook needs to know there's a third Celery process
  (worker + Beat + the existing scheduler).

- **Management command dry-run-by-default discipline.** Both
  `backfill_asset_roles` (SESSION 185) and now
  `sweep_expired_assets` (this session) default to dry-run +
  require `--commit`. This pattern should be canonical for
  any future destructive / mass-update management command.

## Test counts at SESSION 210 close

| Suite | Count |
|---|---|
| Django | 1364 (+21 vs SESSION 209) |
| Media-engine | 221 (+7) |
| SPA vitest | 456 (+1) |

INVENTORY regenerated against `000dd94` (Celery task count
9 → 10).

**One env-issue caveat**: 3 tests in
`apps/scripts/tests/test_api.py` fail without
`EMBEDDING_FORCE_MOCK=1` set in the env (they hit the real
embedding service path and require `OPENAI_API_KEY`).
Running with `set -a && source ../.env && set +a &&
EMBEDDING_FORCE_MOCK=1 pytest` yields 1364/1364 clean. Pre-
existing env-shape issue, not from this session.
