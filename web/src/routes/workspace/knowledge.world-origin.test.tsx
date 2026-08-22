/**
 * SESSION 277 Slice 13 (Q-277-13-C) — World-detail origin
 * destination regression at `/workspace/knowledge`.
 *
 * Covers acceptance criteria C, D, E, F, G from Slice 13 §259:
 *   C — origin=world_detail_add_knowledge renders shared-World
 *       contextual mode (World name resolved; no character
 *       resolution; ingest tabs immediately available).
 *   D — switching ingest tabs preserves the World context.
 *   E — refresh / direct-URL mount renders world-detail mode
 *       from first paint.
 *   F — invalid / missing Universe fails safely to the generic
 *       UploadPanel (never fabricates a World, never falls back
 *       to WORKSPACE).
 *   G — payload emitted is {workspace, universe, ...content} —
 *       identical shape to Slice 12's World branch. Never
 *       audience_scope="workspace". Never spokesperson_ids.
 *   Additional — no CHARACTER audience option is ever exposed in
 *   world-detail mode (SESSION 275 broadening-prevention).
 *
 * A + B (bare/generic and character-origin isolation) live in
 * `knowledge.contextual.test.tsx` — verified unchanged there.
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

vi.mock("@/lib/api/knowledge", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/knowledge")>(
    "@/lib/api/knowledge",
  );
  return {
    ...actual,
    useKnowledgeList: vi.fn(),
    useCreateKnowledge: vi.fn(),
    useDeleteKnowledge: vi.fn(),
    useKnowledgeSearch: vi.fn(),
  };
});

vi.mock("@/lib/api/universes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/universes")>(
    "@/lib/api/universes",
  );
  return {
    ...actual,
    useUniverse: vi.fn(),
    useUniverses: vi.fn(),
  };
});

vi.mock("@/lib/api/spokespeople", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/spokespeople")>(
    "@/lib/api/spokespeople",
  );
  return { ...actual, useSpokesperson: vi.fn() };
});

import { useMe } from "@/lib/api/workspaces";
import {
  useKnowledgeList,
  useCreateKnowledge,
  useDeleteKnowledge,
  useKnowledgeSearch,
} from "@/lib/api/knowledge";
import { useUniverse, useUniverses } from "@/lib/api/universes";
import { useSpokesperson } from "@/lib/api/spokespeople";
import { WorkspaceKnowledgeRoute } from "./knowledge";

const useMeMock = useMe as unknown as ReturnType<typeof vi.fn>;
const useKnowledgeListMock =
  useKnowledgeList as unknown as ReturnType<typeof vi.fn>;
const useCreateKnowledgeMock =
  useCreateKnowledge as unknown as ReturnType<typeof vi.fn>;
const useDeleteKnowledgeMock =
  useDeleteKnowledge as unknown as ReturnType<typeof vi.fn>;
const useKnowledgeSearchMock =
  useKnowledgeSearch as unknown as ReturnType<typeof vi.fn>;
const useUniverseMock = useUniverse as unknown as ReturnType<typeof vi.fn>;
const useUniversesMock = useUniverses as unknown as ReturnType<typeof vi.fn>;
const useSpokespersonMock =
  useSpokesperson as unknown as ReturnType<typeof vi.fn>;


const FF_UNI = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f";

function makeUniverse(overrides: Record<string, unknown> = {}) {
  return {
    id: FF_UNI,
    workspace: "ws_1",
    name: "Fox & Flour Bakery",
    slug: "fox-flour-bakery",
    description: "",
    brief: "A neighborhood artisan bakery.",
    created_by: null,
    created_at: "2026-07-23T00:00:00Z",
    updated_at: "2026-08-22T00:00:00Z",
    archived_at: null,
    teammate_count: 2,
    knowledge_document_count: 0,
    episode_count: 2,
    ...overrides,
  };
}

function makeMutation<T = unknown>(result: T | null = null, error: unknown = null) {
  return {
    mutateAsync: vi.fn().mockResolvedValue(result),
    isPending: false,
    isError: !!error,
    error,
    reset: vi.fn(),
  };
}

function renderRoute(url: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[url]}>
        <Routes>
          <Route
            path="/workspace/knowledge"
            element={<WorkspaceKnowledgeRoute />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}


beforeEach(() => {
  useMeMock.mockReset();
  useKnowledgeListMock.mockReset();
  useCreateKnowledgeMock.mockReset();
  useDeleteKnowledgeMock.mockReset();
  useKnowledgeSearchMock.mockReset();
  useUniverseMock.mockReset();
  useUniversesMock.mockReset();
  useSpokespersonMock.mockReset();

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
  useKnowledgeListMock.mockReturnValue({
    data: [],
    isLoading: false,
    error: null,
  });
  useDeleteKnowledgeMock.mockReturnValue(makeMutation());
  useKnowledgeSearchMock.mockReturnValue(makeMutation({ results: [] }));
  useUniversesMock.mockReturnValue({
    data: [makeUniverse()],
    isLoading: false,
    error: null,
  });
});


// ---------------------------------------------------------------
// Acceptance C — shared-World contextual mode renders correctly.
// ---------------------------------------------------------------

describe("world_detail_add_knowledge origin — destination mode (C)", () => {
  beforeEach(() => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    // Belt-and-braces: even if spokesperson mock is called, return
    // undefined — the world-detail path must NOT resolve a
    // spokesperson.
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
  });

  it("renders shared-World header with the resolved World name", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );
    expect(screen.getByTestId("contextual-upload")).toBeTruthy();
    expect(
      (screen.getByTestId("contextual-upload") as HTMLElement).dataset.origin,
    ).toBe("world_detail_add_knowledge");
    expect(screen.getByTestId("contextual-world-name").textContent).toBe(
      "Fox & Flour Bakery",
    );
    // Explicit copy affirms shared-World intent.
    expect(screen.getByText(/Add shared knowledge to/i)).toBeTruthy();
    expect(
      screen.getByText(
        /Every character in this World inherits what you add here/i,
      ),
    ).toBeTruthy();
  });

  it("does NOT resolve a character — no character name anywhere", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );
    expect(screen.queryByTestId("contextual-character-name")).toBeNull();
    // Character resolution hook was NOT called — the world-detail
    // panel skips useSpokesperson entirely.
    expect(useSpokespersonMock).not.toHaveBeenCalled();
  });

  it("does NOT render the two-choice audience selector (SESSION 275)", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );
    expect(screen.queryByTestId("contextual-audience")).toBeNull();
    expect(screen.queryByTestId("contextual-audience-world")).toBeNull();
    expect(screen.queryByTestId("contextual-audience-character")).toBeNull();
    // No "Who should know this?" copy.
    expect(screen.queryByText(/Who should know this/i)).toBeNull();
  });

  it("renders ingest tabs IMMEDIATELY — no gate on audience picking", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );
    expect(screen.getByTestId("contextual-ingest")).toBeTruthy();
    expect(screen.getByTestId("ctx-tab-paste")).toBeTruthy();
    expect(screen.getByTestId("ctx-tab-upload")).toBeTruthy();
    expect(screen.getByTestId("ctx-tab-url")).toBeTruthy();
    expect(screen.getByTestId("ctx-tab-search")).toBeTruthy();
    expect(screen.getByTestId("ctx-paste-submit")).toBeTruthy();
  });

  it("does NOT expose WORKSPACE audience anywhere (SESSION 275 + acceptance G)", () => {
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );
    // No legacy sentinel copy anywhere.
    expect(screen.queryByText(/None \(legacy/i)).toBeNull();
    expect(screen.queryByText(/workspace-wide/i)).toBeNull();
    // No generic UniverseScopePicker.
    expect(screen.queryByTestId("paste-universe-scope")).toBeNull();
  });
});


// ---------------------------------------------------------------
// Acceptance G — payload shape matches Slice 12 World branch.
// ---------------------------------------------------------------

describe("world_detail_add_knowledge origin — payload shape (G)", () => {
  it("posts {workspace, universe, title, text_content} — no spokesperson_ids, no audience_scope", async () => {
    const create = makeMutation({ id: "kd_new" });
    useCreateKnowledgeMock.mockReturnValue(create);
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });

    const user = userEvent.setup();
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );

    await user.type(
      screen.getByTestId("ctx-paste-title"),
      "Fox & Flour Sunday hours",
    );
    await user.type(
      screen.getByTestId("ctx-paste-content"),
      "Fox & Flour closes at 3pm on Sundays.",
    );
    await user.click(screen.getByTestId("ctx-paste-submit"));

    await waitFor(() =>
      expect(create.mutateAsync).toHaveBeenCalledTimes(1),
    );
    const payload = create.mutateAsync.mock.calls[0]![0] as Record<
      string,
      unknown
    >;
    expect(payload).toMatchObject({
      workspace: "ws_1",
      universe: FF_UNI,
      title: "Fox & Flour Sunday hours",
      text_content: "Fox & Flour closes at 3pm on Sundays.",
    });
    // No spokesperson_ids; no audience_scope.
    expect("spokesperson_ids" in payload).toBe(false);
    expect("audience_scope" in payload).toBe(false);
  });
});


// ---------------------------------------------------------------
// Acceptance D — switching ingest tabs preserves context.
// ---------------------------------------------------------------

describe("world_detail_add_knowledge origin — tab switching (D)", () => {
  it("preserves the World context when switching ingest tabs", async () => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());

    const user = userEvent.setup();
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );

    // World name visible on Paste tab (default).
    expect(screen.getByTestId("contextual-world-name").textContent).toBe(
      "Fox & Flour Bakery",
    );
    // Switch to URL tab.
    await user.click(screen.getByTestId("ctx-tab-url"));
    // World name STILL visible — context lives on the surrounding
    // panel, not per-tab. No per-tab UniverseScopePicker reset.
    expect(screen.getByTestId("contextual-world-name").textContent).toBe(
      "Fox & Flour Bakery",
    );
    expect(screen.queryByTestId("paste-universe-scope")).toBeNull();
    // Switch to Upload PDF.
    await user.click(screen.getByTestId("ctx-tab-upload"));
    expect(screen.getByTestId("contextual-world-name").textContent).toBe(
      "Fox & Flour Bakery",
    );
  });
});


// ---------------------------------------------------------------
// Acceptance E — refresh / direct URL mounts the same mode.
// ---------------------------------------------------------------

describe("world_detail_add_knowledge origin — deep-link (E)", () => {
  it("mounts world-detail mode from first paint on direct navigation", () => {
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );
    // First paint already shows the shared-World header + ingest tabs.
    expect(screen.getByTestId("contextual-upload")).toBeTruthy();
    expect(
      (screen.getByTestId("contextual-upload") as HTMLElement).dataset.origin,
    ).toBe("world_detail_add_knowledge");
    expect(screen.getByTestId("contextual-ingest")).toBeTruthy();
  });
});


// ---------------------------------------------------------------
// Acceptance F — invalid / stale params fail safely.
// ---------------------------------------------------------------

describe("world_detail_add_knowledge origin — fail-safe (F)", () => {
  it("falls back to generic UploadPanel when universe UUID doesn't resolve", () => {
    useUniverseMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&origin=world_detail_add_knowledge`,
    );
    // Fell back to the pre-Slice-12 generic UploadPanel — no
    // contextual mode, no fabricated World.
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
    // And the generic scope picker is there (compatibility path).
    expect(screen.getByTestId("paste-universe-scope")).toBeTruthy();
  });

  it("falls back to generic UploadPanel when universe param is entirely missing", () => {
    useUniverseMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
    // No universe param → parser returns null → generic panel.
    renderRoute("/workspace/knowledge?origin=world_detail_add_knowledge");
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
  });

  it("falls back when universe param is malformed (not-a-uuid)", () => {
    useUniverseMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
    renderRoute(
      "/workspace/knowledge?universe=garbage&origin=world_detail_add_knowledge",
    );
    expect(screen.getByTestId("knowledge-upload")).toBeTruthy();
    expect(screen.queryByTestId("contextual-upload")).toBeNull();
  });

  it("stray spokesperson param on world-detail origin does NOT flip to character mode", () => {
    // The parser's origin discriminator wins — a leaked
    // spokesperson param must not silently switch modes and expose
    // a character audience option.
    useUniverseMock.mockReturnValue({
      data: makeUniverse(),
      isLoading: false,
      error: null,
    });
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      error: null,
    });
    useCreateKnowledgeMock.mockReturnValue(makeMutation());
    renderRoute(
      `/workspace/knowledge?universe=${FF_UNI}&spokesperson=f4de81f3-ef65-4196-a50e-38cfc6d1854f&origin=world_detail_add_knowledge`,
    );
    expect(
      (screen.getByTestId("contextual-upload") as HTMLElement).dataset.origin,
    ).toBe("world_detail_add_knowledge");
    expect(screen.queryByTestId("contextual-audience-character")).toBeNull();
    expect(useSpokespersonMock).not.toHaveBeenCalled();
  });
});
