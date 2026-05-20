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
  });

  it("renders campaign name, spokesperson, and status badge", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign(),
      isLoading: false,
      isError: false,
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
    } as unknown as ReturnType<typeof useCampaign>);

    renderDetail();

    expect(screen.getByTestId("delete-campaign-btn")).toBeInTheDocument();
  });

  it("does not render Delete button for non-DRAFT campaigns", () => {
    vi.mocked(useCampaign).mockReturnValue({
      data: makeCampaign({ status: "completed" }),
      isLoading: false,
      isError: false,
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
