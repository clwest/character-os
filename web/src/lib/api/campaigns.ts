/**
 * /api/campaigns/ wrapper — B3.7 + B3.8.
 *
 * Backend surface: CampaignViewSet
 * (shell/apps/campaigns/views.py). SESSION B3.7 / B3.8.
 *
 * Covers:
 *   - PersonalizedCampaign list + detail + create + delete
 *   - ParseCsv action (POST /api/campaigns/<id>/parse_csv/)
 *   - Recipients sub-list (GET /api/campaigns/<id>/recipients/)
 *   - Forecast (GET /api/campaigns/<id>/forecast/)         [B3.8]
 *   - Launch  (POST /api/campaigns/<id>/launch/)           [B3.8]
 *   - Retry   (POST /api/campaigns/<id>/retry_recipient/)  [B3.8]
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

// ---- BC4: source_script block schema -------------------------

/**
 * Nullable block returned by GET /api/campaigns/<id>/ when the
 * campaign was derived from an approved Script. Mirrors the
 * SerializerMethodField on PersonalizedCampaignSerializer.
 * BC3 ships the backend; BC4 wires the SPA.
 */
export const sourceScriptBlockSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.enum(["draft", "ready", "rendered", "archived"] as const),
  verification_status: z.string(), // loose — mirrors VerificationStatus
  chunk_count: z.number().int().nonnegative(),
});

export type SourceScriptBlock = z.infer<typeof sourceScriptBlockSchema>;

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
  // BC4 — nullable FK block. Present on detail; may be absent on list items
  // that predate the BC3 migration. z.undefined() fallback covers that.
  source_script: sourceScriptBlockSchema.nullable().optional(),
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
  /**
   * Now optional — BC4. If omitted and source_script_id is provided,
   * the server back-fills template from script.draft_text. At least one
   * of template / source_script_id must be present (server validates).
   */
  template?: string;
  /**
   * BC4 — optional. If set, the Campaign derives from this approved Script
   * (must be READY or RENDERED and in the same workspace). The source_script
   * FK is set at create time and immutable thereafter (Q-bc-3 resolved by
   * absence — no SPA control for post-create mutation).
   */
  source_script_id?: string;
}

export async function createCampaign(
  input: CreateCampaignInput,
): Promise<PersonalizedCampaign> {
  // Only send defined fields. Don't send template: "" when omitted — the
  // backend serializer treats an empty string as "missing template" for the
  // cross-field validation (at least one of template / source_script_id).
  const body: Record<string, unknown> = {
    workspace_id: input.workspace_id,
    spokesperson_id: input.spokesperson_id,
    name: input.name,
  };
  if (input.template !== undefined && input.template !== "") {
    body.template = input.template;
  }
  if (input.source_script_id) {
    body.source_script_id = input.source_script_id;
  }
  return apiJson(
    "/api/campaigns/",
    { method: "POST", body },
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

/** Single campaign detail. Enabled only when id is non-empty.
 *  Polls every 5 s while the campaign is LAUNCHING or IN_FLIGHT
 *  (the Celery worker updates status asynchronously). Stops on
 *  any terminal state per the videos.ts refetchInterval pattern.
 */
export function useCampaign(id: string | undefined) {
  return useQuery({
    queryKey: ["campaign", id ?? null],
    queryFn: () => getCampaign(id!),
    enabled: Boolean(id),
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const active: CampaignStatus[] = ["launching", "in_flight"];
      return active.includes(data.status) ? 5_000 : false;
    },
    refetchIntervalInBackground: false,
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
      // Refresh the detail + recipients + forecast after a new
      // parse. The forecast is the load-bearing one for the
      // operator's "is this launchable?" decision — without
      // this invalidation the panel shows 0 recipients +
      // $0.00 total after a successful paste.
      void qc.invalidateQueries({ queryKey: ["campaign-recipients", campaignId] });
      void qc.invalidateQueries({ queryKey: ["campaign", campaignId] });
      void qc.invalidateQueries({ queryKey: ["campaign-forecast", campaignId] });
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

// ---- B3.8: Forecast / Launch / Retry schemas ----------------

/** Structured blocking_reason from the forecast endpoint. */
export const blockingReasonSchema = z.object({
  code: z.enum([
    "no_recipients",
    "campaign_not_draft",
    "personalized_batch_too_large",
    "video_limit_reached",
  ]),
  message: z.string(),
});
export type BlockingReason = z.infer<typeof blockingReasonSchema>;

/** GET /api/campaigns/<id>/forecast/ response. */
export const forecastSchema = z.object({
  recipient_count: z.number().int().nonnegative(),
  batch_cap: z.number().int().nonnegative().nullable(),
  videos_per_month_limit: z.number().int().nonnegative().nullable(),
  videos_used_this_month: z.number().int().nonnegative(),
  videos_remaining: z.number().int().nonnegative().nullable(),
  projected_cost_micros: z.number().int().nonnegative(),
  per_recipient_cost_micros: z.number().int().nonnegative(),
  ready_to_launch: z.boolean(),
  blocking_reason: blockingReasonSchema.nullable(),
});
export type CampaignForecast = z.infer<typeof forecastSchema>;

/** POST /api/campaigns/<id>/launch/ success response. */
export const launchResponseSchema = z.object({
  campaign: z.lazy(() => personalizedCampaignSchema),
  queued_count: z.number().int().nonnegative(),
  failed_at_render_count: z.number().int().nonnegative(),
});
export type LaunchResponse = z.infer<typeof launchResponseSchema>;

/** POST /api/campaigns/<id>/retry_recipient/ success response. */
export const retryResponseSchema = z.object({
  recipient: z.lazy(() => personalizedRecipientSchema),
  campaign_status: z.enum(CAMPAIGN_STATUSES),
});
export type RetryResponse = z.infer<typeof retryResponseSchema>;

// ---- B3.8 fetch helpers --------------------------------------

/** GET /api/campaigns/<id>/forecast/ */
export async function getCampaignForecast(
  campaignId: string,
): Promise<CampaignForecast> {
  return apiJson(
    `/api/campaigns/${encodeURIComponent(campaignId)}/forecast/`,
    {},
    (json) => forecastSchema.parse(json),
  );
}

/** POST /api/campaigns/<id>/launch/ */
export async function launchCampaign(
  campaignId: string,
): Promise<LaunchResponse> {
  return apiJson(
    `/api/campaigns/${encodeURIComponent(campaignId)}/launch/`,
    { method: "POST" },
    (json) => launchResponseSchema.parse(json),
  );
}

/** POST /api/campaigns/<id>/retry_recipient/ */
export async function retryRecipient(
  campaignId: string,
  recipientId: string,
): Promise<RetryResponse> {
  return apiJson(
    `/api/campaigns/${encodeURIComponent(campaignId)}/retry_recipient/`,
    { method: "POST", body: { recipient_id: recipientId } },
    (json) => retryResponseSchema.parse(json),
  );
}

// ---- B3.8 React Query hooks ----------------------------------

/** Cost forecast for the launch modal. Re-fetches on mount. */
export function useCampaignForecast(campaignId: string | undefined) {
  return useQuery({
    queryKey: ["campaign-forecast", campaignId ?? null],
    queryFn: () => getCampaignForecast(campaignId!),
    enabled: Boolean(campaignId),
    staleTime: 10_000,
  });
}

/**
 * Launch a campaign. Invalidates detail + recipients queries on
 * success so the SPA immediately renders the IN_FLIGHT view.
 */
export function useLaunchCampaign(campaignId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => launchCampaign(campaignId!),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["campaign", campaignId] });
      void qc.invalidateQueries({ queryKey: ["campaign-recipients", campaignId] });
      void qc.invalidateQueries({ queryKey: ["campaign-forecast", campaignId] });
    },
  });
}

/**
 * Retry a single FAILED recipient. Invalidates the campaign +
 * recipients cache on success so the row flips to QUEUED.
 */
export function useRetryRecipient(campaignId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (recipientId: string) => retryRecipient(campaignId!, recipientId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["campaign", campaignId] });
      void qc.invalidateQueries({ queryKey: ["campaign-recipients", campaignId] });
    },
  });
}

// ---- B3.8 display helpers -----------------------------------

/** Human-readable explanation for a blocking_reason code. */
export function blockingReasonMessage(code: BlockingReason["code"]): string {
  switch (code) {
    case "no_recipients":
      return "Add recipients by pasting a CSV before launching.";
    case "campaign_not_draft":
      return "Only DRAFT campaigns can be launched.";
    case "personalized_batch_too_large":
      return "Batch exceeds your tier's per-launch limit. Remove recipients or upgrade.";
    case "video_limit_reached":
      return "You have reached your monthly video limit. Upgrade to launch more.";
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
