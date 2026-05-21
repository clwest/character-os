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
> SESSION 213 post-arc Q-r-2 fix shipped + SESSION 214 verified
> via real-mode dogfood (0× `recall_knowledge` in 2-min Rigby
> conversation across 4 product-info questions).
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
> **Voiceover (VO-arc):** `docs/design/VOICEOVER_V1.md`.
> **VO.0 + VO.1 SHIPPED SESSION 211; VO.2 SHIPPED SESSION 212**;
> VO.3-VO.6 queued.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_214_QR2_DOGFOOD_PLUS_EMBED_FIX.md`.

---

## SESSION 214 outcome — Q-r-2 dogfood verified + embed-cache fix

Two slices in one session. **+1 test, $0.16 real-mode spend.**

| Commit | Slice |
|---|---|
| (pending) | fix(embeddings): mock-mode bypasses cache to prevent real-mode poisoning |
| (pending) | docs: SESSION 214 close — Q-r-2 dogfood verified + embed-cache fix + inventory |

### What landed

- **Q-r-2 loop verified dead.** One 2-min Rigby session
  (`61c25661-87b3-459d-b2d8-3fd5bfc7b129`), 4 product-info
  questions, **0× `recall_knowledge` invocations** (pre-213
  baseline: 4× per thin-knowledge query). Rigby answered
  every question from the loaded document — top-K 30→50
  bump in Fix 3B was load-bearing; dispatch dedup (Fix 2A)
  was defense-in-depth and never needed to fire.
- **Embedding cache mock/real collision fixed.** Parallel CC
  flagged `shell/apps/embeddings/embedding_service.py` sharing
  cache keys between mock and real paths — mock-mode `cache.set`
  was silently poisoning real-mode `cache.get`. Mock mode now
  bypasses the cache entirely (Option B: eliminate by
  construction, since mock vectors are already deterministic
  from `sha256(text)`).
- **+1 regression test** —
  `test_mock_does_not_poison_real_mode_cache` — asserts mock
  doesn't leak vectors AND real-mode without `OPENAI_API_KEY`
  raises rather than silently returning the mock.
- **Other dogfood findings (non-blocking)**: greeting bias
  holds (memory `feedback_runway_avatar_greeting_bias`);
  cost ticker matches R9 rate exactly ($0.16 / 2 min);
  `render_video` modal flow works end-to-end (operator
  rejected Rigby's unprompted video offer cleanly);
  multilingual tolerance OK ("Conta, vem" Portuguese
  handled gracefully).

### Test counts at SESSION 214 close

| Suite | Count |
|---|---|
| Django | **1424** (+1 vs SESSION 213) |
| Media-engine | **258** (unchanged) |
| SPA vitest | **456** (unchanged) |

Full session detail in
`docs/handoffs/SESSION_214_QR2_DOGFOOD_PLUS_EMBED_FIX.md`.

---

## FIRST THING (SESSION 215): Operational housekeeping, then VO.3

### Step 1 — Embedding cache flush decision (≤ 5 min)

The SESSION 214 fix prevents new poisoning. Existing mock
vectors may still sit in Redis from prior mixed-mode runs
(30-day TTL). Three options for the operator:

1. **Full flush** of `text-embedding-3-small`-prefixed keys:
   ```bash
   docker exec character_os_redis redis-cli -n 0 \
       --scan --pattern 'text-embedding-3-small*' \
     | xargs -r docker exec -i character_os_redis redis-cli -n 0 del
   ```
   Next ingest pays re-embed cost on valid real-mode entries
   too. Clean state immediately. **Recommended.**
2. **Let it TTL** — 30 days of stale-mock-poisoned reads.
3. **Targeted flush** — no machine-readable way to identify
   which entries are which today.

### Step 2 — Decide on `scripts/ingest-udb-spokesperson-corpus.py`

Currently untracked. Two paths:

* Commit as the v1 reference (the script is functional and
  was used to populate the 939 chunks now in the DB).
* Defer until the parallel CC's docker bridge lands and may
  supersede this script's role entirely.

### Step 3 — DealFlowTracker confirmation run (optional)

SESSION 214 dogfood already proved the loop is dead in the
general case. The verbatim SESSION 213 plan called for an
explicit "Tell me about DealFlowTracker." run — the
thin-knowledge worst case from SESSION 212. Optional
belt-and-suspenders. Cost cap: $0.16 (one 2-min session).

### Step 4 — VO.3 (next queued FIRST THING from VO-arc)

`cta_swap` starter + recipe registry + `voice_picker` field
type. Effort: ½ session.

---

## Slice queue (after FIRST THING)

### VO-arc remaining slices

| | Slice | Effort |
|---|---|---|
| 1 | VO.3 — `cta_swap` starter + recipe registry + `voice_picker` field type | ½ session |
| 2 | VO.4 — `narrated_intro` starter + duration estimator helper | ½ session |
| 3 | VO.5 — SPA recipe gallery `voice_picker` (3-tab) wiring | 1 session |
| 4 | VO.6 — real-mode dogfood (keeper + Sasha CTA) + arc close | ½ session |

### Queued from SESSION 210 closeout

| | Slice | Effort |
|---|---|---|
| A | Asset upload UI | 1-2 sessions |
| B | Light mode (Q-v3-2) | 1 session |

### V3 deferrals (post-arc, non-blocking)

| | Item | Effort |
|---|---|---|
| 5 | Tailwind 4 migration | ½ session |
| 6 | Animation perf measurement on dashboard | small |
| 7 | Per-workspace branding via `data-brand` swap | 1 session |

### Still queued (unchanged)

| | Slice | Effort |
|---|---|---|
| 8 | F8.1 — K10 seed corpus | blocked |
| 9 | K7.x v3 YouTube oEmbed | queued |
| 10 | K6.4 v3 architectural fix | queued |
| 11 | W12 legacy form retirement | queued |
| 12 | B-2 v2 `auto_script_polished` + `auto_script_cinematic` | queued |
| 13 | Path B — composition soft-delete via `archived_at` | 1 session |
| 14 | Tier 2 ingest for PD + DF | blocked on source docs |
| 15 | Recipe gallery copy + grouping pass | ½ session |

### Composition arc candidates

| | Arc | Effort |
|---|---|---|
| 16 | B-2 ↔ B-14 (Script-grounded publish bundles) | ~½ regular arc |
| 17 | B-1 ↔ B-3 (Transcript-mined → personalized batch) | ~½ regular arc |
| 18 | B-3 ↔ B-14 (Per-recipient platform fan-out) | ~½ regular arc |

### Parallel-CC slices (out of this session's scope)

| | Slice | Owner |
|---|---|---|
| P1 | u-d-b ↔ character-os docker bridge | parallel CC |

---

## Where we are

**Phases 0-3:** Done.
**Phase 4:** All four arcs (K / V / F / R) complete; BC arc
partially (BC0-BC4 shipped, BC5 cancelled).
**Phase 5 (brand):** **BRAND_IDENTITY_V3 COMPLETE.**

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V18 | DONE + REAL-MODE VALIDATED |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED; **SESSION 214 Q-r-2 loop verified dead** |
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
| **VO-arc scope lock (VO.0)** | DONE SESSION 211 |
| **VO.1 — TTS provider + primitive + role enum** | DONE SESSION 211 |
| **VO.2 — `/internal/clips/overlay_audio/` + primitive** | DONE SESSION 212 |
| **Realtime Q-r-2 loop kill (Fix 2A/2C/3B)** | **DONE SESSION 213 + VERIFIED SESSION 214** |
| **Embedding cache mock/real collision fix** | **DONE SESSION 214** |
| VO.3-VO.6 (2 recipes + SPA + dogfood) | Queued (~2 sessions) |

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis :6381 + Postgres :5433

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
celery -A character_os worker --loglevel=info --pool=solo

# Beat for the hourly expired-asset sweep
cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
celery -A character_os beat --loglevel=info

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host localhost --port 8001 --reload

cd web && pnpm dev                          # :5174
```

**Session-start drift sweep:**

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

> **SESSION 213 finding (still applies):** doctor doesn't run
> pytest. Pair the doctor check with `pytest apps/<arc>` against
> any arc the previous session touched.

**Inventory regen** (after any backend model / route / Celery task change):

```bash
cd shell && python manage.py inventory
```

**Operator-facing expired-asset cleanup**:

```bash
cd shell && python manage.py sweep_expired_assets             # dry-run
cd shell && python manage.py sweep_expired_assets --commit    # apply
```

**HARD REQUIREMENTS:**

1. Django runserver (`.env` sourced)
2. SPA `pnpm dev` :5174
3. Redis (docker)
4. Celery worker (`.env` sourced)
5. Celery Beat (for hourly expired-asset sweep)
6. Media-engine for real-mode renders

**Smoke checks** (counts as of SESSION 214 close):

```bash
# Backend (from shell/)
set -a && source ../.env && set +a && EMBEDDING_FORCE_MOCK=1 pytest    # 1424 tests

# Media-engine (from media-engine/)
python -m pytest                              # 258 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 456 vitest tests
```

> **Env-issue caveat:** 3 tests in
> `apps/scripts/tests/test_api.py` fail without
> `EMBEDDING_FORCE_MOCK=1` set in the env (they exercise the
> embedding service path and require `OPENAI_API_KEY`). Set
> `EMBEDDING_FORCE_MOCK=1` for clean 1424/1424 results.

---

## AI / assistant context

- **Last session: SESSION 214 — Q-r-2 dogfood verified + embed-cache fix.**
  Two slices: real-mode Rigby dogfood proved the SESSION 213
  Q-r-2 fix dead (0× firings across 4 product-info questions,
  best-case outcome); parallel CC flagged + AI fixed the
  embedding-service mock/real cache collision. +1 regression
  test (1424 Django total).

- **Parallel-CC workflow continues.** A second CC is building
  out the u-d-b ↔ character-os docker bridge. Their work
  surfaced the embedding-cache bug during their ingest workflow.
  Coordination protocol: flag findings as fix-shaped candidates
  (file + bug + workaround + fix options); the recipient CC
  acts immediately.

- **Mock/real boundary as a recurring bug class** (codified
  SESSION 214). Any cache or storage crossing the mock/real
  boundary must namespace by mode OR opt mock out of
  persistence entirely. Second occurrence (first was R3's
  Runway `provider_session_key` shape divergence).

- **Top-K 30→50 was the load-bearing Q-r-2 fix**, not the
  dispatch dedup. When the avatar can't see tool results,
  bake knowledge into the document body, not into retrieval.
  Defense-in-depth dedup remains valuable but didn't fire in
  the dogfood.

- **"Real-mode finds bugs in every arc" streak: 12-for-12.**
  SESSION 214 added the embedding-cache finding (caught via
  parallel-CC operation, not solo dogfood). Pattern continues
  from SESSION 173.

- **Doctor catches narrative drift; pytest catches code
  drift.** Pair the two at session start when the previous
  session changed code in a cross-cutting way.

- **Data-location note (SESSION 214):** source markdown for
  Rigby's corpus lives in `unified-donkey-betz/docs/spokesperson/`;
  ingested chunks live in character-os Postgres :5433; the
  ingest script `scripts/ingest-udb-spokesperson-corpus.py`
  is currently untracked. The parallel CC's docker bridge is
  building an automated version of this same pipeline.

- Collaboration: AI drafts, human edits. Per-slice doc
  updates required at session end (codified SESSION 143).
  Handoff `## Calibration moments worth carrying` required
  at session end.
