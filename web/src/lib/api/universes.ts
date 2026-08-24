/**
 * /api/universes/ wrapper.
 *
 * SESSION 261 — Universe substrate. Backend surface:
 * shell/apps/universe/views.py::UniverseViewSet.
 * See docs/design/UNIVERSE_SCHEMA_V1.md §"API contract".
 *
 * Load-bearing:
 * - Explicit-only canon. Every create/edit is operator-initiated.
 * - NULL universe on Teammate/KnowledgeDocument = legacy semantics.
 *   The SPA MUST NOT silently pick a Universe; the operator picks.
 */
import { z } from "zod";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { apiJson } from "./client";

const universeSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  workspace_name: z.string().optional(),
  name: z.string(),
  slug: z.string(),
  description: z.string().default(""),
  /** SESSION 277 Slice 8 (Q-277-8) — compact deterministic World
   * identity injected into synthesis. 2000-char cap. Blank is
   * valid indefinitely (existing Universes migrated with brief=""). */
  brief: z.string().default(""),
  created_by: z.union([z.string(), z.number()]).nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  archived_at: z.string().nullable(),
  teammate_count: z.number().int().nonnegative().default(0),
  knowledge_document_count: z.number().int().nonnegative().default(0),
  // SESSION 262 / EPISODE_SCHEMA_V1 — Episode child count.
  episode_count: z.number().int().nonnegative().default(0),
});

export type Universe = z.infer<typeof universeSchema>;

const listResponseSchema = z.union([
  z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(universeSchema),
  }),
  z.array(universeSchema),
]);

function unwrapList(json: unknown): Universe[] {
  const parsed = listResponseSchema.parse(json);
  return Array.isArray(parsed) ? parsed : parsed.results;
}

// ---- list ----

export interface ListUniverseFilters {
  workspace?: string;
  includeArchived?: boolean;
}

export async function listUniverses(
  filters: ListUniverseFilters = {},
): Promise<Universe[]> {
  const params = new URLSearchParams();
  if (filters.workspace) params.set("workspace", filters.workspace);
  if (filters.includeArchived) params.set("include_archived", "true");
  const qs = params.toString();
  return apiJson(`/api/universes/${qs ? `?${qs}` : ""}`, {}, unwrapList);
}

/** List Universes for a workspace. Active-only by default. */
export function useUniverses(
  workspaceId: string | undefined,
  options?: {
    includeArchived?: boolean;
  } & Omit<UseQueryOptions<Universe[]>, "queryKey" | "queryFn">,
) {
  const { includeArchived, ...queryOptions } = options ?? {};
  return useQuery({
    queryKey: [
      "universes",
      "list",
      workspaceId,
      includeArchived ? "with-archived" : "active",
    ],
    queryFn: () =>
      listUniverses({
        workspace: workspaceId!,
        includeArchived,
      }),
    enabled: !!workspaceId,
    ...queryOptions,
  });
}

// ---- detail ----

export async function getUniverse(id: string): Promise<Universe> {
  return apiJson(`/api/universes/${id}/`, {}, (json) =>
    universeSchema.parse(json),
  );
}

export function useUniverse(id: string | undefined) {
  return useQuery({
    queryKey: ["universe", id],
    queryFn: () => getUniverse(id!),
    enabled: !!id,
    staleTime: 30 * 1000,
  });
}

// ---- create ----

export interface CreateUniverseInput {
  workspace: string;
  name: string;
  description?: string;
  /** SESSION 277 Slice 8 (Q-277-8) — compact World identity.
   * Optional at CREATE (Slice-5 inline name-only flow still
   * works); the dedicated /workspace/universes/new form exposes
   * an input for this. */
  brief?: string;
}

export async function createUniverse(
  input: CreateUniverseInput,
): Promise<Universe> {
  return apiJson(
    "/api/universes/",
    { method: "POST", body: input },
    (json) => universeSchema.parse(json),
  );
}

export function useCreateUniverse(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createUniverse,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["universes", "list", workspaceId] });
    },
  });
}

// ---- update ----

export interface UpdateUniverseInput {
  name?: string;
  description?: string;
  /** SESSION 277 Slice 8 (Q-277-8) — operator-editable via PATCH. */
  brief?: string;
}

export async function updateUniverse(
  id: string,
  input: UpdateUniverseInput,
): Promise<Universe> {
  return apiJson(
    `/api/universes/${id}/`,
    { method: "PATCH", body: input },
    (json) => universeSchema.parse(json),
  );
}

export function useUpdateUniverse(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateUniverseInput;
    }) => updateUniverse(id, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["universes", "list", workspaceId] });
      qc.invalidateQueries({ queryKey: ["universe", data.id] });
    },
  });
}

// ---- archive (soft delete) ----

export async function archiveUniverse(id: string): Promise<void> {
  await apiJson(`/api/universes/${id}/`, { method: "DELETE" });
}

export function useArchiveUniverse(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: archiveUniverse,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["universes", "list", workspaceId] });
    },
  });
}

// ---- unarchive ----

export async function unarchiveUniverse(id: string): Promise<Universe> {
  return apiJson(
    `/api/universes/${id}/unarchive/`,
    { method: "POST", body: {} },
    (json) => universeSchema.parse(json),
  );
}

export function useUnarchiveUniverse(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: unarchiveUniverse,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["universes", "list", workspaceId] });
    },
  });
}

// ---- hard delete (empty universes only; 409 if populated) ----

export async function hardDeleteUniverse(id: string): Promise<void> {
  await apiJson(`/api/universes/${id}/?hard=true`, { method: "DELETE" });
}

export function useHardDeleteUniverse(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: hardDeleteUniverse,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["universes", "list", workspaceId] });
    },
  });
}

// ---- Sentinel used in select controls that need an explicit "legacy" pick.
//      The SPA renders this as a real option so the operator makes a choice;
//      the payload sends either a real UUID or `null` (never empty).
export const UNIVERSE_LEGACY_SENTINEL = "__LEGACY__";


// ---- SESSION 280 v1 — possible-next-Episode suggestions --------------
//
// Read-only surface: given a Universe with ≥ 1 Episode, return a small
// number of one-sentence possible next-Episode directions. Operator
// remains authoritative — nothing here creates, edits, or persists
// anything. See docs/design/SESSION_280_EPISTEMIC_ASYMMETRY_AUDIT.md
// §56-§68 for design and §69+ for this implementation slice.

const suggestionSchema = z.object({
  text: z.string(),
});

const nextEpisodeSuggestionsResponseSchema = z.object({
  suggestions: z.array(suggestionSchema),
  substrate_summary: z
    .object({
      episodes_used: z.number().int().nonnegative(),
      memories_used: z.number().int().nonnegative(),
      cast_count: z.number().int().nonnegative(),
    })
    .partial()
    .passthrough(),
  generated_at: z.string(),
  model: z.string(),
  cache: z
    .object({
      hit: z.boolean(),
      ttl_seconds: z.number().int().nonnegative(),
    })
    .passthrough(),
});

export type NextEpisodeSuggestion = z.infer<typeof suggestionSchema>;
export type NextEpisodeSuggestionsResponse = z.infer<
  typeof nextEpisodeSuggestionsResponseSchema
>;

export async function getNextEpisodeSuggestions(
  universeId: string,
  opts: { n?: number; refresh?: boolean } = {},
): Promise<NextEpisodeSuggestionsResponse> {
  const params = new URLSearchParams();
  if (opts.n != null) params.set("n", String(opts.n));
  if (opts.refresh) params.set("refresh", "true");
  const qs = params.toString();
  return apiJson(
    `/api/universes/${universeId}/next-episode-suggestions/${qs ? `?${qs}` : ""}`,
    {},
    (json) => nextEpisodeSuggestionsResponseSchema.parse(json),
  );
}

/**
 * Query for "where could this story go next?" suggestions for a Universe.
 *
 * Gated on the caller-supplied `enabled` flag — the SPA is expected to
 * pass `enabled: existingEpisodesCount >= 1` so we don't spend a
 * provider call generating suggestions for a Universe with no story
 * substrate. Server also short-circuits empty Universes with a fast
 * 200 + empty list (no LLM call), but the frontend gate saves a round
 * trip.
 */
export function useNextEpisodeSuggestions(
  universeId: string | undefined,
  opts: {
    n?: number;
    enabled?: boolean;
  } & Omit<
    UseQueryOptions<NextEpisodeSuggestionsResponse>,
    "queryKey" | "queryFn"
  > = {},
) {
  const { n, enabled = true, ...queryOptions } = opts;
  return useQuery({
    queryKey: ["universe", universeId, "next-episode-suggestions", n ?? 3],
    queryFn: () => getNextEpisodeSuggestions(universeId!, { n }),
    enabled: !!universeId && enabled,
    // Match server-side 10-minute cache so a fresh mount within the
    // window doesn't re-fetch.
    staleTime: 10 * 60 * 1000,
    // Refresh is operator-driven via refetch() — don't refetch on
    // window focus (would surprise the operator with new options
    // just from clicking away and back).
    refetchOnWindowFocus: false,
    retry: false,
    ...queryOptions,
  });
}
