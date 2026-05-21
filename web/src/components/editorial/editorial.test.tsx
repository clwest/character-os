/**
 * V3.2 editorial primitives — render tests.
 *
 * One file covers all five primitives. Each component's contract:
 * 1. Renders without crashing.
 * 2. Surfaces the literal copy / attributes the SPA depends on.
 * 3. Applies the load-bearing class names that the editorial
 *    register depends on (font-mono / tracking / gold tones).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import {
  DoctrineQuote,
  EditorialCaption,
  EngagementBrief,
  HairlineDivider,
  SectionHeader,
} from "./index";

// ---- SectionHeader ------------------------------------------------

describe("SectionHeader", () => {
  it("renders `§ NN — Title` with auto-padded number", () => {
    render(<SectionHeader number={1} title="The Charter" />);
    const node = screen.getByTestId("section-header");
    expect(node).toHaveTextContent("§ 01 — The Charter");
  });

  it("pads multi-digit numbers correctly (12 stays 12)", () => {
    render(<SectionHeader number={12} title="The Lab" />);
    expect(screen.getByTestId("section-header")).toHaveTextContent(
      "§ 12 — The Lab",
    );
  });

  it("clamps numbers to 1-99", () => {
    render(<SectionHeader number={120} title="Overshoot" />);
    expect(screen.getByTestId("section-header")).toHaveTextContent(
      "§ 99 — Overshoot",
    );
  });

  it("applies the load-bearing editorial classes", () => {
    render(<SectionHeader number={3} title="The Position" />);
    const node = screen.getByTestId("section-header");
    expect(node.className).toMatch(/font-mono/);
    expect(node.className).toMatch(/uppercase/);
    expect(node.className).toMatch(/tracking-\[0\.34em\]/);
    expect(node.className).toMatch(/text-gold/);
  });

  it("renders as the configured tag", () => {
    render(<SectionHeader number={4} title="The Suite" as="h2" />);
    const node = screen.getByTestId("section-header");
    expect(node.tagName.toLowerCase()).toBe("h2");
  });
});

// ---- HairlineDivider ----------------------------------------------

describe("HairlineDivider", () => {
  it("defaults to a 12-unit solid bright gold bar", () => {
    render(<HairlineDivider />);
    const node = screen.getByTestId("hairline-divider");
    expect(node.className).toMatch(/w-12/);
    expect(node.className).toMatch(/bg-gold\/60/);
    expect(node.dataset.variant).toBe("solid");
    expect(node.dataset.tone).toBe("bright");
  });

  it("supports width presets", () => {
    render(<HairlineDivider width="xl" />);
    expect(screen.getByTestId("hairline-divider").className).toMatch(/w-32/);
  });

  it("swaps to a gradient variant", () => {
    render(<HairlineDivider variant="gradient" />);
    const node = screen.getByTestId("hairline-divider");
    expect(node.className).toMatch(/hairline-gold/);
    expect(node.dataset.variant).toBe("gradient");
  });

  it("muted tone uses gold/40 not gold/60", () => {
    render(<HairlineDivider tone="muted" />);
    expect(screen.getByTestId("hairline-divider").className).toMatch(
      /bg-gold\/40/,
    );
  });

  it("is decorative — aria-hidden", () => {
    render(<HairlineDivider />);
    expect(screen.getByTestId("hairline-divider")).toHaveAttribute(
      "aria-hidden",
      "true",
    );
  });
});

// ---- EditorialCaption ---------------------------------------------

describe("EditorialCaption", () => {
  it("renders Plate NN with auto-padded number", () => {
    render(<EditorialCaption plate={1}>The proprietor.</EditorialCaption>);
    const node = screen.getByTestId("editorial-caption");
    expect(node.dataset.plate).toBe("01");
    expect(node).toHaveTextContent("Plate 01");
    expect(node).toHaveTextContent("The proprietor.");
  });

  it("preserves string plates (e.g. Roman numerals)", () => {
    render(<EditorialCaption plate="VI">Lab VI · Character OS.</EditorialCaption>);
    const node = screen.getByTestId("editorial-caption");
    expect(node.dataset.plate).toBe("VI");
    expect(node).toHaveTextContent("Plate VI");
  });

  it("defaults to right alignment", () => {
    render(<EditorialCaption plate={1}>Right.</EditorialCaption>);
    expect(screen.getByTestId("editorial-caption").className).toMatch(
      /text-right/,
    );
  });

  it("supports left + center alignment", () => {
    const { rerender } = render(
      <EditorialCaption plate={2} align="left">
        Left.
      </EditorialCaption>,
    );
    expect(screen.getByTestId("editorial-caption").className).toMatch(
      /text-left/,
    );
    rerender(
      <EditorialCaption plate={3} align="center">
        Center.
      </EditorialCaption>,
    );
    expect(screen.getByTestId("editorial-caption").className).toMatch(
      /text-center/,
    );
  });
});

// ---- DoctrineQuote ------------------------------------------------

describe("DoctrineQuote", () => {
  it("renders the body and optional source", () => {
    render(
      <DoctrineQuote source="The 24/7 Doctrine">
        The future belongs to those who...
      </DoctrineQuote>,
    );
    expect(screen.getByTestId("doctrine-quote")).toHaveTextContent(
      "The future belongs to those who...",
    );
    expect(screen.getByTestId("doctrine-quote-source")).toHaveTextContent(
      "The 24/7 Doctrine",
    );
  });

  it("omits the footer when no source is given", () => {
    render(<DoctrineQuote>Standalone doctrine.</DoctrineQuote>);
    expect(screen.queryByTestId("doctrine-quote-source")).toBeNull();
  });

  it("scales by size prop", () => {
    const { rerender } = render(
      <DoctrineQuote size="sm">Tiny.</DoctrineQuote>,
    );
    const small = screen.getByTestId("doctrine-quote").querySelector("p");
    expect(small?.className).toMatch(/text-xl/);

    rerender(<DoctrineQuote size="lg">Huge.</DoctrineQuote>);
    const large = screen.getByTestId("doctrine-quote").querySelector("p");
    expect(large?.className).toMatch(/text-3xl/);
  });
});

// ---- EngagementBrief ----------------------------------------------

describe("EngagementBrief", () => {
  const ENTRIES = [
    { label: "Cadence", value: "Quarterly · ongoing" },
    { label: "Format", value: "Embedded studio" },
    { label: "Discretion", value: "Implicit" },
    { label: "Reply", value: "By morning", emphasis: true },
  ];

  it("renders the title and every entry", () => {
    render(<EngagementBrief entries={ENTRIES} />);
    const aside = screen.getByTestId("engagement-brief");
    expect(aside).toHaveTextContent("Engagement Brief");
    for (const entry of ENTRIES) {
      expect(aside).toHaveTextContent(entry.label);
      expect(aside).toHaveTextContent(entry.value);
    }
  });

  it("uses gold-bright on emphasized rows; default cream otherwise", () => {
    render(<EngagementBrief entries={ENTRIES} />);
    const rows = screen.getAllByTestId("engagement-brief-row");
    expect(rows).toHaveLength(4);
    // first three rows: default cream
    expect(rows[0]!.querySelector("dd")?.className).toMatch(/text-cream/);
    expect(rows[1]!.querySelector("dd")?.className).toMatch(/text-cream/);
    expect(rows[2]!.querySelector("dd")?.className).toMatch(/text-cream/);
    // last row: gold-bright
    expect(rows[3]!.querySelector("dd")?.className).toMatch(/text-gold-bright/);
  });

  it("supports a custom title", () => {
    render(<EngagementBrief title="Reply Brief" entries={ENTRIES} />);
    expect(screen.getByTestId("engagement-brief")).toHaveTextContent(
      "Reply Brief",
    );
  });

  it("renders zero rows without crashing", () => {
    render(<EngagementBrief entries={[]} />);
    expect(screen.queryAllByTestId("engagement-brief-row")).toHaveLength(0);
  });
});
