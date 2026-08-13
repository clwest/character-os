/**
 * /api/knowledge/preview/ wrapper.
 *
 * F4 (workspace fabric arc). Best-effort preview of what
 * `retrieve_for_spokesperson` would surface for a render given
 * the current operator brief. The recipe form calls this
 * debounced on script edits so the operator can see which
 * docs would inform the LLM-synthesized script before submit.
 *
 * Per F0 contract rule 6 the panel is informative, not
 * blocking — any failure renders as "preview unavailable" and
 * the form still submits.
 */
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "./client";

const previewDocSchema = z.object({
  id: z.string(),
  title: z.string(),
  chunk_count: z.number().int(),
});

const previewSchema = z.object({
  docs_used: z.array(previewDocSchema),
  total_chunks: z.number().int(),
  query_used: z.string(),
  preview_failed: z.boolean().optional(),
});

export type KnowledgePreviewDoc = z.infer<typeof previewDocSchema>;
export type KnowledgePreview = z.infer<typeof previewSchema>;

export interface KnowledgePreviewInput {
  spokesperson: string;
  query: string;
  top_k?: number;
}

export async function previewKnowledge(
  input: KnowledgePreviewInput,
): Promise<KnowledgePreview> {
  return apiJson(
    "/api/knowledge/preview/",
    { method: "POST", body: input },
    (json) => previewSchema.parse(json),
  );
}

/**
 * Hook variant — caller decides when to enable. The recipe
 * form gates this on `use_knowledge` checked + spokesperson
 * picked + query long enough. Query state is debounced
 * upstream; this hook reacts to the already-debounced value.
 */
export function useKnowledgePreview(input: KnowledgePreviewInput | null) {
  return useQuery({
    queryKey: [
      "knowledge-preview",
      input?.spokesperson,
      input?.query,
      input?.top_k,
    ],
    queryFn: () => previewKnowledge(input!),
    enabled: Boolean(input && input.spokesperson && input.query.length >= 8),
    staleTime: 30_000,
    retry: false,
  });
}
