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
> **Last handoff:** `docs/handoffs/SESSION_180_V_ARC_REAL_MODE_DOGFOOD_POLISH.md`.

---

## SESSION 180 outcome — V-arc real-mode dogfood: talking_head_polished

Three commits. Single-recipe dogfood. SESSION 179 closed
flagging 14 V-arc recipes still real-mode unvalidated;
SESSION 180 took `talking_head_polished` end-to-end and
surfaced **six** production bugs along the way — extending
the SESSION 179 "real-mode dogfood finds bugs in every
recipe it touches" pattern from four-for-four to
**ten-for-five**.

* **`65fb165`** — V9 polish form shorthands
  (`intro_text` / `outro_text` / `burn_captions`). Closed
  the gap where the SPA form didn't expose the polish
  steps' inputs, so the recipe was functionally identical
  to plain `talking_head` from the form.
* **`41fbbe4`** — intro_outro endpoint triple fix
  (drawtext apostrophe escape / input indexing math /
  hardcoded canvas dims). All three latent-since-V9
  bugs that would have bitten any real-mode polish
  render with apostrophe text on a non-1280x720 source.
* **`bcc9178`** — drawtext textfile + fontfile resolver.
  Pivoted from `text=` to `textfile=` after four
  iterations of text-escape variants all rendered
  blank cards (silent failure even when status-code-
  checking tests passed).

Tests: Django **428** (420 → 428, +8). Media-engine **156**
(143 → 156, +13). SPA vitest **95** unchanged.

Real-mode spend this session: **~$0.25** (one polished
composition + five intro_outro-only re-fires via
`retry_step` — backdrop/speech assets reused from cache).

### Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended:

1. **"200 OK + plausible byte count" doesn't mean
   correct output.** Four iterations of "the endpoint
   returns 200, mp4 is the right size, ship it" all
   produced pure-black rendered intro frames. Only the
   visible-pixel regression test caught the truth.
2. **Uvicorn `--reload` has a stale-during-restart
   window.** Mid-session edits + immediate re-fires
   land during the reloader's swap → in-flight POST
   served by old module. Signal: regenerated output
   with byte-identical md5 to the broken version.
3. **drawtext `text=` is a footgun once `fontfile=`
   joins the filter.** Multiple escape variants all
   silently render blank. `textfile=` is the only
   escape-immune option for any drawtext invocation
   that's been touched once.

### Final state at session close

* **5 V-arc recipes real-mode validated** (talking_head
  + long_form_ad + cinematic_visual +
  talking_head_with_backdrop + talking_head_polished).
* **13 recipes remain unvalidated.** SESSION 181
  priority.
* **Polish family is fully done** — `talking_head_polished`
  renders captions + intro card + outro card end-to-end
  with apostrophe-safe text on non-default body clip
  dimensions.

### FIRST THING (SESSION 181): pick a recipe and dogfood it

Operator-locked direction (continued from SESSION 178 →
179 → 180): walk through recipes you actually need
rather than mechanically dogfood all 18. The polish
family is done; layout family is the next-lowest-friction
+ highest-debugging-yield (exercises `composite_video`
in shapes V8 doesn't, validates `reformat_clip` and
`mix_audio` real-mode for the first time):

1. **`reels_format`** — 2-step (avatar speech →
   reformat_clip to 720:1280 vertical). ~$0.35 + ~2 min.
   First real-mode validation of `reformat_clip`.
2. **`pip_layout`** — picture-in-picture composite of
   two existing CLIPs. Needs 2 CLIP Assets in workspace.
   No Runway spend.
3. **`cohost_layout`** — same shape, different overlay.
4. **`broll_splice`** — base avatar + cinematic cutaway
   spliced in. 3-step.
5. **`music_bed_pass`** — base clip + audio mix-down.
   First real-mode `mix_audio`.
6. **`voice_design`** — one-shot custom voice. Pure
   media-engine call. ~$0.
7. **`multi_lang_dub`** — voice-clone across 29
   languages. Heaviest call.
8. **`style_remix_pass`** — Aleph gen4_aleph. ~$1.50.
9. **`storyboard_ad`** — 7-step. ~$2.00.
10. **`recut_teaser`** — first real-mode `transcribe`.
11. **`storyboard_voiced`** — V15.4 bonus 10-step.
    Heaviest spend.
12. **`dialogue_scene`** — multi-spokesperson.
13. **`backdrop_layout`** — standalone (distinct from
    V8's full flow).

Expected class of bugs (priors from SESSION 179+180
ten-for-five hit rate):
* Form gaps where recipe form doesn't expose starter's
  capability surface (SESSION 180 V9 shorthands pattern)
* Silent visual-output failures that pass status-code
  checks but produce wrong frames
* ffmpeg filter / muxer edge cases triggered by
  operator-realistic inputs (non-default sizes,
  apostrophes, special characters)
* Hardcoded defaults matching one common shape and
  silently breaking others

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete. Operator-facing edit
surfaces include voice swap, rebake, voice telemetry,
voice preview, personality split.
**Phase 4:** All four arcs (K / V / F / R) complete +
R-arc real-mode validated end-to-end (SESSION 176);
V-arc real-mode validation **in progress** (5 of 18
recipes, SESSIONS 158 + 179 + 180).
**Phase 5 (new):** Brand ecosystem repositioning under
24/7 GLOBAL AI parent (SESSION 178 B-arc).

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 + V16 | DONE (mock); **5/18 real-mode validated** |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED (SESSION 176) |
| W11.6.0-W11.6.5 (media gen) | DONE (SESSIONS 172-173) |
| W11.x voice telemetry + W11.y personality split | DONE (SESSIONS 174-175) + Runway-sync (SESSION 176) |
| K7.1 cost telemetry | DONE (SESSION 174) |
| K7.x v2 YouTube extractor | DONE (SESSION 175); real-mode unverified |
| Multi-step composition title disambig | DONE (SESSION 177) |
| Sasha + Donny voice re-persist | DONE (SESSION 177, data-only) |
| B0-B5 brand ecosystem pivot | DONE (SESSION 178) |
| V16 remove_avatar_background | DONE (SESSION 179) |
| **V9 polish form shorthands + intro_outro triple fix + textfile pivot** | **DONE (SESSION 180)** |
| B6-B10 brand arc | Deferred (product #2 reality / dogfood polish) |
| F8.1 (K10 seed corpus) | Queued (platform-authored markdown) |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| Thruman stale spokesperson cleanup | Queued (from SESSION 177) |
| W12 legacy form retirement | Queued |
| **13 of 18 V-arc recipes real-mode unverified** | **SESSION 181 priority** |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
    (SESSION 179 V16 hero + SESSION 180 polish hero)
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
    (stale "Thruman" record at same prefix queued for cleanup)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` —
    voice `david` (most-dogfooded — 4 ENDED realtime
    sessions + 1 rendered MP4 SESSION 176)

**Workspace artifacts from SESSION 180**:

  - 1 `Composition` (`c241a39a-...`,
    `talking_head_polished`, completed) — Riggs delivering
    "Three rules. Don't blink. Don't fold. Don't apologize."
    with "Riggs's Rules." intro + "Don't blink." outro
  - Final asset:
    `/data/_internal/intro_outros/019cf3803c177062.mp4`
    (~503KB, 11s)
  - Two card text files at `019cf3803c177062-{intro,outro}.txt`

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

**SESSION 181 stack-up note**: Celery worker was last
restarted SESSION 179 (pid 18279, picked up the V16
`remove_avatar_background` primitive registry entry).
SESSION 180 added no new primitives or tasks. Restart
only if you touch `apps/compositions/primitives/` OR
`apps/*/tasks.py` OR `apps/*/signals.py` (per SESSION 179
TRUST_CALIBRATION entry — Celery does NOT auto-reload).

**Media-engine note**: If iterating on `media-engine/app/`
files with `--reload` active, wait for the "Application
startup complete" log line between edits and re-fires.
Mid-reload window can serve requests with stale module
code — signal is regenerated output with byte-identical
md5 to the prior broken version (per SESSION 180
TRUST_CALIBRATION entry).

**First-call deps cached on the operator's box**: the
~176MB `u2net_human_seg.onnx` rembg model lives at
`~/.u2net/u2net_human_seg.onnx`. First V16 invocation
after a fresh checkout re-downloads (~5s).

**Smoke checks** (counts as of SESSION 180 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 843+ tests
# (SESSION 180 added 8 V9 polish tests; full count
#  TBD on next regen — running compositions/ shows 428)

# Media-engine (from media-engine/)
python -m pytest                              # 156 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New SPA / endpoint surfaces from SESSION 180**:
* `talking_head_polished` recipe form now exposes three
  shorthand fields below "Use workspace knowledge":
  - Intro card text (optional)
  - Outro card text (optional)
  - Burn captions from script (checkbox)

---

## AI / assistant context

- **Last session: SESSION 180 — V-arc real-mode dogfood:
  talking_head_polished.** Three commits, single-recipe
  dogfood. Six bugs surfaced + fixed inline: V9 form gap,
  drawtext apostrophe escape, input indexing math,
  hardcoded canvas dims, missing fontfile=, drawtext text=
  vs textfile= incompatibility. 5 V-arc recipes now
  real-mode validated (4 → 5). Tests: Django **428**
  compositions (420 → 428, +8); media-engine **156**
  (143 → 156, +13).

- **Calibration carried forward (NEW SESSION 180)**:
  - **"200 OK + plausible byte count" doesn't mean
    correct output.** For rendering pipelines, the
    regression test MUST probe the actual rendered
    output, not just the request/response surface.
  - **Uvicorn `--reload` has a stale-during-restart
    window.** Wait for "Application startup complete"
    between edits, or kill + restart cleanly.
  - **drawtext `text=` is a footgun once `fontfile=`
    joins the filter.** Use `textfile=` for any
    drawtext invocation that's been touched once.

- **Calibration carried forward (from earlier sessions)**:
  - Celery worker does NOT auto-reload (SESSION 179).
  - ffmpeg can't infer muxer from double-extension
    tempfile names (SESSION 179).
  - Real-mode dogfood found a bug in every recipe it
    touched (SESSION 179 — now reinforced ten-for-five
    after SESSION 180).
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

- **V-arc growth template (SESSION 179)**: V16 set the
  precedent for post-close V-slices. Narrow scope (one
  primitive + one knob + one endpoint), opt-in default to
  preserve backwards-compat, real-mode validated before
  handoff. SESSION 180's V9 form shorthand extension
  fits the same template.

- **Brand layer is load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3. Never inline
  "CharacterOS" or "24/7 GLOBAL AI" in component code.

- **13 of 18 V-arc recipes never real-mode validated** —
  hit rate so far is ten bugs across five recipes.
  Continue the dogfood walk; layout family is next.

- Collaboration conventions: AI drafts, human edits.
  Handoff `## Calibration moments worth carrying` +
  per-slice doc updates required at session end.
