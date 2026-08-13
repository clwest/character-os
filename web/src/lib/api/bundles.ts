/**
 * /api/publish_bundles/ wrapper — B14.4.
 *
 * Backend surface: PublishBundleViewSet
 * (shell/apps/publish/views.py). SESSION B14.4.
 *
 * Covers:
 *   - PublishBundle list + detail + create + delete
 *   - Variants sub-list (GET /api/publish_bundles/<id>/variants/)
 *   - Forecast (GET /api/publish_bundles/<id>/forecast/)
 *   - Launch  (POST /api/publish_bundles/<id>/launch/)
 *   - Retry   (POST /api/publish_bundles/<id>/retry_variant/)
 *
 * Scope: docs/design/PUBLISH_BUNDLE_V1.md §B14.4.
 */
import { z } from "zod";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Platform catalog (rule 7 — closed v1, mirrored client-side) ----

/**
 * Client-side mirror of apps/compositions/platform_catalog.py.
 * Rule 7: catalog is closed v1 — no /api/platforms/ endpoint.
 * Update here when the backend catalog changes.
 */
export const PLATFORM_CATALOG = [
  {
    key: "reels",
    display: "Instagram Reels",
    target_ratio: "720:1280",
    max_duration_ms: 60000,
  },
  {
    key: "shorts",
    display: "YouTube Shorts",
    target_ratio: "720:1280",
    max_duration_ms: 60000,
  },
  {
    key: "tiktok",
    display: "TikTok",
    target_ratio: "720:1280",
    max_duration_ms: 90000,
  },
  {
    key: "x_twitter",
    display: "X / Twitter",
    target_ratio: "1280:720",
    max_duration_ms: 140000,
  },
  {
    key: "linkedin",
    display: "LinkedIn",
    target_ratio: "1280:720",
    max_duration_ms: 30000,
  },
] as const;

export type PlatformKey = (typeof PLATFORM_CATALOG)[number]["key"];

/** Look up display name for a platform key. Falls back gracefully. */
export function platformDisplay(key: string): string {
  const found = PLATFORM_CATALOG.find((p) => p.key === key);
  return found?.display ?? key;
}

/** Format max_duration_ms as a human-readable seconds string. */
export function formatDurationS(ms: number): string {
  return `${Math.round(ms / 1000)}s`;
}

// ---- Status enums -----------------------------------------------

export const BUNDLE_STATUSES = [
  "draft",
  "launching",
  "in_flight",
  "completed",
  "partial",
  "failed",
] as const;
export type BundleStatus = (typeof BUNDLE_STATUSES)[number];

export const VARIANT_STATUSES = [
  "pending",
  "queued",
  "running",
  "completed",
  "failed",
] as const;
export type VariantStatus = (typeof VARIANT_STATUSES)[number];

// ---- Zod schemas ------------------------------------------------

const variantCountsSchema = z.object({
  pending: z.number().int().nonnegative(),
  queued: z.number().int().nonnegative(),
  running: z.number().int().nonnegative(),
  completed: z.number().int().nonnegative(),
  failed: z.number().int().nonnegative(),
  total: z.number().int().nonnegative(),
});

export type VariantCounts = z.infer<typeof variantCountsSchema>;

export const publishBundleSchema = z.object({
  id: z.string(),
  workspace_id: z.string(),
  source_clip_id: z.string(),
  name: z.string(),
  selected_platforms: z.array(z.string()),
  status: z.enum(BUNDLE_STATUSES),
  status_label: z.string(),
  variant_counts: variantCountsSchema,
  launched_at: z.string().nullable(),
  completed_at: z.string().nullable(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type PublishBundle = z.infer<typeof publishBundleSchema>;

export const publishVariantSchema = z.object({
  id: z.string(),
  bundle_id: z.string(),
  platform_key: z.string(),
  target_ratio: z.string(),
  max_duration_ms: z.number().int().nonnegative(),
  status: z.enum(VARIANT_STATUSES),
  status_label: z.string(),
  produced_composition_id: z.string().nullable(),
  error_message: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type PublishVariant = z.infer<typeof publishVariantSchema>;

/** Structured blocking_reason from the forecast endpoint. */
export const bundleBlockingReasonSchema = z.object({
  code: z.enum(["no_variants", "bundle_not_draft", "platforms_invalid"]),
  message: z.string(),
});
export type BundleBlockingReason = z.infer<typeof bundleBlockingReasonSchema>;

/** GET /api/publish_bundles/<id>/forecast/ response. */
export const bundleForecastSchema = z.object({
  variant_count: z.number().int().nonnegative(),
  projected_cost_micros: z.number().int().nonnegative(),
  estimated_wall_time_s: z.number(),
  ready_to_launch: z.boolean(),
  blocking_reason: bundleBlockingReasonSchema.nullable(),
});
export type BundleForecast = z.infer<typeof bundleForecastSchema>;

/** POST /api/publish_bundles/<id>/launch/ success response. */
export const launchResponseSchema = z.object({
  bundle: z.lazy(() => publishBundleSchema),
  queued_count: z.number().int().nonnegative(),
  failed_at_start_count: z.number().int().nonnegative(),
});
export type LaunchResponse = z.infer<typeof launchResponseSchema>;

/** POST /api/publish_bundles/<id>/retry_variant/ success response. */
export const retryResponseSchema = z.object({
  variant: z.lazy(() => publishVariantSchema),
  bundle_status: z.enum(BUNDLE_STATUSES),
});
export type RetryResponse = z.infer<typeof retryResponseSchema>;

// ---- Fetch helpers ---------------------------------------------

/** GET /api/publish_bundles/?status=<status> */
export async function listBundles(params: {
  status?: BundleStatus;
} = {}): Promise<PublishBundle[]> {
  const qs = params.status ? `?status=${encodeURIComponent(params.status)}` : "";
  return apiJson(
    `/api/publish_bundles/${qs}`,
    {},
    (json) => z.array(publishBundleSchema).parse(json),
  );
}

/** GET /api/publish_bundles/<id>/ */
export async function getBundle(id: string): Promise<PublishBundle> {
  return apiJson(
    `/api/publish_bundles/${encodeURIComponent(id)}/`,
    {},
    (json) => publishBundleSchema.parse(json),
  );
}

/** GET /api/publish_bundles/<id>/variants/ */
export async function listBundleVariants(
  bundleId: string,
): Promise<PublishVariant[]> {
  return apiJson(
    `/api/publish_bundles/${encodeURIComponent(bundleId)}/variants/`,
    {},
    (json) => z.array(publishVariantSchema).parse(json),
  );
}

/** GET /api/publish_bundles/<id>/forecast/ */
export async function getBundleForecast(
  bundleId: string,
): Promise<BundleForecast> {
  return apiJson(
    `/api/publish_bundles/${encodeURIComponent(bundleId)}/forecast/`,
    {},
    (json) => bundleForecastSchema.parse(json),
  );
}

/** POST /api/publish_bundles/ */
export interface CreateBundleInput {
  source_clip_id: string;
  name: string;
  selected_platforms: string[];
}

export async function createBundle(
  input: CreateBundleInput,
): Promise<PublishBundle> {
  return apiJson(
    "/api/publish_bundles/",
    { method: "POST", body: input },
    (json) => publishBundleSchema.parse(json),
  );
}

/** DELETE /api/publish_bundles/<id>/ */
export async function deleteBundle(id: string): Promise<void> {
  await apiJson(`/api/publish_bundles/${encodeURIComponent(id)}/`, {
    method: "DELETE",
  });
}

/** POST /api/publish_bundles/<id>/launch/ */
export async function launchBundle(bundleId: string): Promise<LaunchResponse> {
  return apiJson(
    `/api/publish_bundles/${encodeURIComponent(bundleId)}/launch/`,
    { method: "POST" },
    (json) => launchResponseSchema.parse(json),
  );
}

/** POST /api/publish_bundles/<id>/retry_variant/ */
export async function retryVariant(
  bundleId: string,
  variantId: string,
): Promise<RetryResponse> {
  return apiJson(
    `/api/publish_bundles/${encodeURIComponent(bundleId)}/retry_variant/`,
    { method: "POST", body: { variant_id: variantId } },
    (json) => retryResponseSchema.parse(json),
  );
}

// ---- React Query hooks -----------------------------------------

/** Lists all bundles for the workspace, optionally filtered by status. */
export function useBundles(
  _workspaceId: string | undefined,
  filters: { status?: BundleStatus } = {},
) {
  return useQuery({
    queryKey: ["bundles", filters.status ?? null],
    queryFn: () => listBundles(filters),
    enabled: Boolean(_workspaceId),
    staleTime: 15_000,
  });
}

/** Single bundle detail. Polls every 5s while LAUNCHING or IN_FLIGHT.
 *  Stops on any terminal state. Mirrors useCampaign exactly. */
export function useBundle(id: string | undefined) {
  return useQuery({
    queryKey: ["bundle", id ?? null],
    queryFn: () => getBundle(id!),
    enabled: Boolean(id),
    staleTime: 0,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;
      const active: BundleStatus[] = ["launching", "in_flight"];
      return active.includes(data.status) ? 5_000 : false;
    },
    refetchIntervalInBackground: false,
  });
}

/** Per-variant list for the SPA progress grid. */
export function useBundleVariants(bundleId: string | undefined) {
  return useQuery({
    queryKey: ["bundle-variants", bundleId ?? null],
    queryFn: () => listBundleVariants(bundleId!),
    enabled: Boolean(bundleId),
    staleTime: 10_000,
  });
}

/** Cost/time forecast for the launch modal. Re-fetches on mount. */
export function useBundleForecast(bundleId: string | undefined) {
  return useQuery({
    queryKey: ["bundle-forecast", bundleId ?? null],
    queryFn: () => getBundleForecast(bundleId!),
    enabled: Boolean(bundleId),
    staleTime: 10_000,
  });
}

/** Mutation for POST /api/publish_bundles/.
 *  Invalidates the bundles list on success. */
export function useCreateBundle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createBundle,
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["bundles"] });
    },
  });
}

/** Mutation for DELETE /api/publish_bundles/<id>/.
 *  Invalidates the bundles list and removes the per-id cache entry. */
export function useDeleteBundle() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteBundle,
    onSuccess: (_data, id) => {
      void qc.invalidateQueries({ queryKey: ["bundles"] });
      qc.removeQueries({ queryKey: ["bundle", id] });
    },
  });
}

/**
 * Launch a bundle. Invalidates detail + variants + forecast on success
 * so the SPA immediately renders the IN_FLIGHT view.
 *
 * Critical: all three keys are invalidated — session 203 calibration
 * (B-3 forecast cache miss bit) showed that missing the forecast
 * invalidation leaves stale "ready_to_launch=true" in the panel after
 * the bundle moves to IN_FLIGHT.
 */
export function useLaunchBundle(bundleId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: () => launchBundle(bundleId!),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["bundle", bundleId] });
      void qc.invalidateQueries({ queryKey: ["bundle-variants", bundleId] });
      void qc.invalidateQueries({ queryKey: ["bundle-forecast", bundleId] });
    },
  });
}

/**
 * Retry a single FAILED variant. Same triple-invalidation as launch —
 * the bundle status can change (terminal → IN_FLIGHT) and the forecast
 * ready_to_launch state must update too.
 */
export function useRetryVariant(bundleId: string | undefined) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (variantId: string) => retryVariant(bundleId!, variantId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ["bundle", bundleId] });
      void qc.invalidateQueries({ queryKey: ["bundle-variants", bundleId] });
      void qc.invalidateQueries({ queryKey: ["bundle-forecast", bundleId] });
    },
  });
}

// ---- Display helpers -------------------------------------------

/** Color tone for bundle status badges. Mirrors the B-arc / C-arc palette. */
export function bundleStatusTone(
  status: BundleStatus,
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

/** Human-readable label for a BundleStatus value. */
export function bundleStatusLabel(status: BundleStatus): string {
  const MAP: Record<BundleStatus, string> = {
    draft: "Draft",
    launching: "Launching",
    in_flight: "In Flight",
    completed: "Completed",
    partial: "Partial",
    failed: "Failed",
  };
  return MAP[status] ?? status;
}

/** Color tone for variant status badges. */
export function variantStatusTone(
  status: VariantStatus,
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

/** Human-readable explanation for a blocking_reason code. */
export function blockingReasonMessage(
  code: BundleBlockingReason["code"],
): string {
  switch (code) {
    case "no_variants":
      return "Bundle has no variants. Select at least one platform before launching.";
    case "bundle_not_draft":
      return "Only DRAFT bundles can be launched.";
    case "platforms_invalid":
      return "One or more selected platforms are invalid. Create a new bundle with valid platforms.";
  }
}
