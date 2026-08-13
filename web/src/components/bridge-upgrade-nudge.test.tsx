/**
 * BridgeUpgradeNudge vitest coverage — C5.3.
 *
 * Guards the invariants from BRIDGE_TOOLS_UI_V1.md §"Test plan"
 * §"C5.3 — tier gate" at the component level. The route-level
 * assertions (Starter sees nudge / Pro sees form / Agency sees form)
 * already live in tools.test.tsx and continue to pass because the
 * `tools-upgrade-nudge` testid is preserved.
 *
 * The three new tests here pin down the component itself:
 *   - Renders the upgrade copy.
 *   - Renders the CTA link to the engine-connections settings page.
 *   - Renders inside a plain container (no router state required
 *     beyond MemoryRouter for `<Link>`).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { BridgeUpgradeNudge } from "./bridge-upgrade-nudge";

function renderNudge() {
  return render(
    <MemoryRouter>
      <BridgeUpgradeNudge />
    </MemoryRouter>,
  );
}

describe("C5.3 — BridgeUpgradeNudge", () => {
  it("renders the Pro-feature explanation copy", () => {
    renderNudge();
    const nudge = screen.getByTestId("tools-upgrade-nudge");
    expect(nudge).toHaveTextContent(/Engine bridge is a Pro feature/);
    expect(nudge).toHaveTextContent(/Upgrade your workspace/);
  });

  it("links the CTA to /settings/engine-connections", () => {
    renderNudge();
    const cta = screen.getByTestId("tools-upgrade-nudge-cta");
    expect(cta).toHaveAttribute("href", "/settings/engine-connections");
    expect(cta).toHaveTextContent(/View engine settings/);
  });

  it("mounts under its stable testid so the route-level tier gate keeps working", () => {
    renderNudge();
    // Rule: `tools-upgrade-nudge` is the testid tools.test.tsx uses to
    // assert the Starter branch renders. Losing it would silently break
    // that suite's tier-gate coverage, so we pin it here too.
    expect(screen.getByTestId("tools-upgrade-nudge")).toBeInTheDocument();
  });
});
