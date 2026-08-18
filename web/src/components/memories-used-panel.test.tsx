/**
 * SESSION 264 Slice 3 — Composition detail page "Memories used in
 * this render" panel tests.
 *
 * Invariants covered:
 *
 * 1. Empty ``memories`` array renders nothing (no empty-state
 *    noise on standalone / pre-Slice-2 renders).
 * 2. A resolved memory renders body + witness label.
 * 3. Empty ``witnessed_by`` renders as "Everyone in the episode".
 * 4. Narrowed ``witnessed_by`` renders comma-joined names.
 * 5. Archived-since-render memory still appears with a
 *    "Forgotten after this render — still shown here as
 *    provenance." indicator.
 * 6. Superseded-since-render memory shows a similar indicator.
 * 7. Unresolved stub (memory deleted or cross-workspace smuggle)
 *    renders a short "no longer available" note without
 *    breaking layout.
 * 8. Episode backlink renders when episode_id is present.
 *
 * Panel is read-only; no mocks needed beyond MemoryRouter (for
 * the episode backlink anchor).
 */
import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";

import { MemoriesUsedPanel } from "./narrative-memory-panels";
import type { MemoryUsedRow } from "@/lib/api/recipes";

function resolvedMemory(
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

function renderPanel(memories: MemoryUsedRow[]) {
  return render(
    <MemoryRouter>
      <MemoriesUsedPanel memories={memories} />
    </MemoryRouter>,
  );
}

describe("SESSION 264 Slice 3 — MemoriesUsedPanel", () => {
  it("renders nothing when the memories array is empty", () => {
    const { container } = renderPanel([]);
    expect(container).toBeEmptyDOMElement();
  });

  it("shows the memory body + whole-cast witness label by default", () => {
    renderPanel([resolvedMemory()]);
    expect(
      screen.getByTestId("composition-memories-used"),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/thinks it runs the place/),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/Remembered by: Everyone in the episode/),
    ).toBeInTheDocument();
  });

  it("shows narrowed witness names when witnessed_by is populated", () => {
    renderPanel([
      resolvedMemory({
        witnessed_by: [
          { id: "tm-patch", name: "Patch" },
          { id: "tm-rivet", name: "Rivet" },
        ],
      }),
    ]);
    expect(
      screen.getByText(/Remembered by: Patch, Rivet/),
    ).toBeInTheDocument();
  });

  it("flags an archived-since-render memory but still shows it", () => {
    renderPanel([
      resolvedMemory({
        id: "mem-archived",
        body: "the throne joke",
        status: "archived",
        archived_at: "2026-08-18T14:00:00Z",
      }),
    ]);
    // The body is still present.
    expect(screen.getByText(/the throne joke/)).toBeInTheDocument();
    // AND the archived indicator surfaces.
    expect(
      screen.getByTestId(
        "composition-memory-used-archived-mem-archived",
      ),
    ).toHaveTextContent(/Forgotten after this render/);
  });

  it("flags a superseded-since-render memory but still shows it", () => {
    renderPanel([
      resolvedMemory({
        id: "mem-superseded",
        body: "old take",
        status: "superseded",
      }),
    ]);
    expect(screen.getByText(/old take/)).toBeInTheDocument();
    expect(
      screen.getByText(/Replaced by a later memory/),
    ).toBeInTheDocument();
  });

  it("renders an unresolved stub without breaking layout", () => {
    renderPanel([
      { id: "00000000-0000-0000-0000-000000000000", resolved: false },
    ]);
    const stub = screen.getByTestId(
      "composition-memory-used-stub-00000000-0000-0000-0000-000000000000",
    );
    expect(stub).toHaveTextContent(/no longer available/);
  });

  it("renders an episode backlink when episode_id is present", () => {
    renderPanel([
      resolvedMemory({
        episode_id: "ep-42",
        episode_title: "The printer incident",
      }),
    ]);
    const link = screen.getByRole("link", { name: /printer incident/i });
    expect(link).toHaveAttribute("href", "/workspace/episodes/ep-42");
  });

  it("shows correct pluralization in the counter", () => {
    renderPanel([resolvedMemory()]);
    expect(screen.getByText(/1 memory used/i)).toBeInTheDocument();
    // Multiple memories.
    const { rerender } = renderPanel([
      resolvedMemory({ id: "m1" }),
      resolvedMemory({ id: "m2" }),
      resolvedMemory({ id: "m3" }),
    ]);
    // Reused renderer doesn't help; render fresh instead.
    rerender(
      <MemoryRouter>
        <MemoriesUsedPanel
          memories={[
            resolvedMemory({ id: "m1" }),
            resolvedMemory({ id: "m2" }),
            resolvedMemory({ id: "m3" }),
          ]}
        />
      </MemoryRouter>,
    );
    expect(screen.getByText(/3 memories used/i)).toBeInTheDocument();
  });
});
