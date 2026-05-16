/**
 * K6.4 v1.2 — VerificationStatusBadge component tests.
 *
 * Cheap render coverage on the four explicit states + the
 * "empty status renders nothing" backward-compat path. The
 * component is small and the data shape is the load-bearing
 * contract, so we keep coverage shallow per the SESSION 163
 * AI Notes ("test depth follows logic depth, not file count").
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { VerificationStatusBadge } from "./verification-status-badge";

describe("K6.4 v1.2 — VerificationStatusBadge", () => {
  it("renders the verified state with emerald styling", () => {
    render(<VerificationStatusBadge status="verified" />);
    const badge = screen.getByTestId("verification-status-verified");
    expect(badge).toBeInTheDocument();
    expect(badge.textContent).toContain("Verified");
  });

  it("renders the trusted_passthrough state with the operator-typed label", () => {
    render(<VerificationStatusBadge status="trusted_passthrough" />);
    const badge = screen.getByTestId("verification-status-trusted_passthrough");
    expect(badge.textContent).toContain("Operator-typed");
  });

  it("renders the skipped state with the verifier-off label", () => {
    render(<VerificationStatusBadge status="skipped" />);
    expect(screen.getByTestId("verification-status-skipped").textContent).toContain(
      "Verifier off",
    );
  });

  it("renders the rejected state with the strict-rejected label", () => {
    render(<VerificationStatusBadge status="rejected" />);
    expect(screen.getByTestId("verification-status-rejected").textContent).toContain(
      "Strict — rejected",
    );
  });

  it("renders nothing for empty status (pre-v1.2 row or USER message)", () => {
    const { container } = render(<VerificationStatusBadge status="" />);
    expect(container.firstChild).toBeNull();
  });

  it("renders nothing for an unknown status string (defensive)", () => {
    const { container } = render(
      <VerificationStatusBadge status={"bogus" as never} />,
    );
    expect(container.firstChild).toBeNull();
  });
});
