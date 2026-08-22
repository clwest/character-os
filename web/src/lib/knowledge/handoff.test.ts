/**
 * SESSION 277 Slice 12 (Q-277-12) — handoff contract regression.
 *
 * Small pure-function tests locking the shape of the character-
 * origin handoff URL and its inverse parse. Ensures the shared
 * helper stays truthful as callers evolve.
 */
import { describe, expect, it } from "vitest";
import {
  buildKnowledgeHandoffPath,
  parseKnowledgeHandoff,
  KNOWLEDGE_HANDOFF_ORIGINS,
} from "./handoff";

const REAL_UUID_A = "1a0af807-dd6a-47cd-bfaa-3d088f1c105f"; // Fox & Flour Universe
const REAL_UUID_B = "f4de81f3-ef65-4196-a50e-38cfc6d1854f"; // Tyson

describe("buildKnowledgeHandoffPath", () => {
  it("includes universe + spokesperson + origin when all present", () => {
    const path = buildKnowledgeHandoffPath({
      universeId: REAL_UUID_A,
      spokespersonId: REAL_UUID_B,
      origin: "character_welcome",
    });
    expect(path.startsWith("/workspace/knowledge?")).toBe(true);
    const params = new URLSearchParams(path.split("?")[1]);
    expect(params.get("universe")).toBe(REAL_UUID_A);
    expect(params.get("spokesperson")).toBe(REAL_UUID_B);
    expect(params.get("origin")).toBe("character_welcome");
  });

  it("omits the universe param when universeId is null (legacy teammate)", () => {
    const path = buildKnowledgeHandoffPath({
      universeId: null,
      spokespersonId: REAL_UUID_B,
      origin: "character_detail_knowledge_panel",
    });
    const params = new URLSearchParams(path.split("?")[1]);
    expect(params.get("universe")).toBeNull();
    expect(params.get("spokesperson")).toBe(REAL_UUID_B);
    expect(params.get("origin")).toBe("character_detail_knowledge_panel");
  });

  it("omits the universe param when universeId is undefined", () => {
    const path = buildKnowledgeHandoffPath({
      universeId: undefined,
      spokespersonId: REAL_UUID_B,
      origin: "character_welcome",
    });
    const params = new URLSearchParams(path.split("?")[1]);
    expect(params.get("universe")).toBeNull();
  });
});


describe("parseKnowledgeHandoff", () => {
  it("returns null on a bare URL (generic Knowledge flow)", () => {
    const params = new URLSearchParams();
    expect(parseKnowledgeHandoff(params)).toBeNull();
  });

  it("returns null when spokesperson is missing", () => {
    const params = new URLSearchParams({
      universe: REAL_UUID_A,
      origin: "character_welcome",
    });
    expect(parseKnowledgeHandoff(params)).toBeNull();
  });

  it("returns null when origin is missing", () => {
    const params = new URLSearchParams({
      universe: REAL_UUID_A,
      spokesperson: REAL_UUID_B,
    });
    expect(parseKnowledgeHandoff(params)).toBeNull();
  });

  it("returns null when origin is unknown", () => {
    const params = new URLSearchParams({
      universe: REAL_UUID_A,
      spokesperson: REAL_UUID_B,
      origin: "not_a_real_origin",
    });
    expect(parseKnowledgeHandoff(params)).toBeNull();
  });

  it("returns null when spokesperson isn't a UUID", () => {
    const params = new URLSearchParams({
      spokesperson: "garbage",
      origin: "character_welcome",
    });
    expect(parseKnowledgeHandoff(params)).toBeNull();
  });

  it("accepts a null universe with legacy origin (fall-back path)", () => {
    const params = new URLSearchParams({
      spokesperson: REAL_UUID_B,
      origin: "character_detail_knowledge_panel",
    });
    const parsed = parseKnowledgeHandoff(params);
    expect(parsed).toEqual({
      universeId: null,
      spokespersonId: REAL_UUID_B,
      origin: "character_detail_knowledge_panel",
    });
  });

  it("drops a malformed universe param but preserves the rest", () => {
    const params = new URLSearchParams({
      universe: "not-a-uuid",
      spokesperson: REAL_UUID_B,
      origin: "character_welcome",
    });
    const parsed = parseKnowledgeHandoff(params);
    expect(parsed).toEqual({
      universeId: null,
      spokespersonId: REAL_UUID_B,
      origin: "character_welcome",
    });
  });

  it("round-trips a complete valid handoff", () => {
    const path = buildKnowledgeHandoffPath({
      universeId: REAL_UUID_A,
      spokespersonId: REAL_UUID_B,
      origin: "character_welcome",
    });
    const params = new URLSearchParams(path.split("?")[1]);
    expect(parseKnowledgeHandoff(params)).toEqual({
      universeId: REAL_UUID_A,
      spokespersonId: REAL_UUID_B,
      origin: "character_welcome",
    });
  });

  it("KNOWLEDGE_HANDOFF_ORIGINS enumerates exactly the accepted values", () => {
    expect([...KNOWLEDGE_HANDOFF_ORIGINS]).toEqual([
      "character_welcome",
      "character_detail_knowledge_panel",
    ]);
  });
});
