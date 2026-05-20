/**
 * /api/recipes/ + /api/compositions/ wrapper.
 *
 * Backend surface: ``apps.compositions.views.RecipeViewSet`` +
 * ``CompositionViewSet`` (V15.0). Recipes are read-only metadata
 * describing the 17 starter compositions; compositions are the
 * actual runs.
 *
 * Mirrors the zod-at-boundary discipline from videos.ts —
 * the response shape is validated once at the API surface.
 */
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Field schema ------------------------------------------------

export const RECIPE_FIELD_TYPES = [
  "text",
  "textarea",
  "checkbox",
  "select",
  "number",
  "spokesperson_picker",
  "asset_picker",
  "dialogue_lines",
  // B2.5 — auto_script recipe: lets the operator pick an approved Script
  // before firing the composition. The ScriptPicker component in
  // $kind.tsx handles this type (calls useScripts({status:'ready'})).
  "script_picker",
] as const;

export type RecipeFieldType = (typeof RECIPE_FIELD_TYPES)[number];

const recipeFieldChoice = z.object({
  value: z.string(),
  label: z.string(),
});

const recipeFieldSchema = z.object({
  name: z.string(),
  type: z.enum(RECIPE_FIELD_TYPES),
  label: z.string(),
  required: z.boolean(),
  default: z.unknown().optional(),
  help_text: z.string().optional(),
  min_chars: z.number().int().optional(),
  max_chars: z.number().int().optional(),
  min_value: z.number().optional(),
  max_value: z.number().optional(),
  choices: z.array(recipeFieldChoice).optional(),
  asset_type: z.string().optional(),
  // A7 (SESSION 190) — narrows the asset_picker dropdown to
  // a single AssetRole. Server-side `RecipeField.role_filter`.
  // Omitted (not null) when the field doesn't narrow; matches
  // backend `to_json` shape.
  role_filter: z.string().optional(),
});

export type RecipeField = z.infer<typeof recipeFieldSchema>;

// ---- Recipe schema -----------------------------------------------

export const RECIPE_FAMILIES = [
  "talking_head",
  "cinematic",
  "layout",
  "polish",
  "voice",
  "style",
  "creative",
  "dialogue",
] as const;

export type RecipeFamily = (typeof RECIPE_FAMILIES)[number];

export const RECIPE_FAMILY_LABELS: Record<RecipeFamily, string> = {
  talking_head: "Talking head",
  cinematic: "Cinematic",
  layout: "Layout & composite",
  polish: "Polish & format",
  voice: "Voice",
  style: "Style",
  creative: "Creative",
  dialogue: "Dialogue",
};

const recipeSchema = z.object({
  kind: z.string(),
  display_name: z.string(),
  family: z.enum(RECIPE_FAMILIES),
  description: z.string(),
  fields: z.array(recipeFieldSchema),
});

export type Recipe = z.infer<typeof recipeSchema>;

// Live recipe forms — opt in here once a kind has been wired
// end-to-end (form renders all fields + composition runs). V15.1
// shipped the first three; V15.2 added the 7 layout/format recipes
// once the asset_picker field landed.
export const LIVE_RECIPE_KINDS = new Set<string>([
  // V15.1
  "talking_head",
  "cinematic_visual",
  "talking_head_polished",
  // V15.2 — layout + format family
  "pip_layout",
  "backdrop_layout",
  "cohost_layout",
  "broll_splice",
  "music_bed_pass",
  "reels_format",
  "talking_head_with_backdrop",
  // V15.3 — voice / style / long-form / storyboard / recut
  "voice_design",
  "multi_lang_dub",
  "style_remix_pass",
  "long_form_ad",
  "storyboard_ad",
  "recut_teaser",
  // V15.4 — dialogue + storyboard_voiced bonus (V14
  // audio_extract unblocked it)
  "dialogue_scene",
  "storyboard_voiced",
  // V17.2 — extend chain off V4 cinematic_visual. Same
  // form-renderer surface as the other live recipes; no
  // SPA-specific code needed beyond opting in here.
  "cinematic_visual_extended",
  // B2.5 — auto_script recipe: operator selects an approved Script and
  // fires a talking_head render with it. Requires the script_picker
  // field type wired in FieldInput.
  "auto_script",
]);

// ---- List recipes -----------------------------------------------

const recipeListSchema = z.array(recipeSchema);

// ---- Assets (V15.2 asset_picker) -------------------------------

const assetListItemSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  asset_type: z.enum(["clip", "audio", "image", "transcript", "voice"]),
  file_path: z.string(),
  duration_ms: z.number().int().nullable(),
  width: z.number().int().nullable(),
  height: z.number().int().nullable(),
  mime_type: z.string(),
  size_bytes: z.number().int().nullable(),
  cost_micros: z.number().int(),
  composition: z.string().nullable(),
  created_at: z.string(),
  // W11.6.5.1 — operator-facing label + subject for the
  // recipe asset_picker dropdown. Both optional with empty
  // default for backward compat with pre-W11.6.5.1 server
  // responses (the SPA assetLabel falls back to filename).
  title: z.string().default(""),
  subject: z.string().default(""),
});

export type AssetListItem = z.infer<typeof assetListItemSchema>;

const assetListSchema = z.array(assetListItemSchema);

export interface ListAssetsOptions {
  workspace: string;
  assetType?: AssetListItem["asset_type"];
  // A7 (SESSION 190) — optional AssetRole filter. Forwards as
  // ``?role=<value>`` on the picker fetch so V18's
  // ``backdrop_clip_id`` dropdown narrows to BACKDROP-tagged
  // clips (no more smoke / talking-head / composite pollution).
  role?: string;
}

export async function listAssets(
  options: ListAssetsOptions,
): Promise<AssetListItem[]> {
  const params = new URLSearchParams({ workspace: options.workspace });
  if (options.assetType) params.set("asset_type", options.assetType);
  if (options.role) params.set("role", options.role);
  return apiJson(
    `/api/assets/?${params.toString()}`,
    {},
    (json) => assetListSchema.parse(json),
  );
}

export function useAssets(options: ListAssetsOptions | undefined) {
  return useQuery({
    queryKey: ["assets", options],
    queryFn: () => listAssets(options!),
    enabled: Boolean(options?.workspace),
    staleTime: 30 * 1000,
  });
}

export async function listRecipes(): Promise<Recipe[]> {
  return apiJson("/api/recipes/", {}, (json) => recipeListSchema.parse(json));
}

export function useRecipes() {
  return useQuery({
    queryKey: ["recipes"],
    queryFn: listRecipes,
    staleTime: 60 * 60 * 1000, // metadata, rarely changes within a session
  });
}

export async function getRecipe(kind: string): Promise<Recipe> {
  return apiJson(
    `/api/recipes/${encodeURIComponent(kind)}/`,
    {},
    (json) => recipeSchema.parse(json),
  );
}

export function useRecipe(kind: string | undefined) {
  return useQuery({
    queryKey: ["recipe", kind],
    queryFn: () => getRecipe(kind!),
    enabled: Boolean(kind),
    staleTime: 60 * 60 * 1000,
  });
}

// ---- Composition schemas ----------------------------------------

const assetSchema = z.object({
  id: z.string(),
  asset_type: z.enum(["clip", "audio", "image", "transcript", "voice"]),
  file_path: z.string(),
  duration_ms: z.number().int().nullable(),
  width: z.number().int().nullable(),
  height: z.number().int().nullable(),
  mime_type: z.string(),
  size_bytes: z.number().int().nullable(),
  cost_micros: z.number().int(),
  created_at: z.string(),
});

export type Asset = z.infer<typeof assetSchema>;

const compositionStepSchema = z.object({
  id: z.string(),
  position: z.number().int(),
  primitive: z.string(),
  status: z.enum(["pending", "running", "succeeded", "failed", "skipped"]),
  inputs: z.array(z.record(z.string(), z.unknown())),
  params: z.record(z.string(), z.unknown()),
  cost_estimate_micros: z.number().int(),
  cost_actual_micros: z.number().int(),
  error_message: z.string(),
  output_asset: assetSchema.nullable(),
});

export type CompositionStep = z.infer<typeof compositionStepSchema>;

export const COMPOSITION_STATUSES = [
  "draft",
  "planning",
  "running",
  "partial",
  "completed",
  "failed",
] as const;

export type CompositionStatus = (typeof COMPOSITION_STATUSES)[number];

const knowledgeDocCitationSchema = z.object({
  id: z.string(),
  title: z.string(),
  chunk_count: z.number().int(),
});

export type KnowledgeDocCitation = z.infer<typeof knowledgeDocCitationSchema>;

// K6.4 v1.1 — same shape as the unsupportedClaim schema in
// conversations.ts. Duplicated here to keep each API module
// self-contained (no cross-module schema imports).
const unsupportedClaimSchema = z.object({
  claim: z.string(),
  kind: z.string(),
  position: z.number().int(),
});

export type UnsupportedClaim = z.infer<typeof unsupportedClaimSchema>;

// A8 (SESSION 192) — light shape for every Asset emitted by the
// composition's pipeline. SPA panel links each entry to the A6
// detail view at /workspace/assets/<id>.
const producedAssetSchema = z.object({
  id: z.string(),
  asset_type: z.enum(["clip", "audio", "image", "transcript", "voice"]),
  role: z.string(),
  title: z.string(),
  file_path: z.string(),
  storage_health: z.string(),
  is_final: z.boolean(),
});

export type ProducedAsset = z.infer<typeof producedAssetSchema>;

const compositionSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  spokesperson: z.string(),
  name: z.string(),
  template_kind: z.string(),
  status: z.enum(COMPOSITION_STATUSES),
  mock_mode: z.boolean(),
  cost_estimate_micros: z.number().int(),
  cost_actual_micros: z.number().int(),
  knowledge_chunk_ids: z.array(z.string()),
  // F6 — server-resolved doc-level view of the chunk ids
  // above. Empty array when the composition didn't draw on
  // knowledge. Older composition rows that pre-date F6 will
  // surface as empty (until/unless re-rendered).
  knowledge_docs_used: z.array(knowledgeDocCitationSchema).default([]),
  error_message: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  steps: z.array(compositionStepSchema),
  final_asset: assetSchema.nullable(),
  // A8 (SESSION 192) — every Asset emitted by this composition's
  // pipeline. The SPA panel labels which one is the final via
  // is_final. Defaults to [] for older composition rows.
  produced_assets: z.array(producedAssetSchema).default([]),
  // K6.4 v1.1 — verifier surface. Empty array on clean
  // renders, populated on Warn-mode flags and Strict-mode
  // rejections. ``rejected_synthesis`` carries the text the
  // LLM produced before strict rejected it (empty otherwise).
  verification_warnings: z.array(unsupportedClaimSchema).default([]),
  rejected_synthesis: z.string().default(""),
  // K6.4 v1.2 — verification_status badge. Four explicit
  // states + empty for pre-v1.2 rows. See
  // apps.compositions.models.VerificationStatus.
  verification_status: z
    .enum(["", "verified", "trusted_passthrough", "skipped", "rejected"])
    .default(""),
  // K6.6 — synthesized brief on successful renders. Populated
  // only when K6 actually synthesized; empty for force-mock,
  // degraded paths, operator-typed scripts, and pre-K6.6
  // rows.
  synthesized_brief: z.string().default(""),
});

export type Composition = z.infer<typeof compositionSchema>;

const compositionListSchema = z.array(compositionSchema);

const COMPOSITION_TERMINAL_STATUSES: CompositionStatus[] = [
  "completed",
  "failed",
  "partial",
];

// ---- Compositions API --------------------------------------------

export interface CreateCompositionInput {
  kind: string;
  workspace: string;
  params: Record<string, unknown>;
}

export async function createComposition(
  input: CreateCompositionInput,
): Promise<Composition> {
  return apiJson(
    "/api/compositions/",
    { method: "POST", body: input },
    (json) => compositionSchema.parse(json),
  );
}

export function useCreateComposition() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createComposition,
    onSuccess: (composition) => {
      qc.setQueryData(["composition", composition.id], composition);
      qc.invalidateQueries({ queryKey: ["compositions"] });
    },
  });
}

export async function getComposition(id: string): Promise<Composition> {
  return apiJson(
    `/api/compositions/${id}/`,
    {},
    (json) => compositionSchema.parse(json),
  );
}

export function useComposition(id: string | undefined) {
  return useQuery({
    queryKey: ["composition", id],
    queryFn: () => getComposition(id!),
    enabled: Boolean(id),
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return 2_000;
      return COMPOSITION_TERMINAL_STATUSES.includes(data.status)
        ? false
        : 2_000;
    },
    refetchIntervalInBackground: false,
    staleTime: 0,
  });
}

export async function listCompositions(): Promise<Composition[]> {
  return apiJson(
    "/api/compositions/",
    {},
    (json) => compositionListSchema.parse(json),
  );
}

export function useCompositions() {
  return useQuery({
    queryKey: ["compositions"],
    queryFn: listCompositions,
  });
}

export function isTerminalStatus(status: CompositionStatus): boolean {
  return COMPOSITION_TERMINAL_STATUSES.includes(status);
}

// ---- Lineage (F5, workspace fabric arc) -------------------------

const lineageRefSchema = z.object({
  composition_id: z.string(),
  composition_name: z.string(),
  template_kind: z.string(),
  status: z.enum(COMPOSITION_STATUSES),
});

const derivedFromEntrySchema = lineageRefSchema.extend({
  asset_id: z.string(),
  asset_type: z.enum(["clip", "audio", "image", "transcript", "voice"]),
});

const compositionLineageSchema = z.object({
  composition_id: z.string(),
  derived_from: z.array(derivedFromEntrySchema),
  used_by: z.array(lineageRefSchema),
});

export type CompositionLineage = z.infer<typeof compositionLineageSchema>;
export type LineageDerivedFromEntry = z.infer<typeof derivedFromEntrySchema>;
export type LineageRef = z.infer<typeof lineageRefSchema>;

export async function getCompositionLineage(
  id: string,
): Promise<CompositionLineage> {
  return apiJson(
    `/api/compositions/${id}/lineage/`,
    {},
    (json) => compositionLineageSchema.parse(json),
  );
}

export function useCompositionLineage(id: string | undefined) {
  return useQuery({
    queryKey: ["composition-lineage", id],
    queryFn: () => getCompositionLineage(id!),
    enabled: Boolean(id),
    staleTime: 30_000,
  });
}
