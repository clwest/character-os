/**
 * /api/transcript_highlights/ wrapper — B1.5.
 *
 * Backend surface: TranscriptHighlightViewSet
 * (shell/apps/transcripts/views.py). SESSION 202 / B1.5.
 *
 * Covers:
 *   - Transcript list (reuses useWorkspaceAssets with asset_type=transcript)
 *   - Single transcript detail (reuses getWorkspaceAsset)
 *   - TranscriptHighlight list (GET /api/transcript_highlights/)
 *   - Mine mutation (POST /api/transcript_highlights/mine/)
 *
 * B1.6 will add approve/reject mutations; they live here when shipped.
 */
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "./client";
import {
  useWorkspaceAssets,
  useWorkspaceAsset,
  type WorkspaceAssetsParams,
} from "./workspace-assets";

// ---- Re-export transcript-as-asset helpers --------------------
// The list view needs transcript assets from the existing endpoint.
// Callers import these rather than reaching into workspace-assets.

export { useWorkspaceAsset as useTranscript, useWorkspaceAssets };

/** Fetch transcript assets for the workspace.
 *  Thin wrapper that pre-sets asset_type=transcript so callers don't
 *  repeat themselves. Extra params (workspace, q, etc.) pass through. */
export function useTranscripts(params: Omit<WorkspaceAssetsParams, "asset_type"> = {}) {
  return useWorkspaceAssets({ ...params, asset_type: ["transcript"] });
}

// ---- Highlight status -----------------------------------------

/** Mirrors TranscriptHighlight.Status TextChoices (lowercase values). */
export const HIGHLIGHT_STATUSES = [
  "pending",
  "approved",
  "rejected",
  "rendered",
] as const;
export type HighlightStatus = (typeof HIGHLIGHT_STATUSES)[number];

// ---- Zod schemas ----------------------------------------------

export const transcriptHighlightSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  source_transcript_id: z.string(),
  text: z.string(),
  char_start: z.number(),
  char_end: z.number(),
  llm_reasoning: z.string(),
  status: z.enum(HIGHLIGHT_STATUSES),
  status_label: z.string(),
  produced_composition_id: z.string().nullable(),
  rejection_reason: z.string(),
  mined_at: z.string(),
  decided_at: z.string().nullable(),
  llm_model_id: z.string(),
  llm_cost_micros: z.number(),
  llm_tokens_input: z.number(),
  llm_tokens_output: z.number(),
});

export type TranscriptHighlight = z.infer<typeof transcriptHighlightSchema>;

export const mineResponseSchema = z.object({
  highlights: z.array(transcriptHighlightSchema),
  used_synthesis: z.boolean(),
  model: z.string(),
});

export type MineResponse = z.infer<typeof mineResponseSchema>;

export interface MineRequest {
  transcript_asset_id: string;
  /** Number of highlights to request. Clamped 1-10 server-side. Default: 5. */
  target_count?: number;
  /** Max characters per highlight. Clamped 50-280 server-side. Default: 280. */
  max_chars?: number;
}

// ---- Fetch helpers --------------------------------------------

/** GET /api/transcript_highlights/?source_transcript=<id> */
export async function listHighlightsForTranscript(
  transcriptId: string,
): Promise<TranscriptHighlight[]> {
  return apiJson(
    `/api/transcript_highlights/?source_transcript=${encodeURIComponent(transcriptId)}`,
    {},
    (json) => z.array(transcriptHighlightSchema).parse(json),
  );
}

/** POST /api/transcript_highlights/mine/ */
export async function mineTranscript(
  body: MineRequest,
): Promise<MineResponse> {
  return apiJson(
    "/api/transcript_highlights/mine/",
    { method: "POST", body },
    (json) => mineResponseSchema.parse(json),
  );
}

// ---- React Query hooks ----------------------------------------

/** Lists all highlights for a single transcript. Enabled only when
 *  transcriptId is non-empty. */
export function useHighlightsForTranscript(transcriptId: string | undefined) {
  return useQuery({
    queryKey: ["transcript-highlights", transcriptId ?? null],
    queryFn: () => listHighlightsForTranscript(transcriptId!),
    enabled: Boolean(transcriptId),
    staleTime: 15_000,
  });
}

/** Mutation for POST /api/transcript_highlights/mine/.
 *  Invalidates the highlights list for the transcript on success. */
export function useMineTranscript() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: mineTranscript,
    onSuccess: (_data, variables) => {
      // Invalidate the highlights list so the detail page re-fetches.
      void qc.invalidateQueries({
        queryKey: ["transcript-highlights", variables.transcript_asset_id],
      });
    },
  });
}

// ---- Display helpers ------------------------------------------

/** Human-readable label for a HighlightStatus value. */
export function highlightStatusLabel(status: HighlightStatus): string {
  const MAP: Record<HighlightStatus, string> = {
    pending: "Pending",
    approved: "Approved",
    rejected: "Rejected",
    rendered: "Rendered",
  };
  return MAP[status] ?? status;
}

/**
 * Tone for highlight status badges.
 * Mirrors the storage-health palette from workspace-assets.ts.
 */
export function highlightStatusTone(
  status: HighlightStatus,
): "amber" | "success" | "muted" | "danger" {
  switch (status) {
    case "pending":
      return "amber";
    case "approved":
      return "success";
    case "rejected":
      return "muted";
    case "rendered":
      return "success";
  }
}
