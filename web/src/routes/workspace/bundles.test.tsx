/**
 * B14.4 route tests — /workspace/bundles (list),
 * /workspace/bundles/new (create), /workspace/bundles/:id (detail).
 *
 * Also covers: asset detail "Publish bundle" CTA (CLIP-only).
 *
 * Strategy: mock API hooks at the module boundary.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { WorkspaceBundlesRoute } from "./bundles";
import { BundleNewRoute } from "./bundles.new";
import { BundleDetailRoute } from "./bundles.$id";
import { WorkspaceAssetDetailRoute } from "./assets.$id";

// ---- Module mocks --------------------------------------------

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
}));

vi.mock("@/lib/api/workspace-assets", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/workspace-assets")>();
  return {
    ...actual,
    useWorkspaceAssets: vi.fn(),
    useWorkspaceAsset: vi.fn(),
  };
});

vi.mock("@/lib/api/bundles", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/bundles")>();
  return {
    ...actual,
    useBundles: vi.fn(),
    useBundle: vi.fn(),
    useBundleVariants: vi.fn(),
    useBundleForecast: vi.fn(),
    useCreateBundle: vi.fn(),
    useDeleteBundle: vi.fn(),
    useLaunchBundle: vi.fn(),
    useRetryVariant: vi.fn(),
  };
});

import { useMe } from "@/lib/api/workspaces";
import { useWorkspaceAssets, useWorkspaceAsset } from "@/lib/api/workspace-assets";
import {
  useBundles,
  useBundle,
  useBundleVariants,
  useBundleForecast,
  useCreateBundle,
  useDeleteBundle,
  useLaunchBundle,
  useRetryVariant,
} from "@/lib/api/bundles";

// ---- Fixtures ------------------------------------------------

const WORKSPACE_ID = "ws-00000000-0000-0000-0000-000000000001";
const BUNDLE_ID = "b-00000000-0000-0000-0000-000000000001";
const CLIP_ID = "a-00000000-0000-0000-0000-000000000001";
const VARIANT_ID = "v-00000000-0000-0000-0000-000000000001";

function makeBundle(overrides: Record<string, unknown> = {}) {
  return {
    id: BUNDLE_ID,
    workspace_id: WORKSPACE_ID,
    source_clip_id: CLIP_ID,
    name: "Q3 product launch",
    selected_platforms: ["reels", "tiktok"],
    status: "draft" as const,
    status_label: "Draft",
    variant_counts: {
      pending: 2,
      queued: 0,
      running: 0,
      completed: 0,
      failed: 0,
      total: 2,
    },
    launched_at: null,
    completed_at: null,
    created_at: "2026-05-19T10:00:00Z",
    updated_at: "2026-05-19T10:00:00Z",
    ...overrides,
  };
}

function makeVariant(overrides: Record<string, unknown> = {}) {
  return {
    id: VARIANT_ID,
    bundle_id: BUNDLE_ID,
    platform_key: "reels",
    target_ratio: "720:1280",
    max_duration_ms: 60000,
    status: "pending" as const,
    status_label: "Pending",
    produced_composition_id: null,
    error_message: "",
    created_at: "2026-05-19T10:00:00Z",
    updated_at: "2026-05-19T10:00:00Z",
    ...overrides,
  };
}

function makeClip(overrides: Record<string, unknown> = {}) {
  return {
    id: CLIP_ID,
    asset_type: "clip" as const,
    role: "composite_output" as const,
    file_path: "https://example.com/clip.mp4",
    title: "My product clip",
    subject: "",
    duration_ms: 30000,
    width: 1280,
    height: 720,
    mime_type: "video/mp4",
    size_bytes: 12345678,
    cost_micros: 250000,
    created_at: "2026-05-19T10:00:00Z",
    storage_health: "https_live" as const,
    primitive_kind: "generate_avatar_speech",
    producing_prompt: "",
    composition: null,
    ...overrides,
  };
}

function makeAssetDetail(overrides: Record<string, unknown> = {}) {
  return {
    ...makeClip(),
    producing_step: null,
    downstream_compositions: [],
    inline_content: "",
    ...overrides,
  };
}

function makeForecast(overrides: Record<string, unknown> = {}) {
  return {
    variant_count: 2,
    projected_cost_micros: 0,
    estimated_wall_time_s: 10,
    ready_to_launch: true,
    blocking_reason: null,
    ...overrides,
  };
}

// ---- Render helper ------------------------------------------

function renderWithProviders(
  ui: React.ReactElement,
  initialPath = "/",
  routePath = "/",
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route path={routePath} element={ui} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---- Default stubs for all tests ----------------------------

beforeEach(() => {
  vi.mocked(useMe).mockReturnValue({
    data: { default_workspace: { id: WORKSPACE_ID } },
    isLoading: false,
    isError: false,
  } as ReturnType<typeof useMe>);

  // Default idle stubs — individual tests override as needed.
  vi.mocked(useBundles).mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useBundles>);

  vi.mocked(useBundle).mockReturnValue({
    data: undefined,
    isLoading: true,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useBundle>);

  vi.mocked(useBundleVariants).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useBundleVariants>);

  vi.mocked(useBundleForecast).mockReturnValue({
    data: undefined,
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useBundleForecast>);

  vi.mocked(useCreateBundle).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useCreateBundle>);

  vi.mocked(useDeleteBundle).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useDeleteBundle>);

  vi.mocked(useLaunchBundle).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useLaunchBundle>);

  vi.mocked(useRetryVariant).mockReturnValue({
    mutateAsync: vi.fn(),
    isPending: false,
  } as unknown as ReturnType<typeof useRetryVariant>);

  vi.mocked(useWorkspaceAssets).mockReturnValue({
    data: { results: [makeClip()], count: 1, next: null, previous: null },
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useWorkspaceAssets>);

  vi.mocked(useWorkspaceAsset).mockReturnValue({
    data: makeAssetDetail(),
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  } as unknown as ReturnType<typeof useWorkspaceAsset>);
});

// ---- List route tests ---------------------------------------

describe("WorkspaceBundlesRoute (list)", () => {
  it("renders the page title", () => {
    vi.mocked(useBundles).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundles>);

    renderWithProviders(
      <WorkspaceBundlesRoute />,
      "/workspace/bundles",
      "/workspace/bundles",
    );
    expect(screen.getByTestId("bundles-title")).toBeInTheDocument();
  });

  it("renders empty state when no bundles", () => {
    vi.mocked(useBundles).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundles>);

    renderWithProviders(
      <WorkspaceBundlesRoute />,
      "/workspace/bundles",
      "/workspace/bundles",
    );
    expect(screen.getByTestId("bundles-empty")).toBeInTheDocument();
  });

  it("renders bundle rows when data is present", () => {
    vi.mocked(useBundles).mockReturnValue({
      data: [makeBundle()],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundles>);

    renderWithProviders(
      <WorkspaceBundlesRoute />,
      "/workspace/bundles",
      "/workspace/bundles",
    );
    expect(screen.getByTestId(`bundle-row-${BUNDLE_ID}`)).toBeInTheDocument();
    expect(screen.getByTestId(`bundle-name-${BUNDLE_ID}`)).toHaveTextContent(
      "Q3 product launch",
    );
  });

  it("renders all status filter chips", () => {
    vi.mocked(useBundles).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundles>);

    renderWithProviders(
      <WorkspaceBundlesRoute />,
      "/workspace/bundles",
      "/workspace/bundles",
    );
    for (const chip of ["all", "draft", "in_flight", "completed", "partial", "failed"]) {
      expect(screen.getByTestId(`filter-chip-${chip}`)).toBeInTheDocument();
    }
  });

  it("renders loading skeleton while loading", () => {
    vi.mocked(useBundles).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundles>);

    renderWithProviders(
      <WorkspaceBundlesRoute />,
      "/workspace/bundles",
      "/workspace/bundles",
    );
    expect(screen.getByTestId("bundles-skeleton")).toBeInTheDocument();
  });

  it("renders new bundle CTA button", () => {
    vi.mocked(useBundles).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundles>);

    renderWithProviders(
      <WorkspaceBundlesRoute />,
      "/workspace/bundles",
      "/workspace/bundles",
    );
    expect(screen.getByTestId("new-bundle-btn")).toBeInTheDocument();
  });
});

// ---- Create route tests -------------------------------------

describe("BundleNewRoute (create)", () => {
  it("renders the create form", () => {
    renderWithProviders(
      <BundleNewRoute />,
      "/workspace/bundles/new",
      "/workspace/bundles/new",
    );
    expect(screen.getByTestId("bundle-new-title")).toBeInTheDocument();
    expect(screen.getByTestId("bundle-create-form")).toBeInTheDocument();
    expect(screen.getByTestId("bundle-name-input")).toBeInTheDocument();
  });

  it("renders platform checkboxes for all 5 platforms", () => {
    renderWithProviders(
      <BundleNewRoute />,
      "/workspace/bundles/new",
      "/workspace/bundles/new",
    );
    for (const key of ["reels", "shorts", "tiktok", "x_twitter", "linkedin"]) {
      expect(screen.getByTestId(`platform-checkbox-${key}`)).toBeInTheDocument();
    }
  });

  it("shows clip picker with available clips", () => {
    renderWithProviders(
      <BundleNewRoute />,
      "/workspace/bundles/new",
      "/workspace/bundles/new",
    );
    expect(screen.getByTestId("clip-picker-list")).toBeInTheDocument();
    expect(screen.getByTestId(`clip-option-${CLIP_ID}`)).toBeInTheDocument();
  });

  it("shows validation errors when submitted empty", async () => {
    renderWithProviders(
      <BundleNewRoute />,
      "/workspace/bundles/new",
      "/workspace/bundles/new",
    );
    const submitBtn = screen.getByTestId("bundle-create-submit");
    await userEvent.click(submitBtn);
    expect(screen.getByTestId("bundle-name-error")).toBeInTheDocument();
    expect(screen.getByTestId("bundle-platform-error")).toBeInTheDocument();
  });

  it("toggles platform checkbox on click", async () => {
    renderWithProviders(
      <BundleNewRoute />,
      "/workspace/bundles/new",
      "/workspace/bundles/new",
    );
    const checkbox = screen.getByTestId("platform-checkbox-reels") as HTMLInputElement;
    expect(checkbox.checked).toBe(false);
    await userEvent.click(
      screen.getByTestId("platform-checkbox-label-reels"),
    );
    expect(checkbox.checked).toBe(true);
  });

  it("submits and navigates on success", async () => {
    const newBundle = makeBundle({ id: "b-new-id-001" });
    vi.mocked(useCreateBundle).mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(newBundle),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateBundle>);

    const qc = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });

    // We need a navigate mock — use a memory router that shows the
    // result route so we can detect navigation indirectly.
    render(
      <QueryClientProvider client={qc}>
        <MemoryRouter initialEntries={["/workspace/bundles/new"]}>
          <Routes>
            <Route path="/workspace/bundles/new" element={<BundleNewRoute />} />
            <Route
              path="/workspace/bundles/:id"
              element={<div data-testid="bundle-detail-page" />}
            />
          </Routes>
        </MemoryRouter>
      </QueryClientProvider>,
    );

    // Fill in name
    await userEvent.type(screen.getByTestId("bundle-name-input"), "Q3 launch");
    // Select source clip
    await userEvent.click(screen.getByTestId(`clip-option-${CLIP_ID}`));
    // Select a platform
    await userEvent.click(
      screen.getByTestId("platform-checkbox-label-reels"),
    );

    await userEvent.click(screen.getByTestId("bundle-create-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("bundle-detail-page")).toBeInTheDocument();
    });
  });

  it("prefills source clip from query param source_clip_id", async () => {
    renderWithProviders(
      <BundleNewRoute />,
      `/workspace/bundles/new?source_clip_id=${CLIP_ID}`,
      "/workspace/bundles/new",
    );

    // The prefilled clip shows in the selected-clip-display hint.
    await waitFor(() => {
      expect(screen.getByTestId("selected-clip-display")).toBeInTheDocument();
    });
    expect(screen.getByTestId("selected-clip-display")).toHaveTextContent(
      "My product clip",
    );
  });

  it("shows submit error inline on API 400", async () => {
    const { ApiError } = await import("@/lib/api/client");
    vi.mocked(useCreateBundle).mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(
        new ApiError("Bad request", 400, { detail: "Invalid platform." }),
      ),
      isPending: false,
    } as unknown as ReturnType<typeof useCreateBundle>);

    renderWithProviders(
      <BundleNewRoute />,
      "/workspace/bundles/new",
      "/workspace/bundles/new",
    );

    // Fill out enough to pass client validation
    await userEvent.type(screen.getByTestId("bundle-name-input"), "Q3");
    await userEvent.click(screen.getByTestId(`clip-option-${CLIP_ID}`));
    await userEvent.click(
      screen.getByTestId("platform-checkbox-label-reels"),
    );
    await userEvent.click(screen.getByTestId("bundle-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("bundle-submit-error")).toBeInTheDocument();
    });
  });
});

// ---- Detail route — DRAFT -----------------------------------

describe("BundleDetailRoute — DRAFT", () => {
  beforeEach(() => {
    vi.mocked(useBundle).mockReturnValue({
      data: makeBundle(),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundle>);
    vi.mocked(useBundleVariants).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useBundleVariants>);
    vi.mocked(useBundleForecast).mockReturnValue({
      data: makeForecast(),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useBundleForecast>);
  });

  it("renders bundle name and status badge", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("bundle-detail-name")).toHaveTextContent(
      "Q3 product launch",
    );
    expect(screen.getByTestId("bundle-status-badge")).toBeInTheDocument();
  });

  it("renders forecast panel with cost $0 and estimated wall-time", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    const summary = screen.getByTestId("forecast-summary");
    expect(summary).toHaveTextContent("$0.00");
    expect(summary).toHaveTextContent("10s");
  });

  it("launch button is enabled when ready_to_launch=true", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    const btn = screen.getByTestId("launch-btn");
    expect(btn).not.toBeDisabled();
  });

  it("launch button is disabled when ready_to_launch=false", () => {
    vi.mocked(useBundleForecast).mockReturnValue({
      data: makeForecast({
        ready_to_launch: false,
        blocking_reason: { code: "no_variants", message: "No variants." },
      }),
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useBundleForecast>);

    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("launch-btn")).toBeDisabled();
    expect(screen.getByTestId("blocking-reason")).toBeInTheDocument();
  });

  it("opens launch modal on launch button click", async () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    await userEvent.click(screen.getByTestId("launch-btn"));
    expect(screen.getByTestId("launch-modal")).toBeInTheDocument();
    expect(screen.getByTestId("launch-modal-heading")).toHaveTextContent(
      "2 variants",
    );
  });

  it("closes launch modal on cancel", async () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    await userEvent.click(screen.getByTestId("launch-btn"));
    expect(screen.getByTestId("launch-modal")).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("launch-modal-cancel"));
    expect(screen.queryByTestId("launch-modal")).not.toBeInTheDocument();
  });

  it("renders platform chips in metadata panel", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("platform-chip-reels")).toBeInTheDocument();
    expect(screen.getByTestId("platform-chip-tiktok")).toBeInTheDocument();
  });

  it("renders variant preview rows in forecast panel", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("variant-preview-row-reels")).toBeInTheDocument();
    expect(screen.getByTestId("variant-preview-row-tiktok")).toBeInTheDocument();
  });

  it("modal shows $0.00 cost", async () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    await userEvent.click(screen.getByTestId("launch-btn"));
    expect(screen.getByTestId("launch-modal")).toHaveTextContent("$0.00");
  });
});

// ---- Detail route — IN_FLIGHT + progress grid ---------------

describe("BundleDetailRoute — IN_FLIGHT", () => {
  beforeEach(() => {
    vi.mocked(useBundle).mockReturnValue({
      data: makeBundle({
        status: "in_flight",
        variant_counts: {
          pending: 0,
          queued: 1,
          running: 1,
          completed: 0,
          failed: 0,
          total: 2,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundle>);
    vi.mocked(useBundleVariants).mockReturnValue({
      data: [
        makeVariant({ status: "queued" }),
        makeVariant({
          id: "v-00000000-0000-0000-0000-000000000002",
          platform_key: "tiktok",
          target_ratio: "720:1280",
          max_duration_ms: 90000,
          status: "running",
        }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useBundleVariants>);
  });

  it("renders variant grid", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("variant-grid")).toBeInTheDocument();
  });

  it("renders progress summary with correct count", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("progress-summary")).toBeInTheDocument();
  });

  it("renders progress bar", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("progress-bar")).toBeInTheDocument();
  });

  it("renders variant rows with status badges", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId(`variant-row-${VARIANT_ID}`)).toBeInTheDocument();
    expect(
      screen.getByTestId("variant-status-badge-queued"),
    ).toBeInTheDocument();
  });

  it("does not render forecast panel in IN_FLIGHT", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    // Forecast panel only shows for DRAFT
    expect(screen.queryByTestId("forecast-panel")).not.toBeInTheDocument();
  });
});

// ---- Detail route — PARTIAL (terminal + retry) --------------

describe("BundleDetailRoute — PARTIAL (terminal)", () => {
  beforeEach(() => {
    vi.mocked(useBundle).mockReturnValue({
      data: makeBundle({
        status: "partial",
        variant_counts: {
          pending: 0,
          queued: 0,
          running: 0,
          completed: 1,
          failed: 1,
          total: 2,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundle>);
    vi.mocked(useBundleVariants).mockReturnValue({
      data: [
        makeVariant({ status: "completed" }),
        makeVariant({
          id: "v-00000000-0000-0000-0000-000000000002",
          platform_key: "tiktok",
          target_ratio: "720:1280",
          max_duration_ms: 90000,
          status: "failed",
          error_message: "ffmpeg error: codec not found",
        }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useBundleVariants>);
  });

  it("renders terminal banner with partial text", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("terminal-banner")).toBeInTheDocument();
    expect(screen.getByTestId("terminal-banner-text")).toHaveTextContent(
      "Partial",
    );
  });

  it("renders browse assets link", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("browse-assets-link")).toBeInTheDocument();
  });

  it("renders retry button on failed variant row", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    const retryBtn = screen.getByTestId(
      "retry-btn-v-00000000-0000-0000-0000-000000000002",
    );
    expect(retryBtn).toBeInTheDocument();
    expect(retryBtn).toHaveTextContent("Retry");
  });

  it("retry button moves to 'confirm retry' on first click", async () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    const retryBtn = screen.getByTestId(
      "retry-btn-v-00000000-0000-0000-0000-000000000002",
    );
    await userEvent.click(retryBtn);
    expect(retryBtn).toHaveTextContent("Confirm retry");
  });

  it("fires retry mutation on confirm click", async () => {
    const mockRetry = vi.fn().mockResolvedValue({
      variant: makeVariant({ id: "v-00000000-0000-0000-0000-000000000002", status: "queued" }),
      bundle_status: "in_flight",
    });
    vi.mocked(useRetryVariant).mockReturnValue({
      mutateAsync: mockRetry,
      isPending: false,
    } as unknown as ReturnType<typeof useRetryVariant>);

    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    const retryBtn = screen.getByTestId(
      "retry-btn-v-00000000-0000-0000-0000-000000000002",
    );
    // First click → confirm state
    await userEvent.click(retryBtn);
    // Second click → fires mutation
    await userEvent.click(retryBtn);
    await waitFor(() => {
      expect(mockRetry).toHaveBeenCalledWith(
        "v-00000000-0000-0000-0000-000000000002",
      );
    });
  });

  it("shows error message on failed variant", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(
      screen.getByTestId("variant-error-v-00000000-0000-0000-0000-000000000002"),
    ).toHaveTextContent("ffmpeg error");
  });
});

// ---- Detail route — COMPLETED -------------------------------

describe("BundleDetailRoute — COMPLETED", () => {
  beforeEach(() => {
    vi.mocked(useBundle).mockReturnValue({
      data: makeBundle({
        status: "completed",
        variant_counts: {
          pending: 0,
          queued: 0,
          running: 0,
          completed: 2,
          failed: 0,
          total: 2,
        },
      }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundle>);
    vi.mocked(useBundleVariants).mockReturnValue({
      data: [
        makeVariant({ status: "completed" }),
        makeVariant({
          id: "v-00000000-0000-0000-0000-000000000002",
          platform_key: "tiktok",
          target_ratio: "720:1280",
          max_duration_ms: 90000,
          status: "completed",
        }),
      ],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useBundleVariants>);
  });

  it("renders completed terminal banner", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("terminal-banner-text")).toHaveTextContent(
      "Completed",
    );
  });

  it("no retry buttons on completed rows", () => {
    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.queryByTestId(`retry-btn-${VARIANT_ID}`)).not.toBeInTheDocument();
  });
});

// ---- Detail route — loading skeleton + error states ---------

describe("BundleDetailRoute — loading / error states", () => {
  it("renders loading skeleton", () => {
    vi.mocked(useBundle).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundle>);

    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/${BUNDLE_ID}`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("bundle-detail-skeleton")).toBeInTheDocument();
  });

  it("renders not-found for 404", () => {
    vi.mocked(useBundle).mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: { status: 404, message: "Not found" },
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useBundle>);

    renderWithProviders(
      <BundleDetailRoute />,
      `/workspace/bundles/nonexistent`,
      `/workspace/bundles/:id`,
    );
    expect(screen.getByTestId("bundle-not-found")).toBeInTheDocument();
  });
});

// ---- Asset detail — "Publish bundle" CTA --------------------

describe("WorkspaceAssetDetailRoute — Publish bundle CTA", () => {
  it("shows Publish bundle CTA for CLIP assets", async () => {
    vi.mocked(useWorkspaceAsset).mockReturnValue({
      data: makeAssetDetail({ asset_type: "clip" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useWorkspaceAsset>);

    renderWithProviders(
      <WorkspaceAssetDetailRoute />,
      `/workspace/assets/${CLIP_ID}`,
      `/workspace/assets/:id`,
    );
    await waitFor(() => {
      expect(screen.getByTestId("publish-bundle-cta")).toBeInTheDocument();
    });
  });

  it("does NOT show Publish bundle CTA for IMAGE assets", async () => {
    vi.mocked(useWorkspaceAsset).mockReturnValue({
      data: makeAssetDetail({ asset_type: "image" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useWorkspaceAsset>);

    renderWithProviders(
      <WorkspaceAssetDetailRoute />,
      `/workspace/assets/${CLIP_ID}`,
      `/workspace/assets/:id`,
    );
    expect(screen.queryByTestId("publish-bundle-cta")).not.toBeInTheDocument();
  });

  it("does NOT show Publish bundle CTA for TRANSCRIPT assets", async () => {
    vi.mocked(useWorkspaceAsset).mockReturnValue({
      data: makeAssetDetail({ asset_type: "transcript" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useWorkspaceAsset>);

    renderWithProviders(
      <WorkspaceAssetDetailRoute />,
      `/workspace/assets/${CLIP_ID}`,
      `/workspace/assets/:id`,
    );
    expect(screen.queryByTestId("publish-bundle-cta")).not.toBeInTheDocument();
  });

  it("Publish bundle CTA links to bundles/new?source_clip_id=<id>", async () => {
    vi.mocked(useWorkspaceAsset).mockReturnValue({
      data: makeAssetDetail({ id: CLIP_ID, asset_type: "clip" }),
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    } as unknown as ReturnType<typeof useWorkspaceAsset>);

    renderWithProviders(
      <WorkspaceAssetDetailRoute />,
      `/workspace/assets/${CLIP_ID}`,
      `/workspace/assets/:id`,
    );
    await waitFor(() => {
      const cta = screen.getByTestId("publish-bundle-cta");
      expect(cta).toHaveAttribute(
        "href",
        `/workspace/bundles/new?source_clip_id=${CLIP_ID}`,
      );
    });
  });
});
