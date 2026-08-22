/**
 * SESSION 277 Slice 5 (Q-277-5) — World picker regression coverage.
 *
 * The wizard's Step 1 must require an explicit World before the
 * operator can advance. Behaviors covered:
 *
 * 1. With no World selected, the Next button is disabled even when
 *    name + brief are filled.
 * 2. Selecting an existing World enables Next; the chosen UUID is
 *    reflected in the picker.
 * 3. Choosing "+ Create new World…" opens the inline create surface.
 * 4. Submitting the inline create fires POST /api/universes/,
 *    receives the new UUID, and selects it — Next then enables.
 *
 * The submit path itself (POST /api/spokespeople/ with the
 * `universe` field) is exercised by the backend regression
 * `test_universe_required_on_create.py`; here we prove the SPA-side
 * gate + inline-create wiring.
 *
 * Auto-select is NOT tested because Slice 5 §"Scope lock" explicitly
 * forbids it — even with a single existing World the picker must
 * remain at "— Pick a World —" until the operator picks. A
 * regression test asserts that too.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/lib/api/workspaces", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/workspaces")>(
    "@/lib/api/workspaces",
  );
  return { ...actual, useMe: vi.fn() };
});

vi.mock("@/lib/api/universes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/universes")>(
    "@/lib/api/universes",
  );
  return {
    ...actual,
    useUniverses: vi.fn(),
    useCreateUniverse: vi.fn(),
  };
});

vi.mock("@/lib/api/spokespeople", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/spokespeople")>(
    "@/lib/api/spokespeople",
  );
  return {
    ...actual,
    useCreateSpokesperson: vi.fn(),
    useCloneVoice: vi.fn(),
    useSpokespersonTemplates: vi.fn(),
  };
});

vi.mock("@/lib/api/prompts", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/prompts")>(
    "@/lib/api/prompts",
  );
  return { ...actual, useSuggestTone: vi.fn() };
});

import { useMe } from "@/lib/api/workspaces";
import { useUniverses, useCreateUniverse } from "@/lib/api/universes";
import {
  useCreateSpokesperson,
  useCloneVoice,
  useSpokespersonTemplates,
} from "@/lib/api/spokespeople";
import { useSuggestTone } from "@/lib/api/prompts";
import { SpokespersonWizard } from "./spokesperson-wizard";

const useMeMock = useMe as unknown as ReturnType<typeof vi.fn>;
const useUniversesMock = useUniverses as unknown as ReturnType<typeof vi.fn>;
const useCreateUniverseMock =
  useCreateUniverse as unknown as ReturnType<typeof vi.fn>;
const useCreateSpokespersonMock =
  useCreateSpokesperson as unknown as ReturnType<typeof vi.fn>;
const useCloneVoiceMock = useCloneVoice as unknown as ReturnType<typeof vi.fn>;
const useSpokespersonTemplatesMock =
  useSpokespersonTemplates as unknown as ReturnType<typeof vi.fn>;
const useSuggestToneMock = useSuggestTone as unknown as ReturnType<typeof vi.fn>;

function makeWorld(overrides: Record<string, unknown> = {}) {
  return {
    id: "u_1",
    workspace: "ws_1",
    workspace_name: "Chris's workspace",
    name: "Fox & Flour Bakery",
    slug: "fox-flour-bakery",
    description: "",
    created_by: null,
    created_at: "2026-08-17T00:00:00Z",
    updated_at: "2026-08-17T00:00:00Z",
    archived_at: null,
    teammate_count: 0,
    knowledge_document_count: 0,
    episode_count: 0,
    ...overrides,
  };
}

function makeMutation<T>(result: T | null = null, error: unknown = null) {
  return {
    mutateAsync: vi.fn().mockResolvedValue(result),
    isPending: false,
    isError: !!error,
    error,
    reset: vi.fn(),
  };
}

function renderWizard() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/spokespeople/new"]}>
        <SpokespersonWizard />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useMeMock.mockReset();
  useUniversesMock.mockReset();
  useCreateUniverseMock.mockReset();
  useCreateSpokespersonMock.mockReset();
  useCloneVoiceMock.mockReset();
  useSpokespersonTemplatesMock.mockReset();
  useSuggestToneMock.mockReset();

  useMeMock.mockReturnValue({
    data: {
      id: 1,
      email: "chris@donkeybetz.com",
      is_staff: false,
      default_workspace: {
        id: "ws_1",
        name: "Chris's workspace",
        slug: "chriss-workspace",
        role: "owner",
      },
    },
    isLoading: false,
    error: null,
  });
  useCreateSpokespersonMock.mockReturnValue(makeMutation());
  useCloneVoiceMock.mockReturnValue(makeMutation());
  useSpokespersonTemplatesMock.mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  });
  useSuggestToneMock.mockReturnValue({ data: null, isLoading: false });
});


describe("Step 1 World picker (SESSION 277 Slice 5)", () => {
  it("keeps Next disabled when name+brief are filled but no World is picked", async () => {
    useUniversesMock.mockReturnValue({
      data: [makeWorld()],
      isLoading: false,
      error: null,
    });
    useCreateUniverseMock.mockReturnValue(makeMutation());

    const user = userEvent.setup();
    renderWizard();

    // Fill the required non-World fields.
    await user.type(screen.getByTestId("wizard-name-input"), "Ruby");
    await user.type(
      screen.getByTestId("wizard-brief-input"),
      "Small-batch bakery in Boulder.",
    );

    // World picker exists and defaults to the placeholder.
    const picker = screen.getByTestId(
      "wizard-world-select",
    ) as HTMLSelectElement;
    expect(picker.value).toBe("");

    // Next remains disabled.
    const next = screen.getByTestId("wizard-next") as HTMLButtonElement;
    expect(next.disabled).toBe(true);
  });

  it("does NOT auto-select when exactly one World exists (Slice 5 scope-lock)", async () => {
    useUniversesMock.mockReturnValue({
      data: [makeWorld()],
      isLoading: false,
      error: null,
    });
    useCreateUniverseMock.mockReturnValue(makeMutation());

    renderWizard();

    const picker = screen.getByTestId(
      "wizard-world-select",
    ) as HTMLSelectElement;
    // Placeholder still selected — no auto-pick.
    expect(picker.value).toBe("");
    // No "Selected World" hint yet.
    expect(screen.queryByTestId("wizard-world-selected")).toBeNull();
  });

  it("enables Next once an existing World is selected", async () => {
    useUniversesMock.mockReturnValue({
      data: [makeWorld()],
      isLoading: false,
      error: null,
    });
    useCreateUniverseMock.mockReturnValue(makeMutation());

    const user = userEvent.setup();
    renderWizard();

    await user.type(screen.getByTestId("wizard-name-input"), "Ruby");
    await user.type(
      screen.getByTestId("wizard-brief-input"),
      "Small-batch bakery in Boulder.",
    );

    // Pick the existing World.
    await user.selectOptions(
      screen.getByTestId("wizard-world-select"),
      "u_1",
    );

    await waitFor(() =>
      expect(
        (screen.getByTestId("wizard-next") as HTMLButtonElement).disabled,
      ).toBe(false),
    );
    expect(screen.getByTestId("wizard-world-selected")).toHaveTextContent("u_1");
  });

  it("opens the inline create surface when '+ Create new World…' is picked", async () => {
    useUniversesMock.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    useCreateUniverseMock.mockReturnValue(makeMutation());

    const user = userEvent.setup();
    renderWizard();

    await user.selectOptions(
      screen.getByTestId("wizard-world-select"),
      "__CREATE__",
    );

    expect(screen.getByTestId("wizard-world-create-panel")).toBeTruthy();
    expect(screen.getByTestId("wizard-world-new-name")).toBeTruthy();
    // Submit disabled until name is typed.
    const submit = screen.getByTestId(
      "wizard-world-create-submit",
    ) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
  });

  it("submits inline create, selects the new World, and enables Next", async () => {
    const newWorld = makeWorld({ id: "u_new", name: "Fresh World" });
    const createMutation = makeMutation(newWorld);
    useUniversesMock.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    useCreateUniverseMock.mockReturnValue(createMutation);

    const user = userEvent.setup();
    renderWizard();

    await user.type(screen.getByTestId("wizard-name-input"), "Ruby");
    await user.type(
      screen.getByTestId("wizard-brief-input"),
      "Small-batch bakery in Boulder.",
    );

    await user.selectOptions(
      screen.getByTestId("wizard-world-select"),
      "__CREATE__",
    );
    await user.type(
      screen.getByTestId("wizard-world-new-name"),
      "Fresh World",
    );
    await user.click(screen.getByTestId("wizard-world-create-submit"));

    await waitFor(() =>
      expect(createMutation.mutateAsync).toHaveBeenCalledWith({
        workspace: "ws_1",
        name: "Fresh World",
      }),
    );
    // Panel closes, back to select.
    await waitFor(() =>
      expect(screen.queryByTestId("wizard-world-create-panel")).toBeNull(),
    );
    await waitFor(() =>
      expect(screen.getByTestId("wizard-world-selected")).toHaveTextContent(
        "u_new",
      ),
    );
    expect(
      (screen.getByTestId("wizard-next") as HTMLButtonElement).disabled,
    ).toBe(false);
  });

  it("cancels inline create without changing the current selection", async () => {
    useUniversesMock.mockReturnValue({
      data: [makeWorld()],
      isLoading: false,
      error: null,
    });
    useCreateUniverseMock.mockReturnValue(makeMutation());

    const user = userEvent.setup();
    renderWizard();

    // Select an existing World first.
    await user.selectOptions(
      screen.getByTestId("wizard-world-select"),
      "u_1",
    );
    // Open create panel.
    await user.selectOptions(
      screen.getByTestId("wizard-world-select"),
      "__CREATE__",
    );
    expect(screen.getByTestId("wizard-world-create-panel")).toBeTruthy();

    // Cancel.
    await user.click(screen.getByTestId("wizard-world-create-cancel"));
    await waitFor(() =>
      expect(screen.queryByTestId("wizard-world-create-panel")).toBeNull(),
    );
    // Prior selection preserved.
    expect(screen.getByTestId("wizard-world-selected")).toHaveTextContent(
      "u_1",
    );
  });
});
