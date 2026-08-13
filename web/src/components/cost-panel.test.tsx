/**
 * K7.1 (SESSION 174) — CostPanel unit tests.
 *
 * Covers: loading skeleton, error banner, unavailable state
 * (backend doesn't yet ship cost_breakdown), and the live
 * three-state render with MTD + all-time + per-surface
 * dollar formatting.
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { CostPanel, formatDollars } from "./cost-panel";
import type { OverviewCostBreakdown } from "@/lib/api/overview";

const SAMPLE: OverviewCostBreakdown = {
  compositions_micros: 2_500_000, // $2.50
  images_micros: 17_500, // $0.0175
  realtime_micros: 50_000, // $0.05
  total_micros: 2_567_500, // $2.5675
  mtd_micros: 67_500, // $0.0675
  mtd_compositions_micros: 0,
  mtd_images_micros: 17_500,
  mtd_realtime_micros: 50_000,
  month_start: "2026-05-01T00:00:00+00:00",
};

describe("K7.1 — CostPanel", () => {
  it("renders the skeleton while loading", () => {
    render(<CostPanel loading={true} error={null} data={undefined} />);
    expect(screen.getByTestId("cost-panel-skeleton")).toBeInTheDocument();
  });

  it("renders the unavailable note when backend omits cost_breakdown", () => {
    render(<CostPanel loading={false} error={null} data={undefined} />);
    expect(screen.getByTestId("cost-panel-unavailable")).toBeInTheDocument();
  });

  it("renders the error banner when overview fetch failed", () => {
    render(
      <CostPanel
        loading={false}
        error={new Error("boom")}
        data={undefined}
      />,
    );
    expect(screen.getByTestId("cost-panel-error")).toBeInTheDocument();
  });

  it("renders MTD + all-time totals and per-surface breakdown", () => {
    render(<CostPanel loading={false} error={null} data={SAMPLE} />);
    const mtd = screen.getByTestId("cost-total-mtd");
    expect(mtd).toHaveTextContent("This month");
    // $0.0675 — under-$1 path uses 3 decimals (the sub-cent
    // formatter only kicks in below $0.01).
    expect(mtd).toHaveTextContent(/\$0\.0\d{2}/);

    const allTime = screen.getByTestId("cost-total-alltime");
    expect(allTime).toHaveTextContent("All time");
    expect(allTime).toHaveTextContent("$2.57");

    // Per-surface rows surface both MTD and all-time numbers.
    expect(screen.getByTestId("cost-row-compositions")).toHaveTextContent(
      "Videos (compositions)",
    );
    expect(screen.getByTestId("cost-row-images")).toHaveTextContent("Images");
    expect(screen.getByTestId("cost-row-realtime")).toHaveTextContent(
      "Realtime sessions",
    );

    // Images row total ($0.0175) sits in the sub-dollar band →
    // 3 decimals → "$0.018".
    const imagesRow = screen.getByTestId("cost-row-images");
    expect(imagesRow.textContent).toMatch(/\$0\.\d{3}/);
  });

  it("formatDollars covers the three precision bands", () => {
    expect(formatDollars(0)).toBe("$0.00");
    expect(formatDollars(6_500)).toBe("$0.0065"); // sub-cent
    expect(formatDollars(50_000)).toBe("$0.050"); // sub-dollar
    expect(formatDollars(2_500_000)).toBe("$2.50"); // dollars
    expect(formatDollars(42_500_000)).toBe("$42.50");
  });
});
