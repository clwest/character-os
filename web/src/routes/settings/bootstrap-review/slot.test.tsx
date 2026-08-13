/**
 * /settings/bootstrap-review/:runId/:fixtureId/:kind/:purpose vitest
 * — §19 Step 9.b.2 decision controls (SESSION 249).
 *
 * Covers:
 *   - 6 reviewable cards; normalized primary + raw toggle
 *   - Select control + No candidate approved control
 *   - Current-decision banner (unreviewed vs decided)
 *   - Amendment path requires reason
 *   - Decision history expandable
 *   - Provider-declined evidence still rendered factually (grouped)
 *   - Zero promote / approve-version / reject / finalize controls
 *   - Manifest panel expandable
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
    useBootstrapSlot: vi.fn(),
    useCreateDecision: vi.fn(),
    usePromoteSlot: vi.fn(),
  };
});

import {
  useBootstrapSlot,
  useCreateDecision,
  usePromoteSlot,
  type SlotDetail,
} from "@/lib/api/bootstrap-review";
import { BootstrapReviewSlotRoute } from "./slot";

const FROZEN_RUN_ID = "bootstrap_20260808T044853Z_7eb392992e0f";

function buildReviewable(
  direction: "identity_only" | "softened_photographic",
  profile: "compact" | "team_card" | "presence",
) {
  const cell_id = `fixture_h1__portrait_reference__front__${profile}`;
  return {
    frozen_candidate_id: `${FROZEN_RUN_ID}/${direction}/stability_still/${cell_id}`,
    cell_id,
    run_id: FROZEN_RUN_ID,
    fixture_id: "fixture_h1",
    direction_hypothesis: direction,
    provider: "stability_still" as const,
    surface_profile: profile,
    reference_kind: "portrait_reference" as const,
    reference_purpose: "front" as const,
    outcome: "success",
    provider_stage: {
      outcome: "success",
      provider_model: "sd3-large",
      requested_execution_mode: "real_required",
      actual_execution_mode: "real",
      elapsed_ms: 8420,
      error: null,
    },
    normalization_stage: {
      attempted: true,
      outcome: "success",
      pipeline_version: "pipeline_v1:...",
      surface_profile_id: profile,
      surface_profile_version: 1,
      background_id: "neutral_warm_studio",
      failure: null,
    },
    raw_artifact: { byte_count: 1320169, sha256_hex: "a".repeat(64) },
    normalized_artifact: { byte_count: 9775, sha256_hex: "b".repeat(64) },
    manifest_artifact: { byte_count: 6005, sha256_hex: "c".repeat(64) },
    factual_normalization_notices: [],
  };
}

function buildUnsupportedGroup(provider: "runway_still_portrait" | "stability_still", count: number) {
  return {
    provider,
    error_class: "UnsupportedAspectRatioError",
    error_message: `${provider} refusal`,
    count,
    members: Array.from({ length: count }, (_, i) => ({
      frozen_candidate_id: `${FROZEN_RUN_ID}/identity_only/${provider}/member_${i}`,
      direction: "identity_only" as const,
      surface_profile: "compact" as const,
    })),
  };
}

function mockSlotData(overrides: Partial<SlotDetail> = {}): SlotDetail {
  const reviewable = [
    buildReviewable("identity_only", "compact"),
    buildReviewable("identity_only", "team_card"),
    buildReviewable("identity_only", "presence"),
    buildReviewable("softened_photographic", "compact"),
    buildReviewable("softened_photographic", "team_card"),
    buildReviewable("softened_photographic", "presence"),
  ];
  return {
    run_id: FROZEN_RUN_ID,
    fixture_id: "fixture_h1",
    reference_kind: "portrait_reference",
    reference_purpose: "front",
    reviewable_candidates: reviewable,
    unsupported_evidence: [],
    unsupported_summary: [
      buildUnsupportedGroup("runway_still_portrait", 10),
      buildUnsupportedGroup("stability_still", 4),
    ],
    current_decision: null,
    current_promotion: null,
    decision_history: [],
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
          `/settings/bootstrap-review/${FROZEN_RUN_ID}/fixture_h1/portrait_reference/front`,
        ]}
      >
        <Routes>
          <Route
            path="/settings/bootstrap-review/:runId/:fixtureId/:kind/:purpose"
            element={<BootstrapReviewSlotRoute />}
          />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}

const mockMutate = vi.fn().mockResolvedValue({ decision: {}, created: true, review_run_id: "x" });
const mockPromoteMutate = vi
  .fn()
  .mockResolvedValue({
    kind: "selected",
    decision_id: "d",
    promotion_audit_id: "a",
    character_identity_version_id: "v",
    identity_reference_id: "r",
    superseded_identity_reference_id: null,
    slot_revision: 1,
  });

beforeEach(() => {
  mockMutate.mockClear();
  mockPromoteMutate.mockClear();
  vi.mocked(useCreateDecision).mockReturnValue({
    mutateAsync: mockMutate,
    isPending: false,
  } as unknown as ReturnType<typeof useCreateDecision>);
  vi.mocked(usePromoteSlot).mockReturnValue({
    mutateAsync: mockPromoteMutate,
    isPending: false,
  } as unknown as ReturnType<typeof usePromoteSlot>);
  vi.mocked(useBootstrapSlot).mockReturnValue({
    data: mockSlotData(),
    isLoading: false,
    isError: false,
    error: null,
  } as ReturnType<typeof useBootstrapSlot>);
});

describe("BootstrapReviewSlotRoute (9.b.2)", () => {
  it("renders six reviewable candidate cards with distinct frozen_candidate_ids", () => {
    renderRoute();
    const cards = screen.getAllByTestId("candidate-card");
    expect(cards).toHaveLength(6);
    const fcids = cards.map((c) => c.getAttribute("data-fcid"));
    expect(new Set(fcids).size).toBe(6);
  });

  it("current-decision banner reads 'unreviewed' when no decision exists", () => {
    renderRoute();
    const banner = screen.getByTestId("current-decision-banner");
    expect(banner.getAttribute("data-status")).toBe("unreviewed");
  });

  it("renders one Select button per reviewable candidate", () => {
    renderRoute();
    expect(screen.getAllByTestId("select-candidate")).toHaveLength(6);
  });

  it("renders exactly one No-candidate-approved control", () => {
    renderRoute();
    expect(screen.getAllByTestId("no-candidate-submit")).toHaveLength(1);
  });

  it("Select on first decision does NOT require an amendment reason", async () => {
    const user = userEvent.setup();
    renderRoute();
    const firstCard = screen.getAllByTestId("candidate-card")[0]!;
    // No reason textarea when there's no current decision.
    expect(within(firstCard).queryByTestId("select-reason")).toBeNull();
    await user.click(within(firstCard).getByTestId("select-candidate"));
    expect(mockMutate).toHaveBeenCalledTimes(1);
    const arg = mockMutate.mock.calls[0]![0];
    expect(arg.disposition).toBe("selected");
    expect(arg.supersedesDecisionId).toBeNull();
    expect(arg.amendmentReason).toBeNull();
  });

  it("Amend Select requires non-blank reason", async () => {
    const user = userEvent.setup();
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "d1",
          disposition: "no_candidate_approved",
          frozen_candidate_id: null,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    const firstCard = screen.getAllByTestId("candidate-card")[0]!;
    // Reason textarea IS present in amendment mode.
    expect(within(firstCard).getByTestId("select-reason")).toBeInTheDocument();
    // Click without filling reason → no mutation call + error message.
    await user.click(within(firstCard).getByTestId("select-candidate"));
    expect(mockMutate).not.toHaveBeenCalled();
    expect(within(firstCard).getByTestId("select-error")).toHaveTextContent(
      /reason is required/i,
    );
  });

  it("Amend Select with reason invokes mutation with supersedes chain", async () => {
    const user = userEvent.setup();
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "prior-decision-abc",
          disposition: "no_candidate_approved",
          frozen_candidate_id: null,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    const firstCard = screen.getAllByTestId("candidate-card")[0]!;
    await user.type(
      within(firstCard).getByTestId("select-reason"),
      "reconsidered after comparing profiles",
    );
    await user.click(within(firstCard).getByTestId("select-candidate"));
    expect(mockMutate).toHaveBeenCalledTimes(1);
    const arg = mockMutate.mock.calls[0]![0];
    expect(arg.disposition).toBe("selected");
    expect(arg.supersedesDecisionId).toBe("prior-decision-abc");
    expect(arg.amendmentReason).toBe("reconsidered after comparing profiles");
  });

  it("currently-selected card shows 'Currently selected' + is disabled", () => {
    const targetFcid = `${FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact`;
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "d1",
          disposition: "selected",
          frozen_candidate_id: targetFcid,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    const cards = screen.getAllByTestId("candidate-card");
    const selectedCard = cards.find(
      (c) => c.getAttribute("data-fcid") === targetFcid,
    )!;
    const button = within(selectedCard).getByTestId("select-candidate");
    expect(button).toBeDisabled();
    expect(button).toHaveTextContent(/Currently selected/i);
  });

  it("no-candidate first-decision submits without reason", async () => {
    const user = userEvent.setup();
    renderRoute();
    // No reason textarea for first no-candidate decision.
    expect(screen.queryByTestId("no-candidate-reason")).toBeNull();
    await user.click(screen.getByTestId("no-candidate-submit"));
    expect(mockMutate).toHaveBeenCalledTimes(1);
    const arg = mockMutate.mock.calls[0]![0];
    expect(arg.disposition).toBe("no_candidate_approved");
    expect(arg.frozenCandidateId).toBeNull();
    expect(arg.supersedesDecisionId).toBeNull();
    expect(arg.amendmentReason).toBeNull();
  });

  it("no-candidate amendment requires reason", async () => {
    const user = userEvent.setup();
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "prior-abc",
          disposition: "selected",
          frozen_candidate_id: `${FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact`,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    expect(screen.getByTestId("no-candidate-reason")).toBeInTheDocument();
    // Click without reason.
    await user.click(screen.getByTestId("no-candidate-submit"));
    expect(mockMutate).not.toHaveBeenCalled();
    expect(screen.getByTestId("no-candidate-error")).toHaveTextContent(
      /reason is required/i,
    );
  });

  it("decision history section renders when history exists", () => {
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        decision_history: [
          {
            decision_id: "r1",
            disposition: "no_candidate_approved",
            frozen_candidate_id: null,
            supersedes_decision_id: null,
            amendment_reason: null,
            reviewer_user_id: 42,
            reviewer_email_at_write_time: "chris@example.test",
            decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
          },
          {
            decision_id: "r2",
            disposition: "selected",
            frozen_candidate_id: `${FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact`,
            supersedes_decision_id: "r1",
            amendment_reason: "reconsidered",
            reviewer_user_id: 42,
            reviewer_email_at_write_time: "chris@example.test",
            decided_at_utc: "2026-08-08T11:00:00.000000+00:00",
          },
        ],
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    expect(screen.getByTestId("history-toggle")).toHaveTextContent(
      /Decision history \(2\)/,
    );
  });

  it("no promote/approve-version controls when there is no current decision (unreviewed slot)", () => {
    // Default fixture has current_decision=null; promotion controls
    // remain absent until a selected decision lands.
    renderRoute();
    expect(screen.queryByTestId("promote-to-reference")).toBeNull();
    for (const label of [
      /^approve version/i,
      /^reject/i,
      /^finalize/i,
      /^qualified/i,
    ]) {
      expect(
        screen.queryByRole("button", { name: label }),
      ).toBeNull();
    }
  });

  it("has ZERO ranking / scoring / recommendation vocabulary", () => {
    renderRoute();
    for (const pattern of [
      /rank/i,
      /score/i,
      /rating/i,
      /star/i,
      /thumbs/i,
      /recommend/i,
      /AI pick/i,
    ]) {
      expect(screen.queryByText(pattern)).toBeNull();
    }
  });

  it("unsupported evidence still renders factually, not as reviewer status", () => {
    renderRoute();
    const section = screen.getByTestId("unsupported-section");
    expect(within(section).getByText(/Provider-declined evidence/i)).toBeInTheDocument();
    expect(within(section).queryByText(/^rejected$/i)).toBeNull();
    expect(within(section).queryByText(/unapproved/i)).toBeNull();
    expect(within(section).queryByText(/poor quality/i)).toBeNull();
  });

  // ---------------------------------------------------------------
  // 9.b.3b — promotion panel
  // ---------------------------------------------------------------

  it("promote button appears when current decision is selected + not yet promoted", () => {
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "d1",
          disposition: "selected",
          frozen_candidate_id: `${FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact`,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
        current_promotion: null,
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    const panel = screen.getByTestId("promotion-panel");
    expect(panel.getAttribute("data-status")).toBe("not_promoted");
    expect(screen.getByTestId("promote-to-reference")).toBeInTheDocument();
  });

  it("clicking promote fires the promote mutation", async () => {
    const user = userEvent.setup();
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "d1",
          disposition: "selected",
          frozen_candidate_id: `${FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact`,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
        current_promotion: null,
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    await user.click(screen.getByTestId("promote-to-reference"));
    expect(mockPromoteMutate).toHaveBeenCalledTimes(1);
    const arg = mockPromoteMutate.mock.calls[0]![0];
    expect(arg.fixtureId).toBe("fixture_h1");
    expect(arg.referenceKind).toBe("portrait_reference");
    expect(arg.referencePurpose).toBe("front");
  });

  it("published state shows 'Published Revision NNN'", () => {
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "d1",
          disposition: "selected",
          frozen_candidate_id: `${FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact`,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
        current_promotion: {
          promotion_audit_id: "audit-1",
          slot_revision: 1,
          substrate_committed_at_utc: "2026-08-08T10:00:01.000000+00:00",
          evidence_published_at_utc: "2026-08-08T10:00:02.000000+00:00",
          publication_status: "published",
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    const panel = screen.getByTestId("promotion-panel");
    expect(panel.getAttribute("data-status")).toBe("published");
    expect(within(panel).getByText(/Published Revision 001/i)).toBeInTheDocument();
    // Promote button hidden when already published.
    expect(screen.queryByTestId("promote-to-reference")).toBeNull();
  });

  it("publication_pending state offers a retry button", async () => {
    const user = userEvent.setup();
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "d1",
          disposition: "selected",
          frozen_candidate_id: `${FROZEN_RUN_ID}/identity_only/stability_still/fixture_h1__portrait_reference__front__compact`,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
        current_promotion: {
          promotion_audit_id: "audit-1",
          slot_revision: 1,
          substrate_committed_at_utc: "2026-08-08T10:00:01.000000+00:00",
          evidence_published_at_utc: null,
          publication_status: "publication_pending",
        },
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    const panel = screen.getByTestId("promotion-panel");
    expect(panel.getAttribute("data-status")).toBe("publication_pending");
    expect(within(panel).getByText(/Publication recovery required/i)).toBeInTheDocument();
    await user.click(within(panel).getByTestId("retry-publication"));
    expect(mockPromoteMutate).toHaveBeenCalledTimes(1);
  });

  it("no_candidate_approved decision hides the promotion panel entirely", () => {
    vi.mocked(useBootstrapSlot).mockReturnValue({
      data: mockSlotData({
        current_decision: {
          decision_id: "d1",
          disposition: "no_candidate_approved",
          frozen_candidate_id: null,
          supersedes_decision_id: null,
          amendment_reason: null,
          reviewer_user_id: 42,
          reviewer_email_at_write_time: "chris@example.test",
          decided_at_utc: "2026-08-08T10:00:00.000000+00:00",
        },
        current_promotion: null,
      }),
      isLoading: false,
      isError: false,
      error: null,
    } as ReturnType<typeof useBootstrapSlot>);
    renderRoute();
    expect(screen.queryByTestId("promotion-panel")).toBeNull();
  });
});
