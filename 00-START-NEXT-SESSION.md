---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`.
> **Brand identity lock (current):** `docs/design/BRAND_IDENTITY_V3.md` —
> editorial dark-luxe; V2 superseded SESSION 209.
> **Parent-company anchor:** `docs/247_GLOBAL_AI_OVERVIEW.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer:** `docs/design/KNOWLEDGE_LAYER.md`.
> **Video composition:** `docs/design/VIDEO_COMPOSITION_V1.md`.
> V0-V18 COMPLETE.
> **Realtime avatar:** `docs/design/REALTIME_AVATAR_V1.md`.
> R0-R10 + R6.1 COMPLETE.
> **Workspace fabric:** `docs/design/WORKSPACE_FABRIC_V1.md`.
> F0-F10 COMPLETE.
> **Media generation:** `docs/design/MEDIA_GENERATION_V1.md`.
> W11.6.0-W11.6.5 COMPLETE.
> **Asset Library:** `docs/design/ASSET_LIBRARY_V1.md`.
> A0-A8 COMPLETE.
> **Transcript Miner (B-1):** `docs/design/TRANSCRIPT_MINER_V1.md`.
> B1.0-B1.7 COMPLETE.
> **Personalized Video (B-3):** `docs/design/PERSONALIZED_VIDEO_V1.md`.
> B3.0-B3.9 COMPLETE.
> **Publish Bundle (B-14):** `docs/design/PUBLISH_BUNDLE_V1.md`.
> B14.0-B14.5 COMPLETE.
> **Auto-Scripting (B-2):** `docs/design/AUTO_SCRIPTING_V1.md`.
> B2.0-B2.6 COMPLETE.
> **B-2 ↔ B-3 Composition:** `docs/design/B2_B3_COMPOSITION_V1.md`.
> BC0-BC4 SHIPPED; **BC5 CANCELLED SESSION 209** (pivot wiped data).
> **BRAND IDENTITY V3:** `docs/design/BRAND_IDENTITY_V3.md`.
> **V3.0-V3.9 COMPLETE + REAL-MODE DOGFOOD VALIDATED (SESSION 209).**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory --write` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_209_PIVOT_AND_BRAND_V3.md`.

---

## SESSION 209 outcome — strategic pivot + V3 brand arc shipped

Largest session since Phase 4. Started as BC5 dogfood;
pivoted to clean-slate keeper + Tier 1/2 knowledge + entire
V3 brand arc in one push.

**15 code/doc commits + ~$2.00 real-mode spend + 6 renders +
1 sub-arc subagent-delivered.**

### What landed

| Workstream | Commits |
|---|---|
| Scripts list Zod fix · Nav rail 5→11 · Videos library | `86f002f` `bab6b93` |
| Strategic pivot, keeper, Tier 1 corpus, validation | `06dc794` `1dc603f` |
| **BRAND_IDENTITY_V3 arc (10 slices V3.0–V3.9)** | `f2b32be` → V3.9 (this commit) |

Plus 4 TRUST_CALIBRATION entries (expired-asset purge gap;
chunk_ids propagation bug, broadened to all knowledge-grounded
recipes; K6 brief-replaces-script surprise; outro card text
no-wrap clipping).

Full session detail in
`docs/handoffs/SESSION_209_PIVOT_AND_BRAND_V3.md`.

### Workspace state

- **1 spokesperson:** 24/7 Global AI (`d3d0fb14-...`).
- **37 KnowledgeDocuments / 884 chunks** (7 Tier 1
  editorial summaries + 29 Tier 2 deep corpus across
  4 sibling projects + 1 trafilatura research carryover).
- **6 compositions** (5 brand-on pitch variants + 1 V3.9
  dogfood; ~$1.50 visible in Videos library).
- 0 RT sessions / scripts / campaigns / bundles /
  transcripts / raw uploads.

### Test counts at SESSION 209 close

| Suite | Count |
|---|---|
| Django | 1343 (unchanged — no backend changes this session) |
| Media-engine | 214 (unchanged) |
| SPA vitest | 455 (+29: V3.2 primitives + V3.4-V3.8 fixture adjustments) |

---

## FIRST THING (SESSION 210): TBD — operator picks

Three flavors of work queue up for SESSION 210. AI
recommends Candidate A (the chunk_ids patch) since it's
small, surgical, and unblocks every SPA citation surface.

### Candidate A — `knowledge_chunk_ids` propagation patch (½ slice) — RECOMMENDED

The SESSION 209 calibration finding (Tier 1 + Tier 2
dogfood) surfaced: every `use_knowledge=True` render not
anchored in a Script-row lineage writes chunks to the
final Asset's `source_spec.knowledge_chunk_ids` but never
aggregates to `Composition.knowledge_chunk_ids`. SPA
citation surfaces (F-arc brief-mode panel, BC4 lineage,
verifier panel) fail for single-step renders.

Fix: post-completion aggregator that walks produced
assets' `source_spec.knowledge_chunk_ids` for ALL
recipes, dedupes, writes to
`Composition.knowledge_chunk_ids`. Generic — applies to
talking_head, talking_head_polished, long_form_ad,
storyboard_voiced, and any future knowledge-grounded
recipe. ~20-30 LOC + tests.

**Why first:** Small + surgical. Unblocks SPA surfaces
that have been broken since SESSION 209. Cheap to ship
before bigger arcs.

### Candidate B — V3.x polish slices (½-1 session)

V3 shipped end-to-end but a few polish items deferred:

1. **Brief-replaces-script SPA copy pass** (½ slice) —
   recipe form labels: "Script" → "Topic" on grounded
   variants. Surface estimated duration after synthesis.
2. **Outro/intro card auto-wrap** (½ slice) —
   `media-engine/app/routers/internal.py:_build_card_filter`
   gains `textwrap.wrap`. ~10 LOC.
3. **Storage-health filter on Videos library** (½ slice).
4. **Expired-asset Celery Beat sweep** (½ slice).

Each is independent and could be subagent-delivered if
batched.

### Candidate C — VO-arc scope lock (½ session)

Post-hoc voiceover insertion at specific time offsets.
The SESSION 209 finding noted this as a queued arc;
scope-lock first per the V-arc / R-arc cadence.

### Parallel work (operator-driven, ongoing)

- **Keeper rename** — placeholder "24/7 Global AI"
  still active; operator considering alternatives.
- **Keeper profile** — set `personality`,
  `tone_archetype`, bio fields from the SPA at
  `/spokespeople/d3d0fb14-193e-4c4c-88d1-acae9af25bb5`.

---

## Slice queue (after FIRST THING)

### Newly queued (from SESSION 209)

| | Slice | Effort |
|---|---|---|
| 1 | `knowledge_chunk_ids` propagation patch (broadened scope) | ½ slice |
| 2 | Brief-replaces-script SPA copy pass | ½ slice |
| 3 | Outro/intro card auto-wrap | ½ slice |
| 4 | Storage-health filter on Videos library | ½ slice |
| 5 | Expired-asset Celery Beat sweep | ½ slice |
| 6 | VO-arc — post-hoc voiceover insertion | 2 sessions (scope + impl) |

### V3 deferrals (post-arc, non-blocking)

| | Item | Effort |
|---|---|---|
| 7 | Light mode (Q-v3-2) | 1 session |
| 8 | Tailwind 4 migration | ½ session |
| 9 | Animation perf measurement on dashboard | small |
| 10 | Per-workspace branding via `data-brand` swap | 1 session |

### Still queued (unchanged by SESSION 209)

| | Slice | Effort |
|---|---|---|
| 11 | Asset upload UI | 1-2 sessions |
| 12 | F8.1 — K10 seed corpus | blocked |
| 13 | K7.x v3 YouTube oEmbed | queued |
| 14 | K6.4 v3 architectural fix | queued |
| 15 | W12 legacy form retirement | queued |
| 16 | B-2 v2 `auto_script_polished` + `auto_script_cinematic` | queued |
| 17 | Path B — composition soft-delete via `archived_at` | 1 session |
| 18 | Tier 2 ingest for PD + DF | blocked on source docs |
| 19 | Recipe gallery copy + grouping pass | ½ session |

### Composition arc candidates

| | Arc | Effort |
|---|---|---|
| 20 | B-2 ↔ B-14 (Script-grounded publish bundles) | ~½ regular arc |
| 21 | B-1 ↔ B-3 (Transcript-mined → personalized batch) | ~½ regular arc |
| 22 | B-3 ↔ B-14 (Per-recipient platform fan-out) | ~½ regular arc |

---

## Where we are

**Phases 0-3:** Done.
**Phase 4:** All four arcs (K / V / F / R) complete; BC
arc partially (BC0-BC4 shipped, BC5 cancelled).
**Phase 5 (brand):** **BRAND_IDENTITY_V3 COMPLETE.**

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
| BC0-BC5 | BC0-BC4 SHIPPED; BC5 CANCELLED SESSION 209 |
| Knowledge Ingest Tier 1 (7 KDs) | DONE SESSION 209 |
| Tier 2 (charos/CK/MF/CC — 29 KDs / 871 chunks) | DONE SESSION 209 |
| Tier 2 for PD + DF | Blocked on source docs |
| 24/7 Global AI keeper spokesperson | DONE SESSION 209 |
| **BRAND_IDENTITY_V3 arc (V3.0-V3.9)** | **DONE + REAL-MODE VALIDATED SESSION 209** |
| `knowledge_chunk_ids` propagation patch | Queued (½ slice) |
| Brief-replaces-script SPA copy pass | Queued (½ slice) |
| Outro/intro card auto-wrap | Queued (½ slice) |
| Storage-health filter / expired Celery Beat sweep | Queued |
| VO-arc | Queued (2 sessions) |

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis :6381 + Postgres :5433

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

**Inventory regen** (after any backend model / route / Celery task change):

```bash
cd shell && python manage.py inventory --write
```

**HARD REQUIREMENTS:**

1. Django runserver (`.env` sourced)
2. SPA `pnpm dev` :5174
3. Redis (docker)
4. Celery worker (`.env` sourced)
5. Media-engine for real-mode renders

**Smoke checks** (counts as of SESSION 209 close):

```bash
# Backend (from shell/)
python -m pytest                              # 1343 tests

# Media-engine (from media-engine/)
python -m pytest                              # 214 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 455 vitest tests
```

---

## AI / assistant context

- **Last session: SESSION 209 — strategic pivot + V3
  brand arc.** Started as BC5 dogfood. Pivoted to
  clean-slate keeper rebuild + Tier 1/2 knowledge
  corpus + the entire 10-slice BRAND_IDENTITY_V3 arc.
  15 commits, ~$2.00 real-mode spend. V2 superseded;
  V3 active.

- **Calibration carried forward (41 + 4 new from
  SESSION 209):** expired-asset accumulation has no
  purge mechanism · `use_knowledge=True` doesn't
  propagate chunk_ids to Composition (any recipe) ·
  K6 brief replaces operator script as spoken text ·
  outro/intro card text no-wrap clipping.

- **"Real-mode finds bugs in every arc" pattern is
  now 9-for-9.** SESSION 209's V3 dogfood validated
  that the editorial register doesn't regress the
  composition pipeline (V3 is purely visual).

- **Subagent delivery on tight contract briefs is
  3-for-3** (B2.5 + BC4 + V3.5). The V3.5 18-route
  brief was the largest yet and shipped clean.

- **A canonical external source compresses arc cycle
  time.** V3 was estimated 4-5 sessions; shipped in
  1 thanks to `/24-7-ai-global/` as the canonical
  port source.

- **The CSS-var indirection for fonts + colors lets
  `data-brand` swap brand identities atomically.**
  V1 / V2 / V3 all preserved; flipping `data-brand`
  swaps the entire visual identity with no redeploy.

- **Cross-product references in editorial-summary
  copy retrieve better than deep design docs.**
  Future Tier 1 seed copy should keep product
  summaries explicitly cross-referenced.

- **Editorial dark-luxe register exceeded
  expectations** during the V3 dogfood — multiple
  operator confirmations during the slice run ("it
  looks amazing"). Brand decisions should lean
  editorial not generic-SaaS where the parent
  narrative supports it.

- Collaboration: AI drafts, human edits. Per-slice
  doc updates required at session end (codified
  SESSION 143). Handoff `## Calibration moments
  worth carrying` required at session end.
