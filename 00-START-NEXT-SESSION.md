---
state: active
---

# Next Session — Start Here

> **Design lock:** `docs/design/UI_REDESIGN_V2.md`.
> **Contract lock:** `docs/design/MEDIA_ENGINE_INTERNAL_API.md`.
> **SPA scope lock:** `docs/design/SPA_ARCHITECTURE.md`.
> **Brand ecosystem lock:** `docs/design/BRAND_ECOSYSTEM_V1.md`
> (locked SESSION 178 — 10 contract rules, B0-B10 slice
> breakdown). **B0-B5 SHIPPED; B6-B10 deferred to product #2
> reality.**
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
> **Last handoff:** `docs/handoffs/SESSION_179_V_ARC_REAL_MODE_DOGFOOD_V16.md`.

---

## SESSION 179 outcome — V-arc real-mode dogfood + V16

Six commits. Mixed real-mode dogfood + bug-fix + first-post-
close V-slice. SESSION 178 flagged "17 of 18 V-arc recipes
never real-mode validated" as the SESSION 179 focus.
SESSION 179 validated **three** of them end-to-end with real
Runway credits, surfaced four production bugs that mock-mode
tests couldn't catch, fixed every one, and shipped V16
(`remove_avatar_background`) as the V-arc's first post-close
addition to solve the cinematic-backdrop white-frame problem.

* **`f9f000e`** — SPA playback for media-engine concat /
  composite / mix assets (FastAPI StaticFiles `/data` mount +
  Vite `/data` proxy).
* **`9db31c3`** — `cinematic_visual` text-only path routes to
  gen4.5 (was failing 400 on gen4_turbo's image requirement).
* **`077c349`** — V8 multi-backdrop chain for
  `talking_head_with_backdrop` (eliminates 3s motion seam on
  long avatar speech over 10s-capped backdrops).
* **`04fcdb0`** — `_download_concat_input` resolver honors
  `/data/` SPA-mount prefix (intermediate composition assets
  can flow as inputs to downstream steps).
* **`57c2530`** — V16 `remove_avatar_background` primitive +
  opt-in `talking_head_with_backdrop` wiring (mat the white
  square out of Runway avatars; recipe gallery exposes the
  checkbox).
* **`88b341e`** — V16 muxer fix + broken-pipe stderr capture
  (ffmpeg can't infer format from `.webm.tmp` suffix; pin
  with `-f webm`; surface real ffmpeg errors instead of
  generic 500).
* **`9a05865`** — V16 design doc + CLAUDE.md updates
  (doc-with-commit discipline).

Tests: Django **843** (816 → 843, +27 — V8 multi-backdrop +
V16 primitive + V16 starter wiring + isolation allowlist).
Media-engine **143** (133 → 143, +10 — concat resolver +
remove_background endpoint). SPA vitest **95** unchanged.

Real-mode spend this session: **~$3.50** across four
compositions.

### Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended:

1. **Celery worker doesn't auto-reload on new primitive
   registrations.** V16 first dogfood failed
   `UnknownPrimitiveError` because the worker was running
   since before the registry edit. Pattern: any commit
   touching `apps/compositions/primitives/` OR `apps/*/tasks.py`
   OR `apps/*/signals.py` needs a Celery restart on the
   operator's box.
2. **ffmpeg can't infer output muxer from `.webm.tmp`
   tempfile suffix.** V16 first ffmpeg invocation died on
   muxer inference; pin with explicit `-f <muxer>` whenever
   shelling out with double-extension tempfile names.
3. **Real-mode dogfood found a bug in every recipe it
   touched.** Three real-mode runs yielded four production
   bugs. Mock-mode test coverage is necessary but
   insufficient. Budget the ~$0.50-$2.00 of Runway spend per
   validation as the cost of not shipping broken recipes.

### Final state at session close

* **V8 backdrop recipe** real-mode validated end-to-end at
  three depths: single-backdrop, multi-backdrop chain, AND
  with V16 matting enabled.
* **`remove_avatar_background` matting confirmed clean** on
  the underwater-backdrop dogfood — clean silhouette, no
  white frame.
* **Recipe gallery exposes the matting checkbox** below "Use
  workspace knowledge" on the `talking_head_with_backdrop`
  form. Default off.
* **V-arc validation count: 4 of 18 recipes.** SESSION 158
  (`talking_head`) + SESSION 179 (`long_form_ad` +
  `cinematic_visual` + `talking_head_with_backdrop`).
* **14 recipes remain unvalidated** — high probability of
  hidden bugs in each per the SESSION 179 four-for-four
  hit rate.

### FIRST THING (SESSION 180): pick a recipe and dogfood it

Operator-locked direction (SESSION 178 → 179): walk through
recipes you actually need rather than mechanically dogfood
all 18. Continuing the same pattern.

Polish family is the lowest-friction next-pick (single-step
or two-step compositions, fast feedback loop). Layout family
is the highest-value-for-debugging (exercises composite_video
in shapes V8 doesn't):

1. **`talking_head_polished`** — talking-head + captions +
   intro/outro. 4-step composition. ~$0.40 + ~2-3 min.
   Exercises V9 polish primitives end-to-end for the first
   time in real mode.
2. **`reels_format`** — talking-head reformatted to 720:1280
   vertical. 2-step. ~$0.35 + ~2 min. Validates
   `reformat_clip` real-mode.
3. **`pip_layout`** — picture-in-picture composite of two
   existing CLIPs. Needs two pre-existing CLIP Assets in the
   workspace (no Runway spend; pure media-engine ffmpeg).
4. **`cohost_layout`** — same shape as pip_layout, different
   ffmpeg overlay. Validates the cohost layout kind.
5. **`broll_splice`** — base avatar + cinematic cutaway
   spliced into a time window. 3-step. Validates the broll
   layout kind.
6. **`music_bed_pass`** — base clip + audio mix-down.
   Exercises `mix_audio` primitive real-mode for the first
   time.
7. **`voice_design`** — one-shot custom voice generation. No
   composition steps; pure media-engine call. ~$0 (Runway
   voice design is free-tier).
8. **`multi_lang_dub`** — voice-clone across 29 languages.
   Heaviest real-mode call.
9. **`style_remix_pass`** — Aleph gen4_aleph style transfer
   on an existing CLIP. ~$1.50.
10. **`storyboard_ad`** — 7-step Hook/Action/Payoff
    composition. Heavy spend (~$2.00).
11. **`recut_teaser`** — transcribe + trim existing CLIP into
    a teaser. Validates V12 transcribe.
12. **`storyboard_voiced`** — V15.4 bonus 10-step recipe.
    Heaviest spend.
13. **`dialogue_scene`** — multi-spokesperson scripted scene.
    Needs ≥2 cast members.

Skip / defer: `talking_head` (validated SESSION 158),
`talking_head_with_backdrop` + `backdrop_layout` (validated
SESSION 179), `long_form_ad` + `cinematic_visual` (validated
SESSION 179).

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete. Operator-facing edit surfaces
include voice swap, rebake, voice telemetry, voice preview,
personality split.
**Phase 4:** All four arcs (K / V / F / R) complete + R-arc
real-mode validated end-to-end (SESSION 176); V-arc
real-mode validation **in progress** (4 of 18 recipes,
SESSIONS 158 + 179).
**Phase 5 (new):** Brand ecosystem repositioning under
24/7 GLOBAL AI parent (SESSION 178 B-arc).

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 | DONE (mock); **4/18 real-mode validated** |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED (SESSION 176) |
| W11.6.0-W11.6.5 (media gen) | DONE (SESSIONS 172-173) |
| W11.x voice telemetry + W11.y personality split | DONE (SESSIONS 174-175) + Runway-sync (SESSION 176) |
| K7.1 cost telemetry | DONE (SESSION 174) |
| K7.x v2 YouTube extractor | DONE (SESSION 175); real-mode unverified |
| Multi-step composition title disambig | DONE (SESSION 177) |
| Sasha + Donny voice re-persist | DONE (SESSION 177, data-only) |
| B0-B5 brand ecosystem pivot | DONE (SESSION 178) |
| **V16 remove_avatar_background** | **DONE (SESSION 179) — post-close polish** |
| B6-B10 brand arc | Deferred (product #2 reality / dogfood polish) |
| F8.1 (K10 seed corpus) | Queued (platform-authored markdown) |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| Thruman stale spokesperson cleanup | Queued (from SESSION 177) |
| W12 legacy form retirement | Queued |
| **14 of 18 V-arc recipes real-mode unverified** | **SESSION 180 priority** |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
    (SESSION 179 V16 hero — validated against underwater
    backdrop, clean silhouette)
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
    (note: stale "Thruman" record at same prefix queued for
    cleanup)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice
    `david` (most dogfooded — 4 ENDED realtime sessions + 1
    rendered MP4 SESSION 176)

**Workspace artifacts from SESSION 179**:

  - 1 `Composition` (`a8a110da-...`, `talking_head_with_backdrop`,
    completed) with V16 matting applied — Riggs over an
    underwater scene; final asset
    `/data/_internal/composites/backdrop-c873d7757844b6af.mp4`
  - Multiple intermediate `Asset(CLIP)` rows from the
    backdrop chain + matting tests

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

**SESSION 180 stack-up note**: Celery worker was last
restarted SESSION 179 (pid 18279, picked up the V16
`remove_avatar_background` primitive registry entry). Restart
only if you touch `apps/compositions/primitives/` OR
`apps/*/tasks.py` OR `apps/*/signals.py` (per SESSION 179
TRUST_CALIBRATION entry — Celery does NOT auto-reload).

**First-call deps cached on the operator's box**: the
~176MB `u2net_human_seg.onnx` rembg model lives at
`~/.u2net/u2net_human_seg.onnx`. First V16 invocation after a
fresh checkout will re-download it (~5s).

**Smoke checks** (counts as of SESSION 179 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 843 tests

# Media-engine (from media-engine/)
python -m pytest                              # 143 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New SPA / endpoint surfaces from SESSION 179**:
* `http://localhost:5174/data/_internal/*` — media-engine
  filesystem proxy (FastAPI StaticFiles mount + Vite proxy).
  SPA `<video>` tags can play intermediate Composition assets
  by their canonical SPA URL.
* `POST /internal/clips/remove_background/` — media-engine
  endpoint for V16 matting. WebM/VP9 alpha output.
* `remove_avatar_bg` checkbox on the
  `talking_head_with_backdrop` recipe form. Default off; adds
  ~2-3 min wall-clock per render.

---

## AI / assistant context

- **Last session: SESSION 179 — V-arc real-mode dogfood + V16.**
  Six commits. Mixed real-mode dogfood + bug-fix + first-post-
  close V-slice. Three recipes validated end-to-end (4/18
  total now). V16 `remove_avatar_background` shipped to fix
  the cinematic-backdrop white-frame problem dogfood exposed.
  Tests: Django **843** (+27); media-engine **143** (+10);
  SPA **95** unchanged.

- **Calibration carried forward (NEW SESSION 179)**:
  - **Celery worker does NOT auto-reload.** Restart after
    any primitive / task / signal change. Django runserver
    auto-reloads but Celery doesn't.
  - **ffmpeg can't infer muxer from double-extension
    tempfile names.** Pin with `-f <muxer>` whenever
    shelling out with `.foo.tmp` patterns.
  - **Real-mode dogfood found four bugs across three
    recipes.** Mock-only tests hide upstream drift at scale.
    Budget ~$0.50-$2.00 per validation as the cost of not
    shipping broken recipes.

- **Calibration carried forward (from earlier sessions)**:
  - PostCSS `@import` order is load-bearing (SESSION 178).
  - Operator catches premature extraction (SESSION 178).
  - DevTools computed-style snippet is the fastest
    visual-bug diagnostic (SESSION 178).
  - Lossy paraphrase of scope locks in menu copy (SESSION 177).
  - Handoff "swapped/edited" claims need verification (SESSION 177).
  - Runway DELETE poisons the conversation (SESSION 176).
  - Mock-only test coverage hides upstream drift (SESSION 176).
  - Operator framing unlocks AI blockers (SESSION 176).
  - gpt-5 reasoning eats output budget silently (SESSION 176).
  - Tool descriptions need narration scaffolding (SESSION 176).
  - Real-mode dogfood after operator-facing slices.
  - SPA gates need both `pnpm test` AND `pnpm build`.
  - Distinct request boundaries for distinct side-effects.
  - Hook order across early returns (SESSION 169).
  - AI's "shipped" framing belongs to the operator after review.
  - Doctor is the drift tool + handoff write at session-end.
  - OpenAI gpt-5 family uses the Responses API.
  - lru_cached `get_settings()` bypasses FastAPI
    dependency_overrides.
  - Radix UI primitives need `userEvent` under jsdom.
  - Scope-lock reviews should distinguish operator input from
    LLM input.
  - Don't rationalise "somewhat readable" — look at what the
    operator-facing surface actually renders.
  - Vitest atomic assertions can mask real UX bugs.
  - Stale browser before stale code.
  - K6.4 stoplist curation trickle.

- **V-arc growth template (NEW SESSION 179)**: V16 set the
  precedent for post-close V-slices. Narrow scope (one
  primitive + one knob + one endpoint), opt-in default to
  preserve backwards-compat, real-mode validated before
  handoff. Codified in `VIDEO_COMPOSITION_V1.md`
  §"Post-close additions."

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3. Never inline
  "CharacterOS" or "24/7 GLOBAL AI" in component code.

- **14 of 18 V-arc recipes never real-mode validated** —
  same pattern as the R-arc pre-SESSION-176. SESSION 180
  continues the dogfood walk.

- Collaboration conventions: AI drafts, human edits. Handoff
  `## Calibration moments worth carrying` + per-slice doc
  updates required at session end.
