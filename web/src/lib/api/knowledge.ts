/**
 * /api/knowledge/ wrapper.
 *
 * Backend surface: KnowledgeDocumentViewSet
 * (shell/apps/embeddings/views.py). SESSION 138 / K4.
 *
 * The route is workspace-scoped via a ``?workspace=<uuid>``
 * query param. Membership checks happen on the server.
 *
 * Two write paths: ``text_content`` for paste / markdown,
 * ``pdf_data_uri`` for PDF upload. Exactly one must be set.
 */
import { z } from "zod";
import {
  useMutation,
  useQuery,
  useQueryClient,
  type UseQueryOptions,
} from "@tanstack/react-query";
import { apiJson } from "./client";

// Mirrors apps.embeddings.models.DocumentType
export const DOCUMENT_TYPES = ["text", "markdown", "pdf", "url"] as const;
export type DocumentType = (typeof DOCUMENT_TYPES)[number];

// Mirrors apps.embeddings.models.IngestedVia
export const INGESTED_VIAS = ["paste", "upload", "serper", "seed"] as const;
export type IngestedVia = (typeof INGESTED_VIAS)[number];

// Mirrors apps.embeddings.models.DocumentStatus
export const DOCUMENT_STATUSES = [
  "pending",
  "processing",
  "processed",
  "failed",
] as const;
export type DocumentStatus = (typeof DOCUMENT_STATUSES)[number];

const knowledgeChunkSchema = z.object({
  id: z.string(),
  chunk_index: z.number(),
  chunk_text: z.string(),
  chunk_size: z.number(),
  overlap_size: z.number(),
  embedding_model: z.string(),
  embedding_cost_micros: z.number(),
  processing_time_ms: z.number().nullable(),
});

export type KnowledgeChunk = z.infer<typeof knowledgeChunkSchema>;

const knowledgeDocumentSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  workspace_name: z.string().optional(),
  spokespeople: z.array(z.string()),
  title: z.string(),
  document_type: z.enum(DOCUMENT_TYPES),
  content_hash: z.string(),
  source_url: z.string(),
  source_metadata: z.record(z.string(), z.unknown()).default({}),
  ingested_via: z.enum(INGESTED_VIAS),
  status: z.enum(DOCUMENT_STATUSES),
  error_message: z.string(),
  is_active: z.boolean(),
  chunk_count: z.number(),
  created_at: z.string(),
  updated_at: z.string(),
  // K4.1 — populated only on the detail endpoint, not list.
  chunks: z.array(knowledgeChunkSchema).optional(),
});

export type KnowledgeDocument = z.infer<typeof knowledgeDocumentSchema>;

const listResponseSchema = z.union([
  z.object({
    count: z.number(),
    next: z.string().nullable(),
    previous: z.string().nullable(),
    results: z.array(knowledgeDocumentSchema),
  }),
  z.array(knowledgeDocumentSchema),
]);

function unwrapList(json: unknown): KnowledgeDocument[] {
  const parsed = listResponseSchema.parse(json);
  return Array.isArray(parsed) ? parsed : parsed.results;
}

// ---- list -----------------------------------------------

export interface ListKnowledgeFilters {
  workspace: string;
  spokesperson?: string; // SESSION 138 / K5 — narrow to docs visible to one spokesperson
}

export async function listKnowledge(
  filters: ListKnowledgeFilters,
): Promise<KnowledgeDocument[]> {
  const params = new URLSearchParams({ workspace: filters.workspace });
  if (filters.spokesperson) {
    params.set("spokesperson", filters.spokesperson);
  }
  return apiJson(`/api/knowledge/?${params.toString()}`, {}, unwrapList);
}

export function useKnowledgeList(
  workspaceId: string | undefined,
  options?: Omit<
    UseQueryOptions<KnowledgeDocument[]>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: ["knowledge", "list", workspaceId],
    queryFn: () => listKnowledge({ workspace: workspaceId! }),
    enabled: !!workspaceId,
    ...options,
  });
}

/** SESSION 138 / K5 — spokesperson-scoped list. Returns docs
 * visible to this spokesperson (empty M2M OR they're attached). */
export function useSpokespersonKnowledge(
  workspaceId: string | undefined,
  spokespersonId: string | undefined,
  options?: Omit<
    UseQueryOptions<KnowledgeDocument[]>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: ["knowledge", "for-spokesperson", workspaceId, spokespersonId],
    queryFn: () =>
      listKnowledge({
        workspace: workspaceId!,
        spokesperson: spokespersonId!,
      }),
    enabled: !!workspaceId && !!spokespersonId,
    ...options,
  });
}

// ---- detail ---------------------------------------------

export async function getKnowledgeDocument(
  id: string,
): Promise<KnowledgeDocument> {
  return apiJson(`/api/knowledge/${id}/`, {}, (json) =>
    knowledgeDocumentSchema.parse(json),
  );
}

export function useKnowledgeDocument(
  id: string | undefined,
  options?: Omit<
    UseQueryOptions<KnowledgeDocument>,
    "queryKey" | "queryFn"
  >,
) {
  return useQuery({
    queryKey: ["knowledge", "detail", id],
    queryFn: () => getKnowledgeDocument(id!),
    enabled: !!id,
    ...options,
  });
}

// ---- compositions reverse (F7, workspace fabric) -------

const knowledgeUsedByItemSchema = z.object({
  composition_id: z.string(),
  composition_name: z.string(),
  template_kind: z.string(),
  status: z.enum([
    "draft",
    "planning",
    "running",
    "partial",
    "completed",
    "failed",
  ]),
  created_at: z.string(),
  spokesperson_name: z.string(),
  chunk_count: z.number().int(),
});

const knowledgeUsedByResponseSchema = z.object({
  compositions: z.array(knowledgeUsedByItemSchema),
});

export type KnowledgeUsedByItem = z.infer<typeof knowledgeUsedByItemSchema>;

export async function getKnowledgeCompositions(
  id: string,
): Promise<KnowledgeUsedByItem[]> {
  return apiJson(
    `/api/knowledge/${id}/compositions/`,
    {},
    (json) => knowledgeUsedByResponseSchema.parse(json).compositions,
  );
}

export function useKnowledgeCompositions(id: string | undefined) {
  return useQuery({
    queryKey: ["knowledge", "compositions", id],
    queryFn: () => getKnowledgeCompositions(id!),
    enabled: !!id,
    staleTime: 30_000,
  });
}

// ---- create ---------------------------------------------

export interface CreateKnowledgePayload {
  workspace: string;
  title?: string;             // optional for URL path — page title is derived
  text_content?: string;
  pdf_data_uri?: string;
  source_url_input?: string;  // K7 — URL ingest
  via_serper?: boolean;       // K7 — flag set when URL came from search
  spokesperson_ids?: string[];
}

export async function createKnowledge(
  payload: CreateKnowledgePayload,
): Promise<KnowledgeDocument> {
  return apiJson(
    "/api/knowledge/",
    { method: "POST", body: payload },
    (json) => knowledgeDocumentSchema.parse(json),
  );
}

export function useCreateKnowledge(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createKnowledge,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["knowledge", "list", workspaceId] });
    },
  });
}

// ---- update (title + spokespeople) ----------------------

export interface UpdateKnowledgePayload {
  title?: string;
  spokesperson_ids?: string[];
}

export async function updateKnowledge(
  id: string,
  payload: UpdateKnowledgePayload,
): Promise<KnowledgeDocument> {
  return apiJson(
    `/api/knowledge/${id}/`,
    { method: "PATCH", body: payload },
    (json) => knowledgeDocumentSchema.parse(json),
  );
}

export function useUpdateKnowledge(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({
      id,
      payload,
    }: {
      id: string;
      payload: UpdateKnowledgePayload;
    }) => updateKnowledge(id, payload),
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["knowledge", "list", workspaceId] });
      qc.invalidateQueries({ queryKey: ["knowledge", "detail", data.id] });
    },
  });
}

// ---- attach / detach (SESSION 138 / K5) -----------------

export async function attachSpokesperson(
  documentId: string,
  spokespersonId: string,
): Promise<KnowledgeDocument> {
  return apiJson(
    `/api/knowledge/${documentId}/attach/`,
    { method: "POST", body: { spokesperson_id: spokespersonId } },
    (json) => knowledgeDocumentSchema.parse(json),
  );
}

export async function detachSpokesperson(
  documentId: string,
  spokespersonId: string,
): Promise<KnowledgeDocument> {
  return apiJson(
    `/api/knowledge/${documentId}/detach/`,
    { method: "POST", body: { spokesperson_id: spokespersonId } },
    (json) => knowledgeDocumentSchema.parse(json),
  );
}

/** Toggle attachment of one spokesperson to one knowledge doc.
 * Invalidates both the global list and the per-spokesperson list. */
export function useToggleSpokespersonAttachment(
  workspaceId: string | undefined,
  spokespersonId: string | undefined,
) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({
      documentId,
      attach,
    }: {
      documentId: string;
      attach: boolean;
    }) => {
      if (!spokespersonId) {
        throw new Error("spokespersonId is required to toggle attachment");
      }
      return attach
        ? attachSpokesperson(documentId, spokespersonId)
        : detachSpokesperson(documentId, spokespersonId);
    },
    onSuccess: (data) => {
      qc.invalidateQueries({ queryKey: ["knowledge", "list", workspaceId] });
      qc.invalidateQueries({
        queryKey: ["knowledge", "for-spokesperson", workspaceId, spokespersonId],
      });
      qc.invalidateQueries({ queryKey: ["knowledge", "detail", data.id] });
    },
  });
}

// ---- delete (soft) --------------------------------------

export async function deleteKnowledge(id: string): Promise<void> {
  await apiJson(`/api/knowledge/${id}/`, { method: "DELETE" });
}

export function useDeleteKnowledge(workspaceId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteKnowledge,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["knowledge", "list", workspaceId] });
    },
  });
}

// ---- search discovery (SESSION 140 / K7) ---------------

const searchResultSchema = z.object({
  title: z.string(),
  url: z.string(),
  snippet: z.string(),
  position: z.number(),
});

export type SearchResult = z.infer<typeof searchResultSchema>;

const searchResponseSchema = z.object({
  query: z.string(),
  results: z.array(searchResultSchema),
});

export async function searchKnowledge(
  query: string,
  topK: number = 8,
): Promise<SearchResult[]> {
  return apiJson(
    "/api/knowledge/search/",
    { method: "POST", body: { q: query, top_k: topK } },
    (json) => searchResponseSchema.parse(json).results,
  );
}

export function useKnowledgeSearch() {
  // Mutation rather than query — the search fires on operator
  // submit, not on render. Result lives in the component's
  // useState until the operator picks one to ingest.
  return useMutation({
    mutationFn: (q: string) => searchKnowledge(q),
  });
}

// ---- helpers --------------------------------------------

/** Convert a File (from <input type="file" />) into a base64
 * data URI suitable for the ``pdf_data_uri`` field. */
export async function pdfFileToDataUri(file: File): Promise<string> {
  if (file.type !== "application/pdf" && !file.name.toLowerCase().endsWith(".pdf")) {
    throw new Error("Only PDF files are accepted.");
  }
  const reader = new FileReader();
  return new Promise((resolve, reject) => {
    reader.onerror = () => reject(reader.error ?? new Error("file read failed"));
    reader.onload = () => {
      const result = reader.result;
      if (typeof result !== "string") {
        reject(new Error("unexpected non-string FileReader result"));
        return;
      }
      // FileReader yields ``data:<mime>;base64,...``. Normalize the
      // MIME prefix so the backend's strict-prefix check accepts it.
      const idx = result.indexOf(";base64,");
      if (idx < 0) {
        reject(new Error("FileReader did not produce a base64 data URI"));
        return;
      }
      resolve("data:application/pdf;base64," + result.slice(idx + ";base64,".length));
    };
    reader.readAsDataURL(file);
  });
}

/** Status pill color hint — used by the SPA list view. */
export function statusTone(status: DocumentStatus): "neutral" | "info" | "success" | "danger" {
  switch (status) {
    case "pending":
      return "neutral";
    case "processing":
      return "info";
    case "processed":
      return "success";
    case "failed":
      return "danger";
  }
}
