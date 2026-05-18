/**
 * R8.0 TalkRoute unit tests.
 *
 * Mocks the API client + SDK so the lifecycle assertions
 * run hermetically. Mock-mode UX is the focus — production
 * SDK behavior is tested live at session-create time.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { TalkRoute } from "./talk";

// Mock the SDK before the route imports it. We don't render
// real WebRTC; the route's mock_mode branch skips the SDK
// mount anyway. This stub keeps the unit test path free of
// LiveKit / livekit-client imports that would otherwise
// pull in a worker.
//
// The stub honors children + onError so R8.2's AvatarSessionInner
// render path + WebRTC-fallback path can be exercised in
// unit tests without a real WebRTC connection.
vi.mock("@runwayml/avatars-react", () => ({
  AvatarCall: ({
    children,
    onError: _onError,
  }: {
    children?: React.ReactNode;
    onError?: (err: Error) => void;
  }) => <div data-testid="avatar-call-stub">{children}</div>,
  AvatarVideo: () => <div data-testid="avatar-video-stub" />,
  useClientEvents: () => undefined,
}));

// Mock the API client surface used by the route.
vi.mock("@/lib/api/spokespeople", () => ({
  useSpokesperson: vi.fn(),
}));
vi.mock("@/lib/api/realtime", () => ({
  useCreateRealtimeSession: vi.fn(),
  useEndRealtimeSession: vi.fn(),
  useRealtimeSession: vi.fn(),
  useInvokeTool: vi.fn(),
  useApproveInvocation: vi.fn(),
  useRejectInvocation: vi.fn(),
  useRealtimeCostEstimate: vi.fn(),
}));

import { useSpokesperson } from "@/lib/api/spokespeople";
import {
  useApproveInvocation,
  useCreateRealtimeSession,
  useEndRealtimeSession,
  useInvokeTool,
  useRealtimeCostEstimate,
  useRealtimeSession,
  useRejectInvocation,
} from "@/lib/api/realtime";

const useSpokespersonMock = useSpokesperson as unknown as ReturnType<typeof vi.fn>;
const useCreateMock = useCreateRealtimeSession as unknown as ReturnType<typeof vi.fn>;
const useEndMock = useEndRealtimeSession as unknown as ReturnType<typeof vi.fn>;
const useGetMock = useRealtimeSession as unknown as ReturnType<typeof vi.fn>;
const useInvokeMock = useInvokeTool as unknown as ReturnType<typeof vi.fn>;
const useApproveMock = useApproveInvocation as unknown as ReturnType<typeof vi.fn>;
const useRejectMock = useRejectInvocation as unknown as ReturnType<typeof vi.fn>;
const useCostMock = useRealtimeCostEstimate as unknown as ReturnType<typeof vi.fn>;

function makeSpokesperson(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "sp_1",
    workspace: "ws_1",
    name: "Sasha",
    business_brief: "Sells bicycle bells.",
    tone_archetype: "expert",
    visual_subject: "",
    runway_avatar_id: "av_1",
    voice_id: "voice_1",
    portrait_path: "https://fake/p.png",
    created_at: "2026-05-01T00:00:00Z",
    updated_at: "2026-05-01T00:00:00Z",
    ...overrides,
  };
}

function makeSession(overrides: Partial<Record<string, unknown>> = {}) {
  return {
    id: "rt_1",
    workspace: "ws_1",
    spokesperson: "sp_1",
    spokesperson_name: "Sasha",
    thread: null,
    provider: "runway",
    provider_session_id: "rt_provider_1",
    provider_document_id: "doc_1",
    knowledge_chunk_ids: ["c1", "c2"],
    status: "ready",
    error_message: "",
    started_at: "2026-05-15T10:00:00Z",
    ready_at: "2026-05-15T10:00:01Z",
    ended_at: null,
    expires_at: null,
    cost_estimate_micros: 0,
    cost_actual_micros: 0,
    duration_seconds: 0,
    mock_mode: true,
    transcript_asset: null,
    created_at: "2026-05-15T10:00:00Z",
    updated_at: "2026-05-15T10:00:01Z",
    tool_invocations: [],
    ...overrides,
  };
}

function renderRoute() {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/spokespeople/sp_1/talk"]}>
        <Routes>
          <Route path="/spokespeople/:id/talk" element={<TalkRoute />} />
          <Route path="/spokespeople/:id" element={<div>back-target</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

describe("TalkRoute (R8.0)", () => {
  beforeEach(() => {
    useSpokespersonMock.mockReturnValue({
      data: makeSpokesperson(),
      isLoading: false,
      isError: false,
      error: null,
    });
    useGetMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    });
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    useEndMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    useInvokeMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    useApproveMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    useRejectMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    useCostMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: false,
    });
  });

  it("renders idle state with Start button", () => {
    renderRoute();
    expect(screen.getByTestId("talk-route")).toHaveAttribute(
      "data-lifecycle",
      "idle",
    );
    expect(screen.getByTestId("talk-start")).toBeInTheDocument();
  });

  it("idle panel renders cost forecast pill (R8.1) — fallback constants", () => {
    renderRoute();
    const pill = screen.getByTestId("cost-forecast");
    expect(pill).toBeInTheDocument();
    // 5 min × $0.08/min = $0.40 fallback
    expect(pill).toHaveTextContent("$0.40");
    expect(pill).toHaveTextContent(/for 5 min/i);
    // No tier-cap → no minutes-remaining hint
    expect(screen.queryByTestId("minutes-remaining")).not.toBeInTheDocument();
  });

  it("idle panel uses backend cost estimate when available (R9)", () => {
    useCostMock.mockReturnValue({
      data: {
        provider: "runway",
        cost_per_minute_micros: 100_000, // $0.10/min — different from fallback
        max_session_minutes: 5,
        monthly_minutes_used: 12,
        monthly_minutes_limit: 30,
        monthly_minutes_remaining: 18,
        tier: "starter",
      },
      isLoading: false,
      isError: false,
    });
    renderRoute();
    const pill = screen.getByTestId("cost-forecast");
    // 5 min × $0.10/min = $0.50 (backend-driven)
    expect(pill).toHaveTextContent("$0.50");
    // Minutes-remaining hint renders for capped tiers.
    const hint = screen.getByTestId("minutes-remaining");
    expect(hint).toHaveTextContent("18");
    expect(hint).toHaveTextContent("of 30 min left this month");
  });

  it("idle panel hides minutes-remaining hint for unlimited tier (R9)", () => {
    useCostMock.mockReturnValue({
      data: {
        provider: "runway",
        cost_per_minute_micros: 80_000,
        max_session_minutes: 5,
        monthly_minutes_used: 1000,
        monthly_minutes_limit: null,
        monthly_minutes_remaining: null,
        tier: "agency",
      },
      isLoading: false,
      isError: false,
    });
    renderRoute();
    expect(screen.queryByTestId("minutes-remaining")).not.toBeInTheDocument();
  });

  it("mock-mode session exposes tool dispatch buttons (R8.1)", async () => {
    const mockSession = {
      ...makeSession({ mock_mode: true }),
      provider_session_key: "mock_key",
    };
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockSession),
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await waitFor(() =>
      expect(screen.getByTestId("mock-tool-buttons")).toBeInTheDocument(),
    );
    expect(
      screen.getByTestId("mock-fire-render-video"),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId("mock-fire-show-videos-tab"),
    ).toBeInTheDocument();
  });

  it("firing an over-threshold tool opens the approval modal (R8.1)", async () => {
    const mockSession = {
      ...makeSession({ mock_mode: true }),
      provider_session_key: "mock_key",
    };
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockSession),
      isPending: false,
    });
    const awaitingResult = {
      state: "awaiting_approval" as const,
      invocation_id: "inv_42",
      tool_name: "render_video",
      cost_micros: 80_000,
      reason: "tool cost $0.08 exceeds workspace threshold $0.05",
    };
    useInvokeMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(awaitingResult),
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await userEvent.click(screen.getByTestId("mock-fire-render-video"));
    await waitFor(() =>
      expect(screen.getByTestId("tool-approval-modal")).toBeInTheDocument(),
    );
    expect(screen.getByText(/render a video for you/i)).toBeInTheDocument();
  });

  it("renders cost ticker while live (R8.2)", async () => {
    const mockSession = {
      ...makeSession({
        mock_mode: true,
        ready_at: new Date().toISOString(),
      }),
      provider_session_key: "mock_key",
    };
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockSession),
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await waitFor(() =>
      expect(screen.getByTestId("cost-ticker")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("cost-ticker")).toHaveTextContent(/demo/i);
  });

  it("renders WebRTC fallback CTA when error panel shows (R8.2)", async () => {
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(new Error("network issue")),
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await waitFor(() =>
      expect(screen.getByTestId("talk-error")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("talk-fallback")).toBeInTheDocument();
    expect(screen.getByTestId("talk-retry")).toBeInTheDocument();
  });

  it("firing an under-threshold tool surfaces success in tool-result panel (R8.1)", async () => {
    const mockSession = {
      ...makeSession({ mock_mode: true }),
      provider_session_key: "mock_key",
    };
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockSession),
      isPending: false,
    });
    const succeededResult = {
      state: "succeeded" as const,
      invocation_id: "inv_43",
      tool_name: "show_videos_tab",
      cost_micros: 0,
      result: { event: "show_videos_tab", spokesperson_id: "sp_1" },
    };
    useInvokeMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(succeededResult),
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await userEvent.click(screen.getByTestId("mock-fire-show-videos-tab"));
    await waitFor(() =>
      expect(screen.getByTestId("tool-result-panel")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("tool-result-panel")).toHaveAttribute(
      "data-state",
      "succeeded",
    );
    // Modal should NOT have opened.
    expect(
      screen.queryByTestId("tool-approval-modal"),
    ).not.toBeInTheDocument();
  });

  it("transitions to live with mock-mode pill after Start", async () => {
    const mockSession = {
      ...makeSession({ mock_mode: true }),
      provider_session_key: "mock_key",
    };
    const mutateAsync = vi.fn().mockResolvedValue(mockSession);
    useCreateMock.mockReturnValue({
      mutateAsync,
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await waitFor(() =>
      expect(screen.getByTestId("talk-route")).toHaveAttribute(
        "data-lifecycle",
        "ready",
      ),
    );
    // Mock-mode UX: skips the SDK mount, shows the mock panel.
    expect(screen.getByTestId("live-pill-mock")).toBeInTheDocument();
    expect(screen.getByTestId("mock-session-panel")).toBeInTheDocument();
    expect(screen.queryByTestId("avatar-call-stub")).not.toBeInTheDocument();
    // create was called with the spokesperson id.
    expect(mutateAsync).toHaveBeenCalledWith({ spokesperson: "sp_1" });
  });

  it("mounts the SDK in real (non-mock) mode", async () => {
    const realSession = {
      ...makeSession({ mock_mode: false }),
      provider_session_key: "real_key",
    };
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(realSession),
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await waitFor(() =>
      expect(screen.getByTestId("avatar-call-stub")).toBeInTheDocument(),
    );
    expect(screen.getByTestId("live-pill-real")).toBeInTheDocument();
    expect(screen.queryByTestId("mock-session-panel")).not.toBeInTheDocument();
  });

  it("transitions to ended after End", async () => {
    const mockSession = {
      ...makeSession({ mock_mode: true }),
      provider_session_key: "mock_key",
    };
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(mockSession),
      isPending: false,
    });
    const endedSession = makeSession({
      status: "ended",
      duration_seconds: 12,
      mock_mode: true,
    });
    useEndMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(endedSession),
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await waitFor(() =>
      expect(screen.getByTestId("talk-end")).toBeInTheDocument(),
    );
    await userEvent.click(screen.getByTestId("talk-end"));
    await waitFor(() =>
      expect(screen.getByTestId("talk-route")).toHaveAttribute(
        "data-lifecycle",
        "ended",
      ),
    );
    expect(screen.getByTestId("talk-ended")).toBeInTheDocument();
    expect(screen.getByText(/12s/)).toBeInTheDocument();
  });

  it("shows error panel when create fails", async () => {
    useCreateMock.mockReturnValue({
      mutateAsync: vi.fn().mockRejectedValue(new Error("backend down")),
      isPending: false,
    });
    renderRoute();
    await userEvent.click(screen.getByTestId("talk-start"));
    await waitFor(() =>
      expect(screen.getByTestId("talk-error")).toBeInTheDocument(),
    );
    expect(screen.getByText(/backend down/)).toBeInTheDocument();
  });

  it("renders skeleton while spokesperson loads", () => {
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      error: null,
    });
    renderRoute();
    expect(screen.getByTestId("talk-skeleton")).toBeInTheDocument();
  });

  it("renders fatal error when spokesperson 404s", () => {
    useSpokespersonMock.mockReturnValue({
      data: undefined,
      isLoading: false,
      isError: true,
      error: new Error("Spokesperson not found."),
    });
    renderRoute();
    expect(screen.getByTestId("talk-fatal-error")).toBeInTheDocument();
  });
});
