/**
 * B1.5 route tests — /workspace/transcripts (list) +
 * /workspace/transcripts/:id (detail + mining).
 *
 * SESSION 202 / B1.5.
 *
 * Strategy: mock the API hooks at the module boundary so the
 * component tree renders without real fetches.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { WorkspaceTranscriptsRoute } from "./transcripts";
import { WorkspaceTranscriptDetailRoute } from "./transcripts.$id";

// ---- Module mocks --------------------------------------------

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
}));

vi.mock("@/lib/api/transcripts", async (importActual) => {
  // Keep the real display helpers (highlightStatusLabel, etc.) but
  // replace the hooks with controllable stubs.
  const actual = await importActual<typeof import("@/lib/api/transcripts")>();
  return {
    ...actual,
    useTranscripts: vi.fn(),
    useTranscript: vi.fn(),
    useHighlightsForTranscript: vi.fn(),
    useMineTranscript: vi.fn(),
  };
});

import { useMe } from "@/lib/api/workspaces";
import {
  useTranscripts,
  useTranscript,
  useHighlightsForTranscript,
  useMineTranscript,
} from "@/lib/api/transcripts";

// ---- Fixtures ------------------------------------------------

const WORKSPACE_ID = "ws-00000000-0000-0000-0000-000000000001";

function makeAsset(overrides: Record<string, unknown> = {}) {
  return {
    id: "t-00000000-0000-0000-0000-000000000001",
    asset_type: "transcript" as const,
    role: "transcript" as const,
    file_path: "",
    title: "Session with Sasha",
    subject: "Sasha talked about Q3 pipeline goals.",
    duration_ms: null,
    width: null,
    height: null,
    mime_type: "text/plain",
    size_bytes: 580,
    cost_micros: 0,
    created_at: "2026-05-19T10:00:00Z",
    storage_health: "data_uri" as const,
    primitive_kind: "",
    producing_prompt: "",
    composition: null,
    ...overrides,
  };
}

function makeDetailAsset(overrides: Record<string, unknown> = {}) {
  return {
    ...makeAsset(),
    producing_step: null,
    downstream_compositions: [],
    inline_content:
      "Sasha: Welcome everyone. Let's discuss the Q3 pipeline goals today.",
    ...overrides,
  };
}

function makeHighlight(overrides: Record<string, unknown> = {}) {
  return {
    id: "h-00000000-0000-0000-0000-000000000001",
    workspace_id: WORKSPACE_ID,
    source_transcript_id: "t-00000000-0000-0000-0000-000000000001",
    text: "Let's discuss the Q3 pipeline goals today.",
    char_start: 25,
    char_end: 68,
    llm_reasoning: "Clear CTA with high energy.",
    status: "pending" as const,
    status_label: "Pending",
    produced_composition_id: null,
    rejection_reason: "",
    mined_at: "2026-05-19T10:05:00Z",
    decided_at: null,
    llm_model_id: "gpt-5-mini",
    llm_cost_micros: 1200,
    llm_tokens_input: 450,
    llm_tokens_output: 80,
    ...overrides,
  };
}

// ---- WorkspaceTranscriptsRoute (list) tests ------------------

describe("WorkspaceTranscriptsRoute", () => {
  beforeEach(() => {
    vi.mocked(useMe).mockReturnValue({
      data: { default_workspace: { id: WORKSPACE_ID } },
    } as unknown as ReturnType<typeof useMe>);
  });

  function renderList() {
    return render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={["/workspace/transcripts"]}>
          <Routes>
            <Route path="/workspace/transcripts" element={<WorkspaceTranscriptsRoute />} />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("renders the page title", () => {
    vi.mocked(useTranscripts).mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscripts>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);

    renderList();

    expect(screen.getByTestId("transcripts-title")).toBeInTheDocument();
    expect(screen.getByText("Transcript Miner")).toBeInTheDocument();
  });

  it("renders transcript rows when transcripts are present", () => {
    vi.mocked(useTranscripts).mockReturnValue({
      data: {
        results: [makeAsset()],
        count: 1,
        next: null,
        previous: null,
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscripts>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);

    renderList();

    expect(screen.getByTestId("transcripts-list")).toBeInTheDocument();
    expect(
      screen.getByTestId("transcript-row-t-00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
    expect(screen.getByText("Session with Sasha")).toBeInTheDocument();
  });

  it("renders empty state with link to spokespeople when no transcripts", () => {
    vi.mocked(useTranscripts).mockReturnValue({
      data: { results: [], count: 0, next: null, previous: null },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscripts>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);

    renderList();

    expect(screen.getByTestId("transcripts-empty")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /start a live session/i }),
    ).toBeInTheDocument();
  });

  it("shows loading skeleton while data fetches", () => {
    vi.mocked(useTranscripts).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useTranscripts>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);

    renderList();

    expect(screen.getByTestId("transcripts-skeleton")).toBeInTheDocument();
  });

  it("shows highlight count badge when transcript has highlights", () => {
    vi.mocked(useTranscripts).mockReturnValue({
      data: {
        results: [makeAsset()],
        count: 1,
        next: null,
        previous: null,
      },
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscripts>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [makeHighlight(), makeHighlight({ id: "h-2" })],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);

    renderList();

    expect(screen.getByText("2 highlights")).toBeInTheDocument();
  });
});

// ---- WorkspaceTranscriptDetailRoute tests --------------------

describe("WorkspaceTranscriptDetailRoute", () => {
  beforeEach(() => {
    vi.mocked(useMe).mockReturnValue({
      data: { default_workspace: { id: WORKSPACE_ID } },
    } as unknown as ReturnType<typeof useMe>);
  });

  function renderDetail(id = "t-00000000-0000-0000-0000-000000000001") {
    return render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
        <MemoryRouter initialEntries={[`/workspace/transcripts/${id}`]}>
          <Routes>
            <Route
              path="/workspace/transcripts/:id"
              element={<WorkspaceTranscriptDetailRoute />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );
  }

  it("renders transcript title and body", () => {
    vi.mocked(useTranscript).mockReturnValue({
      data: makeDetailAsset(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
      data: undefined,
    } as unknown as ReturnType<typeof useMineTranscript>);

    renderDetail();

    expect(screen.getByTestId("transcript-detail-title")).toBeInTheDocument();
    expect(screen.getByText("Session with Sasha")).toBeInTheDocument();
    expect(screen.getByTestId("transcript-body")).toBeInTheDocument();
    expect(
      screen.getByText(/discuss the Q3 pipeline goals/),
    ).toBeInTheDocument();
  });

  it("renders Mine highlights button", () => {
    vi.mocked(useTranscript).mockReturnValue({
      data: makeDetailAsset(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
      data: undefined,
    } as unknown as ReturnType<typeof useMineTranscript>);

    renderDetail();

    const btn = screen.getByTestId("mine-highlights-btn");
    expect(btn).toBeInTheDocument();
    expect(btn).not.toBeDisabled();
  });

  it("Mine button is disabled while mutation is in-flight", () => {
    vi.mocked(useTranscript).mockReturnValue({
      data: makeDetailAsset(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: true,
      isSuccess: false,
      data: undefined,
    } as unknown as ReturnType<typeof useMineTranscript>);

    renderDetail();

    expect(screen.getByTestId("mine-highlights-btn")).toBeDisabled();
    expect(screen.getByTestId("mine-spinner")).toBeInTheDocument();
  });

  it("renders highlights after successful mining", () => {
    vi.mocked(useTranscript).mockReturnValue({
      data: makeDetailAsset(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [makeHighlight()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: true,
      data: {
        highlights: [makeHighlight()],
        used_synthesis: true,
        model: "gpt-5-mini",
      },
    } as unknown as ReturnType<typeof useMineTranscript>);

    renderDetail();

    expect(screen.getByTestId("highlights-list")).toBeInTheDocument();
    expect(
      screen.getByTestId("highlight-row-h-00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("highlight-text-h-00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
  });

  it("renders empty highlights state before mining", () => {
    vi.mocked(useTranscript).mockReturnValue({
      data: makeDetailAsset(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
      data: undefined,
    } as unknown as ReturnType<typeof useMineTranscript>);

    renderDetail();

    expect(screen.getByTestId("highlights-empty")).toBeInTheDocument();
    expect(
      screen.getByText(/Click.*Mine highlights.*to find shareable moments/),
    ).toBeInTheDocument();
  });

  it("shows loading skeleton while transcript is loading", () => {
    vi.mocked(useTranscript).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
      data: undefined,
    } as unknown as ReturnType<typeof useMineTranscript>);

    renderDetail();

    expect(screen.getByTestId("transcript-detail-skeleton")).toBeInTheDocument();
  });

  it("invokes mutateAsync when Mine button is clicked", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue({
      highlights: [],
      used_synthesis: false,
      model: "",
    });

    vi.mocked(useTranscript).mockReturnValue({
      data: makeDetailAsset(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync,
      isPending: false,
      isSuccess: false,
      data: undefined,
    } as unknown as ReturnType<typeof useMineTranscript>);

    renderDetail();

    await user.click(screen.getByTestId("mine-highlights-btn"));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          transcript_asset_id: "t-00000000-0000-0000-0000-000000000001",
        }),
      );
    });
  });

  it("renders no approve/reject buttons (B1.6 scope)", () => {
    vi.mocked(useTranscript).mockReturnValue({
      data: makeDetailAsset(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: [makeHighlight()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
      data: undefined,
    } as unknown as ReturnType<typeof useMineTranscript>);

    renderDetail();

    // B1.6 scope guard: no approve or reject buttons should exist.
    expect(screen.queryByText(/^approve$/i)).not.toBeInTheDocument();
    expect(screen.queryByText(/^reject$/i)).not.toBeInTheDocument();
  });
});
