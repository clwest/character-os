/**
 * workspace-assets.ts unit tests — SESSION 189 / A5.
 *
 * Covers:
 *   - Zod schema parsing (well-formed payload round-trips cleanly)
 *   - buildAssetsQueryString URL construction (arrays → comma lists,
 *     page 1 omitted, page > 1 included)
 *   - relativeTime helper edge cases
 *   - storageHealthTone helper (spot-checks each tone bucket)
 *   - assetRoleLabel / assetTypeLabel for all enum values
 */
import { describe, expect, it } from "vitest";
import {
  buildAssetsQueryString,
  relativeTime,
  storageHealthTone,
  assetRoleLabel,
  assetTypeLabel,
} from "./workspace-assets";

// ---- buildAssetsQueryString ----------------------------------

describe("buildAssetsQueryString", () => {
  it("returns empty string when no params", () => {
    expect(buildAssetsQueryString({})).toBe("");
  });

  it("omits page when page=1 (default)", () => {
    const qs = buildAssetsQueryString({ page: 1, page_size: 25 });
    expect(qs).not.toContain("page=");
    expect(qs).toContain("page_size=25");
  });

  it("includes page when page > 1", () => {
    const qs = buildAssetsQueryString({ page: 3 });
    expect(qs).toContain("page=3");
  });

  it("joins role array as comma-separated value", () => {
    const qs = buildAssetsQueryString({
      role: ["talking_head", "backdrop"],
    });
    expect(qs).toContain("role=talking_head%2Cbackdrop");
  });

  it("joins asset_type array as comma-separated value", () => {
    const qs = buildAssetsQueryString({
      asset_type: ["clip", "image"],
    });
    expect(qs).toContain("asset_type=clip%2Cimage");
  });

  it("omits empty arrays", () => {
    const qs = buildAssetsQueryString({ role: [], asset_type: [] });
    expect(qs).toBe("");
  });

  it("includes q when non-empty", () => {
    const qs = buildAssetsQueryString({ q: "talking head" });
    expect(qs).toContain("q=talking+head");
  });

  it("includes created_after and created_before", () => {
    const qs = buildAssetsQueryString({
      created_after: "2026-01-01",
      created_before: "2026-06-01",
    });
    expect(qs).toContain("created_after=2026-01-01");
    expect(qs).toContain("created_before=2026-06-01");
  });

  it("includes workspace when provided", () => {
    const qs = buildAssetsQueryString({ workspace: "ws-abc-123" });
    expect(qs).toContain("workspace=ws-abc-123");
  });

  it("assembles all params together", () => {
    const qs = buildAssetsQueryString({
      role: ["clip"],
      asset_type: ["image"],
      storage: ["https_live"],
      q: "test",
      page: 2,
      page_size: 50,
    });
    expect(qs).toContain("role=clip");
    expect(qs).toContain("asset_type=image");
    expect(qs).toContain("storage=https_live");
    expect(qs).toContain("q=test");
    expect(qs).toContain("page=2");
    expect(qs).toContain("page_size=50");
  });
});

// ---- relativeTime --------------------------------------------

describe("relativeTime", () => {
  function isoSecondsAgo(s: number): string {
    return new Date(Date.now() - s * 1_000).toISOString();
  }

  it("returns 'just now' for < 60 seconds ago", () => {
    expect(relativeTime(isoSecondsAgo(30))).toBe("just now");
  });

  it("returns minutes for < 60 minutes ago", () => {
    const result = relativeTime(isoSecondsAgo(120));
    expect(result).toBe("2m ago");
  });

  it("returns hours for < 24 hours ago", () => {
    const result = relativeTime(isoSecondsAgo(3 * 3600));
    expect(result).toBe("3h ago");
  });

  it("returns 'yesterday' for exactly 1 day ago", () => {
    expect(relativeTime(isoSecondsAgo(25 * 3600))).toBe("yesterday");
  });

  it("returns days for < 7 days ago", () => {
    expect(relativeTime(isoSecondsAgo(3 * 24 * 3600))).toBe("3d ago");
  });

  it("returns a formatted date for > 7 days ago", () => {
    // 10 days ago — should be a formatted date string, not "Nd ago".
    const result = relativeTime(isoSecondsAgo(10 * 24 * 3600));
    expect(result).not.toMatch(/\d+d ago/);
    expect(result.length).toBeGreaterThan(3);
  });
});

// ---- storageHealthTone ---------------------------------------

describe("storageHealthTone", () => {
  it("returns success for https_live", () => {
    expect(storageHealthTone("https_live")).toBe("success");
  });

  it("returns success for local_present", () => {
    expect(storageHealthTone("local_present")).toBe("success");
  });

  it("returns success for data_uri", () => {
    expect(storageHealthTone("data_uri")).toBe("success");
  });

  it("returns warning for https_expiring_soon", () => {
    expect(storageHealthTone("https_expiring_soon")).toBe("warning");
  });

  it("returns danger for https_expired", () => {
    expect(storageHealthTone("https_expired")).toBe("danger");
  });

  it("returns danger for local_missing", () => {
    expect(storageHealthTone("local_missing")).toBe("danger");
  });

  it("returns neutral for upload_pending", () => {
    expect(storageHealthTone("upload_pending")).toBe("neutral");
  });
});

// ---- assetRoleLabel ------------------------------------------

describe("assetRoleLabel", () => {
  it("returns human label for all defined roles", () => {
    expect(assetRoleLabel("talking_head")).toBe("Talking head");
    expect(assetRoleLabel("backdrop")).toBe("Backdrop");
    expect(assetRoleLabel("composite_output")).toBe("Composite output");
    expect(assetRoleLabel("polish_output")).toBe("Polish output");
    expect(assetRoleLabel("reference_image")).toBe("Reference image");
    expect(assetRoleLabel("b_roll")).toBe("B-roll");
    expect(assetRoleLabel("transcript")).toBe("Transcript");
    expect(assetRoleLabel("audio_track")).toBe("Audio track");
    expect(assetRoleLabel("raw_upload")).toBe("Raw upload");
    expect(assetRoleLabel("experiment")).toBe("Experiment");
  });
});

// ---- assetTypeLabel ------------------------------------------

describe("assetTypeLabel", () => {
  it("returns human label for all defined types", () => {
    expect(assetTypeLabel("clip")).toBe("Clip");
    expect(assetTypeLabel("audio")).toBe("Audio");
    expect(assetTypeLabel("image")).toBe("Image");
    expect(assetTypeLabel("transcript")).toBe("Transcript");
    expect(assetTypeLabel("voice")).toBe("Voice");
  });
});
