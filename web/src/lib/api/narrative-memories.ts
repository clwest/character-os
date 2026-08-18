/**
 * /api/narrative-memories/ wrapper.
 *
 * SESSION 264 Slice 1 — thin operator-visible vertical slice.
 * Backend: shell/apps/memory/views.py::NarrativeMemoryViewSet +
 * the promote action on
 * shell/apps/compositions/views.py::CompositionViewSet.promote_narrative_memory.
 *
 * Load-bearing rules mirrored on the SPA side:
 *
 * - Promotion is explicit. No auto-promote from render success.
 * - Narrative memory NEVER mutates KnowledgeDocument. This client
 *   only calls the memory endpoints and the promote action; there
 *   is no path to canon here.
 * - Retrieval integration is Slice 2 — this file lets the operator
 *   promote and inspect. It does not surface memories into
 *   synthesis prompts.
 */
import { z } from "zod";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { apiJson } from "./client";

export const NARRATIVE_MEMORY_KINDS = [
  "event",
  "action",
  "promise",
  "dialogue_callback",
  "world_detail",
] as const;
export type NarrativeMemoryKind = (typeof NARRATIVE_MEMORY_KINDS)[number];

export const NARRATIVE_MEMORY_WEIGHTS = ["central", "peripheral"] as const;
export type NarrativeMemoryWeight = (typeof NARRATIVE_MEMORY_WEIGHTS)[number];

export const NARRATIVE_MEMORY_STATUSES = [
  "remembered",
  "superseded",
  "archived",
] as const;
export type NarrativeMemoryStatus = (typeof NARRATIVE_MEMORY_STATUSES)[number];

const witnessSchema = z.object({
  id: z.string(),
  name: z.string(),
});

const narrativeMemorySchema = z.object({
  id: z.string(),
  episode: z.string(),
  episode_title: z.string().optional().default(""),
  source_composition: z.string(),
  source_composition_name: z.string().optional().default(""),
  workspace: z.string(),
  universe: z.string(),
  universe_name: z.string().optional().default(""),
  kind: z.enum(NARRATIVE_MEMORY_KINDS),
  body: z.string(),
  witnessed_by: z.array(witnessSchema).default([]),
  weight: z.enum(NARRATIVE_MEMORY_WEIGHTS),
  status: z.enum(NARRATIVE_MEMORY_STATUSES),
  supersedes: z.string().nullable(),
  superseded_at: z.string().nullable(),
  superseded_reason: z.string().default(""),
  archived_at: z.string().nullable(),
  promoted_by: z.union([z.string(), z.number()]).nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  is_current: z.boolean().default(false),
});

export type NarrativeMemory = z.infer<typeof narrativeMemorySchema>;
export type NarrativeMemoryWitness = z.infer<typeof witnessSchema>;

const listResponseSchema = z.union([
  z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(narrativeMemorySchema),
  }),
  z.array(narrativeMemorySchema),
]);

function unwrapList(json: unknown): NarrativeMemory[] {
  const parsed = listResponseSchema.parse(json);
  return Array.isArray(parsed) ? parsed : parsed.results;
}

// ---- list ----

export interface ListNarrativeMemoriesFilters {
  episode?: string;
  universe?: string;
  sourceComposition?: string;
  includeArchived?: boolean;
  includeSuperseded?: boolean;
}

export async function listNarrativeMemories(
  filters: ListNarrativeMemoriesFilters = {},
): Promise<NarrativeMemory[]> {
  const params = new URLSearchParams();
  if (filters.episode) params.set("episode", filters.episode);
  if (filters.universe) params.set("universe", filters.universe);
  if (filters.sourceComposition)
    params.set("source_composition", filters.sourceComposition);
  if (filters.includeArchived) params.set("include_archived", "true");
  if (filters.includeSuperseded) params.set("include_superseded", "true");
  const qs = params.toString();
  return apiJson(
    `/api/narrative-memories/${qs ? `?${qs}` : ""}`,
    {},
    unwrapList,
  );
}

/** List memories scoped to one Episode. */
export function useNarrativeMemoriesByEpisode(
  episodeId: string | undefined,
  options?: {
    includeArchived?: boolean;
    includeSuperseded?: boolean;
  } & Omit<UseQueryOptions<NarrativeMemory[]>, "queryKey" | "queryFn">,
) {
  const { includeArchived, includeSuperseded, ...queryOptions } = options ?? {};
  return useQuery({
    queryKey: [
      "narrative-memories",
      "episode",
      episodeId ?? "none",
      { includeArchived, includeSuperseded },
    ],
    queryFn: () =>
      listNarrativeMemories({
        episode: episodeId,
        includeArchived,
        includeSuperseded,
      }),
    enabled: !!episodeId,
    ...(queryOptions ?? {}),
  });
}

/** List memories scoped to one Universe (across all its Episodes). */
export function useNarrativeMemoriesByUniverse(
  universeId: string | undefined,
  options?: {
    includeArchived?: boolean;
    includeSuperseded?: boolean;
  } & Omit<UseQueryOptions<NarrativeMemory[]>, "queryKey" | "queryFn">,
) {
  const { includeArchived, includeSuperseded, ...queryOptions } = options ?? {};
  return useQuery({
    queryKey: [
      "narrative-memories",
      "universe",
      universeId ?? "none",
      { includeArchived, includeSuperseded },
    ],
    queryFn: () =>
      listNarrativeMemories({
        universe: universeId,
        includeArchived,
        includeSuperseded,
      }),
    enabled: !!universeId,
    ...(queryOptions ?? {}),
  });
}

/** List memories promoted from one specific Composition. */
export function useNarrativeMemoriesByComposition(
  compositionId: string | undefined,
  options?: {
    includeArchived?: boolean;
    includeSuperseded?: boolean;
  } & Omit<UseQueryOptions<NarrativeMemory[]>, "queryKey" | "queryFn">,
) {
  const { includeArchived, includeSuperseded, ...queryOptions } = options ?? {};
  return useQuery({
    queryKey: [
      "narrative-memories",
      "composition",
      compositionId ?? "none",
      { includeArchived, includeSuperseded },
    ],
    queryFn: () =>
      listNarrativeMemories({
        sourceComposition: compositionId,
        includeArchived,
        includeSuperseded,
      }),
    enabled: !!compositionId,
    ...(queryOptions ?? {}),
  });
}

// ---- promote from composition ----

export interface PromoteMemoryItem {
  body: string;
  kind?: NarrativeMemoryKind;
  weight?: NarrativeMemoryWeight;
  witnessed_by?: string[];
  supersedes?: string;
  superseded_reason?: string;
}

export interface PromoteMemoriesPayload {
  episode: string;
  memories: PromoteMemoryItem[];
}

const promoteResponseSchema = z.object({
  memories: z.array(narrativeMemorySchema),
});

export function usePromoteMemories(compositionId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: PromoteMemoriesPayload) =>
      apiJson(
        `/api/compositions/${compositionId}/promote-narrative-memory/`,
        {
          method: "POST",
          body: payload,
        },
        (json) => promoteResponseSchema.parse(json).memories,
      ),
    onSuccess: (_data, payload) => {
      qc.invalidateQueries({
        queryKey: ["narrative-memories", "composition", compositionId],
      });
      qc.invalidateQueries({
        queryKey: ["narrative-memories", "episode", payload.episode],
      });
      qc.invalidateQueries({ queryKey: ["narrative-memories", "universe"] });
    },
  });
}

// ---- archive / unarchive ----

export function useArchiveMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      apiJson<null>(
        `/api/narrative-memories/${id}/`,
        { method: "DELETE" },
        () => null,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["narrative-memories"] });
    },
  });
}

export function useUnarchiveMemory() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      apiJson<NarrativeMemory>(
        `/api/narrative-memories/${id}/unarchive/`,
        { method: "POST" },
        (json) => narrativeMemorySchema.parse(json),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["narrative-memories"] });
    },
  });
}
