/**
 * SESSION 276 Slice 12 / Delta Stage 3B-4 (Q-276-24) — SPA-side
 * regression for `universeScopeToAudienceMarker`. Load-bearing
 * assertions:
 *
 *   1. picking "None (legacy)" sentinel sends `"workspace"` marker
 *   2. picking a Universe UUID sends NO marker
 *   3. picking neither (unpicked) sends NO marker
 *   4. `universeScopePicked` unchanged by Slice 12
 *   5. helper never emits any value besides `"workspace"` or `undefined`
 *      (guards against Slice 12 silently absorbing UNIVERSE/CHARACTER
 *      inference into the marker path — those states must remain
 *      derived from `universe` FK + `spokesperson_ids` respectively)
 *
 * See docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md §186-§204.
 */
import { describe, expect, it } from "vitest";
import { UNIVERSE_LEGACY_SENTINEL } from "@/lib/api/universes";
import {
  universeScopePicked,
  universeScopeToAudienceMarker,
  universeScopeToPayload,
  type UniverseScopeValue,
} from "./knowledge";

describe("universeScopeToAudienceMarker (Slice 12)", () => {
  it("returns 'workspace' when the operator picks None (legacy)", () => {
    const marker = universeScopeToAudienceMarker(UNIVERSE_LEGACY_SENTINEL);
    expect(marker).toBe("workspace");
  });

  it("returns undefined when the operator picks a specific Universe UUID", () => {
    const universeUuid = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f";
    const marker = universeScopeToAudienceMarker(
      universeUuid as UniverseScopeValue,
    );
    expect(marker).toBeUndefined();
  });

  it("returns undefined when the picker is unpicked", () => {
    const marker = universeScopeToAudienceMarker("");
    expect(marker).toBeUndefined();
  });

  it("preserves the Slice 4 §51 asymmetry: 'workspace' OR undefined only", () => {
    // Every valid picker value maps to either the workspace marker or
    // undefined. The helper must never emit "character" / "universe" /
    // "none" — those audience states derive from other positive inputs.
    const values: UniverseScopeValue[] = [
      "",
      UNIVERSE_LEGACY_SENTINEL,
      "1a0af807-dd6a-47cd-bfaa-3d088f1c105f",
    ];
    for (const v of values) {
      const marker = universeScopeToAudienceMarker(v);
      expect(marker === "workspace" || marker === undefined).toBe(true);
    }
  });
});

describe("universeScopeToPayload (unchanged by Slice 12)", () => {
  it("throws when unpicked (submit disabled sentinel)", () => {
    expect(() => universeScopeToPayload("")).toThrow(
      /Universe scope must be explicitly picked/,
    );
  });

  it("returns null for the legacy sentinel", () => {
    expect(universeScopeToPayload(UNIVERSE_LEGACY_SENTINEL)).toBeNull();
  });

  it("returns the UUID for a Universe pick", () => {
    const uuid = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f";
    expect(universeScopeToPayload(uuid as UniverseScopeValue)).toBe(uuid);
  });
});

describe("universeScopePicked (unchanged by Slice 12)", () => {
  it("returns false when unpicked", () => {
    expect(universeScopePicked("")).toBe(false);
  });
  it("returns true when legacy sentinel picked", () => {
    expect(universeScopePicked(UNIVERSE_LEGACY_SENTINEL)).toBe(true);
  });
  it("returns true when a Universe UUID picked", () => {
    expect(
      universeScopePicked(
        "1a0af807-dd6a-47cd-bfaa-3d088f1c105f" as UniverseScopeValue,
      ),
    ).toBe(true);
  });
});
