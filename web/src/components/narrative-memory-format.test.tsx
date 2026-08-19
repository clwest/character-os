/**
 * SESSION 267 §15.11.4 — formatWitnessAvailability unit tests.
 *
 * The helper renders a NarrativeMemory's witness list as a
 * creator-facing availability condition. Locked outputs so the
 * rendered wording stays truthful to the retrieval predicate
 * (shell/apps/embeddings/retrieval.py:499-543):
 *
 *   * empty witness list → Universe-wide eligibility
 *   * one witness         → eligibility when that character is
 *                           in the future cast
 *   * two+ witnesses      → OR-overlap (at least one witness in
 *                           the future cast). Rendered with an
 *                           explicit "or" so the string cannot
 *                           be misread as AND-intersection.
 */
import { describe, expect, it } from "vitest";

import { formatWitnessAvailability } from "./narrative-memory-panels";

describe("SESSION 267 §15.11.4 — formatWitnessAvailability", () => {
  it("whole-cast (empty list) reads as 'In any future scene'", () => {
    expect(formatWitnessAvailability([])).toBe("In any future scene");
  });

  it("single witness reads as 'When {name} is present'", () => {
    expect(formatWitnessAvailability([{ name: "Rivet" }])).toBe(
      "When Rivet is present",
    );
  });

  it("two witnesses render with explicit OR", () => {
    // Multi-witness runtime is OR-overlap. The rendered string
    // must not be readable as AND ("Patch AND Rivet present").
    expect(
      formatWitnessAvailability([{ name: "Patch" }, { name: "Rivet" }]),
    ).toBe("When Patch or Rivet is present");
  });

  it("three witnesses render with Oxford-or", () => {
    expect(
      formatWitnessAvailability([
        { name: "Patch" },
        { name: "Rivet" },
        { name: "Bolt" },
      ]),
    ).toBe("When Patch, Rivet, or Bolt is present");
  });

  it("preserves witness order supplied by the caller", () => {
    // The caller (backend serializer / DB queryset) controls
    // ordering. The formatter must not reorder alphabetically.
    expect(
      formatWitnessAvailability([{ name: "Zed" }, { name: "Ada" }]),
    ).toBe("When Zed or Ada is present");
  });
});
