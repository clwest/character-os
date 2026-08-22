/**
 * SESSION 277 Slice 12 (Q-277-12) — Contextual character-origin
 * Knowledge handoff contract. Slice 13 (Q-277-13-C) — extended
 * with a World-detail origin.
 *
 * Three operator surfaces route the operator to
 * `/workspace/knowledge` with preserved context so the destination
 * can render the right audience-picker (or none, when the origin
 * implies the audience).
 *
 * Pre-Slice-12 the routes were bare strings that lost every scrap
 * of context — Slice 6 §120 handoff gap. Slice 12 landed a
 * lossless handoff for character origins. Slice 13 adds the
 * World-detail origin: when the operator explicitly clicks
 * "Add shared knowledge" from a World detail page, both the World
 * AND the audience (UNIVERSE) are already known — the origin IS
 * the audience intent. No further operator decision is required.
 *
 * Contract:
 * - `universe` (UUID). REQUIRED for `world_detail_add_knowledge`
 *   (the origin's audience needs a target World). Optional for
 *   character origins — omitted when the character is a legacy
 *   `universe=NULL` teammate so the destination falls back to the
 *   generic flow rather than fabricating a World.
 * - `spokesperson` (UUID). REQUIRED for character origins.
 *   Omitted for `world_detail_add_knowledge` — that origin has no
 *   character context; the whole World is the audience.
 * - `origin` (discriminator; see `KNOWLEDGE_HANDOFF_ORIGINS`).
 *
 * URL param names are stable strings; downstream parsers/tests
 * import the constants rather than hardcoding the names.
 */

/** Query-string parameter names. Exported for the destination
 * parser and tests. */
export const KNOWLEDGE_HANDOFF_PARAM = {
  universe: "universe",
  spokesperson: "spokesperson",
  origin: "origin",
} as const;

/** Discriminator values. New origins must be appended here + the
 * destination surface must handle them explicitly.
 *
 * - `character_welcome`: user just created the character via the
 *   wizard and landed on `/spokespeople/:id/welcome`.
 * - `character_detail_knowledge_panel`: user opened the character
 *   detail page and clicked the KnowledgePanel's manage-link or
 *   empty-state CTA.
 * - `world_detail_add_knowledge` (Slice 13): user opened the World
 *   detail page and clicked the "Add shared knowledge" action. The
 *   origin itself expresses UNIVERSE-audience intent — the
 *   destination MUST NOT re-ask for audience and MUST NOT expose a
 *   CHARACTER audience option in this variant. */
export const KNOWLEDGE_HANDOFF_ORIGINS = [
  "character_welcome",
  "character_detail_knowledge_panel",
  "world_detail_add_knowledge",
] as const;
export type KnowledgeHandoffOrigin =
  (typeof KNOWLEDGE_HANDOFF_ORIGINS)[number];

/** Character-origin values. Both require a spokesperson UUID and
 * offer a two-choice audience selector at the destination. */
const CHARACTER_HANDOFF_ORIGINS: readonly KnowledgeHandoffOrigin[] = [
  "character_welcome",
  "character_detail_knowledge_panel",
];

export function isKnowledgeHandoffOrigin(
  value: string | null | undefined,
): value is KnowledgeHandoffOrigin {
  return (
    typeof value === "string" &&
    (KNOWLEDGE_HANDOFF_ORIGINS as readonly string[]).includes(value)
  );
}

export function isCharacterHandoffOrigin(
  origin: KnowledgeHandoffOrigin,
): boolean {
  return CHARACTER_HANDOFF_ORIGINS.includes(origin);
}

interface BuildKnowledgeHandoffPathInput {
  /** The character's World UUID (for character origins) OR the
   * World's own UUID (for world-detail origin). REQUIRED for
   * `world_detail_add_knowledge`; nullable/undefined allowed for
   * legacy `universe=NULL` teammate character origins (destination
   * falls back to the generic flow). */
  universeId: string | null | undefined;
  /** The character's UUID. REQUIRED for character origins;
   * undefined (or explicitly omitted) for `world_detail_add_knowledge`
   * — that origin carries no character context. */
  spokespersonId?: string;
  /** Which surface initiated the handoff. */
  origin: KnowledgeHandoffOrigin;
}

/** Build the `/workspace/knowledge?…` path for a contextual
 * handoff. Always includes `origin`; includes `universe` and
 * `spokesperson` conditionally based on origin semantics. */
export function buildKnowledgeHandoffPath(
  input: BuildKnowledgeHandoffPathInput,
): string {
  const params = new URLSearchParams();
  if (input.universeId) {
    params.set(KNOWLEDGE_HANDOFF_PARAM.universe, input.universeId);
  }
  if (input.spokespersonId) {
    params.set(KNOWLEDGE_HANDOFF_PARAM.spokesperson, input.spokespersonId);
  }
  params.set(KNOWLEDGE_HANDOFF_PARAM.origin, input.origin);
  return `/workspace/knowledge?${params.toString()}`;
}

/** Parsed handoff context. Origin-conditional shape:
 * - Character origins guarantee `spokespersonId !== null` (parser
 *   rejects the URL otherwise). `universeId` may be `null` when the
 *   character is a legacy universe=NULL teammate.
 * - `world_detail_add_knowledge` guarantees `universeId !== null`
 *   (parser rejects otherwise). `spokespersonId` is always `null`.
 *
 * The destination surface must additionally verify the referenced
 * rows actually resolve (via TanStack Query hooks); shape-level
 * validation here only rejects obviously-bad params. */
export interface ParsedKnowledgeHandoff {
  universeId: string | null;
  spokespersonId: string | null;
  origin: KnowledgeHandoffOrigin;
}

/** Loose UUID shape check. The destination surface's data hooks
 * do the authoritative validation; this is a cheap gate to reject
 * obviously-bad params (e.g. an operator typed a garbage string
 * into the URL bar). */
function looksLikeUuid(value: string | null | undefined): value is string {
  if (typeof value !== "string") return false;
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(
    value,
  );
}

/** Parse the destination surface's URL query string. Returns
 * `null` when the handoff cannot be reconstructed. The destination
 * MUST fall back to the generic (non-contextual) Knowledge flow in
 * that case per Slice 11 §217 "fail safely without broadening
 * audience". Origin-conditional requirements:
 *
 * - Character origins require a UUID-shaped `spokesperson`. When
 *   missing/malformed, returns null.
 * - `world_detail_add_knowledge` requires a UUID-shaped `universe`.
 *   When missing/malformed, returns null (do NOT fall back to
 *   WORKSPACE audience — see Slice 13 §259 acceptance G).
 * - Unknown origins return null unconditionally.
 * - Universe-shape check applies to both character and world
 *   origins — a malformed universe is dropped for character
 *   (destination falls back to the generic flow) and treated as
 *   invalid for world (returns null → generic flow). */
export function parseKnowledgeHandoff(
  searchParams: URLSearchParams,
): ParsedKnowledgeHandoff | null {
  const origin = searchParams.get(KNOWLEDGE_HANDOFF_PARAM.origin);
  if (!isKnowledgeHandoffOrigin(origin)) return null;

  const rawUniverseId = searchParams.get(KNOWLEDGE_HANDOFF_PARAM.universe);
  const rawSpokespersonId = searchParams.get(
    KNOWLEDGE_HANDOFF_PARAM.spokesperson,
  );
  const universeId = looksLikeUuid(rawUniverseId) ? rawUniverseId : null;
  const spokespersonId = looksLikeUuid(rawSpokespersonId)
    ? rawSpokespersonId
    : null;

  if (isCharacterHandoffOrigin(origin)) {
    // Character origins REQUIRE a valid spokesperson UUID.
    if (!spokespersonId) return null;
    return { universeId, spokespersonId, origin };
  }

  // world_detail_add_knowledge: universe is REQUIRED; spokesperson
  // is intentionally ignored (this origin has no character context).
  if (!universeId) return null;
  return { universeId, spokespersonId: null, origin };
}
