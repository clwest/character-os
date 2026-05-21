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
> SESSION 213 post-arc Q-r-2 loop kill shipped (Fix 2A/2C/3B).
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
> **Last handoff:** `docs/handoffs/SESSION_213_QR2_LOOP_KILL.md`.

---

## SESSION 213 outcome — Q-r-2 loop kill (Fix 2A + 2C + 3B)

Three layered fixes in one slice + one drift-sweep companion.
**+9 tests, 0 real-mode spend.**

| Commit | Slice |
|---|---|
| (pending) | feat(realtime): dispatch dedup + recall_knowledge tightened + top-K 30→50 |

### What landed

- **Fix 2A — `apps/realtime/dispatch.py`** dedup window
  (`DEFAULT_DEDUP_WINDOW_SECONDS=10`,
  `REALTIME_TOOL_DEDUP_WINDOW_SECONDS` override). Identical
  `(session, tool_name, args)` refires return
  `already_returned: True` + `matched_invocation_id`. Terminal-
  failure states (FAILED / REJECTED) don't dedup; legitimate
  retries flow through. New `ToolSpec.dedup_enabled: bool`
  field lets mutating tools opt out — `attach_memory` sets
  False per Q-r-8 last-write-wins.
- **Fix 2C — `recall_knowledge` description tightened** to
  476 chars with explicit non-trigger: "Do NOT invoke when
  the operator's question is answerable from the loaded
  document. Invoke only when the operator asks for a
  specific fact the document is silent on."
- **Fix 3B — `DEFAULT_TOP_K` 30 → 50** in
  `character_os/realtime_document.py`. More chunks baked
  into the session document = fewer Q-r-2 strikes.
- **Drift-sweep companion** — bumped R6
  `test_composer_drops_memory_first_under_budget`
  `max_chars` 250 → 1300 to fit the SESSION 212
  Conversation Style block in the header.

### Test counts at SESSION 213 close

| Suite | Count |
|---|---|
| Django | **1423** (+9 vs SESSION 212) |
| Media-engine | **258** (unchanged) |
| SPA vitest | **456** (unchanged) |

Full session detail in
`docs/handoffs/SESSION_213_QR2_LOOP_KILL.md`.

---

## FIRST THING (SESSION 214): Real-mode dogfood — verify Q-r-2 loop is dead

Replay the SESSION 212 Rigby + DealFlowTracker scenario
against the fixes. **Targets:**

1. **`recall_knowledge` fires 0-1× per identical query**
   (vs. 4× in SESSION 212). 0 if boosted retrieval covers
   the answer; 1 + dedup hint if Rigby still chooses to
   look up.
2. **Audit-row count stays low** —
   `RealtimeToolInvocation.objects.filter(session=s,
   tool_name='recall_knowledge').count()` ≤ 1 for any
   identical-args query.
3. **No perceptible latency change** — dedup short-circuits
   are sub-ms; the user-visible flow stays identical.

**Setup**:
1. Bring the stack up (commands below).
2. Hit "Talk to Rigby" from `/spokespeople/<keeper-id>/talk`.
3. Two scripted prompts:
   * "Tell me about DealFlowTracker." — thin-knowledge product
     (1-chunk stub).
   * "How does Character OS work?" — well-grounded product
     (29-chunk corpus).
4. Capture the `RealtimeToolInvocation` rows for the session
   via `/api/realtime_tool_invocations/?session=<id>` after
   ending the call.
5. Operator-driven SPA flow; AI tails DB/logs in parallel
   per the human/AI testing split rule.

**Expected loop kill:**
* Pre-SESSION-213: 4× `recall_knowledge` rows for thin
  query, all SUCCEEDED with identical args.
* Post-SESSION-213: 1 row for thin query (or 0 if avatar
  speaks from document). Any second avatar fire returns
  the cached id + `already_returned: True`.

**If a new loop emerges on a different tool**
(`recall_recent_conversations` or `attach_memory`-via-spam),
the dedup applies by default — but `attach_memory` opts
out. Flag the finding as a SESSION 215 candidate; don't
silently flip the opt-out.

**Cost cap**: ≤ $1.00 spend. Two sessions, 5 min each
at $0.08/min = $0.80 max. Beat is now part of the local
runner — make sure it's up for the expired-asset sweep
visibility surface.

After SESSION 214 dogfood → **VO.3** (`cta_swap` starter
+ recipe registry + `voice_picker` field type) is the
next queued FIRST THING from the VO-arc.

---

## SESSION 212 outcome — VO.2 + realtime calibration

Two parallel arcs in one session.

**VO.2 shipped** (commit `c788966`) — overlay_audio
primitive + ffmpeg-only splice route + +39 tests
(Django 1387 → 1414; media-engine 246 → 258).
Byte-identity for `-c:v copy` validated via real-mode
ffmpeg.

**Realtime calibration shipped** (commit `2b861e6`)
— platform `## Conversation Style` block in every
realtime document, `render_video` /
`recall_recent_conversations` descriptions tightened,
operator handle resolution from workspace.owner.email,
Conversation Style section in test budget math.

**Real-mode dogfood with Rigby (8 sessions, ~$0.65
spend)** surfaced findings now closed by SESSION 213.

Full session detail in
`docs/handoffs/SESSION_212_VO2_PLUS_REALTIME_CALIBRATION.md`.

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
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED; **SESSION 213 Q-r-2 fix shipped** |
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
| **Realtime Q-r-2 loop kill (Fix 2A/2C/3B)** | **DONE SESSION 213** |
| VO.3-VO.6 (2 recipes + SPA + dogfood) | Queued (~2 sessions) |

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

> **SESSION 213 finding:** doctor doesn't run pytest. The R6
> `test_composer_drops_memory_first_under_budget` test was
> broken on `main` between SESSION 212 close and 213 open and
> doctor reported clean. Pair the doctor check with
> `pytest apps/<arc>` against any arc the previous session
> touched.

**Inventory regen** (after any backend model / route / Celery task change):

```bash
cd shell && python manage.py inventory
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

**Smoke checks** (counts as of SESSION 213 close):

```bash
# Backend (from shell/)
set -a && source ../.env && set +a && EMBEDDING_FORCE_MOCK=1 pytest    # 1423 tests

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
> `EMBEDDING_FORCE_MOCK=1` for clean 1423/1423 results.

---

## AI / assistant context

- **Last session: SESSION 213 — Q-r-2 loop kill.** Three
  layered fixes (dispatch dedup window + tighter
  `recall_knowledge` description + DEFAULT_TOP_K 30→50)
  plus one drift-sweep companion (R6 budget test
  `max_chars` 250 → 1300). +9 Django tests; media-engine
  + SPA unchanged. No real-mode spend. New `ToolSpec.dedup_enabled`
  field formalizes the read-only-vs-mutating tool
  distinction; `attach_memory` opts out per Q-r-8.

- **SESSION 212 — VO.2 + realtime calibration.** VO.2
  overlay_audio primitive + Rigby real-mode dogfood
  surfacing Q-r-2 / Conversation Style / tool-description
  / avatar-greeting findings. SESSION 213 closed the
  first one structurally.

- **SESSION 211 — VO arc opens (VO.0 + VO.1).** TTS
  provider chain + shell primitive + 48 tests.

- **"Real-mode finds bugs in every arc" streak: 11-for-11.**
  SESSION 212's Rigby dogfood surfaced 5 findings;
  SESSION 213 closed the first (Q-r-2 loop). Remaining 4
  findings tracked in `feedback_*` memory files.

- **Fix-shaped findings continue to compound.** The
  SESSION 212 handoff wrote Q-r-2 mitigation as three
  fix-shaped candidates with paths + acceptance + effort
  sizing. SESSION 213 executed them in ½ a session with
  no re-orientation. Pattern continues from SESSION 210.

- **Doctor catches narrative drift; pytest catches code
  drift.** SESSION 213 surfaced one budget test failure
  on `main` that doctor missed. Pair the two at session
  start when the previous session changed code in a
  cross-cutting way (e.g. the SESSION 212 Conversation
  Style block touched all R-arc compose paths).

- **`dedup_enabled` flag as architectural forcing
  function.** Adding a new realtime tool now requires
  the decorator answer "is this re-fire-friendly?". The
  flag makes the read-vs-mutate semantics explicit at
  registration, not at runtime.

- Collaboration: AI drafts, human edits. Per-slice doc
  updates required at session end (codified SESSION 143).
  Handoff `## Calibration moments worth carrying` required
  at session end.
