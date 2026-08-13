/**
 * BridgeResultPanel vitest coverage — C5.2.
 *
 * Guards the invariants from BRIDGE_TOOLS_UI_V1.md §"Test plan"
 * §"C5.2 — result panel":
 *   - Answer text renders (whitespace-preserved).
 *   - Copy button copies the answer text to the clipboard.
 *   - "View in asset library" link points at the correct URL when an
 *     asset_id is present, and is omitted when it isn't.
 *   - Empty-answer payload falls back cleanly to the empty-state label.
 *
 * The component uses `Link` from react-router-dom, so tests wrap in
 * a MemoryRouter. Clipboard access is stubbed via a per-test spy on
 * `navigator.clipboard.writeText`.
 */
import { describe, expect, it } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";

import { BridgeResultPanel } from "./bridge-result-panel";
import type { DispatchResult } from "@/lib/api/realtime";

function makeResult(
  overrides: Partial<{
    answer: unknown;
    asset_id: unknown;
    state: DispatchResult["state"];
  }> = {},
): DispatchResult {
  const {
    answer = "Bridge answer text.",
    asset_id = "as-bridge-1",
    state = "succeeded",
  } = overrides;
  return {
    state,
    invocation_id: "inv-1",
    tool_name: "consult_engine",
    cost_micros: 5_000,
    result: {
      answer,
      asset_id,
      event: "avatar_says_answer",
    } as DispatchResult["result"],
    error_message: "",
    reason: "",
  };
}

function renderPanel(result: DispatchResult) {
  return render(
    <MemoryRouter>
      <BridgeResultPanel result={result} />
    </MemoryRouter>,
  );
}

describe("C5.2 — BridgeResultPanel", () => {
  it("renders the answer text and preserves whitespace", () => {
    renderPanel(makeResult({ answer: "Line one.\nLine two." }));
    const answer = screen.getByTestId("tools-result-answer");
    expect(answer).toHaveTextContent("Line one.");
    expect(answer).toHaveTextContent("Line two.");
    // whitespace-pre-wrap keeps newlines addressable via the raw text.
    expect(answer.textContent).toContain("\n");
  });

  it("copies the answer to the clipboard when the copy button fires", async () => {
    // `userEvent.setup()` installs its own clipboard emulation on
    // `navigator.clipboard` (a paired writeText/readText stub) — read
    // through the same surface to verify the write landed.
    const user = userEvent.setup();
    renderPanel(makeResult({ answer: "Forty-two." }));

    await user.click(screen.getByTestId("tools-result-copy"));

    await waitFor(async () => {
      const copied = await navigator.clipboard.readText();
      expect(copied).toBe("Forty-two.");
    });
    // Optimistic UI: button flips to "Copied" label.
    expect(screen.getByTestId("tools-result-copy")).toHaveTextContent(
      "Copied",
    );
  });

  it("links to the asset library detail view when an asset_id is present", () => {
    renderPanel(makeResult({ asset_id: "as-42" }));
    const link = screen.getByTestId("tools-result-asset-link");
    expect(link).toHaveAttribute("href", "/workspace/assets/as-42");
  });

  it("omits the asset library link when asset_id is missing", () => {
    renderPanel(makeResult({ asset_id: null }));
    expect(
      screen.queryByTestId("tools-result-asset-link"),
    ).not.toBeInTheDocument();
  });

  it("falls back to the empty-state label when the answer is blank and hides the copy button", () => {
    renderPanel(makeResult({ answer: "" }));
    expect(screen.getByTestId("tools-result-answer")).toHaveTextContent(
      "(no answer content returned)",
    );
    // No answer content → no copy affordance.
    expect(
      screen.queryByTestId("tools-result-copy"),
    ).not.toBeInTheDocument();
  });
});
