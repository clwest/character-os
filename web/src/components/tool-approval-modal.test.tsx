/**
 * R8.1 ToolApprovalModal unit tests.
 *
 * Tests cover:
 * - Renders headline + cost in dollars
 * - Approve calls useApproveInvocation + fires onResolved
 *   with the result
 * - Reject (without reason) calls useRejectInvocation
 *   with no reason
 * - Reject (with reason) passes the trimmed reason
 * - Dismiss button fires onDismiss
 * - Esc fires onDismiss when idle
 * - Error path: approve failure surfaces a structured error
 *   without dismissing
 *
 * The API hooks are mocked; the modal is hermetic.
 */
import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  ToolApprovalModal,
  type PendingInvocation,
} from "./tool-approval-modal";

vi.mock("@/lib/api/realtime", () => ({
  useApproveInvocation: vi.fn(),
  useRejectInvocation: vi.fn(),
}));

import {
  useApproveInvocation,
  useRejectInvocation,
} from "@/lib/api/realtime";

const approveMock = useApproveInvocation as unknown as ReturnType<typeof vi.fn>;
const rejectMock = useRejectInvocation as unknown as ReturnType<typeof vi.fn>;

function makePending(
  overrides: Partial<PendingInvocation> = {},
): PendingInvocation {
  return {
    invocation_id: "inv_1",
    tool_name: "render_video",
    cost_micros: 80_000,
    reason: "tool cost $0.08 exceeds workspace threshold $0.05",
    args: { script: "Pitch the spring sale." },
    ...overrides,
  };
}

function renderModal(
  overrides: Partial<Parameters<typeof ToolApprovalModal>[0]> = {},
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const onResolved = vi.fn();
  const onDismiss = vi.fn();
  const utils = render(
    <QueryClientProvider client={qc}>
      <ToolApprovalModal
        invocation={overrides.invocation ?? makePending()}
        spokespersonName="Sasha"
        onResolved={overrides.onResolved ?? onResolved}
        onDismiss={overrides.onDismiss ?? onDismiss}
      />
    </QueryClientProvider>,
  );
  return { ...utils, onResolved, onDismiss };
}

describe("ToolApprovalModal (R8.1)", () => {
  beforeEach(() => {
    approveMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
    rejectMock.mockReturnValue({
      mutateAsync: vi.fn(),
      isPending: false,
    });
  });

  it("renders headline with spokesperson + tool + cost", () => {
    renderModal();
    expect(screen.getByTestId("tool-approval-modal")).toBeInTheDocument();
    // "Sasha wants to render a video for you."
    expect(
      screen.getByText(/Sasha wants to render a video for you/i),
    ).toBeInTheDocument();
    // Cost is rendered as a dollar string
    expect(screen.getByText(/\$0\.08/)).toBeInTheDocument();
  });

  it("renders args dict when present", () => {
    renderModal();
    const args = screen.getByTestId("tool-approval-args");
    expect(args).toHaveTextContent("script");
    expect(args).toHaveTextContent("Pitch the spring sale.");
  });

  it("approve fires useApproveInvocation + onResolved", async () => {
    const successResult = {
      state: "succeeded" as const,
      invocation_id: "inv_1",
      tool_name: "render_video",
      cost_micros: 80_000,
      result: { composition_id: "comp_1" },
    };
    const mutateAsync = vi.fn().mockResolvedValue(successResult);
    approveMock.mockReturnValue({ mutateAsync, isPending: false });
    const { onResolved } = renderModal();
    await userEvent.click(screen.getByTestId("tool-approval-approve"));
    await waitFor(() => expect(onResolved).toHaveBeenCalledWith(successResult));
    expect(mutateAsync).toHaveBeenCalledWith("inv_1");
  });

  it("reject without reason fires useRejectInvocation with undefined reason", async () => {
    const rejectedResult = {
      state: "rejected" as const,
      invocation_id: "inv_1",
      tool_name: "render_video",
      cost_micros: 80_000,
    };
    const mutateAsync = vi.fn().mockResolvedValue(rejectedResult);
    rejectMock.mockReturnValue({ mutateAsync, isPending: false });
    const { onResolved } = renderModal();
    await userEvent.click(screen.getByTestId("tool-approval-reject"));
    await waitFor(() => expect(onResolved).toHaveBeenCalled());
    expect(mutateAsync).toHaveBeenCalledWith({
      invocationId: "inv_1",
      reason: undefined,
    });
  });

  it("reject with trimmed reason passes the reason", async () => {
    const rejectedResult = {
      state: "rejected" as const,
      invocation_id: "inv_1",
      tool_name: "render_video",
      cost_micros: 80_000,
      reason: "Not now",
    };
    const mutateAsync = vi.fn().mockResolvedValue(rejectedResult);
    rejectMock.mockReturnValue({ mutateAsync, isPending: false });
    renderModal();
    await userEvent.type(
      screen.getByTestId("tool-approval-reason"),
      "  Not now  ",
    );
    await userEvent.click(screen.getByTestId("tool-approval-reject"));
    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith({
        invocationId: "inv_1",
        reason: "Not now",
      }),
    );
  });

  it("dismiss button fires onDismiss", async () => {
    const { onDismiss } = renderModal();
    await userEvent.click(screen.getByTestId("tool-approval-dismiss"));
    expect(onDismiss).toHaveBeenCalled();
  });

  it("Esc dismisses when idle", async () => {
    const { onDismiss } = renderModal();
    await userEvent.keyboard("{Escape}");
    expect(onDismiss).toHaveBeenCalled();
  });

  it("error message renders on approve failure (modal stays open)", async () => {
    const mutateAsync = vi
      .fn()
      .mockRejectedValue(new Error("backend transient outage"));
    approveMock.mockReturnValue({ mutateAsync, isPending: false });
    const { onResolved } = renderModal();
    await userEvent.click(screen.getByTestId("tool-approval-approve"));
    await waitFor(() =>
      expect(screen.getByTestId("tool-approval-error")).toBeInTheDocument(),
    );
    expect(screen.getByText(/backend transient outage/)).toBeInTheDocument();
    expect(onResolved).not.toHaveBeenCalled();
  });
});
