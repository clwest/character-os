/**
 * /api/images/ + /api/styles/ wrapper.
 *
 * Backend surface: ``apps.compositions.views.ImageViewSet`` +
 * ``StyleLibraryViewSet`` (W11.6.2, SESSION 173). Mirrors the
 * zod-at-boundary discipline from videos.ts / recipes.ts —
 * the response shape is validated once at the API surface.
 *
 * Scope: ``docs/design/MEDIA_GENERATION_V1.md`` §"Surface inventory"
 * (W11.6.3 hooks).
 */
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "./client";

// ---- Constants (mirror the backend enums) -----------------------

/** Non-avatar purposes accepted by the SPA generation form.
 *  Backend's full enum includes "avatar" but rejects it via
 *  Contract rule 2 (avatar wizard owns that path in v1). */
export const IMAGE_PURPOSES = ["scene", "broll", "product", "ad"] as const;
export type ImagePurpose = (typeof IMAGE_PURPOSES)[number];

export const IMAGE_PURPOSE_LABELS: Record<ImagePurpose, string> = {
  scene: "Scene",
  broll: "B-roll",
  product: "Product",
  ad: "Ad creative",
};

export const IMAGE_PURPOSE_HINTS: Record<ImagePurpose, string> = {
  scene: "Hero imagery, landing-page visuals, situational illustrations.",
  broll: "Supplementary footage stills for cutaways in video edits.",
  product: "Centered product shots with clean studio composition.",
  ad: "Bold advertising visuals with strong hierarchy.",
};

/** Stability models exposed on the picker. Backend whitelist
 *  matches; adding a new model is a coordinated change here +
 *  ``apps/compositions/views.STABILITY_VALID_MODELS``. */
export const STABILITY_MODELS = [
  "core",
  "sdxl",
  "sd3-medium",
  "sd3-large-turbo",
  "sd3-large",
  "ultra",
] as const;
export type StabilityModel = (typeof STABILITY_MODELS)[number];

export const STABILITY_MODEL_LABELS: Record<StabilityModel, string> = {
  core: "Core",
  sdxl: "SDXL",
  "sd3-medium": "SD3 Medium",
  "sd3-large-turbo": "SD3 Large Turbo",
  "sd3-large": "SD3 Large",
  ultra: "Ultra",
};

/** Hint copy locked in MEDIA_GENERATION_V1.md §"Model hint copy". */
export const STABILITY_MODEL_HINTS: Record<StabilityModel, string> = {
  core: "Fastest + cheapest (3 credits). Good for quick concepting and scratchpad iterations.",
  sdxl: "Balanced speed and quality (~3 credits). General-purpose workhorse.",
  "sd3-medium": "Detailed mid-tier (3.5 credits). Good default for most production images.",
  "sd3-large-turbo": "SD3 quality at faster speeds (4 credits). When you want SD3 detail but in a hurry.",
  "sd3-large": "Best SD3 quality (6.5 credits). Recommended default for final-use images.",
  ultra: "Premium flagship (8 credits). Use for hero images and marketing-quality results.",
};

export const STABILITY_MODEL_CREDITS: Record<StabilityModel, number> = {
  core: 3.0,
  sdxl: 3.0,
  "sd3-medium": 3.5,
  "sd3-large-turbo": 4.0,
  "sd3-large": 6.5,
  ultra: 8.0,
};

export const IMAGE_ASPECT_RATIOS = [
  "1:1",
  "16:9",
  "9:16",
  "4:3",
  "3:4",
  "21:9",
] as const;
export type ImageAspectRatio = (typeof IMAGE_ASPECT_RATIOS)[number];

/** Hint copy locked in MEDIA_GENERATION_V1.md §"Aspect ratio hint copy". */
export const IMAGE_ASPECT_RATIO_HINTS: Record<ImageAspectRatio, string> = {
  "1:1": "Square. Social posts, profile images, product shots.",
  "16:9": "Landscape widescreen. Video backdrops, banners, web headers.",
  "9:16": "Vertical / tall. Reels, TikTok, Stories, mobile-first content.",
  "4:3": "Traditional landscape. Slide decks, blog headers.",
  "3:4": "Portrait. Profile photos, character art.",
  "21:9": "Cinematic ultrawide. Dramatic scenes, panoramas.",
};

// ---- Image asset schema -----------------------------------------

const imageAssetSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  asset_type: z.literal("image"),
  file_path: z.string(),
  mime_type: z.string(),
  width: z.number().int().nullable(),
  height: z.number().int().nullable(),
  size_bytes: z.number().int().nullable(),
  cost_micros: z.number().int(),
  composition: z.string().nullable(),
  purpose: z.string(),
  model: z.string(),
  style_preset: z.string(),
  prompt: z.string(),
  // W11.6.4 — original operator subject (pre-composition).
  // Empty for pre-W11.6.4 image rows; the SPA Regenerate CTA
  // falls back to "Adjust" (form opens with subject blank) in
  // that case.
  subject: z.string().default(""),
  negative_prompt: z.string(),
  aspect_ratio: z.string(),
  spokesperson: z.string().nullable(),
  created_at: z.string(),
});

export type ImageAsset = z.infer<typeof imageAssetSchema>;

const imageAssetListSchema = z.array(imageAssetSchema);

// ---- Style library schema ---------------------------------------

const stylePresetSchema = z.object({
  name: z.string(),
  display_name: z.string(),
  category: z.string(),
  description: z.string(),
  best_for: z.array(z.string()),
  mood: z.string(),
  example_prompt_suffix: z.string(),
});

export type StylePreset = z.infer<typeof stylePresetSchema>;

const styleCategorySchema = z.object({
  id: z.string(),
  display_name: z.string(),
  description: z.string(),
  icon: z.string(),
  presets: z.array(stylePresetSchema),
});

export type StyleCategory = z.infer<typeof styleCategorySchema>;

const styleLibrarySchema = z.object({
  categories: z.array(styleCategorySchema),
  total_presets: z.number().int(),
});

export type StyleLibrary = z.infer<typeof styleLibrarySchema>;

// ---- API surface ------------------------------------------------

export interface ListImagesOptions {
  workspace: string;
  purpose?: ImagePurpose;
  model?: StabilityModel;
  stylePreset?: string;
  spokesperson?: string;
}

export async function listImages(
  options: ListImagesOptions,
): Promise<ImageAsset[]> {
  const params = new URLSearchParams({ workspace: options.workspace });
  if (options.purpose) params.set("purpose", options.purpose);
  if (options.model) params.set("model", options.model);
  if (options.stylePreset) params.set("style_preset", options.stylePreset);
  if (options.spokesperson) params.set("spokesperson", options.spokesperson);
  return apiJson(
    `/api/images/?${params.toString()}`,
    {},
    (json) => imageAssetListSchema.parse(json),
  );
}

export function useImages(options: ListImagesOptions | undefined) {
  return useQuery({
    queryKey: ["images", options],
    queryFn: () => listImages(options!),
    enabled: Boolean(options?.workspace),
    staleTime: 30 * 1000,
  });
}

export async function getImage(id: string): Promise<ImageAsset> {
  return apiJson(
    `/api/images/${id}/`,
    {},
    (json) => imageAssetSchema.parse(json),
  );
}

export function useImage(id: string | undefined) {
  return useQuery({
    queryKey: ["image", id],
    queryFn: () => getImage(id!),
    enabled: Boolean(id),
    staleTime: 60 * 1000,
  });
}

export interface GenerateImageInput {
  workspace: string;
  purpose: ImagePurpose;
  subject: string;
  model?: StabilityModel;
  style_preset?: string;
  aspect_ratio?: ImageAspectRatio;
  negative_prompt_override?: string;
  spokesperson?: string;
}

export async function generateImage(
  input: GenerateImageInput,
): Promise<ImageAsset> {
  return apiJson(
    "/api/images/",
    { method: "POST", body: input },
    (json) => imageAssetSchema.parse(json),
  );
}

export function useGenerateImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: generateImage,
    onSuccess: (asset) => {
      qc.setQueryData(["image", asset.id], asset);
      // Invalidate every cached image list — workspace + filter
      // combinations are too varied to selectively bump.
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

export async function deleteImage(id: string): Promise<void> {
  await apiJson(`/api/images/${id}/`, { method: "DELETE" });
}

export function useDeleteImage() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteImage,
    onSuccess: (_void, id) => {
      qc.removeQueries({ queryKey: ["image", id] });
      qc.invalidateQueries({ queryKey: ["images"] });
    },
  });
}

export async function getStyleLibrary(): Promise<StyleLibrary> {
  return apiJson(
    "/api/styles/",
    {},
    (json) => styleLibrarySchema.parse(json),
  );
}

export function useStyleLibrary() {
  return useQuery({
    queryKey: ["style-library"],
    queryFn: getStyleLibrary,
    // Static reference data — cache aggressively. The library is
    // a code-level constant on the media-engine; it only changes
    // when a slice ships new presets.
    staleTime: 60 * 60 * 1000,
    gcTime: 24 * 60 * 60 * 1000,
  });
}
