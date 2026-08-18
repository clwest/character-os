/**
 * SESSION 257 / AI-D4 — dialogue_scene SPA mode toggle +
 * per-mode field visibility tests.
 *
 * Covers:
 * - Mode select renders and defaults to manual.
 * - Per-mode field visibility (manual shows DialogueLinesEditor +
 *   hides AI fields; AI Topic hides DialogueLinesEditor + shows
 *   AI fields).
 * - Both modes keep shared fields (outro, name, mock_mode) visible.
 * - Mode-switch preserves local state (switching back restores the
 *   previously-visible editor).
 * - Submission payload only includes active-mode fields; stale
 *   hidden values don't leak to the backend.
 * - Cross-recipe non-regression: talking_head's field set is not
 *   affected by dialogue mode logic.
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import type { Composition } from "@/lib/api/recipes";
import type { Recipe, RecipeField } from "@/lib/api/recipes";
import type { Spokesperson } from "@/lib/api/spokespeople";
import { RecipeFormRoute } from "./$kind";

// ---- Test fixtures ------------------------------------------------

const PATCH: Spokesperson = {
  id: "sp-patch",
  workspace: "ws-1",
  name: "Patch",
  runway_avatar_id: "av-patch",
  portrait_path: "https://fake/patch.png",
} as unknown as Spokesperson;

const RIVET: Spokesperson = {
  id: "sp-rivet",
  workspace: "ws-1",
  name: "Rivet",
  runway_avatar_id: "av-rivet",
  portrait_path: "https://fake/rivet.png",
} as unknown as Spokesperson;

// Dialogue_scene recipe metadata matching AI-D3 backend shape.
const DIALOGUE_RECIPE: Recipe = {
  kind: "dialogue_scene",
  display_name: "Dialogue scene (multi-character)",
  family: "dialogue",
  description: "Manual + AI Topic multi-character dialogue.",
  speaking_rate_chars_per_second: 15,
  fields: [
    {
      name: "dialogue_mode",
      type: "select",
      label: "How should Character OS build this?",
      required: false,
      default: "manual",
      choices: [
        { value: "manual", label: "I'll write each line" },
        { value: "ai_topic", label: "Character OS writes it from a topic" },
      ],
    } as RecipeField,
    {
      name: "primary_spokesperson_id",
      type: "spokesperson_picker",
      label: "Primary spokesperson (owner / narrator)",
      required: true,
    } as RecipeField,
    {
      name: "lines",
      type: "dialogue_lines",
      label: "Dialogue lines",
      required: false,
    } as RecipeField,
    {
      name: "secondary_spokesperson_id",
      type: "spokesperson_picker",
      label: "Second character",
      required: false,
    } as RecipeField,
    {
      name: "topic",
      type: "textarea",
      label: "What's the scene about?",
      required: false,
      max_chars: 800,
    } as RecipeField,
    {
      name: "target_duration_seconds",
      type: "select",
      label: "Target duration",
      required: false,
      // SESSION 264 post-Terra-dogfood — Episode Dialogue Scene
      // default raised from "60" to "90". Mock schema matches the
      // real backend registry (see recipes.py:1573 in Python).
      default: "90",
      choices: [
        { value: "30", label: "~30 seconds" },
        { value: "60", label: "~60 seconds" },
        { value: "90", label: "~90 seconds" },
        { value: "120", label: "~120 seconds" },
      ],
    } as RecipeField,
    {
      name: "use_knowledge",
      type: "checkbox",
      label: "Use workspace knowledge",
      required: false,
      default: true,
    } as RecipeField,
    {
      name: "verifier_mode",
      type: "select",
      label: "Fact-check mode",
      required: false,
      default: "warn",
      choices: [
        { value: "warn", label: "Warn" },
        { value: "strict", label: "Strict" },
        { value: "off", label: "Off" },
      ],
    } as RecipeField,
    {
      name: "opener",
      type: "text",
      label: "Opening line (optional)",
      required: false,
      max_chars: 240,
    } as RecipeField,
    {
      name: "outro_text",
      type: "text",
      label: "Brand outro card (optional)",
      required: false,
      max_chars: 80,
    } as RecipeField,
    {
      name: "name",
      type: "text",
      label: "Composition name (optional)",
      required: false,
      max_chars: 200,
    } as RecipeField,
    {
      name: "mock_mode",
      type: "checkbox",
      label: "Mock mode (skip real provider calls)",
      required: false,
      default: false,
    } as RecipeField,
  ],
};

// Talking_head metadata for the non-regression test — must NOT
// see dialogue-mode visibility filtering.
const TALKING_HEAD_RECIPE: Recipe = {
  kind: "talking_head",
  display_name: "Talking head",
  family: "talking_head",
  description: "Single-character talking head.",
  speaking_rate_chars_per_second: 15,
  fields: [
    {
      name: "primary_spokesperson_id",
      type: "spokesperson_picker",
      label: "Primary spokesperson",
      required: true,
    } as RecipeField,
    {
      name: "script",
      type: "textarea",
      label: "Script or topic",
      required: true,
      max_chars: 800,
    } as RecipeField,
    {
      name: "use_knowledge",
      type: "checkbox",
      label: "Use workspace knowledge",
      required: false,
      default: false,
    } as RecipeField,
    {
      name: "opener",
      type: "text",
      label: "Opening line (optional)",
      required: false,
      max_chars: 240,
    } as RecipeField,
    {
      name: "outro_text",
      type: "text",
      label: "Outro card (optional)",
      required: false,
      max_chars: 80,
    } as RecipeField,
  ],
};

// ---- Hook mocks ---------------------------------------------------

const mockCreate = vi.fn<[unknown], Promise<Composition>>();

vi.mock("@/lib/api/recipes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/recipes")>(
    "@/lib/api/recipes",
  );
  return {
    ...actual,
    // Make dialogue_scene + talking_head live so the form renders.
    LIVE_RECIPE_KINDS: new Set(["dialogue_scene", "talking_head"]),
    useRecipe: (kind: string | undefined) => {
      if (kind === "dialogue_scene") {
        return {
          data: DIALOGUE_RECIPE,
          isLoading: false,
          isError: false,
          error: null,
        };
      }
      if (kind === "talking_head") {
        return {
          data: TALKING_HEAD_RECIPE,
          isLoading: false,
          isError: false,
          error: null,
        };
      }
      return {
        data: undefined,
        isLoading: false,
        isError: true,
        error: new Error("unknown recipe"),
      };
    },
    useCreateComposition: () => ({
      mutateAsync: mockCreate,
      isPending: false,
    }),
    useAssets: () => ({ data: [], isLoading: false }),
  };
});

vi.mock("@/lib/api/workspaces", () => ({
  useMe: () => ({
    data: {
      default_workspace: { id: "ws-1", name: "WS" },
    },
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

vi.mock("@/lib/api/knowledge-preview", () => ({
  useKnowledgePreview: () => ({
    data: undefined,
    isFetching: false,
    error: null,
  }),
}));

// ---- Render helper ------------------------------------------------

function renderRoute(kind: string) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/recipes/${kind}`]}>
        <Routes>
          <Route path="/recipes/:kind" element={<RecipeFormRoute />} />
          <Route path="/compositions/:id" element={<div>composition-detail</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---- Tests --------------------------------------------------------

describe("dialogue_scene SPA (AI-D4)", () => {
  beforeEach(() => {
    mockCreate.mockReset();
    mockCreate.mockResolvedValue({
      id: "comp-1",
      workspace: "ws-1",
      status: "planning",
      template_kind: "dialogue_scene",
    } as unknown as Composition);
  });

  // 1. Dialogue mode control renders.
  it("renders the dialogue_mode select at the top of the form", () => {
    renderRoute("dialogue_scene");
    const wrapper = screen.getByTestId("recipe-field-dialogue_mode");
    expect(wrapper).toBeInTheDocument();
    const select = wrapper.querySelector("select") as HTMLSelectElement;
    expect(select.value).toBe("manual");
  });

  // 2. Manual mode shows DialogueLinesEditor.
  it("shows the DialogueLinesEditor in manual mode", () => {
    renderRoute("dialogue_scene");
    expect(screen.getByTestId("dialogue-lines-editor")).toBeInTheDocument();
  });

  // 3. Manual mode hides AI-only fields.
  it("hides AI-only fields in manual mode", () => {
    renderRoute("dialogue_scene");
    expect(
      screen.queryByTestId("recipe-field-secondary_spokesperson_id"),
    ).toBeNull();
    expect(screen.queryByTestId("recipe-field-topic")).toBeNull();
    expect(
      screen.queryByTestId("recipe-field-target_duration_seconds"),
    ).toBeNull();
    expect(screen.queryByTestId("recipe-field-use_knowledge")).toBeNull();
    expect(screen.queryByTestId("recipe-field-verifier_mode")).toBeNull();
    expect(screen.queryByTestId("recipe-field-opener")).toBeNull();
  });

  // 4. AI Topic mode hides DialogueLinesEditor.
  it("hides the DialogueLinesEditor in AI Topic mode", async () => {
    const user = userEvent.setup();
    renderRoute("dialogue_scene");
    const wrapper = screen.getByTestId("recipe-field-dialogue_mode");
    const select = wrapper.querySelector("select") as HTMLSelectElement;
    await user.selectOptions(select, "ai_topic");
    expect(screen.queryByTestId("dialogue-lines-editor")).toBeNull();
    expect(screen.queryByTestId("recipe-field-lines")).toBeNull();
  });

  // 5. AI Topic mode shows secondary character.
  // 6. AI Topic mode shows topic.
  // 7. AI Topic mode shows target duration.
  // 8. AI Topic mode shows use-knowledge control.
  // 9. AI Topic mode shows verifier control.
  // 10. AI Topic mode shows opener.
  it("shows every AI-only field in AI Topic mode", async () => {
    const user = userEvent.setup();
    renderRoute("dialogue_scene");
    const modeWrapper = screen.getByTestId("recipe-field-dialogue_mode");
    const modeSelect = modeWrapper.querySelector("select") as HTMLSelectElement;
    await user.selectOptions(modeSelect, "ai_topic");
    for (const name of [
      "secondary_spokesperson_id",
      "topic",
      "target_duration_seconds",
      "use_knowledge",
      "verifier_mode",
      "opener",
    ]) {
      expect(
        screen.getByTestId(`recipe-field-${name}`),
        `expected AI-mode field ${name} to render`,
      ).toBeInTheDocument();
    }
  });

  // 11. Outro remains visible in both modes.
  // 12. Name remains visible in both modes.
  // 13. Mock mode remains visible in both modes.
  it("keeps outro, name, mock_mode visible in both modes", async () => {
    const user = userEvent.setup();
    renderRoute("dialogue_scene");
    // Manual mode
    expect(screen.getByTestId("recipe-field-outro_text")).toBeInTheDocument();
    expect(screen.getByTestId("recipe-field-name")).toBeInTheDocument();
    expect(screen.getByTestId("recipe-field-mock_mode")).toBeInTheDocument();
    // Switch to AI Topic
    const modeWrapper = screen.getByTestId("recipe-field-dialogue_mode");
    const modeSelect = modeWrapper.querySelector("select") as HTMLSelectElement;
    await user.selectOptions(modeSelect, "ai_topic");
    expect(screen.getByTestId("recipe-field-outro_text")).toBeInTheDocument();
    expect(screen.getByTestId("recipe-field-name")).toBeInTheDocument();
    expect(screen.getByTestId("recipe-field-mock_mode")).toBeInTheDocument();
  });

  // 14. Switching Manual → AI hides manual editor.
  it("hides DialogueLinesEditor when switching Manual → AI", async () => {
    const user = userEvent.setup();
    renderRoute("dialogue_scene");
    expect(screen.getByTestId("dialogue-lines-editor")).toBeInTheDocument();
    const modeWrapper = screen.getByTestId("recipe-field-dialogue_mode");
    const modeSelect = modeWrapper.querySelector("select") as HTMLSelectElement;
    await user.selectOptions(modeSelect, "ai_topic");
    expect(screen.queryByTestId("dialogue-lines-editor")).toBeNull();
  });

  // 15. Switching AI → Manual restores manual editor.
  it("restores DialogueLinesEditor when switching AI → Manual", async () => {
    const user = userEvent.setup();
    renderRoute("dialogue_scene");
    const modeWrapper = screen.getByTestId("recipe-field-dialogue_mode");
    const modeSelect = modeWrapper.querySelector("select") as HTMLSelectElement;
    await user.selectOptions(modeSelect, "ai_topic");
    expect(screen.queryByTestId("dialogue-lines-editor")).toBeNull();
    await user.selectOptions(modeSelect, "manual");
    expect(screen.getByTestId("dialogue-lines-editor")).toBeInTheDocument();
  });

  // 16. AI-mode submission includes dialogue_mode="ai_topic".
  // 18. Hidden manual lines do not accidentally drive AI-mode
  //     request semantics.
  it(
    "submits an AI Topic request with dialogue_mode='ai_topic' and NO stale lines",
    async () => {
      const user = userEvent.setup();
      renderRoute("dialogue_scene");
      // Author some manual lines first, THEN switch to AI mode.
      const primaryWrapper = screen.getByTestId(
        "recipe-field-primary_spokesperson_id",
      );
      const primarySelect = primaryWrapper.querySelector(
        "select",
      ) as HTMLSelectElement;
      await user.selectOptions(primarySelect, "sp-patch");
      // Fill one manual line to establish stale form state.
      const line0Speaker = screen.getByTestId("dialogue-line-speaker-0");
      await user.selectOptions(line0Speaker, "sp-patch");
      const line0Text = screen.getByTestId("dialogue-line-text-0");
      await user.type(line0Text, "Stale manual line");
      // Switch to AI Topic.
      const modeWrapper = screen.getByTestId("recipe-field-dialogue_mode");
      const modeSelect = modeWrapper.querySelector(
        "select",
      ) as HTMLSelectElement;
      await user.selectOptions(modeSelect, "ai_topic");
      // Fill AI-mode required fields.
      const secondaryWrapper = screen.getByTestId(
        "recipe-field-secondary_spokesperson_id",
      );
      const secondarySelect = secondaryWrapper.querySelector(
        "select",
      ) as HTMLSelectElement;
      await user.selectOptions(secondarySelect, "sp-rivet");
      const topicWrapper = screen.getByTestId("recipe-field-topic");
      const topicArea = topicWrapper.querySelector(
        "textarea",
      ) as HTMLTextAreaElement;
      await user.type(topicArea, "About the workshop");
      // Submit.
      const submit = screen.getByTestId("recipe-submit");
      await user.click(submit);
      expect(mockCreate).toHaveBeenCalledTimes(1);
      const call = mockCreate.mock.calls[0][0] as {
        kind: string;
        workspace: string;
        params: Record<string, unknown>;
      };
      expect(call.kind).toBe("dialogue_scene");
      expect(call.workspace).toBe("ws-1");
      expect(call.params.dialogue_mode).toBe("ai_topic");
      expect(call.params.secondary_spokesperson_id).toBe("sp-rivet");
      expect(call.params.topic).toBe("About the workshop");
      // SESSION 264 post-Terra-dogfood — default duration for
      // Episode Dialogue Scene raised from 60 s to 90 s.
      expect(call.params.target_duration_seconds).toBe("90");
      // Load-bearing: stale manual lines MUST NOT be in the payload.
      expect(call.params.lines).toBeUndefined();
    },
  );

  // 17. Manual-mode submission includes dialogue_mode="manual"
  //     (default) and manual lines, no AI-only stale values.
  it(
    "submits a manual request with dialogue_mode='manual' and NO AI-only values",
    async () => {
      const user = userEvent.setup();
      renderRoute("dialogue_scene");
      // Establish AI-only stale values by switching to AI, filling
      // fields, then switching back to Manual.
      const modeWrapper = screen.getByTestId("recipe-field-dialogue_mode");
      const modeSelect = modeWrapper.querySelector(
        "select",
      ) as HTMLSelectElement;
      await user.selectOptions(modeSelect, "ai_topic");
      const topicWrapper = screen.getByTestId("recipe-field-topic");
      const topicArea = topicWrapper.querySelector(
        "textarea",
      ) as HTMLTextAreaElement;
      await user.type(topicArea, "Some topic");
      // Switch back to manual.
      await user.selectOptions(modeSelect, "manual");
      // Fill manual fields.
      const primaryWrapper = screen.getByTestId(
        "recipe-field-primary_spokesperson_id",
      );
      const primarySelect = primaryWrapper.querySelector(
        "select",
      ) as HTMLSelectElement;
      await user.selectOptions(primarySelect, "sp-patch");
      const line0Speaker = screen.getByTestId("dialogue-line-speaker-0");
      await user.selectOptions(line0Speaker, "sp-patch");
      const line0Text = screen.getByTestId("dialogue-line-text-0");
      await user.type(line0Text, "Hi");
      // Submit.
      const submit = screen.getByTestId("recipe-submit");
      await user.click(submit);
      expect(mockCreate).toHaveBeenCalledTimes(1);
      const call = mockCreate.mock.calls[0][0] as {
        params: Record<string, unknown>;
      };
      expect(call.params.dialogue_mode).toBe("manual");
      // Stale AI-only values must NOT be in the payload.
      expect(call.params.topic).toBeUndefined();
      expect(call.params.secondary_spokesperson_id).toBeUndefined();
      expect(call.params.target_duration_seconds).toBeUndefined();
      expect(call.params.use_knowledge).toBeUndefined();
      expect(call.params.verifier_mode).toBeUndefined();
      expect(call.params.opener).toBeUndefined();
      // Manual lines DO appear.
      expect(call.params.lines).toEqual([
        { spokesperson_id: "sp-patch", text: "Hi" },
      ]);
    },
  );

  // Additional AI-D4 UX: secondary picker filters out primary.
  it(
    "hides the primary spokesperson from the secondary picker's options",
    async () => {
      const user = userEvent.setup();
      renderRoute("dialogue_scene");
      const primaryWrapper = screen.getByTestId(
        "recipe-field-primary_spokesperson_id",
      );
      const primarySelect = primaryWrapper.querySelector(
        "select",
      ) as HTMLSelectElement;
      await user.selectOptions(primarySelect, "sp-patch");
      // Switch to AI Topic so the secondary field renders.
      const modeWrapper = screen.getByTestId("recipe-field-dialogue_mode");
      const modeSelect = modeWrapper.querySelector(
        "select",
      ) as HTMLSelectElement;
      await user.selectOptions(modeSelect, "ai_topic");
      const secondaryWrapper = screen.getByTestId(
        "recipe-field-secondary_spokesperson_id",
      );
      const secondarySelect = secondaryWrapper.querySelector(
        "select",
      ) as HTMLSelectElement;
      const optionValues = Array.from(secondarySelect.options).map(
        (o) => o.value,
      );
      expect(optionValues).not.toContain("sp-patch");
      expect(optionValues).toContain("sp-rivet");
    },
  );

  // 19. Existing non-dialogue recipe forms are unaffected.
  it(
    "does not apply dialogue-mode visibility filtering to talking_head",
    () => {
      renderRoute("talking_head");
      // talking_head has no dialogue_mode field.
      expect(screen.queryByTestId("recipe-field-dialogue_mode")).toBeNull();
      // But it still has its own opener + use_knowledge fields —
      // those must render, NOT be hidden by dialogue's manual-mode
      // filter.
      expect(screen.getByTestId("recipe-field-opener")).toBeInTheDocument();
      expect(
        screen.getByTestId("recipe-field-use_knowledge"),
      ).toBeInTheDocument();
    },
  );
});
