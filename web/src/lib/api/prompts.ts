/**
 * /api/prompts/* wrappers — thin SPA bindings for the
 * `character_os.prompts` helpers exposed over HTTP via
 * `shell/character_os/api_prompts.py`.
 *
 * Today this is just the tone-suggestion endpoint used by the
 * wizard's Step 1. More helpers (palette suggestion, sharpening,
 * etc.) can land alongside as their UI surfaces appear.
 */
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "./client";
import { TONE_ARCHETYPES, type ToneArchetype } from "./spokespeople";

const suggestToneResponseSchema = z.object({
  tone: z.enum(TONE_ARCHETYPES),
});

export async function suggestTone(brief: string): Promise<ToneArchetype> {
  return apiJson(
    `/api/prompts/suggest-tone/?brief=${encodeURIComponent(brief)}`,
    {},
    (json) => suggestToneResponseSchema.parse(json).tone,
  );
}

/**
 * Reactive tone suggestion for the brief textarea.
 *
 * The hook is disabled until the brief crosses ``minChars`` (30 by
 * default) — there's no useful signal in a 4-character brief, and
 * we don't want to hammer the endpoint on every keystroke. TanStack
 * Query's `staleTime` debounces follow-ups for the same brief —
 * typing then deleting back to the same prefix doesn't re-fetch.
 */
export function useSuggestTone(
  brief: string,
  { minChars = 30 }: { minChars?: number } = {},
) {
  const trimmed = brief.trim();
  return useQuery({
    queryKey: ["prompts", "suggest-tone", trimmed],
    queryFn: () => suggestTone(trimmed),
    enabled: trimmed.length >= minChars,
    // Briefs change slowly while the operator types; cache aggressively.
    staleTime: 10 * 60 * 1000,
  });
}
