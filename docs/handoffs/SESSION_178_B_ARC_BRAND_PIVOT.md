---
title: "Session 178 — B-arc brand pivot (CharacterOS → 24/7 GLOBAL AI parent company)"
date: 2026-05-18
status: complete
session: 178
previous_handoff: ./SESSION_177_DRIFT_SWEEP_TITLE_DISAMBIG_K10_REFRAME.md
---

# Session 178 — B-arc brand pivot

## TL;DR

Eight commits, single-arc session. Operator pivoted the entire
product framing: CharacterOS reframes from "the company / the
product" to "the first product in the **24/7 GLOBAL AI** parent
company's `*OS` family." The B-arc (Brand Ecosystem) shipped
B0-B5 in one sitting — scope lock, token infrastructure, V2 dark
navy + gold flip, per-surface color migration, messaging refresh
to infrastructure-credible tone, and a dedicated `/about`
parent-company route. B6-B10 deferred until product #2 is real
(operator caught B6 — multi-product extraction prep — as
premature YAGNI; correct call).

By session-end the SPA reads as **enterprise AI infrastructure
under 24/7 GLOBAL AI** instead of consumer SaaS:
* Dark navy `#0F1116` background with gold `#C8A35F` accent
  everywhere
* "Powered by 24/7 GLOBAL AI" footer + clickable header chip on
  every page
* `/about` route introducing the parent company + 6-product
  family roster (CharacterOS Live; DealerOS / AgentOS / OpsOS /
  VoiceOS / SupportOS reserved)
* All operator-facing copy rewritten: "Make a video" →
  "New render" / "Open recipe gallery"; "Create your first
  spokesperson" → "Provision spokesperson"; "Type your
  business. Click. Get a video ad." → "Compose a render. Ground
  in workspace knowledge. Ship to your channels."
* `BRAND_IDENTITY_V1.md` (editorial-warm / SMB-creator audience)
  preserved with deprecation banner; `BRAND_IDENTITY_V2.md`
  active.

Three TRUST_CALIBRATION entries added (PostCSS `@import` order
bug, operator-caught premature extraction, V2-not-applying-was-
browser-cache).

Tests: Django **816** unchanged (no backend touched). SPA vitest
**95** unchanged. Media-engine **133** unchanged. Zero
business-logic / model / route / API changes per B-arc contract
rule 6.

Real-mode spend this session: **$0** (no LLM / Runway /
Stability calls — purely SPA + docs work).

## Calibration moments worth carrying

Three new TRUST_CALIBRATION entries appended (full text in
`docs/TRUST_CALIBRATION.md`):

1. **PostCSS silently drops `@import` declarations that come
   after `@tailwind` directives.** B2 shipped looking visually
   broken — gold accents worked but background + text colors
   stayed V1 white. Root cause: my `@import "./tokens.css";`
   was AFTER `@tailwind base/components/utilities` in
   globals.css. CSS spec requires `@import` at the top; PostCSS
   drops misplaced ones silently. The fix was a one-line move
   plus a multi-line comment block documenting the order
   requirement so a future refactor can't regress. Pattern: if
   a Tailwind utility like `bg-background` renders transparent
   when the token IS defined in an `@import`ed file, check
   import order before debugging cascade.

2. **Operator caught premature extraction (B6).** The
   BRAND_ECOSYSTEM_V1 lock listed B6 as "multi-product
   extraction prep — stub product config files for DealerOS /
   AgentOS / etc." After B5 shipped, operator pushed back:
   "Lets hold off on B6 since it sounds like its outside the
   scope of the actual app we are working in right now."
   Correct call — the scope lock itself listed monorepo
   extraction as out-of-scope ("Reserved for product #2
   reality"); B6 was on the edge of that boundary. Pattern:
   the operator's "are we building this for something that
   exists?" framing is the right circuit-breaker on
   architectural slices in a multi-product / extensibility
   arc. AI tendency is to "complete the framework"; operator
   tendency is "ship for the product reality." Operator wins
   this trade.

3. **"V2 isn't applying" mystery was operator browser cache,
   not code.** During B2 dogfood the operator saw gold
   accents BUT white background. We diagnosed by having them
   paste DevTools computed-style output. The result was
   conclusive: `body computed bg: rgb(15, 17, 21)` —
   that's dark navy `#0F1115`, V2 perfectly applied. The
   operator perceived it as light due to (a) color blindness
   making dark navy hard to distinguish from light surfaces,
   and (b) several components had hardcoded light backgrounds
   that ARE visible against the dark body (which led to B3.1
   + B3.2 cleanup). Pattern: when an operator reports "V2
   isn't working" but partial evidence shows V2 IS working,
   the fastest path is a DevTools console snippet to read
   computed styles directly. Skip code-spelunking; ask for
   the runtime state.

## What shipped — commit by commit

### `4f567e1` — B0 — Brand Ecosystem scope lock + Brand Identity V2 + parent-company anchor

Architectural foundation. Three new design docs + 1 modified:

* `docs/design/BRAND_ECOSYSTEM_V1.md` — parent scope lock for
  the B-arc. 10 contract rules (no hardcoded company/product
  strings in components; tokens shared across products;
  per-product configs can override accent but not primitives;
  multi-product extraction reserved for product #2; etc.).
  6-product family reserved (`*OS` naming convention). Token
  architecture with parent / product / primitive layers. B0-B10
  slice breakdown. Six verification tests named. Out-of-scope
  list (no repo rename in v1; no Django project rename; no
  monorepo split; no per-workspace brand routing; no A/B
  testing). Open questions Q-b-1 through Q-b-6 deferred.

* `docs/design/BRAND_IDENTITY_V2.md` — visual lock that
  supersedes V1. Full palette derived from the signature card
  built SESSION 176: deep navy `#0F1116` background, gold
  `#C8A35F` accent, V2 muted/card/popover/border tokens.
  Typography consolidated to Geist (variable sans, display +
  body) + JetBrains Mono. Fraunces V1 editorial serif retired.
  Tighter sizing scale, multi-layer shadow scale calibrated for
  dark backgrounds, linear motion language. Six acceptance
  criteria locked for B1 (token infrastructure ships
  invisibly).

* `docs/247_GLOBAL_AI_OVERVIEW.md` — parent-company anchor doc.
  TL;DR + tagline ("ALWAYS ON. ALWAYS SMART. ALWAYS GLOBAL.")
  + product family roster + brand principles
  (infrastructure-credible / one-company-many-products /
  gold-is-signal-not-decoration / premium-dark-first /
  operator-first) + operational principles (real-mode
  validation / workspace isolation structural / doc-with-commit
  / operator-framing-unlocks-blockers).

* `docs/design/BRAND_IDENTITY_V1.md` — deprecation banner
  inserted; original content preserved beneath. Frontmatter
  `status: deprecated`, `superseded_by: BRAND_IDENTITY_V2.md`.

Naming decisions locked from the operator boot conversation:
(Q1) hybrid — keep `character-os` repo + `character_os` Django
project; brand layer extraction-ready inside this repo. (Q2)
keep `CHARACTER_OS_*` product anchors; add parent anchor doc.
(Q3) V2 supersedes V1 with banner. (Q4) incremental rollout.
(Q5 default) footer + header chip in B2; `/about` route in B5.
(Q6 default) B4 messaging side-by-side review.

### `3902814` — B1 — Brand layer infrastructure shipped invisibly

Six new files; zero visual change. Token system live but inert
(scoped to `[data-brand="v2"]` which nothing sets yet — V1
`:root` in globals.css continues to drive Tailwind).

* `web/src/lib/brand/tokens.ts` — TS source of truth for the
  V2 design tokens (colors / typography / spacing / radius /
  shadow / motion). Zero product-specific strings.

* `web/src/lib/brand/parent.ts` — 24/7 GLOBAL AI identity
  (name, slug, tagline, positioning, poweredByLabel, website,
  contact).

* `web/src/lib/brand/products/character-os.ts` — CharacterOS
  product config (name, slug, subtitle, description, optional
  accent override). Imports from tokens; no token primitives
  redefined per BRAND_ECOSYSTEM_V1 contract rule 2.

* `web/src/lib/brand/index.ts` — module entry. Exports
  `BRAND` aggregate + `useBrand()` React hook + direct
  re-exports of sub-modules + types.

* `web/src/styles/tokens.css` — V2 CSS custom properties
  scoped to `[data-brand="v2"]`. Mirrors tokens.ts.

* `web/src/styles/globals.css` — adds `@import "./tokens.css";`
  at top (placement matters — see B2 hotfix below).

Eight acceptance criteria from BRAND_IDENTITY_V2 §B1 all green.

### `30e2d3f` — B2 — flip the SPA to V2 (dark navy + gold) + brand chip + footer

First visible brand change. Four files:

* `web/index.html` — `data-brand="v2"` attribute on `<html>`
  activates the V2 token block. Title bumped to "CharacterOS
  — 24/7 GLOBAL AI" so browser tabs reflect the parent-company
  hierarchy. Fraunces dropped from the Google Fonts preload.

* `web/src/styles/globals.css` — V1 `:root` rescoped to
  `[data-brand="v1"]` for rollback. `.dark` block deleted (V2
  is dark-first). Fraunces-specific `font-variation-settings`
  axes + serif h1/h2/h3 stack + body radial-gradient paper
  background all removed. h1/h2/h3 use Geist with weight
  600/700 + tighter tracking. `::selection` switched from
  oxblood to gold accent at 22% alpha.

* `web/tailwind.config.ts` — `font-serif` + `font-display`
  consolidated to Geist (V2 has no serif primitive). `paper`
  + `paper-hover` boxShadow aliases re-pointed at V2's
  `--shadow-sm` / `--shadow` custom properties.

* `web/src/routes/_layout.tsx` — wired through `BRAND` layer.
  Product mark from `BRAND.product.name` ("CharacterOS") +
  subtitle from `BRAND.product.subtitle` ("Persistent AI
  Spokesperson Infrastructure"). New `ParentBrandChip`
  top-right: gold square + "a product of 24/7 GLOBAL AI" with
  gold company name. Footer right side
  `BRAND.parent.poweredByLabel` ("POWERED BY 24/7 GLOBAL AI").
  Layout switched to flex column so footer sticks to viewport
  bottom.

### `b2b6475` — B2 hotfix — move @import to top of globals.css

PostCSS silently dropped the `@import "./tokens.css"` because
it was placed AFTER `@tailwind` directives. CSS spec requires
`@import` at the absolute top before any other rule. Result:
neither V1 nor V2 token blocks reached the bundle, so
`bg-background` resolved to `hsl(var(--background))` with
undefined `--background` → invalid CSS → browser fallback to
white. Operator caught it: "the colors don't really look Navy
and Gold, they still look like its just Black words on a white
background." One-line fix plus a multi-line comment block
documenting the order requirement.

### `a2659c4` — B3.1 — talk-route + status colors migrated to V2 tokens

First B3 per-surface slice. `talk.tsx` had the most hardcoded-
color density of any operator-facing route (5 distinct
components used amber / emerald / yellow / blue / white
literals). All migrated to V2 semantic tokens. Side effect:
tailwind.config gains `success` + `warning` colors exposed as
utility classes (`bg-success`, `border-warning`, etc.) plus
`accent.muted` and `accent.bright` accent variants.

Components migrated: headphones tip (warning), AvatarCall
wrapper (bg-card border-border), LiveIndicator pill (muted
for mock / success for real), ToolResultPanel (4-state palette
to status tokens; queued → accent gold), RecallSessionsList +
RecallKnowledgeList cards (bg-card/80 border-border).

### `c850cfa` — B3.2 — migrate remaining hardcoded V1 colors across SPA to V2 semantic tokens

11 files migrated in one sweep. After this commit
`grep -rE 'bg-(amber|emerald|yellow|blue|...)-[0-9]'` returns
zero hits in SPA source. Replacement convention:
`border-X-500/40 bg-X-500/5 text-X-700` → `border-<token>/40
bg-<token>/10 text-<token>`. No semantic drift — every
replacement preserves the original tone intent.

Files: routes/compositions/$id.tsx, conversations/$id.tsx,
dashboard/index.tsx, recipes/$kind.tsx, workspace/knowledge.tsx
+ knowledge.$id.tsx; components/spokesperson-rebake-modal,
spokesperson-edit-modal, knowledge-panel, cost-ticker,
verification-status-badge.

### `0f97adb` — B4 — messaging refresh to infrastructure-credible tone

Operator-facing copy on highest-traffic surfaces rewritten.
Tone target: AWS / Stripe / Vercel docs, not consumer SaaS
landing. Verbs are infrastructure verbs (provision, compose,
ground, fire); no exclamation marks; no "transform your
business" copy.

Files: routes/dashboard/index.tsx (PrimaryAction hero,
SpokespeoplePanel empty, Activity empty), routes/recipes/index.tsx
(header copy), routes/spokespeople/$id.tsx (detail CTA),
components/onboarding-tour.tsx (all 3 steps).

Sample: "Type your business. Click. Get a video ad." →
"Compose a render. Ground in workspace knowledge. Ship to
your channels." "Make a video" → "New render" or "Open recipe
gallery". "Create your first spokesperson" → "Provision
spokesperson". Onboarding step 3 "Pick a recipe and render"
→ "Fire a composition".

### `fbf8909` — B5 — dedicated /about parent-company route + brand chip is now a link

First dedicated 24/7 GLOBAL AI surface in the SPA. Public
route (no auth gate) so external evaluators can land directly.

* `web/src/routes/about.tsx` — Hero (tagline accent line +
  parent name + description + positioning), Product family
  table (CharacterOS Live with pulsing dot + 5 reserved with
  muted pills), Contact card (name / title / email / website /
  phone), footer link to `/signature` template.

* `web/src/lib/brand/parent.ts` — added `productFamily` array
  mirroring `docs/247_GLOBAL_AI_OVERVIEW.md` §"Product family".
  CharacterOS `status: "live"`; DealerOS / AgentOS / OpsOS /
  VoiceOS / SupportOS `status: "reserved"`.

* `web/src/lib/brand/index.ts` — re-export
  `productFamily` + `ProductFamilyEntry` type.

* `web/src/App.tsx` — `<AboutRoute />` at `/about` (no
  RequireAuth wrapper).

* `web/src/routes/_layout.tsx` — `ParentBrandChip` upgraded
  to `<Link to="/about">` with hover state.

## B-arc completion state

| Slice | Status | Notes |
|---|---|---|
| B0 — Scope lock + identity v2 + parent anchor | ✓ shipped | docs/design/BRAND_ECOSYSTEM_V1.md + IDENTITY_V2.md + 247_GLOBAL_AI_OVERVIEW.md |
| B1 — Token infrastructure (invisible) | ✓ shipped | web/src/lib/brand/* + tokens.css |
| B2 — SPA flip to V2 | ✓ shipped | + B2 hotfix for @import order |
| B3.1 / B3.2 — Per-surface color migration | ✓ shipped | 0 hardcoded V1 colors remain |
| B4 — Messaging refresh | ✓ shipped | infrastructure-credible copy on hero / CTAs / onboarding |
| B5 — `/about` parent route | ✓ shipped | chip linked + product family roster |
| **B6 — Multi-product extraction prep** | **DEFERRED** | Operator caught it as premature; activates when product #2 is real |
| B7 — Enterprise polish pass | DEFERRED | Folds into normal SPA work as the operator dogfoods |
| B8 — Operator dogfood + screenshot review | DEFERRED | Happens naturally as the operator uses the SPA |
| B9 — V1 archive cleanup | DEFERRED | Doc maintenance; can happen anytime |
| B10 — Arc closure | DEFERRED | Becomes irrelevant if we close the arc effectively here |

**The B-arc is "effectively complete" at B5 for v1.** B6-B10
carry forward as latent items that activate when their
preconditions are met (product #2 reality / enterprise polish
during dogfood / etc.). The brand pivot is shipped end-to-end.

## Cast roster + workspace state

Unchanged from SESSION 177 close:

* Riggs — `06bf999f-...` voice `vincent`
* **Sasha** — `79d48883-...` voice `felix` (re-persisted SESSION 177)
* **Donny** — `f30b2980-...` voice `vincent` (re-persisted SESSION 177)
* Maya — `9410f23f-...` voice `victoria`
* Marcus — `b6a00dd8-...` voice `david` (W11.y personality
  + voice Runway-synced SESSION 176)

Plus the stale "Thruman" record at same prefix as Maya — still
queued for cleanup.

## Final state — tests + counts

* Django: **816** unchanged
* SPA vitest: **95** unchanged
* Media-engine: **133** unchanged
* Migrations: **62 / 62** unchanged
* Celery tasks: **9** unchanged
* Commits ahead of `origin/main`: 0 (all 8 B-arc commits
  pushed + wrap docs commit will be the 9th once committed)

INVENTORY restamp pending at session-end (mechanical — no
schema deltas).

## Operational notes carried forward

* **B-arc patterns now load-bearing.** The brand layer is the
  single source of truth for company/product strings. Every
  future SPA surface must import from `@/lib/brand` — never
  inline "CharacterOS" or "24/7 GLOBAL AI" in component
  markup.
* **PostCSS `@import` order** documented in globals.css
  itself; future edits to that file have the warning inline.
* **The `[data-brand="v2"]` HTML attribute** activates V2.
  Set in `web/index.html`. Flipping to `data-brand="v1"`
  rolls back to editorial-warm V1 styles (preserved scoped
  in globals.css).
* **No backend touched all session.** Django runserver +
  Celery worker stack from SESSION 177 close still valid.

## FIRST THING (SESSION 179): recipe + surface dogfood

Per operator-locked direction: hold further architectural arcs
and validate the actual product surfaces. The V-arc shipped 18
starter recipes SESSION 142-144 with mock-mode tests; only
`talking_head` has been real-mode validated (SESSION 176 R-arc
`render_video` tool). The other 17 are untested in real mode —
same pattern that bit the R-arc.

Per-operator dogfood:

1. **Pick 2-3 recipes operator actually needs** (e.g.
   `long_form_ad` for longer Rome video, `cinematic_visual`
   for B-roll, `storyboard_voiced` for multi-beat narrative).
2. Fire each from the new V2-themed `/recipes` gallery.
3. AI tails logs + DB + surfaces any real-mode bugs.
4. Fix what breaks; skip what works.

Other queued items if recipe dogfood resolves quickly:

* **K7.x v2 YouTube extractor real-mode validation** —
  shipped SESSION 175 but never operator-tested against a real
  YouTube URL. Likely to break given recent drift pattern.
* **W11.6.x image gen surfaces real-mode validation** —
  Stability + Runway image forms last validated SESSION 173.
* **Thruman stale spokesperson cleanup** — verify it's not
  load-bearing for anything, remove.
* **Multi-step composition title disambig** — shipped SESSION
  177; first multi-step composition operator runs will
  validate the per-step suffix.
* **K10 seed corpus** — still blocked on operator authoring
  the 5-10 markdown files about Character OS / 24/7 GLOBAL AI
  for `docs/seeds/character_os/*.md`.
* **K6.4 v3 architectural fix** — generalize sentence-position-
  aware imperative-verb detection.

## Stack-up boilerplate

```bash
cd infra && docker compose up -d
cd media-engine && source .venv/bin/activate && uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
cd shell && source .venv/bin/activate && python manage.py runserver
cd shell && source .venv/bin/activate && celery -A character_os worker --loglevel=info --pool=solo
cd web && pnpm dev
```

Doctor sweep:

```bash
python3 /Users/donkeyking/development/context-kit/context_kit.py doctor
```

Smoke checks:

```bash
cd shell && python -m pytest -q       # 816 tests
cd media-engine && python -m pytest -q  # 133 tests
cd web && pnpm test                   # 95 vitest tests
cd web && pnpm build                  # type-check + bundle
```

Recipe dogfood URL (after `pnpm dev`):

* `http://localhost:5174/recipes` — V2-themed recipe gallery.
* `http://localhost:5174/about` — new parent-company surface.
