/**
 * Brand layer entry point.
 *
 * Components consume the brand layer through this module:
 *
 *   import { BRAND, useBrand } from "@/lib/brand";
 *   …
 *   <span>{BRAND.parent.name}</span>             // 24/7 GLOBAL AI
 *   <span>{BRAND.product.name}</span>            // CharacterOS
 *   <span>{BRAND.parent.poweredByLabel}</span>   // Powered by 24/7 GLOBAL AI
 *   <span>{BRAND.product.subtitle}</span>        // Persistent AI Spokesperson …
 *
 * Per BRAND_ECOSYSTEM_V1 contract rule 3, component code MUST
 * NOT inline these strings. Locked SESSION 178.
 *
 * The exported `BRAND` aggregate snapshots the active product
 * (CharacterOS in v1; future routing can swap). `useBrand()` is
 * the hook variant — identical content, idiomatic-React shape.
 *
 * Multi-product extraction: when product #2 launches this
 * module + `parent.ts` + `tokens.ts` extract to
 * `@247globalai/brand`; per-product configs stay in each
 * product's repo.
 */

import { useMemo } from "react";

import { parentBrand } from "./parent";
import { characterOsProduct } from "./products/character-os";
import { tokens } from "./tokens";

/** Active product. v1 hardcodes CharacterOS; multi-product
 *  routing replaces this in B6+. */
const ACTIVE_PRODUCT = characterOsProduct;

/** Aggregate brand snapshot — the everywhere-import. */
export const BRAND = {
  parent: parentBrand,
  product: ACTIVE_PRODUCT,
  tokens,
} as const;

export type Brand = typeof BRAND;

/** React hook for components that prefer hook shape over const
 *  import. Identical content; memoized to keep referential
 *  equality stable across renders. */
export function useBrand(): Brand {
  return useMemo(() => BRAND, []);
}

// Re-exports so consumers can import sub-pieces directly without
// touching `BRAND.*`. Useful for `signature.tsx`-style surfaces
// that want only `parentBrand.contact`.
export { parentBrand } from "./parent";
export { characterOsProduct } from "./products/character-os";
export { tokens, colors, typography, spacing, radius, shadow, motion }
  from "./tokens";
export type { ParentBrand } from "./parent";
export type { CharacterOsProduct } from "./products/character-os";
export type { Tokens } from "./tokens";
