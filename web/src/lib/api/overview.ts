/**
 * /api/workspace/overview/ wrapper.
 *
 * F3 (workspace fabric arc). Cross-cut endpoint that powers
 * the dashboard's activity feed + knowledge corpus stats +
 * spokesperson badges. Single-roundtrip aggregate over
 * Composition, KnowledgeDocument, and Spokesperson.
 */
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "./client";

const overviewSpokespersonSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  tone_archetype: z.string(),
  runway_avatar_id: z.string(),
  portrait_path: z.string(),
  composition_count: z.number().int(),
  attached_docs_count: z.number().int(),
});

const overviewKnowledgeMostRecentSchema = z.object({
  id: z.string(),
  title: z.string(),
  document_type: z.string(),
  ingested_via: z.string(),
  created_at: z.string(),
});

const overviewKnowledgeSchema = z.object({
  doc_count: z.number().int(),
  chunk_count: z.number().int(),
  source_mix: z.record(z.string(), z.number().int()),
  most_recent: overviewKnowledgeMostRecentSchema.nullable(),
});

const overviewCompositionSchema = z.object({
  id: z.string(),
  name: z.string(),
  template_kind: z.string(),
  status: z.enum([
    "draft",
    "planning",
    "running",
    "partial",
    "completed",
    "failed",
  ]),
  spokesperson_id: z.string(),
  spokesperson_name: z.string(),
  mock_mode: z.boolean(),
  cost_actual_micros: z.number().int(),
  created_at: z.string(),
});

const overviewCompositionsSchema = z.object({
  running_count: z.number().int(),
  total_count: z.number().int(),
  total_cost_micros: z.number().int(),
  recent: z.array(overviewCompositionSchema),
});

// K7.1 (SESSION 174) — per-surface + MTD cost rollup. Pre-K7.1
// servers omit ``cost_breakdown`` entirely; the schema makes it
// optional so the SPA still parses against an older backend
// without a hard failure.
const overviewCostBreakdownSchema = z.object({
  compositions_micros: z.number().int(),
  images_micros: z.number().int(),
  realtime_micros: z.number().int(),
  total_micros: z.number().int(),
  mtd_micros: z.number().int(),
  mtd_compositions_micros: z.number().int(),
  mtd_images_micros: z.number().int(),
  mtd_realtime_micros: z.number().int(),
  month_start: z.string(),
});

export type OverviewCostBreakdown = z.infer<typeof overviewCostBreakdownSchema>;

const overviewSchema = z.object({
  workspace: z.object({
    id: z.string(),
    name: z.string(),
    slug: z.string(),
  }),
  spokespeople: z.array(overviewSpokespersonSchema),
  knowledge: overviewKnowledgeSchema,
  compositions: overviewCompositionsSchema,
  cost_breakdown: overviewCostBreakdownSchema.optional(),
});

export type WorkspaceOverview = z.infer<typeof overviewSchema>;
export type OverviewSpokesperson = z.infer<typeof overviewSpokespersonSchema>;
export type OverviewComposition = z.infer<typeof overviewCompositionSchema>;

export async function getWorkspaceOverview(
  workspaceId?: string,
): Promise<WorkspaceOverview> {
  const path = workspaceId
    ? `/api/workspace/overview/?workspace=${workspaceId}`
    : "/api/workspace/overview/";
  return apiJson(path, {}, (json) => overviewSchema.parse(json));
}

export function useWorkspaceOverview(workspaceId?: string) {
  return useQuery({
    queryKey: ["workspace-overview", workspaceId],
    queryFn: () => getWorkspaceOverview(workspaceId),
    // Refresh every 5s — running compositions move through
    // states quickly in mock mode and the feed should reflect
    // that without manual reload. Background-only refetch is
    // disabled so we don't burn requests when the tab is
    // hidden.
    refetchInterval: 5_000,
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}
