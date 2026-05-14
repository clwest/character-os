/**
 * /api/spokespeople/ wrapper.
 *
 * Backend surface: SpokespersonViewSet (shell/apps/spokespeople/views.py).
 * DRF's default router returns a list as `{count, next, previous, results}`
 * when pagination is configured, or a bare array otherwise. We tolerate
 * both shapes here so the SPA doesn't break when pagination flips on.
 */
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
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

// ---- Single-resource fetch (detail page) ---------------------------

export async function getSpokesperson(id: string): Promise<Spokesperson> {
  return apiJson(`/api/spokespeople/${id}/`, {}, (json) =>
    spokespersonSchema.parse(json),
  );
}

export function useSpokesperson(id: string | undefined) {
  return useQuery({
    queryKey: ["spokesperson", id],
    queryFn: () => getSpokesperson(id!),
    enabled: Boolean(id),
    // Detail page refresh cadence: tighter than the list (operator
    // is actively looking at one row, expects status pill changes
    // to show within a few seconds). Real avatar / voice status
    // transitions land here too in future slices.
    staleTime: 15 * 1000,
  });
}

// ---- Create (S-06) -------------------------------------------------

export interface CreateSpokespersonInput {
  workspace: string;
  name: string;
  business_brief: string;
  /** ``data:image/{png|jpeg|webp};base64,...`` — optional. When
   * supplied, the backend fires the media-engine avatar create
   * synchronously and persists `runway_avatar_id` on the row. */
  portrait_data_uri?: string;
  voice_preset?: string;
}

export async function createSpokesperson(
  input: CreateSpokespersonInput,
): Promise<Spokesperson> {
  return apiJson(
    "/api/spokespeople/",
    { method: "POST", body: input },
    (json) => spokespersonSchema.parse(json),
  );
}

export function useCreateSpokesperson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createSpokesperson,
    onSuccess: (spokesperson) => {
      // Invalidate the list so the dashboard refreshes when the
      // user navigates back. Also seed the single-resource cache
      // so the detail page renders instantly on redirect.
      qc.invalidateQueries({ queryKey: ["spokespeople"] });
      qc.setQueryData(["spokesperson", spokesperson.id], spokesperson);
      // Subscription usage might have shifted (spokespeople count).
      qc.invalidateQueries({ queryKey: ["subscription"] });
    },
  });
}
