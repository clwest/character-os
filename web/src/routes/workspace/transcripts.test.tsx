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
    useApproveHighlight: vi.fn(),
    useRejectHighlight: vi.fn(),
  };
});

import { useMe } from "@/lib/api/workspaces";
import {
  useTranscripts,
  useTranscript,
  useHighlightsForTranscript,
  useMineTranscript,
  useApproveHighlight,
  useRejectHighlight,
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
    // Default stubs for B1.6 approval hooks — overridden in specific tests.
    vi.mocked(useApproveHighlight).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useApproveHighlight>);
    vi.mocked(useRejectHighlight).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useRejectHighlight>);
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

  it("renders approve/reject buttons for pending highlight (B1.6)", () => {
    const mutateAsync = vi.fn().mockResolvedValue(makeHighlight({ status: "approved" }));
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
    vi.mocked(useApproveHighlight).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useApproveHighlight>);
    vi.mocked(useRejectHighlight).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useRejectHighlight>);

    renderDetail();

    expect(
      screen.getByTestId("approve-btn-h-00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("reject-btn-h-00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
  });
});

// ---- B1.6 approval UX tests ----------------------------------

describe("WorkspaceTranscriptDetailRoute — B1.6 approval UX", () => {
  const TRANSCRIPT_ID = "t-00000000-0000-0000-0000-000000000001";
  const HIGHLIGHT_ID = "h-00000000-0000-0000-0000-000000000001";

  function setupDetailMocks({
    highlights = [makeHighlight()],
    approveAsync = vi.fn().mockResolvedValue(makeHighlight({ status: "approved" })),
    rejectAsync = vi.fn().mockResolvedValue(makeHighlight({ status: "rejected" })),
    approvePending = false,
    rejectPending = false,
  }: {
    highlights?: ReturnType<typeof makeHighlight>[];
    approveAsync?: ReturnType<typeof vi.fn>;
    rejectAsync?: ReturnType<typeof vi.fn>;
    approvePending?: boolean;
    rejectPending?: boolean;
  } = {}) {
    vi.mocked(useMe).mockReturnValue({
      data: { default_workspace: { id: WORKSPACE_ID } },
    } as unknown as ReturnType<typeof useMe>);
    vi.mocked(useTranscript).mockReturnValue({
      data: makeDetailAsset(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useTranscript>);
    vi.mocked(useHighlightsForTranscript).mockReturnValue({
      data: highlights,
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useHighlightsForTranscript>);
    vi.mocked(useMineTranscript).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
      isSuccess: false,
      data: undefined,
    } as unknown as ReturnType<typeof useMineTranscript>);
    vi.mocked(useApproveHighlight).mockReturnValue({
      mutateAsync: approveAsync,
      isPending: approvePending,
    } as unknown as ReturnType<typeof useApproveHighlight>);
    vi.mocked(useRejectHighlight).mockReturnValue({
      mutateAsync: rejectAsync,
      isPending: rejectPending,
    } as unknown as ReturnType<typeof useRejectHighlight>);
  }

  function renderDetail(id = TRANSCRIPT_ID) {
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

  // ---- Approve button state ------------------------------------

  it("Approve button is enabled only when highlight is pending", () => {
    setupDetailMocks({ highlights: [makeHighlight({ status: "pending" })] });
    renderDetail();
    const btn = screen.getByTestId(`approve-btn-${HIGHLIGHT_ID}`);
    expect(btn).not.toBeDisabled();
  });

  it("does not render Approve button for non-pending highlight", () => {
    setupDetailMocks({ highlights: [makeHighlight({ status: "approved" })] });
    renderDetail();
    expect(screen.queryByTestId(`approve-btn-${HIGHLIGHT_ID}`)).not.toBeInTheDocument();
  });

  it("Approve button disabled while mutation is in-flight", () => {
    setupDetailMocks({ approvePending: true });
    renderDetail();
    expect(screen.getByTestId(`approve-btn-${HIGHLIGHT_ID}`)).toBeDisabled();
    expect(screen.getByTestId(`approve-spinner-${HIGHLIGHT_ID}`)).toBeInTheDocument();
  });

  it("Approve button calls mutateAsync with highlight id", async () => {
    const user = userEvent.setup();
    const approveAsync = vi.fn().mockResolvedValue(
      makeHighlight({ status: "approved" }),
    );
    setupDetailMocks({ approveAsync });
    renderDetail();

    await user.click(screen.getByTestId(`approve-btn-${HIGHLIGHT_ID}`));

    await waitFor(() => {
      expect(approveAsync).toHaveBeenCalledWith(HIGHLIGHT_ID);
    });
  });

  // ---- Reject button state ------------------------------------

  it("Reject button is enabled only when highlight is pending", () => {
    setupDetailMocks({ highlights: [makeHighlight({ status: "pending" })] });
    renderDetail();
    expect(screen.getByTestId(`reject-btn-${HIGHLIGHT_ID}`)).not.toBeDisabled();
  });

  it("does not render Reject button for non-pending highlight", () => {
    setupDetailMocks({ highlights: [makeHighlight({ status: "rejected" })] });
    renderDetail();
    expect(screen.queryByTestId(`reject-btn-${HIGHLIGHT_ID}`)).not.toBeInTheDocument();
  });

  // ---- Reject inline textarea flow ----------------------------

  it("clicking Reject reveals the textarea + confirm/cancel buttons", async () => {
    const user = userEvent.setup();
    setupDetailMocks();
    renderDetail();

    // Reject form not visible initially.
    expect(screen.queryByTestId(`reject-form-${HIGHLIGHT_ID}`)).not.toBeInTheDocument();

    await user.click(screen.getByTestId(`reject-btn-${HIGHLIGHT_ID}`));

    expect(screen.getByTestId(`reject-form-${HIGHLIGHT_ID}`)).toBeInTheDocument();
    expect(screen.getByTestId(`reject-reason-${HIGHLIGHT_ID}`)).toBeInTheDocument();
    expect(screen.getByTestId(`reject-confirm-btn-${HIGHLIGHT_ID}`)).toBeInTheDocument();
    expect(screen.getByTestId(`reject-cancel-btn-${HIGHLIGHT_ID}`)).toBeInTheDocument();
  });

  it("Cancel button collapses the reject form without firing", async () => {
    const user = userEvent.setup();
    const rejectAsync = vi.fn();
    setupDetailMocks({ rejectAsync });
    renderDetail();

    await user.click(screen.getByTestId(`reject-btn-${HIGHLIGHT_ID}`));
    expect(screen.getByTestId(`reject-form-${HIGHLIGHT_ID}`)).toBeInTheDocument();

    await user.click(screen.getByTestId(`reject-cancel-btn-${HIGHLIGHT_ID}`));

    expect(screen.queryByTestId(`reject-form-${HIGHLIGHT_ID}`)).not.toBeInTheDocument();
    expect(rejectAsync).not.toHaveBeenCalled();
  });

  it("Confirm Reject fires mutateAsync with id and rejection_reason", async () => {
    const user = userEvent.setup();
    const rejectAsync = vi.fn().mockResolvedValue(
      makeHighlight({ status: "rejected", rejection_reason: "Off topic" }),
    );
    setupDetailMocks({ rejectAsync });
    renderDetail();

    await user.click(screen.getByTestId(`reject-btn-${HIGHLIGHT_ID}`));
    await user.type(screen.getByTestId(`reject-reason-${HIGHLIGHT_ID}`), "Off topic");
    await user.click(screen.getByTestId(`reject-confirm-btn-${HIGHLIGHT_ID}`));

    await waitFor(() => {
      expect(rejectAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          id: HIGHLIGHT_ID,
          rejection_reason: "Off topic",
        }),
      );
    });
  });

  it("reject form collapses after successful rejection", async () => {
    const user = userEvent.setup();
    const rejectAsync = vi.fn().mockResolvedValue(
      makeHighlight({ status: "rejected" }),
    );
    setupDetailMocks({ rejectAsync });
    renderDetail();

    await user.click(screen.getByTestId(`reject-btn-${HIGHLIGHT_ID}`));
    await user.click(screen.getByTestId(`reject-confirm-btn-${HIGHLIGHT_ID}`));

    await waitFor(() => {
      expect(screen.queryByTestId(`reject-form-${HIGHLIGHT_ID}`)).not.toBeInTheDocument();
    });
  });

  // ---- Approve success → composition link ---------------------

  it("shows View composition link when produced_composition_id is set", () => {
    setupDetailMocks({
      highlights: [
        makeHighlight({
          status: "approved",
          produced_composition_id: "comp-uuid-abc",
        }),
      ],
    });
    renderDetail();

    const link = screen.getByTestId(`highlight-composition-link-${HIGHLIGHT_ID}`);
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/compositions/comp-uuid-abc");
  });

  it("does not show composition link when produced_composition_id is null", () => {
    setupDetailMocks({ highlights: [makeHighlight({ produced_composition_id: null })] });
    renderDetail();
    expect(
      screen.queryByTestId(`highlight-composition-link-${HIGHLIGHT_ID}`),
    ).not.toBeInTheDocument();
  });

  // ---- 400 error surfaced inline ------------------------------

  it("surfaces inline error when approve returns 400", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/client");
    const approveAsync = vi.fn().mockRejectedValue(
      new ApiError("400", 400, { detail: "cannot approve rejected highlight" }),
    );
    setupDetailMocks({ approveAsync });
    renderDetail();

    await user.click(screen.getByTestId(`approve-btn-${HIGHLIGHT_ID}`));

    await waitFor(() => {
      expect(screen.getByTestId(`approve-error-${HIGHLIGHT_ID}`)).toBeInTheDocument();
      expect(screen.getByTestId(`approve-error-${HIGHLIGHT_ID}`)).toHaveTextContent(
        "cannot approve rejected highlight",
      );
    });
  });

  it("surfaces inline error when reject returns 400", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/client");
    const rejectAsync = vi.fn().mockRejectedValue(
      new ApiError("400", 400, { detail: "cannot reject approved highlight" }),
    );
    setupDetailMocks({ rejectAsync });
    renderDetail();

    await user.click(screen.getByTestId(`reject-btn-${HIGHLIGHT_ID}`));
    await user.click(screen.getByTestId(`reject-confirm-btn-${HIGHLIGHT_ID}`));

    await waitFor(() => {
      expect(screen.getByTestId(`reject-error-${HIGHLIGHT_ID}`)).toBeInTheDocument();
      expect(screen.getByTestId(`reject-error-${HIGHLIGHT_ID}`)).toHaveTextContent(
        "cannot reject approved highlight",
      );
    });
  });

  // ---- LLM reasoning visible -----------------------------------

  it("renders LLM reasoning for audit (scope-lock rule 3)", () => {
    setupDetailMocks();
    renderDetail();
    expect(
      screen.getByTestId(`highlight-reasoning-${HIGHLIGHT_ID}`),
    ).toBeInTheDocument();
    expect(screen.getByText("Clear CTA with high energy.")).toBeInTheDocument();
  });

  // ---- Rejection reason display --------------------------------

  it("shows rejection reason when status is rejected and reason is set", () => {
    setupDetailMocks({
      highlights: [
        makeHighlight({
          status: "rejected",
          rejection_reason: "Too long for Reels.",
        }),
      ],
    });
    renderDetail();
    expect(
      screen.getByTestId(`highlight-rejection-reason-${HIGHLIGHT_ID}`),
    ).toBeInTheDocument();
    expect(screen.getByText(/Too long for Reels/)).toBeInTheDocument();
  });

  // ---- Char-range hover-highlight ------------------------------

  it("marks the correct char range in the transcript body on row hover", async () => {
    const user = userEvent.setup();
    setupDetailMocks({
      highlights: [
        makeHighlight({
          char_start: 25,
          char_end: 68,
        }),
      ],
    });
    renderDetail();

    // No mark before hovering.
    expect(screen.queryByTestId("transcript-highlight-mark")).not.toBeInTheDocument();

    // Hover the highlight row.
    await user.hover(screen.getByTestId(`highlight-row-${HIGHLIGHT_ID}`));

    await waitFor(() => {
      const mark = screen.getByTestId("transcript-highlight-mark");
      expect(mark).toBeInTheDocument();
      // The inline_content is:
      // "Sasha: Welcome everyone. Let's discuss the Q3 pipeline goals today."
      // char 25-68 is "Let's discuss the Q3 pipeline goals today."
      expect(mark).toHaveTextContent("Let's discuss the Q3 pipeline goals today.");
    });
  });

  it("removes the mark when mouse leaves the row", async () => {
    const user = userEvent.setup();
    setupDetailMocks({
      highlights: [makeHighlight({ char_start: 25, char_end: 68 })],
    });
    renderDetail();

    const row = screen.getByTestId(`highlight-row-${HIGHLIGHT_ID}`);
    await user.hover(row);

    await waitFor(() => {
      expect(screen.getByTestId("transcript-highlight-mark")).toBeInTheDocument();
    });

    await user.unhover(row);

    await waitFor(() => {
      expect(screen.queryByTestId("transcript-highlight-mark")).not.toBeInTheDocument();
    });
  });
});
