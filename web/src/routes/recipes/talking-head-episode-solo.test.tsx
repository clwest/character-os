/**
 * SESSION 269 §15 — Episode-solo talking_head UX tests.
 *
 * Scope: only the §15 additions to the shared recipe form
 * (`web/src/routes/recipes/$kind.tsx`). Companion to
 * `episode-composition-workflow.test.tsx` (SESSION 262) and
 * `episode-cast-picker.test.tsx` (SESSION 269 §12).
 *
 * Behaviours proven:
 *  1. talking_head + episode + cast.length==1 renders the
 *     read-only "Story intent" display containing
 *     Episode.operator_topic.
 *  2. talking_head + episode + cast.length==1 HIDES the Script/topic
 *     textarea AND the Use workspace knowledge checkbox.
 *  3. Submit force-supplies script=episode.operator_topic +
 *     use_knowledge=true so the backend receives the same wire
 *     shape a standalone AI-topic submit produces (backend then
 *     routes to the solo_scene writing contract via the
 *     `composition.episode_id + template_kind` discriminator).
 *  4. Standalone /recipes/talking_head (no episode) renders the
 *     classic dual-mode form unchanged — the Script/topic
 *     textarea + Use workspace knowledge checkbox are visible.
 *  5. Episode with cast.length != 1 does NOT activate solo mode
 *     (defense-in-depth — the Episode-detail CTA already gates
 *     on cast.length==1, but the recipe-form guard is
 *     belt-and-braces).
 */
import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { Composition, Recipe, RecipeField } from "@/lib/api/recipes";
import type { Spokesperson } from "@/lib/api/spokespeople";
import type { Episode } from "@/lib/api/episodes";
import { RecipeFormRoute } from "@/routes/recipes/$kind";

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

const TALKING_HEAD_RECIPE: Recipe = {
  kind: "talking_head",
  display_name: "Talking head",
  family: "talking_head",
  description: "One spokesperson speaking a script or topic.",
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
      label: "Script or topic",
      required: true,
      min_chars: 8,
      max_chars: 4000,
    } as RecipeField,
    {
      name: "use_knowledge",
      type: "checkbox",
      label: "Use workspace knowledge",
      required: false,
      default: false,
    } as RecipeField,
    {
      name: "target_duration_seconds",
      type: "select",
      label: "Target duration",
      required: false,
      default: "",
      choices: [
        { value: "", label: "No target" },
        { value: 60, label: "60s" },
        { value: 90, label: "90s" },
      ],
    } as RecipeField,
  ],
} as unknown as Recipe;

const SOLO_EPISODE: Episode = {
  id: "ep-solo",
  universe: "u-workshop",
  universe_name: "Workshop",
  title: "Patch does research on AI Agents",
  operator_topic: "Patch does research on AI Agents",
  cast: [{ id: PATCH.id, name: PATCH.name }],
  composition_count: 0,
  archived_at: null,
  created_by: null,
  created_at: "2026-08-19T00:00:00Z",
  updated_at: "2026-08-19T00:00:00Z",
} as unknown as Episode;

const TWO_HANDER_EPISODE: Episode = {
  ...SOLO_EPISODE,
  id: "ep-two",
  title: "Two hander",
  operator_topic: "Two hander",
  cast: [
    { id: PATCH.id, name: PATCH.name },
    { id: RIVET.id, name: RIVET.name },
  ],
} as unknown as Episode;

// ---- Mocks ------------------------------------------------------

const mockCreate = vi.fn<[unknown], Promise<Composition>>();
let currentEpisode: Episode | undefined;

vi.mock("@/lib/api/recipes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/recipes")>(
    "@/lib/api/recipes",
  );
  return {
    ...actual,
    LIVE_RECIPE_KINDS: new Set(["talking_head", "dialogue_scene"]),
    useRecipe: (kind: string | undefined) => ({
      data: kind === "talking_head" ? TALKING_HEAD_RECIPE : undefined,
      isLoading: false,
      isError: false,
      error: null,
    }),
    useCreateComposition: () => ({
      mutateAsync: mockCreate,
      isPending: false,
    }),
    useAssets: () => ({ data: [], isLoading: false }),
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
      data: [PATCH, RIVET],
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
  };
});

vi.mock("@/lib/api/knowledge-preview", () => ({
  useKnowledgePreview: () => ({
    data: undefined,
    isFetching: false,
    error: null,
  }),
}));

// ---- Render helper ----------------------------------------------

function renderRecipeForm(path: string) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[path]}>
        <Routes>
          <Route path="/recipes/:kind" element={<RecipeFormRoute />} />
          <Route
            path="/compositions/:id"
            element={<div data-testid="comp-stub">comp</div>}
          />
          <Route
            path="/workspace/episodes/:id"
            element={<div>episode</div>}
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
    template_kind: "talking_head",
  } as unknown as Composition);
  currentEpisode = undefined;
});

// ==================================================================
// Episode-solo mode (cast.length === 1)
// ==================================================================

describe("Episode-solo talking_head (SESSION 269 §15)", () => {
  it("1. renders read-only Story intent with Episode.operator_topic", async () => {
    currentEpisode = SOLO_EPISODE;
    renderRecipeForm(`/recipes/talking_head?episode=${SOLO_EPISODE.id}`);

    const intent = await screen.findByTestId("episode-solo-story-intent");
    expect(intent.textContent).toContain(SOLO_EPISODE.operator_topic);
    // Chris-facing wording — the label makes it explicit that
    // Episode owns the intent.
    expect(intent.textContent).toContain("Story intent (owned by Episode)");
  });

  it("2. HIDES Script/topic textarea AND Use workspace knowledge checkbox", async () => {
    currentEpisode = SOLO_EPISODE;
    renderRecipeForm(`/recipes/talking_head?episode=${SOLO_EPISODE.id}`);

    await screen.findByTestId("episode-solo-story-intent");
    // The Script/topic textarea would normally have a
    // data-testid="recipe-field-script" wrapper; it must NOT
    // appear in Episode-solo mode.
    expect(screen.queryByTestId("recipe-field-script")).toBeNull();
    // The Use workspace knowledge checkbox likewise.
    expect(screen.queryByTestId("recipe-field-use_knowledge")).toBeNull();
    // But the Target duration control REMAINS visible (KEEP per
    // §14.7 classification).
    expect(
      screen.getByTestId("recipe-field-target_duration_seconds"),
    ).toBeTruthy();
  });

  it(
    "3. submits with script=episode.operator_topic + use_knowledge=true silently forced",
    async () => {
      const user = userEvent.setup();
      currentEpisode = SOLO_EPISODE;
      renderRecipeForm(`/recipes/talking_head?episode=${SOLO_EPISODE.id}`);

      // Wait for form to render and mount.
      await screen.findByTestId("episode-solo-story-intent");
      // Submit as-is — the hidden fields' values must be forced
      // into the payload without operator input.
      await user.click(screen.getByTestId("recipe-submit"));

      await waitFor(() => {
        expect(mockCreate).toHaveBeenCalledTimes(1);
      });
      const payload = mockCreate.mock.calls[0][0] as {
        kind: string;
        params: Record<string, unknown>;
        episode?: string;
      };
      expect(payload.kind).toBe("talking_head");
      expect(payload.episode).toBe(SOLO_EPISODE.id);
      expect(payload.params.script).toBe(SOLO_EPISODE.operator_topic);
      expect(payload.params.use_knowledge).toBe(true);
      // Spokesperson prefill still populated from Episode.cast[0].
      expect(payload.params.spokesperson_id).toBe(PATCH.id);
    },
  );
});

// ==================================================================
// Standalone regression + defense-in-depth
// ==================================================================

describe("Standalone talking_head unchanged (regression)", () => {
  it("4. standalone /recipes/talking_head still shows Script/topic + Use workspace knowledge", async () => {
    currentEpisode = undefined;
    renderRecipeForm("/recipes/talking_head");

    // The Script/topic textarea AND the Use workspace knowledge
    // checkbox must remain visible on the standalone path.
    expect(await screen.findByTestId("recipe-field-script")).toBeTruthy();
    expect(screen.getByTestId("recipe-field-use_knowledge")).toBeTruthy();
    // No Story intent block on standalone.
    expect(screen.queryByTestId("episode-solo-story-intent")).toBeNull();
  });

  it("5. two-cast Episode does NOT activate solo mode", async () => {
    currentEpisode = TWO_HANDER_EPISODE;
    renderRecipeForm(
      `/recipes/talking_head?episode=${TWO_HANDER_EPISODE.id}`,
    );

    // Wait for the Episode chip to render so we know the form
    // has completed its first render pass.
    await screen.findByTestId("episode-context-chip");
    // Story intent block is Episode-solo-only.
    expect(screen.queryByTestId("episode-solo-story-intent")).toBeNull();
    // Script + use_knowledge remain visible (the recipe-form
    // guard is defense-in-depth against the CTA gating; both
    // controls stay available to the operator).
    expect(screen.getByTestId("recipe-field-script")).toBeTruthy();
    expect(screen.getByTestId("recipe-field-use_knowledge")).toBeTruthy();
  });
});
