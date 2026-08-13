/**
 * /api/workspace/assets/ wrapper.
 *
 * Backend surface: WorkspaceAssetViewSet
 * (shell/apps/compositions/views.py). SESSION 189 / A5.
 *
 * Asset Library v1 list view. The route is workspace-scoped
 * via request.user.default_workspace or ?workspace=<uuid>.
 * Membership checks happen server-side.
 *
 * A6 (SESSION 191) adds getWorkspaceAsset + useWorkspaceAsset
 * for the per-asset detail page at /workspace/assets/:id.
 */
import { z } from "zod";
import { useQuery } from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Enums (mirrors backend TextChoices) ----------------------

/** Mirrors apps.compositions.models.AssetType */
export const ASSET_TYPES = [
  "clip",
  "audio",
  "image",
  "transcript",
  "voice",
] as const;
export type AssetType = (typeof ASSET_TYPES)[number];

/** Mirrors apps.compositions.models.AssetRole
 *
 * SESSION 224 F-05: bridge_answer added when SPA drifted from
 * backend (11 vs 10 values) after C3 shipped 2026-07-22 in
 * PR #4 `dc67d2e`; the transcripts page (via useTranscripts →
 * useWorkspaceAssets) broke for any workspace with a
 * BRIDGE_ANSWER asset. The regression test in
 * ``workspace-assets.test.ts`` (``ASSET_ROLES matches backend``)
 * enforces this stays in sync — when you touch
 * ``apps/compositions/models.py::AssetRole``, update this list
 * and the ``assetRoleLabel`` map below.
 */
export const ASSET_ROLES = [
  "talking_head",
  "backdrop",
  "composite_output",
  "polish_output",
  "reference_image",
  "b_roll",
  "transcript",
  "audio_track",
  "raw_upload",
  "experiment",
  "bridge_answer",
] as const;
export type AssetRole = (typeof ASSET_ROLES)[number];

/** Mirrors apps.compositions.assets.StorageHealth */
export const STORAGE_HEALTH_VALUES = [
  "https_live",
  "https_expiring_soon",
  "https_expired",
  "local_present",
  "local_missing",
  "data_uri",
  "upload_pending",
] as const;
export type StorageHealth = (typeof STORAGE_HEALTH_VALUES)[number];

// ---- Schemas --------------------------------------------------

const compositionRefSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  template_kind: z.string(),
});

export type CompositionRef = z.infer<typeof compositionRefSchema>;

const workspaceAssetSchema = z.object({
  id: z.string(),
  asset_type: z.enum(ASSET_TYPES),
  role: z.enum(ASSET_ROLES),
  file_path: z.string(),
  title: z.string(),
  subject: z.string(),
  duration_ms: z.number().nullable(),
  width: z.number().nullable(),
  height: z.number().nullable(),
  mime_type: z.string(),
  size_bytes: z.number().nullable(),
  cost_micros: z.number(),
  created_at: z.string(),
  storage_health: z.enum(STORAGE_HEALTH_VALUES),
  primitive_kind: z.string(),
  producing_prompt: z.string(),
  composition: compositionRefSchema.nullable(),
});

export type WorkspaceAsset = z.infer<typeof workspaceAssetSchema>;

// ---- Detail-only schemas (A6) ----------------------------------------

/**
 * The CompositionStep that produced this asset.
 * Mirrors _serialize_detail_asset's producing_step shape.
 */
export const producingStepSchema = z.object({
  id: z.string(),
  position: z.number(),
  primitive: z.string(),
  params: z.record(z.string(), z.unknown()),
  inputs: z.array(z.unknown()),
  source_spec: z.record(z.string(), z.unknown()).nullable(),
});

export type ProducingStep = z.infer<typeof producingStepSchema>;

/**
 * A downstream composition that consumed this asset as input.
 * Mirrors the `downstream_compositions` array in _serialize_detail_asset.
 */
export const downstreamCompositionSchema = z.object({
  id: z.string(),
  name: z.string(),
  status: z.string(),
  template_kind: z.string(),
});

export type DownstreamComposition = z.infer<typeof downstreamCompositionSchema>;

/**
 * Full detail shape: list fields + producing_step + downstream_compositions
 * + inline_content (for TRANSCRIPT assets — added to the detail serializer
 * in A6 because transcript bodies are the primary operator value).
 */
export const workspaceAssetDetailSchema = workspaceAssetSchema.extend({
  producing_step: producingStepSchema.nullable(),
  downstream_compositions: z.array(downstreamCompositionSchema),
  inline_content: z.string(),
});

export type WorkspaceAssetDetail = z.infer<typeof workspaceAssetDetailSchema>;

const workspaceAssetListResponseSchema = z.object({
  count: z.number(),
  next: z.string().nullable(),
  previous: z.string().nullable(),
  results: z.array(workspaceAssetSchema),
});

export type WorkspaceAssetListResponse = z.infer<
  typeof workspaceAssetListResponseSchema
>;

// ---- Query params ---------------------------------------------

export interface WorkspaceAssetsParams {
  /** Comma-joined array — each element is an AssetRole value. */
  role?: string[];
  /** Comma-joined array — each element is an AssetType value. */
  asset_type?: string[];
  /** Comma-joined array — primitive_kind values. */
  primitive_kind?: string[];
  /** Comma-joined array — StorageHealth values. */
  storage?: string[];
  /** Full-text search over title + subject + producing_prompt. */
  q?: string;
  /** ISO date string — filters created_at >= value. */
  created_after?: string;
  /** ISO date string — filters created_at <= value. */
  created_before?: string;
  page?: number;
  page_size?: number;
  /** Explicit workspace UUID — defaults to user's default on the server. */
  workspace?: string;
}

// ---- Fetch helper ---------------------------------------------

/** Build a URLSearchParams string from WorkspaceAssetsParams.
 *  Arrays are joined as comma-separated values per backend contract. */
export function buildAssetsQueryString(
  params: WorkspaceAssetsParams,
): string {
  const p = new URLSearchParams();

  if (params.role?.length) p.set("role", params.role.join(","));
  if (params.asset_type?.length)
    p.set("asset_type", params.asset_type.join(","));
  if (params.primitive_kind?.length)
    p.set("primitive_kind", params.primitive_kind.join(","));
  if (params.storage?.length) p.set("storage", params.storage.join(","));
  if (params.q) p.set("q", params.q);
  if (params.created_after) p.set("created_after", params.created_after);
  if (params.created_before) p.set("created_before", params.created_before);
  if (params.page != null && params.page > 1)
    p.set("page", String(params.page));
  if (params.page_size != null) p.set("page_size", String(params.page_size));
  if (params.workspace) p.set("workspace", params.workspace);

  const qs = p.toString();
  return qs ? `?${qs}` : "";
}

export async function listWorkspaceAssets(
  params: WorkspaceAssetsParams,
): Promise<WorkspaceAssetListResponse> {
  const qs = buildAssetsQueryString(params);
  return apiJson(
    `/api/workspace/assets/${qs}`,
    {},
    (json) => workspaceAssetListResponseSchema.parse(json),
  );
}

// ---- React Query hook ----------------------------------------

export function useWorkspaceAssets(params: WorkspaceAssetsParams) {
  return useQuery({
    queryKey: ["workspace-assets", "list", params],
    queryFn: () => listWorkspaceAssets(params),
    // 20s stale time mirrors knowledge.ts behaviour — asset list
    // doesn't need aggressive re-fetching on focus.
    staleTime: 20_000,
    // Keep the previous page data in cache for smooth pagination.
    placeholderData: (prev) => prev,
  });
}

// ---- Detail fetch + hook (A6) --------------------------------

/**
 * Fetch a single asset by id.
 * Workspace is optional — defaults to the user's default on the server.
 * Cross-workspace ids → 404; unauthenticated → 401/403.
 */
export async function getWorkspaceAsset(
  id: string,
  workspace?: string,
): Promise<WorkspaceAssetDetail> {
  const p = new URLSearchParams();
  if (workspace) p.set("workspace", workspace);
  const qs = p.toString() ? `?${p.toString()}` : "";
  return apiJson(
    `/api/workspace/assets/${id}/${qs}`,
    {},
    (json) => workspaceAssetDetailSchema.parse(json),
  );
}

/** React Query hook for a single asset detail. */
export function useWorkspaceAsset(id: string | undefined, workspace?: string) {
  return useQuery({
    queryKey: ["workspace-asset", id ?? null, workspace ?? null],
    queryFn: () => getWorkspaceAsset(id!, workspace),
    enabled: Boolean(id),
    staleTime: 20_000,
  });
}

// ---- Display helpers -----------------------------------------

/** Human-readable label for an AssetRole value. */
export function assetRoleLabel(role: AssetRole): string {
  const MAP: Record<AssetRole, string> = {
    talking_head: "Talking head",
    backdrop: "Backdrop",
    composite_output: "Composite output",
    polish_output: "Polish output",
    reference_image: "Reference image",
    b_roll: "B-roll",
    transcript: "Transcript",
    audio_track: "Audio track",
    raw_upload: "Raw upload",
    experiment: "Experiment",
    bridge_answer: "Engine bridge answer",
  };
  return MAP[role] ?? role;
}

/** Human-readable label for an AssetType value. */
export function assetTypeLabel(type: AssetType): string {
  const MAP: Record<AssetType, string> = {
    clip: "Clip",
    audio: "Audio",
    image: "Image",
    transcript: "Transcript",
    voice: "Voice",
  };
  return MAP[type] ?? type;
}

/** Tailwind colour classes for storage health badges.
 *  Returns [border, bg, text] classes as a single string. */
export function storageHealthTone(
  health: StorageHealth,
): "success" | "warning" | "danger" | "neutral" {
  switch (health) {
    case "https_live":
    case "local_present":
    case "data_uri":
      return "success";
    case "https_expiring_soon":
      return "warning";
    case "https_expired":
    case "local_missing":
      return "danger";
    case "upload_pending":
      return "neutral";
  }
}

/** Human-readable label for a StorageHealth value. */
export function storageHealthLabel(health: StorageHealth): string {
  const MAP: Record<StorageHealth, string> = {
    https_live: "Live",
    https_expiring_soon: "Expiring soon",
    https_expired: "Expired",
    local_present: "Local",
    local_missing: "Missing",
    data_uri: "Embedded",
    upload_pending: "Pending",
  };
  return MAP[health] ?? health;
}

/** Relative time string — "3h ago", "yesterday", "5 Jan 2026". */
export function relativeTime(isoString: string): string {
  const now = Date.now();
  const then = new Date(isoString).getTime();
  const diffMs = now - then;
  const diffSeconds = Math.floor(diffMs / 1_000);
  const diffMinutes = Math.floor(diffSeconds / 60);
  const diffHours = Math.floor(diffMinutes / 60);
  const diffDays = Math.floor(diffHours / 24);

  if (diffSeconds < 60) return "just now";
  if (diffMinutes < 60)
    return `${diffMinutes}m ago`;
  if (diffHours < 24)
    return `${diffHours}h ago`;
  if (diffDays === 1) return "yesterday";
  if (diffDays < 7) return `${diffDays}d ago`;

  // Fall back to a formatted date for older assets.
  return new Intl.DateTimeFormat("en-US", {
    day: "numeric",
    month: "short",
    year: diffDays > 365 ? "numeric" : undefined,
  }).format(new Date(isoString));
}
