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
  created_by: z.union([z.string(), z.number()]).nullable(),
  created_at: z.string(),
  updated_at: z.string(),
  archived_at: z.string().nullable(),
  teammate_count: z.number().int().nonnegative().default(0),
  knowledge_document_count: z.number().int().nonnegative().default(0),
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
