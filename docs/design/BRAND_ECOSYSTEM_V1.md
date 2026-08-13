---
title: "Brand Ecosystem v1 — 24/7 GLOBAL AI parent + multi-product architecture"
status: locked
generated: 2026-05-18 (SESSION 178)
companion_docs: ["BRAND_IDENTITY_V2.md", "247_GLOBAL_AI_OVERVIEW.md"]
supersedes: "implicit single-product framing in UI_REDESIGN_V2.md + BRAND_IDENTITY_V1.md"
---

# Brand Ecosystem v1

> **Read first:** this is the parent scope lock for the B-arc
> (Brand Ecosystem). It establishes the brand hierarchy, names
> the product family, locks the token-system architecture, and
> sequences the B0-B10 slice breakdown. Visual specifics
> (colors, typography, spacing, shadows) live in
> `BRAND_IDENTITY_V2.md`. The parent company narrative lives
> in `247_GLOBAL_AI_OVERVIEW.md` (to be authored in B0).

---

## TL;DR — One Sentence

**24/7 GLOBAL AI is a premium enterprise AI infrastructure
parent company** that ships a family of `*OS` products
(CharacterOS being the first), unified by a shared dark-navy +
gold visual identity, shared design tokens, and shared "Powered
by 24/7 GLOBAL AI" identity layer — built so a second product
can join the family without re-platforming the first.

---

## Why this lock exists

**SESSION 177 close discovered a brand pivot**, not drift:

* `BRAND_IDENTITY_V1.md` (SESSION 117) locked an
  **editorial-warm, paper-toned, light-mode-only, SMB / solo-
  creator** aesthetic — explicitly rejecting enterprise blue.
* SESSION 178 operator framing inverts every premise: premium
  enterprise dark navy + gold, parent-company-with-product-
  family, infrastructure-focused messaging.

Two product directions are not compatible. v1 isn't drift —
it's a different product pitch. v2 supersedes it deliberately.

**Architectural goal**: CharacterOS should not feel like the
company. It should feel like a product powered by 24/7 GLOBAL
AI. Future products (DealerOS, AgentOS, OpsOS, VoiceOS,
SupportOS) should slot in without re-platforming.

---

## Contract rules (load-bearing)

These bind every B-slice the same way V0's rules bind every
composition slice.

1. **24/7 GLOBAL AI is the only company name surfaced as the
   author.** Every public-facing surface (footer, email
   signature, "about", marketing pages, status pages) names
   24/7 GLOBAL AI as the company. CharacterOS appears only
   as the **product name** on product-specific surfaces.

2. **Products share design tokens; products do not share
   product identity.** A single source of truth for colors,
   typography, spacing, shadows, motion lives in shared
   modules (`web/src/lib/brand/tokens.ts`,
   `web/src/styles/tokens.css`, Tailwind config). Per-product
   identity (logos, product name, taglines, accent
   override) lives in per-product config that **reads from
   tokens, never overrides them across products**.

3. **No hardcoded company / product / accent strings in
   component code.** All references to "24/7 GLOBAL AI",
   "CharacterOS", "ALWAYS ON. ALWAYS SMART. ALWAYS GLOBAL.",
   the gold accent, etc. go through a `brand` config import.
   `<header>` markup never inlines product names.

4. **Token mutations don't break products.** A color rename
   in `tokens.ts` must propagate to every consumer without
   per-product edits. CI / type-check enforces this:
   removed tokens fail the build.

5. **Future products extract cleanly.** The B-arc
   intentionally keeps multi-product machinery inside this
   repo (no premature monorepo). The shape must be such that
   when product #2 starts, the brand layer extracts to a
   shared package without rewriting CharacterOS.

6. **Existing product functionality preserved bit-for-bit.**
   The B-arc is *visual + naming + messaging only*. Zero
   business-logic, model, route, or API contract changes.
   Test counts before / after a B-slice must match.

7. **BRAND_IDENTITY_V1 is preserved with a deprecation
   banner.** V1 stays in `docs/design/` with a top-of-file
   header noting that v2 supersedes it + a one-paragraph
   explanation of the audience pivot. Future agents see
   both and understand the deliberate reposition.

8. **Messaging tone is infrastructure-credible, not
   marketing-loud.** Operator-facing copy uses language
   like "Persistent AI Representatives" and "Autonomous
   Spokesperson Infrastructure" — credible, intelligent,
   infrastructure-focused. No exclamation marks, no
   "transform your business" copy. The model is enterprise
   AWS / Stripe / Vercel docs, not consumer SaaS landing
   pages.

9. **Incremental rollout, never big-bang.** Every B-slice
   ships a contained surface change with screenshots in the
   commit. No single PR flips the whole SPA. Side-by-side
   comparison must be possible at every step.

10. **The repo + Django project keep their current names
    for v1.** `character-os` repo + `character_os` Django
    project + `apps.*` modules stay. Premature rename =
    premature pain. Multi-product extraction is a real
    project for product #2's launch session, not this arc.

---

## Brand hierarchy

```
24/7 GLOBAL AI                              (parent company)
├── CharacterOS                             (product: persistent AI spokesperson infrastructure)
├── DealerOS                                (future: dealer / automotive vertical)
├── AgentOS                                 (future: agent network operations)
├── OpsOS                                   (future: operations automation)
├── VoiceOS                                 (future: voice-first interfaces)
└── SupportOS                               (future: customer support intelligence)
```

* **Parent company**: 24/7 GLOBAL AI. Tagline: *"ALWAYS ON.
  ALWAYS SMART. ALWAYS GLOBAL."*
* **Product naming convention**: `<Domain>OS`. CamelCase, no
  spaces. The `OS` suffix is the family signal.
* **Product subtitle convention**: an infrastructure-focused
  one-liner. CharacterOS: *"Persistent AI Spokesperson
  Infrastructure"* (locked B4).
* **Product accent override**: each product MAY override the
  gold accent with a single secondary color for product
  recognition. CharacterOS keeps gold. Reserved for future
  products (TBD per product launch).

---

## Naming decisions (operator-locked SESSION 178)

These were the load-bearing questions from the boot
conversation. Locked answers:

* **(Q1) Repo + Django package**: hybrid. Keep
  `character-os` repo and `character_os` Django project + all
  `apps.*` modules. Brand layer ships inside this repo at a
  shape ready for extraction when product #2 is real. **No
  monorepo split in v1.**
* **(Q2 — default, operator review)** Doc anchor naming:
  `docs/CHARACTER_OS_*.md` stays as product-specific anchors
  (they describe CharacterOS). New parent anchor
  `docs/247_GLOBAL_AI_OVERVIEW.md` ships in B0 — the company
  narrative, brand hierarchy diagram, product roster.
* **(Q3) BRAND_IDENTITY_V1**: stays in `docs/design/` with a
  deprecation banner pointing to v2. One-paragraph history
  note on the audience pivot. V2 is the active visual lock.
* **(Q4) Visual rollout**: incremental. B1 ships token
  infrastructure invisibly. B2 ships layout chrome. B3 ships
  per-surface application with screenshots in each commit.
  Side-by-side comparison required at every step.
* **(Q5 — default, operator review)** Parent identity
  surfaces: footer "Powered by 24/7 GLOBAL AI" everywhere
  (B2) + a subtle header chip top-right (B2). Dedicated
  `/about` parent-company route deferred to B5.
* **(Q6 — default, operator review)** Messaging tone: B4
  will draft each replaced phrase side-by-side
  (marketing-y vs infrastructure variant) for operator
  pick. Default lean is the infrastructure variant.

---

## Token architecture

### Locations

| Layer | Path | Purpose |
|---|---|---|
| Primitive tokens (TS) | `web/src/lib/brand/tokens.ts` | Single source of truth for color / typography / spacing / shadow / motion primitives. TS const objects, fully typed. |
| Primitive tokens (CSS vars) | `web/src/styles/tokens.css` | CSS custom properties mirroring `tokens.ts` for runtime theming + Tailwind. Generated from TS in v2 (manual in v1 — small enough). |
| Tailwind config | `web/tailwind.config.{js,ts}` | Maps Tailwind classes to CSS vars. `bg-background`, `text-foreground`, `text-accent`, etc. all flow from tokens. |
| Product config | `web/src/lib/brand/products/character-os.ts` | Per-product identity (product name, subtitle, tagline override, optional accent override). Reads from primitive tokens. |
| Parent config | `web/src/lib/brand/parent.ts` | 24/7 GLOBAL AI company identity (name, tagline, contact, signature card data). Reads from primitive tokens. |
| Active product hook | `web/src/lib/brand/index.ts` | Exports `useBrand()` + `BRAND` consts that components consume. Defaults to CharacterOS product in v1; future routing can swap. |

### What lives where

* **Primitive tokens (`tokens.ts`)**: color palette (navy
  shades, gold accents, neutrals), font families, font sizes,
  line heights, spacing scale, radius scale, shadow scale,
  motion durations + easings.
* **Product config**: product name string, product subtitle,
  product slug, optional accent override (CharacterOS = gold,
  others TBD), product logo asset path.
* **Parent config**: company name string, tagline, contact
  details, signature card props, footer copy.
* **Component code**: imports `BRAND` from
  `@/lib/brand/index.ts` — never inlines company / product
  strings.

### Migration path for future product

When product #2 (e.g. DealerOS) becomes real:

1. `web/src/lib/brand/` extracts to a publishable npm
   package `@247globalai/brand`.
2. `tokens.ts` + `parent.ts` move into the package
   unchanged.
3. Per-product configs (`character-os.ts`, `dealer-os.ts`)
   live in each product's repo and import the shared
   package.
4. Existing CharacterOS code keeps importing from
   `@/lib/brand/index.ts` — the shape is identical.

This is why **the token layer must not contain any
product-specific strings**. Per-product identity stays in
per-product config from day one.

---

## Backend touch points (shell + media-engine)

Brand layer is primarily SPA / web concern, but two backend
surfaces leak product / company strings:

* **`character_os/api_prompts.py`** + tone archetype copy
  — operator-facing strings the SPA renders. B4 reviews.
* **Email-style templates** (if any) in
  `shell/character_os/templates/` — none currently, but
  noted for future-proofing.
* **Django project package name** `character_os` —
  intentionally NOT renamed (contract rule 10).
* **Doc filenames** `CHARACTER_OS_*.md` —
  intentionally kept as product docs (Q2 default).

No backend code changes in B0-B3. B4 may add a tiny
`brand` config module to `character_os/` if backend-rendered
strings need parameterization; otherwise no backend
churn.

---

## Slice breakdown

| Slice | Deliverable | Depends on |
|---|---|---|
| **B0** | Scope lock (this doc) + `BRAND_IDENTITY_V2.md` + V1 deprecation banner + new `247_GLOBAL_AI_OVERVIEW.md` parent anchor doc. | nothing |
| **B1** | Token infrastructure shipped invisibly. `lib/brand/tokens.ts`, `styles/tokens.css`, Tailwind config wired to CSS vars, `lib/brand/parent.ts` + `lib/brand/products/character-os.ts` + `lib/brand/index.ts` scaffolded. **No visual changes** — existing editorial-warm colors stay as token values temporarily so the SPA renders identically. The mechanism is in place; the values flip in B2. | B0 |
| **B2** | Layout chrome flipped to dark-navy + gold. Header, nav, dashboard frame, footer with "Powered by 24/7 GLOBAL AI". Subtle 24/7 GLOBAL AI chip top-right of header. **First visible brand change.** Operator review pause before B3. | B1 |
| **B3** | Per-surface rollout (incremental commits with screenshots): wizard, spokesperson detail, talk route, recipe gallery, knowledge surfaces, conversation chat, composition status, signature route. Each surface a separate commit so any can roll back. | B2 |
| **B4** | Messaging refresh. Replace consumer-product language ("AI video generator", "avatar creator", "ad maker") with infrastructure language ("Persistent AI Representatives", "Autonomous Spokesperson Infrastructure", etc.). Each replacement drafted side-by-side (marketing-y vs infrastructure variants) for operator pick. | B3 |
| **B5** | Dedicated `/about` parent-company route. Introduces 24/7 GLOBAL AI, product roster, value-prop. Signature card already built integrates here. | B4 |
| **B6** | Multi-product extraction prep. `lib/brand/` shape audited + documented for npm-package extraction. Stub product config files for DealerOS / AgentOS / etc. (config-only, no UI) to prove the structure. | B5 |
| **B7** | Enterprise polish pass: cinematic dashboards, subtle global-grid backgrounds, premium shadow scale, motion language. Calibrated against the "enterprise AI operations center" aesthetic. | B6 |
| **B8** | Operator dogfood + screenshot review of every flipped surface. Calibration entries from any tone misses. | B7 |
| **B9** | BRAND_IDENTITY_V1 archived (kept in `docs/design/archive/` if shelf gets crowded; otherwise stays with deprecation banner). | B8 |
| **B10** | B-arc closes. R-arc-style change-log entry + handoff aggregation. | B9 |

Estimated ~6-10 sessions across the arc. B1 is the most
critical (token infrastructure) — get it right and B2-B7
become mechanical.

---

## Out of scope (explicitly)

* **Repo rename to `247-global-ai`.** Premature. Reserved
  for product #2's launch session.
* **Django project rename from `character_os`.** Same reason.
  Internal naming stays.
* **Monorepo split.** Reserved for product #2 reality.
* **Multi-tenant brand routing.** No per-workspace brand
  override in v1. Every CharacterOS workspace gets the same
  CharacterOS-product look.
* **A/B testing of v1 vs v2 brand.** Operator decided v2 is
  the direction; we're not running a beauty contest.
* **Brand consultancy / external design agency input.**
  In-house, operator-led, AI-assisted.
* **Logo / wordmark design.** Treated as a fixed input. If
  the operator ships a logo asset, B5 integrates it.
  Otherwise B5 uses the typeset "24/7 GLOBAL AI" wordmark
  from the signature card.

---

## Open questions (resolve in implementation slices)

* **Q-b-1 — Token value source for dark navy + gold.** The
  signature card uses `#0F1116` background + `#C8A35F` gold
  accent. Are these the locked values for B1, or should B1
  propose a wider palette (deep navy variants, gold
  variants) calibrated for full SPA use?
* **Q-b-2 — Typography for v2.** V1 used Fraunces (display
  serif) + Geist Sans + JetBrains Mono. V2 enterprise
  direction may want a sans display (Inter Display, Geist
  Variable, or a tighter system) instead of a serif. Resolve
  in B1.
* **Q-b-3 — Light mode handling.** V1 was light-only. V2 is
  dark-first. Do we ship a light mode at all in v1 (system
  preference respecting), or commit to dark-only? Resolve
  in B1.
* **Q-b-4 — Per-product accent override.** CharacterOS keeps
  gold. Future DealerOS / AgentOS / etc. accents are TBD.
  Don't pre-pick — resolve when each product launches.
* **Q-b-5 — Background motion language.** Operator mentioned
  "subtle world-grid / global network visuals". How subtle?
  Static SVG background pattern, or animated CSS, or pure
  typography + spacing carries the aesthetic? Resolve B7.
* **Q-b-6 — Email signature surface scope.** Signature card
  shipped SESSION 176 at `/signature` (SPA-only preview).
  Does B5 surface this in a settings page operators can copy
  from, or stays a developer-facing preview? Resolve B5.

---

## How to verify the brand-ecosystem guarantees

Before B10 closes, six test cases must pass:

1. **`test_no_hardcoded_company_string_in_components`**: grep
   the SPA `src/components/**` for "24/7 GLOBAL AI" — every
   match must be in a test or a `lib/brand/` file. Component
   code goes through `BRAND` import.

2. **`test_no_hardcoded_product_string_in_components`**:
   same shape, for "CharacterOS" / "Character OS" in
   component code.

3. **`test_token_removal_fails_typecheck`**: remove a token
   from `tokens.ts`, run `pnpm tsc --noEmit`, expect errors
   in every consumer site. Proves the type chain is real.

4. **`test_product_config_extractable`**: introduce a stub
   `dealer-os.ts` product config that imports from the brand
   layer only; assert it compiles + exposes the same shape
   as `character-os.ts`. Proves the extraction path works.

5. **`test_brand_identity_v1_has_deprecation_banner`**:
   simple file-content check that V1 doc starts with the
   "superseded by V2" header banner.

6. **`test_no_marketing_words_in_operator_copy`**: lint
   pass against an operator-copy allowlist. Catches
   "Transform your business", "Revolutionary AI", etc. from
   ever shipping accidentally.

The six tests are the contract. Implementation can vary; the
tests cannot fail.

---

## Migration story (BRAND_IDENTITY_V1 → V2)

* V1 stays at `docs/design/BRAND_IDENTITY_V1.md` with a
  top-of-file banner inserted in B0:

  > **DEPRECATED — superseded by BRAND_IDENTITY_V2.md
  > (SESSION 178).** This document captured the v1
  > editorial-warm light-mode brand locked SESSION 117 for
  > SMB / solo-creator audience. SESSION 178 operator pivoted
  > to a premium enterprise dark-mode brand under 24/7 GLOBAL
  > AI parent company. V1 preserved here as history; V2 is
  > the active visual lock.

* V2 lives at `docs/design/BRAND_IDENTITY_V2.md` with full
  color palette, typography stack, spacing scale, shadow
  scale, motion language.

* `00-START-NEXT-SESSION.md` Design lock list:
  - Active: `BRAND_IDENTITY_V2.md` (replaces v1 in the
    listing)
  - Archived reference: `BRAND_IDENTITY_V1.md` (footnote)
  - New: `BRAND_ECOSYSTEM_V1.md` (this doc)
  - New: `247_GLOBAL_AI_OVERVIEW.md` (parent anchor)

---

## Change log

- 2026-05-18 (SESSION 178) — Initial scope lock. Triggered
  by operator's brand-pivot framing at SESSION 177 close:
  "Transform the current CharacterOS project into the first
  product ecosystem under the parent company brand 24/7
  GLOBAL AI." Locked 10 contract rules; 6-product family
  reserved (`*OS` naming convention); token architecture
  with parent / product / primitive separation; incremental
  rollout sequenced B0-B10; six verification tests named.
  Repo + Django project names deliberately NOT renamed
  (contract rule 10). BRAND_IDENTITY_V1 superseded by V2
  with deprecation banner preserving the audience-pivot
  history. B0 closes with this doc + V2 doc + parent-anchor
  doc + V1 banner update. B1 starts the token
  infrastructure work invisibly.

- 2026-05-18 (SESSION 178) — **B0-B5 shipped end-to-end in
  a single session; B6-B10 deferred to product #2 reality.**
  The B-arc is effectively complete at B5 for v1. Eight
  commits across the arc:

  * **B0** (`4f567e1`) — Scope lock (this doc) +
    BRAND_IDENTITY_V2.md + 247_GLOBAL_AI_OVERVIEW.md parent
    anchor + V1 deprecation banner. Architectural
    foundation; 10 contract rules; 6-product `*OS` family
    reserved.

  * **B1** (`3902814`) — Token infrastructure shipped
    invisibly. `web/src/lib/brand/{tokens.ts,parent.ts,
    products/character-os.ts,index.ts}` + `web/src/styles/
    tokens.css` (scoped to `[data-brand="v2"]` which nothing
    activated yet). All 8 acceptance criteria from
    BRAND_IDENTITY_V2 §B1 green; no visual change.

  * **B2** (`30e2d3f`) — SPA flipped to V2. `<html
    data-brand="v2">` set, V1 :root rescoped to
    `[data-brand="v1"]` for rollback, Fraunces dropped from
    fonts + globals, paper-warm body background removed,
    `font-display` + `font-serif` consolidated to Geist,
    `::selection` to gold accent. Layout chrome rewired
    through `BRAND.product.name` + new `ParentBrandChip` top
    -right + `BRAND.parent.poweredByLabel` footer.

  * **B2 hotfix** (`b2b6475`) — PostCSS `@import` order
    bug. The `@import "./tokens.css";` was placed after
    `@tailwind` directives → silently dropped → V2 tokens
    not in the bundle → operator saw white background with
    gold accents. 1-line move + 6-line comment block;
    TRUST_CALIBRATION entry added.

  * **B3.1** (`a2659c4`) — talk-route + status colors to
    V2 tokens. Side effect: tailwind.config gains `success`
    + `warning` color utilities + `accent.muted` + `accent
    .bright` variants. 5 distinct components migrated
    (headphones tip, AvatarCall wrapper, LiveIndicator
    pill, ToolResultPanel 4-state palette, recall results
    cards).

  * **B3.2** (`c850cfa`) — rest of SPA hardcoded V1
    colors migrated in one sweep. 11 files touched. After
    this commit `grep -rE 'bg-(amber|emerald|yellow|blue|
    ...)-[0-9]'` returns zero hits in SPA source.
    Replacement convention: `border-X-500/40 bg-X-500/5
    text-X-700 dark:text-X-300` →  `border-<token>/40
    bg-<token>/10 text-<token>` per intent. Zero semantic
    drift.

  * **B4** (`0f97adb`) — messaging refresh to
    infrastructure-credible tone. Dashboard hero, empty
    states, recipe gallery header, spokesperson detail
    CTA, onboarding tour all rewritten. Verbs are
    infrastructure verbs (provision / compose / ground /
    fire); no exclamation marks; no "transform your
    business" copy. Sample: "Type your business. Click.
    Get a video ad." → "Compose a render. Ground in
    workspace knowledge. Ship to your channels." "Make a
    video" → "New render" or "Open recipe gallery."
    "Create your first spokesperson" → "Provision
    spokesperson." Onboarding step 3 "Pick a recipe and
    render" → "Fire a composition."

  * **B5** (`fbf8909`) — dedicated `/about` parent-company
    route + brand chip clickable. Hero (tagline + parent
    name + positioning) + Product family table
    (CharacterOS Live + 5 reserved siblings with status
    pills) + Contact card + /signature footer link. Public
    route (no auth gate) so external evaluators can land
    directly. `productFamily` array added to `parent.ts`
    mirroring `docs/247_GLOBAL_AI_OVERVIEW.md` §"Product
    family"; `ProductFamilyEntry` type exported.

  * **B6-B10 deferred.** Operator-caught
    premature-extraction at the B5/B6 boundary: B6's "stub
    product config files for DealerOS / AgentOS / etc."
    contradicted contract rule 10 + §"Out of scope" item
    "Monorepo split. Reserved for product #2 reality."
    B7 (enterprise polish), B8 (operator dogfood +
    screenshot review), B9 (V1 archive cleanup), and B10
    (formal arc closure) all carry forward as latent
    items that activate when their preconditions are met
    (product #2 reality / dogfood-driven polish / doc
    maintenance). The B-arc is closed for v1.

  **Three TRUST_CALIBRATION entries appended** (PostCSS
  `@import` order; operator-caught premature extraction;
  V2-not-applying-was-cache).

  **Test totals:** Django 816 unchanged; SPA vitest 95
  unchanged; media-engine 133 unchanged. Per contract rule
  6 zero business-logic / model / route / API touched.

  **Real-mode spend:** $0 — pure SPA + docs work.

  **B-arc state:** B0-B5 SHIPPED; B6-B10 DEFERRED. The
  CharacterOS SPA now reads as enterprise AI infrastructure
  under the 24/7 GLOBAL AI parent company. Every public
  surface names 24/7 GLOBAL AI as the company (contract
  rule 1); every component string flows through
  `BRAND.parent` / `BRAND.product` (contract rule 3);
  tokens are the shared substrate (contract rule 2). Brand
  layer is extraction-ready when product #2 launches.
