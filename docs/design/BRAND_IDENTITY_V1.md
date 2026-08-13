---
title: "Brand Identity v1 — Editorial-warm (DEPRECATED — superseded by V2)"
status: deprecated (V1 lock; superseded SESSION 178)
generated: 2026-05-13 (SESSION 117)
deprecated: 2026-05-18 (SESSION 178)
superseded_by: BRAND_IDENTITY_V2.md
companion_doc: UI_REDESIGN_V2.md
---

# Brand Identity v1 — DEPRECATED

> **DEPRECATED — superseded by `BRAND_IDENTITY_V2.md`
> (SESSION 178).** This document captured the v1
> editorial-warm light-mode brand locked SESSION 117 for SMB /
> solo-creator audience ("not call themselves marketers").
> SESSION 178 operator pivoted to a premium enterprise
> dark-mode brand under the **24/7 GLOBAL AI** parent company,
> repositioning CharacterOS as the first product in a
> multi-product family (DealerOS, AgentOS, OpsOS, VoiceOS,
> SupportOS reserved).
>
> V1 is preserved here as history. **For all visual / brand
> decisions from SESSION 178 forward, see
> `BRAND_IDENTITY_V2.md` and the parent scope lock
> `BRAND_ECOSYSTEM_V1.md`.** The pivot was deliberate, not
> drift — different audience, different aesthetic, different
> product hierarchy.

---

# Brand Identity v1 (original content)

> **Read first:** `UI_REDESIGN_V2.md` §10 deferred this to a later
> doc; SESSION 117 (workspace dashboard) forced the question. This is
> the v1 lock — minimal enough to revisit when real users land,
> opinionated enough to make every Phase 3 slice coherent.

---

## TL;DR

**Editorial-warm.** Paper-toned background, deep ink type, distinctive
variable-serif display headings, refined sans body. One warm
high-contrast accent (oxblood) for primary actions. Light-mode only
for v1.

The audience is solo creators + SMB owners who do **not** call
themselves marketers (`UI_REDESIGN_V2.md` §1.1). The aesthetic
should signal *"this is for people who run a business, not a
hobby"* — refined, calm, confident — without resorting to enterprise
blue or trendy-startup purple. We're closer to a print magazine
than a SaaS dashboard.

---

## Typography

| Role    | Family            | Why |
|---------|-------------------|-----|
| Display | **Fraunces**      | Variable serif with optical sizing. Real character at large sizes — feels printed, not generated. Free from Google Fonts. |
| Body    | **Geist Sans**    | Vercel's sans. Crisp, neutral, modern without being trendy. Pairs cleanly with a serif. Free from Google Fonts. |
| Mono    | **JetBrains Mono**| For IDs, hashes, code snippets in the admin / error surfaces. Free. |

Display sizing: trust Fraunces's optical-sizing. H1 ~48-56px, H2
~32-36px. Always with refined letter-spacing (`tracking-tight`).

Body sizing: 15px default. Long-form copy at 17px. Line-height 1.5
for body, 1.2 for display.

**Explicit non-choices:** no Inter, no Roboto, no system-stack
default, no Space Grotesk, no DM Sans. These are the trendy defaults
that make AI-generated work look AI-generated.

---

## Color

Light-mode only for v1. HSL values for shadcn token consistency.

| Token                  | HSL                  | Hex (approx) | Usage |
|------------------------|----------------------|--------------|-------|
| `--background`         | `36 33% 94%`         | `#f5efe5`    | Warm paper. Default page bg. |
| `--foreground`         | `30 12% 12%`         | `#231e1a`    | Deep ink. Default text. |
| `--muted`              | `36 18% 88%`         | `#e8e1d4`    | Cards on the page (subtle one-step lift). |
| `--muted-foreground`   | `30 10% 38%`         | `#6a625b`    | Secondary copy, captions, kicker text. |
| `--card`               | `40 40% 97%`         | `#faf6ec`    | Card surface (lifts above page). |
| `--card-foreground`    | `30 12% 12%`         | `#231e1a`    | Same as foreground. |
| `--border`             | `33 18% 80%`         | `#d6cdbd`    | Hairline rules. |
| `--input`              | `33 18% 80%`         | `#d6cdbd`    | Same as border. |
| `--ring`               | `8 60% 32%`          | `#84231e`    | Focus rings. Same family as accent. |
| `--primary`            | `8 60% 32%`          | `#84231e`    | **Oxblood.** Primary CTAs only. |
| `--primary-foreground` | `40 40% 97%`         | `#faf6ec`    | Paper-cream on oxblood. |
| `--secondary`          | `36 18% 88%`         | `#e8e1d4`    | Secondary buttons. |
| `--secondary-foreground`| `30 12% 12%`         | `#231e1a`    | |
| `--destructive`        | `4 60% 38%`          | `#9b3329`    | Just a darker oxblood. Errors. |
| `--destructive-foreground`| `40 40% 97%`      | `#faf6ec`    | |
| `--accent`             | `36 18% 88%`         | `#e8e1d4`    | Hover surfaces. Same as muted. |

The accent (oxblood) appears only on primary CTAs + focus rings.
Everything else lives in the paper/ink/muted family. This contrast
ratio is the *thing someone will remember*: a mostly quiet, paper-
textured surface with occasional decisive reds.

**Borders:** 1px hairline (`--border`). No rounded corners > 6px.
Cards: `rounded-md` (4px). Buttons: `rounded-md`. Inputs: `rounded-md`.
Refined, not friendly-blob.

---

## Motion

Restrained.

- **Page load:** Stagger reveal of dashboard cards. ~80ms between
  items, 240ms fade+rise per item. CSS animation, not JS.
- **Hover:** Subtle scale (1.005) + shadow lift on cards. ~150ms
  ease-out.
- **Button:** Background-color transition only, 120ms.
- **Loading:** Skeletons matching the final layout. No spinners.
  No "wave" gradient — flat `--muted` blocks.
- **Errors:** Slide-in from above by 4px + fade-in, 200ms. Stays
  put after that.

What we don't do: bouncy springs, parallax, scroll-triggered text
reveals, particle effects, gradient animations. All of those add
cognitive load to an operator who wants to render a video, not
admire the chrome.

---

## Spatial composition

- **Container max-width:** 72rem (1152px). Most screens narrower.
- **Vertical rhythm:** 8px base. Sections separated by 48-64px.
- **Grids:** Spokespeople tiles use a 1/2/3 column responsive
  grid. Other lists are vertical, never horizontal-scroll.
- **Asymmetry:** Headers are flush-left, content is centered-
  contained. Page feels grounded, not floating.

---

## Out of scope (revisit when needed)

- **Dark mode.** Defer. The audience overwhelmingly works in
  daylight (TikTok, Instagram, business). Dark mode is a power-
  user feature, not a launch feature.
- **Brand logomark + wordmark.** Defer. The header just renders
  the workspace name in Fraunces for now.
- **Illustration / image style.** Defer. The dashboard uses
  initials-in-serif as portrait placeholders until real Spokesperson
  portraits land.
- **Marketing site palette.** Different surface; the design lock
  treats the marketing site as a separate Phase 3 deliverable.
- **Color tokens for video kinds, status pills.** Defer until S-11
  (video detail) actually renders them.

---

## How to override

Brand identity decisions are notoriously taste-driven. If the
operator disagrees with the v1 direction, the lock is a single
file change:

1. Edit `web/src/styles/globals.css` — change the HSL tokens.
2. Edit `web/index.html` — swap the Google Fonts link.
3. Edit `web/tailwind.config.ts` — swap the `fontFamily.*` values.
4. Update this doc with the new direction.

That's it. The components reference tokens, not hex codes. The
v1 lock is opinionated, not load-bearing — easy to amend, easy
to roll back.

---

## Change log

- 2026-05-13 (SESSION 117) — Initial v1 lock. Editorial-warm.
  Fraunces + Geist Sans + JetBrains Mono. Paper/ink/oxblood
  palette.
