/**
 * B3.7 route tests — /workspace/campaigns (list),
 * /workspace/campaigns/new (create), /workspace/campaigns/:id (detail + CSV).
 *
 * SESSION B3.7.
 *
 * Strategy: mock API hooks at the module boundary so the component
 * tree renders without real fetches.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { WorkspaceCampaignsRoute } from "./campaigns";
import { CampaignNewRoute } from "./campaigns.new";
import { CampaignDetailRoute } from "./campaigns.$id";

// ---- Module mocks --------------------------------------------

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
}));

vi.mock("@/lib/api/spokespeople", () => ({
  useSpokespeople: vi.fn(),
}));

vi.mock("@/lib/api/campaigns", async (importActual) => {
  // Keep real display helpers + parsePlaceholders but replace hooks.
  const actual = await importActual<typeof import("@/lib/api/campaigns")>();
  return {
    ...actual,
    useCampaigns: vi.fn(),
    useCampaign: vi.fn(),
    useCreateCampaign: vi.fn(),
    useDeleteCampaign: vi.fn(),
    useParseCsv: vi.fn(),
    useRecipients: vi.fn(),
    useCampaignForecast: vi.fn(),
    useLaunchCampaign: vi.fn(),
    useRetryRecipient: vi.fn(),
  };
});

import { useMe } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import {
  useCampaigns,
  useCampaign,
  useCreateCampaign,
  useDeleteCampaign,
  useParseCsv,
  useRecipients,
  useCampaignForecast,
  useLaunchCampaign,
  useRetryRecipient,
} from "@/lib/api/campaigns";

// ---- Shared default stubs for B3.8 hooks --------------------
// These are set in beforeEach blocks inside the B3.8 describe;
// listed here for documentation.

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
      pending: 0,
      queued: 0,
      running: 0,
      completed: 0,
      failed: 0,
      total: 0,
    },
    launched_at: null,
    completed_at: null,
    created_at: "2026-05-19T10:00:00Z",
    updated_at: "2026-05-19T10:00:00Z",
    ...overrides,
  };
}

function makeSpokesperson(overrides: Record<string, unknown> = {}) {
  return {
    id: "sp-00000000-0000-0000-0000-000000000001",
    workspace: WORKSPACE_ID,
    name: "Sasha",
    business_brief: "SaaS sales platform",
    personality: "",
    visual_subject: "founder",
    visual_template: "founder" as const,
    tone_archetype: "authority" as const,
    status: "ready" as const,
    runway_avatar_id: "av-1",
    runway_avatar_status: "ready",
    portrait_path: "",
    voice_id: "v-1",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...overrides,
  };
}

function makeRecipient(overrides: Record<string, unknown> = {}) {
  return {
    id: "r-00000000-0000-0000-0000-000000000001",
    campaign_id: "c-00000000-0000-0000-0000-000000000001",
    variables: { first_name: "Alice", company: "Acme" },
    label: "Alice",
    rendered_script: "",
    position: 1,
    status: "pending" as const,
    status_label: "Pending",
    produced_composition_id: null,
    error_message: "",
    created_at: "2026-05-19T10:00:00Z",
    updated_at: "2026-05-19T10:00:00Z",
    ...overrides,
  };
}

// ---- Render helpers ------------------------------------------

function qc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderList(search = "") {
  return render(
    <QueryClientProvider client={qc()}>
      <MemoryRouter initialEntries={[`/workspace/campaigns${search}`]}>
        <Routes>
          <Route
            path="/workspace/campaigns"
            element={<WorkspaceCampaignsRoute />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderNew() {
  return render(
    <QueryClientProvider client={qc()}>
      <MemoryRouter initialEntries={["/workspace/campaigns/new"]}>
        <Routes>
          <Route
            path="/workspace/campaigns/new"
            element={<CampaignNewRoute />}
          />
          {/* Catch-all so navigation after create doesn't 404 in tests */}
          <Route path="/workspace/campaigns/:id" element={<div data-testid="detail-page" />} />
          <Route path="/workspace/campaigns" element={<div data-testid="list-page" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

function renderDetail(id = "c-00000000-0000-0000-0000-000000000001") {
  return render(
    <QueryClientProvider client={qc()}>
      <MemoryRouter initialEntries={[`/workspace/campaigns/${id}`]}>
        <Routes>
          <Route
            path="/workspace/campaigns/:id"
            element={<CampaignDetailRoute />}
          />
          <Route path="/workspace/campaigns" element={<div data-testid="list-page" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---- WorkspaceCampaignsRoute (list) -------------------------

describe("WorkspaceCampaignsRoute", () => {
  beforeEach(() => {
    vi.mocked(useMe).mockReturnValue({
      data: { default_workspace: { id: WORKSPACE_ID } },
    } as unknown as ReturnType<typeof useMe>);
  });

  it("renders the page title", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaigns>);

    renderList();

    expect(screen.getByTestId("campaigns-title")).toBeInTheDocument();
    expect(screen.getByText("Campaigns")).toBeInTheDocument();
  });

  it("renders campaign rows when campaigns are present", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: [makeCampaign()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaigns>);

    renderList();

    expect(screen.getByTestId("campaigns-list")).toBeInTheDocument();
    expect(
      screen.getByTestId("campaign-row-c-00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
    expect(screen.getByText("Q3 Outreach")).toBeInTheDocument();
  });

  it("renders empty state with create CTA when no campaigns", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaigns>);

    renderList();

    expect(screen.getByTestId("campaigns-empty")).toBeInTheDocument();
    expect(
      screen.getByRole("link", { name: /create your first campaign/i }),
    ).toBeInTheDocument();
  });

  it("shows loading skeleton while data fetches", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useCampaigns>);

    renderList();

    expect(screen.getByTestId("campaigns-skeleton")).toBeInTheDocument();
  });

  it("status filter chips render", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaigns>);

    renderList();

    expect(screen.getByTestId("filter-chip-all")).toBeInTheDocument();
    expect(screen.getByTestId("filter-chip-draft")).toBeInTheDocument();
    expect(screen.getByTestId("filter-chip-in_flight")).toBeInTheDocument();
  });

  it("renders New campaign button linking to /workspace/campaigns/new", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaigns>);

    renderList();

    const btn = screen.getByTestId("new-campaign-btn");
    expect(btn).toBeInTheDocument();
    expect(btn.closest("a")).toHaveAttribute("href", "/workspace/campaigns/new");
  });

  it("active filter chip is highlighted", () => {
    vi.mocked(useCampaigns).mockReturnValue({
      data: [makeCampaign()],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaigns>);

    renderList("?status=draft");

    const draftChip = screen.getByTestId("filter-chip-draft");
    // The active chip has the primary background class.
    expect(draftChip.className).toContain("bg-primary");
  });
});

// ---- CampaignNewRoute (create form) -------------------------

describe("CampaignNewRoute", () => {
  beforeEach(() => {
    vi.mocked(useMe).mockReturnValue({
      data: { default_workspace: { id: WORKSPACE_ID } },
    } as unknown as ReturnType<typeof useMe>);
    vi.mocked(useSpokespeople).mockReturnValue({
      data: [makeSpokesperson()],
      isLoading: false,
    } as unknown as ReturnType<typeof useSpokespeople>);
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(makeCampaign()),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateCampaign>);
  });

  it("renders the create form with required fields", () => {
    renderNew();

    expect(screen.getByTestId("campaign-new-title")).toBeInTheDocument();
    expect(screen.getByTestId("campaign-name-input")).toBeInTheDocument();
    expect(screen.getByTestId("campaign-spokesperson-select")).toBeInTheDocument();
    expect(screen.getByTestId("campaign-template-input")).toBeInTheDocument();
    expect(screen.getByTestId("campaign-create-submit")).toBeInTheDocument();
  });

  it("shows inline name validation error when name is empty on submit", async () => {
    const user = userEvent.setup();
    renderNew();

    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("campaign-name-error")).toBeInTheDocument();
    });
  });

  it("shows inline template validation error when template is empty on submit", async () => {
    const user = userEvent.setup();
    renderNew();

    await user.type(screen.getByTestId("campaign-name-input"), "My Campaign");
    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("campaign-template-error")).toBeInTheDocument();
    });
  });

  it("displays detected-vars preview as the operator types placeholders", async () => {
    const { fireEvent } = await import("@testing-library/react");
    renderNew();

    // userEvent.type can't handle literal "{" chars; use fireEvent.change instead.
    fireEvent.change(screen.getByTestId("campaign-template-input"), {
      target: { value: "Hi {first_name}, at {company}" },
    });

    await waitFor(() => {
      expect(screen.getByTestId("detected-var-first_name")).toBeInTheDocument();
      expect(screen.getByTestId("detected-var-company")).toBeInTheDocument();
    });
  });

  it("calls mutateAsync with correct payload on valid submit", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(makeCampaign());
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateCampaign>);
    const { fireEvent } = await import("@testing-library/react");

    renderNew();

    await user.type(screen.getByTestId("campaign-name-input"), "My Campaign");
    // Use fireEvent for template since "{" is a special char in userEvent.
    fireEvent.change(screen.getByTestId("campaign-template-input"), {
      target: { value: "Hi {first_name}" },
    });
    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "My Campaign",
          template: "Hi {first_name}",
          workspace_id: WORKSPACE_ID,
        }),
      );
    });
  });

  it("navigates to detail page after successful create", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(makeCampaign());
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateCampaign>);
    const { fireEvent } = await import("@testing-library/react");

    renderNew();

    await user.type(screen.getByTestId("campaign-name-input"), "My Campaign");
    fireEvent.change(screen.getByTestId("campaign-template-input"), {
      target: { value: "Hi {first_name}" },
    });
    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("detail-page")).toBeInTheDocument();
    });
  });

  it("shows spinner while mutation is pending", () => {
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: true,
    } as unknown as ReturnType<typeof useCreateCampaign>);

    renderNew();

    expect(screen.getByTestId("campaign-create-spinner")).toBeInTheDocument();
    expect(screen.getByTestId("campaign-create-submit")).toBeDisabled();
  });

  it("surfaces 400 template syntax error inline", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/client");
    const { fireEvent } = await import("@testing-library/react");
    const mutateAsync = vi.fn().mockRejectedValue(
      new ApiError("400", 400, {
        template: ["Template has malformed placeholder at position 5."],
      }),
    );
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateCampaign>);

    renderNew();

    await user.type(screen.getByTestId("campaign-name-input"), "Test");
    // Use fireEvent for template to avoid userEvent keyboard special-char issues.
    fireEvent.change(screen.getByTestId("campaign-template-input"), {
      target: { value: "Hi {bad template" },
    });
    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("campaign-submit-error")).toBeInTheDocument();
      expect(screen.getByTestId("campaign-submit-error")).toHaveTextContent(
        "Template has malformed placeholder at position 5.",
      );
    });
  });
});

// ---- CampaignDetailRoute ------------------------------------

describe("CampaignDetailRoute — metadata + CSV panel", () => {
  beforeEach(() => {
    vi.mocked(useDeleteCampaign).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useDeleteCampaign>);
    vi.mocked(useParseCsv).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({
        header: ["first_name", "company"],
        valid_count: 2,
        rejected_count: 0,
        rejected_rows: [],
        recipients: [makeRecipient(), makeRecipient({ id: "r-2", label: "Bob" })],
      }),
      isPending: false,
    } as unknown as ReturnType<typeof useParseCsv>);
    // B3.8 hooks — stub to safe defaults for B3.7 tests.
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

  it("renders campaign name, spokesperson, and status badge", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign(),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("campaign-detail-name")).toBeInTheDocument();
    expect(screen.getByText("Q3 Outreach")).toBeInTheDocument();
    expect(screen.getByText(/Sasha/)).toBeInTheDocument();
    expect(screen.getByTestId("campaign-status-badge")).toBeInTheDocument();
  });

  it("renders placeholder chips from the campaign", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign(),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("placeholder-chip-first_name")).toBeInTheDocument();
    expect(screen.getByTestId("placeholder-chip-company")).toBeInTheDocument();
  });

  it("renders the template preview", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign(),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("campaign-template-preview")).toHaveTextContent(
      "Hi {first_name}, saw {company}.",
    );
  });

  it("renders the CSV paste form for DRAFT campaigns", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "draft" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("csv-panel")).toBeInTheDocument();
    expect(screen.getByTestId("csv-textarea")).toBeInTheDocument();
    expect(screen.getByTestId("parse-csv-btn")).toBeInTheDocument();
  });

  it("shows loading skeleton while campaign loads", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("campaign-detail-skeleton")).toBeInTheDocument();
  });

  it("renders CSV parse happy path: valid count badge + recipient table", async () => {
    const user = userEvent.setup();
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "draft" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    await user.type(
      screen.getByTestId("csv-textarea"),
      "first_name,company\nAlice,Acme\nBob,Globex",
    );
    await user.click(screen.getByTestId("parse-csv-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("parse-result")).toBeInTheDocument();
      expect(screen.getByTestId("valid-count-badge")).toBeInTheDocument();
      expect(screen.getByTestId("valid-count-badge")).toHaveTextContent("2 valid");
    });
    expect(screen.getByTestId("recipients-preview")).toBeInTheDocument();
  });

  it("renders CSV header-error inline without replacing recipients", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/client");
    vi.mocked(useParseCsv).mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(
        new ApiError("400", 400, {
          header_error: "CSV header missing required columns: company",
          header: ["first_name"],
          valid_count: 0,
          rejected_count: 0,
          rejected_rows: [],
        }),
      ),
      isPending: false,
    } as unknown as ReturnType<typeof useParseCsv>);
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "draft" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    await user.type(screen.getByTestId("csv-textarea"), "first_name\nAlice");
    await user.click(screen.getByTestId("parse-csv-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("parse-header-error")).toBeInTheDocument();
      expect(screen.getByTestId("parse-header-error")).toHaveTextContent(
        "CSV header missing required columns: company",
      );
    });
    // Recipients preview must NOT appear.
    expect(screen.queryByTestId("recipients-preview")).not.toBeInTheDocument();
  });

  it("shows expandable rejected rows section when rejection count > 0", async () => {
    const user = userEvent.setup();
    vi.mocked(useParseCsv).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue({
        header: ["first_name", "company"],
        valid_count: 1,
        rejected_count: 1,
        rejected_rows: [
          {
            row_number: 2,
            error: "Missing column: company",
            raw: "Bob,",
          },
        ],
        recipients: [makeRecipient()],
      }),
      isPending: false,
    } as unknown as ReturnType<typeof useParseCsv>);
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "draft" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    await user.type(screen.getByTestId("csv-textarea"), "first_name,company\nAlice,Acme\nBob,");
    await user.click(screen.getByTestId("parse-csv-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("rejected-count-badge")).toBeInTheDocument();
      expect(screen.getByTestId("rejected-count-badge")).toHaveTextContent("1 rejected");
    });

    // Expand the rejected rows.
    await user.click(screen.getByTestId("rejected-count-badge"));

    await waitFor(() => {
      expect(screen.getByTestId("rejected-rows-section")).toBeInTheDocument();
      expect(screen.getByTestId("rejected-row-2")).toBeInTheDocument();
      expect(screen.getByTestId("rejected-row-2")).toHaveTextContent("Row 2");
      expect(screen.getByTestId("rejected-row-2")).toHaveTextContent("Missing column: company");
    });
  });

  it("renders Delete button only for DRAFT campaigns", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "draft" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("delete-campaign-btn")).toBeInTheDocument();
  });

  it("does not render Delete button for non-DRAFT campaigns", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "completed" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.queryByTestId("delete-campaign-btn")).not.toBeInTheDocument();
  });

  it("clicking Delete once shows confirmation prompt", async () => {
    const user = userEvent.setup();
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "draft" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    const deleteBtn = screen.getByTestId("delete-campaign-btn");
    await user.click(deleteBtn);

    // Button should now read "Confirm delete".
    await waitFor(() => {
      expect(screen.getByTestId("delete-campaign-btn")).toHaveTextContent("Confirm delete");
    });
  });

  it("confirms delete and navigates back to campaigns list", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    vi.mocked(useDeleteCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useDeleteCampaign>);
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "draft" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    // First click — shows confirmation.
    await user.click(screen.getByTestId("delete-campaign-btn"));
    // Second click — confirms.
    await user.click(screen.getByTestId("delete-campaign-btn"));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        "c-00000000-0000-0000-0000-000000000001",
      );
    });

    await waitFor(() => {
      expect(screen.getByTestId("list-page")).toBeInTheDocument();
    });
  });
});

// ---- B3.8 helpers -------------------------------------------

function makeForecast(overrides: Record<string, unknown> = {}) {
  return {
    recipient_count: 3,
    batch_cap: 5,
    videos_per_month_limit: 30,
    videos_used_this_month: 5,
    videos_remaining: 25,
    projected_cost_micros: 750_000,
    per_recipient_cost_micros: 250_000,
    ready_to_launch: true,
    blocking_reason: null,
    ...overrides,
  };
}

function makeRecipientRow(overrides: Record<string, unknown> = {}) {
  return {
    id: "r-00000000-0000-0000-0000-000000000001",
    campaign_id: "c-00000000-0000-0000-0000-000000000001",
    variables: { first_name: "Alice", company: "Acme" },
    label: "Alice",
    rendered_script: "",
    position: 1,
    status: "pending" as const,
    status_label: "Pending",
    produced_composition_id: null,
    error_message: "",
    created_at: "2026-05-19T10:00:00Z",
    updated_at: "2026-05-19T10:00:00Z",
    ...overrides,
  };
}

// ---- CampaignDetailRoute B3.8 — ForecastPanel + launch ------

describe("CampaignDetailRoute B3.8 — ForecastPanel + launch", () => {
  beforeEach(() => {
    vi.mocked(useDeleteCampaign).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useDeleteCampaign>);
    vi.mocked(useParseCsv).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useParseCsv>);
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

  it("renders forecast panel for DRAFT campaign with recipients", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "draft",
        recipient_counts: {
          pending: 3,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useCampaignForecast).mockReturnValue({
      data: makeForecast(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaignForecast>);
    vi.mocked(useLaunchCampaign).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useLaunchCampaign>);

    renderDetail();

    expect(screen.getByTestId("forecast-panel")).toBeInTheDocument();
    expect(screen.getByTestId("forecast-summary")).toBeInTheDocument();
    // $0.75 total from 3 × $0.25
    expect(screen.getByTestId("forecast-summary")).toHaveTextContent("$0.75");
  });

  it("does not render forecast panel when DRAFT campaign has no recipients", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "draft" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useCampaignForecast).mockReturnValue({
      data: makeForecast({ recipient_count: 0 }),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaignForecast>);
    vi.mocked(useLaunchCampaign).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useLaunchCampaign>);

    renderDetail();

    expect(screen.queryByTestId("forecast-panel")).not.toBeInTheDocument();
  });

  it("Launch button is disabled when ready_to_launch=false", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "draft",
        recipient_counts: {
          pending: 3,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useCampaignForecast).mockReturnValue({
      data: makeForecast({
        ready_to_launch: false,
        blocking_reason: {
          code: "personalized_batch_too_large",
          message: "Batch exceeds the limit.",
        },
      }),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaignForecast>);
    vi.mocked(useLaunchCampaign).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useLaunchCampaign>);

    renderDetail();

    expect(screen.getByTestId("launch-btn")).toBeDisabled();
    expect(screen.getByTestId("blocking-reason")).toBeInTheDocument();
    expect(screen.getByTestId("blocking-reason")).toHaveTextContent(
      "Batch exceeds your tier",
    );
  });

  it("clicking Launch button opens the confirmation modal", async () => {
    const user = userEvent.setup();
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "draft",
        recipient_counts: {
          pending: 3,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useCampaignForecast).mockReturnValue({
      data: makeForecast(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaignForecast>);
    vi.mocked(useLaunchCampaign).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useLaunchCampaign>);

    renderDetail();

    await user.click(screen.getByTestId("launch-btn"));

    await waitFor(() => {
      expect(screen.getByTestId("launch-modal")).toBeInTheDocument();
      expect(screen.getByTestId("launch-modal-heading")).toHaveTextContent(
        "Launch 3 personalized videos?",
      );
    });
  });

  it("modal Cancel closes without firing launch", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn();
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "draft",
        recipient_counts: {
          pending: 3,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useCampaignForecast).mockReturnValue({
      data: makeForecast(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaignForecast>);
    vi.mocked(useLaunchCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useLaunchCampaign>);

    renderDetail();

    await user.click(screen.getByTestId("launch-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("launch-modal")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("launch-modal-cancel"));

    await waitFor(() => {
      expect(screen.queryByTestId("launch-modal")).not.toBeInTheDocument();
    });
    expect(mutateAsync).not.toHaveBeenCalled();
  });

  it("modal Yes, launch fires mutateAsync and shows success banner", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue({
      campaign: makeCampaign({ status: "in_flight" }),
      queued_count: 3,
      failed_at_render_count: 0,
    });
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "draft",
        recipient_counts: {
          pending: 3,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useCampaignForecast).mockReturnValue({
      data: makeForecast(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaignForecast>);
    vi.mocked(useLaunchCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useLaunchCampaign>);

    renderDetail();

    await user.click(screen.getByTestId("launch-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("launch-modal")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("launch-modal-confirm"));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalled();
      expect(screen.queryByTestId("launch-modal")).not.toBeInTheDocument();
      expect(screen.getByTestId("launch-success-banner")).toBeInTheDocument();
    });
    expect(screen.getByTestId("launch-success-banner")).toHaveTextContent(
      "3 renders queued",
    );
  });

  it("launch 402 personalized_batch_too_large surfaces inline error", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/client");
    const mutateAsync = vi.fn().mockRejectedValue(
      new ApiError("402", 402, {
        code: "personalized_batch_too_large",
        message: "Batch of 40 exceeds your Pro tier cap of 30.",
      }),
    );
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "draft",
        recipient_counts: {
          pending: 40,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 0,
          total: 40,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useCampaignForecast).mockReturnValue({
      data: makeForecast({ recipient_count: 40, ready_to_launch: true }),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaignForecast>);
    vi.mocked(useLaunchCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useLaunchCampaign>);

    renderDetail();

    await user.click(screen.getByTestId("launch-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("launch-modal")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("launch-modal-confirm"));

    await waitFor(() => {
      expect(screen.getByTestId("launch-error")).toBeInTheDocument();
      expect(screen.getByTestId("launch-error")).toHaveTextContent(
        "Batch of 40 exceeds your Pro tier cap of 30.",
      );
    });
  });

  it("launch 402 video_limit_reached surfaces inline error", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/client");
    const mutateAsync = vi.fn().mockRejectedValue(
      new ApiError("402", 402, {
        code: "video_limit_reached",
        message: "Monthly video limit reached — 30 of 30 used.",
      }),
    );
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "draft",
        recipient_counts: {
          pending: 3,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useCampaignForecast).mockReturnValue({
      data: makeForecast({ videos_remaining: 0, ready_to_launch: true }),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useCampaignForecast>);
    vi.mocked(useLaunchCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useLaunchCampaign>);

    renderDetail();

    await user.click(screen.getByTestId("launch-btn"));
    await waitFor(() => {
      expect(screen.getByTestId("launch-modal")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("launch-modal-confirm"));

    await waitFor(() => {
      expect(screen.getByTestId("launch-error")).toBeInTheDocument();
      expect(screen.getByTestId("launch-error")).toHaveTextContent(
        "Monthly video limit reached",
      );
    });
  });
});

// ---- CampaignDetailRoute B3.8 — IN_FLIGHT recipient grid ----

describe("CampaignDetailRoute B3.8 — IN_FLIGHT grid", () => {
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
    vi.mocked(useRetryRecipient).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useRetryRecipient>);
  });

  it("renders recipient grid for IN_FLIGHT campaign", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "in_flight",
        recipient_counts: {
          pending: 0,
          queued: 2,
          running: 1,
          completed: 0,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [
        makeRecipientRow({ status: "queued", label: "Alice" }),
        makeRecipientRow({
          id: "r-2",
          status: "running",
          label: "Bob",
          variables: { first_name: "Bob", company: "Globex" },
        }),
        makeRecipientRow({
          id: "r-3",
          status: "queued",
          label: "Carol",
          variables: { first_name: "Carol", company: "Initech" },
        }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);

    renderDetail();

    expect(screen.getByTestId("recipient-grid")).toBeInTheDocument();
    expect(screen.getByTestId("progress-summary")).toBeInTheDocument();
    expect(screen.getByTestId("progress-bar")).toBeInTheDocument();
    // Recipient rows present.
    expect(
      screen.getByTestId("recipient-row-r-00000000-0000-0000-0000-000000000001"),
    ).toBeInTheDocument();
    expect(screen.getByTestId("recipient-row-r-2")).toBeInTheDocument();
  });

  it("status badges use correct palette: queued=amber, completed=emerald, failed=destructive", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "in_flight",
        recipient_counts: {
          pending: 0,
          queued: 1,
          running: 0,
          completed: 1,
          failed: 1,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [
        makeRecipientRow({ id: "r-1", status: "queued" }),
        makeRecipientRow({ id: "r-2", status: "completed" }),
        makeRecipientRow({ id: "r-3", status: "failed" }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);

    renderDetail();

    const queuedBadge = screen.getByTestId("recipient-status-badge-queued");
    expect(queuedBadge.className).toContain("amber");

    const completedBadge = screen.getByTestId("recipient-status-badge-completed");
    expect(completedBadge.className).toContain("emerald");

    const failedBadge = screen.getByTestId("recipient-status-badge-failed");
    expect(failedBadge.className).toContain("destructive");
  });

  it("progress summary shows active count and progress bar", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "in_flight",
        recipient_counts: {
          pending: 0,
          queued: 2,
          running: 0,
          completed: 1,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);

    renderDetail();

    const summary = screen.getByTestId("progress-summary");
    expect(summary).toHaveTextContent("1 of 3");
  });

  it("hides CSV panel for IN_FLIGHT campaign", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "in_flight",
        recipient_counts: {
          pending: 0,
          queued: 3,
          running: 0,
          completed: 0,
          failed: 0,
          total: 3,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);

    renderDetail();

    expect(screen.queryByTestId("csv-panel")).not.toBeInTheDocument();
    expect(screen.queryByTestId("forecast-panel")).not.toBeInTheDocument();
  });
});

// ---- CampaignDetailRoute B3.8 — terminal states + retry -----

describe("CampaignDetailRoute B3.8 — terminal states + retry", () => {
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
  });

  function setupTerminal(status: "completed" | "partial" | "failed") {
    const counts =
      status === "completed"
        ? { pending: 0, queued: 0, running: 0, completed: 3, failed: 0, total: 3 }
        : status === "partial"
          ? { pending: 0, queued: 0, running: 0, completed: 2, failed: 1, total: 3 }
          : { pending: 0, queued: 0, running: 0, completed: 0, failed: 3, total: 3 };

    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status, recipient_counts: counts }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);
    vi.mocked(useRetryRecipient).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useRetryRecipient>);
  }

  it("renders terminal banner for COMPLETED with correct text", () => {
    setupTerminal("completed");
    renderDetail();
    expect(screen.getByTestId("terminal-banner")).toBeInTheDocument();
    expect(screen.getByTestId("terminal-banner-text")).toHaveTextContent(
      "Completed — 3 of 3 rendered",
    );
  });

  it("renders terminal banner for PARTIAL with failed count", () => {
    setupTerminal("partial");
    renderDetail();
    expect(screen.getByTestId("terminal-banner-text")).toHaveTextContent(
      "Partial — 2 succeeded, 1 failed",
    );
  });

  it("renders terminal banner for FAILED", () => {
    setupTerminal("failed");
    renderDetail();
    expect(screen.getByTestId("terminal-banner-text")).toHaveTextContent(
      "Failed — all 3 recipients failed",
    );
  });

  it("Browse produced assets link is present for COMPLETED", () => {
    setupTerminal("completed");
    renderDetail();
    expect(screen.getByTestId("browse-assets-link")).toBeInTheDocument();
    expect(screen.getByTestId("browse-assets-link")).toHaveAttribute(
      "href",
      "/workspace/assets",
    );
  });

  it("Browse produced assets link is present for PARTIAL", () => {
    setupTerminal("partial");
    renderDetail();
    expect(screen.getByTestId("browse-assets-link")).toBeInTheDocument();
  });

  it("Browse produced assets link is absent for FAILED", () => {
    setupTerminal("failed");
    renderDetail();
    expect(screen.queryByTestId("browse-assets-link")).not.toBeInTheDocument();
  });

  it("Retry button is visible on FAILED recipient in FAILED campaign", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "failed",
        recipient_counts: {
          pending: 0,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 1,
          total: 1,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [
        makeRecipientRow({
          status: "failed",
          error_message: "Missing variable: milestone",
        }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);
    vi.mocked(useRetryRecipient).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useRetryRecipient>);

    renderDetail();

    const retryBtn = screen.getByTestId(
      "retry-btn-r-00000000-0000-0000-0000-000000000001",
    );
    expect(retryBtn).toBeInTheDocument();
    // Error message also renders.
    expect(
      screen.getByTestId(
        "recipient-error-r-00000000-0000-0000-0000-000000000001",
      ),
    ).toHaveTextContent("Missing variable: milestone");
  });

  it("clicking Retry once shows confirm text; second click fires mutateAsync", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue({
      recipient: makeRecipientRow({ status: "queued" }),
      campaign_status: "in_flight",
    });
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "failed",
        recipient_counts: {
          pending: 0,
          queued: 0,
          running: 0,
          completed: 0,
          failed: 1,
          total: 1,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [makeRecipientRow({ status: "failed" })],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);
    vi.mocked(useRetryRecipient).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useRetryRecipient>);

    renderDetail();

    const retryBtn = screen.getByTestId(
      "retry-btn-r-00000000-0000-0000-0000-000000000001",
    );

    // First click — shows confirm prompt.
    await user.click(retryBtn);
    await waitFor(() => {
      expect(retryBtn).toHaveTextContent("Confirm retry");
    });

    // Second click — fires mutateAsync.
    await user.click(retryBtn);
    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        "r-00000000-0000-0000-0000-000000000001",
      );
    });
  });

  it("Retry button is not visible for COMPLETED recipients in terminal campaign", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "completed",
        recipient_counts: {
          pending: 0,
          queued: 0,
          running: 0,
          completed: 1,
          failed: 0,
          total: 1,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [makeRecipientRow({ status: "completed" })],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);
    vi.mocked(useRetryRecipient).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useRetryRecipient>);

    renderDetail();

    expect(
      screen.queryByTestId(
        "retry-btn-r-00000000-0000-0000-0000-000000000001",
      ),
    ).not.toBeInTheDocument();
  });

  it("composition link renders on completed recipient rows", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({
        status: "completed",
        recipient_counts: {
          pending: 0,
          queued: 0,
          running: 0,
          completed: 1,
          failed: 0,
          total: 1,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useCampaign>);
    vi.mocked(useRecipients).mockReturnValue({
      data: [
        makeRecipientRow({
          status: "completed",
          produced_composition_id: "comp-uuid-42",
        }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useRecipients>);
    vi.mocked(useRetryRecipient).mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    } as unknown as ReturnType<typeof useRetryRecipient>);

    renderDetail();

    const link = screen.getByTestId(
      "recipient-composition-link-r-00000000-0000-0000-0000-000000000001",
    );
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute("href", "/compositions/comp-uuid-42");
  });
});
