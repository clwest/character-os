/**
 * SESSION 277 Slice 8 (Q-277-8) — Universe.brief SPA form coverage.
 *
 * The `/workspace/universes` CreatePanel now exposes a `brief`
 * textarea (optional). Tests:
 *
 * 1. brief field is rendered with helper copy.
 * 2. Slice-5 name-only create still works (brief omitted).
 * 3. When brief is supplied, it round-trips into the mutation payload.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

vi.mock("@/lib/api/workspaces", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/workspaces")>(
    "@/lib/api/workspaces",
  );
  return { ...actual, useMe: vi.fn() };
});

vi.mock("@/lib/api/universes", async () => {
  const actual = await vi.importActual<typeof import("@/lib/api/universes")>(
    "@/lib/api/universes",
  );
  return {
    ...actual,
    useUniverses: vi.fn(),
    useCreateUniverse: vi.fn(),
    useArchiveUniverse: vi.fn(),
  };
});

import { useMe } from "@/lib/api/workspaces";
import {
  useUniverses,
  useCreateUniverse,
  useArchiveUniverse,
} from "@/lib/api/universes";
import { WorkspaceUniversesRoute } from "./universes";

const useMeMock = useMe as unknown as ReturnType<typeof vi.fn>;
const useUniversesMock = useUniverses as unknown as ReturnType<typeof vi.fn>;
const useCreateUniverseMock =
  useCreateUniverse as unknown as ReturnType<typeof vi.fn>;
const useArchiveMock = useArchiveUniverse as unknown as ReturnType<typeof vi.fn>;

function makeMutation<T = unknown>(result: T | null = null, error: unknown = null) {
  return {
    mutateAsync: vi.fn().mockResolvedValue(result),
    isPending: false,
    isError: !!error,
    error,
    reset: vi.fn(),
  };
}

function renderRoute() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  return render(
    <QueryClientProvider client={qc}>
      <MemoryRouter initialEntries={["/workspace/universes"]}>
        <WorkspaceUniversesRoute />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

beforeEach(() => {
  useMeMock.mockReset();
  useUniversesMock.mockReset();
  useCreateUniverseMock.mockReset();
  useArchiveMock.mockReset();

  useMeMock.mockReturnValue({
    data: {
      id: 1,
      email: "chris@donkeybetz.com",
      is_staff: false,
      default_workspace: {
        id: "ws_1",
        name: "Chris's workspace",
        slug: "chriss-workspace",
        role: "owner",
      },
    },
    isLoading: false,
    error: null,
  });
  useUniversesMock.mockReturnValue({ data: [], isLoading: false, error: null });
  useArchiveMock.mockReturnValue(makeMutation());
});


describe("Universe create panel — SESSION 277 Slice 8 brief", () => {
  it("renders the brief textarea with the helper contract copy", () => {
    useCreateUniverseMock.mockReturnValue(makeMutation());
    renderRoute();
    const brief = screen.getByTestId("universe-brief") as HTMLTextAreaElement;
    expect(brief).toBeTruthy();
    expect(brief.maxLength).toBe(2000);
    // Helper copy explains the contract (identity, not policies/pricing).
    expect(
      screen.getByText(
        /Keep detailed facts, pricing, policies, menus, and procedures in Knowledge/i,
      ),
    ).toBeTruthy();
  });

  it("Slice-5 name-only create still works (brief omitted from payload)", async () => {
    const create = makeMutation({ id: "u_new", name: "Nameless" });
    useCreateUniverseMock.mockReturnValue(create);

    const user = userEvent.setup();
    renderRoute();
    await user.type(screen.getByTestId("universe-name"), "Nameless");
    await user.click(screen.getByTestId("universe-create-submit"));

    await waitFor(() => expect(create.mutateAsync).toHaveBeenCalledTimes(1));
    const payload = create.mutateAsync.mock.calls[0]![0] as {
      workspace: string;
      name: string;
      brief?: string;
    };
    expect(payload.workspace).toBe("ws_1");
    expect(payload.name).toBe("Nameless");
    expect(payload.brief).toBeUndefined();
  });

  it("passes brief in the CREATE payload when the operator types one", async () => {
    const create = makeMutation({ id: "u_brief", name: "Fox & Flour" });
    useCreateUniverseMock.mockReturnValue(create);

    const user = userEvent.setup();
    renderRoute();
    await user.type(screen.getByTestId("universe-name"), "Fox & Flour");
    await user.type(
      screen.getByTestId("universe-brief"),
      "A warm neighborhood artisan bakery.",
    );
    await user.click(screen.getByTestId("universe-create-submit"));

    await waitFor(() => expect(create.mutateAsync).toHaveBeenCalledTimes(1));
    const payload = create.mutateAsync.mock.calls[0]![0] as {
      workspace: string;
      name: string;
      brief?: string;
    };
    expect(payload.brief).toBe("A warm neighborhood artisan bakery.");
  });
});
