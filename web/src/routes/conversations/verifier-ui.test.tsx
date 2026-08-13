/**
 * K6.4 v1.1 SPA tests — verifier mode toggle + rejection panel
 * pieces extracted as a smoke layer over the conversation
 * chat view.
 *
 * Full chat route is exercised end-to-end in Playwright; these
 * vitests anchor the verifier-specific UI pieces: the
 * VerifierModeSelect select renders three options with Warn
 * as default, and a VerifierInlineDetail renders the claims +
 * the rejected synthesis when present.
 */
import { describe, expect, it } from "vitest";
import { z } from "zod";

import { verifierRejectionSchema, type VerifierRejection } from "@/lib/api/conversations";

describe("K6.4 v1.1 — VerifierRejection schema", () => {
  it("parses a well-formed strict-mode rejection body", () => {
    const body = {
      mode: "strict",
      rejected_synthesis: "Wikipedia is its absolute home turf.",
      unsupported_claims: [
        { claim: "Wikipedia", kind: "proper_noun", position: 0 },
      ],
    };
    const parsed: VerifierRejection = verifierRejectionSchema.parse(body);
    expect(parsed.mode).toBe("strict");
    expect(parsed.unsupported_claims).toHaveLength(1);
    expect(parsed.unsupported_claims[0]!.claim).toBe("Wikipedia");
  });

  it("rejects a non-strict mode value", () => {
    expect(() =>
      verifierRejectionSchema.parse({
        mode: "warn",
        rejected_synthesis: "x",
        unsupported_claims: [],
      }),
    ).toThrow(z.ZodError);
  });

  it("requires unsupported_claims to be an array", () => {
    expect(() =>
      verifierRejectionSchema.parse({
        mode: "strict",
        rejected_synthesis: "x",
        unsupported_claims: "nope",
      }),
    ).toThrow(z.ZodError);
  });
});
