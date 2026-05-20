/**
 * BC4 tests — Script detail "Derived campaigns" panel.
 *
 * Covers useDerivedCampaigns empty state and populated state rendering.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { ScriptDetailRoute } from "./scripts.$id";

// ---- Module mocks --------------------------------------------

vi.mock("@/lib/api/scripts", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/scripts")>();
  return {
    ...actual,
    useScript: vi.fn(),
    useRegenerateScript: vi.fn(),
    useApproveScript: vi.fn(),
    useRenderScript: vi.fn(),
    useCloneScript: vi.fn(),
    useDeleteScript: vi.fn(),
    useDerivedCampaigns: vi.fn(),
  };
});

vi.mock("@/lib/api/campaigns", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/campaigns")>();
  return {
    ...actual,
  };
});

import {
  useScript,
  useRegenerateScript,
  useApproveScript,
  useRenderScript,
  useCloneScript,
  useDeleteScript,
  useDerivedCampaigns,
} from "@/lib/api/scripts";

// ---- Fixtures ------------------------------------------------

function makeScript(overrides: Record<string, unknown> = {}) {
  return {
    id: "sc-00000000-0000-0000-0000-000000000001",
    workspace_id: "ws-00000000-0000-0000-0000-000000000001",
    spokesperson_id: "sp-00000000-0000-0000-0000-000000000001",
    spokesperson_name: "Sasha",
    name: "Five Good Emperors",
    prompt: "Write about Roman history",
    opener: "",
    draft_text: "The reign of the Five Good Emperors.",
    knowledge_chunk_ids: ["c1", "c2", "c3", "c4", "c5"],
    model: "gpt-5-mini",
    tokens_input: 1000,
    tokens_output: 400,
    verification_status: "verified" as const,
    verification_status_label: "Verified",
    verifier_mode: "warn" as const,
    revision_count: 1,
    status: "ready" as const,
    status_label: "Approved",
    approved_at: "2026-05-20T10:00:00Z",
    created_at: "2026-05-20T09:00:00Z",
    updated_at: "2026-05-20T10:00:00Z",
    cited_documents: [],
    verification_warnings: [],
    revision_history: [],
    ...overrides,
  };
}

function makeDerivedCampaign(overrides: Record<string, unknown> = {}) {
  return {
    id: "c-00000000-0000-0000-0000-000000000001",
    name: "Q3 Outreach",
    status: "draft" as const,
    recipient_count: 10,
    spokesperson_name: "Sasha",
    created_at: "2026-05-20T00:00:00Z",
    launched_at: null,
    ...overrides,
  };
}

// ---- Render helper -------------------------------------------

function qc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderDetail(id = "sc-00000000-0000-0000-0000-000000000001") {
  return render(
    <QueryClientProvider client={qc()}>
      <MemoryRouter initialEntries={[`/workspace/scripts/${id}`]}>
        <Routes>
          <Route path="/workspace/scripts/:id" element={<ScriptDetailRoute />} />
          <Route path="/workspace/scripts" element={<div data-testid="scripts-list" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---- Setup ---------------------------------------------------

beforeEach(() => {
  vi.mocked(useScript).mockReturnValue({
    data: makeScript(),
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useScript>);

  vi.mocked(useRegenerateScript).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRegenerateScript>);

  vi.mocked(useApproveScript).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useApproveScript>);

  vi.mocked(useRenderScript).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRenderScript>);

  vi.mocked(useCloneScript).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
    isError: false,
  } as unknown as ReturnType<typeof useCloneScript>);

  vi.mocked(useDeleteScript).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useDeleteScript>);
});

// ---- Tests ---------------------------------------------------

describe("ScriptDetailRoute BC4 — Derived campaigns panel", () => {
  it("renders derived campaigns panel", () => {
    vi.mocked(useDerivedCampaigns).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDerivedCampaigns>);

    renderDetail();

    expect(screen.getByTestId("derived-campaigns-panel")).toBeInTheDocument();
  });

  it("empty state renders 'Not yet used...' hint when N=0 (collapsed by default)", () => {
    vi.mocked(useDerivedCampaigns).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDerivedCampaigns>);

    renderDetail();

    // Panel starts collapsed when N=0; toggle to see content
    const toggle = screen.getByTestId("derived-campaigns-toggle");
    // The count shows 0
    expect(toggle).toHaveTextContent("Derived campaigns (0)");
  });

  it("empty state shows 'Not yet used' text after expanding", async () => {
    const user = userEvent.setup();
    vi.mocked(useDerivedCampaigns).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDerivedCampaigns>);

    renderDetail();

    // Expand the collapsed panel
    await user.click(screen.getByTestId("derived-campaigns-toggle"));

    await waitFor(() => {
      expect(screen.getByTestId("derived-campaigns-empty")).toBeInTheDocument();
      expect(screen.getByTestId("derived-campaigns-empty")).toHaveTextContent(
        "Not yet used in any campaign.",
      );
    });
  });

  it("populated state renders N rows expanded by default", () => {
    vi.mocked(useDerivedCampaigns).mockReturnValue({
      data: [
        makeDerivedCampaign(),
        makeDerivedCampaign({
          id: "c-00000000-0000-0000-0000-000000000002",
          name: "Q4 Outreach",
          recipient_count: 5,
        }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDerivedCampaigns>);

    renderDetail();

    // Panel should be expanded with 2 rows
    expect(screen.getByTestId("derived-campaigns-list")).toBeInTheDocument();
    expect(
      screen.getByTestId("derived-campaign-row-c-00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("derived-campaign-row-c-00000000-0000-0000-0000-000000000002"),
    ).toBeInTheDocument();
  });

  it("populated state rows contain links to campaign detail pages", () => {
    vi.mocked(useDerivedCampaigns).mockReturnValue({
      data: [makeDerivedCampaign()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDerivedCampaigns>);

    renderDetail();

    const link = screen.getByTestId(
      "derived-campaign-link-c-00000000-0000-0000-0000-000000000001",
    );
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute(
      "href",
      "/workspace/campaigns/c-00000000-0000-0000-0000-000000000001",
    );
    expect(link).toHaveTextContent("Q3 Outreach");
  });

  it("populated state rows show recipient count", () => {
    vi.mocked(useDerivedCampaigns).mockReturnValue({
      data: [makeDerivedCampaign({ recipient_count: 42 })],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useDerivedCampaigns>);

    renderDetail();

    expect(
      screen.getByTestId("derived-campaign-row-c-00000000-0000-0000-0000-000000000001"),
    ).toHaveTextContent("42 recipients");
  });
});
