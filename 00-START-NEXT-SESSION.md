---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`
> (locked SESSION 178 — 10 contract rules, B0-B10 slice
> breakdown). **B0-B5 SHIPPED; B6-B10 deferred.**
> **Brand identity lock:** `docs/design/BRAND_IDENTITY_V2.md`
> (locked SESSION 178 — supersedes V1). Premium enterprise
> dark + gold; Geist + JetBrains Mono.
> **Parent-company anchor:** `docs/247_GLOBAL_AI_OVERVIEW.md`.
> **Prompt helpers:** `docs/design/PROMPT_HELPERS.md`.
> **Wizard scope lock:** `docs/design/CREATE_SPOKESPERSON_WIZARD.md`.
> **Knowledge layer scope lock:** `docs/design/KNOWLEDGE_LAYER.md`
> (locked SESSION 137 — 7 contract rules, K1-K10 slice breakdown).
> **Video composition scope lock:** `docs/design/VIDEO_COMPOSITION_V1.md`
> (locked SESSION 142 — **22 contract rules** total: V1's 9 + V17's
> 4 merged as rules 10-13 + Asset Library's 9 merged as rules 14-22;
> V0-V15 + V16 slice breakdown).
> **V16 POST-CLOSE SHIPPED (SESSION 179) — remove_avatar_background.**
> **V17 LOCKED (SESSION 182) — extend + keyframes.**
> V17.0 + V17.1 + V17.2 + V17.5 SHIPPED + REAL-MODE VALIDATED.
> **V17.3 DEFERRED (SESSION 184)** — see Q-v17-6 in
> `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`.
> **V18 SHIPPED + REAL-MODE VALIDATED (SESSION 184).**
> **V-arc UX polish COMPLETE (SESSION 200) — storyboard extend
> chain + crossfade closes the last known UX gap.**
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown). **R-ARC COMPLETE + REAL-MODE HARDENED
> (SESSION 176).**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Media generation scope lock:** `docs/design/MEDIA_GENERATION_V1.md`
> (locked SESSION 172 — 10 contract rules, W11.6.0-W11.6.5
> slice breakdown). **W11.6.0-W11.6.5 + W11.6.5 sub-slices 1/2/3 COMPLETE.**
> **Asset Library scope lock:** `docs/design/ASSET_LIBRARY_V1.md`
> (locked SESSION 185). **COMPLETE (SESSION 192) + REAL-MODE
> DOGFOOD VALIDATED (SESSION 193)** — all 9 slices A0-A8
> shipped across SESSIONS 185-192; end-to-end dogfood pass
> SESSION 193.
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`
> (revised SESSION 192 — Asset Library v1 marked complete).
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_200_STORYBOARD_EXTEND_CHAIN.md`.

---

## SESSION 200 outcome — storyboard extend-chain SHIPPED + REAL-MODE VALIDATED

The last known V-arc UX gap shipped + validated. `storyboard_ad`
+ `storyboard_voiced` expose two opt-in operator knobs that
close the hard-shot-transition complaint from SESSIONS 195+197.

* **`use_extend_for_shots`** — each shot becomes generate (5s)
  + extend (5s last-frame-conditioned). Doubles each shot from
  5s → 10s. ~3× cost.
* **`crossfade_ms`** — ffmpeg `xfade` + `acrossfade` between
  consecutive shots. 0 = hard cuts (default); 250–500ms blend.

Both default off; mirrors V17.5's `use_extend_for_backdrop`.

### Real-mode dogfood — 2 bugs found + fixed same session

Operator dogfooded `storyboard_ad(extend=True, crossfade=500,
outro_text="...")` immediately after the feature commit.
**Two bugs surfaced**:

1. **`intro_outro` silent-base** (fixed `8f6ff6c`). storyboard_ad
   has no narration, so the SESSION 200 silent extend+concat
   pipeline fed a silent body into intro_outro, which referenced
   `[0:a]` and ffmpeg exited rc=234. Latent since SESSION 198
   added outro_text to storyboard_ad with mock-only tests.
   **Same shape as SESSION 196 mix_audio silent-base**. Fix
   mirrors that one: ffprobe + synthesize silent audio when
   absent. 2 regression tests.

2. **Celery worker stale** (operational; recurring 3rd hit).
   Worker started 19:03; feature commit 21:38; fire 21:48.
   Worker ran the OLD primitive that didn't read `crossfade_ms`.
   Django auto-reloaded the starter (step.params written
   correctly), but the OLD Celery primitive silently dropped
   the param → demuxer fast path. **Silent semantic regression**:
   11/11 steps `succeeded`; only ffprobe revealed missing
   crossfade. After Celery restart, re-fire produced 29.27s
   @ 30fps (xfade verified).

### Final validation: composition `c592dd51`

- **status**: completed ✓
- 235s wall-time, **$1.62 spend**
- 11/11 steps green
- concat at 29.27s @ 30fps (xfade applied + framerate normalized)
- final at 32.27s @ 30fps (outro "24/7 Global AI" rendered cleanly)

All three SESSION 200 features validated end-to-end real-mode.
Total dogfood spend: **~$2.50** ($0.88 wasted on Celery-stale
first fire + $1.62 successful re-fire).

### Tests at SESSION 200 close

| Suite | Count |
|---|---|
| Django | 1039 |
| - compositions | 608 |
| Media-engine | 204 (+7 vs SESSION 199: +5 features +2 silent-base) |
| SPA vitest | 134 |

Real-mode dogfood spend SESSION 200: **~$2.50**.

### Calibration (3 new — 28 total)

1. **Celery worker doesn't auto-reload — third hit; promote
   to pre-fire checklist.** Silent stale-code shape (worker
   running, all steps succeed, output semantically wrong).
   New pre-fire check: compare last commit against
   `shell/apps/compositions/primitives/` mtime vs Celery
   worker start time. If commit is newer, restart Celery.

2. **Mock-mode hides upstream stream-shape drift — fourth
   hit.** Same V14/V15.4 mix_audio shape (assume base has
   audio, break on silent input). Forward defense: audit
   add_captions, composite_video, trim_clip, reformat_clip,
   style_remix for `[N:a]` references on downloaded clips.

3. **SESSION 200 dogfood — two bugs, one fix, one operational
   lesson.** Pattern is 4-for-4 across SESSIONS 195/197/200
   dogfoods. Post-feature real-mode dogfood is load-bearing
   for any feature touching ffmpeg endpoints.

---

## SESSION 199 outcome — outro_text parity FINISHED

Third quick-wins session in the outro_text parity rollout. Three
small slices ship outro_text to the remaining deliverable-shaped
V-arc recipes:

* **`cinematic_visual`** — single-step recipe; outro at position 1.
* **`cinematic_visual_extended`** — variable position based on
  extend chain length.
* **`dialogue_scene`** — multi/single-line variable position
  (mirrors long_form_ad).

**outro_text parity now complete** across 7 V-arc recipes
(talking_head_polished pre-existing + 6 added across SESSIONS
197-199). Remaining V-arc recipes are either post-processing
(recut_teaser, polish family) or intermediates where outro
doesn't fit semantically.

Backend tests **1020 → 1027 (+7)**. No real-mode spend.

The 3-session parity rollout cumulative:
- SESSION 197: 1 recipe (storyboard_voiced) + closure fire
- SESSION 198: 2 recipes (storyboard_ad, long_form_ad) + 1 taxonomy
- SESSION 199: 3 recipes (cinematic_visual, cinematic_visual_extended, dialogue_scene)

---

## SESSION 198 outcome — polish triple

Quick-wins session post the SESSION 197 V-arc 100% closure.
Three small slices shipped in one pass — same pattern as
SESSION 194 (V18 polish double) + SESSION 196 (V-arc fix
double).

* **Slice A — `outro_text` on `storyboard_ad`.**
* **Slice B — `outro_text` on `long_form_ad`.**
* **Slice C — `long_form_ad` concat `result_role=talking_head`.**

Backend tests **1014 → 1020 (+6)**. No real-mode spend.

---

## SESSION 197 outcome — V-arc 100% REAL-MODE CLOSED

**Milestone session.** First time the full V-arc is end-to-end
real-mode-validated against real Runway + Stability. Closed
via `storyboard_voiced` fire — the last unvalidated recipe.
**18/18 V-arc recipes now real-mode validated.**

Bundled with the closure: operator-noticed UX gap from
SESSION 195 dogfood (storyboard ended cold without branding)
shipped as a same-session polish — new optional `outro_text`
field on `storyboard_voiced`. The closure composition's final
carries "Dog Food Coffee House" as a 3-second outro card.

### The closure fire

Composition `1ce4d201`:
- **status: completed** ✓
- 245s wall-time, **$1.12 spend** (under the $1.92 forecast)
- 11 steps, 11/11 succeeded

### V-arc real-mode validation arc spend (SESSIONS 195→196→197)

| Session | Outcome | Spend |
|---|---|---|
| 195 | 2 bugs found; 1/2 recipes completed | $3.17 |
| 196 | Both fixes shipped; no fires | $0 |
| 197 | V-arc closed via storyboard_voiced + outro bundle | $1.12 |
| **Total** | **V-arc 18/18 + 2 production bugs + 1 UX feature** | **$4.29** |

---

## FIRST THING (SESSION 201): operator picks

**No arc in flight.** All four Phase 4 arcs + Asset Library v1
closed; V-arc 100% real-mode validated; outro_text parity rollout
complete (SESSIONS 197+198+199); **V-arc UX polish COMPLETE +
REAL-MODE VALIDATED (SESSION 200 — storyboard extend chain +
crossfade)**. Every known V-arc UX gap is closed AND validated
against real Runway.

**Pre-fire checklist enforcement (NEW SESSION 200):** Before any
real-mode composition fire, verify Celery worker is newer than
the last commit against `shell/apps/compositions/primitives/`:

```bash
CELERY_PID=$(pgrep -f "celery -A character_os" | head -1)
CELERY_START_EPOCH=$(ps -o lstart= -p $CELERY_PID | xargs -I{} date -j -f "%a %b %e %T %Y" "{}" "+%s")
LAST_PRIMITIVE_COMMIT_EPOCH=$(git log -1 --format=%at -- shell/apps/compositions/primitives/)
if [ "$LAST_PRIMITIVE_COMMIT_EPOCH" -gt "$CELERY_START_EPOCH" ]; then
  echo "STALE: restart Celery worker before firing"
fi
```

Same rule applies to `runner.py`, `tasks.py`,
`character_os/clients/media_engine.py`.

### Remaining polish / parity follow-ups

* **`outro_text` on `talking_head`** — scope decision deferred
  (talking_head_polished already has it; would duplicate the
  polished surface).
* **2 of 18 V-arc recipes unvalidated against real Runway** —
  storyboard_voiced was validated SESSION 197; the unfired
  pair are now recipes without a real-mode closure fire.
  Deferrable.

### Bigger backlog items

* **Asset upload UI** (1-2 sessions) — unblocks the 8 legacy
  RAW_UPLOAD rows + operator-uploaded content. Likely the
  most impactful "feature" remaining.
* **W12 legacy form retirement** (1 session).
* **K6.4 v3 architectural fix** (1 session).
* **K7.x v3 YouTube oEmbed** (½ session).

### Blocked / deferred (unchanged)

* F8.1 K10 seed corpus — blocked on operator markdown.
* B6-B10 brand arc — deferred SESSION 178.

### Optional real-mode validation

**`storyboard_ad` extend+crossfade+outro real-mode validated
SESSION 200.** The SESSIONS 198/199 outro flows on the OTHER
recipes (long_form_ad, cinematic_visual, cinematic_visual_extended,
dialogue_scene) still haven't been real-mode-fired with outros.
Operator could bundle one of those into the next composition
fire to validate the SESSIONS 198/199 outro parity surfaces
end-to-end. Estimated spend: $0.50–$1.50 depending on recipe.

### New-arc candidates from CONTENT_FORMAT_BACKLOG.md

* **B-1 Transcript Miner** — top strategic per memory.
* **B-3 Personalized Video** — biggest revenue unlock.
* **B-14 Multi-Platform Variants** — distribution stickiness.

### Recommended next direction

Five sessions of small-slice work in a row (194 polish double,
196 fix double, 198 polish triple, 199 outro parity, 200
extend chain + dogfood). Small-slice backlog is genuinely thin.

Natural next moves (operator picks):

1. **Open a new arc** — B-1 Transcript Miner is closest to
   shipped infra (R-arc transcripts already captured;
   A-arc Asset Library provides the surface).
2. **Asset upload UI** — operator-content bottleneck;
   unblocks new arcs that need operator-authored footage.
3. **Forward-defense audit** — apply the SESSION 200 calibration
   lesson by auditing add_captions, composite_video, trim_clip,
   reformat_clip, style_remix for unchecked `[N:a]` references.
   Roughly ½ session.

### Queued backlog (operator picks)

| Item | Effort | Notes |
|---|---|---|
| ~~Storyboard extend-chain~~ | **DONE SESSION 200** | V-arc UX gap closed. |
| **F8.1 — K10 seed corpus** | Operator-blocked | Markdown seed for new workspaces. Operator-authored content; AI can scaffold the loader. |
| **Real-mode validation: extend chain + outros** | 1 session | Bundle SESSIONS 198/199/200 new surfaces into one fire. ~$3.50 if full chain on. |
| **V17.3 keyframes (deferred SESSION 184)** | Blocked | Re-open criteria in `VIDEO_COMPOSITION_V17_PROPOSAL.md` §Q-v17-6. |
| **B6-B10 brand arc (deferred SESSION 178)** | Multi-session | Brand ecosystem v2; lower priority than feature work. |
| **K7.x v3 YouTube oEmbed** | ½ session | YouTube extractor v2 ships heuristic-based; v3 adds oEmbed for richer metadata. |
| **K6.4 v3 architectural fix** | 1 session | Verifier surface design lock — see K-arc scope doc. |
| **Asset upload UI (AUDIO / IMAGE)** | 1-2 sessions | The 8 needs-review legacy rows from SESSION 185 backfill stay at RAW_UPLOAD until this surface ships. |
| **W12 legacy form retirement** | 1 session | Old single-form recipe path still rides on the V6 shim. |
| **Thruman stale spokesperson cleanup** | ½ session | Dev DB tidy. |
| **CONTENT_FORMAT_BACKLOG.md picks** | Multi-session | 20 video formats/pipelines the V-arc's 18 recipes don't cover but primitives could ship. |

### New arc candidates (operator-pick)

1. **B-1 / Transcript Highlight Miner** — R-arc transcripts
   are captured but never mined. Likely 6-8 slices.
2. **B-3 / Personalized Video** — variable-substitution at
   render time. 10+ slices.
3. **B-14 / Multi-Platform Variants** — one composition
   render → reformatted variants for IG / TikTok / YT
   Shorts / LinkedIn. 5-6 slices.

See `docs/design/CONTENT_FORMAT_BACKLOG.md` for the full
catalog.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete.
**V-arc 18/18 real-mode validated + UX polish complete**
(SESSIONS 195→196→197 closure + 198→199 outro parity + 200
extend chain).
**Phase 5:** Brand ecosystem under 24/7 GLOBAL AI parent
(SESSION 178 B-arc).
**Asset Library v1 arc COMPLETE (SESSIONS 185-192) +
DOGFOOD VALIDATED (SESSION 193).**

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 | DONE + 18/18 RECIPES REAL-MODE VALIDATED |
| V17.0 + V17.1 + V17.2 + V17.5 | DONE + REAL-MODE VALIDATED |
| V18 (backdrop_clip on V8) | DONE + REAL-MODE VALIDATED |
| V17.3 (keyframes) + V17.4 | DEFERRED (SESSION 184) |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED |
| W11.6.0-W11.6.5 (media gen) | DONE |
| **outro_text parity (7 recipes)** | DONE (SESSIONS 197-199) |
| **storyboard extend chain + crossfade** | DONE (SESSION 200) |
| B0-B5 brand ecosystem pivot | DONE |
| Asset Library v1 (A0-A8) | DONE (SESSIONS 185-192) + DOGFOOD VALIDATED (SESSION 193) |
| B6-B10 brand arc | Deferred |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| W12 legacy form retirement | Queued |
| Asset upload UI (AUDIO / IMAGE) | Queued |
| Thruman stale spokesperson cleanup | Queued |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
  - Marcus the Battle Unicorn — id `b6a00dd8-...` — voice `david`

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host localhost --port 8001 --reload

cd shell && source .venv/bin/activate
python manage.py runserver                 # :8000

cd shell && source .venv/bin/activate
celery -A character_os worker --loglevel=info --pool=solo

cd web && pnpm dev                          # :5174 — V2 dark navy + gold
```

**Session-start drift sweep**:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

**HARD REQUIREMENTS** (promoted SESSION 193):

1. **Django dev server** — `python manage.py runserver` from `shell/`.
2. **SPA dev server** — `pnpm dev` from `web/`. :5174.
3. **Redis** — `cd infra && docker compose up -d` (port 6381).
4. **Celery worker** — **REQUIRED for any composition fire,
   including mock-mode.**
   ```bash
   cd shell && source .venv/bin/activate
   celery -A character_os worker --loglevel=info --pool=solo
   ```
   Without a worker, compositions hang silent at DRAFT
   (`error_message=""`, both steps `pending`) and queue
   envelopes stack in Redis. If a composition doesn't
   advance within 5 seconds in mock-mode, check
   `ps aux | grep celery` first.

**Optional** (depending on which next-item is picked):

* **Media-engine** — only for real-mode renders.
  `uvicorn app.main:app --host localhost --port 8001 --reload`
  from `media-engine/`. Mock-mode skips this entirely.

**Slice-open checklist (codified SESSION 182, hardened SESSION 184):**

For any new recipe or primitive that wraps a third-party API:

1. **Live-doc check** the API surface the slice depends on.
2. **String choice values** in recipe `select` fields per the SPA Zod schema.
3. **`LIVE_RECIPE_KINDS` opt-in** in `web/src/lib/api/recipes.ts` for new recipes.
4. **Default-aware form submission** verified.
5. **Unit fixtures shaped after a sample of provider output.**
6. **For starter changes consuming workspace Assets:** validate workspace, type, AND `duration_ms` non-null BEFORE Composition rows are created.

**A-arc primitive contract checklist (SESSION 186):**

For any new step primitive added after A2:

1. **Add a row to `PRIMITIVE_TO_ROLE`** in `apps/compositions/asset_roles.py`.
2. **Stamp `role=AssetRole.X.value`** on every `PrimitiveResult(...)` constructor call.
3. **Run `test_primitive_role_coverage.py`** — three layers of static + runtime assertions.
4. **Register the primitive** in `apps/compositions/primitives/__init__.py::_REGISTRY`.

**Smoke checks** (counts as of SESSION 200 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 1039 tests (compositions: 608)

# Media-engine (from media-engine/)
python -m pytest                              # 202 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 134 vitest tests
```

**New surfaces from SESSION 200:**

* `concat_clips` primitive + `/internal/clips/concat/` endpoint
  gained `crossfade_ms: int` (0–5000). When > 0 the endpoint
  uses an ffmpeg `xfade` + `acrossfade` filter_complex chain
  with per-clip ffprobe duration detection; when 0 the existing
  concat-demuxer fast path stays in place.
* `storyboard_ad` + `storyboard_voiced` starters gained two
  optional kwargs: `use_extend_for_shots: bool` (per-shot extend
  chain mirroring V17.5's pattern) and `crossfade_ms: int`
  (forwarded to the concat step). Step layouts shift up when
  the extend chain is on; outro position recomputed.
* Recipe metadata for both storyboard recipes exposes
  `use_extend_for_shots` (checkbox) + `crossfade_ms` (number,
  max_value 5000). Default param-map wiring (no custom
  `param_map` entries needed).

**Earlier surfaces — see SESSION 199 start-here in
`docs/handoffs/SESSION_199_OUTRO_PARITY_FINISHED.md` and prior
handoffs for the full backlog.**

---

## AI / assistant context

- **Last session: SESSION 200 — storyboard extend-chain SHIPPED
  + REAL-MODE VALIDATED + 2 production bugs caught.**
  Four feature slices + 1 post-close fix slice. Backend 1027
  → 1039 (+12). Media-engine 197 → 204 (+7: +5 features +2
  silent-base regression). 3 new TRUST_CALIBRATION entries
  (Celery stale, mock-mode stream-shape, dogfood pattern
  confirmation). $2.50 real-mode spend; 4-for-4 on "real-mode
  finds bugs in every recipe".

- **Prior session: SESSION 199 — outro_text parity finished.**
  Backend 1020 → 1027 (+7).

- **Calibration carried forward (28 total — +3 SESSION 200)**:
  V-arc 100% real-mode closure milestone;
  operator-noticed-during-dogfood → next-session ship loop;
  mix_audio silent-base; concat_clips role semantics
  recipe-dependent; real-mode dogfood finds bugs in EVERY
  recipe; Celery worker required for ALL composition fires;
  arc-close dogfood high-yield even after full test
  coverage; A-arc growth template; subagent
  source-of-truth; one-runner-emit pattern; live-doc-check
  2-for-2; V18 duration mismatch; asset taxonomy gap; smoke
  orphans; Celery silent stop-state; backdrop reuse shape
  mismatch; (+ earlier carry-forward).

- **V-arc UX polish exhausted (SESSION 200).** Every known
  V-arc UX gap closed AND real-mode validated. Next polish
  would be operator-driven from real-mode dogfood findings,
  not from queued backlog.

- **NEW pre-fire hard check (SESSION 200):** Compare last
  commit against `shell/apps/compositions/primitives/` mtime
  vs Celery worker start time. If commit is newer, restart
  Celery before firing. Silent stale-code regression is the
  failure mode — operator paid $0.88 to catch it this time.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **A-arc COMPLETE (SESSIONS 185-192) + DOGFOOD VALIDATED
  (SESSION 193).** Asset Library v1 shipped all 9 slices
  A0-A8.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
