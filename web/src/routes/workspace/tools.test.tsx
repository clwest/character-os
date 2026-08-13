/**
 * /workspace/tools vitest coverage — C5.1.
 *
 * Guards the load-bearing invariants from BRIDGE_TOOLS_UI_V1.md:
 *   - Rule 2 (never start a live realtime session): only create + invoke
 *     endpoints get called; no follow-up start_session hop.
 *   - Rule 3 (DRAFT session is page-scoped) + Rule 5 (auto-create + reuse):
 *     first dispatch creates the DRAFT; second dispatch on the same
 *     spokesperson reuses.
 *   - Rule 4 tier + cost surfacing: picker option labels include
 *     "Pro · $0.005" (partial P3 4.4 coverage).
 *   - Rule 8 (EB) tier gate: Starter workspaces see the placeholder
 *     nudge, not the form.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
  useSubscription: vi.fn(),
}));

vi.mock("@/lib/api/spokespeople", async (importActual) => {
  const actual =
    await importActual<typeof import("@/lib/api/spokespeople")>();
  return {
    ...actual,
    useSpokespeople: vi.fn(),
  };
});

vi.mock("@/lib/api/realtime", async (importActual) => {
  const actual = await importActual<typeof import("@/lib/api/realtime")>();
  return {
    ...actual,
    useCreateRealtimeSession: vi.fn(),
    useInvokeTool: vi.fn(),
  };
});

import { useMe, useSubscription } from "@/lib/api/workspaces";
import { useSpokespeople } from "@/lib/api/spokespeople";
import {
  useCreateRealtimeSession,
  useInvokeTool,
} from "@/lib/api/realtime";
import { WorkspaceToolsRoute } from "./tools";

// ---- Test fixtures --------------------------------------------

const MOCK_ME = {
  id: "user-1",
  email: "op@example.com",
  is_staff: false,
  default_workspace: {
    id: "ws-1",
    name: "Demo Workspace",
    slug: "demo",
    role: "owner",
  },
};

function mockSubscription(tier: string) {
  return {
    workspace_id: "ws-1",
    workspace_name: "Demo Workspace",
    tier,
    status: "active",
    videos_used: 0,
    videos_limit: null,
    spokespeople_used: 1,
    spokespeople_limit: null,
    period_start: "2026-07-01T00:00:00Z",
    period_end: "2026-08-01T00:00:00Z",
  };
}

function mockSpokesperson(id: string, name: string, workspace = "ws-1") {
  return {
    id,
    workspace,
    workspace_name: "Demo Workspace",
    name,
    business_brief: "",
    personality: "",
    visual_subject: "",
    visual_template: "founder" as const,
    tone_archetype: "friend" as const,
    status: "ready" as const,
    runway_avatar_id: "av-1",
    runway_avatar_status: "ready",
    portrait_path: "",
    voice_id: "vo-1",
    video_count: 0,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  };
}

function mockSessionWithKey(id = "rt-1") {
  return {
    id,
    workspace: "ws-1",
    spokesperson: "sp-1",
    spokesperson_name: "Rigby",
    thread: null,
    provider: "runway",
    provider_session_id: "prov-sess-1",
    provider_session_key: "prov-key-secret",
    provider_document_id: "doc-1",
    knowledge_chunk_ids: [],
    status: "draft" as const,
    error_message: "",
    started_at: null,
    ready_at: null,
    ended_at: null,
    expires_at: null,
    cost_estimate_micros: 0,
    cost_actual_micros: 0,
    duration_seconds: 0,
    mock_mode: true,
    transcript_asset: null,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
    tool_invocations: [],
  };
}

function mockDispatchResult(overrides: Partial<{
  state: "succeeded" | "failed" | "awaiting_approval" | "queued" | "rejected";
  tool_name: string;
  result: unknown;
  error_message: string;
}> = {}) {
  return {
    state: "succeeded" as const,
    invocation_id: "inv-1",
    tool_name: "consult_engine",
    cost_micros: 5_000,
    result: {
      answer: "Bridge answer text.",
      asset_id: "as-bridge-1",
      event: "avatar_says_answer",
    },
    error_message: "",
    reason: "",
    ...overrides,
  };
}

// ---- Mutation stubs -------------------------------------------

const CREATE_SESSION_MUTATE = vi.fn();
const INVOKE_MUTATE = vi.fn();

function idleCreateMutation() {
  return {
    mutateAsync: CREATE_SESSION_MUTATE,
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    data: undefined,
    error: null,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useCreateRealtimeSession>;
}

function idleInvokeMutation() {
  return {
    mutateAsync: INVOKE_MUTATE,
    mutate: vi.fn(),
    isPending: false,
    isError: false,
    isSuccess: false,
    data: undefined,
    error: null,
    reset: vi.fn(),
  } as unknown as ReturnType<typeof useInvokeTool>;
}

// ---- Harness --------------------------------------------------

function renderRoute() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={["/workspace/tools"]}>
        <Routes>
          <Route path="/workspace/tools" element={<WorkspaceToolsRoute />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  CREATE_SESSION_MUTATE.mockReset();
  INVOKE_MUTATE.mockReset();

  (useMe as ReturnType<typeof vi.fn>).mockReturnValue({
    data: MOCK_ME,
    isLoading: false,
    isError: false,
  });
  (useSubscription as ReturnType<typeof vi.fn>).mockReturnValue({
    data: mockSubscription("pro"),
    isLoading: false,
    isError: false,
  });
  (useSpokespeople as ReturnType<typeof vi.fn>).mockReturnValue({
    data: [mockSpokesperson("sp-1", "Rigby")],
    isLoading: false,
    isError: false,
  });
  (useCreateRealtimeSession as ReturnType<typeof vi.fn>).mockReturnValue(
    idleCreateMutation(),
  );
  (useInvokeTool as ReturnType<typeof vi.fn>).mockReturnValue(
    idleInvokeMutation(),
  );
});

// ---- Tests ----------------------------------------------------

describe("C5.1 — tier gate + basic render", () => {
  it("renders the form for Pro workspaces", () => {
    renderRoute();
    expect(screen.getByTestId("tools-form")).toBeInTheDocument();
    expect(
      screen.queryByTestId("tools-upgrade-nudge"),
    ).not.toBeInTheDocument();
  });

  it("renders the upgrade nudge (not the form) for Starter workspaces", () => {
    (useSubscription as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockSubscription("starter"),
      isLoading: false,
      isError: false,
    });
    renderRoute();
    expect(screen.getByTestId("tools-upgrade-nudge")).toBeInTheDocument();
    expect(screen.queryByTestId("tools-form")).not.toBeInTheDocument();
  });

  it("renders the form for Agency workspaces (tier ≥ Pro)", () => {
    (useSubscription as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockSubscription("agency"),
      isLoading: false,
      isError: false,
    });
    renderRoute();
    expect(screen.getByTestId("tools-form")).toBeInTheDocument();
  });

  it("shows a loading state while `me`/`subscription`/`spokespeople` are in flight", () => {
    (useSpokespeople as ReturnType<typeof vi.fn>).mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
    });
    renderRoute();
    expect(screen.getByTestId("tools-loading")).toBeInTheDocument();
    expect(screen.queryByTestId("tools-form")).not.toBeInTheDocument();
  });
});

describe("C5.1 — tool picker (partial P3 4.4 tier+cost surfacing)", () => {
  it("populates the tool picker with the v1 bridge tool (consult_engine only)", () => {
    // F-10-C — `query_spider_data` and `agent_consult` are backend-
    // registered but excluded from the v1 SPA picker until the per-
    // tool form renderer (candidate C6) can send their required args
    // (`topic` / `agent_name`). This assertion pins the v1 shape so
    // a future re-enable is a deliberate multi-file change (tools.ts
    // + this test + scope-lock doc rule 4).
    renderRoute();
    const picker = screen.getByTestId("tools-tool-picker") as HTMLSelectElement;
    const values = Array.from(picker.options).map((o) => o.value);
    expect(values).toEqual(["consult_engine"]);
  });

  it("renders tier + cost hints inline on the option label", () => {
    renderRoute();
    const picker = screen.getByTestId("tools-tool-picker") as HTMLSelectElement;
    const labels = Array.from(picker.options).map((o) => o.textContent);
    // Every visible option surfaces tier + cost — partial P3 4.4 coverage.
    for (const label of labels) {
      expect(label).toMatch(/Pro/);
      expect(label).toMatch(/\$0\./);
    }
    // consult_engine is $0.005; explicitly assert so a future rate
    // change (or a new tool sneaking in ahead of the picker itself)
    // fails here rather than silently at dispatch.
    expect(labels[0]).toContain("$0.005");
  });
});

describe("C5.1 — spokesperson picker", () => {
  it("populates the spokesperson picker from the workspace", () => {
    (useSpokespeople as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [
        mockSpokesperson("sp-1", "Rigby"),
        mockSpokesperson("sp-2", "Sasha"),
        // Cross-workspace spokesperson MUST be filtered out (matches
        // /workspace/scripts.new behavior).
        mockSpokesperson("sp-3", "Not-mine", "ws-other"),
      ],
      isLoading: false,
      isError: false,
    });
    renderRoute();
    const picker = screen.getByTestId(
      "tools-spokesperson-picker",
    ) as HTMLSelectElement;
    const values = Array.from(picker.options).map((o) => o.value);
    expect(values).toEqual(["sp-1", "sp-2"]);
    expect(values).not.toContain("sp-3");
  });
});

describe("C5.1 — submit gating", () => {
  it("disables the submit button while the question textarea is empty", () => {
    renderRoute();
    const submit = screen.getByTestId("tools-submit");
    expect(submit).toBeDisabled();
  });

  it("enables the submit button once a question is typed", async () => {
    const user = userEvent.setup();
    renderRoute();
    const submit = screen.getByTestId("tools-submit");
    const question = screen.getByTestId("tools-question");
    await user.type(question, "hello");
    expect(submit).not.toBeDisabled();
  });
});

describe("C5.1 — dispatch + DRAFT session reuse (rules 2, 3, 5)", () => {
  it("creates a DRAFT session then invokes the tool on first submit", async () => {
    CREATE_SESSION_MUTATE.mockResolvedValue(mockSessionWithKey("rt-1"));
    INVOKE_MUTATE.mockResolvedValue(mockDispatchResult());
    (useCreateRealtimeSession as ReturnType<typeof vi.fn>).mockReturnValue(
      idleCreateMutation(),
    );
    (useInvokeTool as ReturnType<typeof vi.fn>).mockReturnValue(
      idleInvokeMutation(),
    );

    const user = userEvent.setup();
    renderRoute();

    await user.type(
      screen.getByTestId("tools-question"),
      "What is the total?",
    );
    await user.click(screen.getByTestId("tools-submit"));

    await waitFor(() => {
      expect(CREATE_SESSION_MUTATE).toHaveBeenCalledTimes(1);
    });
    // F-09 fix — `draft_only: true` is load-bearing. Without it the
    // backend endpoint calls MediaEngineClient and starts a real
    // Runway session ($0.14+ spend per form submit), which violates
    // BRIDGE_TOOLS_UI_V1.md rule 2. Assert the SPA sends it so any
    // future refactor that drops the flag fails here rather than in
    // production dogfood.
    expect(CREATE_SESSION_MUTATE).toHaveBeenCalledWith({
      spokesperson: "sp-1",
      title: "Bridge tool session",
      draft_only: true,
    });
    expect(INVOKE_MUTATE).toHaveBeenCalledTimes(1);
    expect(INVOKE_MUTATE).toHaveBeenCalledWith({
      sessionId: "rt-1",
      tool_name: "consult_engine",
      args: { question: "What is the total?" },
    });
  });

  it("reuses the DRAFT session on a second dispatch (no re-create)", async () => {
    CREATE_SESSION_MUTATE.mockResolvedValue(mockSessionWithKey("rt-1"));
    INVOKE_MUTATE.mockResolvedValue(mockDispatchResult());

    const user = userEvent.setup();
    renderRoute();

    await user.type(screen.getByTestId("tools-question"), "first");
    await user.click(screen.getByTestId("tools-submit"));
    await waitFor(() => expect(INVOKE_MUTATE).toHaveBeenCalledTimes(1));

    // Clear the question and fire again — same spokesperson.
    await user.clear(screen.getByTestId("tools-question"));
    await user.type(screen.getByTestId("tools-question"), "second");
    await user.click(screen.getByTestId("tools-submit"));

    await waitFor(() => expect(INVOKE_MUTATE).toHaveBeenCalledTimes(2));
    // Rule 5 — DRAFT was created ONCE across two dispatches.
    expect(CREATE_SESSION_MUTATE).toHaveBeenCalledTimes(1);
    // Both dispatches used the same session id.
    expect(INVOKE_MUTATE.mock.calls[0]?.[0]?.sessionId).toBe("rt-1");
    expect(INVOKE_MUTATE.mock.calls[1]?.[0]?.sessionId).toBe("rt-1");
    // Rule 2 evidence — the "reusing session" badge surfaces to make
    // the invariant visible in the UI too.
    expect(
      screen.getByTestId("tools-session-reuse-badge"),
    ).toBeInTheDocument();
  });
});

describe("C5.1 — result + error surfacing", () => {
  it("renders the answer text on a succeeded dispatch", async () => {
    CREATE_SESSION_MUTATE.mockResolvedValue(mockSessionWithKey("rt-1"));
    INVOKE_MUTATE.mockResolvedValue(
      mockDispatchResult({
        result: {
          answer: "Forty-two.",
          asset_id: "as-1",
          event: "avatar_says_answer",
        },
      }),
    );

    const user = userEvent.setup();
    renderRoute();

    await user.type(screen.getByTestId("tools-question"), "the meaning?");
    await user.click(screen.getByTestId("tools-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("tools-result-answer")).toHaveTextContent(
        "Forty-two.",
      );
    });
    expect(screen.getByTestId("tools-result-asset-link")).toHaveAttribute(
      "href",
      "/workspace/assets/as-1",
    );
  });

  it("surfaces error_message when the dispatch state is `failed`", async () => {
    CREATE_SESSION_MUTATE.mockResolvedValue(mockSessionWithKey("rt-1"));
    INVOKE_MUTATE.mockResolvedValue(
      mockDispatchResult({
        state: "failed",
        error_message: "Engine not configured for this workspace.",
        result: null,
      }),
    );

    const user = userEvent.setup();
    renderRoute();

    await user.type(screen.getByTestId("tools-question"), "hi");
    await user.click(screen.getByTestId("tools-submit"));

    await waitFor(() => {
      expect(screen.getByTestId("tools-submit-error")).toHaveTextContent(
        "Engine not configured for this workspace.",
      );
    });
    // Failed dispatches must NOT render the answer panel.
    expect(screen.queryByTestId("tools-result-panel")).not.toBeInTheDocument();
  });
});
