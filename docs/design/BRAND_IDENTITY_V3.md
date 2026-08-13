---
title: "Brand Identity v3 — Editorial dark-luxe (24/7 Global AI parent alignment)"
status: scope-locked (SESSION 209)
generated: 2026-05-20
companion_docs: ["BRAND_ECOSYSTEM_V1.md", "BRAND_IDENTITY_V2.md", "247_GLOBAL_AI_OVERVIEW.md"]
supersedes: BRAND_IDENTITY_V2.md
source_of_truth: 24/7 Global AI parent marketing site (external)
---

# Brand Identity v3

> **Read first:**
> - `BRAND_ECOSYSTEM_V1.md` — parent scope lock, brand hierarchy
>   (Character OS is Lab VI under 24/7 Global AI per
>   `lib/products.ts`).
> - `BRAND_IDENTITY_V2.md` — the active "premium enterprise dark
>   + gold" lock V3 supersedes.
> - `247_GLOBAL_AI_OVERVIEW.md` — parent positioning anchor.
> - The 24/7 Global AI parent marketing site (external repo,
>   not in this monorepo) is V3's canonical source of truth
>   for visual language. When V3's written tokens disagree
>   with the site's running CSS, the site wins.
> - V2 preserved with deprecation banner; V3 is the active
>   visual contract from this lock forward.

---

## TL;DR

**Editorial dark-luxe. Agentic AI operating partner.** Ink
black backgrounds, sparing gold accent across a 4-stop scale,
Bodoni Moda serif at display sizes, DM Sans for body,
JetBrains Mono for technical microtext. Section-dossier
numbering (`§ 01 — The Charter`), hairline gold dividers,
italic-display headlines with gold-stroke contrast, orbit /
rise / sweep / shimmer motion language. "Plate 01" caption
treatment, "Reply by morning" voice.

V3 inherits V2's *dark-mode-first + gold accent* foundation
but pivots the aesthetic from **"enterprise AI operations
center"** to **"agentic AI operating partner"** — closer to a
private intelligence dossier than to a Vercel docs derivative.
The trigger is parent-company alignment: when an operator
lands on `247globalai.com` and then opens Character OS, the
two should feel like one studio's two surfaces, not two
products from two companies.

**Audience is unchanged** from V2 (sophisticated operators
evaluating AI infrastructure). **What's changing is the
register** — from "infrastructure-credible" toward
"infrastructure-credible *and editorially poised*."

---

## Source of truth

The canonical visual language lives in the 24/7 Global AI
parent marketing site (external repo, not in this monorepo):

- `src/app/globals.css` — color tokens (`@theme inline` block),
  fonts, animation keyframes, utility classes.
- `src/app/page.tsx` — the canonical home page; reference
  implementation of section numbering, hero pattern, pillar
  grid, suite grid, lab grid, doctrine quote, engagement card.
- `src/components/SiteHeader.tsx` / `SiteFooter.tsx` —
  global chrome.
- `src/components/ProductCard.tsx` — card pattern.
- `src/components/WorldClock.tsx` / `RotatingWord.tsx` —
  bespoke motion components.
- `src/lib/products.ts` — voice / copy patterns (taglines,
  elevators, status sub-labels, "Plate 01"-style captions).

**V3 must not invent.** When a token, font, animation, or
copy pattern lands in Character OS, it points back to one of
these sources. New material gets added to the parent site
first, then ported.

---

## Contract rules (load-bearing)

These constrain every V3 slice. Violations are scope-lock
events, not patch decisions.

1. **Dark-mode-first. Light mode deferred.** V3 ships dark-
   only. The parent site is dark-only by design ("private
   operating layer"). A light mode could land in v3.x if
   operator demand surfaces; v3.0 doesn't ship one.

2. **Gold is the only branded color.** Same restraint as V2
   rule. Used for: primary CTAs, brand accent on display
   headlines, hairline dividers, focus rings, key data
   emphasis, orbital decorations. NOT used for body text,
   NOT used for hover-fill on every interactive element.
   Status colors (success / warning / destructive) stay
   in their own desaturated palette — they coexist with gold
   without competing.

3. **Bodoni Moda is the display face.** Italic variants
   carry brand emphasis (per the parent site's
   `<span className="italic gold-text">smart.</span>`
   pattern). Body type is DM Sans. Mono is JetBrains Mono
   for IDs, file paths, technical microtext. No third sans,
   no second serif.

4. **Section numbering is canonical.** Every section that
   maps to one of the parent site's `§ NN` blocks adopts
   the editorial-dossier numbering pattern. Format:
   `§ 01 — The Charter` in `font-mono text-[10.5px]
   uppercase tracking-[0.34em] text-gold` per the parent
   page.tsx.

5. **No pure black, no pure white.** Background is ink
   `#050a14` (not `#000000`). Foreground is cream `#f6ecd3`
   (not `#ffffff`). Carries the editorial-warm-on-cold-base
   character.

6. **Tailwind v3 first; v4 migration is a separate slice.**
   The parent site uses Tailwind 4 `@theme inline` blocks.
   Character OS is on Tailwind 3. V3 ports tokens to v3
   syntax (CSS custom properties + `tailwind.config` extend).
   A future v3.x slice can migrate to v4 if needed; the
   token shapes don't change.

7. **shadcn primitives keep their slots.** Buttons, cards,
   inputs, badges, dialogs all retain their existing API.
   V3 rethemes them via CSS variables + variant overrides,
   never by replacing their component structure. The 30+
   pages that already consume shadcn primitives don't need
   per-page rewrites.

8. **Brand layer is load-bearing.** Every component must
   import company/product strings from `@/lib/brand`. V3
   extends `BRAND` with palette + typography token exports
   so future copy / styling references one source.

9. **Voice patterns ship as helpers, not magic strings.**
   "§ NN — Section Name", "Plate NN", "Reply by morning"
   patterns land as `<SectionHeader number={1}
   title="The Charter" />` / `<EditorialCaption number={1}
   note="..." />` / `<EngagementBrief />` reusable
   components — not as freestyle JSX scattered across
   routes.

10. **24/7 Global AI parent chip stays on every authenticated
    surface.** Already enforced by the `ParentBrandChip` in
    `_layout.tsx`. V3 keeps it; only restyles to the new
    palette.

---

## Color tokens

Mirror of `/24-7-ai-global/src/app/globals.css`'s `@theme
inline` block, ported to CSS custom properties + Tailwind v3
`extend`. All values land in `web/src/styles/tokens.css` and
mirror to `web/src/lib/brand/tokens.ts` as TS constants.

### Neutral scale (dark base, cream foreground)

| Token | Hex | Usage |
|---|---|---|
| `--ink` | `#050a14` | Page background. The base everything sits on. |
| `--night` | `#0a1426` | One step lighter. Section backgrounds. |
| `--midnight` | `#0d1a30` | Card surfaces. |
| `--deep` | `#142544` | Elevated surfaces. |
| `--steel` | `#1f3a64` | Borders, decorative shapes (blurred backdrops). |
| `--fog` | `#6b7d99` | Muted text (microtype, dates, IDs). |
| `--mist` | `#b8c4d6` | Secondary body text. |
| `--bone` | `#ece4cf` | Slightly cooled cream — alt heading color. |
| `--cream` | `#f6ecd3` | Primary foreground. Body text + bright headings. |

### Gold scale

| Token | Hex | Usage |
|---|---|---|
| `--gold` | `#c9a961` | Primary accent. CTAs, hairlines, section labels. |
| `--gold-bright` | `#e8c87a` | Hover / emphasis. Pairs with text-gradient effects. |
| `--gold-deep` | `#8a6f33` | Pressed state, darker borders. |
| `--ember` | `#d4af37` | Hot accent — limited to "Engagement / Reply by morning" type CTAs and the orbiting-dot decorative motif. |

### Semantic shadcn mapping

| shadcn token | V3 value | Note |
|---|---|---|
| `--background` | `var(--ink)` | |
| `--foreground` | `var(--cream)` | |
| `--card` | `var(--midnight)` | |
| `--card-foreground` | `var(--cream)` | |
| `--popover` | `var(--deep)` | |
| `--popover-foreground` | `var(--cream)` | |
| `--muted` | `var(--steel)` | |
| `--muted-foreground` | `var(--mist)` | |
| `--accent` | `var(--gold)` | |
| `--accent-foreground` | `var(--ink)` | |
| `--border` | `color-mix(in srgb, var(--gold) 15%, transparent)` | "luxe" border — gold at 15% opacity. Parent site uses `border-luxe` for this. |
| `--input` | `var(--steel)` | |
| `--ring` | `var(--gold)` | |
| `--destructive` | `#D14F4F` | Carried from V2 (works on ink base). |
| `--success` | `#3CB371` | Carried from V2. |
| `--warning` | `var(--ember)` | Reuses ember — desaturated enough to not compete with gold. |

### Specific palette notes

- **Background gradient is intentional**: `bg-ink` with
  ambient `radial-spot` + `grid-globe` overlays from the
  parent site (lifted in `globals.css`). Not flat.
- **Selection color** is `gold` on `ink` (parent site's
  `::selection { background: var(--color-gold); color:
  var(--color-ink); }`).
- **`text-balance`** utility is the parent's default for
  display headlines. Port it.

---

## Typography

### Stack

| Role | Family | Source | Why |
|---|---|---|---|
| Display | **Bodoni Moda** | Google Fonts | Editorial-luxe serif. The "magazine cover" face. Variable; carries weight + optical-size. Italic variants are load-bearing (gold-stroke italic = brand emphasis). |
| Body | **DM Sans** | Google Fonts | Geometric humanist sans. Pairs Bodoni Moda's editorial weight without competing. The parent site's default body face. |
| Mono | **JetBrains Mono** | Google Fonts | Carried from V2. Tracked-out uppercase microtype (`font-mono text-[10.5px] uppercase tracking-[0.34em]`) is canonical for section labels, "Plate NN" captions, technical IDs. |

**Explicit non-choices**: no Geist (V2's choice — replaced by
DM Sans), no Inter, no Fraunces (V1 — Bodoni is the closer
editorial relative), no system stack default, no Space Grotesk.

### Sizing

Display headlines use the parent site's clamped scale:
`clamp(3rem, 7.4vw, 7.5rem)` for hero, `5xl` / `6xl` (default
Tailwind) for section headers, `3xl` / `4xl` for sub-headers.

Body type stays at 14-17px depending on density (parent
hero body is `text-[17px] leading-relaxed text-mist`).

Microtype is `font-mono text-[10px] uppercase
tracking-[0.22em]` (subtle) through `text-[12px] uppercase
tracking-[0.34em]` (section labels). Tracking is load-bearing
— the editorial register depends on it.

---

## Editorial patterns

### Section numbering

```tsx
<SectionHeader number={1} title="The Charter" />
```

Renders as the parent site's `§ 01 — The Charter` block:
`font-mono text-[10.5px] uppercase tracking-[0.34em]
text-gold` over the section heading. Component lives in
`web/src/components/editorial/SectionHeader.tsx`.

### Hairline dividers

`<span className="h-px w-12 bg-gold/60" />` — the 12px-wide
gold hairline pattern used to flag editorial transitions.
Composes into `<HairlineDivider />`.

### Italic-display contrast

```tsx
<h1>
  Always <span className="italic">on.</span>
  Always <span className="italic gold-text">smart.</span>
  Always <span className="italic gold-stroke">global.</span>
</h1>
```

The italic-runs-with-gold-stroke pattern. Two utility classes
needed:
- `.gold-text` — solid gold fill via `color: var(--gold)`
- `.gold-stroke` — text outline in gold, fill transparent.
  Lift the parent site's exact CSS.

### Plate / caption pattern

```tsx
<EditorialCaption plate="01">
  The proprietor of 24/7 Global AI. Pocket watch by
  appointment; the hour is irrelevant.
</EditorialCaption>
```

Renders as the bottom-right hero caption from parent's
`page.tsx` lines 109-116: hairline above, "Plate 01" in
gold-mono microtype, italic cream-foreground body.

### Engagement brief card

The parent's `§ 06 — Engage` card — `<dl>` of microtype
keys + italic cream values: `Cadence · Format · Discretion ·
Reply`. Ships as `<EngagementBrief />` for any
contact/inquiry surface. Character OS doesn't need this on
every page; reserve for landing, public surfaces, the
spokesperson "Talk" lead-capture if it ever opens publicly.

### Doctrine quote pattern

The parent's `§ 05 — The Position` block — gold-italic
large quote marks flanking a centered editorial line.
`<DoctrineQuote>...</DoctrineQuote>` component.

---

## Motion

Four keyframes ported from the parent site verbatim
(`@keyframes` blocks in `globals.css`):

| Name | Use |
|---|---|
| `rise` | Entry animation for hero / section reveals. `translateY(28px)` → `0`, 1.2s `cubic-bezier(0.2, 0.65, 0.2, 1)`. |
| `orbit` | Decorative orbital dot on hero portrait. 360° rotation, 24-28s linear infinite. |
| `shimmer` | Subtle ambient — opacity pulse on background glyphs. 4s ease-in-out. |
| `ticker` | World-clock / status ticker scroll. 60s linear infinite. |

The parent site also has `flip` (rotating-word) and
`pulse-soft`. Port both. Add to `tailwind.config` under
`extend.keyframes` + `extend.animation`.

---

## Voice patterns

Adopt the parent site's voice register where Character OS
surfaces parallel the parent's editorial moves. Not every
page needs it — internal admin / debug surfaces stay
functional.

| Pattern | Where to apply |
|---|---|
| **"§ NN — Section Name"** | Top-of-section labels on dashboard, knowledge corpus overview, recipes gallery, Videos library. |
| **"Plate NN"** | Editorial-style captions under hero images / spokesperson portraits / featured renders. |
| **"Reply by morning"** | Engagement / contact surfaces. The parent's signature urgency-without-noise tone. |
| **"Pocket watch by appointment; the hour is irrelevant"** style metaphor | Hero copy on public landing surfaces. Don't dilute by overusing. |
| **Italic-as-emphasis** | Display headlines. The italic carries weight; avoid bold-as-emphasis. |
| **Microtype labels** in all caps tracked-out | Field labels, status pills, "Cadence / Format / Discretion / Reply" patterns. |

**Do not**: adopt startup-tech voice ("AI-powered", "next-gen",
"revolutionary"). The parent site's editorial restraint is the
brand. Stay close to it.

---

## Slice plan

V3 ships across multiple slices. **No big-bang re-skin** —
the SPA is too large (30+ routes) for a single PR. Phasing
matches the operator's three-tier estimate from the SESSION
209 conversation.

### V3.0 — Scope lock (this doc)

**½ session.** Doc + contract rules + token map. No code.

### V3.1 — Token swap + fonts

**~1 session.** Visual base. After this, every page looks
broadly on-brand.

- `web/src/styles/tokens.css` updated to V3 palette.
- `web/src/lib/brand/tokens.ts` mirror.
- Bodoni Moda + DM Sans + JetBrains Mono loaded via `next/font`-
  equivalent (Vite font hosting or `<link>` in index.html).
- `tailwind.config` extend with new colors + animations.
- `globals.css` ports `rise` / `orbit` / `shimmer` / `ticker`
  / `flip` / `pulse-soft` keyframes.
- Selection color, body class, background gradient overlays
  ported.
- BRAND_LAYER export adds `BRAND.palette` + `BRAND.fonts`.

**Acceptance**: every page boots, dashboard reads
recognizably 24/7-on-brand. No layout breakage. Subjective
operator dogfood: "feels like the same studio."

### V3.2 — Editorial components

**½-1 session.** Ship the reusable editorial primitives:

- `SectionHeader` (`§ NN — Title`).
- `HairlineDivider`.
- `EditorialCaption` (Plate NN pattern).
- `DoctrineQuote`.
- `EngagementBrief`.
- `.gold-text` and `.gold-stroke` utilities.

No page changes yet — components ship + storybook-style
tests + `web/src/routes/_dev/brand-v3-preview.tsx` page
demonstrates them all.

### V3.3 — Header / Footer / NavRail dark-luxe variants

**½ session.** Top-level chrome:

- `SiteHeader` ported from parent's `SiteHeader.tsx`.
  ParentBrandChip restyles to match the gold-link hover state.
- `SiteFooter` adopts parent's `font-mono uppercase tracked`
  footer band.
- `NavRail` (the 11-item rail from SESSION 209) gets dark
  variant — gold-active-state, fog-default-state. Hairline
  separators.

### V3.4 — Dashboard masthead + activity panels

**½ session.** The most-visited page. Apply:

- `§ 01 — Workspace` section label above masthead.
- Display-Bodoni headline.
- Hairline divider under masthead.
- Activity feed rows adopt `font-mono uppercase
  tracking-[0.22em]` for template_kind + status labels.
- Primary action card adopts dark-luxe Card variant.

### V3.5 — Knowledge / Scripts / Campaigns / Bundles / Assets / Videos / Recipes

**1 session.** Bulk page restyle. Each route gets:

- `SectionHeader` instead of plain `h1`.
- Card variants confirmed dark-luxe.
- Microtype labels for filter chips / status pills.
- Form input dark-luxe verification.

Probably can be subagent-delivered with a tight brief
(per memory: subagent delivery on tight contract briefs is
reliable, 2-for-2).

### V3.6 — Spokesperson detail + recipe forms

**½ session.** Detail surfaces. Portrait component adopts the
parent's orbital-rings + decorative hairlines pattern.
Recipe forms get tighter editorial labels.

### V3.7 — Engagement / sign-in / sign-up

**½ session.** Public surfaces. Adopt the parent's full
editorial register — `EngagementBrief`, `DoctrineQuote`,
hero-clamp display headlines. These surfaces *are* the brand
on first impression.

### V3.8 — Voice copy pass

**½ session.** Page-by-page audit. Replace generic strings:

- Empty-state messages → editorial register.
- Button labels → "Open recipe gallery" stays; "Save" →
  "Save brief" / "Commit". One pass.
- Error messages stay functional (don't editorialize errors).
- Brand strings come from `@/lib/brand` (contract rule 8).

### V3.9 — Real-mode dogfood + close

**½ session.** Render a marketing video on the re-skinned
Character OS, take it through `/recipes` → composition →
detail. Calibration findings as TRUST entries. Closeout
handoff. Optional: V3.x deferral list (Tailwind 4 migration,
light mode, animation parity polish).

**Total: 4-5 sessions** depending on density. V3.1 alone is
the meaningful first win — pause-and-evaluate is fine after
that slice.

---

## Open questions

- **Q-v3-1.** Bodoni Moda has multiple optical sizes (6, 96).
  Default `opsz` for body? `opsz=14` (compromise)? `opsz=96`
  for display only? Parent site uses `"opsz" 96, "SOFT" 30,
  "WONK" 1` on hero — port directly?
- **Q-v3-2.** Does `light-mode` deferral hold across all V3
  slices, or do specific routes (e.g. /sign-in for first-time
  visitor accessibility) warrant a light surface? Hold for
  now; revisit in V3.7.
- **Q-v3-3.** `.gold-stroke` is text-outline (`-webkit-text-stroke`).
  Cross-browser? Firefox + Safari + Chrome all support
  modern `-webkit-text-stroke` per MDN, but verify on first
  V3.2 build.
- **Q-v3-4.** Does the F-arc nav-rail expansion (11 items)
  fit in the parent's nav style? The parent has a 4-item
  primary nav (Suite / Lab / Operations / Engage). Character
  OS's 11-item workspace rail is a different surface
  (authenticated post-login). Treat them as distinct surfaces
  in V3.3; the parent-style 4-item nav lives only on public
  surfaces (sign-in, marketing landing if Character OS ever
  has one).
- **Q-v3-5.** Animation parity vs perf. Parent site has 6
  keyframes always running. On the dashboard with many
  components, do they compound to jank? Port + measure during
  V3.1 dogfood; pull back if FPS drops.

---

## Out of scope (v3.x deferrals)

- **Light mode.** Q-v3-2 holds it for v3.x.
- **Tailwind 4 migration.** Contract rule 6 holds; v3.0
  ports tokens to v3 syntax.
- **`next/font` migration.** Character OS is Vite, not Next.
  Use a Vite-compatible font hosting pattern (Fontsource or
  CSS `@import`). Migration to Next would be a project-level
  decision, not a brand slice.
- **Public marketing surface.** Character OS doesn't have
  one today (the parent site is the public surface). If one
  ever lands, it inherits all V3 editorial patterns by
  default.
- **Per-recipe brand-overrides.** Operator workspaces are
  workspace-themed (multi-tenant future). V3 doesn't address
  per-workspace branding; that's a separate arc.

---

## Change log

- **2026-05-20 (SESSION 209)** — V3 scope locked. Trigger:
  parent-company marketing site (external) discovered
  mid-session; Character OS needs to feel like the same
  studio as the parent. V2's "premium enterprise dark + gold"
  foundation kept; aesthetic pivoted from "infrastructure
  operations center" to "editorial agentic operating partner."
  Bodoni Moda + DM Sans replace V2's Geist. Section-dossier
  numbering, hairline gold dividers, "Plate NN" captions,
  "Reply by morning" voice added as load-bearing patterns.
  10-slice plan (V3.0 — V3.9) queued. V2 preserved with
  deprecation banner; status pivots to "superseded".

- **2026-05-20 (SESSION 209) — V3.1 SHIPPED** (`801add2`).
  Token swap + fonts. `tokens.css` new `[data-brand="v3"]`
  block, `globals.css` keyframes + utility classes,
  `tailwind.config.ts` raw color tokens + animation
  utilities, `index.html` flipped to `data-brand="v3"` +
  Bodoni Moda + DM Sans + JetBrains Mono Google Fonts link,
  `tokens.ts` v3 exports. Validation: 434/434 tests, build
  clean. Rollback escape hatch: flip `data-brand` to "v2"
  or "v1".

- **2026-05-20 (SESSION 209) — V3.2 SHIPPED** (`ff2e9ad`).
  Editorial component primitives. Five components in
  `web/src/components/editorial/`: `SectionHeader`,
  `HairlineDivider`, `EditorialCaption`, `DoctrineQuote`,
  `EngagementBrief`. Preview page at `/dev/brand-v3`. 21
  new tests; 455/455 total.

- **2026-05-20 (SESSION 209) — V3.3 SHIPPED** (`d3e5775`).
  Site chrome dark-luxe variants. SiteHeader brand mark
  split (italic-gold "OS"), hairline-gold under header,
  ParentBrandChip italic-gold treatment, SiteFooter
  microtype + italic-gold poweredBy, NavRail gold-active /
  fog-inactive.

- **2026-05-20 (SESSION 209) — V3.4 SHIPPED** (`89c402d`).
  Dashboard masthead + activity. `§ 01 — Workspace`
  pattern, hairline divider, PrimaryAction card with
  luxe-shadow + border-luxe + italic-gold "Ship."

- **2026-05-20 (SESSION 209) — V3.5 SHIPPED** (`ffc40a1`,
  subagent-delivered). 18 workspace route files (Recipes,
  Knowledge, Videos, Assets, Transcripts, Scripts,
  Campaigns, Bundles + their detail / new sub-routes)
  re-skinned to V3 editorial register. Section-dossier
  numbering, italic-gold display headlines, hairline-gold
  separators, V3 class swaps throughout. 3 test fixtures
  adjusted for italic-span text splits. Calibration:
  subagent delivery on tight contract briefs now 3-for-3.

- **2026-05-20 (SESSION 209) — V3.6 SHIPPED** (`3692850`).
  Spokesperson detail + recipe form. **Orbital portrait
  treatment** ported from parent site hero (three
  concentric gold rings + outer + inner orbiting dots +
  circular crop with luxe-shadow). Masthead section
  header + hairline. Class swaps across spokespeople/$id,
  spokespeople/new, spokespeople/talk, recipes/$kind.

- **2026-05-20 (SESSION 209) — V3.7 SHIPPED** (`da93d23`).
  Public surfaces. sign-in italic-gold "in.", sign-up
  "Commission your **operating partner.**" with first
  EngagementBrief outside the preview, about.tsx full
  restructure with first DoctrineQuote outside the
  preview + four-section dossier numbering + product
  family editorial table + contact split with
  EngagementBrief sidebar.

- **2026-05-20 (SESSION 209) — V3.8 SHIPPED** (`087fa4b`).
  Voice copy pass. Dashboard + Videos empty states gain
  italic-display register and editorial-imperative
  language. "Commission a spokesperson →" replaces
  "Provision spokesperson" (parent-site verb match).
  All primary CTAs gain the editorial " →" arrow glyph.

- **2026-05-20 (SESSION 209) — V3.9 SHIPPED.** Real-mode
  V3 dogfood. Brand-on talking_head_polished fired
  through the re-skinned SPA. Validates that the V3
  token + font + utility changes don't regress the
  composition pipeline. V-arc closed. Per slice plan,
  V3 arc complete — 4-5 session estimate landed in
  a single SESSION 209 push (~3 hours of focused work)
  thanks to the V3.5 subagent acceleration + tight
  scope-lock + parent-site canonical source.

  **Total: 10 commits across V3.0 — V3.9** (incl. one
  subagent-delivered slice). Validation: 455/455 vitest
  green across every slice. Build clean. CSS bundle
  growth: 36 KB (V2) → 40.6 KB (V3.8) — a 4.6 KB
  premium for the entire editorial register.

  Deferred to V3.x (not blocking close):
  - Light mode (Q-v3-2).
  - Tailwind 4 migration (Q-v3-6).
  - `next/font` migration (out-of-scope — Vite, not Next).
  - Animation perf measurement on dashboard
    (open question Q-v3-5 — port-and-measure noted
    but no FPS issues observed during dogfood).
  - Per-recipe brand-overrides (multi-tenant, separate
    arc).
