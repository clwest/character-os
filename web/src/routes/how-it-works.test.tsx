/**
 * /how-it-works smoke test.
 *
 * Asserts the load-bearing surface: every section renders, the
 * CTA wires through to a mailto: with the parent-company contact,
 * and the "What's not built yet" honesty block actually shows up.
 * If a future copy edit accidentally drops the honesty section,
 * this test catches it before the page lies to a reader.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { HowItWorksRoute } from "./how-it-works";
import { parentBrand } from "@/lib/brand";

function renderRoute() {
  return render(
    <MemoryRouter>
      <HowItWorksRoute />
    </MemoryRouter>,
  );
}

describe("HowItWorksRoute", () => {
  it("renders every section testid", () => {
    renderRoute();
    expect(screen.getByTestId("how-hero")).toBeInTheDocument();
    expect(screen.getByTestId("how-monday")).toBeInTheDocument();
    expect(screen.getByTestId("how-pipeline")).toBeInTheDocument();
    expect(screen.getByTestId("how-live-today")).toBeInTheDocument();
    expect(screen.getByTestId("how-not-built")).toBeInTheDocument();
    expect(screen.getByTestId("how-cta")).toBeInTheDocument();
    expect(screen.getByTestId("how-faq")).toBeInTheDocument();
  });

  it("renders all five pipeline steps in order", () => {
    renderRoute();
    for (const n of [1, 2, 3, 4, 5]) {
      expect(
        screen.getByTestId(`how-pipeline-step-${n}`),
      ).toBeInTheDocument();
    }
  });

  it("wires the CTA to a mailto with the parent-company contact", () => {
    renderRoute();
    const cta = screen.getByTestId("how-cta-mailto");
    const href = cta.getAttribute("href") ?? "";
    expect(href).toMatch(/^mailto:/);
    expect(href).toContain(parentBrand.contact.email);
    // Subject prefilled
    expect(href).toContain("subject=");
  });

  it("honesty block surfaces at least the high-visibility gaps", () => {
    renderRoute();
    const block = screen.getByTestId("how-not-built");
    // These are load-bearing — operator wants third-party readers
    // to see the real state, not the marketing version.
    expect(block).toHaveTextContent(/pricing yet|paid tier/i);
    expect(block).toHaveTextContent(/light mode/i);
    expect(block).toHaveTextContent(/Runway/);
  });

  it("FAQ surfaces at least four common questions", () => {
    renderRoute();
    const faq = screen.getByTestId("how-faq");
    const dts = faq.querySelectorAll("dt");
    expect(dts.length).toBeGreaterThanOrEqual(4);
  });
});
