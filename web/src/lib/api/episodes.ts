/**
 * /api/episodes/ wrapper.
 *
 * SESSION 262 / EPISODE_SCHEMA_V1. Backend surface:
 * shell/apps/universe/views.py::EpisodeViewSet + Composition
 * attach/detach at
 * shell/apps/compositions/views.py::CompositionViewSet.attach_episode.
 *
 * Load-bearing:
 * - Episode creation is explicit-only. The SPA MUST NOT silently
 *   auto-create Episodes.
 * - Composition may remain episode=NULL indefinitely (standalone
 *   workflow untouched).
 * - Episode linkage never mutates SESSION 262 Composition
 *   observability fields.
 */
import { z } from "zod";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { apiJson } from "./client";

const castMemberSchema = z.object({
  id: z.string(),
  name: z.string(),
});

const episodeSchema = z.object({
  id: z.string(),
  universe: z.string(),
  universe_name: z.string().optional(),
  title: z.string(),
  operator_topic: z.string(),
  cast: z.array(castMemberSchema).default([]),
  composition_count: z.number().int().nonnegative().default(0),
  archived_at: z.string().nullable(),
  created_by: z.union([z.string(), z.number()]).nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Episode = z.infer<typeof episodeSchema>;
export type EpisodeCastMember = z.infer<typeof castMemberSchema>;

const listResponseSchema = z.union([
  z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(episodeSchema),
  }),
  z.array(episodeSchema),
]);

function unwrapList(json: unknown): Episode[] {
  const parsed = listResponseSchema.parse(json);
  return Array.isArray(parsed) ? parsed : parsed.results;
}

// ---- list ----

export interface ListEpisodeFilters {
  universe?: string;
  includeArchived?: boolean;
}

export async function listEpisodes(
  filters: ListEpisodeFilters = {},
): Promise<Episode[]> {
  const params = new URLSearchParams();
  if (filters.universe) params.set("universe", filters.universe);
  if (filters.includeArchived) params.set("include_archived", "true");
  const qs = params.toString();
  return apiJson(`/api/episodes/${qs ? `?${qs}` : ""}`, {}, unwrapList);
}

export function useEpisodes(
  universeId: string | undefined,
  options?: {
    includeArchived?: boolean;
  } & Omit<UseQueryOptions<Episode[]>, "queryKey" | "queryFn">,
) {
  const { includeArchived, ...queryOptions } = options ?? {};
  return useQuery({
    queryKey: ["episodes", universeId ?? "none", { includeArchived }],
    queryFn: () =>
      listEpisodes({
        universe: universeId,
        includeArchived,
      }),
    enabled: !!universeId,
    ...(queryOptions ?? {}),
  });
}

// ---- retrieve ----

export function useEpisode(id: string | undefined) {
  return useQuery({
    queryKey: ["episode", id],
    queryFn: () =>
      apiJson<Episode>(`/api/episodes/${id}/`, {}, (json) =>
        episodeSchema.parse(json),
      ),
    enabled: !!id,
  });
}

// ---- create ----

export interface CreateEpisodePayload {
  universe: string;
  title: string;
  operator_topic: string;
  /**
   * SESSION 269 §12 — optional atomic cast seed. Every UUID must
   * belong to a Teammate in this Episode's Universe. Backend
   * attaches under a transaction with the same signal validation
   * the dedicated ``/cast/`` endpoint uses. Absent/empty means
   * "create an empty-cast draft" (byte-identical to pre-§12).
   */
  cast_ids?: string[];
}

export function useCreateEpisode(universeId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (payload: CreateEpisodePayload) =>
      apiJson<Episode>(
        `/api/episodes/`,
        {
          method: "POST",
          body: payload,
        },
        (json) => episodeSchema.parse(json),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", universeId] });
    },
  });
}

// ---- update (title / operator_topic) ----

export interface UpdateEpisodePayload {
  title?: string;
  operator_topic?: string;
}

export function useUpdateEpisode(universeId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: { id: string; payload: UpdateEpisodePayload }) =>
      apiJson<Episode>(
        `/api/episodes/${args.id}/`,
        {
          method: "PATCH",
          body: args.payload,
        },
        (json) => episodeSchema.parse(json),
      ),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["episode", data.id] });
      qc.invalidateQueries({ queryKey: ["episodes", universeId] });
    },
  });
}

// ---- archive / unarchive / hard-delete ----

export function useArchiveEpisode(universeId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      apiJson<null>(`/api/episodes/${id}/`, { method: "DELETE" }, () => null),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", universeId] });
    },
  });
}

export function useUnarchiveEpisode(universeId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      apiJson<Episode>(
        `/api/episodes/${id}/unarchive/`,
        { method: "POST" },
        (json) => episodeSchema.parse(json),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", universeId] });
    },
  });
}

export function useHardDeleteEpisode(universeId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (id: string) =>
      apiJson<null>(
        `/api/episodes/${id}/?hard=true`,
        { method: "DELETE" },
        () => null,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episodes", universeId] });
    },
  });
}

// ---- cast add / remove ----

export function useAddCastMember(episodeId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (teammateId: string) =>
      apiJson<Episode>(
        `/api/episodes/${episodeId}/cast/`,
        {
          method: "POST",
          body: { teammate: teammateId },
        },
        (json) => episodeSchema.parse(json),
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episode", episodeId] });
    },
  });
}

export function useRemoveCastMember(episodeId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (teammateId: string) =>
      apiJson<null>(
        `/api/episodes/${episodeId}/cast/${teammateId}/`,
        { method: "DELETE" },
        () => null,
      ),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["episode", episodeId] });
    },
  });
}

// ---- Composition attach / detach (proxy for the CompositionViewSet) ----

export function useAttachCompositionToEpisode() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (args: {
      compositionId: string;
      episodeId: string | null;
    }) => {
      if (args.episodeId === null) {
        return apiJson(
          `/api/compositions/${args.compositionId}/attach-episode/`,
          { method: "DELETE" },
          () => null,
        );
      }
      return apiJson(
        `/api/compositions/${args.compositionId}/attach-episode/`,
        {
          method: "POST",
          body: { episode: args.episodeId },
        },
        () => null,
      );
    },
    onSuccess: (_data, args) => {
      qc.invalidateQueries({
        queryKey: ["composition", args.compositionId],
      });
      qc.invalidateQueries({ queryKey: ["episodes"] });
    },
  });
}
