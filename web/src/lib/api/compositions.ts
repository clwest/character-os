/**
 * /api/compositions/ — paginated list client for the Videos library.
 *
 * SESSION 209 — Path A. Backend list endpoint paginates via
 * ``PageNumberPagination`` (default 25/page, max 100). Detail and
 * create flows go through other modules (recipes.ts, compositions/$id).
 */
import { z } from "zod";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { apiJson } from "./client";

export const COMPOSITION_STATUSES = [
  "draft",
  "planning",
  "running",
  "partial",
  "completed",
  "failed",
] as const;
export type CompositionStatus = (typeof COMPOSITION_STATUSES)[number];

export const VERIFICATION_STATUSES = [
  "",
  "verified",
  "warn",
  "rejected",
  "trusted_passthrough",
] as const;
export type VerificationStatus = (typeof VERIFICATION_STATUSES)[number];

export const compositionListItemSchema = z.object({
  id: z.string(),
  name: z.string(),
  template_kind: z.string(),
  status: z.enum(COMPOSITION_STATUSES),
  mock_mode: z.boolean(),
  cost_actual_micros: z.number().int(),
  verification_status: z.enum(VERIFICATION_STATUSES),
  spokesperson_id: z.string().nullable(),
  spokesperson_name: z.string(),
  final_asset_id: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type CompositionListItem = z.infer<typeof compositionListItemSchema>;

export const paginatedCompositionsSchema = z.object({
  count: z.number().int().nonnegative(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(compositionListItemSchema),
});

export type PaginatedCompositions = z.infer<typeof paginatedCompositionsSchema>;

export interface ListCompositionsParams {
  workspace?: string;
  spokesperson?: string;
  status?: CompositionStatus;
  page?: number;
  page_size?: number;
}

export async function listCompositions(
  params: ListCompositionsParams = {},
): Promise<PaginatedCompositions> {
  const qs = new URLSearchParams();
  if (params.workspace) qs.set("workspace", params.workspace);
  if (params.spokesperson) qs.set("spokesperson", params.spokesperson);
  if (params.status) qs.set("status", params.status);
  if (params.page && params.page > 1) qs.set("page", String(params.page));
  if (params.page_size) qs.set("page_size", String(params.page_size));
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiJson(
    `/api/compositions/${suffix}`,
    {},
    (json) => paginatedCompositionsSchema.parse(json),
  );
}

export function useCompositions(params: ListCompositionsParams = {}) {
  return useQuery({
    queryKey: ["compositions", params],
    queryFn: () => listCompositions(params),
    placeholderData: keepPreviousData,
    refetchInterval: 5_000,
    refetchIntervalInBackground: false,
  });
}
