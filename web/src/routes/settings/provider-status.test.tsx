/**
 * /settings/provider-status vitest coverage — P1 slice 2.3.
 *
 * Enforces the truthfulness invariants documented in
 * `docs/production-readiness/REAL_MODE_PROVIDER_RUNBOOK.md` §2.4
 * on the SPA side:
 *
 *   media-engine reachability != provider configuration
 *     != provider selection != provider reachability
 *       != completed product journey
 *
 * All API hooks are mocked at the module boundary so the tests
 * exercise the component tree without real fetches.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
}));

vi.mock("@/lib/api/provider-health", async (importActual) => {
  const actual =
    await importActual<typeof import("@/lib/api/provider-health")>();
  return {
    ...actual,
    useProviderReport: vi.fn(),
  };
});

import { useMe } from "@/lib/api/workspaces";
import { useProviderReport } from "@/lib/api/provider-health";
import type { ProviderReport } from "@/lib/api/provider-health";
import { ProviderStatusRoute } from "./provider-status";
import { ApiError } from "@/lib/api/client";

const WORKSPACE_ID = "ws-00000000-0000-0000-0000-000000000001";

function renderRoute() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={["/settings/provider-status"]}>
        <Routes>
          <Route
            path="/settings/provider-status"
            element={<ProviderStatusRoute />}
          />
          <Route path="/sign-in" element={<div>Sign-in page</div>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

// -------- fixture builders --------

function mockReport(overrides: Partial<ProviderReport> = {}): ProviderReport {
  const nullReach = {
    configured: false as boolean,
    mode: "mock" as const,
    reachable: null,
    source: "media_engine_health" as const,
    detail: "media-engine reachable; provider configuration observed; provider not probed",
  };
  return {
    status: "ok",
    generated_at: "2026-07-22T03:14:17.537280Z",
    media_engine: { reachable: true, detail: null },
    providers: {
      runway: { ...nullReach },
      image_gen: {
        ...nullReach,
        detail:
          "media-engine reachable; provider configuration observed; provider not probed; derives from runway_mock; independent split queued (P1 2.2 follow-up)",
      },
      llm_provider: {
        configured: true,
        mode: "real",
        reachable: null,
        source: "media_engine_health",
        detail:
          "media-engine reachable; provider configuration observed; provider not probed; provider=openai model='gpt-4o-mini'",
      },
      realtime: { ...nullReach },
      openai_shell: {
        configured: false,
        mode: "unavailable",
        reachable: null,
        source: "shell_env",
        detail:
          "OPENAI_API_KEY unset; not all shell force-mock flags are on ...",
      },
      stability: {
        configured: false,
        mode: "mock",
        reachable: null,
        source: "shell_env",
        detail: "not surfaced on /health; shell reads root .env directly",
      },
      elevenlabs: {
        configured: false,
        mode: "mock",
        reachable: null,
        source: "shell_env",
        detail: "default_provider='auto'; auto chain: runway -> elevenlabs -> mock",
      },
      serper: {
        configured: false,
        mode: "unavailable",
        reachable: null,
        source: "shell_env",
        detail: "SERPER_API_KEY unset and SERPER_FORCE_MOCK not set ...",
      },
      engine_bridge: {
        configured: false,
        mode: "unavailable",
        reachable: null,
        source: "none",
        detail: "workspace not specified; env fallback absent",
      },
      // SESSION 224 F-07 — celery worker liveness. Fixture defaults
      // to "healthy" (1 worker responding) so the majority of tests
      // pass without per-case celery setup; individual tests that
      // want to exercise the dead-worker degrade override this row.
      celery_worker: {
        configured: true,
        mode: "real",
        reachable: true,
        source: "shell_env",
        detail: "1 worker(s) responding: celery@testhost",
      },
    },
    ...overrides,
  };
}

function setReport(state: {
  data?: ProviderReport;
  isPending?: boolean;
  isFetching?: boolean;
  error?: unknown;
  refetch?: () => void;
}) {
  vi.mocked(useProviderReport).mockReturnValue({
    data: state.data,
    isPending: state.isPending ?? false,
    isFetching: state.isFetching ?? false,
    error: state.error ?? null,
    refetch: state.refetch ?? vi.fn(),
  } as unknown as ReturnType<typeof useProviderReport>);
}

// -------- shared setup --------

beforeEach(() => {
  vi.mocked(useMe).mockReturnValue({
    data: {
      id: 1,
      email: "op@example.com",
      is_staff: false,
      default_workspace: {
        id: WORKSPACE_ID,
        name: "Studio",
        slug: "studio",
        role: "owner",
      },
    },
  } as unknown as ReturnType<typeof useMe>);
});

// -------- tests --------

describe("ProviderStatusRoute", () => {
  it("renders the loading state before data arrives", () => {
    setReport({ isPending: true });
    renderRoute();
    expect(screen.getByTestId("provider-status-loading")).toBeInTheDocument();
  });

  it("renders every provider row from the all-mock report", () => {
    setReport({ data: mockReport() });
    renderRoute();
    const list = screen.getByTestId("provider-list");
    const names = [
      "runway",
      "image_gen",
      "llm_provider",
      "realtime",
      "openai_shell",
      "stability",
      "elevenlabs",
      "serper",
      "engine_bridge",
      "celery_worker",
    ];
    for (const name of names) {
      expect(within(list).getByTestId(`provider-row-${name}`)).toBeInTheDocument();
    }
  });

  it("shows 'Real mode selected' + 'Not probed' for a real-selected-but-unprobed row", () => {
    setReport({ data: mockReport() });
    renderRoute();
    const llm = screen.getByTestId("provider-row-llm_provider");
    expect(within(llm).getByTestId("mode-llm_provider")).toHaveTextContent(
      "Real mode selected",
    );
    // reachable=null renders as "Not probed" — never "Unavailable/Offline/Failed".
    expect(within(llm).getByTestId("reachable-null")).toHaveTextContent(
      "Not probed",
    );
    expect(within(llm).getByTestId("reachable-null-hint-llm_provider")).toBeInTheDocument();
  });

  it("renders a degraded, partial report when media-engine is unreachable", () => {
    setReport({
      data: mockReport({
        status: "degraded",
        media_engine: {
          reachable: false,
          detail: "connection refused",
        },
        providers: {
          ...mockReport().providers,
          runway: {
            configured: false,
            mode: "unknown",
            reachable: null,
            source: "none",
            detail: "media-engine unreachable",
          },
          serper: {
            configured: true,
            mode: "real",
            reachable: null,
            source: "shell_env",
            detail: null,
          },
        },
      }),
    });
    renderRoute();
    // Report is still rendered — not replaced by an error page.
    expect(screen.getByTestId("provider-status-report")).toBeInTheDocument();
    expect(screen.getByTestId("top-status-degraded")).toBeInTheDocument();
    expect(screen.getByTestId("media-engine-block")).toHaveTextContent(
      "Media engine unavailable — showing partial status",
    );
    // Shell-side rows remain truthful under partial state.
    expect(
      within(screen.getByTestId("provider-row-serper")).getByTestId("mode-serper"),
    ).toHaveTextContent("Real mode selected");
    // Media-engine-derived row falls back to unknown.
    expect(
      within(screen.getByTestId("provider-row-runway")).getByTestId("mode-runway"),
    ).toHaveTextContent("Mode unknown");
  });

  it("displays reachable=null as 'Not probed' for every provider row (no overclaims)", () => {
    setReport({ data: mockReport() });
    renderRoute();
    const list = screen.getByTestId("provider-list");
    // All 9 provider rows carry the 'Not probed' badge in v1.
    const badges = within(list).getAllByTestId("reachable-null");
    expect(badges).toHaveLength(9);
    for (const badge of badges) {
      expect(badge).toHaveTextContent("Not probed");
    }
  });

  it("copy never implies successful provider contact", () => {
    setReport({ data: mockReport() });
    renderRoute();
    const body = document.body.textContent ?? "";
    // Forbidden phrasings — would overclaim provider readiness.
    const forbidden = [
      "provider is online",
      "provider is available",
      "provider is ready",
      "provider is healthy",
      "successfully contacted",
      "fully configured",
      "ready to use",
    ];
    for (const phrase of forbidden) {
      expect(body.toLowerCase()).not.toContain(phrase);
    }
  });

  it("labels engine_bridge source truthfully — workspace-scoped label when workspace is present", () => {
    setReport({
      data: mockReport({
        providers: {
          ...mockReport().providers,
          engine_bridge: {
            configured: true,
            mode: "real",
            reachable: null,
            source: "engine_connection_row",
            detail: "resolver dry-run only; test_ping NOT invoked",
          },
        },
      }),
    });
    renderRoute();
    expect(screen.getByTestId("workspace-context")).toHaveTextContent(
      /Engine-bridge row scoped to workspace/,
    );
    expect(
      within(screen.getByTestId("provider-row-engine_bridge")).getByTestId(
        "source-engine_bridge",
      ),
    ).toHaveTextContent("Per-workspace EngineConnection row");
  });

  it("labels engine_bridge as environment fallback when workspace context is missing", () => {
    // Override useMe: no default workspace.
    vi.mocked(useMe).mockReturnValue({
      data: {
        id: 2,
        email: "no-ws@example.com",
        is_staff: false,
        default_workspace: null,
      },
    } as unknown as ReturnType<typeof useMe>);
    setReport({
      data: mockReport({
        providers: {
          ...mockReport().providers,
          engine_bridge: {
            configured: true,
            mode: "real",
            reachable: null,
            source: "env_fallback",
            detail: "workspace not specified; reporting env-fallback state only",
          },
        },
      }),
    });
    renderRoute();
    expect(screen.getByTestId("workspace-context")).toHaveTextContent(
      /environment fallback only/,
    );
    expect(
      within(screen.getByTestId("provider-row-engine_bridge")).getByTestId(
        "source-engine_bridge",
      ),
    ).toHaveTextContent("Environment fallback");
  });

  it("clicking 'Refresh status' fires refetch", async () => {
    const refetch = vi.fn();
    setReport({ data: mockReport(), refetch });
    renderRoute();
    const button = screen.getByTestId("refresh-button");
    await userEvent.click(button);
    expect(refetch).toHaveBeenCalledTimes(1);
  });

  it("renders auth-gate on ApiError(401)", () => {
    setReport({ error: new ApiError("GET /api/health/providers/ → 401", 401, null) });
    renderRoute();
    expect(screen.getByTestId("provider-status-auth-gate")).toHaveTextContent(
      /Sign in required/,
    );
  });

  it("renders generic error panel on network failure with Retry", async () => {
    const refetch = vi.fn();
    setReport({ error: new Error("Failed to fetch"), refetch });
    renderRoute();
    const panel = screen.getByTestId("provider-status-error");
    expect(panel).toBeInTheDocument();
    const retry = within(panel).getByRole("button", { name: /Refresh status/i });
    await userEvent.click(retry);
    expect(refetch).toHaveBeenCalledTimes(1);
    // Degraded provider state is NOT implied by this failure path.
    expect(panel).toHaveTextContent(/does not mean any provider is down/i);
  });

  it("renders all 10 provider rows stably (SPA-side contract)", () => {
    // SESSION 224 F-07 grew this from 9 → 10 with celery_worker.
    setReport({ data: mockReport() });
    renderRoute();
    const list = screen.getByTestId("provider-list");
    expect(within(list).getAllByRole("region", { hidden: false })).toHaveLength(10);
  });
});
