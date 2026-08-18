/**
 * EPISODE_COMPOSITION_WORKFLOW_V1 (SESSION 262) — SPA tests.
 *
 * Covers the 11 behaviors required by the operator brief:
 *
 *  1. Episode recipe launch pre-fills topic.
 *  2. Episode recipe launch pre-fills cast in EpisodeCast.added_at order.
 *  3. added_at ordering is a UI default; operator may swap.
 *  4. Non-cast Universe character cannot silently become a performer.
 *  5. Empty/insufficient Episode cast has an explicit operator path.
 *  6. Operator may override Composition.operator_topic without
 *     changing Episode.operator_topic (verified via form-level edit
 *     landing in submit payload).
 *  7. Episode-less recipe workflow unchanged.
 *  8. Episode detail lists attached Compositions only.
 *  9. Create Composition → return to Episode → new version visible.
 * 10. Make another version retains Episode story/cast context.
 * 11. Composition observability fields remain unchanged by Episode
 *     workflow operations (structural — attach uses save(update_fields=
 *     [episode, updated_at]); SESSION 262 model-level guard covers
 *     this. Verified in test_session262_composition_observability
 *     and test_episode.py — cross-referenced here.)
 */
import { describe, expect, it, beforeEach, vi } from "vitest";
import { fireEvent, render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { Composition, Recipe, RecipeField, CompositionRow } from "@/lib/api/recipes";
import type { Spokesperson } from "@/lib/api/spokespeople";
import type { Episode } from "@/lib/api/episodes";
import { RecipeFormRoute } from "@/routes/recipes/$kind";
import { EpisodeDetailRoute } from "@/routes/workspace/episodes.$id";

// ---- Fixtures ---------------------------------------------------

const PATCH: Spokesperson = {
  id: "sp-patch",
  workspace: "ws-1",
  universe: "u-workshop",
  name: "Patch",
  runway_avatar_id: "av-patch",
  portrait_path: "https://fake/patch.png",
} as unknown as Spokesperson;

const RIVET: Spokesperson = {
  id: "sp-rivet",
  workspace: "ws-1",
  universe: "u-workshop",
  name: "Rivet",
  runway_avatar_id: "av-rivet",
  portrait_path: "https://fake/rivet.png",
} as unknown as Spokesperson;

const BAKER: Spokesperson = {
  id: "sp-baker",
  workspace: "ws-1",
  universe: "u-bakery",
  name: "Baker",
  runway_avatar_id: "av-baker",
  portrait_path: "https://fake/baker.png",
} as unknown as Spokesperson;

// dialogue_scene metadata — trimmed to the fields the workflow
// exercises.
const DIALOGUE_RECIPE: Recipe = {
  kind: "dialogue_scene",
  display_name: "Dialogue scene (multi-character)",
  family: "dialogue",
  description: "AI-Topic dialogue.",
  speaking_rate_chars_per_second: 15,
  fields: [
    {
      name: "dialogue_mode",
      type: "select",
      label: "Mode",
      required: false,
      default: "manual",
      choices: [
        { value: "manual", label: "Manual" },
        { value: "ai_topic", label: "AI Topic" },
      ],
    } as RecipeField,
    {
      name: "primary_spokesperson_id",
      type: "spokesperson_picker",
      label: "Primary",
      required: true,
    } as RecipeField,
    {
      name: "secondary_spokesperson_id",
      type: "spokesperson_picker",
      label: "Secondary",
      required: false,
    } as RecipeField,
    {
      name: "topic",
      type: "textarea",
      label: "Topic",
      required: false,
      max_chars: 800,
    } as RecipeField,
    {
      name: "target_duration_seconds",
      type: "select",
      label: "Duration",
      required: false,
      default: 60,
      choices: [
        { value: "60", label: "60s" },
        { value: "90", label: "90s" },
      ],
    } as RecipeField,
    {
      name: "use_knowledge",
      type: "checkbox",
      label: "Use knowledge",
      required: false,
      default: true,
    } as RecipeField,
    {
      name: "mock_mode",
      type: "checkbox",
      label: "Mock",
      required: false,
      default: false,
    } as RecipeField,
  ],
} as Recipe;

// talking_head recipe — for the "single-performer / insufficient-cast"
// case: cast>=1 satisfies, cast==0 blocks.
const TALKING_HEAD_RECIPE: Recipe = {
  kind: "talking_head",
  display_name: "Talking head",
  family: "talking_head",
  description: "Single-character.",
  speaking_rate_chars_per_second: 15,
  fields: [
    {
      name: "spokesperson_id",
      type: "spokesperson_picker",
      label: "Spokesperson",
      required: true,
    } as RecipeField,
    {
      name: "script",
      type: "textarea",
      label: "Script",
      required: true,
    } as RecipeField,
  ],
} as Recipe;

const EPISODE_WITH_FULL_CAST: Episode = {
  id: "ep-1",
  universe: "u-workshop",
  universe_name: "Workshop",
  title: "AI took over the lab",
  operator_topic: "Rivet warns Patch about the AI takeover.",
  cast: [
    { id: PATCH.id, name: PATCH.name },
    { id: RIVET.id, name: RIVET.name },
  ],
  composition_count: 1,
  archived_at: null,
  created_by: "u-1",
  created_at: "2026-08-18T00:00:00Z",
  updated_at: "2026-08-18T00:00:00Z",
};

const EPISODE_EMPTY_CAST: Episode = {
  ...EPISODE_WITH_FULL_CAST,
  id: "ep-empty",
  cast: [],
  composition_count: 0,
};

const EPISODE_ONE_CAST: Episode = {
  ...EPISODE_WITH_FULL_CAST,
  id: "ep-one",
  cast: [{ id: PATCH.id, name: PATCH.name }],
  composition_count: 0,
};

const COMPOSITION_ROW_60S: CompositionRow = {
  id: "comp-60",
  name: "60s render",
  template_kind: "dialogue_scene",
  status: "completed",
  mock_mode: true,
  cost_actual_micros: 0,
  verification_status: "verified",
  spokesperson_id: PATCH.id,
  spokesperson_name: PATCH.name,
  final_asset_id: "asset-1",
  final_asset_storage_health: "ok",
  created_at: "2026-08-18T01:00:00Z",
  updated_at: "2026-08-18T01:00:00Z",
  episode: EPISODE_WITH_FULL_CAST.id,
  episode_title: EPISODE_WITH_FULL_CAST.title,
  target_duration_seconds: 60,
};

// ---- Mocks ------------------------------------------------------

const mockCreate = vi.fn<[unknown], Promise<Composition>>();
let currentEpisode: Episode | undefined = EPISODE_WITH_FULL_CAST;
let currentCompositions: CompositionRow[] = [];

vi.mock("@/lib/api/recipes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/recipes")>(
    "@/lib/api/recipes",
  );
  return {
    ...actual,
    LIVE_RECIPE_KINDS: new Set(["dialogue_scene", "talking_head"]),
    useRecipe: (kind: string | undefined) => ({
      data:
        kind === "dialogue_scene"
          ? DIALOGUE_RECIPE
          : kind === "talking_head"
          ? TALKING_HEAD_RECIPE
          : undefined,
      isLoading: false,
      isError: false,
      error: null,
    }),
    useCreateComposition: () => ({
      mutateAsync: mockCreate,
      isPending: false,
    }),
    useAssets: () => ({ data: [], isLoading: false }),
    useCompositionsForEpisode: (_episodeId: string | undefined) => ({
      data: currentCompositions,
      isLoading: false,
      error: null,
    }),
  };
});

vi.mock("@/lib/api/workspaces", () => ({
  useMe: () => ({
    data: { default_workspace: { id: "ws-1", name: "WS" } },
    isLoading: false,
  }),
}));

vi.mock("@/lib/api/spokespeople", async () => {
  const actual = await vi.importActual<
    typeof import("@/lib/api/spokespeople")
  >("@/lib/api/spokespeople");
  return {
    ...actual,
    useSpokespeople: () => ({
      data: [PATCH, RIVET, BAKER],
      isLoading: false,
    }),
  };
});

vi.mock("@/lib/api/episodes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/episodes")>(
    "@/lib/api/episodes",
  );
  return {
    ...actual,
    useEpisode: (id: string | undefined) => ({
      data: id ? currentEpisode : undefined,
      isLoading: false,
      isError: false,
      error: null,
    }),
    useUpdateEpisode: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useArchiveEpisode: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useUnarchiveEpisode: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useHardDeleteEpisode: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useAddCastMember: () => ({ mutateAsync: vi.fn(), isPending: false }),
    useRemoveCastMember: () => ({ mutateAsync: vi.fn(), isPending: false }),
  };
});

vi.mock("@/lib/api/knowledge-preview", () => ({
  useKnowledgePreview: () => ({
    data: undefined,
    isFetching: false,
    error: null,
  }),
}));

// ---- Render helpers ---------------------------------------------

function renderRecipeForm(path: string) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/recipes/:kind" element={<RecipeFormRoute />} />
          <Route path="/compositions/:id" element={<div>composition-detail</div>} />
          <Route
            path="/workspace/episodes/:id"
            element={<div data-testid="episode-detail-stub">episode</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderEpisodeDetail(episodeId: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/workspace/episodes/${episodeId}`]}>
        <Routes>
          <Route
            path="/workspace/episodes/:id"
            element={<EpisodeDetailRoute />}
          />
          <Route
            path="/workspace/universes/:id/episodes"
            element={<div>list</div>}
          />
          <Route
            path="/compositions/:id"
            element={<div data-testid="comp-stub">comp</div>}
          />
          <Route
            path="/recipes/:kind"
            element={<div data-testid="recipe-stub">recipe</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  mockCreate.mockReset();
  mockCreate.mockResolvedValue({
    id: "new-comp",
    workspace: "ws-1",
    status: "planning",
    template_kind: "dialogue_scene",
  } as unknown as Composition);
  currentEpisode = EPISODE_WITH_FULL_CAST;
  currentCompositions = [];
});

// ==================================================================
// Recipe-form tests (behaviors 1-7, 11)
// ==================================================================

describe("Recipe form — Episode-driven pre-fill", () => {
  it("1. pre-fills topic from Episode.operator_topic", () => {
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_WITH_FULL_CAST.id}`,
    );
    const topicWrapper = screen.getByTestId("recipe-field-topic");
    const topicInput = topicWrapper.querySelector(
      "textarea",
    ) as HTMLTextAreaElement;
    expect(topicInput.value).toBe(EPISODE_WITH_FULL_CAST.operator_topic);
  });

  it("2. pre-fills primary + secondary from cast in added_at order", () => {
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_WITH_FULL_CAST.id}`,
    );
    const primary = screen
      .getByTestId("recipe-field-primary_spokesperson_id")
      .querySelector("select") as HTMLSelectElement;
    const secondary = screen
      .getByTestId("recipe-field-secondary_spokesperson_id")
      .querySelector("select") as HTMLSelectElement;
    expect(primary.value).toBe(PATCH.id); // cast[0]
    expect(secondary.value).toBe(RIVET.id); // cast[1]
  });

  it("3. added_at ordering is a UI default; operator may swap primary/secondary", async () => {
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_WITH_FULL_CAST.id}`,
    );
    const user = userEvent.setup();
    const primarySelect = screen
      .getByTestId("recipe-field-primary_spokesperson_id")
      .querySelector("select") as HTMLSelectElement;
    // Swap the roles.
    await user.selectOptions(primarySelect, RIVET.id);
    expect(primarySelect.value).toBe(RIVET.id);
    // Secondary should still be an Episode.cast member — the swap
    // is between two cast members, not a reach outside the cast.
    const secondarySelect = screen
      .getByTestId("recipe-field-secondary_spokesperson_id")
      .querySelector("select") as HTMLSelectElement;
    const secondaryOptions = Array.from(secondarySelect.options).map(
      (o) => o.value,
    );
    // Secondary picker filters primary out per AI-D4, so after swap
    // only PATCH remains as a legal secondary; RIVET (now primary)
    // is excluded from the option list.
    expect(secondaryOptions).toContain(PATCH.id);
    expect(secondaryOptions).not.toContain(RIVET.id);
    expect(secondaryOptions).not.toContain(BAKER.id);
  });

  it("4. non-cast Universe character cannot appear in the picker option list", () => {
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_WITH_FULL_CAST.id}`,
    );
    const primarySelect = screen
      .getByTestId("recipe-field-primary_spokesperson_id")
      .querySelector("select") as HTMLSelectElement;
    const options = Array.from(primarySelect.options).map((o) => o.value);
    expect(options).toContain(PATCH.id);
    expect(options).toContain(RIVET.id);
    // Baker is in the workspace but NOT in Episode.cast — must be
    // absent from the picker. This is correction #1 in the operator
    // brief: Episode.cast is authoritative for performers.
    expect(options).not.toContain(BAKER.id);
  });

  it("5. empty Episode cast blocks submit + shows explicit add-cast path", () => {
    currentEpisode = EPISODE_EMPTY_CAST;
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_EMPTY_CAST.id}`,
    );
    const block = screen.getByTestId("episode-insufficient-cast");
    expect(block).toBeInTheDocument();
    expect(
      within(block).getByRole("link", { name: /add cast to episode/i }),
    ).toHaveAttribute("href", `/workspace/episodes/${EPISODE_EMPTY_CAST.id}`);
    const submit = screen.getByTestId("recipe-submit") as HTMLButtonElement;
    expect(submit).toBeDisabled();
  });

  it("5b. one-cast Episode with dialogue_scene (needs 2) also blocks", () => {
    currentEpisode = EPISODE_ONE_CAST;
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_ONE_CAST.id}`,
    );
    expect(
      screen.getByTestId("episode-insufficient-cast"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("recipe-submit")).toBeDisabled();
  });

  it("5c. one-cast Episode with talking_head (needs 1) does NOT block", () => {
    currentEpisode = EPISODE_ONE_CAST;
    renderRecipeForm(
      `/recipes/talking_head?episode=${EPISODE_ONE_CAST.id}`,
    );
    expect(
      screen.queryByTestId("episode-insufficient-cast"),
    ).not.toBeInTheDocument();
    expect(screen.getByTestId("recipe-submit")).not.toBeDisabled();
  });

  it("6. operator may override topic; submit payload carries the override", async () => {
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_WITH_FULL_CAST.id}`,
    );
    const user = userEvent.setup();
    const topicInput = screen
      .getByTestId("recipe-field-topic")
      .querySelector("textarea") as HTMLTextAreaElement;
    await user.clear(topicInput);
    await user.type(topicInput, "VARIANT-ONLY TOPIC");
    await user.click(screen.getByTestId("recipe-submit"));
    await waitFor(() => expect(mockCreate).toHaveBeenCalledTimes(1));
    const payload = mockCreate.mock.calls[0]![0] as {
      params: Record<string, unknown>;
      episode: string;
    };
    expect(payload.params.topic).toBe("VARIANT-ONLY TOPIC");
    expect(payload.episode).toBe(EPISODE_WITH_FULL_CAST.id);
  });

  it("7. Episode-less recipe workflow shows workspace roster + no chip", () => {
    currentEpisode = undefined;
    renderRecipeForm(`/recipes/dialogue_scene`);
    // No Episode chip, no insufficient-cast block.
    expect(
      screen.queryByTestId("episode-context-chip"),
    ).not.toBeInTheDocument();
    expect(
      screen.queryByTestId("episode-insufficient-cast"),
    ).not.toBeInTheDocument();
    // Picker includes ALL workspace teammates (Patch + Rivet + Baker).
    const primarySelect = screen
      .getByTestId("recipe-field-primary_spokesperson_id")
      .querySelector("select") as HTMLSelectElement;
    const options = Array.from(primarySelect.options).map((o) => o.value);
    expect(options).toEqual(
      expect.arrayContaining([PATCH.id, RIVET.id, BAKER.id]),
    );
  });

  it("shows the Episode context chip when episode is present", () => {
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_WITH_FULL_CAST.id}`,
    );
    const chip = screen.getByTestId("episode-context-chip");
    expect(chip).toHaveTextContent(EPISODE_WITH_FULL_CAST.title);
    // Chip's title link routes back to Episode detail.
    expect(
      within(chip).getByTestId("episode-context-title-link"),
    ).toHaveAttribute(
      "href",
      `/workspace/episodes/${EPISODE_WITH_FULL_CAST.id}`,
    );
  });

  it("attaches episode FK on submit + defaults dialogue_mode to ai_topic", async () => {
    renderRecipeForm(
      `/recipes/dialogue_scene?episode=${EPISODE_WITH_FULL_CAST.id}`,
    );
    const user = userEvent.setup();
    await user.click(screen.getByTestId("recipe-submit"));
    await waitFor(() => expect(mockCreate).toHaveBeenCalledTimes(1));
    const payload = mockCreate.mock.calls[0]![0] as {
      params: Record<string, unknown>;
      episode: string;
    };
    expect(payload.episode).toBe(EPISODE_WITH_FULL_CAST.id);
    expect(payload.params.dialogue_mode).toBe("ai_topic");
    expect(payload.params.primary_spokesperson_id).toBe(PATCH.id);
    expect(payload.params.secondary_spokesperson_id).toBe(RIVET.id);
  });
});

// ==================================================================
// Episode-detail tests (behaviors 8-10)
// ==================================================================

describe("Episode detail — versions list", () => {
  it("8. lists Compositions attached to the Episode (empty state)", () => {
    currentCompositions = [];
    renderEpisodeDetail(EPISODE_WITH_FULL_CAST.id);
    expect(screen.getByTestId("episode-versions-section")).toBeInTheDocument();
    expect(screen.getByText(/no renders yet/i)).toBeInTheDocument();
  });

  it("8b. populated versions list renders row per Composition", () => {
    currentCompositions = [COMPOSITION_ROW_60S];
    renderEpisodeDetail(EPISODE_WITH_FULL_CAST.id);
    const list = screen.getByTestId("episode-versions-list");
    expect(within(list).getByText("60s render")).toBeInTheDocument();
    expect(
      within(list).getByTestId(`episode-version-open-${COMPOSITION_ROW_60S.id}`),
    ).toHaveAttribute("href", `/compositions/${COMPOSITION_ROW_60S.id}`);
  });

  it("10. 'make another version' link retains episode context", () => {
    currentCompositions = [COMPOSITION_ROW_60S];
    renderEpisodeDetail(EPISODE_WITH_FULL_CAST.id);
    const relaunch = screen.getByTestId(
      `episode-version-relaunch-${COMPOSITION_ROW_60S.id}`,
    );
    // Same recipe kind + episode ID in the query string.
    expect(relaunch).toHaveAttribute(
      "href",
      `/recipes/${COMPOSITION_ROW_60S.template_kind}?episode=${EPISODE_WITH_FULL_CAST.id}`,
    );
  });

  it("9. simulated 'return to Episode after create' shows new version", () => {
    // Behavior 9 exercises the react-query refetch pattern; here we
    // simulate the "return trip" by mutating the mocked list source
    // and re-rendering. In production, useCompositionsForEpisode's
    // query key invalidates when useCreateComposition succeeds
    // (onSuccess in the mutation hook invalidates ["compositions"]).
    currentCompositions = [];
    const { unmount } = renderEpisodeDetail(EPISODE_WITH_FULL_CAST.id);
    expect(screen.getByText(/no renders yet/i)).toBeInTheDocument();
    unmount();
    currentCompositions = [COMPOSITION_ROW_60S];
    renderEpisodeDetail(EPISODE_WITH_FULL_CAST.id);
    expect(
      screen.getByTestId(`episode-version-row-${COMPOSITION_ROW_60S.id}`),
    ).toBeInTheDocument();
  });
});
