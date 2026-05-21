---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`.
> **B0-B5 SHIPPED; B6-B10 deferred.**
> **Brand identity lock (current):** `docs/design/BRAND_IDENTITY_V2.md`.
> **Parent-company anchor:** `docs/247_GLOBAL_AI_OVERVIEW.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer:** `docs/design/KNOWLEDGE_LAYER.md`.
> **Video composition:** `docs/design/VIDEO_COMPOSITION_V1.md`.
> V0-V18 COMPLETE + 18/18 RECIPES REAL-MODE VALIDATED.
> **V-arc UX polish COMPLETE (SESSION 200).**
> **Realtime avatar:** `docs/design/REALTIME_AVATAR_V1.md`.
> R0-R10 + R6.1 COMPLETE + REAL-MODE HARDENED.
> **Workspace fabric:** `docs/design/WORKSPACE_FABRIC_V1.md`.
> F0-F10 COMPLETE; F8.1 queued.
> **Media generation:** `docs/design/MEDIA_GENERATION_V1.md`.
> W11.6.0-W11.6.5 + sub-slices 1/2/3 COMPLETE.
> **Asset Library:** `docs/design/ASSET_LIBRARY_V1.md`.
> A0-A8 COMPLETE + DOGFOOD VALIDATED.
> **Transcript Miner (B-1):** `docs/design/TRANSCRIPT_MINER_V1.md`.
> B1.0-B1.7 COMPLETE + REAL-MODE VALIDATED.
> **Personalized Video (B-3):** `docs/design/PERSONALIZED_VIDEO_V1.md`.
> B3.0-B3.9 COMPLETE + REAL-MODE VALIDATED.
> **Publish Bundle (B-14):** `docs/design/PUBLISH_BUNDLE_V1.md`.
> B14.0-B14.5 COMPLETE + REAL-MODE VALIDATED.
> **Auto-Scripting (B-2):** `docs/design/AUTO_SCRIPTING_V1.md`.
> B2.0-B2.6 COMPLETE + REAL-MODE VALIDATED.
> **B-2 ↔ B-3 Composition:** `docs/design/B2_B3_COMPOSITION_V1.md`.
> BC0-BC4 SHIPPED (SESSION 208).
> **BC5 dogfood CANCELLED (SESSION 209 pivot — data wiped).**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Working scratch:** `docs/SESSION_209_PLANNING.md` —
> full pivot record, scheduled for distillation + delete.
> **Last handoff:** `docs/handoffs/SESSION_208_BC_ARC_LANDS.md`
> (SESSION 209 handoff pending at session close).

---

## SESSION 209 outcome — strategic pivot

Started as BC5 dogfood. Pivoted mid-session to a
clean-slate rebuild around a single parent-company
spokesperson. **Six distinct workstreams shipped**:

| # | Workstream | Commit / artifact |
|---|---|---|
| 1 | Scripts list Zod contract drift fix | `86f002f` |
| 2 | Nav rail expansion (5 → 11) + Videos library (paginated `/workspace/videos`) | `bab6b93` |
| 3 | Runtime cleanup — 76 compositions / 195 assets / 13 RT sessions / 324 spokespeople / ~328 MiB disk freed | data-only, uncommitted |
| 4 | New "24/7 Global AI" keeper spokesperson created (real-mode Runway avatar, Marcus voice) | data-only |
| 5 | Tier 1 knowledge corpus — 7 KDs seeded from `/24-7-ai-global/products.ts`, 13 chunks embedded | data-only |
| 6 | **Tier 1 validation — RAG probes + real-mode render confirm corpus works end-to-end** | **calibration findings filed** |

Plus 3 TRUST_CALIBRATION entries appended:
expired-asset purge gap, `talking_head` chunk_ids
propagation bug, K6 brief-replaces-script design
surprise. Full session detail in
`docs/SESSION_209_PLANNING.md`.

### Current state of the workspace

- **1 spokesperson:** 24/7 Global AI (`d3d0fb14-...`),
  runway_avatar_id `f1e5cec2-...`, voice `david`,
  status `ready`, portrait at
  `_internal/avatar_portraits/f1e5cec2-...jpg`.
- **0 compositions, 0 RT sessions, 0 raw_uploads,
  0 transcripts, 0 campaigns, 0 bundles, 0 videos
  (legacy), 0 scripts.**
- **7 KnowledgeDocuments** seeded with editorial
  product summaries (Charter + 6 catalogued products).
- **13 embedded knowledge chunks** total.

### Real-mode spend SESSION 209

| | Cost |
|---|---|
| New avatar creation (Runway) | $0 (counted in monthly cap, no per-call charge) |
| First test render (`talking_head`, deleted in wipe) | $0.25 |
| Tier 1 embedding (`text-embedding-3-small`) | $0.00005 |
| Tier 1 validation render (`talking_head` with `use_knowledge=True`) | $0.25 |
| **Total** | **~$0.50** |

---

## FIRST THING (SESSION 210): TBD — operator picks

Tier 1 validation closed SESSION 209 (Candidate A
from the original list). Three new candidates for
SESSION 210. AI recommends Candidate A1 — the small
patch that emerged from validation findings.

### Candidate A1 — `talking_head` chunk_ids propagation patch (½ slice) — RECOMMENDED

The Tier 1 validation surfaced a real bug:
`talking_head` with `use_knowledge=True` writes the
retrieved chunk_ids to the final Asset's
`source_spec.knowledge_chunk_ids` but never aggregates
them up to `Composition.knowledge_chunk_ids`. Asymmetric
with `talking_head_polished` which DOES propagate.
SPA citation surfaces (F-arc brief-mode, BC4 lineage,
verifier panel) all fail for single-step renders.

**Fix:** post-completion aggregator that walks produced
assets' `source_spec.knowledge_chunk_ids` and dedupes
into `Composition.knowledge_chunk_ids`. ~10-20 LOC,
mirrors `talking_head_polished`'s carry-up at
`apps/compositions/starters.py:252`. Plus tests
asserting chunks land on the composition for both
starters.

**Why first:** Small, surgical, unblocks the
audit-trail surfaces. Cheap to ship before bigger arcs.

### Candidate B — Tier 2 knowledge ingest (1-2 sessions)

Walk each of the 6 project repos' `docs/` directories
and bulk-ingest. Per-project KnowledgeDocument with
chunk-level file metadata. Idempotent re-runs via
content hash. New management command:
`python manage.py ingest_project_docs <root>
[--reembed] [--dry-run]`.

**Pre-req:** scope-lock doc
`docs/design/KNOWLEDGE_INGEST_V1.md` (½ session).

**Why second:** Deeper corpus = more useful keeper. But
without Tier 1 validation we don't know which
direction the chunking strategy should lean.

### Candidate B2 — Brief-replaces-script SPA copy pass (½ slice)

Companion calibration finding from Tier 1 validation:
when `use_knowledge=True`, K6's `build_render_brief`
**replaces** the operator's script with a brand-voiced
expansion (120-char input → 557-char rendered text,
50.6s render). The current recipe form labels it
"Script" — implying "lines to speak." It should read
"Topic" or "What should the spokesperson talk about?"
on grounded variants. Plus surface an estimated
duration *after* synthesis, not from script length
pre-synthesis.

**Effort:** ½ slice. Audit recipe form copy across
all grounded recipes; add post-synthesis duration
preview in the SPA.

### Candidate C — Brand Identity v3 scope-lock (½ session)

Write `docs/design/BRAND_IDENTITY_V3.md` capturing the
editorial-dark-luxe direction discovered in
`/24-7-ai-global/`. Ink/gold palette, Bodoni Moda
display, section dossier numbering, "Plate 01" /
"Proprietor" / "Reply by morning" voice patterns.

Sequencing for actual re-skin (1-2 sessions) follows
in SESSION 211+.

**Why third:** Significant work but doesn't block any
keeper functionality. Pure UX layer.

### Parallel work (operator-driven, ongoing)

- **Keeper profile** — set personality, tone_archetype,
  any free-form bio fields from the SPA at
  `/spokespeople/d3d0fb14-193e-4c4c-88d1-acae9af25bb5`.
- **Keeper rename** — pick the final name. "24/7 Donkey"
  was a placeholder.

---

## Slice queue (after FIRST THING)

### Dead (data was wiped — slice is now meaningless)

- ~~BC5 — composition arc dogfood + close~~
- ~~B-2 v2 polish slice~~ (no scripts to polish)
- ~~Composition-detail verifier panel polish~~ (no
  compositions to verify against)
- ~~Marcus rig re-bake~~ (Marcus gone)

### Still queued (unchanged by pivot)

| | Slice | Effort |
|---|---|---|
| 1 | Asset upload UI | 1-2 sessions |
| 2 | F8.1 — K10 seed corpus | blocked |
| 3 | K7.x v3 YouTube oEmbed | queued |
| 4 | K6.4 v3 architectural fix | queued |
| 5 | W12 legacy form retirement | queued |
| 6 | Storage-health filter on Videos library | ½ session |
| 7 | Expired-asset Celery Beat sweep | ½ session |
| 8 | B-2 v2 `auto_script_polished` + `auto_script_cinematic` | queued |
| 9 | Path B — soft-delete via `archived_at` | 1 session |
| 10 | VO-arc — post-hoc voiceover insertion | 2 sessions (scope + impl) |
| 11 | Recipe gallery copy + grouping pass | ½ session |

### New (added SESSION 209)

| | Slice | Effort |
|---|---|---|
| 12 | **Knowledge Ingest Tier 2 — deep per-project corpus** | 1-2 sessions (after scope-lock) |
| 13 | **Brand Identity v3 — editorial-dark-luxe re-skin** | 1-2 sessions (after scope-lock) |

### Composition arc candidates (deferred — need data)

| | Arc |
|---|---|
| 14 | B-2 ↔ B-14 (Script-grounded publish bundles) |
| 15 | B-1 ↔ B-3 (Transcript-mined recipients → personalized batch) |
| 16 | B-3 ↔ B-14 (Per-recipient platform fan-out) |

---

## Where we are

**Phases 0-3:** Done.
**Phase 4:** All four arcs complete; BC arc complete
(BC5 dogfood cancelled — data was the wrong shape for
the new direction).
**Workspace wiped to fresh slate** with a single
parent-company keeper spokesperson.

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V18 | DONE + REAL-MODE VALIDATED |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED |
| W11.6.0-W11.6.5 | DONE |
| A0-A8 | DONE + DOGFOOD VALIDATED |
| B1.0-B1.7 | DONE + REAL-MODE VALIDATED |
| B3.0-B3.9 | DONE + REAL-MODE VALIDATED |
| B14.0-B14.5 | DONE + REAL-MODE VALIDATED |
| B2.0-B2.6 | DONE + REAL-MODE VALIDATED |
| BC0-BC5 | BC0-BC4 SHIPPED; BC5 CANCELLED |
| **Knowledge Ingest Tier 1 (7 KDs seeded)** | **DONE SESSION 209** |
| **24/7 Global AI keeper spokesperson** | **DONE SESSION 209** |
| **Tier 1 validation (RAG + render end-to-end)** | **DONE SESSION 209 — 2 findings filed** |
| `talking_head` chunk_ids propagation patch | Queued (½ slice) |
| Brief-replaces-script SPA copy pass | Queued (½ slice) |
| Knowledge Ingest Tier 2 | Queued |
| Brand Identity v3 | Queued |

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381 + Postgres :5433

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
celery -A character_os worker --loglevel=info --pool=solo

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host localhost --port 8001 --reload

cd web && pnpm dev                          # :5174
```

**Session-start drift sweep:**

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**Inventory regenerate (after the wipe — INVENTORY is
heavily stale):**

```bash
cd shell && source .venv/bin/activate && python manage.py inventory --write
```

**HARD REQUIREMENTS** (promoted SESSIONS 193 + 200):

1. **Django dev server** — `runserver` from `shell/`
   with `.env` sourced.
2. **SPA dev server** — `pnpm dev` from `web/`. :5174.
3. **Redis** — `docker compose up -d` from `infra/`.
4. **Celery worker** — required for embeddings + any
   real-mode renders, **with `.env` sourced**.
5. **Media-engine** — required for real-mode renders
   (also for avatar creation, voice design, etc).

**Smoke checks** (counts as of SESSION 209 close):

```bash
# Backend (from shell/)
python manage.py inventory --write            # regenerate counts
python -m pytest                              # 1343+ tests (pagination + chunk_count added)

# Media-engine (from media-engine/)
python -m pytest                              # 214 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 434 vitest tests
```

**Pre-fire check** (codified SESSION 200, extended
through SESSION 209): restart Celery before any
real-mode fire when the last commit against ANY of
these is newer than worker start:

* `shell/apps/compositions/primitives/`
* `shell/apps/compositions/starters.py`
* `shell/apps/compositions/recipes.py`
* `shell/apps/compositions/views.py` (SESSION 209 — pagination + status filter)
* `shell/apps/compositions/serializers.py` (SESSION 209 — `CompositionListSerializer`)
* `shell/apps/scripts/serializers.py` (SESSION 209 — `knowledge_chunk_count` field)
* `shell/apps/*/signals.py`
* `shell/apps/*/models.py`
* `shell/character_os/clients/media_engine.py`

---

## AI / assistant context

- **Last session: SESSION 209 — strategic pivot.**
  Started as BC5 dogfood. Mid-session operator
  decided to wipe everything and rebuild around a
  parent-company keeper spokesperson. Shipped: 2
  feature commits (`86f002f` scripts fix +
  `bab6b93` Videos library + nav expansion). Plus
  data-only: full wipe (~700 rows), new 24/7 Global
  AI keeper, Tier 1 knowledge corpus (7 KDs). $0.25
  real-mode spend (test render, deleted).

- **Strategic context — parent-company marketing
  site discovered at `/Users/donkeyking/development/24-7-ai-global/`.**
  Six-product catalogue (4 shipped Suite +
  context-kit + Character OS). Editorial-dark-luxe
  brand language (ink/gold, Bodoni Moda, section
  dossier numbering, "Plate 01 / Proprietor" voice).
  Character OS will eventually re-skin to match.

- **Calibration carried forward (41 + 3 new from
  SESSION 209):** "expired-asset accumulation has no
  purge mechanism," "`talking_head` doesn't propagate
  knowledge_chunk_ids to the Composition row," "K6
  brief expansion replaces the operator script as
  the spoken text." All prior calibration still
  applies; the cast-is-example-data memory needs a
  light refresh since named cast (Riggs/Sasha/Donny/
  Marcus) is gone, but the *concept* still holds for
  the new keeper.

- **"Real-mode finds bugs in every arc" pattern is
  now 8-for-8.** SESSION 209's Tier 1 validation
  surfaced two findings on first fire (chunk_ids
  propagation bug + brief-replaces-script surprise).
  The pattern stands: every real-mode dogfood
  surfaces something. Schedule one at the close of
  every arc, no exceptions.

- **Subagent delivery on tight contract briefs is
  reliable.** Two-for-two going in (B2.5 + BC4).

- **Brand layer is load-bearing.** Every component
  must import company/product strings from
  `@/lib/brand`. When BRAND_IDENTITY_V3 lands,
  expect the brand layer to grow palette/typography
  tokens to match `/24-7-ai-global/`.

- **Collaboration conventions:** AI drafts, human
  edits. Handoff `## Calibration moments worth
  carrying` + per-slice doc updates required at
  session end.
