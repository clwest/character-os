/**
 * CostTicker unit tests — R8.2.
 *
 * Drives fake timers to verify the ticker advances every
 * second, the dollar estimate computes correctly, and the
 * color tone shifts as the session approaches its cap.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import { CostTicker } from "./cost-ticker";

// 2026-05-15 14:30:00 UTC — anchor for the fake clock.
const ANCHOR_MS = new Date("2026-05-15T14:30:00Z").getTime();

describe("CostTicker (R8.2)", () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date(ANCHOR_MS));
  });
  afterEach(() => {
    vi.useRealTimers();
  });

  it("renders 0:00 + $0.00 when just started", () => {
    render(
      <CostTicker
        startedAt={new Date(ANCHOR_MS).toISOString()}
        costPerMinuteMicros={80_000}
        maxMinutes={5}
        mockMode={false}
      />,
    );
    const ticker = screen.getByTestId("cost-ticker");
    expect(ticker).toHaveTextContent("0:00");
    expect(ticker).toHaveTextContent("$0.00");
    expect(ticker).toHaveTextContent("5:00 remaining");
    expect(ticker).toHaveAttribute("data-tone", "muted");
  });

  it("advances every second", () => {
    render(
      <CostTicker
        startedAt={new Date(ANCHOR_MS).toISOString()}
        costPerMinuteMicros={80_000}
        maxMinutes={5}
        mockMode={false}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(30_000);
    });
    const ticker = screen.getByTestId("cost-ticker");
    expect(ticker).toHaveAttribute("data-elapsed-seconds", "30");
    expect(ticker).toHaveTextContent("0:30");
    // 30s × $0.08/60s = $0.04
    expect(ticker).toHaveTextContent("$0.04");
  });

  it("flips to amber 3 minutes in", () => {
    render(
      <CostTicker
        startedAt={new Date(ANCHOR_MS).toISOString()}
        costPerMinuteMicros={80_000}
        maxMinutes={5}
        mockMode={false}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(3 * 60 * 1000);
    });
    expect(screen.getByTestId("cost-ticker")).toHaveAttribute(
      "data-tone",
      "amber",
    );
  });

  it("flips to destructive in the last minute", () => {
    render(
      <CostTicker
        startedAt={new Date(ANCHOR_MS).toISOString()}
        costPerMinuteMicros={80_000}
        maxMinutes={5}
        mockMode={false}
      />,
    );
    act(() => {
      vi.advanceTimersByTime(4 * 60 * 1000);
    });
    expect(screen.getByTestId("cost-ticker")).toHaveAttribute(
      "data-tone",
      "destructive",
    );
  });

  it("caps elapsed at maxMinutes and shows 'session cap reached'", () => {
    render(
      <CostTicker
        startedAt={new Date(ANCHOR_MS).toISOString()}
        costPerMinuteMicros={80_000}
        maxMinutes={5}
        mockMode={false}
      />,
    );
    act(() => {
      // Way past the cap
      vi.advanceTimersByTime(10 * 60 * 1000);
    });
    const ticker = screen.getByTestId("cost-ticker");
    expect(ticker).toHaveTextContent("5:00");
    expect(ticker).toHaveTextContent("$0.40");
    expect(ticker).toHaveTextContent("session cap reached");
  });

  it("renders (demo) tag when mockMode is true", () => {
    render(
      <CostTicker
        startedAt={new Date(ANCHOR_MS).toISOString()}
        costPerMinuteMicros={80_000}
        maxMinutes={5}
        mockMode={true}
      />,
    );
    expect(screen.getByTestId("cost-ticker")).toHaveTextContent(/demo/i);
  });

  it("handles null startedAt by rendering 0:00 + no interval", () => {
    render(
      <CostTicker
        startedAt={null}
        costPerMinuteMicros={80_000}
        maxMinutes={5}
        mockMode={false}
      />,
    );
    expect(screen.getByTestId("cost-ticker")).toHaveTextContent("0:00");
    // Advancing time should NOT change the readout (no
    // interval armed).
    act(() => {
      vi.advanceTimersByTime(60_000);
    });
    expect(screen.getByTestId("cost-ticker")).toHaveAttribute(
      "data-elapsed-seconds",
      "0",
    );
  });
});
