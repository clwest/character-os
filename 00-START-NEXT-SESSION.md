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
> **Last handoff:** `docs/handoffs/SESSION_178_B_ARC_BRAND_PIVOT.md`.

---

## SESSION 178 outcome — B-arc brand pivot

Eight commits, single-arc session. CharacterOS repositioned as
**the first product under the 24/7 GLOBAL AI parent company**.

The SPA now reads as enterprise AI infrastructure: dark navy
`#0F1116` background + gold `#C8A35F` accent, Geist sans
throughout, "Powered by 24/7 GLOBAL AI" footer + clickable
header chip on every page, `/about` parent route with product
family roster (CharacterOS Live + 5 reserved siblings).
Operator-facing copy rewritten infrastructure-credible — no
"make a video / type your business" consumer language.

* **`4f567e1`** — B0 scope lock + Brand Identity V2 +
  247_GLOBAL_AI_OVERVIEW parent anchor + V1 deprecation banner.
* **`3902814`** — B1 brand layer infrastructure (invisible).
* **`30e2d3f`** — B2 SPA flip to V2 dark + gold + header chip
  + footer.
* **`b2b6475`** — B2 hotfix (PostCSS `@import` order; tokens
  weren't reaching the bundle).
* **`a2659c4`** — B3.1 talk-route + status colors to V2 tokens.
* **`c850cfa`** — B3.2 rest of SPA hardcoded colors to V2
  tokens (0 hardcoded `bg-(amber|emerald|...)` remain).
* **`0f97adb`** — B4 messaging refresh to infrastructure tone.
* **`fbf8909`** — B5 dedicated `/about` parent route + chip
  linked.

Tests: Django **816**; SPA **95**; media-engine **133** — all
unchanged. Real-mode spend: **$0** (no LLM / Runway / Stability
calls — purely SPA + docs work).

### Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended:

1. **PostCSS silently drops `@import` declarations placed after
   `@tailwind` directives.** Operator-caught visual bug; the
   fix was a 1-line move + an inline comment block so future
   refactors can't regress the order.
2. **Operator caught premature extraction (B6).** B-arc lock
   listed B6 as multi-product extraction prep; operator
   pushback ("outside the scope of the actual app we are
   working in right now") was correct — premature framework
   work. Pattern: operator's "are we building this for
   something that exists?" framing is the right circuit-
   breaker on architectural slices.
3. **"V2 isn't applying" mystery was browser cache + color
   blindness, not code.** DevTools computed-style output
   confirmed V2 IS applied (`body computed bg: rgb(15, 17,
   21)`). Pattern: when operator reports visual regression
   but partial evidence shows the change IS live, ask for
   DevTools computed styles first — skip code-spelunking.

### Final state at session close

* **B-arc effectively complete at B5.** B6-B10 deferred to
  product #2 reality (per operator-locked direction +
  contract rule 10 of the lock).
* **/about route live and public** (no auth gate).
* **Brand chip clickable** from every authenticated page.
* **All operator-visible copy** flows through `BRAND.parent` /
  `BRAND.product` — never inlined.
* **Operator pivot from architectural slices to product
  dogfood.** Recipe + surface validation is the focus going
  forward.

### FIRST THING (SESSION 179): recipe + surface dogfood

The V-arc shipped 18 starter recipes SESSION 142-144 with
mock-mode tests; only `talking_head` has been real-mode
validated (SESSION 176 via R-arc's `render_video` tool). The
other 17 are untested in real mode — **same pattern that bit
the R-arc**. Operator-locked direction is to walk through
recipes you actually need rather than mechanically dogfood
all 18.

Pick by mood:

1. **Recipe dogfood — long_form_ad.** Multi-step composition
   (split_script + concat_clips chain). Will exercise the
   SESSION 177 multi-step title disambiguation. ~$0.50 +
   ~3-5 min render.
2. **Recipe dogfood — cinematic_visual.** Generate-visual-clip
   primitive. ~$0.40 + ~2 min.
3. **Recipe dogfood — storyboard_voiced.** V15.4 bonus
   recipe; multi-beat narrative. Heaviest spend.
4. **K7.x v2 YouTube extractor real-mode validation.** Shipped
   SESSION 175; never operator-tested against a real URL.
   Likely to break given recent drift pattern. ~$0 + ~30 sec.
5. **W11.6.x image gen surfaces real-mode validation.**
   Stability + Runway image forms last validated SESSION 173.
6. **Thruman stale spokesperson cleanup.** Verify not
   load-bearing + remove.
7. **K10 seed corpus** — still blocked on you authoring 5-10
   markdown files about CharacterOS for
   `docs/seeds/character_os/*.md`.
8. **K6.4 v3 architectural fix** — generalize sentence-
   position-aware imperative-verb detection. ~1 session.

---

## Where we are

**Phase 0-2:** Done.
**Phase 3:** Wizard arc complete. Operator-facing edit surfaces
include voice swap, rebake, voice telemetry, voice preview,
personality split.
**Phase 4:** All four arcs (K / V / F / R) complete + R-arc
real-mode validated end-to-end (SESSION 176).
**Phase 5 (new):** Brand ecosystem repositioning under
24/7 GLOBAL AI parent (SESSION 178 B-arc).

| Surface | Status |
|---|---|
| W1-W11 | DONE |
| K0-K9 | DONE |
| V0-V15 | DONE (mock); 1/18 real-mode validated |
| F0-F10 | DONE |
| R0-R10 + R6.1 | DONE + REAL-MODE VALIDATED (SESSION 176) |
| W11.6.0-W11.6.5 (media gen) | DONE (SESSIONS 172-173) |
| W11.x voice telemetry + W11.y personality split | DONE (SESSIONS 174-175) + Runway-sync (SESSION 176) |
| K7.1 cost telemetry | DONE (SESSION 174) |
| K7.x v2 YouTube extractor | DONE (SESSION 175); real-mode unverified |
| Multi-step composition title disambig | DONE (SESSION 177) |
| Sasha + Donny voice re-persist | DONE (SESSION 177, data-only) |
| **B0-B5 brand ecosystem pivot** | **DONE (SESSION 178)** |
| B6-B10 brand arc | Deferred (product #2 reality / dogfood polish) |
| F8.1 (K10 seed corpus) | Queued (platform-authored markdown) |
| K7.x v3 YouTube oEmbed | Queued |
| K6.4 v3 architectural fix | Queued |
| Thruman stale spokesperson cleanup | Queued (from SESSION 177) |
| W12 legacy form retirement | Queued |
| **17 of 18 V-arc recipes real-mode unverified** | **NEW (likely drift) — SESSION 179 candidate** |

**Cast roster in workspace `admins-workspace`**:

  - Riggs the Donkey — id `06bf999f-...` — voice `vincent`
  - Sasha the Raccoon — id `79d48883-...` — voice `felix`
  - Donny the Sloth — id `f30b2980-...` — voice `vincent`
  - Maya the Panda — id `9410f23f-...` — voice `victoria`
    (note: stale "Thruman" record at same prefix queued for
    cleanup)
  - **Marcus the Battle Unicorn** — id `b6a00dd8-...` — voice
    `david` (most dogfooded — 4 ENDED realtime sessions + 1
    rendered MP4 SESSION 176)

**Workspace artifacts from SESSION 176**:

  - Real `Asset(TRANSCRIPT)` rows from Marcus's R-arc sessions
  - 1 `Composition` (talking_head, completed) from
    `render_video` tool invocation
  - 1 `Asset(clip)` MP4 of Marcus on CloudFront

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

**SESSION 179 stack-up note**: Celery worker was last restarted
SESSION 176 close (pid 5625, picked up
`spokespeople.sync_personality_to_runway`). No model / task
changes SESSION 177-178; restart only if you touch
`apps/spokespeople/` OR `apps/realtime/`.

**Smoke checks** (counts as of SESSION 178 close):

```bash
# Backend (from shell/)
python manage.py inventory
python -m pytest                              # 816 tests

# Media-engine (from media-engine/)
python -m pytest                              # 133 tests

# SPA (from web/)
pnpm build                                    # type-check + bundle
pnpm test                                     # 95 vitest tests
```

**New SPA surfaces from SESSION 178**:
* `http://localhost:5174/about` — parent-company route (public,
  no auth gate). Hero + product family roster + contact.
* `http://localhost:5174/signature` — email signature template
  (SESSION 176; integrated into /about footer link in B5).

---

## AI / assistant context

- **Last session: SESSION 178 — B-arc brand pivot.** Eight
  commits, single-arc session. CharacterOS repositioned as
  the first product under 24/7 GLOBAL AI parent company.
  SPA flipped to V2 dark + gold + Geist + infrastructure
  copy; `/about` parent route live. Tests: Django **816**;
  SPA **95**; media-engine **133** — all unchanged.

- **Calibration carried forward (NEW SESSION 178)**:
  - **PostCSS `@import` order is load-bearing.** Place
    `@import` at the absolute top of CSS files; PostCSS
    silently drops misplaced imports.
  - **Operator catches premature extraction.** Architectural
    "complete the framework" instinct is wrong when the
    target reality doesn't exist yet.
  - **DevTools computed-style snippet is the fastest
    visual-bug diagnostic.** Skip code-spelunking when the
    operator reports visual regression — ask for runtime
    state first.

- **Calibration carried forward (from earlier sessions)**:
  - Lossy paraphrase of scope locks in menu copy (SESSION 177).
  - Handoff "swapped/edited" claims need verification (SESSION 177).
  - Runway DELETE poisons the conversation (SESSION 176).
  - Mock-only test coverage hides upstream drift (SESSION 176).
  - Operator framing unlocks AI blockers (SESSION 176).
  - gpt-5 reasoning eats output budget silently (SESSION 176).
  - Tool descriptions need narration scaffolding (SESSION 176).
  - Real-mode dogfood after operator-facing slices.
  - Celery worker restart for any model-extending session.
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

- **Brand layer is now load-bearing.** Every component must
  import company/product strings from `@/lib/brand` per
  BRAND_ECOSYSTEM_V1 contract rule 3. Never inline
  "CharacterOS" or "24/7 GLOBAL AI" in component code.

- **17 of 18 V-arc recipes never real-mode validated.** Same
  pattern as the R-arc pre-SESSION-176. Likely class of bugs:
  Runway API contract drift, mock-mode responses hiding
  real-mode rejections, missing fields at session-create.
  SESSION 179 focus.

- Collaboration conventions: AI drafts, human edits. Handoff
  `## Calibration moments worth carrying` + per-slice doc
  updates required at session end.
