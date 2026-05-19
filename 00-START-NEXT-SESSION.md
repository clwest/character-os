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
> (locked SESSION 142 — 9 contract rules, V0-V15 slice breakdown).
> **V16 POST-CLOSE SHIPPED (SESSION 179) — remove_avatar_background.**
> **V17 LOCKED (SESSION 182) — extend + keyframes.**
> 13 contract rules total (V1's 9 + V17's 4 merged as rules
> 10-13). V17.0 IN FLIGHT this session.
> See `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`.
> **Realtime avatar scope lock:** `docs/design/REALTIME_AVATAR_V1.md`
> (locked SESSION 142 — 10 contract rules, R0-R10 slice
> breakdown). **R-ARC COMPLETE + REAL-MODE HARDENED
> (SESSION 176).**
> **Workspace fabric scope lock:** `docs/design/WORKSPACE_FABRIC_V1.md`
> (locked SESSION 144 — 9 contract rules, F0-F10 slice
> breakdown). **F0-F10 complete; F8.1 queued.**
> **Media generation scope lock:** `docs/design/MEDIA_GENERATION_V1.md`
> (locked SESSION 172 — 10 contract rules, W11.6.0-W11.6.5
> slice breakdown). **W11.6.0-W11.6.5 + W11.6.5.1-3 COMPLETE.**
> **Narrative anchor:** `docs/CHARACTER_OS_WHAT_IT_IS.md`.
> **Runtime anchor:** `docs/CHARACTER_OS_INVENTORY.md` —
> regen via `python manage.py inventory` (from `shell/`).
> **Last handoff:** `docs/handoffs/SESSION_181_V_ARC_LAYOUT_VOICE_STORYBOARD_DOGFOOD.md`.

---

## SESSION 181 outcome — V-arc layout / voice / storyboard dogfood + V17 proposal

Eight commits. Biggest single-session validation run of the
V-arc — **11 recipes** dogfooded end-to-end, bringing V-arc
validation from 5 to **16 of 18**. Five production bugs
surfaced and fixed inline; one architectural gap surfaced as
the V17 proposal.

* **Recipes validated:** `reels_format`, `pip_layout`,
  `cohost_layout`, `broll_splice`, `music_bed_pass`,
  `voice_design`, `recut_teaser`, `backdrop_layout`,
  `style_remix_pass`, `multi_lang_dub`, `storyboard_ad`. All
  4 composite layout kinds (pip / cohost / backdrop / broll)
  now green.

* **`adfa22a`** — V7 broll layout probes base dims + setsar
  on all concat segments (same shape as SESSION 180
  intro_outro canvas-default bug).
* **`583e3a3`** — V11 style_remix client passes 900s timeout
  for Aleph (same pattern as V16 remove_avatar_background
  timeout override).
* **`9e569de`** — V11 Aleph chunked-path merges sub-1s tail
  residual (10.04s source split into 5+5+0.04s; Aleph
  rejected the tail).
* **`6e62dba`** — V13 gen4_image seed PNG bumped 1×1 → 8×8
  (Runway tightened referenceImages validation in the
  interim).
* **`5cc0954`** — V13 prompt_image rewrite extended to
  `/data/_internal/images/` paths (storyboard image-to-video
  was sending local URLs straight to Runway).

* **`docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`** —
  drafted. Operator-surfaced gap: Runway's `extend` video
  + `keyframes` features never integrated. Cures V8
  multi-backdrop seam workaround, V13 character drift, V4
  10s ceiling. 6 slices, ~4 sessions of work. `status:
  proposed`, awaiting scope-lock review.

Tests: Django **428** compositions (unchanged). Media-engine
**177** (162 → 177, +15 across 5 fix slices). SPA vitest
**95** unchanged.

Real-mode spend this session: **~$3.50**.

### Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended:

1. **Operator "are we using X?" framing surfaces capability
   gaps the dogfood loop wouldn't.** All 11 SESSION 181
   recipes ran end-to-end with operator-acceptable output;
   the character-drift gap in storyboard_ad only got named
   when the operator asked about extend + keyframes from
   prior-session recall. Dogfood catches bugs; operator
   framing catches missing capabilities.

2. **Asset upload UI is a recurring gap.** music_bed_pass
   needed AUDIO; multi_lang_dub needed AUDIO — neither had
   an SPA upload path. Shell-side asset-row creation was
   the pragmatic dogfood workaround twice this session.
   Scope target: generic asset upload flow as a workspace
   fabric extension.

3. **External API validation tightens over time — re-dogfood
   periodically.** V13's gen4_image seed PNG was 1×1 when
   shipped SESSION 143; Runway tightened to 2×2+ minimum in
   the interim. Pattern: APIs that "worked when shipped"
   need re-validation against current upstream contracts
   during dogfood passes, not just when code touches the
   path.

### Final state at session close

* **16 V-arc recipes real-mode validated** (talking_head +
  long_form_ad + cinematic_visual + talking_head_with_backdrop
  + talking_head_polished + reels_format + pip_layout +
  cohost_layout + broll_splice + music_bed_pass + voice_design
  + recut_teaser + backdrop_layout + style_remix_pass +
  multi_lang_dub + storyboard_ad).
* **2 recipes remain unvalidated:** `storyboard_voiced` (10-step,
  heaviest) + `dialogue_scene` (multi-spokesperson). Both
  deferred to SESSION 182+ — operator called the session on
  "no sense doing storyboard_voiced before V17 extend
  lands."
* **V17 proposed, not locked.** Design doc ready for review.

### FIRST THING (SESSION 182): V17 review + V17.0 implementation

Operator-locked direction at SESSION 181 close: V17 is the
priority over the last 2 V-arc validations.

1. **Read** `docs/design/VIDEO_COMPOSITION_V17_PROPOSAL.md`.
   Confirm scope (extend + keyframes), 6-slice breakdown
   (V17.0-V17.5), 5 contract rules layered on V1's
   existing 9, out-of-scope list, and 5 open questions
   (Q-v17-1 through Q-v17-5).

2. **Operator edit + scope-lock.** Same pattern as V0/V1
   went through SESSION 142 — proposal becomes binding
   contract after operator review.

3. **Ship V17.0** — media-engine `/internal/clips/extend/`
   endpoint + tests. ~½ session. No Django changes;
   contract is clean.

4. **Ship V17.1** in the same session if time —
   `extend_visual_clip` Django primitive + cost estimator
   + tests. ~½ session.

V17.2-V17.5 spread across SESSIONS 183-184:
* V17.2 — `cinematic_visual_extended` recipe (V4 + extend
  chain)
* V17.3 — multi-keyframe support on `generate_visual_clip`
  + `keyframe_shot` recipe
* V17.4 — V13 `storyboard_ad` opt-in `use_keyframes` flag
* V17.5 — V8 `talking_head_with_backdrop` opt-in
  `use_extend_for_backdrop` flag

After V17 lands: revisit `storyboard_voiced` + `dialogue_scene`
to close out the V-arc validation at 18/18.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete.
**Phase 4:** All four arcs (K / V / F / R) complete +
R-arc real-mode validated (SESSION 176); V-arc real-mode
validation **near-complete** (16 of 18 recipes, SESSIONS
158 + 179 + 180 + 181). V16 post-close shipped (SESSION
179); V17 proposed (SESSION 181), **scope-locked SESSION
182** with rules 10-13 merged into V1.
**Phase 5:** Brand ecosystem under 24/7 GLOBAL AI parent
(SESSION 178 B-arc).

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 | DONE (mock); **16/18 real-mode validated** |
| **V17 (extend + keyframes)** | **LOCKED (SESSION 182); V17.0 in flight** |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED (SESSION 176) |
| W11.6.0-W11.6.5 (media gen) | DONE (SESSIONS 172-173) |
| W11.x voice telemetry + W11.y personality split | DONE |
| K7.1 cost telemetry | DONE (SESSION 174) |
| K7.x v2 YouTube extractor | DONE (SESSION 175); real-mode unverified |
| Multi-step composition title disambig | DONE (SESSION 177) |
| Sasha + Donny voice re-persist | DONE (SESSION 177, data-only) |
| B0-B5 brand ecosystem pivot | DONE (SESSION 178) |
| V16 remove_avatar_background | DONE (SESSION 179) |
| V9 polish form shorthands + intro_outro fixes | DONE (SESSION 180) |
| **V7/V11/V13 dogfood fixes + 11 recipes validated** | **DONE (SESSION 181)** |
| B6-B10 brand arc | Deferred (product #2 reality) |
| F8.1 (K10 seed corpus) | Queued |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| Thruman stale spokesperson cleanup | Queued |
| W12 legacy form retirement | Queued |
| **Asset upload UI (AUDIO / IMAGE)** | **NEW QUEUED (SESSION 181) — operator-facing gap** |
| 2 of 18 V-arc recipes unvalidated | storyboard_voiced + dialogue_scene; deferred until V17 lands |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
    (SESSION 179-181 hero — most-validated avatar)
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
    (stale "Thruman" record at same prefix queued for cleanup)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice
    `david` (most-dogfooded — 4 ENDED realtime sessions + 1
    rendered MP4 SESSION 176)

**SESSION 181 workspace artifacts:**

  - 11 new `Composition` rows (one per dogfooded recipe;
    several with multiple retries during inline fixes)
  - 1 new VOICE asset: Riggs Founder New Voice (voice_id
    `1bc3b784-6985-4d00-9e6b-e1f7fcecb2d5`)
  - 2 placeholder AUDIO assets in
    `/data/_internal/uploads/` (synth pad music bed +
    Riggs voice extract for dub)
  - 1 dubbed AUDIO asset (Spanish translation of Riggs's
    3-rules script)
  - 1 anime-styled CLIP (Aleph remix of underwater backdrop)
  - 1 15s storyboard CLIP (Hook/Action/Payoff founder
    narrative)

---

## How to bring the stack up locally

```bash
cd infra && docker compose up -d           # Redis on :6381, Postgres on :5433

cd media-engine && source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload

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

**SESSION 182 stack-up notes:**

* Celery worker was restarted SESSION 181 (pid 24687) to
  pick up the V11 style_remix client timeout change. No
  new primitives this session. Restart only if you touch
  `apps/compositions/primitives/` OR `apps/*/tasks.py` OR
  `apps/*/signals.py`.
* Uvicorn `--reload` window can serve requests with stale
  module code mid-swap — when iterating on
  `media-engine/app/` files with rapid edits + immediate
  re-fires, wait for the "Application startup complete"
  log line between iterations (per SESSION 180
  TRUST_CALIBRATION entry).
* First-call deps cached: ~176MB `u2net_human_seg.onnx`
  for V16 matting at `~/.u2net/`.

**Smoke checks** (counts as of SESSION 181 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 843+ tests (compositions: 428)

# Media-engine (from media-engine/)
python -m pytest                              # 177 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New surfaces from SESSION 181**:
* No new SPA surfaces — all SESSION 181 changes were
  server-side fix-ups; existing recipe forms unchanged.
* New media-engine behaviour: `maybe_to_data_uri` now
  rewrites `/data/_internal/images/` paths to data URIs
  before Runway calls.

---

## AI / assistant context

- **Last session: SESSION 181 — V-arc layout / voice /
  storyboard dogfood + V17 proposal.** Eight commits. 11
  recipes validated (5 → 16 of 18). 5 production bugs
  fixed inline. V17 proposed for extend + keyframes
  integration. Tests: Django **428** unchanged; media-engine
  **177** (162 → 177, +15); SPA **95** unchanged.

- **Calibration carried forward (NEW SESSION 181)**:
  - **Operator "are we using X?" framing surfaces capability
    gaps.** All-green dogfood doesn't mean no gaps; operator
    framing catches missing capabilities that bugs-only
    testing misses.
  - **Asset upload UI is a recurring gap.** Recipes need
    AUDIO / IMAGE inputs the operator doesn't have; shell-
    side asset creation is the current workaround. Worth
    scoping a proper upload flow.
  - **External API validation tightens over time.** APIs
    that "worked when shipped" can fail later as upstream
    contracts tighten — periodic re-dogfood catches this.

- **Calibration carried forward (from earlier sessions)**:
  - "200 OK + plausible byte count" doesn't mean correct
    output (SESSION 180).
  - Uvicorn `--reload` has stale-during-restart window
    (SESSION 180).
  - drawtext `text=` footgun once `fontfile=` joins
    (SESSION 180).
  - Celery worker doesn't auto-reload (SESSION 179).
  - ffmpeg can't infer muxer from double-extension
    tempfile names (SESSION 179).
  - Real-mode dogfood finds bugs in every recipe
    (SESSIONS 179-181 — now 15+ bugs across 16 recipes).
  - PostCSS `@import` order (SESSION 178).
  - Operator catches premature extraction (SESSION 178).
  - DevTools computed-style snippet for visual bugs
    (SESSION 178).
  - Lossy paraphrase of scope locks (SESSION 177).
  - Handoff "swapped/edited" claims need verification
    (SESSION 177).
  - Runway DELETE poisons conversation (SESSION 176).
  - Mock-only test coverage hides upstream drift
    (SESSION 176).
  - Operator framing unlocks AI blockers (SESSION 176).
  - gpt-5 reasoning eats output budget silently
    (SESSION 176).
  - Tool descriptions need narration scaffolding
    (SESSION 176).
  - Real-mode dogfood after operator-facing slices.
  - SPA gates need both `pnpm test` AND `pnpm build`.
  - Distinct request boundaries for distinct side-effects.
  - Hook order across early returns (SESSION 169).
  - AI's "shipped" framing belongs to operator after
    review.
  - Doctor is the drift tool + handoff write at
    session-end.
  - OpenAI gpt-5 family uses Responses API.
  - lru_cached `get_settings()` bypasses FastAPI
    dependency_overrides.
  - Radix UI primitives need `userEvent` under jsdom.
  - Scope-lock reviews should distinguish operator
    input from LLM input.
  - Don't rationalise "somewhat readable" — look at
    operator-facing surface.
  - Vitest atomic assertions can mask real UX bugs.
  - Stale browser before stale code.
  - K6.4 stoplist curation trickle.

- **V-arc growth template (SESSION 179-181)**: V16 +
  V17-proposal follow the same shape. Narrow scope, opt-in
  defaults, one primitive + one knob + one endpoint per
  slice, real-mode validated before handoff. SESSION 181's
  in-slice fixes (broll dim-probe / Aleph timeouts /
  tail-merge / seed PNG / V13 path rewrite) fit the same
  pattern.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3.

- **2 of 18 V-arc recipes unvalidated** — `storyboard_voiced`
  + `dialogue_scene`. Both deferred until V17 lands per
  operator-locked direction.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
