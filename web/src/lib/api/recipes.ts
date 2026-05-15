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

// V15.1 ships three live recipe forms; the others render as
// "coming soon" cards in the gallery. Update this set as V15.2-V15.4
// add more.
export const LIVE_RECIPE_KINDS = new Set<string>([
  "talking_head",
  "cinematic_visual",
  "talking_head_polished",
]);

// ---- List recipes -----------------------------------------------

const recipeListSchema = z.array(recipeSchema);

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
  error_message: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
  steps: z.array(compositionStepSchema),
  final_asset: assetSchema.nullable(),
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
