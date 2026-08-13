/**
 * CharacterOS — product identity. First product in the
 * 24/7 GLOBAL AI family.
 *
 * Per-product config holds the product name, subtitle, slug, and
 * any optional accent override. **It does NOT redefine tokens** —
 * tokens are the shared substrate (per contract rule 2 of
 * BRAND_ECOSYSTEM_V1). A product may pick its own accent from the
 * existing token palette but cannot introduce a new color
 * primitive at the product layer.
 *
 * When future products launch (DealerOS, AgentOS, OpsOS,
 * VoiceOS, SupportOS) each gets a sibling file in this
 * directory — same shape, different content.
 */

import { colors } from "../tokens";

export const characterOsProduct = {
  /** Product display name. */
  name: "CharacterOS",

  /** URL-safe slug. Used for product asset paths. */
  slug: "character-os",

  /** Single-sentence infrastructure subtitle (locked B4).
   *  Names the infrastructure the product provides, not the
   *  marketing benefit it promises. */
  subtitle: "Persistent AI Spokesperson Infrastructure",

  /** One-paragraph description for product detail surfaces. */
  description:
    "Operators create reusable on-camera AI representatives " +
    "that star in recorded videos and real-time conversations " +
    "grounded in workspace knowledge.",

  /** Optional accent override. CharacterOS keeps the parent's
   *  gold accent (`colors.accent`) — no override needed. Future
   *  products may set this to a different token value for
   *  product recognition. */
  accent: colors.accent,
} as const;

export type CharacterOsProduct = typeof characterOsProduct;
