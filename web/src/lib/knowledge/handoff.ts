/**
 * SESSION 277 Slice 12 (Q-277-12) — Contextual character-origin
 * Knowledge handoff contract.
 *
 * Two operator surfaces (character welcome page + character-detail
 * KnowledgePanel) route the operator to `/workspace/knowledge` to
 * teach a newly-created or existing character. Pre-Slice-12 the
 * routes were bare strings that lost every scrap of context —
 * Slice 6 §120 handoff gap. Slice 12 lands a lossless handoff via
 * URL query params so the destination can render an explicit
 * World-vs-character audience decision instead of the generic
 * scope picker.
 *
 * Contract:
 * - `universe` (UUID; optional — omitted when the character is a
 *   legacy `universe=NULL` teammate so the destination falls back
 *   to the generic flow rather than fabricating a World).
 * - `spokesperson` (UUID; required for character-origin surfaces).
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
 *   empty-state CTA. */
export const KNOWLEDGE_HANDOFF_ORIGINS = [
  "character_welcome",
  "character_detail_knowledge_panel",
] as const;
export type KnowledgeHandoffOrigin =
  (typeof KNOWLEDGE_HANDOFF_ORIGINS)[number];

export function isKnowledgeHandoffOrigin(
  value: string | null | undefined,
): value is KnowledgeHandoffOrigin {
  return (
    typeof value === "string" &&
    (KNOWLEDGE_HANDOFF_ORIGINS as readonly string[]).includes(value)
  );
}

interface BuildKnowledgeHandoffPathInput {
  /** The character's World UUID. Nullable/undefined for legacy
   * `universe=NULL` teammates — the destination will fall back to
   * the generic flow rather than fabricating a World context. */
  universeId: string | null | undefined;
  /** The character's UUID. Required. */
  spokespersonId: string;
  /** Which surface initiated the handoff. */
  origin: KnowledgeHandoffOrigin;
}

/** Build the `/workspace/knowledge?…` path for a character-origin
 * handoff. Always includes `spokesperson` and `origin`; includes
 * `universe` only when the character actually has one. */
export function buildKnowledgeHandoffPath(
  input: BuildKnowledgeHandoffPathInput,
): string {
  const params = new URLSearchParams();
  if (input.universeId) {
    params.set(KNOWLEDGE_HANDOFF_PARAM.universe, input.universeId);
  }
  params.set(KNOWLEDGE_HANDOFF_PARAM.spokesperson, input.spokespersonId);
  params.set(KNOWLEDGE_HANDOFF_PARAM.origin, input.origin);
  return `/workspace/knowledge?${params.toString()}`;
}

/** Parsed handoff context. All fields are pre-validated at the
 * shape/type layer only; the destination surface must additionally
 * verify that `universeId` resolves to an active Universe and that
 * `spokespersonId` resolves to a Teammate whose universe matches
 * (or, when `universeId` is null, that the origin permits legacy
 * teammates). */
export interface ParsedKnowledgeHandoff {
  universeId: string | null;
  spokespersonId: string;
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
 * `null` when the handoff cannot be reconstructed (missing
 * required params, unknown origin, malformed UUIDs). The
 * destination MUST fall back to the generic (non-contextual)
 * Knowledge flow in that case per Slice 11 §217 "fail safely
 * without broadening audience". */
export function parseKnowledgeHandoff(
  searchParams: URLSearchParams,
): ParsedKnowledgeHandoff | null {
  const spokespersonId = searchParams.get(
    KNOWLEDGE_HANDOFF_PARAM.spokesperson,
  );
  const origin = searchParams.get(KNOWLEDGE_HANDOFF_PARAM.origin);
  if (!looksLikeUuid(spokespersonId)) return null;
  if (!isKnowledgeHandoffOrigin(origin)) return null;
  const rawUniverseId = searchParams.get(KNOWLEDGE_HANDOFF_PARAM.universe);
  const universeId = looksLikeUuid(rawUniverseId) ? rawUniverseId : null;
  return { universeId, spokespersonId, origin };
}
