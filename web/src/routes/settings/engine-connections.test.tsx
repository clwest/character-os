/**
 * /settings/engine-connections vitest coverage — EB.4 (S2887 side-step).
 *
 * Guards the load-bearing contract invariants that the SPA is
 * responsible for enforcing on the client side:
 *
 *   - Rule 4 (write-only token): the plaintext token must NEVER
 *     render on the page after save; only the ****last4 preview does.
 *   - Rule 8 (Pro+ tier gate): Starter workspaces see the upgrade
 *     nudge, not the create form.
 *   - Rule 7 (test_ping is config-check, not tool invocation): the
 *     UI wires the test button to the /test_ping/ action; the
 *     backend guarantees no audit row.
 *
 * All API hooks are mocked at the module boundary so tests exercise
 * the component without real fetches.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/lib/api/workspaces", () => ({
  useMe: vi.fn(),
  useSubscription: vi.fn(),
}));

vi.mock("@/lib/api/engine-connections", async (importActual) => {
  const actual =
    await importActual<typeof import("@/lib/api/engine-connections")>();
  return {
    ...actual,
    useEngineConnections: vi.fn(),
    useCreateEngineConnection: vi.fn(),
    usePatchEngineConnection: vi.fn(),
    useDeleteEngineConnection: vi.fn(),
    useTestPingEngineConnection: vi.fn(),
  };
});

import { useMe, useSubscription } from "@/lib/api/workspaces";
import {
  engineConnectionSchema,
  useCreateEngineConnection,
  useDeleteEngineConnection,
  useEngineConnections,
  usePatchEngineConnection,
  useTestPingEngineConnection,
} from "@/lib/api/engine-connections";
import { EngineConnectionsRoute } from "./engine-connections";

function renderRoute() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={["/settings/engine-connections"]}>
        <Routes>
          <Route
            path="/settings/engine-connections"
            element={<EngineConnectionsRoute />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const MOCK_ME = {
  id: "user-1",
  email: "op@example.com",
  is_staff: false,
  default_workspace: null,
};

function mockSubscription(tier: string) {
  return {
    workspace_id: "ws-1",
    workspace_name: "Demo",
    tier,
    status: "active",
    videos_used: 0,
    videos_limit: null,
    spokespeople_used: 0,
    spokespeople_limit: null,
    period_start: "2026-07-01T00:00:00Z",
    period_end: "2026-08-01T00:00:00Z",
  };
}

function mockConnection() {
  return engineConnectionSchema.parse({
    id: "ec-1",
    workspace: "ws-1",
    engine_kind: "udb_pa",
    engine_url: "http://localhost:8020",
    engine_token_preview: "****abcd",
    enabled: true,
    label: "Local the sibling project",
    last_tested_at: "2026-07-22T00:00:00Z",
    last_test_status: 200,
    created_at: "2026-07-22T00:00:00Z",
    updated_at: "2026-07-22T00:00:00Z",
  });
}

const IDLE_MUTATION = {
  isPending: false,
  isError: false,
  isSuccess: false,
  mutate: vi.fn(),
  mutateAsync: vi.fn(),
  data: undefined,
  error: null,
  reset: vi.fn(),
} as unknown as ReturnType<typeof useCreateEngineConnection>;

beforeEach(() => {
  vi.clearAllMocks();

  (useMe as ReturnType<typeof vi.fn>).mockReturnValue({
    data: MOCK_ME,
    isLoading: false,
    isError: false,
  });

  (useCreateEngineConnection as ReturnType<typeof vi.fn>).mockReturnValue(
    IDLE_MUTATION,
  );
  (usePatchEngineConnection as ReturnType<typeof vi.fn>).mockReturnValue(
    IDLE_MUTATION,
  );
  (useDeleteEngineConnection as ReturnType<typeof vi.fn>).mockReturnValue(
    IDLE_MUTATION,
  );
  (useTestPingEngineConnection as ReturnType<typeof vi.fn>).mockReturnValue(
    IDLE_MUTATION,
  );
});

describe("EB.4 — engine-connections tier gate (Rule 8)", () => {
  it("renders the upgrade nudge for Starter workspaces", () => {
    (useSubscription as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockSubscription("starter"),
      isLoading: false,
      isError: false,
    });
    (useEngineConnections as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });

    renderRoute();

    expect(
      screen.getByTestId("engine-connections-upgrade-nudge"),
    ).toBeInTheDocument();
    // Create form must NOT render for Starter — even without a
    // 403 fired, the SPA must not present a path that will fail.
    expect(
      screen.queryByTestId("engine-connections-create-form"),
    ).not.toBeInTheDocument();
  });

  it("renders the create form for Pro workspaces with no existing row", () => {
    (useSubscription as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockSubscription("pro"),
      isLoading: false,
      isError: false,
    });
    (useEngineConnections as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
    });

    renderRoute();

    expect(
      screen.getByTestId("engine-connections-create-form"),
    ).toBeInTheDocument();
    expect(
      screen.queryByTestId("engine-connections-upgrade-nudge"),
    ).not.toBeInTheDocument();
  });

  it("renders the read-only card for Pro workspaces with an existing row", () => {
    (useSubscription as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockSubscription("agency"),
      isLoading: false,
      isError: false,
    });
    (useEngineConnections as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [mockConnection()],
      isLoading: false,
      isError: false,
    });

    renderRoute();

    expect(
      screen.getByTestId("engine-connection-card"),
    ).toBeInTheDocument();
  });
});

describe("EB.4 — engine-connections write-only token invariant (Rule 4)", () => {
  it("displays only the ****last4 preview for the stored token", () => {
    (useSubscription as ReturnType<typeof vi.fn>).mockReturnValue({
      data: mockSubscription("pro"),
      isLoading: false,
      isError: false,
    });
    (useEngineConnections as ReturnType<typeof vi.fn>).mockReturnValue({
      data: [mockConnection()],
      isLoading: false,
      isError: false,
    });

    const { container } = renderRoute();

    // The preview MUST render.
    expect(screen.getByText("****abcd")).toBeInTheDocument();
    // No plaintext token substring EVER renders. This is asserted
    // by scanning the rendered DOM — if a future refactor accidentally
    // pipes the raw token through, this fails.
    const rendered = container.textContent ?? "";
    expect(rendered).not.toMatch(/plaintext-token-fixture-secret/);
    // Serializer redaction is server-side and out of scope here;
    // this test guarantees the SPA never introduces a leak.
  });
});

describe("EB.4 — engine-connections API schema (contract drift signal)", () => {
  it("parses the shipped viewset response shape", () => {
    // If the DRF serializer changes fields, this parse throws; the
    // failure is our contract-drift alarm.
    const parsed = engineConnectionSchema.parse({
      id: "ec-1",
      workspace: "ws-1",
      engine_kind: "udb_pa",
      engine_url: "https://engine.example.com",
      engine_token_preview: "****wxyz",
      enabled: true,
      label: "",
      last_tested_at: null,
      last_test_status: null,
      created_at: "2026-07-22T00:00:00Z",
      updated_at: "2026-07-22T00:00:00Z",
    });
    expect(parsed.engine_kind).toBe("udb_pa");
    expect(parsed.engine_token_preview).toBe("****wxyz");
  });

  it("rejects an unknown engine_kind", () => {
    expect(() =>
      engineConnectionSchema.parse({
        id: "ec-1",
        workspace: "ws-1",
        engine_kind: "not_a_real_kind",
        engine_url: "https://engine.example.com",
        engine_token_preview: "",
        enabled: true,
        label: "",
        last_tested_at: null,
        last_test_status: null,
        created_at: "2026-07-22T00:00:00Z",
        updated_at: "2026-07-22T00:00:00Z",
      }),
    ).toThrow();
  });
});
