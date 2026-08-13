---
title: "Brand Identity v2 — Premium enterprise dark + gold"
status: superseded by BRAND_IDENTITY_V3.md (SESSION 209)
generated: 2026-05-18 (SESSION 178)
companion_doc: BRAND_ECOSYSTEM_V1.md
supersedes: BRAND_IDENTITY_V1.md
superseded_by: BRAND_IDENTITY_V3.md
---

> **SUPERSEDED — SESSION 209.** V3 pivots from "premium
> enterprise dark + gold" to "editorial dark-luxe" with Bodoni
> Moda display, DM Sans body, section-dossier numbering, and
> the 24/7 Global AI parent voice patterns. See
> `BRAND_IDENTITY_V3.md` for the active contract. V2 preserved
> for archaeology and the V2 → V3 pivot rationale.

# Brand Identity v2

> **Read first:** `BRAND_ECOSYSTEM_V1.md` for the parent scope
> lock + brand hierarchy + slice breakdown. This doc holds the
> v2 visual lock: colors, typography, spacing, shadows, motion.
> Supersedes `BRAND_IDENTITY_V1.md` (SESSION 117 editorial-warm
> light-mode lock for SMB audience). V1 preserved with
> deprecation banner; this is the active visual contract for
> every B-slice from B1 forward.

---

## TL;DR

**Premium enterprise AI infrastructure.** Deep navy background,
gold accent, refined sans typography, generous spacing,
sophisticated shadow scale. Cinematic but professional.
"Enterprise AI operations center" reference; not consumer
SaaS dashboard. Dark mode first; light mode deferred to v2.1
if operator dogfood demands it.

The audience pivots from v1's solo creators / SMB owners
("not call themselves marketers") to enterprise buyers +
sophisticated operators evaluating AI infrastructure. The
aesthetic should signal *"this company runs production AI at
scale"* — credible, intelligent, infrastructure-focused —
without resorting to startup-purple or marketing-loud
gradients.

---

## Color

Dark mode first. HSL values for shadcn token consistency. All
tokens land in `web/src/styles/tokens.css` as CSS custom
properties + mirrored in `web/src/lib/brand/tokens.ts` as TS
constants.

### Primary palette

| Token | HSL | Hex (approx) | Usage |
|---|---|---|---|
| `--background` | `222 18% 7%` | `#0F1116` | Page background. Same as the signature card's `#0F1116`. |
| `--foreground` | `0 0% 92%` | `#EAEAEA` | Default text on dark background. Signature card's `#EAEAEA`. |
| `--card` | `222 18% 10%` | `#15181E` | Surface for cards / panels. One step lighter than background. |
| `--card-foreground` | `0 0% 92%` | `#EAEAEA` | Same as foreground for default card text. |
| `--popover` | `222 18% 12%` | `#1A1D24` | Floating surfaces (modals, dropdowns). Two steps lighter than background. |
| `--popover-foreground` | `0 0% 92%` | `#EAEAEA` | Same as foreground. |
| `--muted` | `222 14% 16%` | `#23262E` | Subtle surface for muted UI (input bg, hover states). |
| `--muted-foreground` | `222 9% 64%` | `#A0A7B4` | Secondary text. Signature card's `#A0A7B4`. |
| `--border` | `222 12% 20%` | `#2A2E37` | Default border on dark surfaces. |
| `--input` | `222 14% 16%` | `#23262E` | Input field background. Matches `--muted`. |
| `--ring` | `38 47% 58%` | `#C8A35F` | Focus ring. Matches `--accent`. |

### Accent palette

| Token | HSL | Hex | Usage |
|---|---|---|---|
| `--accent` | `38 47% 58%` | `#C8A35F` | Primary accent. Signature card's gold. Used for primary buttons, focus rings, headings emphasis, brand chip. |
| `--accent-foreground` | `222 18% 7%` | `#0F1116` | Text on accent surfaces (dark text on gold). |
| `--accent-muted` | `38 35% 45%` | `#9E824D` | Muted variant for hover / disabled states. |
| `--accent-bright` | `38 60% 70%` | `#DFC18A` | Bright variant for subtle accents (hairline rules, decorative). |

### Status palette

| Token | HSL | Hex | Usage |
|---|---|---|---|
| `--success` | `142 50% 45%` | `#3CB371` | Success states. Calibrated to be visible on dark navy. |
| `--success-foreground` | `0 0% 92%` | `#EAEAEA` | Text on success surfaces. |
| `--warning` | `38 80% 60%` | `#E5A647` | Warning states. Distinct enough from `--accent` to avoid confusion. |
| `--warning-foreground` | `222 18% 7%` | `#0F1116` | Text on warning surfaces. |
| `--destructive` | `0 65% 55%` | `#D14F4F` | Destructive / error states. |
| `--destructive-foreground` | `0 0% 92%` | `#EAEAEA` | Text on destructive surfaces. |

### Specific palette notes

* **Gold (`#C8A35F`) is the only branded color.** Used sparingly
  — primary CTAs, brand chip, focus ring, key data
  emphasis. NOT used for body text, NOT used for hover-fill
  on every interactive element. Sparingly = signal.
* **No pure black.** Background is `#0F1116`, not `#000000`.
  Pure black is too harsh for the cinematic-but-professional
  aesthetic.
* **No pure white.** Foreground is `#EAEAEA`. Pure white
  fatigues at the typography size we're using.
* **Status colors stay muted.** Success is a desaturated
  green, destructive is a softened red — they need to coexist
  visually with the gold accent without competing for
  attention.

### Light mode (Q-b-3 — open)

V2 ships dark-only in B1. Light mode reserved for v2.1 if
operator dogfood demands it. If shipped: same token names,
same accent (`#C8A35F`), inverted neutrals (paper bg `#F5F5F5`,
ink fg `#1A1A1A`). Color palette designed so the swap is
mechanical.

---

## Typography

### Stack

| Role | Family | Why |
|---|---|---|
| Display | **Geist** (variable) | Vercel's variable sans. Pairs the enterprise-AI infrastructure aesthetic (think Vercel docs, Linear, modern Stripe). Crisp at large sizes; tightening tracking carries the premium feel. Free from Google Fonts. |
| Body | **Geist** (same family) | One typeface family for display + body. Variable weights handle the hierarchy. Reduces font payload + visual noise. |
| Mono | **JetBrains Mono** | Unchanged from v1. For IDs, hashes, code in admin / error surfaces. |

**Explicit non-choices**: no Inter (over-used for AI products),
no Roboto (Google-default feel), no Fraunces (v1 editorial
serif, wrong tone for v2), no system-stack default (loses
brand control), no Space Grotesk (startup-trendy), no DM Sans
(also startup-trendy).

V1 used Fraunces + Geist Sans + JetBrains Mono. V2
consolidates to Geist + JetBrains Mono. Display headings get
weight + tracking via Geist's variable axes, not a separate
serif.

### Sizing scale

Tighter than v1. Enterprise aesthetic uses smaller body type
with more whitespace. Base 14px instead of 15px.

| Step | Size | Line Height | Tracking | Usage |
|---|---|---|---|---|
| `text-xs` | 11px | 1.4 | normal | Meta labels, timestamps |
| `text-sm` | 13px | 1.5 | normal | Secondary text, captions |
| `text-base` | 14px | 1.55 | normal | Body |
| `text-lg` | 16px | 1.5 | normal | Lead paragraphs |
| `text-xl` | 19px | 1.4 | tight | Card titles |
| `text-2xl` | 24px | 1.3 | tight | Section headings |
| `text-3xl` | 30px | 1.25 | tighter | Page headings |
| `text-4xl` | 38px | 1.2 | tighter | Display headings |
| `text-5xl` | 48px | 1.15 | tightest | Hero display |
| `text-6xl` | 60px | 1.1 | tightest | Wordmark / marketing |

Weights: 400 (body), 500 (medium emphasis), 600 (headings),
700 (display).

---

## Spacing

8px base unit. Tailwind-aligned. Generous compared to v1 to
support the premium aesthetic (whitespace = signal of
care).

| Token | Px | Usage |
|---|---|---|
| `space-1` | 4 | Hairline gaps |
| `space-2` | 8 | Tight stack (icon + text) |
| `space-3` | 12 | Default inline gap |
| `space-4` | 16 | Default block gap |
| `space-6` | 24 | Section gap (within card) |
| `space-8` | 32 | Section gap (between cards) |
| `space-12` | 48 | Hero / display padding |
| `space-16` | 64 | Page-level breathing room |
| `space-24` | 96 | Hero / marketing gaps |

---

## Radius

| Token | Px | Usage |
|---|---|---|
| `radius-sm` | 4 | Small chips, badges, inputs |
| `radius` | 8 | Default — buttons, cards |
| `radius-lg` | 12 | Larger cards, modals |
| `radius-xl` | 16 | Hero containers, signature card |
| `radius-full` | 9999 | Pills, avatar circles |

---

## Shadow

Sophisticated shadow scale. v2 uses **multi-layer shadows**
with a soft ambient + a tighter direct component. Calibrated
for dark backgrounds — needs to be subtle (not the blurry
white-glow shadow common in dark-mode SaaS).

| Token | Definition | Usage |
|---|---|---|
| `shadow-xs` | `0 1px 2px 0 rgb(0 0 0 / 0.4)` | Subtle lift (button hover) |
| `shadow-sm` | `0 2px 4px -1px rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.3)` | Card default |
| `shadow` | `0 4px 8px -2px rgb(0 0 0 / 0.5), 0 2px 4px -2px rgb(0 0 0 / 0.4)` | Elevated card / hover |
| `shadow-md` | `0 8px 16px -4px rgb(0 0 0 / 0.6), 0 4px 8px -4px rgb(0 0 0 / 0.4)` | Popover, dropdown |
| `shadow-lg` | `0 16px 32px -8px rgb(0 0 0 / 0.6), 0 8px 16px -8px rgb(0 0 0 / 0.5)` | Modal |
| `shadow-xl` | `0 24px 48px -12px rgb(0 0 0 / 0.7), 0 12px 24px -12px rgb(0 0 0 / 0.5)` | Hero card |
| `shadow-gold` | `0 0 0 1px rgb(200 163 95 / 0.3), 0 4px 12px -2px rgb(200 163 95 / 0.2)` | Brand-accent emphasis (rare) |

---

## Motion

Subtle, infrastructure-credible. No bouncy spring animations.
Linear ramps + ease-out for the rare interactive transitions.

| Token | Duration | Easing | Usage |
|---|---|---|---|
| `duration-fast` | 120ms | `ease-out` | Hover state changes |
| `duration` | 180ms | `ease-out` | Default UI transitions |
| `duration-slow` | 240ms | `ease-out` | Modal enter/exit, route changes |
| `duration-emphasis` | 400ms | `ease-out` | Hero / loading state transitions |

No spring animations. No bounce. No overshoot. Enterprise
infrastructure aesthetic = predictable, calm motion.

---

## Brand chip

The "Powered by 24/7 GLOBAL AI" chip is a recurring brand
surface. Lock its shape so every consumer renders consistently:

* **Inline footer text**: `Powered by 24/7 GLOBAL AI` —
  gold accent on the company name, neutral on the prefix.
  `text-sm` weight 400.
* **Header chip (B2)**: 24×24 gold square + `24/7 GLOBAL AI`
  text. Subtle hover state (`shadow-gold`). Links to `/about`
  once B5 lands.
* **Signature card** (existing, `/signature` route): full
  enterprise card shipped SESSION 176. Reused in B5's
  parent-company route.

---

## Acceptance criteria for B1

The token infrastructure slice ships when:

1. `web/src/lib/brand/tokens.ts` exports all tokens above as
   typed TS constants.
2. `web/src/styles/tokens.css` declares all tokens as CSS
   custom properties — light + dark scoped if light mode
   ships (otherwise dark-only).
3. `web/tailwind.config.{js,ts}` maps Tailwind utilities to
   the CSS vars (`bg-background`, `text-foreground`,
   `bg-accent`, etc).
4. `web/src/lib/brand/parent.ts` exports 24/7 GLOBAL AI
   constants (name, tagline, contact details, signature
   card data).
5. `web/src/lib/brand/products/character-os.ts` exports
   CharacterOS product config (name, subtitle, slug).
6. `web/src/lib/brand/index.ts` exports `BRAND` + a
   `useBrand()` hook that surfaces the active product +
   parent identity to components.
7. **No visual change yet**. Existing editorial-warm colors
   stay as the temporary token values so the SPA renders
   identically. The mechanism is in place; values flip in
   B2.
8. Type-check + build + tests all green.

---

## Change log

- 2026-05-18 (SESSION 178) — Initial v2 lock. Triggered by
  operator's brand-pivot framing at SESSION 177 close. V1
  superseded with deprecation banner. Dark navy + gold
  palette derived from the signature card built SESSION 176.
  Typography consolidated to Geist family + JetBrains Mono
  (Fraunces retired from v1's editorial-warm direction).
  Tighter sizing scale + multi-layer shadow scale + linear
  motion language calibrated for enterprise AI
  infrastructure aesthetic. Six acceptance criteria locked
  for B1 (token infrastructure ships invisibly).
