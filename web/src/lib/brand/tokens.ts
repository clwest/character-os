/**
 * Design tokens — single source of truth for the 24/7 GLOBAL AI
 * brand ecosystem. Mirrors `web/src/styles/tokens.css` (the CSS
 * vars) so TS consumers can introspect token values without
 * reading CSS at runtime.
 *
 * Locked SESSION 178 against `docs/design/BRAND_IDENTITY_V2.md`.
 * Premium enterprise AI infrastructure aesthetic: deep navy +
 * gold, refined sans, generous spacing, sophisticated multi-layer
 * shadows, linear motion.
 *
 * **B1 (this slice) ships the tokens invisibly** — `tokens.css`
 * scopes the V2 CSS vars under `[data-brand="v2"]`, which nothing
 * activates yet. The existing v1 `:root` declarations in
 * `globals.css` continue to drive Tailwind. B2 will set
 * `data-brand="v2"` on `<html>` + remove the v1 `:root` block to
 * flip the SPA to V2.
 *
 * Multi-product extraction note: this module contains zero
 * product-specific strings. Per-product identity (CharacterOS
 * name, subtitle, optional accent override) lives in
 * `web/src/lib/brand/products/*.ts`. When product #2 launches
 * this module extracts cleanly to a publishable `@247globalai/brand`
 * npm package.
 */

// ---- Color --------------------------------------------------------
//
// HSL strings (without the `hsl()` wrapper) for shadcn / Tailwind
// `hsl(var(--token))` consumption. Hex shown in comments for
// designer reference. See BRAND_IDENTITY_V2.md §Color for rationale.

export const colors = {
  // Primary palette
  background: "222 18% 7%",       // #0F1116 — page bg (matches signature card)
  foreground: "0 0% 92%",         // #EAEAEA — default text
  card: "222 18% 10%",            // #15181E — card surface
  cardForeground: "0 0% 92%",     // #EAEAEA
  popover: "222 18% 12%",         // #1A1D24 — floating surface
  popoverForeground: "0 0% 92%",  // #EAEAEA
  muted: "222 14% 16%",           // #23262E — input bg, hover states
  mutedForeground: "222 9% 64%",  // #A0A7B4 — secondary text
  border: "222 12% 20%",          // #2A2E37 — hairlines
  input: "222 14% 16%",           // #23262E — input bg
  ring: "38 47% 58%",             // #C8A35F — focus ring (= accent)

  // Accent palette (the gold — used sparingly)
  accent: "38 47% 58%",           // #C8A35F — primary accent
  accentForeground: "222 18% 7%", // #0F1116 — dark text on gold
  accentMuted: "38 35% 45%",      // #9E824D — hover / disabled
  accentBright: "38 60% 70%",     // #DFC18A — decorative bright variant

  // Status palette (muted on dark — coexist with gold without competing)
  success: "142 50% 45%",         // #3CB371
  successForeground: "0 0% 92%",  // #EAEAEA
  warning: "38 80% 60%",          // #E5A647 — distinct from accent gold
  warningForeground: "222 18% 7%",
  destructive: "0 65% 55%",       // #D14F4F
  destructiveForeground: "0 0% 92%",

  // Compat aliases for shadcn `primary` / `secondary` naming.
  // In V2 the conceptual "primary" action is the gold accent; we
  // alias so existing shadcn-generated components keep rendering.
  primary: "38 47% 58%",           // = accent
  primaryForeground: "222 18% 7%", // = accentForeground
  secondary: "222 14% 16%",        // = muted (subtler secondary)
  secondaryForeground: "0 0% 92%", // = mutedForeground-ish (but readable)
} as const;

// ---- Typography ---------------------------------------------------

export const typography = {
  // V2 consolidates to a single sans family (Geist variable) for
  // display + body. JetBrains Mono unchanged from V1 for code /
  // ids. Fraunces (V1 editorial serif) retired.
  fontFamily: {
    sans: ['"Geist"', "ui-sans-serif", "system-ui", "sans-serif"],
    mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
    // Display alias points to the same sans — V2 uses Geist's
    // variable axes (weight + tracking) for hierarchy instead of
    // a separate serif.
    display: ['"Geist"', "ui-sans-serif", "system-ui", "sans-serif"],
  },
  // Sizing scale (px). Tighter than V1 — base 14 instead of 15 —
  // for the enterprise aesthetic.
  fontSize: {
    xs: ["11px", { lineHeight: "1.4" }],
    sm: ["13px", { lineHeight: "1.5" }],
    base: ["14px", { lineHeight: "1.55" }],
    lg: ["16px", { lineHeight: "1.5" }],
    xl: ["19px", { lineHeight: "1.4" }],
    "2xl": ["24px", { lineHeight: "1.3" }],
    "3xl": ["30px", { lineHeight: "1.25" }],
    "4xl": ["38px", { lineHeight: "1.2" }],
    "5xl": ["48px", { lineHeight: "1.15" }],
    "6xl": ["60px", { lineHeight: "1.1" }],
  },
  fontWeight: {
    normal: 400,
    medium: 500,
    semibold: 600,
    bold: 700,
  },
  letterSpacing: {
    tightest: "-0.04em",
    tighter: "-0.03em",
    tight: "-0.02em",
    normal: "0",
  },
} as const;

// ---- Spacing ------------------------------------------------------
//
// 8px base unit. Tailwind-aligned. Generous compared to V1 to
// signal premium care.

export const spacing = {
  px: "1px",
  0: "0px",
  1: "4px",
  2: "8px",
  3: "12px",
  4: "16px",
  6: "24px",
  8: "32px",
  12: "48px",
  16: "64px",
  24: "96px",
} as const;

// ---- Radius -------------------------------------------------------

export const radius = {
  sm: "4px",
  DEFAULT: "8px",
  lg: "12px",
  xl: "16px",
  full: "9999px",
} as const;

// ---- Shadow -------------------------------------------------------
//
// Multi-layer shadows calibrated for dark backgrounds (soft
// ambient + tighter direct). Avoid the blurry white-glow common
// in dark-mode SaaS.

export const shadow = {
  xs: "0 1px 2px 0 rgb(0 0 0 / 0.4)",
  sm: "0 2px 4px -1px rgb(0 0 0 / 0.4), 0 1px 2px -1px rgb(0 0 0 / 0.3)",
  DEFAULT:
    "0 4px 8px -2px rgb(0 0 0 / 0.5), 0 2px 4px -2px rgb(0 0 0 / 0.4)",
  md: "0 8px 16px -4px rgb(0 0 0 / 0.6), 0 4px 8px -4px rgb(0 0 0 / 0.4)",
  lg: "0 16px 32px -8px rgb(0 0 0 / 0.6), 0 8px 16px -8px rgb(0 0 0 / 0.5)",
  xl: "0 24px 48px -12px rgb(0 0 0 / 0.7), 0 12px 24px -12px rgb(0 0 0 / 0.5)",
  gold:
    "0 0 0 1px rgb(200 163 95 / 0.3), 0 4px 12px -2px rgb(200 163 95 / 0.2)",
} as const;

// ---- Motion -------------------------------------------------------
//
// Subtle, infrastructure-credible. No bouncy springs, no overshoot.

export const motion = {
  duration: {
    fast: "120ms",
    DEFAULT: "180ms",
    slow: "240ms",
    emphasis: "400ms",
  },
  ease: {
    out: "cubic-bezier(0.16, 1, 0.3, 1)",
    inOut: "cubic-bezier(0.65, 0, 0.35, 1)",
  },
} as const;

// ---- Aggregated tokens export ------------------------------------

export const tokens = {
  colors,
  typography,
  spacing,
  radius,
  shadow,
  motion,
} as const;

export type Tokens = typeof tokens;

// =====================================================================
// V3 (SESSION 209) — Editorial dark-luxe / 24/7 Global AI parent
// alignment. Active by default in the SPA (`<html data-brand="v3">`).
// Canonical CSS custom property block lives in
// `web/src/styles/tokens.css` under `[data-brand="v3"]`.
//
// V3 supersedes V2 ("Premium enterprise dark + gold"). Both V2 and V3
// objects are exported so consumers can reference either via
// data-brand attribute swap without code changes.
// =====================================================================

/**
 * V3 raw brand colors (hex). Map to `--color-*` CSS vars under
 * `[data-brand="v3"]`. Consumed by Tailwind `text-gold` / `bg-ink`
 * via the tailwind.config color mapping.
 */
export const v3Colors = {
  // Neutrals
  ink: "#050a14",
  night: "#0a1426",
  midnight: "#0d1a30",
  deep: "#142544",
  steel: "#1f3a64",
  fog: "#6b7d99",
  mist: "#b8c4d6",
  bone: "#ece4cf",
  cream: "#f6ecd3",

  // Gold scale
  gold: "#c9a961",
  goldBright: "#e8c87a",
  goldDeep: "#8a6f33",
  ember: "#d4af37",
} as const;

/**
 * V3 typography stack. Bodoni Moda (display, italic-load-bearing),
 * DM Sans (body), JetBrains Mono (microtype).
 */
export const v3Typography = {
  fontFamily: {
    display: ['"Bodoni Moda"', '"Didot"', "Georgia", "serif"],
    sans: ['"DM Sans"', "ui-sans-serif", "system-ui", "sans-serif"],
    mono: ['"JetBrains Mono"', "ui-monospace", "monospace"],
  },
  // Tracking — load-bearing for the editorial register.
  letterSpacing: {
    microtype: "0.22em",   // small labels
    section: "0.34em",     // "§ NN — Section Name" pattern
    tightest: "-0.04em",
    tighter: "-0.03em",
    tight: "-0.02em",
    normal: "0",
  },
} as const;

/**
 * V3 motion. Six keyframes ported from the parent site
 * (`rise`, `orbit`, `shimmer`, `ticker`, `flip`, `pulse-soft`).
 * Easings include `editorial` for the signature 1.2s rise.
 */
export const v3Motion = {
  duration: {
    fast: "120ms",
    DEFAULT: "180ms",
    slow: "240ms",
    emphasis: "400ms",
    editorial: "1200ms",   // hero rise
    orbit: "24000ms",      // hero portrait orbit
    ticker: "60000ms",     // world-clock scroll
  },
  ease: {
    out: "cubic-bezier(0.16, 1, 0.3, 1)",
    inOut: "cubic-bezier(0.65, 0, 0.35, 1)",
    editorial: "cubic-bezier(0.2, 0.65, 0.2, 1)",
  },
} as const;

/**
 * V3 shadow scale — adds `luxe` (gold-tinted inset + ambient glow +
 * deep direct) for hero cards, CTA blocks, and elevated surfaces.
 */
export const v3Shadow = {
  ...shadow,
  luxe:
    "inset 0 1px 0 rgba(201, 169, 97, 0.18), " +
    "0 0 60px rgba(201, 169, 97, 0.08), " +
    "0 30px 80px -30px rgba(0, 0, 0, 0.7)",
} as const;

export const v3 = {
  colors: v3Colors,
  typography: v3Typography,
  motion: v3Motion,
  shadow: v3Shadow,
} as const;

export type V3Tokens = typeof v3;
