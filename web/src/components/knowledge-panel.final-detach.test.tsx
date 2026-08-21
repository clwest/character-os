/**
 * SESSION 276 Slice 13 / Delta Stage 3C-1 (refined Q-276-27) —
 * SPA-side regression for the final-detach error surfacing helper.
 * Verifies the SPA correctly discriminates the Slice 13 structured
 * backend error from generic errors, so the operator sees a clear
 * non-technical explanation instead of a generic "something went
 * wrong."
 *
 * See docs/design/SESSION_276_ARCHIVED_KD_RECOVERY_AUDIT.md §210-§232.
 */
import { describe, expect, it } from "vitest";
import { ApiError } from "@/lib/api/client";
import { finalDetachErrorMessage } from "./knowledge-panel";

describe("finalDetachErrorMessage (Slice 13)", () => {
  it("returns the structured backend detail on the exact Slice 13 code", () => {
    const err = new ApiError("POST /api/knowledge/... → 400", 400, {
      code: "final_character_detach_requires_audience_decision",
      detail:
        "'Ruby' is the last character using this knowledge. Removing them would leave the knowledge without an audience. Choose a new audience or archive/delete the knowledge instead.",
    });
    const message = finalDetachErrorMessage(err);
    expect(message).toContain("last character");
    expect(message).toContain("archive/delete");
  });

  it("returns null when the ApiError body carries a different code", () => {
    const err = new ApiError("POST /api/knowledge/... → 400", 400, {
      code: "some_other_error",
      detail: "unrelated",
    });
    expect(finalDetachErrorMessage(err)).toBeNull();
  });

  it("returns null when the error is not an ApiError", () => {
    expect(finalDetachErrorMessage(new Error("network fail"))).toBeNull();
    expect(finalDetachErrorMessage(null)).toBeNull();
    expect(finalDetachErrorMessage(undefined)).toBeNull();
    expect(finalDetachErrorMessage("string error")).toBeNull();
  });

  it("returns null when body is missing or malformed", () => {
    const err = new ApiError("POST → 400", 400, null);
    expect(finalDetachErrorMessage(err)).toBeNull();
    const err2 = new ApiError("POST → 400", 400, {
      code: "final_character_detach_requires_audience_decision",
      detail: 42, // wrong type
    });
    expect(finalDetachErrorMessage(err2)).toBeNull();
  });

  it("must never confuse the guard code with a substring collision", () => {
    // Guards against a future backend regression that emits a similar-
    // but-not-identical code string.
    const err = new ApiError("POST → 400", 400, {
      code: "final_character_detach_requires_audience_decision_v2",
      detail: "different variant",
    });
    expect(finalDetachErrorMessage(err)).toBeNull();
  });
});
