/**
 * SESSION 277 Slice 10 (Q-277-10) — World detail view/edit correction.
 *
 * The `/workspace/universes/:id` page now defaults to a readable
 * Overview instead of an always-open form. An explicit "Edit" button
 * reveals the form. Save/Cancel return to Overview. Destructive
 * lifecycle actions live in a distinct "Lifecycle" region below
 * the primary content. `Universe.description`'s operator-visible
 * label became "Operator notes (optional)" — the DB column name is
 * NOT changed.
 *
 * Tests cover:
 * - default renders Overview (brief as prose, no textareas visible).
 * - blank-brief Overview shows the empty-state hint.
 * - Edit button reveals the form (three fields; "Operator notes
 *   (optional)" label present).
 * - Save fires the mutation with {name, brief, description} and
 *   returns to Overview.
 * - Cancel returns to Overview and discards staged edits without
 *   calling the mutation.
 * - Danger region renders separately from the edit form.
 * - Empty operator-notes value doesn't render a stray Overview
 *   Operator-notes section.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

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
    useUniverse: vi.fn(),
    useUpdateUniverse: vi.fn(),
    useArchiveUniverse: vi.fn(),
    useUnarchiveUniverse: vi.fn(),
    useHardDeleteUniverse: vi.fn(),
  };
});

vi.mock("@/lib/api/spokespeople", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/spokespeople")>(
    "@/lib/api/spokespeople",
  );
  return { ...actual, useSpokespeople: vi.fn() };
});

vi.mock("@/lib/api/knowledge", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/knowledge")>(
    "@/lib/api/knowledge",
  );
  return { ...actual, useKnowledgeList: vi.fn() };
});

// The narrative-memory panel calls its own hook chain; stub the whole
// component so we don't have to wire /api/narrative-memories mocks.
vi.mock("@/components/narrative-memory-panels", () => ({
  NarrativeMemoryList: () => <div data-testid="narrative-memory-list-stub" />,
}));

import { useMe } from "@/lib/api/workspaces";
import {
  useUniverse,
  useUpdateUniverse,
  useArchiveUniverse,
  useUnarchiveUniverse,
  useHardDeleteUniverse,
} from "@/lib/api/universes";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useKnowledgeList } from "@/lib/api/knowledge";
import { UniverseDetailRoute } from "./universes.$id";

const useMeMock = useMe as unknown as ReturnType<typeof vi.fn>;
const useUniverseMock = useUniverse as unknown as ReturnType<typeof vi.fn>;
const useUpdateMock = useUpdateUniverse as unknown as ReturnType<typeof vi.fn>;
const useArchiveMock = useArchiveUniverse as unknown as ReturnType<typeof vi.fn>;
const useUnarchiveMock =
  useUnarchiveUniverse as unknown as ReturnType<typeof vi.fn>;
const useHardDeleteMock =
  useHardDeleteUniverse as unknown as ReturnType<typeof vi.fn>;
const useSpokespeopleMock =
  useSpokespeople as unknown as ReturnType<typeof vi.fn>;
const useKnowledgeListMock =
  useKnowledgeList as unknown as ReturnType<typeof vi.fn>;


function makeUniverse(overrides: Record<string, unknown> = {}) {
  return {
    id: "u_1",
    workspace: "ws_1",
    workspace_name: "Chris's workspace",
    name: "Fox & Flour Bakery",
    slug: "fox-flour-bakery",
    description: "",
    brief:
      "Fox & Flour Bakery is a warm neighborhood artisan bakery built around small-batch baking, naturally leavened sourdough, handcrafted pastries, seasonal desserts, and celebration cakes.",
    created_by: null,
    created_at: "2026-07-23T00:00:00Z",
    updated_at: "2026-08-22T00:00:00Z",
    archived_at: null,
    teammate_count: 0,
    knowledge_document_count: 0,
    episode_count: 0,
    ...overrides,
  };
}

function makeMutation<T = unknown>(
  result: T | null = null,
  error: unknown = null,
) {
  return {
    mutateAsync: vi.fn().mockResolvedValue(result),
    isPending: false,
    isError: !!error,
    error,
    reset: vi.fn(),
  };
}

function renderRoute(id = "u_1") {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[`/workspace/universes/${id}`]}>
        <Routes>
          <Route
            path="/workspace/universes/:id"
            element={<UniverseDetailRoute />}
          />
          <Route
            path="/workspace/universes"
            element={<div data-testid="worlds-list-page">worlds</div>}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useMeMock.mockReset();
  useUniverseMock.mockReset();
  useUpdateMock.mockReset();
  useArchiveMock.mockReset();
  useUnarchiveMock.mockReset();
  useHardDeleteMock.mockReset();
  useSpokespeopleMock.mockReset();
  useKnowledgeListMock.mockReset();

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
  useUniverseMock.mockReturnValue({
    data: makeUniverse(),
    isLoading: false,
    error: null,
  });
  useUpdateMock.mockReturnValue(makeMutation({ id: "u_1" }));
  useArchiveMock.mockReturnValue(makeMutation());
  useUnarchiveMock.mockReturnValue(makeMutation());
  useHardDeleteMock.mockReturnValue(makeMutation());
  useSpokespeopleMock.mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  });
  useKnowledgeListMock.mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  });
});


describe("World detail — SESSION 277 Slice 10 view/edit correction", () => {
  it("defaults to Overview with the brief rendered as prose (no inputs visible)", () => {
    renderRoute();
    // Overview visible.
    expect(screen.getByTestId("universe-overview")).toBeTruthy();
    // Brief prose present with the real specimen text.
    const briefView = screen.getByTestId("universe-brief-view");
    expect(briefView.textContent).toContain("warm neighborhood artisan bakery");
    // Edit affordance visible in Overview mode.
    expect(screen.getByTestId("universe-edit-toggle")).toBeTruthy();
    // No edit form is rendered.
    expect(screen.queryByTestId("universe-edit")).toBeNull();
    // No editable name input in Overview mode.
    expect(screen.queryByTestId("universe-name")).toBeNull();
    // Save button is not rendered outside Edit mode.
    expect(screen.queryByTestId("universe-save")).toBeNull();
  });

  it("blank brief renders an empty-state hint prompting Edit", () => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse({ brief: "" }),
      isLoading: false,
      error: null,
    });
    renderRoute();
    expect(screen.queryByTestId("universe-brief-view")).toBeNull();
    const empty = screen.getByTestId("universe-brief-empty");
    expect(empty.textContent).toMatch(/No World brief yet/);
    // Empty operator-notes ALSO doesn't render a stray Overview
    // section (only shows when notes are populated).
    expect(screen.queryByTestId("universe-notes-view")).toBeNull();
  });

  it("clicking Edit reveals the three-field form and hides the Edit button", async () => {
    const user = userEvent.setup();
    renderRoute();
    await user.click(screen.getByTestId("universe-edit-toggle"));
    expect(screen.getByTestId("universe-edit")).toBeTruthy();
    // Overview hidden.
    expect(screen.queryByTestId("universe-overview")).toBeNull();
    // Three fields visible.
    expect(screen.getByTestId("universe-name")).toBeTruthy();
    expect(screen.getByTestId("universe-brief")).toBeTruthy();
    expect(screen.getByTestId("universe-description")).toBeTruthy();
    // "Operator notes (optional)" label present per accepted product
    // decision.
    expect(screen.getByText(/Operator notes \(optional\)/)).toBeTruthy();
    // Helper copy explaining brief vs notes distinction.
    expect(
      screen.getByText(
        /every character in this World inherits and uses during synthesis/i,
      ),
    ).toBeTruthy();
    expect(
      screen.getByText(
        /characters do not use this and it is not consumed by synthesis/i,
      ),
    ).toBeTruthy();
    // Edit affordance is hidden while in Edit mode.
    expect(screen.queryByTestId("universe-edit-toggle")).toBeNull();
  });

  it("Save fires update with {name, brief, description} and returns to Overview", async () => {
    const update = makeMutation({ id: "u_1" });
    useUpdateMock.mockReturnValue(update);
    const user = userEvent.setup();
    renderRoute();
    await user.click(screen.getByTestId("universe-edit-toggle"));

    // Edit the brief; Save button becomes enabled.
    const brief = screen.getByTestId("universe-brief") as HTMLTextAreaElement;
    await user.clear(brief);
    await user.type(brief, "Updated brief.");

    // Edit the notes with "Operator notes (optional)" label.
    const notes = screen.getByTestId(
      "universe-description",
    ) as HTMLTextAreaElement;
    await user.type(notes, "Private reminder.");

    await user.click(screen.getByTestId("universe-save"));

    await waitFor(() => expect(update.mutateAsync).toHaveBeenCalledTimes(1));
    const arg = update.mutateAsync.mock.calls[0]![0] as {
      id: string;
      payload: { name: string; brief: string; description: string };
    };
    expect(arg.id).toBe("u_1");
    expect(arg.payload.name).toBe("Fox & Flour Bakery");
    expect(arg.payload.brief).toBe("Updated brief.");
    expect(arg.payload.description).toBe("Private reminder.");

    // Returns to Overview after successful save.
    await waitFor(() =>
      expect(screen.getByTestId("universe-overview")).toBeTruthy(),
    );
    expect(screen.queryByTestId("universe-edit")).toBeNull();
  });

  it("Cancel returns to Overview and does NOT call the mutation", async () => {
    const update = makeMutation({ id: "u_1" });
    useUpdateMock.mockReturnValue(update);
    const user = userEvent.setup();
    renderRoute();

    await user.click(screen.getByTestId("universe-edit-toggle"));
    const brief = screen.getByTestId("universe-brief") as HTMLTextAreaElement;
    await user.clear(brief);
    await user.type(brief, "Draft that gets discarded.");
    await user.click(screen.getByTestId("universe-cancel"));

    expect(update.mutateAsync).not.toHaveBeenCalled();
    await waitFor(() =>
      expect(screen.getByTestId("universe-overview")).toBeTruthy(),
    );
    expect(screen.queryByTestId("universe-edit")).toBeNull();
    // Overview still shows the original brief (from server truth).
    expect(
      screen.getByTestId("universe-brief-view").textContent,
    ).toContain("warm neighborhood artisan bakery");
  });

  it("renders Danger region separately with Archive + Delete permanently, and never inside the Edit form", async () => {
    const user = userEvent.setup();
    renderRoute();

    // Danger region visible even in Overview mode.
    const danger = screen.getByTestId("universe-danger");
    expect(danger).toBeTruthy();
    expect(danger.textContent).toMatch(/Lifecycle/);
    expect(screen.getByTestId("universe-archive")).toBeTruthy();
    expect(screen.getByTestId("universe-hard-delete")).toBeTruthy();

    // Switching to Edit does NOT put Save/Archive/Delete permanently
    // in the same button row. The Danger region stays out of the
    // Edit form.
    await user.click(screen.getByTestId("universe-edit-toggle"));
    const edit = screen.getByTestId("universe-edit");
    expect(edit.contains(screen.getByTestId("universe-archive"))).toBe(false);
    expect(edit.contains(screen.getByTestId("universe-hard-delete"))).toBe(false);
  });

  it("shows the Overview 'Operator notes' section only when description is non-empty", () => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse({ description: "Private reminder to self." }),
      isLoading: false,
      error: null,
    });
    renderRoute();
    const notesView = screen.getByTestId("universe-notes-view");
    expect(notesView.textContent).toBe("Private reminder to self.");
  });
});
