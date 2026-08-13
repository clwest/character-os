/**
 * fixture.tsx vitest — §19 Step 9.b.3b canonical materialization
 * tile + admit-fixture-identity control.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";

vi.mock("@/lib/api/bootstrap-review", async (importActual) => {
  const actual =
    await importActual<typeof import("@/lib/api/bootstrap-review")>();
  return {
    ...actual,
    useBootstrapFixture: vi.fn(),
    useApproveFixtureVersion: vi.fn(),
  };
});

import {
  useApproveFixtureVersion,
  useBootstrapFixture,
  type FixtureSummary,
} from "@/lib/api/bootstrap-review";
import { BootstrapReviewFixtureRoute } from "./fixture";

const FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f";

function mockFixture(overrides: Partial<FixtureSummary> = {}): FixtureSummary {
  return {
    run_id: FROZEN_RUN_ID,
    fixture_id: "fixture_h1",
    purposes: [
      {
        reference_kind: "portrait_reference",
        reference_purpose: "front",
        reviewable_candidate_count: 6,
        unsupported_evidence_count: 14,
        review_status: "unreviewed",
        current_decision: null,
      },
      {
        reference_kind: "portrait_reference",
        reference_purpose: "slight_left",
        reviewable_candidate_count: 6,
        unsupported_evidence_count: 14,
        review_status: "unreviewed",
        current_decision: null,
      },
      {
        reference_kind: "portrait_reference",
        reference_purpose: "slight_right",
        reviewable_candidate_count: 6,
        unsupported_evidence_count: 14,
        review_status: "unreviewed",
        current_decision: null,
      },
      {
        reference_kind: "portrait_reference",
        reference_purpose: "neutral_rest",
        reviewable_candidate_count: 6,
        unsupported_evidence_count: 14,
        review_status: "unreviewed",
        current_decision: null,
      },
      {
        reference_kind: "portrait_reference",
        reference_purpose: "listening",
        reviewable_candidate_count: 6,
        unsupported_evidence_count: 14,
        review_status: "unreviewed",
        current_decision: null,
      },
      {
        reference_kind: "portrait_reference",
        reference_purpose: "consideration",
        reviewable_candidate_count: 6,
        unsupported_evidence_count: 14,
        review_status: "unreviewed",
        current_decision: null,
      },
      {
        reference_kind: "portrait_reference",
        reference_purpose: "gentle_positive",
        reviewable_candidate_count: 6,
        unsupported_evidence_count: 14,
        review_status: "unreviewed",
        current_decision: null,
      },
    ],
    progress: {
      purposes_total: 7,
      purposes_dispositioned: 0,
      review_complete: false,
      approval_floor_pairs: [
        "portrait_reference/front",
        "portrait_reference/neutral_rest",
      ],
      approval_floor_satisfied_pairs: [],
      approval_floor_satisfied: false,
    },
    canonical_materialization: {
      canonical_reference_floor_satisfied: false,
      canonical_version_admitted: false,
      publication_complete: true,
      evidence_integrity: true,
      step10_ready: false,
      failures: ["canonical_reference_floor_unsatisfied"],
    },
    ...overrides,
  };
}

function renderRoute() {
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter
        initialEntries={[
          `/settings/bootstrap-review/${FROZEN_RUN_ID}/fixture_h1`,
        ]}
      >
        <Routes>
          <Route
            path="/settings/bootstrap-review/:runId/:fixtureId"
            element={<BootstrapReviewFixtureRoute />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mockApproveMutate = vi
  .fn()
  .mockResolvedValue({
    character_identity_version_id: "v",
    state: "approved",
    already_approved: false,
  });

beforeEach(() => {
  mockApproveMutate.mockClear();
  vi.mocked(useApproveFixtureVersion).mockReturnValue({
    mutateAsync: mockApproveMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useApproveFixtureVersion>);
  vi.mocked(useBootstrapFixture).mockReturnValue({
    data: mockFixture(),
    isLoading: false,
    isError: false,
    error: null,
  } as ReturnType<typeof useBootstrapFixture>);
});

describe("BootstrapReviewFixtureRoute (9.b.3b)", () => {
  it("renders review progress + canonical materialization tiles", () => {
    renderRoute();
    expect(screen.getByTestId("progress-review-complete")).toBeInTheDocument();
    expect(screen.getByTestId("progress-approval-floor")).toBeInTheDocument();
    expect(screen.getByTestId("canonical-materialization-tile")).toBeInTheDocument();
  });

  it("shows 'Materialization pending' when floor not satisfied", () => {
    renderRoute();
    const tile = screen.getByTestId("canonical-materialization-tile");
    expect(within(tile).getByText(/Materialization pending/i)).toBeInTheDocument();
    expect(tile.getAttribute("data-step10-ready")).toBe("false");
    expect(screen.queryByTestId("admit-fixture-identity")).toBeNull();
  });

  it("shows admit button when floor satisfied but version not yet admitted", () => {
    vi.mocked(useBootstrapFixture).mockReturnValue({
      data: mockFixture({
        canonical_materialization: {
          canonical_reference_floor_satisfied: true,
          canonical_version_admitted: false,
          publication_complete: true,
          evidence_integrity: true,
          step10_ready: false,
          failures: ["canonical_version_not_admitted"],
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapFixture>);
    renderRoute();
    const tile = screen.getByTestId("canonical-materialization-tile");
    // Heading + list-item both contain the text; the heading is
    // uniquely the h2-styled div. Data-attribute check is the load-
    // bearing assertion:
    expect(tile.getAttribute("data-floor-satisfied")).toBe("true");
    expect(tile.getAttribute("data-version-admitted")).toBe("false");
    expect(screen.getByTestId("admit-fixture-identity")).toBeInTheDocument();
  });

  it("admit button invokes approve mutation with runId + fixtureId", async () => {
    const user = userEvent.setup();
    vi.mocked(useBootstrapFixture).mockReturnValue({
      data: mockFixture({
        canonical_materialization: {
          canonical_reference_floor_satisfied: true,
          canonical_version_admitted: false,
          publication_complete: true,
          evidence_integrity: true,
          step10_ready: false,
          failures: ["canonical_version_not_admitted"],
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapFixture>);
    renderRoute();
    await user.click(screen.getByTestId("admit-fixture-identity"));
    expect(mockApproveMutate).toHaveBeenCalledTimes(1);
    const arg = mockApproveMutate.mock.calls[0]![0];
    expect(arg.runId).toBe(FROZEN_RUN_ID);
    expect(arg.fixtureId).toBe("fixture_h1");
  });

  it("shows Ready for Step 10 when everything satisfied + no admit button", () => {
    vi.mocked(useBootstrapFixture).mockReturnValue({
      data: mockFixture({
        canonical_materialization: {
          canonical_reference_floor_satisfied: true,
          canonical_version_admitted: true,
          publication_complete: true,
          evidence_integrity: true,
          step10_ready: true,
          failures: [],
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapFixture>);
    renderRoute();
    const tile = screen.getByTestId("canonical-materialization-tile");
    expect(within(tile).getByText(/Ready for Step 10/i)).toBeInTheDocument();
    expect(tile.getAttribute("data-step10-ready")).toBe("true");
    expect(screen.queryByTestId("admit-fixture-identity")).toBeNull();
  });

  it("has ZERO qualified / benchmark / score vocabulary on the fixture page", () => {
    renderRoute();
    for (const pattern of [/qualified/i, /benchmark/i, /score/i, /ranking/i]) {
      expect(screen.queryByText(pattern)).toBeNull();
    }
  });
});
