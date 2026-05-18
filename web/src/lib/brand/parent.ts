/**
 * 24/7 GLOBAL AI — parent company identity.
 *
 * Single source of truth for any UI surface that needs to name
 * the parent company (footer "Powered by …" chip, header brand
 * chip, signature card, /about route, email signatures). NEVER
 * inline these strings in component code — always import from
 * here (or from `index.ts`'s `BRAND.parent` aggregate).
 *
 * Locked SESSION 178 against `docs/247_GLOBAL_AI_OVERVIEW.md`
 * (parent narrative) + `docs/design/BRAND_ECOSYSTEM_V1.md`
 * (contract rule 3: no hardcoded company strings in components).
 *
 * Multi-product extraction: this module contains zero
 * product-specific references. When product #2 launches this
 * extracts cleanly into the shared `@247globalai/brand` package.
 */

export const parentBrand = {
  /** Display name — used in every "Powered by" surface, header
   *  chip, footer, signature card, /about page. */
  name: "24/7 GLOBAL AI",

  /** Short slug — usable for URLs, asset paths, package names. */
  slug: "247-global-ai",

  /** Locked tagline. Always rendered in full caps as a single
   *  unit — no variant short forms. */
  tagline: "ALWAYS ON. ALWAYS SMART. ALWAYS GLOBAL.",

  /** One-line description for /about hero + meta tags. */
  description: "Premium enterprise AI infrastructure.",

  /** Long-form positioning for /about body copy. */
  positioning:
    "24/7 GLOBAL AI builds production-grade AI infrastructure " +
    "products under a unified *OS family — each *OS is a focused " +
    "vertical with shared design, shared identity, and shared " +
    "operational principles.",

  /** Footer attribution rendered everywhere. The product surface
   *  prepends "Powered by " — keep this prop the company name only
   *  so consumers compose flexibly. */
  poweredByLabel: "Powered by 24/7 GLOBAL AI",

  /** Public web presence. Used in signature card + footer. */
  website: {
    label: "www.247globalai.com",
    url: "https://www.247globalai.com",
  },

  /** Contact channels. Used in signature card + future /about. */
  contact: {
    name: "Chris West",
    title: "Founder & AI Systems Architect",
    email: "chris@247globalai.com",
    phone: "(970) 689-2591",
  },
} as const;

/**
 * Product family roster. Mirrors `docs/247_GLOBAL_AI_OVERVIEW.md`
 * §"Product family". Used by `/about` to render the public-facing
 * product list. Reserved products are listed so external readers
 * can see the family shape — actual product code lives in
 * `web/src/lib/brand/products/*.ts` per the multi-product
 * architecture (extracts to a shared package when product #2
 * launches).
 */
export const productFamily = [
  {
    name: "CharacterOS",
    slug: "character-os",
    subtitle: "Persistent AI Spokesperson Infrastructure",
    status: "live" as const,
  },
  {
    name: "DealerOS",
    slug: "dealer-os",
    subtitle: "Dealer & automotive vertical AI infrastructure",
    status: "reserved" as const,
  },
  {
    name: "AgentOS",
    slug: "agent-os",
    subtitle: "Agent network operations infrastructure",
    status: "reserved" as const,
  },
  {
    name: "OpsOS",
    slug: "ops-os",
    subtitle: "Operations automation infrastructure",
    status: "reserved" as const,
  },
  {
    name: "VoiceOS",
    slug: "voice-os",
    subtitle: "Voice-first AI interface infrastructure",
    status: "reserved" as const,
  },
  {
    name: "SupportOS",
    slug: "support-os",
    subtitle: "Customer support intelligence infrastructure",
    status: "reserved" as const,
  },
] as const;

export type ProductFamilyEntry = (typeof productFamily)[number];

export type ParentBrand = typeof parentBrand;
