/**
 * /api/scripts/ wrapper — B2.5.
 *
 * Backend surface: ScriptViewSet
 * (shell/apps/scripts/views.py). SESSION B2.5.
 *
 * Covers:
 *   - Script list + detail + create + delete
 *   - Regenerate  (POST /api/scripts/<id>/regenerate/)
 *   - Approve     (POST /api/scripts/<id>/approve/)
 *   - Render      (POST /api/scripts/<id>/render/)
 *   - Clone       (POST /api/scripts/<id>/clone/)
 *
 * Scope: docs/design/AUTO_SCRIPT_V1.md §B2.5.
 *
 * Cache-invalidation discipline (SESSION 203 calibration):
 *   Every mutation invalidates EVERY dependent query key. Missing
 *   even one causes stale UI that survives navigation. The specific
 *   keys for each mutation are documented inline on each hook.
 */
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "./client";
import type { CampaignStatus } from "./campaigns";

// ---- Status enums -----------------------------------------------

export const SCRIPT_STATUSES = [
  "draft",
  "ready",
  "rendered",
  "archived",
] as const;
export type ScriptStatus = (typeof SCRIPT_STATUSES)[number];

export const VERIFICATION_STATUSES = [
  "",
  "verified",
  "warned",
  "skipped",
  "blocked",
  "trusted_passthrough",
] as const;
export type VerificationStatus = (typeof VERIFICATION_STATUSES)[number];

export const VERIFIER_MODES = ["", "strict", "warn", "off"] as const;
export type VerifierMode = (typeof VERIFIER_MODES)[number];

// ---- Zod schemas ------------------------------------------------

const citedDocumentSchema = z.object({
  id: z.string(),
  title: z.string(),
  chunk_count: z.number().int().nonnegative(),
});

export type CitedDocument = z.infer<typeof citedDocumentSchema>;

const verificationWarningSchema = z.object({
  claim: z.string(),
  kind: z.string(),
  position: z.number().int(),
});

export type VerificationWarning = z.infer<typeof verificationWarningSchema>;

const revisionHistoryEntrySchema = z.object({
  ts: z.string(),
  draft_text: z.string(),
  prompt: z.string(),
  opener: z.string(),
  knowledge_chunk_ids: z.array(z.string()),
  model: z.string(),
  verification_status: z.string(),
  verification_warnings: z.array(verificationWarningSchema),
  tokens_input: z.number().int(),
  tokens_output: z.number().int(),
});

export type RevisionHistoryEntry = z.infer<typeof revisionHistoryEntrySchema>;

/**
 * Lite shape returned by the list endpoint.
 * Excludes revision_history, verification_warnings, full
 * knowledge_chunk_ids — those live on the detail shape only.
 */
export const scriptListItemSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  spokesperson_id: z.string(),
  spokesperson_name: z.string(),
  name: z.string(),
  prompt: z.string(),
  opener: z.string(),
  draft_text: z.string(),
  knowledge_chunk_ids: z.array(z.string()),
  model: z.string(),
  tokens_input: z.number().int(),
  tokens_output: z.number().int(),
  verification_status: z.enum(VERIFICATION_STATUSES),
  verification_status_label: z.string(),
  verifier_mode: z.enum(VERIFIER_MODES),
  revision_count: z.number().int().nonnegative(),
  status: z.enum(SCRIPT_STATUSES),
  status_label: z.string(),
  approved_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type ScriptListItem = z.infer<typeof scriptListItemSchema>;

/**
 * Full shape returned by the detail endpoint.
 * Extends the list item with cited_documents, verification_warnings,
 * and revision_history (large fields excluded from the list for perf).
 */
export const scriptDetailSchema = scriptListItemSchema.extend({
  cited_documents: z.array(citedDocumentSchema),
  verification_warnings: z.array(verificationWarningSchema),
  revision_history: z.array(revisionHistoryEntrySchema),
});

export type ScriptDetail = z.infer<typeof scriptDetailSchema>;

/** POST /api/scripts/<id>/render/ response shape. */
export const renderScriptResponseSchema = z.object({
  script: z.lazy(() => scriptDetailSchema),
  composition_id: z.string(),
});

export type RenderScriptResponse = z.infer<typeof renderScriptResponseSchema>;

// ---- Fetch helpers ----------------------------------------------

export interface CreateScriptInput {
  spokesperson_id: string;
  name?: string;
  prompt: string;
  opener?: string;
  verifier_mode?: VerifierMode;
}

/** POST /api/scripts/ */
export async function createScript(
  input: CreateScriptInput,
): Promise<ScriptDetail> {
  return apiJson(
    "/api/scripts/",
    { method: "POST", body: input },
    (json) => scriptDetailSchema.parse(json),
  );
}

export interface ListScriptsParams {
  status?: ScriptStatus;
  spokesperson?: string;
  verification_status?: VerificationStatus;
}

/** GET /api/scripts/?status=&spokesperson=&verification_status= */
export async function listScripts(
  params: ListScriptsParams = {},
): Promise<ScriptListItem[]> {
  const qs = new URLSearchParams();
  if (params.status) qs.set("status", params.status);
  if (params.spokesperson) qs.set("spokesperson", params.spokesperson);
  if (params.verification_status)
    qs.set("verification_status", params.verification_status);
  const suffix = qs.toString() ? `?${qs.toString()}` : "";
  return apiJson(
    `/api/scripts/${suffix}`,
    {},
    (json) => z.array(scriptListItemSchema).parse(json),
  );
}

/** GET /api/scripts/<id>/ */
export async function getScript(id: string): Promise<ScriptDetail> {
  return apiJson(
    `/api/scripts/${encodeURIComponent(id)}/`,
    {},
    (json) => scriptDetailSchema.parse(json),
  );
}

export interface RegenerateScriptInput {
  prompt?: string;
  opener?: string;
  verifier_mode?: VerifierMode;
}

/** POST /api/scripts/<id>/regenerate/ */
export async function regenerateScript(
  id: string,
  input: RegenerateScriptInput = {},
): Promise<ScriptDetail> {
  return apiJson(
    `/api/scripts/${encodeURIComponent(id)}/regenerate/`,
    { method: "POST", body: input },
    (json) => scriptDetailSchema.parse(json),
  );
}

/** POST /api/scripts/<id>/approve/ */
export async function approveScript(id: string): Promise<ScriptDetail> {
  return apiJson(
    `/api/scripts/${encodeURIComponent(id)}/approve/`,
    { method: "POST", body: {} },
    (json) => scriptDetailSchema.parse(json),
  );
}

/** POST /api/scripts/<id>/render/ */
export async function renderScript(
  id: string,
  recipe?: string,
): Promise<RenderScriptResponse> {
  return apiJson(
    `/api/scripts/${encodeURIComponent(id)}/render/`,
    { method: "POST", body: recipe ? { recipe } : {} },
    (json) => renderScriptResponseSchema.parse(json),
  );
}

/** POST /api/scripts/<id>/clone/ */
export async function cloneScript(id: string): Promise<ScriptDetail> {
  return apiJson(
    `/api/scripts/${encodeURIComponent(id)}/clone/`,
    { method: "POST", body: {} },
    (json) => scriptDetailSchema.parse(json),
  );
}

/** DELETE /api/scripts/<id>/ */
export async function deleteScript(id: string): Promise<void> {
  await apiJson(`/api/scripts/${encodeURIComponent(id)}/`, {
    method: "DELETE",
  });
}

// ---- React Query hooks -----------------------------------------

/**
 * Lists scripts for the workspace, optionally filtered.
 * Enabled only when workspaceId is non-empty.
 */
export function useScripts(
  _workspaceId: string | undefined,
  filters: ListScriptsParams = {},
) {
  return useQuery({
    queryKey: ["scripts", filters.status ?? null, filters.spokesperson ?? null, filters.verification_status ?? null],
    queryFn: () => listScripts(filters),
    enabled: Boolean(_workspaceId),
    staleTime: 15_000,
  });
}

/** Single script detail. Enabled only when id is non-empty. */
export function useScript(id: string | undefined) {
  return useQuery({
    queryKey: ["script", id ?? null],
    queryFn: () => getScript(id!),
    enabled: Boolean(id),
    staleTime: 10_000,
  });
}

/**
 * Create a new script. Invalidates the scripts list on success so
 * the list page always reflects the new draft on navigation.
 */
export function useCreateScript() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createScript,
    onSuccess: (script) => {
      // Seed the detail cache so the redirect renders instantly.
      qc.setQueryData(["script", script.id], script);
      // Invalidate ALL filter variants of the list.
      void qc.invalidateQueries({ queryKey: ["scripts"] });
    },
  });
}

/**
 * Regenerate a script draft. Invalidates the detail + list on success
 * because status steps back to DRAFT and revision_count increments.
 */
export function useRegenerateScript(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (input: RegenerateScriptInput) => regenerateScript(id!, input),
    onSuccess: (script) => {
      qc.setQueryData(["script", id], script);
      void qc.invalidateQueries({ queryKey: ["script", id] });
      void qc.invalidateQueries({ queryKey: ["scripts"] });
    },
  });
}

/**
 * Approve a script (DRAFT → READY). Invalidates detail + list so the
 * status pill and action toolbar both update immediately.
 */
export function useApproveScript(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => approveScript(id!),
    onSuccess: (script) => {
      qc.setQueryData(["script", id], script);
      void qc.invalidateQueries({ queryKey: ["script", id] });
      void qc.invalidateQueries({ queryKey: ["scripts"] });
    },
  });
}

/**
 * Render a script (fires auto_script composition). Invalidates the
 * script detail + list so RENDERED status shows immediately.
 * Also invalidates compositions so any composition list pages update.
 */
export function useRenderScript(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (recipe?: string) => renderScript(id!, recipe),
    onSuccess: (result) => {
      qc.setQueryData(["script", id], result.script);
      void qc.invalidateQueries({ queryKey: ["script", id] });
      void qc.invalidateQueries({ queryKey: ["scripts"] });
      // Invalidate compositions so the asset list refreshes after render.
      void qc.invalidateQueries({ queryKey: ["compositions"] });
    },
  });
}

/**
 * Clone a script. Invalidates the scripts list so the new draft
 * appears immediately.
 */
export function useCloneScript(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => cloneScript(id!),
    onSuccess: (newScript) => {
      qc.setQueryData(["script", newScript.id], newScript);
      void qc.invalidateQueries({ queryKey: ["scripts"] });
    },
  });
}

/**
 * Delete a script. Invalidates the list and removes the per-id cache
 * entry on success.
 */
export function useDeleteScript(id: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => deleteScript(id!),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["scripts"] });
      qc.removeQueries({ queryKey: ["script", id] });
    },
  });
}

// ---- Display helpers -------------------------------------------

/** Color tone for script status badges. Mirrors the B-arc / C-arc palette. */
export function scriptStatusTone(
  status: ScriptStatus,
): "muted" | "amber" | "success" | "danger" {
  switch (status) {
    case "draft":
      return "muted";
    case "ready":
      return "amber";
    case "rendered":
      return "success";
    case "archived":
      return "muted";
  }
}

/** Human-readable label for a ScriptStatus value. */
export function scriptStatusLabel(status: ScriptStatus): string {
  const MAP: Record<ScriptStatus, string> = {
    draft: "Draft",
    ready: "Approved",
    rendered: "Rendered",
    archived: "Archived",
  };
  return MAP[status] ?? status;
}

/** Color tone for verification status badges. */
export function verificationStatusTone(
  status: VerificationStatus,
): "muted" | "amber" | "success" | "danger" {
  switch (status) {
    case "verified":
    case "trusted_passthrough":
      return "success";
    case "warned":
      return "amber";
    case "blocked":
      return "danger";
    case "skipped":
    case "":
      return "muted";
  }
}

// ---- BC4: derived campaigns hook --------------------------------

/**
 * Shape of each row returned by
 * GET /api/scripts/<id>/derived_campaigns/.
 * Mirrors PersonalizedCampaign list shape (subset).
 */
export const derivedCampaignRowSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.enum([
    "draft",
    "launching",
    "in_flight",
    "completed",
    "partial",
    "failed",
  ] as const),
  recipient_count: z.number().int().nonnegative(),
  spokesperson_name: z.string().nullable(),
  created_at: z.string(),
  launched_at: z.string().nullable(),
});

export type DerivedCampaignRow = z.infer<typeof derivedCampaignRowSchema>;

/**
 * GET /api/scripts/<id>/derived_campaigns/
 * Optional ?status= filter mirrors the /api/campaigns/ shape.
 * Backend caps at 100 rows.
 */
export async function getDerivedCampaigns(
  scriptId: string,
  params: { status?: CampaignStatus } = {},
): Promise<DerivedCampaignRow[]> {
  const qs = params.status
    ? `?status=${encodeURIComponent(params.status)}`
    : "";
  return apiJson(
    `/api/scripts/${encodeURIComponent(scriptId)}/derived_campaigns/${qs}`,
    {},
    (json) => z.array(derivedCampaignRowSchema).parse(json),
  );
}

/**
 * React Query hook for a Script's derived Campaign list.
 * Enabled only when scriptId is non-empty.
 */
export function useDerivedCampaigns(
  scriptId: string | undefined,
  params: { status?: CampaignStatus } = {},
) {
  return useQuery({
    queryKey: ["script-derived-campaigns", scriptId ?? null, params.status ?? null],
    queryFn: () => getDerivedCampaigns(scriptId!, params),
    enabled: Boolean(scriptId),
    staleTime: 15_000,
  });
}

/** Human-readable label for a VerificationStatus value. */
export function verificationStatusLabel(status: VerificationStatus): string {
  const MAP: Record<VerificationStatus, string> = {
    "": "—",
    verified: "Verified",
    warned: "Warned",
    skipped: "Skipped",
    blocked: "Blocked",
    trusted_passthrough: "Trusted",
  };
  return MAP[status] ?? status;
}
