/**
 * SESSION 251 — SpokespersonDeleteModal unit tests.
 *
 * Covers the SPA half of the customer-facing delete contract:
 *
 * - Confirmation dialog identifies the teammate by name (matches
 *   the copy locked in the task brief).
 * - Cancel + Esc + backdrop dismiss all fire ``onDismiss`` and
 *   do NOT call the delete mutation.
 * - Confirm calls ``useDeleteSpokesperson`` with the teammate id
 *   and, on success, fires ``onDeleted`` (parent handles redirect
 *   + cache invalidation).
 * - Error path surfaces the message and re-enables the buttons
 *   instead of leaving the modal in a stuck "Deleting…" state.
 */
import { beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { SpokespersonDeleteModal } from "./spokesperson-delete-modal";

vi.mock("@/lib/api/spokespeople", () => ({
  useDeleteSpokesperson: vi.fn(),
}));

import { useDeleteSpokesperson } from "@/lib/api/spokespeople";

const deleteMock = useDeleteSpokesperson as unknown as ReturnType<typeof vi.fn>;

function renderModal(
  overrides: Partial<Parameters<typeof SpokespersonDeleteModal>[0]> = {},
) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  const onDismiss = vi.fn();
  const onDeleted = vi.fn();
  const utils = render(
    <QueryClientProvider client={qc}>
      <SpokespersonDeleteModal
        spokespersonId={overrides.spokespersonId ?? "tm_1"}
        spokespersonName={overrides.spokespersonName ?? "Sasha"}
        onDismiss={overrides.onDismiss ?? onDismiss}
        onDeleted={overrides.onDeleted ?? onDeleted}
      />
    </QueryClientProvider>,
  );
  return { ...utils, onDismiss, onDeleted };
}

describe("SpokespersonDeleteModal (SESSION 251)", () => {
  beforeEach(() => {
    deleteMock.mockReturnValue({
      mutateAsync: vi.fn().mockResolvedValue(undefined),
      isPending: false,
    });
  });

  it("names the teammate in the dialog title and confirm button", () => {
    renderModal({ spokespersonName: "Sasha" });
    expect(
      screen.getByTestId("spokesperson-delete-title"),
    ).toHaveTextContent("Delete Sasha?");
    // The confirm button also names them so the destructive action
    // is unambiguous.
    expect(
      screen.getByTestId("spokesperson-delete-confirm"),
    ).toHaveTextContent(/Delete Sasha/);
  });

  it("states that generated content stays in the library", () => {
    renderModal();
    // Product-contract copy — historical outputs are preserved
    // server-side (SESSION 251 SET_NULL migrations). Copy must
    // reflect that so the customer knows the risk is bounded.
    expect(
      screen.getByText(/Existing generated videos and assets will remain/i),
    ).toBeInTheDocument();
  });

  it("discloses the SESSION 275 knowledge-lifecycle contract", () => {
    // Product-contract copy — the backend ``pre_delete``/``post_delete``
    // signals archive KDs where the deleted teammate was the sole
    // spokesperson, and preserve KDs shared with other characters or
    // intentionally shared with a Universe / workspace. The modal
    // must disclose this so an operator can reason about audience
    // scope before confirming the destructive action. See
    // ``docs/design/SESSION_275_CHARACTER_KNOWLEDGE_LIFECYCLE_AUDIT.md``.
    renderModal({ spokespersonName: "Sasha" });
    const copy = screen.getByTestId("spokesperson-delete-knowledge-copy");
    expect(copy).toHaveTextContent(
      /Knowledge assigned only to Sasha will be\s+archived/i,
    );
    expect(copy).toHaveTextContent(/shared with other characters stays with/i);
    expect(copy).toHaveTextContent(
      /intentionally shared Universe or workspace knowledge stays\s+shared/i,
    );
    expect(copy).toHaveTextContent(/not be\s+exposed to your other characters/i);
  });

  it("cancel fires onDismiss and does NOT delete", async () => {
    const mutateAsync = vi.fn();
    deleteMock.mockReturnValue({ mutateAsync, isPending: false });
    const user = userEvent.setup();
    const { onDismiss, onDeleted } = renderModal();
    await user.click(screen.getByTestId("spokesperson-delete-cancel"));
    expect(onDismiss).toHaveBeenCalledOnce();
    expect(mutateAsync).not.toHaveBeenCalled();
    expect(onDeleted).not.toHaveBeenCalled();
  });

  it("confirm calls the mutation with the id and fires onDeleted", async () => {
    const mutateAsync = vi.fn().mockResolvedValue(undefined);
    deleteMock.mockReturnValue({ mutateAsync, isPending: false });
    const user = userEvent.setup();
    const { onDeleted, onDismiss } = renderModal({ spokespersonId: "tm_xyz" });
    await user.click(screen.getByTestId("spokesperson-delete-confirm"));
    await waitFor(() => expect(onDeleted).toHaveBeenCalledOnce());
    expect(mutateAsync).toHaveBeenCalledWith("tm_xyz");
    expect(onDismiss).not.toHaveBeenCalled();
  });

  it("Esc dismisses when idle", async () => {
    const user = userEvent.setup();
    const { onDismiss } = renderModal();
    await user.keyboard("{Escape}");
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("backdrop click dismisses when idle", async () => {
    const user = userEvent.setup();
    const { onDismiss } = renderModal();
    await user.click(screen.getByTestId("spokesperson-delete-modal"));
    expect(onDismiss).toHaveBeenCalledOnce();
  });

  it("delete failure surfaces error and re-enables buttons", async () => {
    const mutateAsync = vi
      .fn()
      .mockRejectedValueOnce(new Error("server said no"));
    deleteMock.mockReturnValue({ mutateAsync, isPending: false });
    const user = userEvent.setup();
    const { onDeleted } = renderModal();
    await user.click(screen.getByTestId("spokesperson-delete-confirm"));
    await waitFor(() =>
      expect(screen.getByTestId("spokesperson-delete-error")).toHaveTextContent(
        /server said no/,
      ),
    );
    expect(onDeleted).not.toHaveBeenCalled();
    // Buttons back to idle so operator can retry or cancel.
    expect(
      screen.getByTestId("spokesperson-delete-confirm"),
    ).not.toBeDisabled();
    expect(screen.getByTestId("spokesperson-delete-cancel")).not.toBeDisabled();
  });
});
