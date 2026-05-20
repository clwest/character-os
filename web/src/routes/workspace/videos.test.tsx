/**
 * SESSION 209 — /workspace/videos route tests.
 *
 * Strategy mirrors transcripts.test.tsx: mock the API hooks at the
 * module boundary so the component tree renders without real fetches.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { WorkspaceVideosRoute } from "./videos";

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
}));

vi.mock("@/lib/api/spokespeople", () => ({
  useSpokespeople: vi.fn(),
}));

vi.mock("@/lib/api/compositions", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/compositions")>();
  return {
    ...actual,
    useCompositions: vi.fn(),
  };
});

import { useMe } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useCompositions } from "@/lib/api/compositions";

const WORKSPACE_ID = "ws-00000000-0000-0000-0000-000000000001";

function makeRow(overrides: Record<string, unknown> = {}) {
  return {
    id: "c-00000000-0000-0000-0000-000000000001",
    name: "Spring launch render",
    template_kind: "talking_head_polished",
    status: "completed" as const,
    mock_mode: false,
    cost_actual_micros: 80_000,
    verification_status: "verified" as const,
    spokesperson_id: "sp-1",
    spokesperson_name: "Sasha",
    final_asset_id: "a-1",
    created_at: "2026-05-20T10:00:00Z",
    updated_at: "2026-05-20T10:05:00Z",
    ...overrides,
  };
}

function makePage(
  results: Array<Record<string, unknown>>,
  {
    count,
    next = null,
    previous = null,
  }: { count?: number; next?: string | null; previous?: string | null } = {},
) {
  return {
    count: count ?? results.length,
    next,
    previous,
    results,
  };
}

function setUseCompositions(value: unknown) {
  vi.mocked(useCompositions).mockReturnValue(
    value as ReturnType<typeof useCompositions>,
  );
}

function renderRoute(initialUrl = "/workspace/videos") {
  return render(
    <QueryClientProvider
      client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}
    >
      <MemoryRouter initialEntries={[initialUrl]}>
        <Routes>
          <Route path="/workspace/videos" element={<WorkspaceVideosRoute />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("WorkspaceVideosRoute", () => {
  beforeEach(() => {
    vi.mocked(useMe).mockReturnValue({
      data: { default_workspace: { id: WORKSPACE_ID } },
    } as unknown as ReturnType<typeof useMe>);
    vi.mocked(useSpokespeople).mockReturnValue({
      data: [{ id: "sp-1", name: "Sasha" }, { id: "sp-2", name: "Marcus" }],
    } as unknown as ReturnType<typeof useSpokespeople>);
  });

  it("renders a loading skeleton while compositions are loading", () => {
    setUseCompositions({ isLoading: true, data: undefined, error: null, isFetching: true });
    renderRoute();
    expect(screen.getByTestId("videos-title")).toHaveTextContent("Videos");
  });

  it("renders the empty state when there are no videos", () => {
    setUseCompositions({
      isLoading: false,
      isFetching: false,
      error: null,
      data: makePage([]),
    });
    renderRoute();
    expect(screen.getByTestId("videos-empty")).toBeInTheDocument();
    expect(screen.getByTestId("results-count")).toHaveTextContent("0");
  });

  it("renders one row per result with template + spokesperson + status", () => {
    setUseCompositions({
      isLoading: false,
      isFetching: false,
      error: null,
      data: makePage([
        makeRow({ id: "c-1", name: "First", spokesperson_name: "Sasha" }),
        makeRow({
          id: "c-2",
          name: "Second",
          spokesperson_name: "Marcus",
          status: "failed",
        }),
      ]),
    });
    renderRoute();
    const rows = screen.getAllByTestId("video-row");
    expect(rows).toHaveLength(2);
    expect(rows[0]!.textContent).toContain("First");
    expect(rows[0]!.textContent).toContain("Sasha");
    expect(rows[1]!.textContent).toContain("Second");
    expect(rows[1]!.textContent).toContain("Marcus");
  });

  it("shows next/prev buttons reflecting pagination state", () => {
    setUseCompositions({
      isLoading: false,
      isFetching: false,
      error: null,
      data: makePage([makeRow()], {
        count: 60,
        next: "/api/compositions/?page=2",
        previous: null,
      }),
    });
    renderRoute();
    expect(screen.getByTestId("pagination-prev")).toBeDisabled();
    expect(screen.getByTestId("pagination-next")).not.toBeDisabled();
  });

  it("advances to page 2 when Next is clicked", async () => {
    setUseCompositions({
      isLoading: false,
      isFetching: false,
      error: null,
      data: makePage([makeRow()], {
        count: 60,
        next: "/api/compositions/?page=2",
        previous: null,
      }),
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("pagination-next"));
    await waitFor(() => {
      const args = vi.mocked(useCompositions).mock.calls.at(-1)?.[0];
      expect(args?.page).toBe(2);
    });
  });

  it("propagates spokesperson filter into the hook params", async () => {
    setUseCompositions({
      isLoading: false,
      isFetching: false,
      error: null,
      data: makePage([makeRow()]),
    });
    renderRoute();
    await userEvent.selectOptions(screen.getByTestId("filter-spokesperson"), "sp-2");
    await waitFor(() => {
      const args = vi.mocked(useCompositions).mock.calls.at(-1)?.[0];
      expect(args?.spokesperson).toBe("sp-2");
    });
  });

  it("propagates status filter into the hook params", async () => {
    setUseCompositions({
      isLoading: false,
      isFetching: false,
      error: null,
      data: makePage([makeRow()]),
    });
    renderRoute();
    await userEvent.selectOptions(screen.getByTestId("filter-status"), "failed");
    await waitFor(() => {
      const args = vi.mocked(useCompositions).mock.calls.at(-1)?.[0];
      expect(args?.status).toBe("failed");
    });
  });

  it("renders an error panel when the query fails", () => {
    setUseCompositions({
      isLoading: false,
      isFetching: false,
      error: new Error("boom"),
      data: undefined,
    });
    renderRoute();
    expect(screen.getByTestId("videos-error")).toHaveTextContent("boom");
  });
});
