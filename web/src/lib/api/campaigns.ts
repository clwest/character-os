/**
 * /api/campaigns/ wrapper — B3.7.
 *
 * Backend surface: CampaignViewSet
 * (shell/apps/campaigns/views.py). SESSION B3.7.
 *
 * Covers:
 *   - PersonalizedCampaign list + detail + create + delete
 *   - ParseCsv action (POST /api/campaigns/<id>/parse_csv/)
 *   - Recipients sub-list (GET /api/campaigns/<id>/recipients/)
 *
 * B3.8 will add forecast / launch / retry mutations; they live
 * here when shipped.
 */
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Status enums --------------------------------------------

export const CAMPAIGN_STATUSES = [
  "draft",
  "launching",
  "in_flight",
  "completed",
  "partial",
  "failed",
] as const;
export type CampaignStatus = (typeof CAMPAIGN_STATUSES)[number];

export const RECIPIENT_STATUSES = [
  "pending",
  "queued",
  "running",
  "completed",
  "failed",
] as const;
export type RecipientStatus = (typeof RECIPIENT_STATUSES)[number];

// ---- Zod schemas ---------------------------------------------

export const personalizedRecipientSchema = z.object({
  id: z.string(),
  campaign_id: z.string(),
  variables: z.record(z.string()),
  label: z.string(),
  rendered_script: z.string(),
  position: z.number().int().nonnegative(),
  status: z.enum(RECIPIENT_STATUSES),
  status_label: z.string(),
  produced_composition_id: z.string().nullable(),
  error_message: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type PersonalizedRecipient = z.infer<typeof personalizedRecipientSchema>;

const recipientCountsSchema = z.object({
  pending: z.number().int().nonnegative(),
  queued: z.number().int().nonnegative(),
  running: z.number().int().nonnegative(),
  completed: z.number().int().nonnegative(),
  failed: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
});

export type RecipientCounts = z.infer<typeof recipientCountsSchema>;

export const personalizedCampaignSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  spokesperson_id: z.string(),
  spokesperson_name: z.string(),
  name: z.string(),
  template: z.string(),
  placeholders: z.array(z.string()),
  status: z.enum(CAMPAIGN_STATUSES),
  status_label: z.string(),
  recipient_counts: recipientCountsSchema,
  launched_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type PersonalizedCampaign = z.infer<typeof personalizedCampaignSchema>;

const rejectedRowSchema = z.object({
  row_number: z.number().int(),
  error: z.string(),
  raw: z.string(),
});
export type RejectedRow = z.infer<typeof rejectedRowSchema>;

export const parseCsvResponseSchema = z.object({
  header: z.array(z.string()).optional(),
  valid_count: z.number().int().nonnegative(),
  rejected_count: z.number().int().nonnegative(),
  rejected_rows: z.array(rejectedRowSchema),
  recipients: z.array(personalizedRecipientSchema).optional(),
  // Error-path response (header_error present when backend returns 400)
  header_error: z.string().optional(),
});

export type ParseCsvResponse = z.infer<typeof parseCsvResponseSchema>;

// ---- Fetch helpers -------------------------------------------

/** GET /api/campaigns/?status=<status> */
export async function listCampaigns(params: {
  status?: CampaignStatus;
} = {}): Promise<PersonalizedCampaign[]> {
  const qs = params.status ? `?status=${encodeURIComponent(params.status)}` : "";
  return apiJson(
    `/api/campaigns/${qs}`,
    {},
    (json) => z.array(personalizedCampaignSchema).parse(json),
  );
}

/** GET /api/campaigns/<id>/ */
export async function getCampaign(id: string): Promise<PersonalizedCampaign> {
  return apiJson(
    `/api/campaigns/${encodeURIComponent(id)}/`,
    {},
    (json) => personalizedCampaignSchema.parse(json),
  );
}

/** POST /api/campaigns/ */
export interface CreateCampaignInput {
  workspace_id: string;
  spokesperson_id: string;
  name: string;
  template: string;
}

export async function createCampaign(
  input: CreateCampaignInput,
): Promise<PersonalizedCampaign> {
  return apiJson(
    "/api/campaigns/",
    { method: "POST", body: input },
    (json) => personalizedCampaignSchema.parse(json),
  );
}

/** DELETE /api/campaigns/<id>/ */
export async function deleteCampaign(id: string): Promise<void> {
  await apiJson(`/api/campaigns/${encodeURIComponent(id)}/`, {
    method: "DELETE",
  });
}

/** POST /api/campaigns/<id>/parse_csv/ */
export async function parseCsv(
  campaignId: string,
  csvText: string,
): Promise<ParseCsvResponse> {
  return apiJson(
    `/api/campaigns/${encodeURIComponent(campaignId)}/parse_csv/`,
    { method: "POST", body: { csv_text: csvText } },
    (json) => parseCsvResponseSchema.parse(json),
  );
}

/** GET /api/campaigns/<id>/recipients/ */
export async function listRecipients(
  campaignId: string,
): Promise<PersonalizedRecipient[]> {
  return apiJson(
    `/api/campaigns/${encodeURIComponent(campaignId)}/recipients/`,
    {},
    (json) => z.array(personalizedRecipientSchema).parse(json),
  );
}

// ---- React Query hooks ----------------------------------------

/** Lists all campaigns for the workspace, optionally filtered by status. */
export function useCampaigns(
  _workspaceId: string | undefined,
  filters: { status?: CampaignStatus } = {},
) {
  return useQuery({
    queryKey: ["campaigns", filters.status ?? null],
    queryFn: () => listCampaigns(filters),
    enabled: Boolean(_workspaceId),
    staleTime: 15_000,
  });
}

/** Single campaign detail. Enabled only when id is non-empty. */
export function useCampaign(id: string | undefined) {
  return useQuery({
    queryKey: ["campaign", id ?? null],
    queryFn: () => getCampaign(id!),
    enabled: Boolean(id),
    staleTime: 15_000,
  });
}

/** Mutation for POST /api/campaigns/.
 *  Invalidates the campaigns list on success. */
export function useCreateCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createCampaign,
    onSuccess: () => {
      // Invalidate all status variants of the list so the list
      // page always reflects the new draft on navigation.
      void qc.invalidateQueries({ queryKey: ["campaigns"] });
    },
  });
}

/** Mutation for DELETE /api/campaigns/<id>/.
 *  Invalidates the campaigns list and removes the campaign from
 *  the per-id cache on success. */
export function useDeleteCampaign() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteCampaign,
    onSuccess: (_data, id) => {
      void qc.invalidateQueries({ queryKey: ["campaigns"] });
      qc.removeQueries({ queryKey: ["campaign", id] });
    },
  });
}

/** Mutation for POST /api/campaigns/<id>/parse_csv/.
 *  Invalidates the recipients list for the campaign on success. */
export function useParseCsv(campaignId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (csvText: string) => parseCsv(campaignId!, csvText),
    onSuccess: () => {
      // Refresh the detail + recipients after a new parse so the
      // preview table renders the updated recipient list.
      void qc.invalidateQueries({ queryKey: ["campaign-recipients", campaignId] });
      void qc.invalidateQueries({ queryKey: ["campaign", campaignId] });
    },
  });
}

/** Lists all recipients for a campaign. Enabled only when
 *  campaignId is non-empty. */
export function useRecipients(campaignId: string | undefined) {
  return useQuery({
    queryKey: ["campaign-recipients", campaignId ?? null],
    queryFn: () => listRecipients(campaignId!),
    enabled: Boolean(campaignId),
    staleTime: 15_000,
  });
}

// ---- Display helpers -----------------------------------------

/** Color tone for campaign status badges. Mirrors the B-arc palette. */
export function campaignStatusTone(
  status: CampaignStatus,
): "muted" | "amber" | "success" | "danger" {
  switch (status) {
    case "draft":
      return "muted";
    case "launching":
    case "in_flight":
    case "partial":
      return "amber";
    case "completed":
      return "success";
    case "failed":
      return "danger";
  }
}

/** Human-readable label for a CampaignStatus value. */
export function campaignStatusLabel(status: CampaignStatus): string {
  const MAP: Record<CampaignStatus, string> = {
    draft: "Draft",
    launching: "Launching",
    in_flight: "In Flight",
    completed: "Completed",
    partial: "Partial",
    failed: "Failed",
  };
  return MAP[status] ?? status;
}

/** Color tone for recipient status badges. */
export function recipientStatusTone(
  status: RecipientStatus,
): "muted" | "amber" | "success" | "danger" {
  switch (status) {
    case "pending":
      return "muted";
    case "queued":
    case "running":
      return "amber";
    case "completed":
      return "success";
    case "failed":
      return "danger";
  }
}

/**
 * Extract `{placeholder}` names from a template string.
 * Mirrors the Python regex in character_os/template_renderer.py.
 * Client-side preview only — backend validates again on submit.
 */
export function parsePlaceholders(template: string): string[] {
  // Matches single-brace vars while ignoring doubled-brace escapes.
  // e.g. "{first_name}" → ["first_name"], "{{literal}}" → []
  const out = new Set<string>();
  // Remove escaped doubles first, then collect remaining singles.
  const stripped = template.replace(/\{\{/g, "\x00").replace(/\}\}/g, "\x01");
  const re = /\{([a-zA-Z_][a-zA-Z0-9_]*)\}/g;
  let m: RegExpExecArray | null;
  while ((m = re.exec(stripped)) !== null) {
    out.add(m[1]!);
  }
  return [...out].sort();
}
