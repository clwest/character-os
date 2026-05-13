/**
 * /api/spokespeople/ wrapper.
 *
 * Backend surface: SpokespersonViewSet (shell/apps/spokespeople/views.py).
 * DRF's default router returns a list as `{count, next, previous, results}`
 * when pagination is configured, or a bare array otherwise. We tolerate
 * both shapes here so the SPA doesn't break when pagination flips on.
 */
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "./client";

const spokespersonSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  workspace_name: z.string().optional(),
  name: z.string(),
  business_brief: z.string(),
  status: z.enum(["setup_needed", "ready", "archived"]),
  runway_avatar_id: z.string(),
  runway_avatar_status: z.string(),
  portrait_path: z.string(),
  voice_id: z.string(),
  video_count: z.number().int().nonnegative().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Spokesperson = z.infer<typeof spokespersonSchema>;

// DRF returns either an array or a paginated envelope. Accept both.
const listResponseSchema = z.union([
  z.array(spokespersonSchema),
  z.object({
    count: z.number().int().optional(),
    next: z.string().nullable().optional(),
    previous: z.string().nullable().optional(),
    results: z.array(spokespersonSchema),
  }),
]);

function unwrapList(json: unknown): Spokesperson[] {
  const parsed = listResponseSchema.parse(json);
  return Array.isArray(parsed) ? parsed : parsed.results;
}

export async function listSpokespeople(): Promise<Spokesperson[]> {
  return apiJson("/api/spokespeople/", {}, unwrapList);
}

export function useSpokespeople() {
  return useQuery({
    queryKey: ["spokespeople"],
    queryFn: listSpokespeople,
  });
}
