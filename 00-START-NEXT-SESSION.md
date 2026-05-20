---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`.
> **B0-B5 SHIPPED; B6-B10 deferred.**
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V2.md`.
> **Parent-company anchor:** `docs/247_GLOBAL_AI_OVERVIEW.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer:** `docs/design/KNOWLEDGE_LAYER.md`.
> **Video composition:** `docs/design/VIDEO_COMPOSITION_V1.md`.
> V0-V18 COMPLETE + 18/18 RECIPES REAL-MODE VALIDATED.
> **V-arc UX polish COMPLETE (SESSION 200).**
> **Forward-defense audit COMPLETE (SESSION 201).**
> **Realtime avatar:** `docs/design/REALTIME_AVATAR_V1.md`.
> R0-R10 + R6.1 COMPLETE + REAL-MODE HARDENED.
> **Workspace fabric:** `docs/design/WORKSPACE_FABRIC_V1.md`.
> F0-F10 COMPLETE; F8.1 queued.
> **Media generation:** `docs/design/MEDIA_GENERATION_V1.md`.
> W11.6.0-W11.6.5 + sub-slices 1/2/3 COMPLETE.
> **Asset Library:** `docs/design/ASSET_LIBRARY_V1.md`.
> A0-A8 COMPLETE (SESSION 192) + DOGFOOD VALIDATED (SESSION 193).
> **Transcript Miner (B-1):** `docs/design/TRANSCRIPT_MINER_V1.md`.
> B1.0-B1.7 COMPLETE + REAL-MODE VALIDATED (SESSION 202).
> **Personalized Video (B-3):** `docs/design/PERSONALIZED_VIDEO_V1.md`.
> **B3.0-B3.9 COMPLETE + REAL-MODE VALIDATED (SESSION 203).**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Publish Bundle (B-14):** `docs/design/PUBLISH_BUNDLE_V1.md`.
> **B14.0-B14.5 COMPLETE + REAL-MODE VALIDATED (SESSION 205).**
> **Auto-Scripting (B-2):** `docs/design/AUTO_SCRIPTING_V1.md`.
> **B2.0-B2.6 COMPLETE + REAL-MODE VALIDATED (SESSION 207).**
> **Last handoff:** `docs/handoffs/SESSION_207_E_ARC_DOGFOOD.md`.

---

## SESSION 207 outcome — E-arc closes

B2.6 dogfood ran end-to-end against Marcus + the "Five
Good Emperors / Antonine peace" topic. Real Runway
render: $0.25 actual = exact prediction. 54.2s mp4.
**Lineage validated end-to-end** (Script.draft_text ≡
Composition.synthesized_brief byte-identical; chunk_ids
5/5 match; rule-7 `trusted_passthrough` honored).

**Real-mode-finds-bugs streak now 7-for-7.** Seven
findings in one fire:

* **1 in-session patch** — Script-detail verifier panel
  was gated on `verification_status ∈ {warned, blocked}`
  and hid K6's informational warnings on `verified`.
  Patch relaxes gate to `warnings.length > 0` + adds
  neutral `info` tone. ~15 LOC in
  `web/src/routes/workspace/scripts.$id.tsx`.
* **6 v2 findings filed** — see
  `docs/handoffs/SESSION_207_E_ARC_DOGFOOD.md`.
* **1 calibration entry** — Marcus rig portrait
  quality (third quality axis alongside SESSION 158's
  voice × lip-sync axis).
* **1 verifier win** — K6.4 correctly flagged a
  weakly-grounded "Machiavelli" reference.

Tests unchanged: Django 1320 / SPA 405 / media-engine
214. Real-mode spend SESSION 207: **$0.25**.

---

## FIRST THING (SESSION 208): operator picks

The E-arc is done. The strategic-axis quartet
(B-1 / B-2 / B-3 / B-14) is shipped + real-mode
validated end-to-end. **No "FIRST THING" lock — this
is an operator-pick session.** Candidate priorities,
ranked by leverage:

### 1. B-2 ↔ B-3 composition (1-2 sessions) — highest leverage

Wire Scripts into PersonalizedCampaign as the
template source. The E-arc's `Script.draft_text` +
the C-arc's per-recipient personalization compose
into "draft once, personalize per recipient."
"Composition is the moat" framing applies — the
combinatorial product of strategic axes is the
defensible feature.

### 2. B-2 v2 polish slice (~½ session) — closes SESSION 207 findings

Three things in one slice:
* Fix Composition-detail verifier panel inconsistency
  (~10 LOC in `web/src/routes/compositions/$id.tsx`).
* Add Script-detail vitest for the in-session patch
  (~30 LOC; build from `transcripts.test.tsx`
  pattern).
* Optionally: `Asset.spokesperson` back-link in
  `auto_script` starter (~3 LOC + 1 test).

### 3. Asset upload UI (1-2 sessions)

Operator-content bottleneck blocks B-1 v2 + the
"production-ready Marcus" workflow. Surfaces a way
for operators to upload their own
images/videos/audio as Asset rows. Could pair with
the Marcus rig re-bake as one workflow.

### 4. B-14 v2 `offset_x` knob (½ session)

SESSION 205 dogfood finding while still relatively
fresh. Cosmetic UX for the publish bundle layout.

### 5. B-1 v2 slices (multiple sessions)

External transcript ingestion, batch mining, highlight
chaining. Builds on SESSION 202's miner foundation.

### 6. `auto_script_polished` + `auto_script_cinematic` variants (~½ session each)

Deferred from B2.4 per scope-lock "if scope permits."
Drop-in recipe variants over `auto_script`.

### 7. Marcus rig re-bake (cosmetic, ~½ session)

Operator noted as "bad image" — re-portrait + re-bake
through the Runway flow. Lower leverage but unblocks
quality demos featuring Marcus.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete.
**V-arc 18/18 real-mode validated + UX polish complete**.
**Asset Library v1 COMPLETE + DOGFOOD VALIDATED**.
**Transcript Miner (B-1) v1 COMPLETE + REAL-MODE VALIDATED**.
**Personalized Video (B-3) v1 COMPLETE + REAL-MODE VALIDATED.**
**Publish Bundle (B-14) v1 COMPLETE + REAL-MODE VALIDATED.**
**Auto-Scripting (B-2) v1 COMPLETE + REAL-MODE VALIDATED.**
**Phase 5:** Brand ecosystem under 24/7 GLOBAL AI parent.

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 + V17 + V18 | DONE + REAL-MODE VALIDATED |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED |
| W11.6.0-W11.6.5 | DONE |
| Asset Library v1 (A0-A8) | DONE + DOGFOOD VALIDATED |
| Transcript Miner v1 (B1.0-B1.7) | DONE + REAL-MODE VALIDATED |
| Personalized Video v1 (B3.0-B3.9) | DONE + REAL-MODE VALIDATED |
| Publish Bundle v1 (B14.0-B14.5) | DONE + REAL-MODE VALIDATED |
| **Auto-Scripting v1 (B2.0-B2.6)** | **DONE + REAL-MODE VALIDATED** |
| B6-B10 brand arc | Deferred |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI | Queued |
| B-14 v2 offset_x knob | Queued (½ session; SESSION 205 dogfood finding) |
| B-2 v2 polish slice | Queued (~½ session; SESSION 207 findings) |
| B-2 v2 auto_script_polished + auto_script_cinematic | Queued (each ~½ session) |
| B-2 ↔ B-3 composition | Queued (1-2 sessions; highest leverage) |
| Marcus rig re-bake | Queued (cosmetic; SESSION 207 finding) |

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate && set -a && source ../.env && set +a
celery -A character_os worker --loglevel=info --pool=solo

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host localhost --port 8001 --reload

cd web && pnpm dev                          # :5174
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**HARD REQUIREMENTS** (promoted SESSIONS 193 + 200):

1. **Django dev server** — `python manage.py runserver` from
   `shell/` **with .env sourced**.
2. **SPA dev server** — `pnpm dev` from `web/`. :5174 (binds
   IPv6 localhost; `127.0.0.1:5174` may fail — use
   `localhost:5174`).
3. **Redis** — `cd infra && docker compose up -d`.
4. **Celery worker** — required for any composition fire
   **with .env sourced**.
5. **Media-engine** — required for real-mode renders.

**Pre-fire check (codified SESSION 200, extended SESSION 202+203+206)**:
restart Celery before any real-mode fire when the last commit
against ANY of these is newer than worker start:
* `shell/apps/compositions/primitives/`
* `shell/apps/compositions/starters.py`
* `shell/apps/compositions/recipes.py` (registry; SESSION 206 added)
* `shell/apps/*/signals.py` (includes
  `apps/transcripts/signals.py`,
  `apps/campaigns/signals.py`,
  `apps/scripts/signals.py`)
* `shell/character_os/clients/media_engine.py`

Signals + registry imports register only at
`apps.py::ready()`; a stale worker silently doesn't fire
them.

**Smoke checks** (counts as of SESSION 207 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 1320 tests

# Media-engine (from media-engine/)
python -m pytest                              # 214 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 405 vitest tests
```

---

## AI / assistant context

- **Last session: SESSION 207 — E-arc B2.6 dogfood + arc
  close.** Two commits: one in-session SPA bug-fix patch
  (`scripts.$id.tsx` verifier panel gate relaxed for
  informational warnings); one docs/handoff bundle.
  Real-mode spend: $0.25 ($0.25 talking-head against
  Marcus + the "Five Good Emperors" topic). Lineage
  validated end-to-end. 7 findings (1 patched, 6 v2,
  1 calibration, 1 win).

- **Prior session: SESSION 206 — E-arc lock + 5 of 7
  slices shipped.** Six commits B2.0-B2.5. Django 1269
  → 1320 (+51). SPA 371 → 405 (+34). 2 new
  TRUST_CALIBRATION entries (39 total). $0 real-mode
  spend.

- **Prior session: SESSION 205 — D-arc shipped in one
  session.** Seven slices B14.0-B14.5 including
  dogfood. Django 1245 → 1269 (+24). SPA 284 → 371
  (+87).

- **Scope-lock cadence is 5-for-5** (A/B/C/D/E arcs).
  Pattern: 8-10 contract rules + 7-10 slices + per-
  slice tests + real-mode dogfood closing. Each arc
  lands in one extended session; dogfood can ride into
  the next session when same-day fatigue would degrade
  validation quality (SESSION 206 made this call;
  SESSION 207 confirmed the ride-over delivered).

- **Calibration carried forward (41 total — +2 SESSION
  207: real-mode-finds-bugs 7-for-7 + Marcus rig
  portrait quality)**: V-arc 100% real-mode closure;
  operator-noticed-during-dogfood loop; mix_audio +
  intro_outro silent-base shapes; real-mode finds bugs
  in EVERY arc (7-for-7 now); Celery worker doesn't
  auto-reload (3rd hit); mock-mode hides stream-shape
  drift (4th hit); forward-defense audits surface
  latent bugs cheaply; gpt-5 reasoning eats output
  budget; scope-lock pattern compresses build phase
  (5-for-5); React Query mutation onSuccess must
  invalidate every dependent query; tier-gated batch
  caps work as designed via forecast preview surface;
  aspect-changing crop is a recurring shape; K6 refactor
  via adapter pattern preserved zero regressions; scope-
  lock cadence 5-for-5; **real-mode-finds-bugs streak
  7-for-7 (NEW SESSION 207)**; **avatar rig quality
  has three axes — portrait, voice × lip-sync, script-
  persona fit (NEW SESSION 207)**.

- **The "real-mode finds bugs in every recipe / arc"
  pattern is now 7-for-7.** Every dogfood across
  SESSIONS 195/197/200/202/203/205/207 surfaced at
  least one finding. Treat "clean" runs as a
  calibration prior of "something was missed."

- **Cross-surface UI consistency is a recurring gap**
  (SESSION 207 finding). Script-detail and
  Composition-detail render the same
  `verification_warnings` JSON differently. Future
  work that adds a "verifier panel" to a new surface
  should template against a shared component.

- **Brand layer is load-bearing.** Every component
  must import company/product strings from
  `@/lib/brand` per BRAND_ECOSYSTEM_V1 contract
  rule 3.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
