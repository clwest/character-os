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
> **Last handoff:** `docs/handoffs/SESSION_210_CALIBRATION_CLOSEOUT.md`.

---

## SESSION 210 outcome — all 4 SESSION 209 calibration findings closed

Stacked-½-slice session. The SESSION 209 handoff left four
operational findings as fix-shaped candidates; SESSION 210
closed all four plus the operator-facing companion to the
last one.

**6 commits, 0 real-mode spend, 0 subagent runs, +29 tests.**

### What landed

| Commit | Slice |
|---|---|
| `e2af47f` | aggregate `knowledge_chunk_ids` at completion |
| `e48d07f` | media-engine intro/outro card auto-wrap |
| `d0adf76` | recipe form "Topic" relabel + tighter helper |
| `7e20e31` | storage-health badge on Videos library |
| `562e16d` | hourly expired-asset Beat sweep |
| `000dd94` | operator-facing `sweep_expired_assets` command |

Full session detail in
`docs/handoffs/SESSION_210_CALIBRATION_CLOSEOUT.md`.

### Notable structural changes

- **First entry in `CELERY_BEAT_SCHEDULE`.** Beat is now part
  of the local-dev surface — `celery -A character_os beat
  --loglevel=info` runs as a third Celery process alongside
  the worker.
- **`run_expired_asset_sweep(commit=bool)` core** shared by
  the Beat task and the management command. Behavior parity
  is structural, not procedural.
- **Pattern reinforced**: visibility surface (badge) +
  recurring fix (Beat) + manual override (command) is the
  right shape for any background reconciliation feature.

### Workspace state (unchanged from SESSION 209)

- **1 spokesperson:** 24/7 Global AI (`d3d0fb14-…`).
- **37 KnowledgeDocuments / 884 chunks** (Tier 1 + Tier 2).
- **6 compositions** from SESSION 209 dogfood.
- 0 expired final_assets (operator did the manual cleanup
  earlier in SESSION 209; subsequent sweeps will catch new
  expirations as they happen).

### Test counts at SESSION 210 close

| Suite | Count |
|---|---|
| Django | **1364** (+21) |
| Media-engine | **221** (+7) |
| SPA vitest | **456** (+1) |

---

## FIRST THING (SESSION 211): operator pick

The SESSION 209 findings queue is empty. Three flavors of
work queue up; AI recommends Candidate A unless the
operator has a strong signal to do otherwise.

### Candidate A — VO-arc scope lock (½ session) — RECOMMENDED

Post-hoc voiceover insertion at specific time offsets.
Unblocks ad recipes that need a different speaker for the
CTA line ("And now back to you, Jessica…"). Doc-only,
no code. Follows the V-arc / R-arc / B-arc scope-lock cadence
— design before code. Recommended next because:

* It's the biggest queued doc-only piece — perfect for a
  thinking-heavy session.
* Future composition recipes block on it (e.g. a `cta_swap`
  recipe needs the VO primitive).
* The session that follows it would be a tight ½-slice
  (VO.0 + VO.1 primitive) that fits the current cadence.

### Candidate B — Asset upload UI (1-2 sessions)

The biggest unblocker on the queue. Operators currently
can't upload their own clips/audio/images; everything has
to be generated. Once upload lands, several v2 recipes
become viable (operator-supplied b-roll, voice samples for
cloning, reference portraits).

### Candidate C — Light mode (1 session)

Q-v3-2 from the V3 arc. Pure token / `data-brand` swap;
small risk because V3 architected this in. Useful if the
operator has been working in dark for the SESSION 210
stacked-slice marathon and wants a break.

### Parallel work (operator-driven, ongoing)

- **Keeper rename** — placeholder "24/7 Global AI" still
  active; operator considering alternatives.
- **Keeper profile** — set `personality`,
  `tone_archetype`, bio fields from the SPA at
  `/spokespeople/d3d0fb14-193e-4c4c-88d1-acae9af25bb5`.

---

## Slice queue (after FIRST THING)

### Queued from SESSION 210 closeout

| | Slice | Effort |
|---|---|---|
| 1 | VO-arc scope lock | ½ session (doc) |
| 2 | VO.0 / VO.1 first primitives | ½ session |
| 3 | Asset upload UI | 1-2 sessions |
| 4 | Light mode (Q-v3-2) | 1 session |

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
| `knowledge_chunk_ids` propagation patch | **DONE SESSION 210** |
| Brief-replaces-script SPA copy pass | **DONE SESSION 210** |
| Outro/intro card auto-wrap | **DONE SESSION 210** |
| Storage-health badge on Videos library | **DONE SESSION 210** |
| Expired-asset hourly Beat sweep + manual command | **DONE SESSION 210** |
| VO-arc | Queued (½ session scope lock) |

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis :6381 + Postgres :5433

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
celery -A character_os worker --loglevel=info --pool=solo

# NEW SESSION 210: Beat for the hourly expired-asset sweep
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

**Inventory regen** (after any backend model / route / Celery task change):

```bash
cd shell && python manage.py inventory --write
```

**Operator-facing expired-asset cleanup** (new SESSION 210):

```bash
cd shell && python manage.py sweep_expired_assets             # dry-run
cd shell && python manage.py sweep_expired_assets --commit    # apply
```

**HARD REQUIREMENTS:**

1. Django runserver (`.env` sourced)
2. SPA `pnpm dev` :5174
3. Redis (docker)
4. Celery worker (`.env` sourced)
5. Celery Beat (NEW — for hourly expired-asset sweep)
6. Media-engine for real-mode renders

**Smoke checks** (counts as of SESSION 210 close):

```bash
# Backend (from shell/)
set -a && source ../.env && set +a && EMBEDDING_FORCE_MOCK=1 pytest    # 1364 tests

# Media-engine (from media-engine/)
python -m pytest                              # 221 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 456 vitest tests
```

> **Env-issue caveat:** 3 tests in
> `apps/scripts/tests/test_api.py` fail without
> `EMBEDDING_FORCE_MOCK=1` set in the env (they exercise the
> embedding service path and require `OPENAI_API_KEY`). Set
> `EMBEDDING_FORCE_MOCK=1` for clean 1364/1364 results.
> Pre-existing env-shape issue, not from SESSION 210.

---

## AI / assistant context

- **Last session: SESSION 210 — calibration closeout.** Six
  ½-slices closing all 4 SESSION 209 calibration findings
  plus the operator-facing companion to the last one. The
  pattern: a well-scoped handoff lets the next session
  stack ½-slices without re-orienting between them.

- **Calibration carried forward (41 + 4 closed SESSION
  210):** all four SESSION 209 findings closed
  structurally. No new findings emerged this session (no
  real-mode renders fired; pure code/test slices).

- **"Real-mode finds bugs in every arc" streak: 10-for-10.**
  SESSION 209's V3 dogfood surfaced 4 findings; SESSION 210
  closed all 4. The streak generalizes: the *next* session
  after a calibration-rich session can be a stacked-½-slice
  closeout if the findings were written as fix-shaped
  candidates rather than as bug reports.

- **First Celery Beat schedule entry in the project.** Beat
  is now part of the local-dev surface. Future periodic
  tasks (asset purge, retention sweeps, scheduled reports)
  ride this precedent.

- **The visibility / Beat / command triad is canonical for
  background reconciliation.** SESSION 210's expired-asset
  story shows the pattern: badge surfaces the state, Beat
  fixes it on a clock, command lets the operator fix it
  now. Apply when a future feature needs both automated
  and manual cleanup paths.

- **Management command dry-run-by-default discipline.**
  `backfill_asset_roles` (SESSION 185) and now
  `sweep_expired_assets` (SESSION 210) both default to
  dry-run + require `--commit`. Canonical pattern for any
  destructive / mass-update command.

- **A single-render finding usually has broader scope.**
  The chunk_ids fix was scoped to `talking_head` in the
  SESSION 209 handoff; inspection broadened it to every
  `use_knowledge=True` recipe. Audit every code path that
  writes to the same target before fixing.

- **Doc-discipline pays off mid-session.** Per-slice handoff
  updates in the start-here doc kept SESSION 210 from
  spiraling — every "keep going" had a clearly-defined
  next item. The handoff was the work plan.

- **Subagent delivery on tight contract briefs is 3-for-3**
  (B2.5 + BC4 + V3.5). Pattern that works: exhaustive
  contract upfront, file list, per-file checklist,
  verification steps. SESSION 210 ran inline — no subagent
  dispatched — because the slices were small enough to not
  benefit from delegation.

- Collaboration: AI drafts, human edits. Per-slice doc
  updates required at session end (codified SESSION 143).
  Handoff `## Calibration moments worth carrying` required
  at session end.
