/**
 * SESSION 264 Slice 3 dogfood follow-up — MemoriesUsedSummary
 * (the compact "Continuity" affordance near the video player).
 *
 * Invariants covered:
 *
 * 1. Zero memories → renders NULL (no empty-state noise near
 *    the primary result).
 * 2. One memory → visible near the primary result with body
 *    quote + episode link.
 * 3. Multiple memories → compact "Used N story memories" count
 *    + first memory's body quote + "+ N-1 more shown below"
 *    (does not overwhelm the primary result).
 * 4. Archived-after-render memory still shows historical
 *    provenance with a "(forgotten after this render …)"
 *    indicator.
 * 5. Superseded-after-render memory shows a similar indicator.
 * 6. Source Episode link points to the correct route.
 * 7. Contains NO mutation controls (no buttons, no inputs, no
 *    forms) — read-only summary only.
 * 8. Section header is "Continuity" (distinct from the Slice 1
 *    promote panel's "Story history" label — the discoverability
 *    finding's whole point).
 * 9. Human-facing language only — no implementation vocabulary
 *    ("memory_ids", "vector", "embedding", "retrieval lane",
 *    "top_k").
 * 10. Handles the pathological all-unresolved case honestly
 *     (surfaces the count, does not fake a body quote).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { MemoriesUsedSummary } from "./narrative-memory-panels";
import type { MemoryUsedRow } from "@/lib/api/recipes";

function resolved(
  overrides: Partial<Extract<MemoryUsedRow, { resolved: true }>> = {},
): MemoryUsedRow {
  return {
    id: "mem-1",
    resolved: true as const,
    kind: "event",
    body: "the agent Patch wired to the workshop thinks it runs the place",
    weight: "peripheral",
    status: "remembered",
    archived_at: null,
    witnessed_by: [],
    episode_id: "ep-1",
    episode_title: "AI took over the lab",
    universe_id: "uni-1",
    universe_name: "Patch's Workshop",
    source_composition_id: "comp-source",
    ...overrides,
  };
}

function renderSummary(memories: MemoryUsedRow[]) {
  return render(
    <MemoryRouter>
      <MemoriesUsedSummary memories={memories} />
    </MemoryRouter>,
  );
}


describe("SESSION 264 Slice 3 dogfood follow-up — MemoriesUsedSummary", () => {
  it("renders nothing when zero memories fed the render", () => {
    const { container } = renderSummary([]);
    expect(container).toBeEmptyDOMElement();
    expect(
      screen.queryByTestId("composition-continuity-summary"),
    ).toBeNull();
  });

  it("shows the count + body quote + episode link for one memory", () => {
    renderSummary([resolved()]);
    // Panel is present.
    expect(
      screen.getByTestId("composition-continuity-summary"),
    ).toBeInTheDocument();
    // Uses "Continuity" as its section header — distinct from
    // the Slice 1 promote panel's "Story history" label
    // (the discoverability finding's whole point).
    expect(
      screen.getByText(/^Continuity$/),
    ).toBeInTheDocument();
    // Count is human-facing pluralized.
    expect(
      screen.getByTestId("composition-continuity-count"),
    ).toHaveTextContent(/Used 1 story memory/);
    // Body quote.
    expect(
      screen.getByTestId("composition-continuity-body"),
    ).toHaveTextContent(/thinks it runs the place/);
    // Episode source link.
    const link = screen.getByTestId("composition-continuity-episode-link");
    expect(link).toHaveAttribute("href", "/workspace/episodes/ep-1");
    expect(link).toHaveTextContent(/AI took over the lab/);
  });

  it("compact-renders N memories with first body + '+ N-1 more shown below'", () => {
    renderSummary([
      resolved({ id: "m1", body: "first body" }),
      resolved({ id: "m2", body: "second body" }),
      resolved({ id: "m3", body: "third body" }),
    ]);
    expect(
      screen.getByTestId("composition-continuity-count"),
    ).toHaveTextContent(/Used 3 story memories/);
    // Only the FIRST body is quoted — panel stays compact.
    expect(
      screen.getByTestId("composition-continuity-body"),
    ).toHaveTextContent(/first body/);
    // Other bodies are NOT quoted in the summary (they live in
    // the detailed MemoriesUsedPanel further down).
    expect(screen.queryByText(/second body/)).toBeNull();
    expect(screen.queryByText(/third body/)).toBeNull();
    // "+ N-1 more shown below" cue.
    expect(
      screen.getByTestId("composition-continuity-more"),
    ).toHaveTextContent(/\+ 2 more shown below/);
  });

  it("flags an archived-after-render memory but still shows body + link", () => {
    renderSummary([
      resolved({
        id: "mem-archived",
        body: "the throne joke",
        status: "archived",
        archived_at: "2026-08-18T14:00:00Z",
      }),
    ]);
    // Body still surfaces.
    expect(
      screen.getByTestId("composition-continuity-body"),
    ).toHaveTextContent(/throne joke/);
    // Archived-after-render indicator.
    expect(
      screen.getByTestId("composition-continuity-archived-flag"),
    ).toHaveTextContent(/forgotten after this render/i);
  });

  it("flags a superseded-after-render memory", () => {
    renderSummary([
      resolved({
        id: "mem-superseded",
        body: "old take",
        status: "superseded",
      }),
    ]);
    expect(
      screen.getByTestId("composition-continuity-body"),
    ).toHaveTextContent(/old take/);
    expect(
      screen.getByTestId("composition-continuity-superseded-flag"),
    ).toHaveTextContent(/replaced by a later memory/i);
  });

  it("honestly surfaces the count when every row is an unresolved stub", () => {
    // Pathological but real case: memory was deleted or cross-
    // workspace-smuggled. Summary should count it but skip the
    // body quote (nothing to quote).
    renderSummary([
      { id: "00000000-0000-0000-0000-000000000000", resolved: false },
    ]);
    expect(
      screen.getByTestId("composition-continuity-count"),
    ).toHaveTextContent(/Used 1 story memory/);
    // No body quote element.
    expect(
      screen.queryByTestId("composition-continuity-body"),
    ).toBeNull();
    // Honest "no longer available" message instead of a fake
    // quote.
    expect(
      screen.getByTestId("composition-continuity-all-unresolved"),
    ).toHaveTextContent(/no longer available/i);
  });

  it("contains NO mutation controls — read-only summary", () => {
    renderSummary([resolved()]);
    const panel = screen.getByTestId("composition-continuity-summary");
    // No buttons, no textboxes, no forms — this is a read-only
    // discoverability affordance. Mutation lives on the Slice 1
    // promote panel and the archive action on the detailed
    // MemoriesUsedPanel.
    expect(panel.querySelector("button")).toBeNull();
    expect(panel.querySelector("input")).toBeNull();
    expect(panel.querySelector("textarea")).toBeNull();
    expect(panel.querySelector("form")).toBeNull();
  });

  it("does NOT use implementation vocabulary on-screen", () => {
    renderSummary([resolved(), resolved({ id: "m2", body: "b2" })]);
    const panel = screen.getByTestId("composition-continuity-summary");
    const text = (panel.textContent ?? "").toLowerCase();
    // These strings must never appear in operator-facing
    // continuity UI (per SESSION 264 dogfood UX correction
    // rule + operator brief).
    for (const forbidden of [
      "memory_ids",
      "vector",
      "embedding",
      "retrieval lane",
      "top_k",
      "narrativememory",
      "chunk_id",
      "promotion",
    ]) {
      expect(
        text.includes(forbidden),
        `forbidden vocabulary "${forbidden}" appeared in the summary text`,
      ).toBe(false);
    }
  });

  it("does not render '+ N-1 more' for a single-memory render", () => {
    renderSummary([resolved()]);
    expect(
      screen.queryByTestId("composition-continuity-more"),
    ).toBeNull();
  });
});
