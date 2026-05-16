/**
 * /api/spokespeople/ wrapper.
 *
 * Backend surface: SpokespersonViewSet (shell/apps/spokespeople/views.py).
 * DRF's default router returns a list as `{count, next, previous, results}`
 * when pagination is configured, or a bare array otherwise. We tolerate
 * both shapes here so the SPA doesn't break when pagination flips on.
 */
import { z } from "zod";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { apiJson } from "./client";

// Tone archetype literals. Mirrors `Spokesperson.Tone` on the Django
// side + `TONE_ARCHETYPES` in `character_os/prompts/brand.py`. Keep
// in sync when any side shifts.
export const TONE_ARCHETYPES = [
  "tutor",
  "authority",
  "friend",
  "expert",
  "performer",
] as const;
export type ToneArchetype = (typeof TONE_ARCHETYPES)[number];

// Visual templates. Mirrors `SUPPORTED_PORTRAIT_TEMPLATES` in
// `shell/apps/spokespeople/views.py`, which itself mirrors
// `media-engine/app/services/character_studio_client.PORTRAIT_TEMPLATES`.
// Used by the wizard's Step 2 Generate tab.
export const PORTRAIT_TEMPLATES = [
  "mascot",
  "founder",
  "coach",
  "local_guide",
] as const;
export type PortraitTemplate = (typeof PORTRAIT_TEMPLATES)[number];

export const PORTRAIT_TEMPLATE_LABELS: Record<PortraitTemplate, string> = {
  mascot: "Mascot",
  founder: "Founder",
  coach: "Coach",
  local_guide: "Local guide",
};

export const PORTRAIT_TEMPLATE_HINTS: Record<PortraitTemplate, string> = {
  mascot: "Anthropomorphic brand character (battle unicorns live here).",
  founder: "Polished, mid-30s, founder-shaped spokesperson.",
  coach: "Energetic motivator with a confident, bright expression.",
  local_guide: "Welcoming neighborhood face for local-business shops.",
};

const spokespersonSchema = z.object({
  id: z.string(),
  workspace: z.string(),
  workspace_name: z.string().optional(),
  name: z.string(),
  business_brief: z.string(),
  visual_subject: z.string(),
  tone_archetype: z.enum(TONE_ARCHETYPES),
  status: z.enum(["setup_needed", "ready", "archived"]),
  runway_avatar_id: z.string(),
  runway_avatar_status: z.string(),
  portrait_path: z.string(),
  voice_id: z.string(),
  video_count: z.number().int().nonnegative().optional(),
  created_at: z.string(),
  updated_at: z.string(),
});

export type Spokesperson = z.infer<typeof spokespersonSchema>;

// DRF returns either an array or a paginated envelope. Accept both.
const listResponseSchema = z.union([
  z.array(spokespersonSchema),
  z.object({
    count: z.number().int().optional(),
    next: z.string().nullable().optional(),
    previous: z.string().nullable().optional(),
    results: z.array(spokespersonSchema),
  }),
]);

function unwrapList(json: unknown): Spokesperson[] {
  const parsed = listResponseSchema.parse(json);
  return Array.isArray(parsed) ? parsed : parsed.results;
}

export async function listSpokespeople(): Promise<Spokesperson[]> {
  return apiJson("/api/spokespeople/", {}, unwrapList);
}

export function useSpokespeople() {
  return useQuery({
    queryKey: ["spokespeople"],
    queryFn: listSpokespeople,
  });
}

// ---- Single-resource fetch (detail page) ---------------------------

export async function getSpokesperson(id: string): Promise<Spokesperson> {
  return apiJson(`/api/spokespeople/${id}/`, {}, (json) =>
    spokespersonSchema.parse(json),
  );
}

export function useSpokesperson(id: string | undefined) {
  return useQuery({
    queryKey: ["spokesperson", id],
    queryFn: () => getSpokesperson(id!),
    enabled: Boolean(id),
    // Detail page refresh cadence: tighter than the list (operator
    // is actively looking at one row, expects status pill changes
    // to show within a few seconds). Real avatar / voice status
    // transitions land here too in future slices.
    staleTime: 15 * 1000,
  });
}

// ---- Create (S-06) -------------------------------------------------

export interface CreateSpokespersonInput {
  workspace: string;
  name: string;
  business_brief: string;
  /** Free-text "what this spokesperson looks like" — "armored
   * battle unicorn", "neon-pink raccoon". Persists on the row;
   * Wizard Step 2 (W7) threads it into `/internal/portrait/`
   * generation when no portrait_data_uri is supplied. */
  visual_subject?: string;
  /** Persona axis. One of `TONE_ARCHETYPES`. Defaults server-side
   * to `expert` if omitted. */
  tone_archetype?: ToneArchetype;
  /** ``data:image/{png|jpeg|webp};base64,...`` — optional. When
   * supplied, the backend fires the media-engine avatar create
   * synchronously and persists `runway_avatar_id` on the row. */
  portrait_data_uri?: string;
  voice_preset?: string;
}

export async function createSpokesperson(
  input: CreateSpokespersonInput,
): Promise<Spokesperson> {
  return apiJson(
    "/api/spokespeople/",
    { method: "POST", body: input },
    (json) => spokespersonSchema.parse(json),
  );
}

export function useCreateSpokesperson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createSpokesperson,
    onSuccess: (spokesperson) => {
      // Invalidate the list so the dashboard refreshes when the
      // user navigates back. Also seed the single-resource cache
      // so the detail page renders instantly on redirect.
      qc.invalidateQueries({ queryKey: ["spokespeople"] });
      qc.setQueryData(["spokesperson", spokesperson.id], spokesperson);
      // Subscription usage might have shifted (spokespeople count).
      qc.invalidateQueries({ queryKey: ["subscription"] });
    },
  });
}

// ---- Refresh portrait (SESSION 169 follow-up) --------------------
//
// Runway's CloudFront thumbnail URLs are JWT-signed with ~30-day
// expiry. When portrait_path 401s, the SPA can hit this endpoint to
// get a fresh signed URL and update its image src. The Portrait
// component's <img onError> uses this so the gap doesn't recur as
// JWTs expire over time.

export async function refreshSpokespersonPortrait(
  id: string,
): Promise<Spokesperson> {
  return apiJson(
    `/api/spokespeople/${id}/refresh-portrait/`,
    { method: "POST", body: {} },
    (json) => spokespersonSchema.parse(json),
  );
}

export function useRefreshPortrait() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: refreshSpokespersonPortrait,
    onSuccess: (spokesperson) => {
      qc.setQueryData(["spokesperson", spokesperson.id], spokesperson);
      qc.invalidateQueries({ queryKey: ["spokespeople"] });
    },
  });
}


// ---- W11.1 — edit spokesperson -----------------------------------

export interface UpdateSpokespersonInput {
  id: string;
  /** Patch only the fields the operator changed. Send only modified
   * keys; the backend PATCH will leave the rest alone. Editable
   * fields per the serializer: name, business_brief, visual_subject,
   * tone_archetype. Voice + avatar are read-only on this path
   * (separate action endpoints; W11.2 to wire). */
  name?: string;
  business_brief?: string;
  visual_subject?: string;
  tone_archetype?: ToneArchetype;
}

export async function updateSpokesperson(
  input: UpdateSpokespersonInput,
): Promise<Spokesperson> {
  const { id, ...payload } = input;
  return apiJson(
    `/api/spokespeople/${id}/`,
    { method: "PATCH", body: payload },
    (json) => spokespersonSchema.parse(json),
  );
}

export function useUpdateSpokesperson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: updateSpokesperson,
    onSuccess: (spokesperson) => {
      // Seed the single-resource cache so the detail page reflects
      // the new values instantly; invalidate the list so the
      // dashboard's name/tone pills refresh.
      qc.setQueryData(["spokesperson", spokesperson.id], spokesperson);
      qc.invalidateQueries({ queryKey: ["spokespeople"] });
    },
  });
}

// ---- Generate portrait (SESSION 130 — wizard slice 7) ---------------

const generatePortraitResponseSchema = z.object({
  portrait_data_uri: z.string(),
  template: z.string(),
  prompt: z.string(),
  mock_mode: z.boolean(),
});

export type GeneratePortraitResponse = z.infer<typeof generatePortraitResponseSchema>;

export interface GeneratePortraitInput {
  template: PortraitTemplate;
  /** Free-text subject — "armored battle unicorn", "neon-pink
   * raccoon in a denim jacket". Empty means "use the template's
   * built-in default subject." */
  subject?: string;
  /** Optional style hint (free-form text or chip names). */
  style?: string;
}

export async function generatePortrait(
  input: GeneratePortraitInput,
): Promise<GeneratePortraitResponse> {
  return apiJson(
    "/api/spokespeople/generate-portrait/",
    { method: "POST", body: input },
    (json) => generatePortraitResponseSchema.parse(json),
  );
}

export function useGeneratePortrait() {
  return useMutation({
    mutationFn: generatePortrait,
    // No cache invalidation — this generates a transient portrait
    // that the wizard accumulates in client state until Confirm.
    // No Spokesperson row exists yet.
  });
}

// ---- Spokesperson templates (SESSION 133 — wizard slice 10) ---------

const spokespersonTemplateSchema = z.object({
  key: z.string(),
  name: z.string(),
  tagline: z.string(),
  business_brief: z.string(),
  tone_archetype: z.enum(TONE_ARCHETYPES),
  visual_template: z.enum(PORTRAIT_TEMPLATES),
  visual_subject: z.string(),
  voice_preset: z.string(),
});

export type SpokespersonTemplate = z.infer<typeof spokespersonTemplateSchema>;

const templatesResponseSchema = z.object({
  templates: z.array(spokespersonTemplateSchema),
});

export async function listSpokespersonTemplates(): Promise<SpokespersonTemplate[]> {
  return apiJson(
    "/api/spokespeople/templates/",
    {},
    (json) => templatesResponseSchema.parse(json).templates,
  );
}

export function useSpokespersonTemplates() {
  return useQuery({
    queryKey: ["spokespeople", "templates"],
    queryFn: listSpokespersonTemplates,
    // Static-ish data; refresh aggressively only when the operator
    // navigates away + back.
    staleTime: 60 * 60 * 1000,
  });
}

// ---- Voice presets (SESSION 126 — wizard slice 3) ------------------

const voicePresetsResponseSchema = z.object({
  presets: z.array(z.string()),
});

export async function listVoicePresets(): Promise<string[]> {
  return apiJson(
    "/api/spokespeople/voice-presets/",
    {},
    (json) => voicePresetsResponseSchema.parse(json).presets,
  );
}

export function useVoicePresets() {
  return useQuery({
    queryKey: ["spokespeople", "voice-presets"],
    queryFn: listVoicePresets,
    // Presets are effectively static (Runway's list shifts on the
    // order of months). Cache aggressively.
    staleTime: 60 * 60 * 1000,
  });
}

// ---- Clone-voice mutation (SESSION 126 — wizard slice 3) -----------

const cloneVoiceResponseSchema = z.object({
  spokesperson: spokespersonSchema,
  voice: z.object({
    voice_id: z.string(),
    status: z.string(),
    preview_url: z.string().nullable(),
    mock_mode: z.boolean(),
  }),
});

export type CloneVoiceResponse = z.infer<typeof cloneVoiceResponseSchema>;

/**
 * Either ``{preset: "vincent"}`` OR ``{audio_data_uri: ...}`` —
 * preset wins if both are sent. Mirrors the backend contract in
 * ``SpokespersonViewSet.clone_voice``.
 */
export interface CloneVoiceInput {
  id: string;
  preset?: string;
  audio_data_uri?: string;
  name?: string;
}

export async function cloneVoice(input: CloneVoiceInput): Promise<CloneVoiceResponse> {
  const { id, ...body } = input;
  return apiJson(
    `/api/spokespeople/${id}/clone-voice/`,
    { method: "POST", body },
    (json) => cloneVoiceResponseSchema.parse(json),
  );
}

export function useCloneVoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: cloneVoice,
    onSuccess: (data) => {
      // Refresh the single-resource cache + invalidate the list so
      // the workspace dashboard reflects voice_id changes when the
      // operator navigates back.
      qc.setQueryData(
        ["spokesperson", data.spokesperson.id],
        data.spokesperson,
      );
      qc.invalidateQueries({ queryKey: ["spokespeople"] });
    },
  });
}
