/**
 * BC4 tests — Campaign detail source_script header block.
 *
 * Tests the SourceScriptPanel that renders when campaign.source_script
 * is non-null, per BC4 spec.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CampaignDetailRoute } from "./campaigns.$id";

// ---- Module mocks --------------------------------------------

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
}));

vi.mock("@/lib/api/campaigns", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/campaigns")>();
  return {
    ...actual,
    useCampaign: vi.fn(),
    useParseCsv: vi.fn(),
    useDeleteCampaign: vi.fn(),
    useCampaignForecast: vi.fn(),
    useLaunchCampaign: vi.fn(),
    useRetryRecipient: vi.fn(),
    useRecipients: vi.fn(),
  };
});

import {
  useCampaign,
  useParseCsv,
  useDeleteCampaign,
  useCampaignForecast,
  useLaunchCampaign,
  useRetryRecipient,
  useRecipients,
} from "@/lib/api/campaigns";

// ---- Fixtures ------------------------------------------------

const WORKSPACE_ID = "ws-00000000-0000-0000-0000-000000000001";

function makeCampaign(overrides: Record<string, unknown> = {}) {
  return {
    id: "c-00000000-0000-0000-0000-000000000001",
    workspace_id: WORKSPACE_ID,
    spokesperson_id: "sp-00000000-0000-0000-0000-000000000001",
    spokesperson_name: "Sasha",
    name: "Q3 Outreach",
    template: "Hi {first_name}, saw {company}.",
    placeholders: ["company", "first_name"],
    status: "draft" as const,
    status_label: "Draft",
    recipient_counts: {
      pending: 0, queued: 0, running: 0, completed: 0, failed: 0, total: 0,
    },
    launched_at: null,
    completed_at: null,
    created_at: "2026-05-19T10:00:00Z",
    updated_at: "2026-05-19T10:00:00Z",
    source_script: null,
    ...overrides,
  };
}

function makeSourceScript(overrides: Record<string, unknown> = {}) {
  return {
    id: "sc-00000000-0000-0000-0000-000000000001",
    name: "Five Good Emperors",
    status: "ready" as const,
    verification_status: "verified",
    chunk_count: 5,
    ...overrides,
  };
}

// ---- Render helper -------------------------------------------

function qc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderDetail(id = "c-00000000-0000-0000-0000-000000000001") {
  return render(
    <QueryClientProvider client={qc()}>
      <MemoryRouter initialEntries={[`/workspace/campaigns/${id}`]}>
        <Routes>
          <Route path="/workspace/campaigns/:id" element={<CampaignDetailRoute />} />
          <Route path="/workspace/campaigns" element={<div data-testid="list-page" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---- Setup ---------------------------------------------------

beforeEach(() => {
  vi.mocked(useDeleteCampaign).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useDeleteCampaign>);
  vi.mocked(useParseCsv).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useParseCsv>);
  vi.mocked(useCampaignForecast).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useCampaignForecast>);
  vi.mocked(useLaunchCampaign).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useLaunchCampaign>);
  vi.mocked(useRecipients).mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useRecipients>);
  vi.mocked(useRetryRecipient).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRetryRecipient>);
});

// ---- Tests ---------------------------------------------------

describe("CampaignDetailRoute BC4 — source_script header block", () => {
  it("renders source_script panel when campaign.source_script is present", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ source_script: makeSourceScript() }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("source-script-panel")).toBeInTheDocument();
    expect(screen.getByTestId("source-script-link")).toBeInTheDocument();
    expect(screen.getByTestId("source-script-link")).toHaveTextContent(
      "Five Good Emperors",
    );
    expect(screen.getByTestId("source-script-link")).toHaveAttribute(
      "href",
      "/workspace/scripts/sc-00000000-0000-0000-0000-000000000001",
    );
  });

  it("source_script panel shows chunk count", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ source_script: makeSourceScript({ chunk_count: 7 }) }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("source-script-chunk-count")).toHaveTextContent(
      "7 chunks",
    );
  });

  it("source_script panel absent when campaign.source_script === null", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ source_script: null }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.queryByTestId("source-script-panel")).not.toBeInTheDocument();
  });

  it("source_script panel absent when source_script is undefined (pre-BC3 campaign)", () => {
    // Campaigns created before BC3 won't have source_script in the payload.
    const campaign = makeCampaign();
    delete (campaign as Record<string, unknown>)["source_script"];
    vi.mocked(useCampaign).mockReturnValue({
      data: campaign,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.queryByTestId("source-script-panel")).not.toBeInTheDocument();
  });
});
