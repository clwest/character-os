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
  // W11.y (SESSION 175) — splits HOW (personality) from WHAT
  // (business_brief). ``.default("")`` keeps the schema parsing
  // pre-W11.y server responses cleanly (operator could roll
  // back the SPA to before the field existed).
  personality: z.string().default(""),
  visual_subject: z.string(),
  visual_template: z.enum(PORTRAIT_TEMPLATES),
  tone_archetype: z.enum(TONE_ARCHETYPES),
  status: z.enum(["setup_needed", "ready", "archived"]),
  runway_avatar_id: z.string(),
  runway_avatar_status: z.string(),
  portrait_path: z.string(),
  voice_id: z.string(),
  // SESSION 232 — Identity surface (contract rule 10). Five new
  // slots that pair with business_brief above to form the six
  // identity fields the customer fills on
  // ``/spokespeople/{id}/identity``. All ``.default("")`` so the
  // schema parses pre-232 server responses cleanly.
  who_you_help: z.string().default(""),
  what_you_sell: z.string().default(""),
  always_emphasize: z.string().default(""),
  never_say: z.string().default(""),
  desired_feeling: z.string().default(""),
  // Server-derived count of non-empty identity fields (range 0-6).
  // Drives the masthead button state ("Define {name}" when < 4;
  // plain "Identity" when >= 4) + the "N of 6 filled" progress
  // signal on the identity page.
  identity_fields_filled: z.number().int().min(0).max(6).default(0),
  // SESSION 253 — Character Voice / Writing Identity fields.
  // Six new fields on top of the existing identity surface. All
  // ``.default("...")`` so the schema parses pre-SESSION-253 server
  // responses cleanly.
  character_point_of_view: z.string().default(""),
  voice_energy: z.enum(["low", "medium", "high"]).default("medium"),
  voice_humor: z.enum(["none", "dry", "warm", "playful"]).default("warm"),
  voice_directness: z.enum(["soft", "balanced", "direct"]).default("balanced"),
  voice_signature_phrases: z.string().default(""),
  voice_avoid_phrases: z.string().default(""),
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
  // W11.y (SESSION 175) — HOW the spokesperson speaks. Optional
  // at create time; defaults to "" (operator can edit later).
  personality?: string;
  /** Free-text "what this spokesperson looks like" — "armored
   * battle unicorn", "neon-pink raccoon". Persists on the row;
   * Wizard Step 2 (W7) threads it into `/internal/portrait/`
   * generation when no portrait_data_uri is supplied. */
  visual_subject?: string;
  /** Portrait template (mascot / founder / coach / local_guide).
   * Wizard Step 1 tile choice. Persists on the row so re-bake
   * (W11.2) can reuse it instead of falling back to a hardcoded
   * default. SESSION 171 fix — pre-fix, the rebake hardcoded
   * `coach`, which silently flipped Marcus from a battle
   * unicorn to a photorealistic human. */
  visual_template?: PortraitTemplate;
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


// ---- W11.2 — voice swap + avatar re-bake -------------------------

const changeVoiceResponseSchema = z.object({
  spokesperson: spokespersonSchema,
  voice_patch: z.object({
    status: z.string(),
    error: z.string().nullable(),
  }),
});

export type ChangeVoiceResponse = z.infer<typeof changeVoiceResponseSchema>;

export interface ChangeVoiceInput {
  id: string;
  preset: string;
}

export async function changeSpokespersonVoice(
  input: ChangeVoiceInput,
): Promise<ChangeVoiceResponse> {
  return apiJson(
    `/api/spokespeople/${input.id}/change-voice/`,
    { method: "POST", body: { preset: input.preset } },
    (json) => changeVoiceResponseSchema.parse(json),
  );
}

export function useChangeVoice() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: changeSpokespersonVoice,
    onSuccess: (result) => {
      qc.setQueryData(
        ["spokesperson", result.spokesperson.id],
        result.spokesperson,
      );
      qc.invalidateQueries({ queryKey: ["spokespeople"] });
    },
  });
}

export interface RebakeAvatarInput {
  id: string;
  visual_subject?: string;
  voice_preset?: string;
  template?: PortraitTemplate;
}

export async function rebakeSpokespersonAvatar(
  input: RebakeAvatarInput,
): Promise<Spokesperson> {
  const { id, ...payload } = input;
  return apiJson(
    `/api/spokespeople/${id}/rebake-avatar/`,
    { method: "POST", body: payload },
    (json) => spokespersonSchema.parse(json),
  );
}

export function useRebakeAvatar() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: rebakeSpokespersonAvatar,
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
   * fields per the serializer: name, business_brief, personality,
   * visual_subject, tone_archetype, plus the SESSION 232 identity
   * slots below. Voice + avatar are read-only on this path
   * (separate action endpoints; W11.2 wired). */
  name?: string;
  business_brief?: string;
  personality?: string;
  visual_subject?: string;
  tone_archetype?: ToneArchetype;
  /** SESSION 232 — Identity surface. Any of these can be PATCHed
   * individually or bundled into a single Save from the identity
   * page. All accept empty strings. */
  who_you_help?: string;
  what_you_sell?: string;
  always_emphasize?: string;
  never_say?: string;
  desired_feeling?: string;
  /** SESSION 253 — Character Voice / Writing Identity. All
   * optional; backend defaults handle new-row shape. */
  character_point_of_view?: string;
  voice_energy?: "low" | "medium" | "high";
  voice_humor?: "none" | "dry" | "warm" | "playful";
  voice_directness?: "soft" | "balanced" | "direct";
  voice_signature_phrases?: string;
  voice_avoid_phrases?: string;
}

// ---- SESSION 232 — Identity surface metadata ---------------------
//
// Six identity slots per the design lock at
// ``docs/design/CUSTOMER_JOURNEY_V1.md`` §"The six identity slots".
// Ordered: business → audience → offering → positive → guardrails
// → felt outcome. Slot 1 is the existing ``business_brief``; the
// other five landed with the SESSION 232 migration.
//
// Labels and one-line help are name-interpolated at render time via
// ``interpolateSpokespersonName(...)`` — no hardcoded "Oliver".

export type IdentityFieldName =
  | "business_brief"
  | "who_you_help"
  | "what_you_sell"
  | "always_emphasize"
  | "never_say"
  | "desired_feeling"
  // SESSION 253 — Character Voice fields.
  | "character_point_of_view"
  | "voice_energy"
  | "voice_humor"
  | "voice_directness"
  | "voice_signature_phrases"
  | "voice_avoid_phrases";

/** SESSION 253 — visual grouping for the identity page. The
 * Identity group is the existing six SESSION 232 slots; the
 * Character Voice group is the SESSION 253 additions. */
export type IdentityFieldGroup = "identity" | "character_voice";

/** SESSION 253 — the identity page renders textareas for
 * free-text fields (existing behavior) and select dropdowns for
 * the three voice axes. Empty ``choices`` implies ``textarea``. */
export interface IdentityFieldChoice {
  value: string;
  label: string;
}

export interface IdentityFieldMeta {
  name: IdentityFieldName;
  label: string;
  /** Character OS one-line help. ``{name}`` is interpolated. */
  help: string;
  /** Grayed placeholder example shown inside the empty field. */
  placeholder: string;
  /** SESSION 253 — visual grouping on the identity page.
   * Missing = "identity" (the six SESSION 232 slots). */
  group?: IdentityFieldGroup;
  /** SESSION 253 — rendered as a `<select>` when ``choices`` is
   * non-empty; otherwise as the existing textarea. */
  choices?: readonly IdentityFieldChoice[];
}

export const IDENTITY_FIELDS: readonly IdentityFieldMeta[] = [
  {
    name: "business_brief",
    label: "What your business does",
    help: "One clear sentence.",
    placeholder: "e.g. Small-batch coffee roaster in Boulder, Colorado.",
  },
  {
    name: "who_you_help",
    label: "Who do you help?",
    help: "Who is {name} talking to?",
    placeholder: "e.g. Home brewers who care about origin and craft, plus specialty cafes stocking single-origin beans.",
  },
  {
    name: "what_you_sell",
    label: "What you sell",
    help: "Products, services, offerings — just the shape, not a full catalog.",
    placeholder: "e.g. Single-origin whole beans, a monthly subscription box, and wholesale for cafes.",
  },
  {
    name: "always_emphasize",
    label: "What {name} should always emphasize",
    help: "The things you want in every video and every conversation.",
    placeholder: "e.g. Small-batch, roasted-to-order, transparent sourcing, family-run since 2019.",
  },
  {
    name: "never_say",
    label: "What {name} should never say",
    help: "Guardrails. Off-limits topics, competitor names, legal claims.",
    placeholder: "e.g. Never claim organic without certification. Don't mention competitors by name.",
  },
  {
    name: "desired_feeling",
    label: "How should people feel after talking to {name}?",
    help: "The emotional outcome — not personality, how they walk away.",
    placeholder: "e.g. Trusted, unhurried, and a little more curious about what makes a great cup of coffee.",
  },
  // SESSION 253 — Character Voice group. Shapes HOW {name}
  // writes; orthogonal to WHAT the business is / does.
  {
    name: "character_point_of_view",
    label: "{name}'s point of view",
    help: "What does {name} notice, believe, enjoy, dislike, or have opinions about? Give them a point of view rather than describing their personality.",
    placeholder: "e.g. {name} notices nervous beginners first. Finds performative outdoors culture a little silly. Believes anyone can belong outside without expensive gear.",
    group: "character_voice",
  },
  {
    name: "voice_energy",
    label: "Energy level",
    help: "How energetic {name}'s writing feels.",
    placeholder: "",
    group: "character_voice",
    choices: [
      { value: "low", label: "Low — calm, deliberate" },
      { value: "medium", label: "Medium — natural pace" },
      { value: "high", label: "High — brisk, animated" },
    ],
  },
  {
    name: "voice_humor",
    label: "Humor style",
    help: "The single biggest generic-AI tell is uniformly humorless writing.",
    placeholder: "",
    group: "character_voice",
    choices: [
      { value: "none", label: "None — straight, sincere" },
      { value: "dry", label: "Dry — occasional understatement" },
      { value: "warm", label: "Warm — friendly, light" },
      { value: "playful", label: "Playful — quick, mischievous" },
    ],
  },
  {
    name: "voice_directness",
    label: "How directly {name} sells or makes asks",
    help: "Shapes CTA phrasing and opinion strength.",
    placeholder: "",
    group: "character_voice",
    choices: [
      { value: "soft", label: "Soft — invitational" },
      { value: "balanced", label: "Balanced — matter-of-fact" },
      { value: "direct", label: "Direct — asks plainly" },
    ],
  },
  {
    name: "voice_signature_phrases",
    label: "Phrases {name} might use",
    help: "Possibilities, one per line — not required catchphrases. Used occasionally when they fit, never forced.",
    placeholder: "e.g.\ncome curious\nsee you on the water",
    group: "character_voice",
  },
  {
    name: "voice_avoid_phrases",
    label: "Phrases {name} would never use",
    help: "One per line. Merged with our default anti-AI-copy list at write time.",
    placeholder: "e.g.\nunforgettable memories\nembrace the journey",
    group: "character_voice",
  },
] as const;

/** Threshold at which the masthead button flips from
 * "Define {name}" to plain "Identity" (design lock: 4 of 6). */
export const IDENTITY_FILLED_THRESHOLD = 4;

/** Interpolate a spokesperson's name into a copy string. No
 * hardcoded "Oliver" — customers name their spokesperson. */
export function interpolateSpokespersonName(
  text: string,
  spokespersonName: string,
): string {
  return text.replace(/\{name\}/g, spokespersonName);
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

// ---- Delete (SESSION 251) -----------------------------------------
//
// Customer-facing delete. Backend contract:
// ``DELETE /api/spokespeople/<id>/`` returns 204 on success and
// 404 for cross-workspace (queryset filter hides the row).
// Historical outputs (compositions, assets, transcripts, scripts,
// campaigns, threads) survive via SET_NULL migrations; the M2M
// knowledge attach rows CASCADE (doc + chunks preserved).

async function deleteSpokesperson(id: string): Promise<void> {
  await apiJson<void>(`/api/spokespeople/${id}/`, { method: "DELETE" });
}

export function useDeleteSpokesperson() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: deleteSpokesperson,
    onSuccess: (_void, id) => {
      // Drop the single-resource cache so any lingering routes
      // that read it get a fresh 404 instead of stale data.
      qc.removeQueries({ queryKey: ["spokesperson", id] });
      // Invalidate every surface that lists or aggregates teammates
      // so the dashboard, spokesperson grid, workspace overview
      // (spokespeople panel counts + activity feed), and videos
      // library reflect the removal after redirect.
      qc.invalidateQueries({ queryKey: ["spokespeople"] });
      qc.invalidateQueries({ queryKey: ["workspace-overview"] });
    },
  });
}

// ---- Chapter 6 slice-1 — Ask + receipt (SESSION 234) --------------
//
// One-turn Q&A against the spokesperson's visible knowledge. Backend
// contract: shell/apps/spokespeople/views.py::SpokespersonViewSet.ask.
// Ship bar mirrored here: citations name ONLY docs whose chunks
// were placed in the model context; ``used_knowledge=false`` implies
// ``citations: []`` and the SPA renders the honest-fallback receipt.

const askCitationSchema = z.object({
  document_id: z.string(),
  title: z.string(),
  chunk_count: z.number().int().nonnegative(),
});

export type AskCitation = z.infer<typeof askCitationSchema>;

const askResponseSchema = z.object({
  answer: z.string(),
  citations: z.array(askCitationSchema),
  used_knowledge: z.boolean(),
  model: z.string(),
});

export type AskResponse = z.infer<typeof askResponseSchema>;

export interface AskSpokespersonInput {
  id: string;
  question: string;
}

export async function askSpokesperson(
  input: AskSpokespersonInput,
): Promise<AskResponse> {
  return apiJson(
    `/api/spokespeople/${input.id}/ask/`,
    { method: "POST", body: { question: input.question } },
    (json) => askResponseSchema.parse(json),
  );
}

export function useAskSpokesperson() {
  return useMutation({
    mutationFn: askSpokesperson,
    // No cache invalidation — asks are read-only against the
    // knowledge corpus; nothing on the row or workspace changes.
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
//
// SESSION 230 — voice sampling (Chapter 2 Beat 3): shape gained
// ``sample_url`` per preset so the picker can play a short clip
// before the operator commits. ``sample_url`` is nullable so the
// UI gracefully renders a "coming soon" state for presets whose
// clip has not been baked yet.

const voicePresetSchema = z.object({
  name: z.string(),
  sample_url: z.string().nullable(),
});

export type VoicePreset = z.infer<typeof voicePresetSchema>;

const voicePresetsResponseSchema = z.object({
  presets: z.array(voicePresetSchema),
});

export async function listVoicePresets(): Promise<VoicePreset[]> {
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
