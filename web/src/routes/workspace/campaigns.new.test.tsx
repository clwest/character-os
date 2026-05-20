/**
 * BC4 tests — /workspace/campaigns/new Script picker.
 *
 * Covers Q-bc-3, Q-bc-4, Q-bc-5, Q-bc-8 resolution.
 *
 * Strategy: mock API hooks at module boundary; no real fetches.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { fireEvent } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { CampaignNewRoute } from "./campaigns.new";

// ---- Module mocks --------------------------------------------

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
}));

vi.mock("@/lib/api/spokespeople", () => ({
  useSpokespeople: vi.fn(),
}));

vi.mock("@/lib/api/campaigns", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/campaigns")>();
  return {
    ...actual,
    useCreateCampaign: vi.fn(),
  };
});

vi.mock("@/lib/api/scripts", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/scripts")>();
  return {
    ...actual,
    useScripts: vi.fn(),
  };
});

import { useMe } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import { useCreateCampaign } from "@/lib/api/campaigns";
import { useScripts } from "@/lib/api/scripts";

// ---- Fixtures ------------------------------------------------

const WORKSPACE_ID = "ws-00000000-0000-0000-0000-000000000001";
const SP_ID = "sp-00000000-0000-0000-0000-000000000001";

function makeSpokesperson(overrides: Record<string, unknown> = {}) {
  return {
    id: SP_ID,
    workspace: WORKSPACE_ID,
    name: "Sasha",
    business_brief: "SaaS sales",
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

function makeScript(overrides: Record<string, unknown> = {}) {
  return {
    id: "sc-00000000-0000-0000-0000-000000000001",
    workspace_id: WORKSPACE_ID,
    spokesperson_id: SP_ID,
    spokesperson_name: "Sasha",
    name: "Five Good Emperors",
    prompt: "Write about Roman history",
    opener: "",
    draft_text: "The reign of the Five Good Emperors marked an era of prosperity.",
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
    ...overrides,
  };
}

function makeCampaign(overrides: Record<string, unknown> = {}) {
  return {
    id: "c-00000000-0000-0000-0000-000000000001",
    workspace_id: WORKSPACE_ID,
    spokesperson_id: SP_ID,
    spokesperson_name: "Sasha",
    name: "Test Campaign",
    template: "Hi there",
    placeholders: [],
    status: "draft" as const,
    status_label: "Draft",
    recipient_counts: {
      pending: 0, queued: 0, running: 0, completed: 0, failed: 0, total: 0,
    },
    launched_at: null,
    completed_at: null,
    created_at: "2026-05-20T00:00:00Z",
    updated_at: "2026-05-20T00:00:00Z",
    source_script: null,
    ...overrides,
  };
}

// ---- Render helper -------------------------------------------

function qc() {
  return new QueryClient({ defaultOptions: { queries: { retry: false } } });
}

function renderNew() {
  return render(
    <QueryClientProvider client={qc()}>
      <MemoryRouter initialEntries={["/workspace/campaigns/new"]}>
        <Routes>
          <Route path="/workspace/campaigns/new" element={<CampaignNewRoute />} />
          <Route path="/workspace/campaigns/:id" element={<div data-testid="detail-page" />} />
          <Route path="/workspace/campaigns" element={<div data-testid="list-page" />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// ---- Shared setup --------------------------------------------

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

  // Default: one READY script
  vi.mocked(useScripts).mockReturnValue({
    data: [makeScript()],
    isLoading: false,
    isError: false,
  } as unknown as ReturnType<typeof useScripts>);
});

// ---- Tests ---------------------------------------------------

describe("CampaignNewRoute BC4 — Script picker", () => {
  it("renders the script picker section", () => {
    renderNew();
    expect(screen.getByTestId("script-picker-section")).toBeInTheDocument();
    expect(screen.getByTestId("script-picker-select")).toBeInTheDocument();
  });

  it("Q-bc-4: picker calls useScripts with spokesperson filter by default", () => {
    renderNew();
    // useScripts is called with the spokesperson filter applied
    expect(vi.mocked(useScripts)).toHaveBeenCalledWith(
      WORKSPACE_ID,
      expect.objectContaining({ spokesperson: SP_ID, status: "ready" }),
    );
  });

  it("Q-bc-4: Show all workspace scripts toggle drops spokesperson filter", async () => {
    const user = userEvent.setup();
    renderNew();

    await user.click(screen.getByTestId("script-picker-show-all-toggle"));

    // After toggle, useScripts should be called without spokesperson filter
    expect(vi.mocked(useScripts)).toHaveBeenCalledWith(
      WORKSPACE_ID,
      expect.objectContaining({ status: "ready" }),
    );
    // The call without spokesperson filter should exist
    const calls = vi.mocked(useScripts).mock.calls;
    const wideCall = calls.find(
      (call) => call[1] && !("spokesperson" in (call[1] as object)),
    );
    expect(wideCall).toBeDefined();
  });

  it("picker empty state when no scripts match", () => {
    vi.mocked(useScripts).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    } as unknown as ReturnType<typeof useScripts>);

    renderNew();
    expect(screen.getByTestId("script-picker-empty")).toBeInTheDocument();
    expect(screen.getByText(/draft one at/i)).toBeInTheDocument();
  });

  it("picking a script renders the preview card", async () => {
    const user = userEvent.setup();
    renderNew();

    await user.selectOptions(
      screen.getByTestId("script-picker-select"),
      "sc-00000000-0000-0000-0000-000000000001",
    );

    await waitFor(() => {
      expect(
        screen.getByTestId("script-preview-card-sc-00000000-0000-0000-0000-000000000001"),
      ).toBeInTheDocument();
      expect(screen.getByTestId("script-preview-name")).toHaveTextContent(
        "Five Good Emperors",
      );
    });
  });

  it("Q-bc-8: 'Use this draft as starting template' copies draft_text verbatim", async () => {
    const user = userEvent.setup();
    renderNew();

    await user.selectOptions(
      screen.getByTestId("script-picker-select"),
      "sc-00000000-0000-0000-0000-000000000001",
    );

    await waitFor(() => {
      expect(screen.getByTestId("script-use-as-template-btn")).toBeInTheDocument();
    });

    await user.click(screen.getByTestId("script-use-as-template-btn"));

    await waitFor(() => {
      const textarea = screen.getByTestId("campaign-template-input") as HTMLTextAreaElement;
      expect(textarea.value).toBe(
        "The reign of the Five Good Emperors marked an era of prosperity.",
      );
    });
  });

  it("submit with source_script_id includes it in the create payload", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(makeCampaign());
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateCampaign>);

    renderNew();

    // Fill campaign name
    await user.type(screen.getByTestId("campaign-name-input"), "My Campaign");

    // Pick script
    await user.selectOptions(
      screen.getByTestId("script-picker-select"),
      "sc-00000000-0000-0000-0000-000000000001",
    );

    // Use as template
    await waitFor(() => {
      expect(screen.getByTestId("script-use-as-template-btn")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("script-use-as-template-btn"));

    // Submit
    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          source_script_id: "sc-00000000-0000-0000-0000-000000000001",
        }),
      );
    });
  });

  it("submit without picking a script omits source_script_id (back-compat)", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(makeCampaign());
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateCampaign>);

    renderNew();

    await user.type(screen.getByTestId("campaign-name-input"), "Free Form Campaign");
    fireEvent.change(screen.getByTestId("campaign-template-input"), {
      target: { value: "Hi {first_name}" },
    });
    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(mutateAsync).toHaveBeenCalledWith(
        expect.objectContaining({
          name: "Free Form Campaign",
          template: "Hi {first_name}",
        }),
      );
      // source_script_id should NOT be present when no script picked
      const call = mutateAsync.mock.calls[0]?.[0] as Record<string, unknown>;
      expect(call.source_script_id).toBeUndefined();
    });
  });

  it("backend 400 source_script_not_ready surfaces inline error", async () => {
    const user = userEvent.setup();
    const { ApiError } = await import("@/lib/api/client");
    const mutateAsync = vi.fn().mockRejectedValue(
      new ApiError("400", 400, {
        code: "source_script_not_ready",
        detail: "Script must be READY or RENDERED to ground a campaign.",
      }),
    );
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateCampaign>);

    renderNew();

    await user.type(screen.getByTestId("campaign-name-input"), "My Campaign");

    // Pick script + use as template
    await user.selectOptions(
      screen.getByTestId("script-picker-select"),
      "sc-00000000-0000-0000-0000-000000000001",
    );
    await waitFor(() => {
      expect(screen.getByTestId("script-use-as-template-btn")).toBeInTheDocument();
    });
    await user.click(screen.getByTestId("script-use-as-template-btn"));

    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("campaign-submit-error")).toBeInTheDocument();
      expect(screen.getByTestId("campaign-submit-error")).toHaveTextContent(
        "only READY or RENDERED scripts can ground a campaign",
      );
    });
  });

  it("template required when no script is picked (existing validation)", async () => {
    const user = userEvent.setup();
    renderNew();

    await user.type(screen.getByTestId("campaign-name-input"), "My Campaign");
    // Do NOT fill template or pick a script
    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("campaign-template-error")).toBeInTheDocument();
    });
  });

  it("template NOT required when a script is picked (cross-field relaxation)", async () => {
    const user = userEvent.setup();
    const mutateAsync = vi.fn().mockResolvedValue(makeCampaign());
    vi.mocked(useCreateCampaign).mockReturnValue({
      mutateAsync,
      isPending: false,
    } as unknown as ReturnType<typeof useCreateCampaign>);

    renderNew();

    await user.type(screen.getByTestId("campaign-name-input"), "My Campaign");

    // Pick script WITHOUT clicking "Use as template"
    await user.selectOptions(
      screen.getByTestId("script-picker-select"),
      "sc-00000000-0000-0000-0000-000000000001",
    );

    // Template textarea is empty — but validation should pass because sourceScriptId is set
    await user.click(screen.getByTestId("campaign-create-submit"));

    await waitFor(() => {
      expect(screen.queryByTestId("campaign-template-error")).not.toBeInTheDocument();
      expect(mutateAsync).toHaveBeenCalled();
    });
  });
});
